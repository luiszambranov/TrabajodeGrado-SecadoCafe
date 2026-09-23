"""
planta_secado.py
==================

ModeloSecadoPlant: implementacion de la interfaz modular ``Plant`` (ver
modbus_server.py) que reemplaza a ToyPlant por el modelo real de secado
del proyecto, cerrando el lazo:

    heater_cmd/fan_cmd -> dinamica_termica (T_process, RH_process)
                        -> cinetica_dinamica (MR, via Tabla 3 Phitakwinai)
                        -> M_coffee (modelo_secado: MR -> humedad %)

Trabajo de grado - Sistema de supervision digital para el secado de cafe.
Etapa 4 del plan de implementacion escalonada (asesoria del 23 sept
2026): "Implementar ModeloSecadoPlant(Plant) en modbus_server.py".
Corresponde al item 3 pendiente de codesys/comunicacion_modbus.md,
seccion 6 ("Conectar modelo_secado.py real").

ESTADO: ESQUELETO (v0), no calibrado ni verificado end-to-end todavia.
Antes de conectar esto a CODESYS falta, como minimo (Etapa 5 del plan):

    1. Verificar que, con T/RH constantes (sin perturbaciones,
       heater_cmd fijo), esta planta reproduce la MISMA curva que ya
       valido ajuste_modelos.py (chequeo de consistencia obligatorio).
    2. Fijar M0/Me reales del caso de estudio en CondicionesSecado (hoy
       usa los valores preliminares "de relleno" de modelo_secado.py:
       50%/12% b.h. - ver advertencia en ese modulo).
    3. Calibrar ParametrosCamara (dinamica_termica.py) contra la ficha
       tecnica de la secadora fisica de referencia, o con el asesor.
    4. Decidir el factor de aceleracion temporal real a usar en las
       pruebas con CODESYS (ver mas abajo).

Factor de aceleracion temporal
----------------------------------
modelo_secado.py y dinamica_termica.py trabajan en HORAS (un secado dura
del orden de horas, hasta ~117 h para la linea base minima). El bucle
Modbus de modbus_server.py corre en segundos de RELOJ REAL (periodo_s,
por defecto 1 s). Sin un factor de aceleracion, verificar unas pocas
horas de secado en el HMI tomaria horas reales de prueba.

``factor_aceleracion`` convierte cada paso de reloj real (dt_s,
segundos) en horas de modelo:

    dt_h_modelo = (dt_s / 3600) * factor_aceleracion

Con el valor por defecto (3600.0) y periodo_s=1 s, 1 segundo real de
reloj equivale a 1 hora de modelo -- una corrida de secado de ~8 h
(propuesta supervisada) se ve completa en ~8 segundos reales en el HMI.
Es un valor PRELIMINAR elegido por conveniencia de prueba, no una
decision final: para la campana de resultados real (Monte Carlo,
comparacion de estrategias) probablemente se necesite un valor mas bajo
o correr en tiempo real 1:1, a decidir cuando se defina el diseno
experimental completo (semana 7).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from modbus_server import PLANT_MODE_HOLD, Plant, PlantInputs, PlantOutputs
from modelo_secado import CondicionesSecado, mr_a_humedad
from cinetica_dinamica import paso_mr
from dinamica_termica import ParametrosCamara, paso_temperatura, rh_proceso
import generador_ambiente as amb


@dataclass
class ParametrosModeloSecadoPlant:
    """Parametros de alto nivel de ModeloSecadoPlant (no confundir con
    ParametrosCamara, que es solo la parte termica)."""

    factor_aceleracion: float = 3600.0  # ver docstring del modulo
    params_camara: ParametrosCamara = field(default_factory=ParametrosCamara)
    cond_humedad: CondicionesSecado = field(default_factory=CondicionesSecado)
    condiciones_ambiente: Optional[amb.CondicionesClimaticas] = None  # None -> condiciones_nominales()


class ModeloSecadoPlant(Plant):
    """Planta real (esqueleto v0): cinetica de secado + dinamica termica
    de camara, en vez de la planta de juguete de primer orden.

    Ver el docstring del modulo para el estado ("ESQUELETO") y los
    pendientes antes de considerarla lista para reemplazar a ToyPlant en
    produccion/entrega.
    """

    def __init__(self, params: Optional[ParametrosModeloSecadoPlant] = None) -> None:
        self.params = params or ParametrosModeloSecadoPlant()
        self._condiciones_ambiente = self.params.condiciones_ambiente or amb.condiciones_nominales()

        self._t_process = self._condiciones_ambiente.t_min  # arranca frio, como ToyPlant.T_AMBIENTE_C
        self._mr = 1.0  # MR=1 -> M=M0 (humedad inicial), coherente con CondicionesSecado
        self._t_acumulado_h = 0.0

    def step(self, dt_s: float, inputs: PlantInputs) -> PlantOutputs:
        dt_h = (dt_s / 3600.0) * self.params.factor_aceleracion
        self._t_acumulado_h += dt_h

        # HOLD explicito de CODESYS tambien debe forzar heater/fan a 0
        # aqui -- mismo criterio que ToyPlant (comm_lost ya viene
        # resuelto en PlantInputs por el watchdog de modbus_server.py).
        heater_cmd = 0 if inputs.plant_mode == PLANT_MODE_HOLD else inputs.heater_cmd
        fan_cmd = 0 if inputs.plant_mode == PLANT_MODE_HOLD else inputs.fan_cmd

        # Ambiente: ciclo diurno nominal de generador_ambiente.py,
        # evaluado en la hora del dia correspondiente al tiempo de
        # modelo acumulado. TODO: dia a dia con condiciones_perturbadas
        # (para la campana Monte Carlo) -- por ahora repite el mismo dia
        # nominal indefinidamente (mod 24h).
        hora_del_dia = self._t_acumulado_h % 24.0
        t_ambiente = float(amb.temperatura(np.asarray([hora_del_dia]), self._condiciones_ambiente)[0])

        self._t_process = paso_temperatura(
            self._t_process, t_ambiente, heater_cmd, fan_cmd, dt_h, self.params.params_camara
        )
        rh_process = rh_proceso(self._t_process, self._condiciones_ambiente.ea_kpa)

        resultado_mr = paso_mr(self._mr, self._t_process, rh_process, dt_h)
        self._mr = resultado_mr.mr_nuevo

        m_coffee = float(mr_a_humedad(np.asarray([self._mr]), self.params.cond_humedad)[0])

        return PlantOutputs(
            t_process_c=self._t_process,
            rh_ambient_pct=rh_process,  # NOTA: hoy es RH del PROCESO, no del ambiente exterior -- ver TODO abajo
            m_coffee_pct=m_coffee,
            tiempo_proceso_h=self._t_acumulado_h,
        )


# TODO (decision pendiente, no solo de codigo): el registro Modbus
# "RH_ambient" (ver modbus_server.py) se penso originalmente para
# humedad AMBIENTE exterior (ToyPlant la simula como oscilacion, sin
# relacion con el clima real). Esta planta publica ahi la humedad
# relativa DENTRO de la camara (rh_proceso), que es mas util para
# supervisar el proceso pero cambia el significado del tag. Revisar
# junto con la tabla de variables operacionalizada (pendiente segun la
# revision del asesor) si conviene separar RH_ambient (exterior) de un
# RH_process nuevo, con su propio registro Modbus y su pieza en el HMI.


if __name__ == "__main__":
    # Smoke test manual: pasos sucesivos con heater encendido todo el
    # tiempo (sin levantar el servidor Modbus), para ver que T_process y
    # M_coffee se mueven en la direccion esperada.
    from modbus_server import PLANT_MODE_RUN

    plant = ModeloSecadoPlant()
    inputs = PlantInputs(heater_cmd=1, fan_cmd=0, plant_mode=PLANT_MODE_RUN, comm_lost=False)

    print("t_acum[h]   T_process[C]   RH_proceso[%]   M_coffee[% b.h.]")
    for i in range(20):
        outputs = plant.step(dt_s=1.0, inputs=inputs)
        if i % 2 == 0:
            print(
                f"{plant._t_acumulado_h:9.2f}   {outputs.t_process_c:11.2f}   "
                f"{outputs.rh_ambient_pct:13.1f}   {outputs.m_coffee_pct:14.2f}"
            )

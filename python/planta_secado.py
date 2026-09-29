"""
planta_secado.py
==================

ModeloSecadoPlant: implementacion de la interfaz modular ``Plant`` (ver
modbus_server.py) que reemplaza a ToyPlant por el modelo real de secado
del proyecto, cerrando el lazo:

    heater_cmd/fan_cmd -> dinamica_termica (T_process, RH_process)
                        -> cinetica_roa (M_coffee, modelo unico Roa-Cenicafe)

ACTUALIZACION 29 sept 2026:
    - La cinetica pasa de cinetica_dinamica.py (Phitakwinai et al. 2019,
      valido solo 50-70 C / 10-30 % HR) a cinetica_roa.py (isoterma de
      Trejos et al. 1989 + capa delgada de Roa, SECAFE 2008), el modelo
      unico de las tres estrategias. Phitakwinai queda como validacion.
    - M0 = 55 % b.h. y humedad de equilibrio Me(T,HR) calculada por la
      isoterma (ya no los valores "de relleno" 50 %/12 % de modelo_secado).
    - Se separan RH_ambient (HR del aire exterior) y RH_process (HR del
      aire dentro de la camara, la que recibe el cafe); cada una con su
      registro Modbus (ver modbus_server.py).
    - El ambiente puede ser una secuencia de dias (``clima_dias``) para
      que la planta reciba la misma realizacion Monte Carlo que las
      lineas base.

Trabajo de grado - Sistema de supervision digital para el secado de cafe.
Etapa 4 del plan de implementacion escalonada (asesoria del 23 sept
2026): "Implementar ModeloSecadoPlant(Plant) en modbus_server.py".
Corresponde al item 3 pendiente de codesys/comunicacion_modbus.md,
seccion 6 ("Conectar modelo_secado.py real").

ESTADO: ESQUELETO (v0), no calibrado ni verificado end-to-end todavia.
Antes de conectar esto a CODESYS falta, como minimo (Etapa 5 del plan):

    1. [HECHO 29 sept] Consistencia dinamico vs estatico a T/RH
       constantes: cinetica_roa.paso_humedad reproduce la solucion
       analitica (error ~1e-14, ver smoke test de cinetica_roa.py).
    2. [HECHO 29 sept] M0 = 55 % b.h. (cinetica_roa.M0_BH_PCT) y Me
       calculada por isoterma; humedad objetivo 11 % b.h. como criterio
       de parada (cinetica_roa.HUMEDAD_OBJETIVO_BH_PCT).
    3. Calibrar ParametrosCamara (dinamica_termica.py) contra literatura
       (resistencia electrica; la secadora fisica solo como referencia).
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
from typing import Optional, Sequence


from modbus_server import PLANT_MODE_HOLD, Plant, PlantInputs, PlantOutputs
import cinetica_roa as roa
from dinamica_termica import ParametrosCamara, paso_temperatura, rh_proceso
import generador_ambiente as amb


@dataclass
class ParametrosModeloSecadoPlant:
    """Parametros de alto nivel de ModeloSecadoPlant (no confundir con
    ParametrosCamara, que es solo la parte termica)."""

    factor_aceleracion: float = 3600.0  # ver docstring del modulo
    params_camara: ParametrosCamara = field(default_factory=ParametrosCamara)
    m0_bh_pct: float = roa.M0_BH_PCT  # humedad inicial [% b.h.]
    clima_dias: Optional[Sequence[amb.CondicionesClimaticas]] = None
    # None -> [condiciones_nominales()] (repite el dia nominal). Para
    # Monte Carlo: la MISMA lista de dias que reciben las lineas base.


class ModeloSecadoPlant(Plant):
    """Planta real (esqueleto v0): cinetica de secado + dinamica termica
    de camara, en vez de la planta de juguete de primer orden.

    Ver el docstring del modulo para el estado ("ESQUELETO") y los
    pendientes antes de considerarla lista para reemplazar a ToyPlant en
    produccion/entrega.
    """

    def __init__(self, params: Optional[ParametrosModeloSecadoPlant] = None) -> None:
        self.params = params or ParametrosModeloSecadoPlant()
        self._clima_dias = list(self.params.clima_dias or [amb.condiciones_nominales()])

        t_amb0, _, _ = amb.ambiente_en(0.0, self._clima_dias)
        self._t_process = t_amb0  # arranca a temperatura ambiente
        self._m0_bs = roa.bh_a_bs(self.params.m0_bh_pct)
        self._m_bs = self._m0_bs
        self._t_acumulado_h = 0.0
        # Contadores para la campana (control de calidad del asesor: "no
        # hay extrapolacion silenciosa"): horas de modelo fuera del rango
        # de las fuentes y horas en rehumectacion.
        self.horas_fuera_de_rango = 0.0
        self.horas_rehumectacion = 0.0

    def step(self, dt_s: float, inputs: PlantInputs) -> PlantOutputs:
        dt_h = (dt_s / 3600.0) * self.params.factor_aceleracion

        # HOLD explicito de CODESYS tambien debe forzar heater/fan a 0
        # aqui -- mismo criterio que ToyPlant (comm_lost ya viene
        # resuelto en PlantInputs por el watchdog de modbus_server.py).
        heater_cmd = 0 if inputs.plant_mode == PLANT_MODE_HOLD else inputs.heater_cmd
        fan_cmd = 0 if inputs.plant_mode == PLANT_MODE_HOLD else inputs.fan_cmd

        # Ambiente exterior (dia correspondiente de la secuencia clima_dias)
        t_ambiente, rh_ambiente, ea_kpa = amb.ambiente_en(self._t_acumulado_h, self._clima_dias)

        self._t_process = paso_temperatura(
            self._t_process, t_ambiente, heater_cmd, fan_cmd, dt_h, self.params.params_camara
        )
        # Aire de la camara = aire exterior calentado (misma ea).
        rh_process = rh_proceso(self._t_process, ea_kpa)

        r = roa.paso_humedad(self._m_bs, self._t_process, rh_process, dt_h, m0_bs_pct=self._m0_bs)
        self._m_bs = r.m_bs_pct
        self.horas_fuera_de_rango += dt_h if r.fuera_de_rango else 0.0
        self.horas_rehumectacion += dt_h if r.rehumectacion else 0.0
        self._t_acumulado_h += dt_h

        return PlantOutputs(
            t_process_c=self._t_process,
            rh_ambient_pct=rh_ambiente,
            m_coffee_pct=roa.bs_a_bh(self._m_bs),
            tiempo_proceso_h=self._t_acumulado_h,
            rh_process_pct=rh_process,
        )


if __name__ == "__main__":
    # Smoke test manual: pasos sucesivos con heater encendido todo el
    # tiempo (sin levantar el servidor Modbus), para ver que T_process y
    # M_coffee se mueven en la direccion esperada.
    from modbus_server import PLANT_MODE_RUN

    plant = ModeloSecadoPlant()
    inputs = PlantInputs(heater_cmd=1, fan_cmd=0, plant_mode=PLANT_MODE_RUN, comm_lost=False)

    print("t_acum[h]   T_process[C]   RH_ambient[%]   RH_process[%]   M_coffee[% b.h.]")
    for i in range(30):
        outputs = plant.step(dt_s=1.0, inputs=inputs)
        if i % 3 == 0:
            print(
                f"{plant._t_acumulado_h:9.2f}   {outputs.t_process_c:11.2f}   "
                f"{outputs.rh_ambient_pct:13.1f}   {outputs.rh_process_pct:13.1f}   "
                f"{outputs.m_coffee_pct:14.2f}"
            )
    print(
        f"Horas fuera de rango de las fuentes: {plant.horas_fuera_de_rango:.1f} h | "
        f"rehumectacion: {plant.horas_rehumectacion:.1f} h"
    )

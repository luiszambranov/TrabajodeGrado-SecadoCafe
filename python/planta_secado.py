"""
planta_secado.py
==================

ModeloSecadoPlant: implementacion de la interfaz modular ``Plant`` (ver
modbus_server.py) que reemplaza a ToyPlant por el modelo real de secado
del proyecto, cerrando el lazo:

    heater_cmd/fan_cmd -> secador_electrico.SecadorElectrico
                          (plenum con resistencia de 6 kW, dinamica_termica.py
                           + lecho de 20 cm por capas, lecho_secado.py:
                           Thompson + Roa-Cenicafe) -> T_process, RH_process,
                           M_coffee

ACTUALIZACION 29 sept 2026 (tarde): lote de 80 kg c.p.s., resistencia
electrica de 6 kW con enclavamiento de flujo (heater AND fan), caudal
0.1 m3/min/kg y lecho de 20 cm (Gonzalez et al., 2010). La fisica vive en
secador_electrico.py, compartida con la replica de control en Python
(control_supervisado.py) que usa la campana Monte Carlo.

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
    3. [HECHO 29 sept] Secador dimensionado con fuentes
       (dinamica_termica.ParametrosSecador; ver
       data/reference/secador_electrico_dimensionamiento.md).
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
Limitacion importante (29 sept 2026): el plenum tiene una constante de
tiempo de ~2 min. Con factor 3600 cada ciclo del servidor avanza 1 h de
modelo con heater_cmd fijo, asi que un control todo/nada desde CODESYS
oscila entre ~21 y ~63 C: sirve para ver el comportamiento cualitativo
en el HMI, NO para resultados. La campana Monte Carlo usa la replica en
Python (control_supervisado.py, ciclo de 1 s). La verificacion
CODESYS vs. replica se hace a tiempo real (--factor-aceleracion 1)
durante una ventana corta (p. ej. 60 min), comparando T_process y la
energia de la resistencia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence

from modbus_server import PLANT_MODE_HOLD, Plant, PlantInputs, PlantOutputs
import cinetica_roa as roa
import generador_ambiente as amb
from dinamica_termica import ParametrosSecador
from secador_electrico import SecadorElectrico


@dataclass
class ParametrosModeloSecadoPlant:
    """Parametros de alto nivel de ModeloSecadoPlant."""

    factor_aceleracion: float = 3600.0  # ver docstring del modulo
    secador: ParametrosSecador = field(default_factory=ParametrosSecador)
    m0_bh_pct: float = roa.M0_BH_PCT  # humedad inicial [% b.h.]
    clima_dias: Optional[Sequence[amb.CondicionesClimaticas]] = None
    # None -> [condiciones_nominales()] (repite el dia nominal). Para
    # Monte Carlo: la MISMA lista de dias que reciben las lineas base.


class ModeloSecadoPlant(Plant):
    """Planta de la propuesta supervisada detras del servidor Modbus.

    Toda la fisica esta en secador_electrico.SecadorElectrico; esta clase
    solo traduce comandos Modbus (heater_cmd, fan_cmd, plant_mode) y
    publica las salidas.
    """

    def __init__(self, params: Optional[ParametrosModeloSecadoPlant] = None) -> None:
        self.params = params or ParametrosModeloSecadoPlant()
        self.secador = SecadorElectrico(self.params.clima_dias, self.params.secador, self.params.m0_bh_pct)

    @property
    def contadores(self):
        """Energia, agua evaporada y horas fuera de rango/rehumectacion."""
        return self.secador.c

    def step(self, dt_s: float, inputs: PlantInputs) -> PlantOutputs:
        dt_h = (dt_s / 3600.0) * self.params.factor_aceleracion

        # HOLD explicito de CODESYS tambien fuerza heater/fan a 0 (mismo
        # criterio que ToyPlant; comm_lost ya viene resuelto por el
        # watchdog de modbus_server.py).
        heater_cmd = 0 if inputs.plant_mode == PLANT_MODE_HOLD else inputs.heater_cmd
        fan_cmd = 0 if inputs.plant_mode == PLANT_MODE_HOLD else inputs.fan_cmd

        flujo_invertido = bool(inputs.flow_dir_cmd) and inputs.plant_mode != PLANT_MODE_HOLD
        e = self.secador.paso(heater_cmd, fan_cmd, dt_h, flujo_invertido=flujo_invertido)
        return PlantOutputs(
            t_process_c=e.t_process_c,
            rh_ambient_pct=e.rh_ambiente_pct,
            m_coffee_pct=e.m_coffee_bh_pct,
            tiempo_proceso_h=e.t_h,
            rh_process_pct=e.rh_process_pct,
            m_coffee_max_pct=e.m_capa_max_bh_pct,
        )


if __name__ == "__main__":
    # Smoke test: 2 h de modelo en pasos de 1 min con todo/nada a 50 C
    # (equivale a correr el servidor con --factor-aceleracion 60).
    from modbus_server import PLANT_MODE_RUN

    plant = ModeloSecadoPlant(ParametrosModeloSecadoPlant(factor_aceleracion=60.0))
    heater = 1
    print("t[h]   T_process[C]  RH_amb[%]  RH_proc[%]  M_coffee[% b.h.]")
    for i in range(120):
        out = plant.step(1.0, PlantInputs(heater_cmd=heater, fan_cmd=1, plant_mode=PLANT_MODE_RUN, comm_lost=False))
        heater = 1 if out.t_process_c < 50.0 else 0
        if i % 20 == 0:
            print(f"{out.tiempo_proceso_h:5.2f}  {out.t_process_c:11.2f}  {out.rh_ambient_pct:8.1f}  "
                  f"{out.rh_process_pct:9.1f}  {out.m_coffee_pct:12.2f}")
    c = plant.contadores
    print(f"Energia resistencia {c.energia_resistencia_kwh:.2f} kWh | agua evaporada {c.agua_evaporada_kg:.2f} kg")

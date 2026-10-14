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

Configuracion (vigente desde el 29 sept 2026): lote de 80 kg c.p.s.,
M0 = 55 % b.h., resistencia electrica de 6 kW con enclavamiento de flujo
(heater AND fan), caudal nominal 0.1 m3/min/kg (8 m3/min, variable de 30
a 100 % desde el 5 oct 2026) y lecho de 20 cm (Gonzalez et al., 2010). La
fisica vive en secador_electrico.py y es la MISMA que usa la replica de
control en Python (control_supervisado.py) de la campana Monte Carlo.
Publica RH_ambient (aire exterior) y RH_process (aire de la camara) por
separado, y acepta una secuencia de dias de clima (``clima_dias``) para
recibir la misma realizacion Monte Carlo que las lineas base.

Trabajo de grado - Sistema de supervision digital para el secado de cafe.

Historial: el 23 sept 2026 esta clase reemplazo a ToyPlant con un primer
modelo (Midilli modificado de Phitakwinai et al., 2019, hoy en
python/legacy/); el 29 sept 2026 se paso al modelo unico de Roa-Cenicafe
y al secador dimensionado con fuentes
(data/reference/secador_electrico_dimensionamiento.md). Ver
docs/evolucion_del_modelo.md.

Factor de aceleracion temporal
----------------------------------
El modelo trabaja en HORAS (un secado supervisado dura ~30-50 h). El bucle
Modbus de modbus_server.py corre en segundos de RELOJ REAL (periodo_s,
por defecto 1 s). Sin un factor de aceleracion, verificar unas pocas
horas de secado en el HMI tomaria horas reales de prueba.

``factor_aceleracion`` convierte cada paso de reloj real (dt_s,
segundos) en horas de modelo:

    dt_h_modelo = (dt_s / 3600) * factor_aceleracion

Valor de uso con el HMI: factor 540 (default de modbus_server.py), es
decir 0.15 h de modelo por segundo real; un secado de ~32 h se ve en
~3.5 min. Como el plenum tiene una constante de tiempo de ~106 s, con
ese factor el termostato no puede cerrarse desde CODESYS (ver la
correccion del 4 oct 2026, abajo). La verificacion CODESYS vs. replica
se hace a tiempo real (--factor-aceleracion 1 --lazo-termico plc)
durante una ventana corta (~60 min), comparando T_process y la energia
de la resistencia.

CORRECCION 4 oct 2026 -- lazo termico local (prueba con el tutor)
--------------------------------------------------------------------
Sintoma observado: con --factor-aceleracion 540 (0.15 h de modelo por
segundo) T_process alternaba 22 C <-> 65 C en cada ciclo, RH_process
7 % <-> 68 %, y el lecho recibia aire a 65 C la mitad del tiempo
(resultado de secado invalido: grano > 50 C).

Causa: problema de MUESTREO, no de la fisica. El plenum tiene una
constante de tiempo tau = C/(m*cp) ~ 15/0.14 ~ 107 s, pero CODESYS solo
puede decidir heater_cmd una vez por ciclo del servidor, es decir cada
dt_modelo = periodo_s * factor (540 s con factor 540). Como
dt_modelo >> tau, dentro de un mismo ciclo el plenum llega al equilibrio
(63 C con resistencia, ~21 C sin ella) y el todo/nada de CODESYS ve
siempre un extremo. Un lazo de control solo funciona si el periodo de
muestreo es mucho menor que la constante de tiempo del proceso
(regla practica T_s <= tau/10, es decir varias muestras por constante
de tiempo; Astrom, K. J. & Wittenmark, B. (1997). Computer-Controlled
Systems, 3.a ed. Prentice Hall -- seleccion del periodo de muestreo).
A tiempo real (factor 1, T_s = 1 s) se cumple; con
factor >= ~10 ya no.

Solucion (arquitectura en dos niveles, como en un secador real):
    - Nivel de campo (Python, "lazo_termico='local'"): el termostato
      todo/nada del ducto se evalua cada 1 s de MODELO dentro del paso
      del servidor, exactamente como lo hace la replica de Monte Carlo
      (control_supervisado.py). El lecho avanza en sub-pasos de 1 min
      con la temperatura media del plenum. => la planta que ve CODESYS
      y la de la campana son IDENTICAS.
    - Nivel de supervision (CODESYS): modo RUN/HOLD, ventilador,
      inversion de flujo, parada por humedad, watchdog. En modo local
      el heater_cmd de CODESYS NO actua sobre la resistencia (se
      registra en el log); la resistencia la habilitan fan_cmd=1 y
      plant_mode=RUN. Python publica el ciclo de trabajo de la
      resistencia (heater_duty_pct, registros 18-19) para el HMI.
    - lazo_termico='plc' conserva el comportamiento anterior (CODESYS
      decide heater_cmd) y es el modo correcto para la verificacion a
      tiempo real (--factor-aceleracion 1).
    - lazo_termico='auto' (por defecto) elige 'plc' si el paso de
      modelo por ciclo es <= tau/10 (~10 s) y 'local' en otro caso.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Sequence

from modbus_server import PLANT_MODE_HOLD, Plant, PlantInputs, PlantOutputs
import cinetica_roa as roa
import generador_ambiente as amb
from dinamica_termica import ParametrosSecador
from secador_electrico import SecadorElectrico

log = logging.getLogger(__name__)

# Regla practica de muestreo: T_s <= tau/10 (Astrom & Wittenmark, 1997).
FRACCION_TAU_MAX = 0.1


def constante_tiempo_plenum_s(p: ParametrosSecador, t_amb_c: float = 20.0) -> float:
    """tau = C_plenum / (m_aire*cp + UA) [s], con ventilador encendido."""
    from dinamica_termica import CP_AIRE
    return p.capacidad_plenum_kj_k / (p.masa_aire_kg_s(t_amb_c) * CP_AIRE + p.ua_plenum_kw_k)


@dataclass
class ParametrosModeloSecadoPlant:
    """Parametros de alto nivel de ModeloSecadoPlant."""

    factor_aceleracion: float = 3600.0  # ver docstring del modulo
    secador: ParametrosSecador = field(default_factory=ParametrosSecador)
    m0_bh_pct: float = roa.M0_BH_PCT  # humedad inicial [% b.h.]
    clima_dias: Optional[Sequence[amb.CondicionesClimaticas]] = None
    # None -> [condiciones_nominales()] (repite el dia nominal). Para
    # Monte Carlo: la MISMA lista de dias que reciben las lineas base.
    lazo_termico: str = "auto"
    # 'auto' | 'plc' | 'local' -- ver "CORRECCION 4 oct 2026" arriba.
    setpoint_c: float = 50.0          # termostato local (Gonzalez et al., 2010)
    histeresis_c: float = 0.0         # igual a control_supervisado.ParametrosControl
    dt_lecho_h: float = 1.0 / 60.0    # sub-paso del lecho: 1 min (igual a la replica)
    dt_ciclo_s: float = 1.0           # ciclo del termostato local [s de modelo]


class ModeloSecadoPlant(Plant):
    """Planta de la propuesta supervisada detras del servidor Modbus.

    Toda la fisica esta en secador_electrico.SecadorElectrico; esta clase
    solo traduce comandos Modbus (heater_cmd, fan_cmd, plant_mode) y
    publica las salidas.
    """

    def __init__(self, params: Optional[ParametrosModeloSecadoPlant] = None, periodo_s: float = 1.0) -> None:
        self.params = params or ParametrosModeloSecadoPlant()
        self.secador = SecadorElectrico(self.params.clima_dias, self.params.secador, self.params.m0_bh_pct)
        self._heater_on = 0
        self.modo_lazo = self._resolver_modo(periodo_s)

    def reset_lote(self) -> None:
        """Nuevo lote (registro 21): secador nuevo con la humedad inicial,
        tiempo de proceso y contadores de energía en cero. Mismo clima y
        parámetros (14 oct 2026)."""
        self.secador = SecadorElectrico(self.params.clima_dias, self.params.secador, self.params.m0_bh_pct)
        self._heater_on = 0

    def _resolver_modo(self, periodo_s: float) -> str:
        modo = self.params.lazo_termico
        tau_s = constante_tiempo_plenum_s(self.params.secador)
        dt_modelo_s = periodo_s * self.params.factor_aceleracion
        if modo == "auto":
            modo = "plc" if dt_modelo_s <= FRACCION_TAU_MAX * tau_s else "local"
        if modo not in ("plc", "local"):
            raise ValueError(f"lazo_termico debe ser 'auto', 'plc' o 'local' (recibido: {modo!r})")
        if modo == "plc" and dt_modelo_s > FRACCION_TAU_MAX * tau_s:
            log.warning(
                "lazo_termico='plc' con %.0f s de modelo por ciclo y tau del plenum = %.0f s: el todo/nada de "
                "CODESYS va a oscilar entre los extremos (use --lazo-termico local o --factor-aceleracion <= %.1f).",
                dt_modelo_s, tau_s, FRACCION_TAU_MAX * tau_s / periodo_s)
        log.info("Lazo termico: %s (tau plenum = %.0f s, paso de modelo por ciclo = %.0f s)", modo, tau_s, dt_modelo_s)
        return modo

    def _termostato(self, t_process: float) -> int:
        """Todo/nada local, mismo criterio que control_supervisado.todo_nada."""
        sp, hy = self.params.setpoint_c, self.params.histeresis_c
        if t_process < sp - hy:
            self._heater_on = 1
        elif t_process >= sp + hy:
            self._heater_on = 0
        return self._heater_on

    @property
    def contadores(self):
        """Energia, agua evaporada y horas fuera de rango/rehumectacion."""
        return self.secador.c

    def step(self, dt_s: float, inputs: PlantInputs) -> PlantOutputs:
        dt_h = (dt_s / 3600.0) * self.params.factor_aceleracion

        # HOLD explicito de CODESYS tambien fuerza heater/fan a 0 (mismo
        # criterio que ToyPlant; comm_lost ya viene resuelto por el
        # watchdog de modbus_server.py).
        hold = inputs.plant_mode == PLANT_MODE_HOLD
        heater_cmd = 0 if hold else inputs.heater_cmd
        fan_cmd = 0 if hold else inputs.fan_cmd
        flujo_invertido = bool(inputs.flow_dir_cmd) and not hold
        # Manipulada 2 (5 oct 2026): 0 = CODESYS no la configura -> 100 %.
        fan_frac = inputs.fan_speed_pct / 100.0 if inputs.fan_speed_pct > 0 else 1.0

        # Sub-pasos del lecho de <= dt_lecho_h (1 min), igual que la replica.
        n = max(1, int(round(dt_h / self.params.dt_lecho_h)))
        h = dt_h / n
        e_res0 = self.secador.c.energia_resistencia_kwh
        if self.modo_lazo == "local":
            # Habilitacion de la resistencia: RUN y ventilador (el
            # enclavamiento heater AND fan lo aplica paso_plenum).
            habilitado = (not hold) and bool(fan_cmd)
            control = self._termostato if habilitado else (lambda _t: 0)
            for _ in range(n):
                e = self.secador.paso(0, fan_cmd, h, control=control, dt_ciclo_s=self.params.dt_ciclo_s,
                                      flujo_invertido=flujo_invertido, fan_frac=fan_frac)
        else:
            for _ in range(n):
                e = self.secador.paso(heater_cmd, fan_cmd, h, flujo_invertido=flujo_invertido, fan_frac=fan_frac)

        p_kw = self.params.secador.potencia_resistencia_kw
        e_res = self.secador.c.energia_resistencia_kwh - e_res0
        duty = 100.0 * e_res / (p_kw * dt_h) if dt_h > 0 else 0.0
        return PlantOutputs(
            t_process_c=e.t_process_c,
            rh_ambient_pct=e.rh_ambiente_pct,
            m_coffee_pct=e.m_coffee_bh_pct,
            tiempo_proceso_h=e.t_h,
            rh_process_pct=e.rh_process_pct,
            m_coffee_max_pct=e.m_capa_max_bh_pct,
            heater_duty_pct=duty,
            caudal_m3_min=e.caudal_m3_min,
            energia_kwh=self.secador.c.energia_electrica_kwh,
        )


if __name__ == "__main__":
    # Smoke test: emula al servidor (periodo 1 s) con factor 540 y el
    # todo/nada de CODESYS escribiendo heater_cmd cada ciclo. En modo
    # 'plc' reproduce la falla del 4 oct 2026 (22 <-> 65 C); en modo
    # 'local' T_process debe quedarse en ~50 C.
    from modbus_server import PLANT_MODE_RUN

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    for modo in ("plc", "local"):
        plant = ModeloSecadoPlant(ParametrosModeloSecadoPlant(factor_aceleracion=540.0, lazo_termico=modo))
        heater = 1
        print(f"--- lazo_termico={modo} ---")
        print("t[h]   T_process[C]  RH_proc[%]  M_coffee[% b.h.]  duty[%]")
        for i in range(60):
            out = plant.step(1.0, PlantInputs(heater_cmd=heater, fan_cmd=1, plant_mode=PLANT_MODE_RUN, comm_lost=False))
            heater = 1 if out.t_process_c < 50.0 else 0   # PLC_PRG actual
            if i >= 54:
                print(f"{out.tiempo_proceso_h:5.2f}  {out.t_process_c:11.2f}  {out.rh_process_pct:9.1f}  "
                      f"{out.m_coffee_pct:12.2f}  {out.heater_duty_pct:9.1f}")
        c = plant.contadores
        print(f"Energia resistencia {c.energia_resistencia_kwh:.2f} kWh | agua evaporada {c.agua_evaporada_kg:.2f} kg"
              f" | horas grano > 50 C: {c.horas_grano_sobre_50c:.2f}")

"""
planta_secado.py
==================

ModeloSecadoPlant: implementacion de la interfaz modular ``Plant`` (ver
modbus_server.py) con el modelo de secado del proyecto, que cierra el lazo:

    heater_cmd/fan_cmd -> secador_electrico.SecadorElectrico
                          (plenum con resistencia de 6 kW, dinamica_termica.py
                           + lecho de 20 cm por capas, lecho_secado.py:
                           Thompson + Roa-Cenicafe) -> T_process, RH_process,
                           M_coffee

Configuracion: lote de 80 kg c.p.s.,
M0 = 55 % b.h., resistencia electrica de 6 kW con enclavamiento de flujo
(heater AND fan), caudal nominal 0.1 m3/min/kg (8 m3/min, variable de 30
a 100 %) y lecho de 20 cm (Gonzalez et al., 2010). La
fisica vive en secador_electrico.py y es la MISMA que usa la replica de
control en Python (control_supervisado.py) de la campana Monte Carlo.
Publica RH_ambient (aire exterior) y RH_process (aire de la camara) por
separado, y acepta una secuencia de dias de clima (``clima_dias``) para
recibir la misma realizacion Monte Carlo que las lineas base.

Trabajo de grado - Sistema de supervision digital para el secado de cafe.

Dimensionamiento del secador: data/reference/secador_electrico_dimensionamiento.md.

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
ese factor el termostato no puede cerrarse desde CODESYS (ver
"Lazo termico local", abajo). La verificacion CODESYS vs. replica
se hace a tiempo real (--factor-aceleracion 1 --lazo-termico plc)
durante una ventana corta (~60 min), comparando T_process y la energia
de la resistencia.

Lazo termico local
------------------
Motivo: si CODESYS cerrara el termostato con --factor-aceleracion 540 (0.15 h de modelo por
segundo) T_process alternaria 22 C <-> 65 C en cada ciclo y el lecho
recibiria aire a 65 C la mitad del tiempo (grano > 50 C).

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
    - lazo_termico='plc': CODESYS decide heater_cmd y es el modo correcto para la verificacion a
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
    # 'auto' | 'plc' | 'local' -- ver "Lazo termico local" arriba.
    setpoint_c: float = 50.0          # termostato local (Gonzalez et al., 2010)
    histeresis_c: float = 0.0         # igual a control_supervisado.ParametrosControl
    dt_lecho_h: float = 1.0 / 60.0    # sub-paso del lecho: 1 min (igual a la replica)
    dt_ciclo_s: float = 1.0           # ciclo del termostato local [s de modelo]
    hora_inicio_h: float = 0.0
    """Hora del día (0-24) en que arranca la planta. 0 =
    medianoche, igual que la campaña Monte Carlo (necesario para comparar
    CODESYS contra la réplica con la misma semilla)."""
    post_ventilacion_h: float = 10.0 / 60.0
    """Política de fallo local: al perder la comunicación con
    CODESYS la resistencia se apaga de inmediato y el ventilador, si venía
    encendido, sigue este tiempo de MODELO para evacuar el calor del ducto
    (práctica de post-ventilación de calentadores de ducto; criterio propio
    declarado) y luego se apaga. 0 = todo apagado de inmediato."""
    clima_desde_lote: bool = False
    """Solo para la verificación CODESYS vs. réplica (``--semilla``): «Nuevo lote»
    reinicia también el reloj del clima a ``hora_inicio_h``, para que el lote vea
    la misma secuencia de días que la réplica de la campaña con esa semilla."""


# Estado de la planta publicado a CODESYS (registro 35)
ESTADO_REPOSO = 0        # HOLD: ventilador y resistencia apagados (la física sigue)
ESTADO_SECANDO = 1       # RUN con calentamiento permitido (SECADO / INVERSION)
ESTADO_VENTILANDO = 2    # RUN sin calentamiento (ENFRIAMIENTO)
ESTADO_POST_VENT = 3     # comunicación perdida: post-ventilación de seguridad
ESTADO_FALLA_COMM = 4    # comunicación perdida: todo apagado
ESTADOS_TXT = {0: "REPOSO", 1: "SECANDO", 2: "VENTILANDO", 3: "POST-VENTILACION", 4: "FALLA_COMM"}


class ModeloSecadoPlant(Plant):
    """Planta de la propuesta supervisada detras del servidor Modbus.

    Toda la fisica esta en secador_electrico.SecadorElectrico; esta clase
    solo traduce comandos Modbus (heater_cmd, fan_cmd, plant_mode) y
    publica las salidas.

    La planta nunca se congela. Con
    HOLD, fin de secado o comunicación perdida solo cambian los comandos
    (resistencia apagada, ventilador según la política de fallo); el
    tiempo físico, el clima día/noche, el enfriamiento y el secado
    residual siguen. Relojes que lleva:
        t_planta_h   desde que arrancó la planta (servidor); nunca se reinicia
        t_lote_h     desde el último "Nuevo lote"; incluye paradas
        t_proceso_h  horas en RUN con ventilador (secado + inversión +
                     enfriamiento); es el registro 10 que usa CODESYS para
                     la inversión cada 6 h y el enfriamiento
        t_secado_h   horas con calentamiento permitido (secado efectivo)
        t_parado_h   = t_lote_h - t_proceso_h (paradas, fallas, fin, reposo)
    """

    def __init__(self, params: Optional[ParametrosModeloSecadoPlant] = None, periodo_s: float = 1.0) -> None:
        self.params = params or ParametrosModeloSecadoPlant()
        self.secador = SecadorElectrico(self.params.clima_dias, self.params.secador, self.params.m0_bh_pct,
                                        t_inicio_h=self.params.hora_inicio_h)
        self._heater_on = 0
        self._sp_plc_c = 0.0   # consigna recibida del PLC; 0 = usar params.setpoint_c
        self.modo_lazo = self._resolver_modo(periodo_s)
        self.t_planta_h = 0.0
        self.t_proceso_h = 0.0
        self.t_secado_h = 0.0
        self._fan_previo = 0
        self._fan_frac_previa = 1.0
        self._t_post_vent_h = 0.0   # tiempo transcurrido de post-ventilación
        self.estado_planta = ESTADO_REPOSO
        self._flujo_inv_valido = False   # último sentido de aire con enlace FluidSIM válido

    @property
    def t_lote_h(self) -> float:
        return self.secador.t_h

    @property
    def t_parado_h(self) -> float:
        return max(0.0, self.t_lote_h - self.t_proceso_h)

    def reset_lote(self) -> None:
        """Nuevo lote (registro 21): café nuevo con la humedad inicial y
        tiempos de lote/energía en cero. La cámara conserva su temperatura
        y el reloj de la planta y el clima siguen."""
        self.secador.nuevo_lote(self.params.m0_bh_pct)
        if self.params.clima_desde_lote:
            self.secador.t_fisico_h = self.params.hora_inicio_h
        self._heater_on = 0
        self.t_proceso_h = 0.0
        self.t_secado_h = 0.0
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
        # la consigna la decide el PLC (perfil térmico de la HMI,
        # registro 26); si no llega (0), se usa la de los parámetros (50 °C).
        sp = self._sp_plc_c if self._sp_plc_c > 0 else self.params.setpoint_c
        hy = self.params.histeresis_c
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
        if inputs.setpoint_c > 0:
            self._sp_plc_c = inputs.setpoint_c

        run = inputs.plant_mode != PLANT_MODE_HOLD
        # Manipulada 2: 0 = CODESYS no la configura -> 100 %.
        fan_frac = inputs.fan_speed_pct / 100.0 if inputs.fan_speed_pct > 0 else 1.0

        if inputs.comm_lost:
            # Política de fallo LOCAL: no depende de la red. Resistencia
            # apagada ya; ventilador en post-ventilación si venía encendido.
            heater_cmd = 0
            permiso_calor = False
            if self._fan_previo and self._t_post_vent_h < self.params.post_ventilacion_h:
                fan_cmd, fan_frac = 1, self._fan_frac_previa
                self._t_post_vent_h += dt_h
                self.estado_planta = ESTADO_POST_VENT
            else:
                fan_cmd = 0
                self._fan_previo = 0
                self.estado_planta = ESTADO_FALLA_COMM
            flujo_invertido = False
        else:
            self._t_post_vent_h = 0.0
            fan_cmd = inputs.fan_cmd if run else 0
            heater_cmd = inputs.heater_cmd if run else 0
            # En lazo local heater_cmd de CODESYS es el PERMISO de calentar
            # (en_marcha AND calentar): en ENFRIAMIENTO el ventilador sigue
            # pero la resistencia no puede encender.
            permiso_calor = bool(run and fan_cmd and inputs.heater_cmd)
            flujo_invertido = bool(inputs.flow_dir_cmd) and run
            # Ensayo F2: con el enlace FluidSIM caído (registro
            # 40 = 3) el sentido que llega no está confirmado por un final de
            # carrera vivo: se conserva el último válido y no se inventa uno.
            if inputs.fluidsim_estado == 3:
                flujo_invertido = self._flujo_inv_valido and run
            else:
                self._flujo_inv_valido = bool(inputs.flow_dir_cmd)
            if not run or not fan_cmd:
                self.estado_planta = ESTADO_REPOSO
            else:
                self.estado_planta = ESTADO_SECANDO if permiso_calor else ESTADO_VENTILANDO
            self._fan_previo = fan_cmd
            self._fan_frac_previa = fan_frac

        # Sub-pasos del lecho de <= dt_lecho_h (1 min), igual que la replica.
        # La física avanza SIEMPRE (también con ventilador apagado).
        n = max(1, int(round(dt_h / self.params.dt_lecho_h))) if dt_h > 0 else 0
        h = dt_h / n if n else 0.0
        e_res0 = self.secador.c.energia_resistencia_kwh
        e = None
        if self.modo_lazo == "local":
            control = self._termostato if permiso_calor else (lambda _t: 0)
            for _ in range(n):
                e = self.secador.paso(0, fan_cmd, h, control=control, dt_ciclo_s=self.params.dt_ciclo_s,
                                      flujo_invertido=flujo_invertido, fan_frac=fan_frac)
        else:
            for _ in range(n):
                e = self.secador.paso(heater_cmd, fan_cmd, h, flujo_invertido=flujo_invertido, fan_frac=fan_frac)
        if e is None:
            e = self.secador.estado()

        self.t_planta_h += dt_h
        if run and fan_cmd and not inputs.comm_lost:
            self.t_proceso_h += dt_h
            if permiso_calor:
                self.t_secado_h += dt_h

        p_kw = self.params.secador.potencia_resistencia_kw
        e_res = self.secador.c.energia_resistencia_kwh - e_res0
        duty = 100.0 * e_res / (p_kw * dt_h) if dt_h > 0 else 0.0
        return PlantOutputs(
            t_process_c=e.t_process_c,
            rh_ambient_pct=e.rh_ambiente_pct,
            m_coffee_pct=e.m_coffee_bh_pct,
            tiempo_proceso_h=self.t_proceso_h,
            rh_process_pct=e.rh_process_pct,
            m_coffee_max_pct=e.m_capa_max_bh_pct,
            heater_duty_pct=duty,
            caudal_m3_min=e.caudal_m3_min,
            energia_kwh=self.secador.c.energia_electrica_kwh,
            t_ambiente_c=e.t_ambiente_c,
            hora_dia_h=e.t_fisico_h % 24.0,
            t_planta_h=self.t_planta_h,
            t_lote_h=self.t_lote_h,
            t_secado_h=self.t_secado_h,
            t_parado_h=self.t_parado_h,
            estado_planta=self.estado_planta,
            m_coffee_min_pct=e.m_capa_min_bh_pct,
            potencia_res_kw=e_res / dt_h if dt_h > 0 else 0.0,
            caudal_natural_m3_min=e.caudal_natural_m3_min,
            setpoint_aplicado_c=self._sp_plc_c if self._sp_plc_c > 0 else self.params.setpoint_c,
            fan_cmd_aplicado=fan_cmd,
            heater_permiso=int(permiso_calor) if self.modo_lazo == "local" else heater_cmd,
            flujo_invertido_aplicado=int(flujo_invertido),
        )

if __name__ == "__main__":
    # Smoke test: emula al servidor (periodo 1 s) con factor 540 y el
    # todo/nada de CODESYS escribiendo heater_cmd cada ciclo. En modo
    # 'plc' con factor alto oscila 22 <-> 65 C; en modo
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
            # PLC_PRG: en 'plc' decide el todo/nada; en 'local' solo da el permiso.
            heater = (1 if out.t_process_c < 50.0 else 0) if modo == "plc" else 1
            if i >= 54:
                print(f"{out.tiempo_proceso_h:5.2f}  {out.t_process_c:11.2f}  {out.rh_process_pct:9.1f}  "
                      f"{out.m_coffee_pct:12.2f}  {out.heater_duty_pct:9.1f}")
        c = plant.contadores
        print(f"Energia resistencia {c.energia_resistencia_kwh:.2f} kWh | agua evaporada {c.agua_evaporada_kg:.2f} kg"
              f" | horas grano > 50 C: {c.horas_grano_sobre_50c:.2f}")

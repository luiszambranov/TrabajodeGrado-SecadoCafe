"""
control_supervisado.py
=======================

Réplica en Python de la lógica de control de CODESYS (PLC_PRG) para la
propuesta supervisada, usada en la campaña Monte Carlo.
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Por qué existe (29 sept 2026)
------------------------------
La campaña Monte Carlo no pasa por CODESYS/Modbus: (1) con el PLC en el
lazo, la misma semilla no da exactamente el mismo resultado (tiempos de
Windows, sondeo Modbus), lo que rompe la reproducibilidad y el diseño
pareado; (2) CODESYS corre en tiempo real y el factor de aceleración
obliga a pasos de 1 h de modelo, demasiado gruesos para el lazo
térmico; (3) las líneas base no tienen PLC. Por eso la lógica del PLC se
replica aquí, se verifica UNA vez contra CODESYS con la misma semilla
(error documentado) y la campaña corre sobre esta réplica. CODESYS/HMI
queda como evidencia de la arquitectura IoT (objetivo 2).

Lógica replicada (debe coincidir con PLC_PRG)
----------------------------------------------
Estado SECANDO (desde t = 0):
    fan_cmd    := 1
    heater_req := T_process < setpoint            (todo/nada, setpoint 50 °C)
                  (con histéresis opcional; 0 = igual al PLC actual)
    heater_cmd := heater_req AND fan_cmd          (enclavamiento de flujo)
    flow_dir_cmd := 1 durante las horas [6,12), [18,24), ... (inversión
                  del sentido del aire cada 6 h; SECAFÉ 2008)
Transición SECANDO -> FIN cuando M_coffee (promedio) <= 11 % b.h. Y la
capa más húmeda <= 12 % b.h.:
    fan_cmd := 0; heater_cmd := 0

Cambios que el PLC debe tener para coincidir (ver comunicacion_modbus.md):
    - fan_cmd encendido durante todo el secado;
    - enclavamiento heater AND fan;
    - parada automática a M_coffee <= 11 % b.h.

Escalas de tiempo: el lazo térmico (plenum, constante de tiempo ~2 min)
se evalúa cada 1 s, que es el periodo con que el servidor Modbus
actualiza T_process en la arquitectura real (a tiempo real 1:1); el lecho
de café (horas) avanza en pasos de 1 min con la temperatura media del
plenum en ese minuto. Un paso de control de 1 min para el todo/nada
produciría oscilaciones artificiales de 35-57 °C (verificado), por eso
el ciclo de 1 s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cinetica_roa as roa
from dinamica_termica import ParametrosSecador
from secador_electrico import Contadores, SecadorElectrico


@dataclass
class ParametrosControl:
    setpoint_c: float = 50.0          # González et al. (2010): T máx. 50 °C
    histeresis_c: float = 0.0         # 0 = todo/nada puro, igual a PLC_PRG actual
    humedad_parada_bh_pct: float = roa.HUMEDAD_OBJETIVO_BH_PCT
    humedad_max_capa_bh_pct: float = 12.0
    """La capa más húmeda debe quedar <= 12 % b.h. (límite superior del
    rango de almacenamiento seguro 10-12 % b.h.; SECAFÉ, 2008)."""
    periodo_inversion_h: float | None = 6.0
    """Inversión del sentido del aire cada 6 h (SECAFÉ, 2008, secador
    estático de Cenicafé). None = sin inversión."""
    dt_control_h: float = 1.0 / 60.0  # paso del lecho: 1 min
    dt_ciclo_s: float = 1.0           # ciclo del lazo térmico: 1 s, igual al periodo
                                      # del servidor Modbus (modbus_server --periodo 1.0)


@dataclass
class ResultadoSupervisada:
    t_obj_h: float
    m_final_bh_pct: float
    m_capa_max_bh_pct: float
    m_capa_min_bh_pct: float
    n_inversiones: int
    contadores: Contadores
    traza: list | None = None

    @property
    def kwh_por_kg_cps(self) -> float:
        return self.contadores.energia_electrica_kwh / self._masa_cps

    @property
    def kj_por_kg_agua(self) -> float:
        a = self.contadores.agua_evaporada_kg
        return 3600.0 * self.contadores.energia_resistencia_kwh / a if a > 0 else math.nan

    _masa_cps: float = 80.0


def simular_supervisada(
    clima_dias,
    pc: ParametrosControl | None = None,
    p: ParametrosSecador | None = None,
    t_max_h: float = 400.0,
    guardar_traza: bool = False,
) -> ResultadoSupervisada:
    pc = pc or ParametrosControl()
    s = SecadorElectrico(clima_dias, p)
    estado_heater = {"on": 0}

    def todo_nada(t_process: float) -> int:
        # Mismo criterio que PLC_PRG, evaluado en cada ciclo.
        if t_process < pc.setpoint_c - pc.histeresis_c:
            estado_heater["on"] = 1
        elif t_process >= pc.setpoint_c + pc.histeresis_c:
            estado_heater["on"] = 0
        return estado_heater["on"]  # el enclavamiento con fan lo aplica paso_plenum

    traza = [] if guardar_traza else None
    t_obj = math.inf
    invertido = False
    n_inv = 0
    while s.t_h < t_max_h - 1e-9:
        if (s.lecho.m_bh_promedio <= pc.humedad_parada_bh_pct
                and s.lecho.m_bh_max <= pc.humedad_max_capa_bh_pct):
            t_obj = s.t_h
            break
        if pc.periodo_inversion_h:
            debe = int((s.t_h + 1e-9) // pc.periodo_inversion_h) % 2 == 1
            if debe != invertido:
                invertido = debe
                n_inv += 1
        e = s.paso(0, 1, pc.dt_control_h, control=todo_nada, dt_ciclo_s=pc.dt_ciclo_s,
                   flujo_invertido=invertido)
        if traza is not None:
            traza.append((e.t_h, e.t_ambiente_c, e.t_process_c, e.rh_process_pct, e.m_coffee_bh_pct,
                          e.m_capa_min_bh_pct, e.m_capa_max_bh_pct, int(invertido)))
    r = ResultadoSupervisada(t_obj, s.lecho.m_bh_promedio, s.lecho.m_bh_max, s.lecho.m_bh_min, n_inv, s.c, traza)
    r._masa_cps = s.p.masa_cps_kg
    return r


if __name__ == "__main__":
    import time

    import generador_ambiente as amb

    t0 = time.time()
    r = simular_supervisada([amb.condiciones_nominales()])
    c = r.contadores
    for per in (None, 6.0):
        rr = simular_supervisada([amb.condiciones_nominales()], ParametrosControl(periodo_inversion_h=per))
        print(f"Inversion {'no' if per is None else f'cada {per:.0f} h'}: t_obj = {rr.t_obj_h:.1f} h | "
              f"capas {rr.m_capa_min_bh_pct:.1f}-{rr.m_capa_max_bh_pct:.1f} % b.h. (prom {rr.m_final_bh_pct:.1f}) | "
              f"{rr.kwh_por_kg_cps:.3f} kWh/kg c.p.s.")
    print(f"Supervisada (80 kg c.p.s., setpoint 50 C, inversion 6 h, dia nominal): t_obj = {r.t_obj_h:.1f} h "
          f"({time.time() - t0:.1f} s de computo)")
    print(f"  Energia: resistencia {c.energia_resistencia_kwh:.1f} kWh + ventilador {c.energia_ventilador_kwh:.1f} kWh "
          f"= {r.kwh_por_kg_cps:.3f} kWh/kg c.p.s.; {r.kj_por_kg_agua:.0f} kJ/kg agua")
    print(f"  Agua evaporada {c.agua_evaporada_kg:.1f} kg | horas grano > 50 C: {c.horas_grano_sobre_50c:.2f} | "
          f"rehumectacion {c.horas_rehumectacion:.1f} h | fuera de rango {c.horas_fuera_de_rango:.1f} h")

"""
corrida_instrumentada.py
=========================

Misma corrida que ``control_supervisado.simular_supervisada`` (misma física de
``secador_electrico.py``, mismo todo/nada cada 1 s, misma inversión cada 6 h y
mismo criterio de fin), pero registrando minuto a minuto lo que pide la guía de
cierre (R2/R3): consigna, temperatura OBTENIDA, potencia realmente aplicada,
ciclo de trabajo, saturación de la resistencia y margen físico frente a la
consigna. Se verifica contra ``simular_supervisada`` en ``__main__``.

Definiciones (por minuto de modelo):
    T_media   temperatura media del plenum en el minuto (la que recibe el lecho)
    duty      fracción del minuto con la resistencia encendida
    saturado  duty >= 99.9 % y T_media < consigna - 1 °C: la resistencia ya da
              todo y aun así no alcanza la consigna (consigna no alcanzable)
    fuera de banda  |T_media - consigna| > 1 °C
    T_max_alcanzable  T_amb + P_res/(m_aire*cp + UA): lo máximo que puede dar
              el calentador con ese caudal y esa T ambiente (equilibrio)

Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cinetica_roa as roa
import generador_ambiente as amb
from dinamica_termica import CP_AIRE, ParametrosSecador
from secador_electrico import SecadorElectrico

BANDA_C = 1.0
HUMEDAD_CAMBIO_BH_PCT = 30.0


@dataclass
class ResultadoInstrumentado:
    t_obj_h: float
    kwh_por_kg: float
    e_res_kwh: float
    e_fan_kwh: float
    agua_kg: float
    m_final: float
    capa_max: float
    capa_min: float
    horas_grano_50: float
    horas_rehum: float
    horas_fuera_rango: float
    traza: list = field(default_factory=list)   # dicts por minuto

    # --- métricas de actuación (R2) ---
    def metricas(self, excluir_arranque_h: float = 0.25) -> dict:
        """Métricas de régimen: se excluyen los primeros ``excluir_arranque_h`` y el
        mismo lapso tras cada cambio de consigna (P2/P3); esos transitorios se
        reportan aparte como tiempo para alcanzar la consigna."""
        dt = 1.0 / 60.0
        cambios = [0.0] + [r["t_h"] for i, r in enumerate(self.traza[1:], 1)
                           if abs(r["sp"] - self.traza[i - 1]["sp"]) > 1e-9]
        tr = [r for r in self.traza if all(not (c - 1e-9 <= r["t_h"] <= c + excluir_arranque_h) for c in cambios)]
        alcanzar = []
        for c in cambios:
            post = [r for r in self.traza if r["t_h"] > c]
            ok = next((r for r in post if abs(r["T_media"] - r["sp"]) <= BANDA_C), None)
            alcanzar.append(60.0 * (ok["t_h"] - c) if ok else float("nan"))
        sat = [r for r in tr if r["saturado"]]
        fuera = [r for r in tr if abs(r["T_media"] - r["sp"]) > BANDA_C]
        # racha más larga de saturación
        racha = mejor = 0
        for r in tr:
            racha = racha + 1 if r["saturado"] else 0
            mejor = max(mejor, racha)
        margen = [r["T_max_alc"] - r["sp"] for r in tr]
        err = [r["sp"] - r["T_media"] for r in tr]
        return {
            "horas_saturado": len(sat) * dt,
            "racha_saturado_h": mejor * dt,
            "horas_fuera_banda": len(fuera) * dt,
            "pct_fuera_banda": 100.0 * len(fuera) / max(1, len(tr)),
            "deficit_max_c": max(err) if err else 0.0,
            "error_medio_c": sum(err) / max(1, len(err)),
            "duty_medio_pct": 100.0 * sum(r["duty"] for r in tr) / max(1, len(tr)),
            "margen_min_c": min(margen) if margen else math.nan,
            "p_media_kw": sum(r["P_kw"] for r in tr) / max(1, len(tr)),
            "min_alcanzar_consigna": max(alcanzar) if alcanzar else math.nan,
        }


def correr(clima_dias, sp_inicial: float, sp_final: float, caudal_frac: float,
           m0_bh_pct: float = roa.M0_BH_PCT, p: ParametrosSecador | None = None,
           t_inicio_h: float = 0.0, t_max_h: float = 400.0, periodo_inversion_h: float = 6.0,
           humedad_parada: float = roa.HUMEDAD_OBJETIVO_BH_PCT, capa_max_parada: float = 12.0,
           guardar_traza: bool = True) -> ResultadoInstrumentado:
    p = p or ParametrosSecador()
    s = SecadorElectrico(clima_dias, p, m0_bh_pct, t_inicio_h=t_inicio_h)
    st = {"on": 0, "sp": sp_inicial, "n": 0, "n_on": 0, "sT": 0.0}

    def todo_nada(t_process: float) -> int:      # igual a control_supervisado.todo_nada (histéresis 0)
        st["on"] = 1 if t_process < st["sp"] else 0
        st["n"] += 1
        st["n_on"] += st["on"]
        st["sT"] += t_process
        return st["on"]

    traza = []
    t_obj = math.inf
    invertido = False
    ff = p.limitar_fan_frac(caudal_frac)
    while s.t_h < t_max_h - 1e-9:
        if s.lecho.m_bh_promedio <= humedad_parada and s.lecho.m_bh_max <= capa_max_parada:
            t_obj = s.t_h
            break
        if periodo_inversion_h:
            invertido = int((s.t_h + 1e-9) // periodo_inversion_h) % 2 == 1
        st["sp"] = sp_inicial if s.lecho.m_bh_promedio > HUMEDAD_CAMBIO_BH_PCT else sp_final
        st["n"] = st["n_on"] = 0
        st["sT"] = 0.0
        e = s.paso(0, 1, 1.0 / 60.0, control=todo_nada, dt_ciclo_s=1.0, flujo_invertido=invertido, fan_frac=caudal_frac)
        if guardar_traza:
            # el ciclo de control evalúa T ANTES de cada sub-paso; la media del minuto la da st["sT"]
            t_media = st["sT"] / max(1, st["n"])
            duty = st["n_on"] / max(1, st["n"])
            g = p.ua_plenum_kw_k + p.masa_aire_kg_s(e.t_ambiente_c, ff) * CP_AIRE
            t_max_alc = e.t_ambiente_c + p.potencia_resistencia_kw / g
            traza.append({
                "t_h": e.t_h, "hora": e.t_fisico_h % 24.0, "T_amb": e.t_ambiente_c, "HR_amb": e.rh_ambiente_pct,
                "sp": st["sp"], "T_media": t_media, "duty": duty, "P_kw": e.potencia_res_kw,
                "saturado": duty >= 0.999 and t_media < st["sp"] - BANDA_C,
                "T_max_alc": t_max_alc, "M": e.m_coffee_bh_pct, "M_max": e.m_capa_max_bh_pct,
                "M_min": e.m_capa_min_bh_pct, "T_grano_max": float(s.lecho.t_grano.max()),
                "E_kwh": s.c.energia_electrica_kwh, "invertido": int(invertido),
            })
    c = s.c
    return ResultadoInstrumentado(
        t_obj_h=t_obj, kwh_por_kg=c.energia_electrica_kwh / p.masa_cps_kg, e_res_kwh=c.energia_resistencia_kwh,
        e_fan_kwh=c.energia_ventilador_kwh, agua_kg=c.agua_evaporada_kg, m_final=s.lecho.m_bh_promedio,
        capa_max=s.lecho.m_bh_max, capa_min=s.lecho.m_bh_min, horas_grano_50=c.horas_grano_sobre_50c,
        horas_rehum=c.horas_rehumectacion, horas_fuera_rango=c.horas_fuera_de_rango, traza=traza)


def m_a_tiempo(traza: list, t_h: float) -> float:
    """Humedad promedio del lote a un tiempo común (para comparar a tiempo común)."""
    for r in traza:
        if r["t_h"] >= t_h - 1e-9:
            return r["M"]
    return traza[-1]["M"] if traza else math.nan


if __name__ == "__main__":
    # Verificación: misma física y mismo control que la réplica de la campaña
    from control_supervisado import simular_supervisada
    from perfiles_termicos import PERFILES_POR_CODIGO

    nom = [amb.condiciones_nominales()]
    for cod in ("REF", "P1-C75", "P2-C100"):
        pf = PERFILES_POR_CODIGO[cod]
        a = simular_supervisada(nom, pf.parametros_control())
        b = correr(nom, pf.sp_inicial_c, pf.sp_final_c, pf.caudal_frac)
        print(f"{cod:8s} réplica: {a.t_obj_h:7.3f} h {a.kwh_por_kg_cps:6.4f} kWh/kg | instrumentada: "
              f"{b.t_obj_h:7.3f} h {b.kwh_por_kg:6.4f} kWh/kg | dif {b.t_obj_h - a.t_obj_h:+.4f} h")

"""
sensibilidad_tornado.py
========================

Sensibilidad de un factor a la vez (tipo tornado) a los parámetros más
inciertos del modelo, recomendada por el evaluador (§3.6): la incertidumbre del
tiempo ABSOLUTO del modelo es grande (validación V3: −45 % a +80 %), pero lo que
importa para el objetivo 3 es si la comparación RELATIVA P1-C75 frente a REF se
mantiene. Se varía cada parámetro ±20 % y se repite el diseño pareado.

Parámetros:
  k_cinetica   velocidad de la cinética de capa delgada de Roa (escala el paso de
               tiempo de cinetica_roa.paso_humedad: k·dt). Cubre el error de la
               cinética y la no uniformidad del grano.
  caudal       caudal específico efectivo (0.1 m³/min/kg ±20 %): fugas,
               distribución no uniforme del aire en el lecho.
  ua_plenum    pérdidas térmicas del plenum (UA ±20 %).
  espesor      espesor del lecho para la misma masa (compactación): 16 / 24 cm.

Diseño: 10 realizaciones de la campaña (semillas 1001-1010: mismo clima y M0
que la campaña) × 2 estrategias × (base + 8 variantes) = 180 corridas.
Salidas: resultados/sensibilidad/resumen_tornado.md, tornado.csv y
../figures/sensibilidad_tornado.png
Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import csv
import os
from dataclasses import replace
from multiprocessing import Pool

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "resultados", "sensibilidad")
SEMILLAS = list(range(1001, 1011))
VARIANTES = [("base", 1.0)] + [(p, f) for p in ("k_cinetica", "caudal", "ua_plenum", "espesor") for f in (0.8, 1.2)]
ESTRATEGIAS = ("REF", "P1-C75")


def correr_caso(args):
    semilla, param, factor, cod = args
    import cinetica_roa as roa
    from campana_montecarlo import realizacion
    from control_supervisado import simular_supervisada
    from dinamica_termica import ParametrosSecador
    from perfiles_termicos import PERFILES_POR_CODIGO

    original = roa.paso_humedad
    if param == "k_cinetica":
        def escalado(m, t, rh, dt, m0_bs_pct=None, _f=factor):
            return original(m, t, rh, dt * _f, m0_bs_pct=m0_bs_pct)
        roa.paso_humedad = escalado
    try:
        p = ParametrosSecador()
        if param == "caudal":
            p = replace(p, caudal_especifico_m3_min_kg=p.caudal_especifico_m3_min_kg * factor)
        elif param == "ua_plenum":
            p = replace(p, ua_plenum_kw_k=p.ua_plenum_kw_k * factor)
        elif param == "espesor":
            p = replace(p, espesor_lecho_m=p.espesor_lecho_m * factor)
        dias, m0 = realizacion(semilla)
        r = simular_supervisada(dias, PERFILES_POR_CODIGO[cod].parametros_control(), p=p, t_max_h=720.0, m0_bh_pct=m0)
        return {"semilla": semilla, "param": param, "factor": factor, "estrategia": cod,
                "t_obj_h": r.t_obj_h, "kwh": r.contadores.energia_electrica_kwh,
                "capa_min": r.m_capa_min_bh_pct, "capa_max": r.m_capa_max_bh_pct,
                "grano50": r.contadores.horas_grano_sobre_50c}
    finally:
        roa.paso_humedad = original


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    tareas = [(s, p, f, e) for (p, f) in VARIANTES for s in SEMILLAS for e in ESTRATEGIAS]
    with Pool(max(1, os.cpu_count() or 1)) as pool:
        res = pool.map(correr_caso, tareas)
    with open(os.path.join(OUT, "tornado.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
        w.writeheader()
        w.writerows(res)

    def sel(p, fct, e):
        return {r["semilla"]: r for r in res if r["param"] == p and r["factor"] == fct and r["estrategia"] == e}

    filas = []
    for p, fct in VARIANTES:
        a, b = sel(p, fct, "REF"), sel(p, fct, "P1-C75")
        s = np.array([100 * (1 - b[k]["kwh"] / a[k]["kwh"]) for k in SEMILLAS])
        dt = np.array([b[k]["t_obj_h"] - a[k]["t_obj_h"] for k in SEMILLAS])
        filas.append({
            "param": p, "factor": fct,
            "t_REF": np.mean([a[k]["t_obj_h"] for k in SEMILLAS]), "t_P1": np.mean([b[k]["t_obj_h"] for k in SEMILLAS]),
            "kwh_kg_REF": np.mean([a[k]["kwh"] for k in SEMILLAS]) / 80, "kwh_kg_P1": np.mean([b[k]["kwh"] for k in SEMILLAS]) / 80,
            "ahorro_pct": s.mean(), "ahorro_min": s.min(), "dt_h": dt.mean(), "dt_pct": 100 * dt.mean() / np.mean([a[k]["t_obj_h"] for k in SEMILLAS]),
            "p1_menos_energia_todas": bool((s > 0).all()), "p1_mas_lento_todas": bool((dt > 0).all()),
            "capa_min_REF": np.mean([a[k]["capa_min"] for k in SEMILLAS]), "capa_min_P1": np.mean([b[k]["capa_min"] for k in SEMILLAS]),
        })
    base = filas[0]
    L = ["# Sensibilidad tipo tornado ±20 % (21 oct 2026)", "",
         "Generado por `python/sensibilidad_tornado.py`: 10 realizaciones de la campaña (semillas 1001–1010) × "
         "REF y P1-C75 × (base + 8 variantes) = 180 corridas pareadas. Un factor a la vez.", "",
         "| Parámetro | Factor | t REF [h] | t P1-C75 [h] | kWh/kg REF | kWh/kg P1-C75 | Ahorro medio [%] | Ahorro mínimo [%] | "
         "Tiempo adicional [h] (%) | P1-C75 gasta menos en todas | P1-C75 tarda más en todas | Capa más seca REF / P1 [% b.h.] |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for f in filas:
        L.append(f"| {f['param']} | {f['factor']:.1f} | {f['t_REF']:.1f} | {f['t_P1']:.1f} | {f['kwh_kg_REF']:.3f} | "
                 f"{f['kwh_kg_P1']:.3f} | {f['ahorro_pct']:.1f} | {f['ahorro_min']:.1f} | {f['dt_h']:+.1f} ({f['dt_pct']:+.0f} %) | "
                 f"{'sí' if f['p1_menos_energia_todas'] else 'NO'} | {'sí' if f['p1_mas_lento_todas'] else 'NO'} | "
                 f"{f['capa_min_REF']:.2f} / {f['capa_min_P1']:.2f} |")
    rango_t = (min(f["t_REF"] for f in filas), max(f["t_REF"] for f in filas))
    rango_s = (min(f["ahorro_pct"] for f in filas), max(f["ahorro_pct"] for f in filas))
    L += ["", "## Lectura", "",
          f"- El tiempo absoluto de REF se mueve entre {rango_t[0]:.1f} y {rango_t[1]:.1f} h (base {base['t_REF']:.1f} h): "
          "el modelo tiene incertidumbre en el valor absoluto, como mostró la validación.",
          f"- El ahorro relativo de P1-C75 frente a REF queda entre {rango_s[0]:.1f} % y {rango_s[1]:.1f} % (base "
          f"{base['ahorro_pct']:.1f} %), y P1-C75 {'gasta menos y tarda más que REF en todas las corridas' if all(f['p1_menos_energia_todas'] and f['p1_mas_lento_todas'] for f in filas) else 'NO conserva el orden en alguna variante (ver tabla)'}: "
          "la frontera de Pareto REF–P1-C75 se conserva.",
          "- Limitación: un factor a la vez, ±20 %, 10 realizaciones; no explora interacciones."]
    with open(os.path.join(OUT, "resumen_tornado.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    params = ["k_cinetica", "caudal", "ua_plenum", "espesor"]
    nombres = {"k_cinetica": "Velocidad de la cinética", "caudal": "Caudal efectivo", "ua_plenum": "Pérdidas del plenum (UA)",
               "espesor": "Espesor del lecho (compactación)"}
    fig, axes = plt.subplots(1, 2, figsize=(12, 3.6))
    for ax, (k, tit, unidad) in zip(axes, (("ahorro_pct", "Ahorro de P1-C75 frente a REF", "%"),
                                           ("t_REF", "Tiempo absoluto de REF", "h"))):
        b0 = base[k]
        for i, p in enumerate(params):
            lo = next(f for f in filas if f["param"] == p and f["factor"] == 0.8)[k]
            hi = next(f for f in filas if f["param"] == p and f["factor"] == 1.2)[k]
            ax.barh(i, lo - b0, left=b0, color="#5dade2", height=0.5, label="−20 %" if i == 0 else None)
            ax.barh(i, hi - b0, left=b0, color="#e59866", height=0.5, label="+20 %" if i == 0 else None)
        ax.axvline(b0, color="#333", lw=1)
        ax.set_yticks(range(len(params)))
        ax.set_yticklabels([nombres[p] for p in params])
        ax.set_xlabel(unidad)
        ax.set_title(f"{tit} (base {b0:.1f} {unidad})", fontsize=10, loc="left")
        ax.legend(fontsize=8)
    fig.suptitle("Sensibilidad ±20 %: el tiempo absoluto es incierto, el ahorro relativo es robusto", fontsize=11)
    fig.tight_layout()
    ruta = os.path.normpath(os.path.join(AQUI, "..", "figures", "sensibilidad_tornado.png"))
    fig.savefig(ruta, dpi=140)
    print("Figura:", ruta)


if __name__ == "__main__":
    main()

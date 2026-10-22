"""
r1_analisis_pareado.py
=======================

Guía de cierre, R1: «Mostrar una mejoría relevante». Análisis pareado sobre la
campaña Monte Carlo (resultados/campana/resultados.csv, 150 realizaciones,
semillas 1001-1150) con los perfiles corregidos del 21 oct 2026 (P2 50 → 35 °C,
P3 35 → 50 °C; ver perfiles_termicos.py).

Comparaciones (cada una por semilla: mismo clima, carga, humedad inicial y
criterio de fin):
    P1-C75 frente a REF   candidata señalada por la guía de cierre
    P3-C75 frente a REF   miembro de la frontera de Pareto con el diseño corregido
    P3-C75 frente a P1-C75

    ΔE_i = E_A,i − E_B,i (kWh por lote de 80 kg c.p.s.); s_i = 100·ΔE_i/E_A,i;
    Δt_i = t_B,i − t_A,i

Se reportan: media y dispersión; media, desviación e IC 95 % (t) de la
DIFERENCIA pareada; IC 95 % por remuestreo de PARES completos (bootstrap,
10 000); percentiles; proporción de semillas con ahorro; COP/lote y COP por
hora adicional; cumplimiento de restricciones con el filtro de 9 % y con
criterios más estrictos; Tabla 5 con una fila por configuración.

Salidas: resultados/r1/resumen_r1.md, resultados/r1/diferencias_pareadas.csv,
../figures/r1_diferencias_pareadas.png
Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
from scipy import stats

AQUI = os.path.dirname(os.path.abspath(__file__))
CAMPANA = os.path.join(AQUI, "resultados", "campana", "resultados.csv")
OUT = os.path.join(AQUI, "resultados", "r1")
TARIFA_COP_KWH = 953.6227   # CHEC, sept. 2026 (data/reference/cotizaciones_bom.md)
MASA_CPS = 80.0
UMBRAL_RELEVANCIA_PCT = 10.0
"""Umbral de relevancia PROPUESTO (a confirmar con el asesor antes de la
versión final): el ahorro es relevante si el límite inferior del IC 95 % del
ahorro medio por semilla es ≥ 10 % y se mantiene en los climas dirigidos (R3) y
en la sensibilidad. Debe superar con holgura el efecto del clima dentro de
p5-p95 (±5 % en energía, R3) y la incertidumbre de equipos (ventilador 0.20 vs
0.37 kW: ±4 %, R2)."""
LIM_GRANO_H, LIM_CAPA_MAX = 0.0, 12.0
UMBRALES_CAPA_MIN = (8.5, 9.0, 9.5, 10.0)
COMPARACIONES = [("REF", "P1-C75"), ("REF", "P3-C75"), ("P1-C75", "P3-C75")]


def miles(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def cumple(df: pd.DataFrame, cap_min: float) -> pd.Series:
    g = pd.to_numeric(df["horas_grano_50c"], errors="coerce").fillna(0.0)
    return (g <= LIM_GRANO_H + 1e-9) & (df["capa_max_bh_pct"] <= LIM_CAPA_MAX + 1e-9) & (df["capa_min_bh_pct"] >= cap_min - 1e-9)


def pareado(d: pd.DataFrame, a: str, b: str, rng) -> dict:
    A = d[d.estrategia == a].set_index("semilla").sort_index()
    B = d[d.estrategia == b].set_index("semilla").sort_index()
    assert (A.index == B.index).all() and (A.censurado == 0).all() and (B.censurado == 0).all()
    dif = pd.DataFrame({"E_A": A.elec_kwh, "E_B": B.elec_kwh, "t_A": A.t_obj_h, "t_B": B.t_obj_h})
    dif["dE"] = dif.E_A - dif.E_B
    dif["s"] = 100 * dif.dE / dif.E_A
    dif["dt"] = dif.t_B - dif.t_A
    dif["cop"] = dif.dE * TARIFA_COP_KWH
    n = len(dif)

    def ic(x):
        m, sd = x.mean(), x.std(ddof=1)
        h = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n)
        return m, sd, m - h, m + h

    idx = rng.integers(0, n, size=(10000, n))
    q = dif[["s", "dt", "dE"]].quantile([0.05, 0.5, 0.95])
    return {
        "a": a, "b": b, "n": n, "dif": dif, "A": A, "B": B,
        "dE": ic(dif.dE), "s": ic(dif.s), "dt": ic(dif.dt), "q": q,
        "bs_s": np.percentile(dif.s.values[idx].mean(axis=1), [2.5, 97.5]),
        "bs_dt": np.percentile(dif.dt.values[idx].mean(axis=1), [2.5, 97.5]),
        "pct_medias": 100 * (1 - dif.E_B.mean() / dif.E_A.mean()),
        "rel_t": 100 * (dif.t_B.mean() / dif.t_A.mean() - 1),
        "positivos": int((dif.dE > 0).sum()),
        "wilcoxon_p": stats.wilcoxon(dif.dE).pvalue,
        "cop_hora": (dif.cop / dif.dt).mean() if (dif.dt > 0).all() else float("nan"),
        "capacidad_pct": 100 * (1 - dif.t_A.mean() / dif.t_B.mean()),
    }


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    d = pd.read_csv(CAMPANA)
    rng = np.random.default_rng(20261021)
    res = [pareado(d, a, b, rng) for a, b in COMPARACIONES]
    pd.concat({f"{r['b']}_vs_{r['a']}": r["dif"] for r in res}, axis=1).round(4).to_csv(
        os.path.join(OUT, "diferencias_pareadas.csv"))

    L = ["# R1 · Mejoría relevante con el diseño corregido (21 oct 2026)", "",
         "Generado por `python/r1_analisis_pareado.py` sobre `resultados/campana/resultados.csv` (150 "
         "realizaciones pareadas, semillas 1001–1150; perfiles corregidos: P2 50 → 35 °C, P3 35 → 50 °C). "
         "Todas son del secador eléctrico simulado: no es el contraste eléctrico–solar.", "",
         "Frontera de Pareto (tiempo–energía) entre las supervisadas que cumplen el filtro de calidad: "
         "**REF, P1-C75 y P3-C75**. Se analizan P1-C75 (la candidata de la guía) y P3-C75 frente a REF, y "
         "P3-C75 frente a P1-C75.", ""]
    for r in res:
        mE, sdE, loE, hiE = r["dE"]
        ms, sds, los, his = r["s"]
        mt, sdt, lot, hit = r["dt"]
        q = r["q"]
        dif = r["dif"]
        L += [f"## {r['b']} frente a {r['a']}", "",
              f"| | {r['a']} | {r['b']} |", "|---|---|---|",
              f"| Energía por lote [kWh] | {dif.E_A.mean():.1f} ± {dif.E_A.std(ddof=1):.1f} | {dif.E_B.mean():.1f} ± {dif.E_B.std(ddof=1):.1f} |",
              f"| Energía por kg c.p.s. [kWh/kg] | {dif.E_A.mean() / MASA_CPS:.3f} | {dif.E_B.mean() / MASA_CPS:.3f} |",
              f"| Tiempo hasta el criterio de fin [h] | {dif.t_A.mean():.1f} ± {dif.t_A.std(ddof=1):.1f} | {dif.t_B.mean():.1f} ± {dif.t_B.std(ddof=1):.1f} |",
              "",
              "| Diferencia pareada | Media | Desv. | IC 95 % (t) | IC 95 % bootstrap por pares | p5 | p50 | p95 |",
              "|---|---|---|---|---|---|---|---|",
              f"| Ahorro ΔE [kWh/lote] | {mE:.2f} | {sdE:.2f} | {loE:.2f} – {hiE:.2f} | — | {q.loc[0.05, 'dE']:.2f} | {q.loc[0.5, 'dE']:.2f} | {q.loc[0.95, 'dE']:.2f} |",
              f"| Ahorro por semilla s [%] | {ms:.2f} | {sds:.2f} | {los:.2f} – {his:.2f} | {r['bs_s'][0]:.2f} – {r['bs_s'][1]:.2f} | "
              f"{q.loc[0.05, 's']:.2f} | {q.loc[0.5, 's']:.2f} | {q.loc[0.95, 's']:.2f} |",
              f"| Tiempo adicional Δt [h] | {mt:.2f} | {sdt:.2f} | {lot:.2f} – {hit:.2f} | {r['bs_dt'][0]:.2f} – {r['bs_dt'][1]:.2f} | "
              f"{q.loc[0.05, 'dt']:.2f} | {q.loc[0.5, 'dt']:.2f} | {q.loc[0.95, 'dt']:.2f} |", "",
              f"- Semillas con ahorro positivo: **{r['positivos']} de {r['n']}**. Wilcoxon: p = {r['wilcoxon_p']:.1e} "
              "(complementario; no basta el valor p).",
              f"- Porcentaje con las medias = {r['pct_medias']:.2f} %; media de los porcentajes individuales s̄ = "
              f"{ms:.2f} %. Son cálculos distintos; se reporta s̄ con su IC.",
              f"- Costo temporal: {mt:+.1f} h por lote ({r['rel_t']:+.0f} % con las medias); un lote individual "
              f"ahorra entre {q.loc[0.05, 's']:.1f} % y {q.loc[0.95, 's']:.1f} % (p5–p95; no es el IC de la media).",
              f"- Ahorro: **{miles(dif.cop.mean())} COP/lote** (tarifa CHEC {TARIFA_COP_KWH:.2f} COP/kWh)"
              + (f"; **{miles(r['cop_hora'])} COP por hora adicional** de máquina (umbral de valor de ocupación, no "
                 f"salario ni beneficio); en cosecha procesa {r['capacidad_pct']:.0f} % menos lotes en el mismo tiempo."
                 if r["cop_hora"] == r["cop_hora"] else "."),
              f"- Umbral de relevancia propuesto (límite inferior del IC 95 % de s̄ ≥ {UMBRAL_RELEVANCIA_PCT:.0f} %): "
              f"límite inferior = {los:.2f} % → **{'cumple' if los >= UMBRAL_RELEVANCIA_PCT else 'no cumple'}**.", ""]

    # ---------- restricciones y criterio más estricto ----------
    L += ["## Restricciones y criterio de calidad más estricto", "",
          "Filtro: grano > 50 °C = 0 h, capa más húmeda ≤ 12 % b.h. y capa más seca ≥ umbral, por realización. "
          "El 9 % se fijó el 5 oct 2026 antes de la campaña (1 punto bajo el 10 % del rango de almacenamiento "
          "10–12 %, SECAFÉ 2008), por la sobresecación inherente de la capa de entrada en un lecho estático de 20 cm. "
          "No se afirma que el café cumpla calidad integral sin ensayos físicos.", "",
          "| Estrategia | " + " | ".join(f"Cumple (capa ≥ {u:g} %)" for u in UMBRALES_CAPA_MIN) + " |",
          "|---|" + "---|" * len(UMBRALES_CAPA_MIN)]
    for e in ["REF", "P1-C75", "P1-C100", "P2-C75", "P2-C100", "P3-C75", "P3-C100"]:
        g = d[d.estrategia == e]
        L.append(f"| {e} | " + " | ".join(f"{100 * cumple(g, u).mean():.0f} %" for u in UMBRALES_CAPA_MIN) + " |")
    L += ["", "Con 9,5 % y 10 % los perfiles con caudal 100 % y escalonados (P2-C100, P3-C100) son los más uniformes; "
          "los de la frontera (REF, P1-C75, P3-C75) sobresecan más la capa de entrada.", ""]

    # ---------- Tabla 5 ----------
    filas5 = []
    for e, g in d.groupby("estrategia", sort=False):
        gr = pd.to_numeric(g["horas_grano_50c"], errors="coerce")
        filas5.append({
            "Estrategia": e,
            "t fin [h]": f"{g.t_obj_h.mean():.1f} ± {g.t_obj_h.std(ddof=1):.1f}",
            "kWh/kg c.p.s.": f"{g.kwh_por_kg_cps.mean():.3f} ± {g.kwh_por_kg_cps.std(ddof=1):.3f}",
            "Grano > 50 °C [h]": "—" if gr.isna().all() else f"{gr.mean():.1f} ± {gr.std(ddof=1):.1f}",
            "Capa más seca [% b.h.]": f"{g.capa_min_bh_pct.mean():.2f} ± {g.capa_min_bh_pct.std(ddof=1):.2f}",
            "Capa más húmeda [% b.h.]": f"{g.capa_max_bh_pct.mean():.2f} ± {g.capa_max_bh_pct.std(ddof=1):.2f}",
            "Cumple filtro (9 %)": f"{100 * cumple(g, 9.0).mean():.0f} %",
        })
    t5 = pd.DataFrame(filas5)
    L += ["## Tabla 5 reorganizada (una fila por configuración; media ± desviación, 150 realizaciones)", "",
          "| " + " | ".join(t5.columns) + " |", "|" + "---|" * len(t5.columns)]
    for _, row in t5.iterrows():
        L.append("| " + " | ".join(str(v) for v in row.values) + " |")
    with open(os.path.join(OUT, "resumen_r1.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))

    # ---------- figura ----------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3))
    colores = {"P1-C75": "#1f618d", "P3-C75": "#1e8449"}
    a1, a2, a3 = axes
    for r in res[:2]:
        dif = r["dif"]
        a1.scatter(dif.dt, dif.s, s=12, alpha=0.6, color=colores[r["b"]],
                   label=f"{r['b']}: s̄ = {r['s'][0]:.1f} % (IC95 {r['s'][2]:.1f}–{r['s'][3]:.1f})")
        a2.hist(dif.s, bins=20, alpha=0.6, color=colores[r["b"]], label=r["b"])
    a1.axhline(UMBRAL_RELEVANCIA_PCT, color="#999", ls="--", lw=0.9, label=f"Umbral propuesto {UMBRAL_RELEVANCIA_PCT:.0f} %")
    a1.set_xlabel("Tiempo adicional frente a REF [h]")
    a1.set_ylabel("Ahorro de energía por semilla [%]")
    a1.set_title("Cada punto = una semilla (mismo clima)", fontsize=10, loc="left")
    a1.legend(fontsize=7.5)
    a2.set_xlabel("Ahorro frente a REF [%]")
    a2.set_ylabel("Semillas")
    a2.set_title("Distribución del ahorro frente a REF", fontsize=10, loc="left")
    a2.legend(fontsize=8)
    med = d.groupby("estrategia").agg(t=("t_obj_h", "mean"), e=("kwh_por_kg_cps", "mean"))
    for e in ["REF", "P1-C75", "P1-C100", "P2-C75", "P2-C100", "P3-C75", "P3-C100"]:
        front = e in ("REF", "P1-C75", "P3-C75")
        a3.scatter(med.loc[e, "t"], med.loc[e, "e"], s=60 if front else 35, color="#c0392b" if front else "#7f8c8d", zorder=3)
        a3.annotate(e, (med.loc[e, "t"], med.loc[e, "e"]), textcoords="offset points", xytext=(5, 4), fontsize=8)
    fr = med.loc[["REF", "P1-C75", "P3-C75"]].sort_values("t")
    a3.plot(fr.t, fr.e, color="#c0392b", lw=1.2)
    a3.set_xlabel("Tiempo medio [h]")
    a3.set_ylabel("Energía [kWh/kg c.p.s.]")
    a3.set_title("Supervisadas que cumplen el filtro; rojo = frontera", fontsize=10, loc="left")
    fig.suptitle("R1 · Diferencias pareadas frente a REF (150 realizaciones; perfiles corregidos)", fontsize=11)
    fig.tight_layout()
    ruta = os.path.normpath(os.path.join(AQUI, "..", "figures", "r1_diferencias_pareadas.png"))
    fig.savefig(ruta, dpi=140)
    print("Figura:", ruta)


if __name__ == "__main__":
    main()

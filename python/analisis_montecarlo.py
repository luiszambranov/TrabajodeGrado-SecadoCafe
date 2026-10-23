"""
analisis_montecarlo.py
=======================

Análisis estadístico de la campaña Monte Carlo (campana_montecarlo.py).
Trabajo de grado - Sistema de supervisión digital para el secado de café.
Protocolo: metodologia_estadistica_monte_carlo.md (secciones 4, 6 y 7).

Dos usos:
    # Después del PILOTO: estima sigma_d y calcula el N de la campaña final
    python analisis_montecarlo.py resultados/piloto --piloto
    # Después de la CAMPAÑA FINAL: estadística descriptiva, pruebas y figuras
    python analisis_montecarlo.py resultados/campana

Cálculo de N (fijado antes de ver el piloto)
---------------------------------------------
N = max(N_potencia, N_precision, 30), redondeado hacia arriba a decenas.
- N_potencia: comparación primaria REF (supervisada, práctica Cenicafé) vs. ACTIVA,
  prueba pareada, alfa = 0.05 bilateral, potencia 0.80, Delta = 12 h,
  d_z = Delta / sigma_d. N de la t pareada (t no central) dividido por la
  eficiencia relativa de Wilcoxon 0.955 (Lehmann, 1975).
- N_precision (criterio de convergencia): el
  intervalo de confianza del 95 % de la media de t_obj de CADA estrategia
  debe tener un semiancho <= Delta/2 = 6 h, es decir, cada media se estima
  con una precisión de la mitad de la diferencia mínima de interés.
  N = (z_0.975 · s / 6)^2.
- Mínimo de 30 realizaciones por estabilidad de las estimaciones de
  dispersión y percentiles.

Pruebas de la campaña final
---------------------------
Wilcoxon de rangos con signo pareada (Wilcoxon, 1945) sobre t_obj y sobre la
energía comprada; Shapiro-Wilk sobre las diferencias (informativo); valores p
ajustados por Holm (1979) dentro de la familia de comparaciones.
"""

from __future__ import annotations

import argparse
import sys
import csv
import math
import os
from collections import defaultdict

import numpy as np
from scipy import stats

DELTA_H = 12.0
ALFA, POTENCIA = 0.05, 0.80
ARE_WILCOXON = 0.955
N_MINIMO = 30
from perfiles_termicos import CAUDALES, PERFILES, TERMICOS

PRIMARIA = ("REF", "ACTIVA")
FACTORIALES = [p.codigo for p in PERFILES if p.codigo != "REF"]
COMPARACIONES = [  # (A, B): diferencia B - A
    ("REF", "ACTIVA"), ("REF", "PASIVA"), ("ACTIVA", "PASIVA"),
] + [("REF", c) for c in FACTORIALES]
METRICAS = [
    ("t_obj_h", "Tiempo hasta 11 % b.h. [h]"),
    ("kwh_por_kg_cps", "Energía comprada [kWh/kg c.p.s.]"),
    ("sec_total_kj_kg", "Energía total por kg de agua [kJ/kg]"),
    ("eficiencia_pct", "Eficiencia térmica [%]"),
    ("tasa_secado_pct_h", "Tasa media de secado [% b.h./h]"),
    ("capa_max_bh_pct", "Humedad final capa más húmeda [% b.h.]"),
    ("capa_min_bh_pct", "Humedad final capa más seca [% b.h.]"),
    ("horas_grano_50c", "Horas con grano > 50 °C [h]"),
    ("iae_c_h", "IAE de T_process [°C·h]"),
    ("sobreimpulso_c", "Sobreimpulso de T_process [°C]"),
    ("horas_rehumectacion", "Horas de rehumectación [h]"),
    ("horas_fuera_rango", "Horas fuera del rango de las fuentes [h]"),
]
ORDEN = ["PASIVA", "ACTIVA", "REF"] + FACTORIALES

# Filtro de calidad (definido antes de la campaña)
# - Grano > 50 °C: 0 h (daño irreversible; González et al., 2010).
# - Capa más húmeda <= 12 % b.h. (límite superior del rango seguro 10-12 %; SECAFÉ, 2008).
# - Capa más seca >= 9 % b.h. (filtro B: tolerancia de 1 punto bajo el 10 %).
#   Se reporta también el filtro estricto A (capa más seca >= 10 %).
# Una estrategia "cumple" si lo hace en al menos el 95 % de las realizaciones.
LIM_GRANO_H = 0.0
LIM_CAPA_MAX = 12.0
LIM_CAPA_MIN_B, LIM_CAPA_MIN_A = 9.0, 10.0
FRACCION_CUMPLE = 0.95


def cumplimiento(datos, e, semillas, lim_min):
    g = np.nan_to_num(vector(datos, e, "horas_grano_50c", semillas), nan=0.0)
    cmax = vector(datos, e, "capa_max_bh_pct", semillas)
    cmin = vector(datos, e, "capa_min_bh_pct", semillas)
    cens = vector(datos, e, "censurado", semillas)
    ok = (g <= LIM_GRANO_H + 1e-9) & (cmax <= LIM_CAPA_MAX + 1e-6) & (cmin >= lim_min - 1e-6) & (cens == 0)
    return float(np.mean(ok))


def pareto(puntos):
    """Códigos no dominados en (tiempo, energía), ambos a minimizar."""
    nd = []
    for c, t, e in puntos:
        if not any((t2 <= t and e2 <= e) and (t2 < t or e2 < e) for c2, t2, e2 in puntos if c2 != c):
            nd.append(c)
    return nd


def cargar(carpeta: str):
    datos: dict[str, dict[int, dict]] = defaultdict(dict)
    desc = {}
    with open(os.path.join(carpeta, "resultados.csv"), newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            datos[fila["estrategia"]][int(fila["semilla"])] = fila
            desc[fila["estrategia"]] = fila["descripcion"]
    semillas = sorted(set.intersection(*(set(v) for v in datos.values())))
    return datos, desc, semillas


def vector(datos, estrategia, metrica, semillas):
    out = []
    for s in semillas:
        v = datos[estrategia][s].get(metrica, "")
        out.append(float(v) if v not in ("", None) else math.nan)
    return np.array(out)


def n_t_pareada(dz: float) -> int:
    """N mínimo de una t pareada bilateral (t no central)."""
    if dz <= 0:
        return 10**9
    for n in range(3, 100000):
        gl = n - 1
        tc = stats.t.ppf(1 - ALFA / 2, gl)
        nc = dz * math.sqrt(n)
        pot = 1 - stats.nct.cdf(tc, gl, nc) + stats.nct.cdf(-tc, gl, nc)
        if pot >= POTENCIA:
            return n
    return 100000


def resumen(x: np.ndarray) -> dict:
    x = x[~np.isnan(x)]
    n = len(x)
    if n == 0:
        return {}
    m, s = float(np.mean(x)), float(np.std(x, ddof=1)) if n > 1 else 0.0
    h = stats.t.ppf(0.975, n - 1) * s / math.sqrt(n) if n > 1 else math.nan
    return {"n": n, "media": m, "de": s, "ic_inf": m - h, "ic_sup": m + h, "semiancho": h,
            "p5": float(np.percentile(x, 5)), "p50": float(np.percentile(x, 50)), "p95": float(np.percentile(x, 95))}


def holm(pvals: list[float]) -> list[float]:
    orden = np.argsort(pvals)
    m = len(pvals)
    adj = [0.0] * m
    acum = 0.0
    for k, i in enumerate(orden):
        acum = max(acum, (m - k) * pvals[i])
        adj[i] = min(1.0, acum)
    return adj


def analizar_piloto(datos, desc, semillas, carpeta):
    lineas = ["# Piloto Monte Carlo: cálculo de N", "",
              f"Realizaciones del piloto: **{len(semillas)}** (semillas {semillas[0]}–{semillas[-1]}).", ""]
    a, b = PRIMARIA
    d = vector(datos, b, "t_obj_h", semillas) - vector(datos, a, "t_obj_h", semillas)
    sd = float(np.std(d, ddof=1))
    dz = DELTA_H / sd if sd > 0 else math.inf
    n_t = n_t_pareada(dz) if math.isfinite(dz) else 3
    n_w = math.ceil(n_t / ARE_WILCOXON)
    lineas += ["## 1. Potencia (comparación primaria)", "",
               f"- Diferencia pareada {b} − {a}: media **{np.mean(d):.1f} h**, σ_d = **{sd:.2f} h**",
               f"- Δ = {DELTA_H} h → d_z = Δ/σ_d = **{dz:.2f}**",
               f"- N (t pareada, α = {ALFA}, potencia = {POTENCIA}) = {n_t} → Wilcoxon (÷ {ARE_WILCOXON}) = **{n_w}**", ""]
    lineas += ["## 2. Precisión de cada media (semiancho IC95 ≤ Δ/2 = 6 h)", "",
               "| Estrategia | Media t_obj [h] | DE [h] | N necesario |", "|---|---|---|---|"]
    n_prec = 0
    for e in ORDEN:
        x = vector(datos, e, "t_obj_h", semillas)
        s = float(np.std(x, ddof=1))
        n_e = math.ceil((stats.norm.ppf(0.975) * s / (DELTA_H / 2)) ** 2)
        n_prec = max(n_prec, n_e)
        lineas.append(f"| {e} ({desc[e]}) | {np.mean(x):.1f} | {s:.2f} | {n_e} |")
    n_final = int(math.ceil(max(n_w, n_prec, N_MINIMO) / 10.0) * 10)
    lineas += ["", "## 3. Resultado", "",
               f"**N de la campaña final = max({n_w}, {n_prec}, {N_MINIMO}) → {n_final} realizaciones**", "",
               "Comando sugerido (semillas nuevas, independientes del piloto):", "",
               "```", f"python campana_montecarlo.py --n {n_final} --semilla-inicial 1001 "
                      f"--salida resultados/campana --procesos 4", "```", ""]
    texto = "\n".join(lineas)
    open(os.path.join(carpeta, "calculo_N.md"), "w", encoding="utf-8").write(texto)
    print(texto)
    return n_final


def analizar_final(datos, desc, semillas, carpeta):
    L = ["# Resultados de la campaña Monte Carlo", "",
         f"Realizaciones: **{len(semillas)}** (semillas {semillas[0]}–{semillas[-1]}). Diseño pareado: las {len(ORDEN)} "
         "estrategias reciben el mismo clima y la misma humedad inicial en cada realización.", ""]
    cens = {e: int(sum(int(datos[e][s]["censurado"]) for s in semillas)) for e in ORDEN}
    L += ["## 1. Estadística descriptiva", ""]
    for met, nombre in METRICAS:
        filas = []
        for e in ORDEN:
            r = resumen(vector(datos, e, met, semillas))
            if r:
                filas.append(f"| {e} | {r['media']:.3f} | {r['de']:.3f} | [{r['ic_inf']:.3f}, {r['ic_sup']:.3f}] | "
                             f"{r['p5']:.3f} | {r['p50']:.3f} | {r['p95']:.3f} |")
        if filas:
            L += [f"### {nombre}", "", "| Estrategia | Media | DE | IC95 | P5 | P50 | P95 |", "|---|---|---|---|---|---|---|"]
            L += filas + [""]
    L += ["Tasa de éxito (llega a 11 % b.h. antes de 720 h): " +
          ", ".join(f"{e} {100 * (1 - cens[e] / len(semillas)):.0f} %" for e in ORDEN), ""]

    L += ["## 2. Diseño factorial (medias): perfil térmico x caudal", ""]
    for met, nombre in [("t_obj_h", "Tiempo [h]"), ("kwh_por_kg_cps", "Energía comprada [kWh/kg c.p.s.]"),
                        ("horas_grano_50c", "Horas con grano > 50 °C"), ("capa_max_bh_pct", "Capa más húmeda [% b.h.]")]:
        L += [f"### {nombre}", "", "| Perfil | " + " | ".join(f"Caudal {cc[1:]} %" for cc, _ in CAUDALES) + " |",
              "|---|" + "---|" * len(CAUDALES)]
        for tc, td, _, _ in TERMICOS:
            celdas = [f"{np.nanmean(vector(datos, f'{tc}-{cc}', met, semillas)):.2f}" for cc, _ in CAUDALES]
            L.append(f"| {tc} ({td}) | " + " | ".join(celdas) + " |")
        L.append(f"| REF (50 °C, 100 %) | | | {np.nanmean(vector(datos, 'REF', met, semillas)):.2f} |")
        L.append("")
    L += ["## 3. Comparaciones pareadas (Wilcoxon, Holm)", ""]
    for met, nombre in [("t_obj_h", "tiempo"), ("kwh_por_kg_cps", "energía comprada")]:
        filas, pv = [], []
        for a, b in COMPARACIONES:
            d = vector(datos, b, met, semillas) - vector(datos, a, met, semillas)
            if np.allclose(d, 0):
                p, sw = 1.0, math.nan
            else:
                p = float(stats.wilcoxon(d, zero_method="zsplit").pvalue)
                sw = float(stats.shapiro(d).pvalue) if len(d) >= 3 else math.nan
            pv.append(p)
            filas.append((a, b, float(np.mean(d)), float(np.median(d)), sw))
        adj = holm(pv)
        L += [f"### Diferencias de {nombre} (B − A)", "",
              "| A | B | Media dif. | Mediana dif. | p Wilcoxon | p Holm | Shapiro p (dif.) |", "|---|---|---|---|---|---|---|"]
        for (a, b, md, me, sw), p, pa in zip(filas, pv, adj):
            prim = " **(primaria)**" if (a, b) == PRIMARIA and met == "t_obj_h" else ""
            L.append(f"| {a} | {b}{prim} | {md:.3f} | {me:.3f} | {p:.2e} | {pa:.2e} | {sw:.3f} |")
        L.append("")

    L += ["## 4. ¿Qué perfil es mejor? Filtro de calidad + frontera de Pareto", "",
          f"Filtro B (el que se usa): grano > 50 °C = {LIM_GRANO_H:.0f} h, capa más húmeda ≤ {LIM_CAPA_MAX:.0f} % "
          f"y capa más seca ≥ {LIM_CAPA_MIN_B:.0f} % b.h., en al menos el {FRACCION_CUMPLE * 100:.0f} % de las "
          f"realizaciones. Filtro A (estricto, informativo): capa más seca ≥ {LIM_CAPA_MIN_A:.0f} %.", "",
          "| Estrategia | t_obj medio [h] | kWh/kg c.p.s. | Grano > 50 °C [h] | Capas [% b.h.] | Diferencia entre capas | "
          "Cumple B | Cumple A |", "|---|---|---|---|---|---|---|---|"]
    supervisadas = ["REF"] + FACTORIALES
    puntos, info = [], {}
    for e in ORDEN:
        t = float(np.nanmean(vector(datos, e, "t_obj_h", semillas)))
        en = float(np.nanmean(vector(datos, e, "kwh_por_kg_cps", semillas)))
        g = float(np.nanmean(np.nan_to_num(vector(datos, e, "horas_grano_50c", semillas), nan=0.0)))
        cmin = float(np.nanmean(vector(datos, e, "capa_min_bh_pct", semillas)))
        cmax = float(np.nanmean(vector(datos, e, "capa_max_bh_pct", semillas)))
        fb = cumplimiento(datos, e, semillas, LIM_CAPA_MIN_B)
        fa = cumplimiento(datos, e, semillas, LIM_CAPA_MIN_A)
        info[e] = (t, en, fb >= FRACCION_CUMPLE)
        if e in supervisadas and fb >= FRACCION_CUMPLE:
            puntos.append((e, t, en))
        L.append(f"| {e} | {t:.1f} | {en:.3f} | {g:.1f} | {cmin:.1f}–{cmax:.1f} | {cmax - cmin:.1f} | "
                 f"{'sí' if fb >= FRACCION_CUMPLE else 'no'} ({fb * 100:.0f} %) | "
                 f"{'sí' if fa >= FRACCION_CUMPLE else 'no'} ({fa * 100:.0f} %) |")
    frontera = pareto(puntos)
    L += ["", "**Supervisadas que pasan el filtro B:** " + (", ".join(c for c, _, _ in puntos) or "ninguna"), "",
          "**Frontera de Pareto (tiempo vs. energía) entre las que pasan:** " + (", ".join(
              f"{c} ({info[c][0]:.1f} h, {info[c][1]:.3f} kWh/kg)" for c in sorted(frontera, key=lambda c: info[c][0]))
              or "ninguna"), "",
          "Lectura: los perfiles de la frontera no se pueden mejorar en tiempo sin gastar más energía (o al revés); "
          "los demás que pasan el filtro están dominados. La elección dentro de la frontera depende de la prioridad: "
          "capacidad (el más rápido), costo (el de menos energía) o equilibrio.", ""]
    _figura_pareto(info, frontera, carpeta, L)

    L += ["## 5. Convergencia", ""]
    for e in ORDEN:
        x = vector(datos, e, "t_obj_h", semillas)
        r = resumen(x)
        n80 = int(0.8 * len(x))
        m80 = float(np.mean(x[:n80])) if n80 > 1 else math.nan
        L.append(f"- {e}: media final {r['media']:.1f} h, semiancho IC95 {r['semiancho']:.2f} h "
                 f"({'cumple' if r['semiancho'] <= DELTA_H / 2 else 'NO cumple'} ≤ 6 h); media con el 80 % de "
                 f"las corridas {m80:.1f} h (cambio {abs(r['media'] - m80):.2f} h)")
    L.append("")
    _figuras(datos, semillas, carpeta, L)
    texto = "\n".join(L)
    open(os.path.join(carpeta, "resumen_resultados.md"), "w", encoding="utf-8").write(texto)
    print(texto)


def _figura_pareto(info, frontera, carpeta, L):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(9, 6))
    for c, (t, e, ok) in info.items():
        if c in ("PASIVA", "ACTIVA"):
            continue
        ax.scatter(t, e, s=70, facecolors="#1565c0" if ok else "none", edgecolors="#c62828" if not ok else "#1565c0",
                   linewidths=1.5, zorder=3)
        ax.annotate(c, (t, e), textcoords="offset points", xytext=(6, 4), fontsize=9)
    if frontera:
        pf = sorted((info[c][0], info[c][1]) for c in frontera)
        ax.plot([p[0] for p in pf], [p[1] for p in pf], "--", color="#1565c0", zorder=2, label="Frontera de Pareto")
    ax.scatter([], [], s=70, color="#1565c0", label="Pasa el filtro de calidad")
    ax.scatter([], [], s=70, facecolors="none", edgecolors="#c62828", label="No pasa el filtro")
    ax.set_xlabel("Tiempo medio hasta 11 % b.h. [h]")
    ax.set_ylabel("Energía comprada media [kWh/kg c.p.s.]")
    ax.set_title("Perfiles supervisados: tiempo vs. energía")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(carpeta, "pareto_tiempo_energia.png"), dpi=150)
    plt.close(fig)
    L.append("Figura: pareto_tiempo_energia.png")
    L.append("")


def _figuras(datos, semillas, carpeta, L):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        L.append("(matplotlib no instalado: no se generaron figuras; `pip install matplotlib`)")
        return
    base = {"P1": "#1565c0", "P2": "#c62828", "P3": "#2e7d32"}
    colores = {"PASIVA": "#8d6e63", "ACTIVA": "#f9a825", "REF": "#212121"}
    colores.update({c: base[c.split("-")[0]] for c in FACTORIALES})
    # Convergencia de la media de t_obj
    fig, ax = plt.subplots(figsize=(9, 5))
    for e in ORDEN:
        x = vector(datos, e, "t_obj_h", semillas)
        n = np.arange(1, len(x) + 1)
        m = np.cumsum(x) / n
        ax.plot(n, m, label=e, color=colores[e], ls="-" if "C100" in e or "-" not in e else ("--" if "C75" in e else ":"))
    ax.set_xlabel("Número de realizaciones")
    ax.set_ylabel("Media acumulada de t_obj [h]")
    ax.set_yscale("log")
    ax.set_title("Convergencia de la media del tiempo de secado")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(carpeta, "convergencia_t_obj.png"), dpi=150)
    plt.close(fig)
    # Diagramas de caja
    for met, nombre, archivo in [("t_obj_h", "Tiempo hasta 11 % b.h. [h]", "caja_t_obj.png"),
                                 ("kwh_por_kg_cps", "Energía comprada [kWh/kg c.p.s.]", "caja_energia.png"),
                                 ("sec_total_kj_kg", "Energía total por kg de agua [kJ/kg]", "caja_sec.png")]:
        fig, ax = plt.subplots(figsize=(12, 5))
        vals = [vector(datos, e, met, semillas) for e in ORDEN]
        bp = ax.boxplot(vals, tick_labels=ORDEN, patch_artist=True)
        ax.tick_params(axis="x", rotation=45)
        for caja, e in zip(bp["boxes"], ORDEN):
            caja.set_facecolor(colores[e])
            caja.set_alpha(0.6)
        ax.set_ylabel(nombre)
        ax.grid(alpha=0.3, axis="y")
        fig.tight_layout()
        fig.savefig(os.path.join(carpeta, archivo), dpi=150)
        plt.close(fig)
    L.append("Figuras: convergencia_t_obj.png, caja_t_obj.png, caja_energia.png, caja_sec.png")


def _consola_utf8() -> None:
    try:  # consolas de Windows con codificación antigua
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--piloto", action="store_true", help="calcular N a partir del piloto")
    args = ap.parse_args()
    _consola_utf8()
    datos, desc, semillas = cargar(args.carpeta)
    if args.piloto:
        analizar_piloto(datos, desc, semillas, args.carpeta)
    else:
        analizar_final(datos, desc, semillas, args.carpeta)


if __name__ == "__main__":
    main()

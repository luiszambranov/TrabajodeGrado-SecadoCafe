"""
efecto_clima.py
================

Efecto del clima sobre el secado. Prueba dirigida,
breve y reproducible (no otra campaña factorial):

    C0 nominal · CT- / CT+ (temperatura) · CH- / CH+ (humedad) · C* combinado
    × REF y P1-C75  = 12 corridas dirigidas
    + PASIVA y ACTIVA (líneas solares) en C0 y C*  = 4 corridas adicionales

Mismo lote (80 kg c.p.s.), misma humedad inicial (55 % b.h.), misma hora de
inicio (00:00, como la campaña), mismos parámetros, mismo criterio de fin.
Niveles: ``niveles_clima.py`` (percentiles 5/95 de NASA POWER 2005-2024 sobre
medias de Naranjal, con consistencia psicrométrica).

Se comparan: tiempo hasta el criterio común de fin, humedad a un tiempo común
(24 h), energía, esfuerzo de la resistencia (ciclo de trabajo) y saturación.

Salidas: resultados/efecto_clima/resumen.md, resultados/efecto_clima/corridas.csv y
../figures/efecto_clima.png
Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import csv
import math
import os

import balance_energia as be
import cinetica_roa as roa
from corrida_instrumentada import correr, m_a_tiempo
from escenario_sol_abierto import condiciones_patio
from linea_base_activa import condiciones_activa
from niveles_clima import anomalias_percentiles, niveles
from perfiles_termicos import PERFILES_POR_CODIGO

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "resultados", "efecto_clima")
T_COMUN_H = 24.0


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    nivs = niveles()
    filas, trazas = [], {}
    for n in nivs:
        for cod in ("REF", "P1-C75"):
            pf = PERFILES_POR_CODIGO[cod]
            r = correr(n.dias(), pf.sp_inicial_c, pf.sp_final_c, pf.caudal_frac)
            m = r.metricas()
            trazas[(cod, n.codigo)] = r.traza
            filas.append({
                "estrategia": cod, "clima": n.codigo, "t_min": round(n.t_min, 2), "t_max": round(n.t_max, 2),
                "ea_kpa": round(n.ea_kpa, 3), "hr_noche": round(n.hr_noche, 1), "hr_dia": round(n.hr_dia, 1),
                "t_obj_h": round(r.t_obj_h, 2), "kwh_kg": round(r.kwh_por_kg, 4),
                "e_res_kwh": round(r.e_res_kwh, 2), "m_24h": round(m_a_tiempo(r.traza, T_COMUN_H), 2),
                "duty_pct": round(m["duty_medio_pct"], 1), "p_media_kw": round(m["p_media_kw"], 2),
                "horas_saturado": round(m["horas_saturado"], 2), "margen_min_c": round(m["margen_min_c"], 2),
                "capa_max": round(r.capa_max, 2), "capa_min": round(r.capa_min, 2),
                "horas_grano_50": round(r.horas_grano_50, 2), "horas_rehum": round(r.horas_rehum, 2),
                "horas_fuera_rango": round(r.horas_fuera_rango, 2),
            })
    # líneas solares (4 corridas adicionales)
    for n in [x for x in nivs if x.codigo in ("C0", "C*")]:
        for cod, cond, bal in (("PASIVA", condiciones_patio, be.balance_pasiva),
                               ("ACTIVA", condiciones_activa, lambda t, m: be.balance_activa(t, m0_bh=m))):
            r = roa.simular(cond(n.dias(80)), t_max_h=1500.0, m0_bh_pct=roa.M0_BH_PCT)
            t = r.t_objetivo_h
            b = bal(t, roa.M0_BH_PCT) if not math.isinf(t) else None
            m24 = float(r.m_bh_pct[min(len(r.m_bh_pct) - 1, int(round(T_COMUN_H / 0.25)))])
            filas.append({"estrategia": cod, "clima": n.codigo, "t_min": round(n.t_min, 2), "t_max": round(n.t_max, 2),
                          "ea_kpa": round(n.ea_kpa, 3), "hr_noche": round(n.hr_noche, 1), "hr_dia": round(n.hr_dia, 1),
                          "t_obj_h": round(t, 2), "kwh_kg": round(b.comprada_kwh_por_kg_cps, 4) if b else "",
                          "e_res_kwh": 0.0, "m_24h": round(m24, 2), "duty_pct": "", "p_media_kw": "",
                          "horas_saturado": "", "margen_min_c": "", "capa_max": "", "capa_min": "",
                          "horas_grano_50": "", "horas_rehum": round(r.horas_rehumectacion, 2),
                          "horas_fuera_rango": round(r.horas_fuera_de_rango, 2)})

    with open(os.path.join(OUT, "corridas.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    # ---------- resumen ----------
    a = anomalias_percentiles()
    base = {f["estrategia"]: f for f in filas if f["clima"] == "C0"}

    def rel(f, k):
        b = base[f["estrategia"]][k]
        return f"{100 * (f[k] / b - 1):+.1f} %" if isinstance(f[k], float) and b else ""

    L = ["# Efecto del clima: prueba dirigida", "",
         "Generado por `python/efecto_clima.py` (12 corridas dirigidas + 4 solares). Mismo lote, "
         "M0 = 55 % b.h., inicio 00:00, criterio de fin promedio ≤ 11 % y capa más húmeda ≤ 12 % b.h.", "",
         "## Cadena de datos", "",
         "| Paso | Qué | Archivo / función | Unidades |", "|---|---|---|---|",
         "| Fuente 1 (medición) | Medias de T mín y T máx de la estación Naranjal (Cenicafé) | "
         "`generador_ambiente.T_MIN_MEDIO`, `T_MAX_MEDIO` (Baldión-Rincón y Guzmán-Martínez, 1998) | °C |",
         "| Fuente 2 (reanálisis) | Serie diaria NASA POWER 2005-2024, punto 4.97 N, 75.65 O: "
         "`T2M_MAX`, `T2M_MIN`, `QV2M`, `PS` | `data/clima/POWER_Naranjal_diario_2005_2024.csv`; "
         "`variabilidad_clima.leer_power_csv` | °C, g/kg, kPa |",
         f"| Transformación | ea = q·PS/(0.622+0.378q); anomalías respecto a la media mensual; media móvil de "
         f"2 días; percentiles 5 y 95 ({a['n_dias']} días) | `niveles_clima.anomalias_percentiles` | °C, fracción |",
         "| Niveles (sintéticos) | Medias de Naranjal + anomalía percentil; ea con consistencia psicrométrica | "
         "`niveles_clima.niveles` | °C, kPa |",
         "| Perturbación horaria | Ciclo diario asimétrico (mín. 05:30, máx. 15:30); HR = ea/es(T) | "
         "`generador_ambiente.temperatura`, `humedad_relativa`, `ambiente_en` | °C, % |",
         "| Entrada a la planta | T_amb y ea entran al balance del plenum (Ec. 5) y al aire del lecho "
         "(misma ea; HR de proceso = ea/es(T_proceso)) | `dinamica_termica.paso_plenum`, `rh_proceso`; "
         "`lecho_secado.LechoThompson.paso` | °C, kPa |",
         "| Salidas | Humedad del café por capa, tiempo hasta el criterio, energía, ciclo de trabajo | "
         "`corrida_instrumentada.correr` | % b.h., h, kWh |", "",
         "Los niveles son realizaciones sintéticas construidas con percentiles; no son mediciones de la estación.", "",
         "## Niveles de clima", "", "| Nivel | T mín [°C] | T máx [°C] | ea [kPa] | HR madrugada | HR tarde | Origen |",
         "|---|---|---|---|---|---|---|"]
    for n in nivs:
        L.append(f"| {n.codigo} | {n.t_min:.2f} | {n.t_max:.2f} | {n.ea_kpa:.3f} | {n.hr_noche:.1f} % | "
                 f"{n.hr_dia:.1f} % | {n.origen} |")
    L += ["", "## Resultados (supervisadas)", "",
          "| Estrategia | Clima | t fin [h] | Δt vs C0 | kWh/kg | ΔE vs C0 | Humedad a 24 h [% b.h.] | "
          "Ciclo de trabajo [%] | P media [kW] | Saturado [h] | Margen mín. [°C] | Grano > 50 °C [h] |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for f in [f for f in filas if f["estrategia"] in ("REF", "P1-C75")]:
        L.append(f"| {f['estrategia']} | {f['clima']} | {f['t_obj_h']} | {rel(f, 't_obj_h')} | {f['kwh_kg']} | "
                 f"{rel(f, 'kwh_kg')} | {f['m_24h']} | {f['duty_pct']} | {f['p_media_kw']} | {f['horas_saturado']} | "
                 f"{f['margen_min_c']} | {f['horas_grano_50']} |")
    L += ["", "## Ahorro de P1-C75 frente a REF en cada clima (pareado: mismo clima)", "",
          "| Clima | Ahorro de energía | Tiempo adicional |", "|---|---|---|"]
    for n in nivs:
        r_ = next(f for f in filas if f["estrategia"] == "REF" and f["clima"] == n.codigo)
        p_ = next(f for f in filas if f["estrategia"] == "P1-C75" and f["clima"] == n.codigo)
        L.append(f"| {n.codigo} | {100 * (1 - p_['kwh_kg'] / r_['kwh_kg']):.1f} % | "
                 f"{p_['t_obj_h'] - r_['t_obj_h']:+.1f} h ({100 * (p_['t_obj_h'] / r_['t_obj_h'] - 1):+.0f} %) |")
    L += ["", "## Líneas solares (contraste nominal / adverso)", "",
          "| Estrategia | Clima | t fin [h] | Δt vs C0 | Humedad a 24 h [% b.h.] | kWh/kg comprados |", "|---|---|---|---|---|---|"]
    for f in [f for f in filas if f["estrategia"] in ("PASIVA", "ACTIVA")]:
        L.append(f"| {f['estrategia']} | {f['clima']} | {f['t_obj_h']} | {rel(f, 't_obj_h')} | {f['m_24h']} | {f['kwh_kg']} |")
    with open(os.path.join(OUT, "resumen.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))

    # ---------- figura ----------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colores = {"C0": "#222222", "CT-": "#2471a3", "CT+": "#c0392b", "CH-": "#d4ac0d", "CH+": "#17a589", "C*": "#7d3c98"}
    fig = plt.figure(figsize=(12, 9))
    gs = fig.add_gridspec(2, 2)
    for j, cod in enumerate(("REF", "P1-C75")):
        ax = fig.add_subplot(gs[0, j])
        ax2 = ax.twinx() if j == 1 else None
        for n in nivs:
            tr = trazas[(cod, n.codigo)]
            ax.plot([x["t_h"] for x in tr], [x["M"] for x in tr], color=colores[n.codigo], lw=1.2, label=n.codigo)
        ax.axhline(11, color="#999", ls=":", lw=0.8)
        ax.axvline(T_COMUN_H, color="#999", ls="--", lw=0.8)
        ax.set_title(f"{cod}: humedad promedio del lote", fontsize=10, loc="left")
        ax.set_xlabel("Tiempo de lote [h]")
        ax.set_ylabel("% b.h.")
        ax.legend(fontsize=8, ncol=3)
        if ax2:
            ax2.set_yticks([])
    ax = fig.add_subplot(gs[1, 0])
    for n in nivs:
        tr = trazas[("REF", n.codigo)]
        # media horaria (el todo/nada conmuta cada segundo; por minuto la potencia sale en escalones de 0.1 kW)
        P = [x["P_kw"] for x in tr]
        T = [x["t_h"] for x in tr]
        ph = [sum(P[i:i + 60]) / len(P[i:i + 60]) for i in range(0, len(P), 60)]
        th = [T[min(i + 30, len(T) - 1)] for i in range(0, len(P), 60)]
        ax.plot(th, ph, color=colores[n.codigo], lw=1.2, label=n.codigo)
    ax.set_title("REF: potencia media horaria de la resistencia (esfuerzo del control)", fontsize=10, loc="left")
    ax.set_xlabel("Tiempo de lote [h]")
    ax.set_ylabel("kW")
    ax.axhline(6.0, color="#999", ls=":", lw=0.8)
    ax.legend(fontsize=8, ncol=3)
    ax = fig.add_subplot(gs[1, 1])
    labs = [n.codigo for n in nivs if n.codigo != "C0"]
    import numpy as np
    x = np.arange(len(labs))
    for k, (cod, off) in enumerate((("REF", -0.2), ("P1-C75", 0.2))):
        b = base[cod]
        de = [100 * (next(f for f in filas if f["estrategia"] == cod and f["clima"] == c)["kwh_kg"] / b["kwh_kg"] - 1) for c in labs]
        dt = [100 * (next(f for f in filas if f["estrategia"] == cod and f["clima"] == c)["t_obj_h"] / b["t_obj_h"] - 1) for c in labs]
        ax.bar(x + off - 0.1, de, 0.2, color=["#c0392b", "#e59866"][k], label=f"{cod}: Δ energía")
        ax.bar(x + off + 0.1, dt, 0.2, color=["#2471a3", "#85c1e9"][k], label=f"{cod}: Δ tiempo")
    ax.axhline(0, color="#333", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labs)
    ax.set_ylabel("% respecto a C0")
    ax.set_title("Cambio de energía y tiempo frente al clima nominal", fontsize=10, loc="left")
    ax.legend(fontsize=7, ncol=2)
    fig.suptitle("Efecto separado de temperatura y humedad ambiente (niveles p5/p95 de NASA POWER)", fontsize=11)
    fig.tight_layout()
    ruta = os.path.normpath(os.path.join(AQUI, "..", "figures", "efecto_clima.png"))
    fig.savefig(ruta, dpi=140)
    print("Figura:", ruta)


if __name__ == "__main__":
    main()

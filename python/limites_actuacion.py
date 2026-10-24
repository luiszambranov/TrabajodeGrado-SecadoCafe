"""
limites_actuacion.py
=====================

Límites de actuación. Comprueba que la
respuesta simulada respeta la potencia y el caudal declarados, y cuándo la
consigna deja de ser alcanzable. No diseña otro controlador ni aumenta equipos
para hacer pasar la prueba.

Corridas (misma física y control que la campaña, ``corrida_instrumentada.py``):
  1. Los 10 perfiles en clima nominal (C0) y en clima frío (CT-, p5 de NASA
     POWER), arrancando a medianoche como la campaña: horas de saturación,
     tiempo fuera de banda, déficit máximo y margen físico.
  2. El caso más exigente encontrado, arrancando a las 18:00 para que la fase
     alta caiga en la madrugada fría.
  3. Sensibilidades: tensión 10 % baja (6 kW -> 4.86 kW, P ∝ V²) y ventilador
     cotizado de 0.37 kW en lugar de 0.20 kW.
  4. Caso hipotético de helada (-4 °C), fuera del clima
     del sitio; muestra qué consignas dejan de ser alcanzables con 6 kW.

Salidas: resultados/limites_actuacion/resumen.md, resultados/limites_actuacion/casos.csv y
../figures/limites_actuacion.png.
Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import csv
import os
from dataclasses import replace

from corrida_instrumentada import correr
from dinamica_termica import CP_AIRE, ParametrosSecador, densidad_aire, potencia_requerida_kw
from niveles_clima import helada_hipotetica, niveles
from perfiles_termicos import PERFILES

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "resultados", "limites_actuacion")


def fila(caso, perfil, nivel, r, t_ini, p):
    m = r.metricas()
    return {
        "caso": caso, "perfil": perfil.codigo, "clima": nivel.codigo, "hora_inicio": t_ini,
        "P_res_kw": p.potencia_resistencia_kw, "P_fan_kw": p.potencia_ventilador_kw,
        "t_obj_h": round(r.t_obj_h, 2), "kwh_kg": round(r.kwh_por_kg, 4),
        "horas_saturado": round(m["horas_saturado"], 2), "racha_saturado_h": round(m["racha_saturado_h"], 2),
        "horas_fuera_banda": round(m["horas_fuera_banda"], 2), "pct_fuera_banda": round(m["pct_fuera_banda"], 1),
        "deficit_max_c": round(m["deficit_max_c"], 2), "margen_min_c": round(m["margen_min_c"], 2),
        "duty_medio_pct": round(m["duty_medio_pct"], 1), "min_alcanzar": round(m["min_alcanzar_consigna"], 0),
        "horas_grano_50": round(r.horas_grano_50, 2),
        "capa_max": round(r.capa_max, 2), "capa_min": round(r.capa_min, 2),
    }


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    niv = {n.codigo: n for n in niveles()}
    p0 = ParametrosSecador()
    filas, trazas = [], {}

    # 1) barrido: 10 perfiles x {C0, CT-}, arranque 00:00
    for cod_c in ("C0", "CT-"):
        for pf in PERFILES:
            r = correr(niv[cod_c].dias(), pf.sp_inicial_c, pf.sp_final_c, pf.caudal_frac, p=p0)
            filas.append(fila("barrido", pf, niv[cod_c], r, 0.0, p0))
            if cod_c == "C0" and pf.codigo in ("REF", "P1-C75"):
                trazas[f"{pf.codigo} · C0"] = r
    peor = max((f for f in filas if f["clima"] == "CT-"), key=lambda f: (f["horas_saturado"], -f["margen_min_c"]))
    pf_peor = next(p for p in PERFILES if p.codigo == peor["perfil"])

    # 2) caso más exigente con arranque a las 18:00 (fase alta en la madrugada fría)
    r = correr(niv["CT-"].dias(), pf_peor.sp_inicial_c, pf_peor.sp_final_c, pf_peor.caudal_frac, p=p0, t_inicio_h=18.0)
    filas.append(fila("mas_exigente", pf_peor, niv["CT-"], r, 18.0, p0))
    trazas[f"{pf_peor.codigo} · CT- · inicio 18:00 (más exigente)"] = r

    # 3) sensibilidades
    p_v = replace(p0, potencia_resistencia_kw=round(6.0 * 0.9 ** 2, 3))
    p_f = replace(p0, potencia_ventilador_kw=0.37)
    for pf in [p for p in PERFILES if p.codigo in ("REF", "P1-C75", pf_peor.codigo)]:
        for nom, pp in (("tension_-10%", p_v), ("ventilador_0.37kW", p_f)):
            for cod_c, t_ini in (("C0", 0.0), ("CT-", 18.0)):
                if nom == "ventilador_0.37kW" and cod_c == "CT-":
                    continue
                r = correr(niv[cod_c].dias(), pf.sp_inicial_c, pf.sp_final_c, pf.caudal_frac, p=pp, t_inicio_h=t_ini)
                filas.append(fila(nom, pf, niv[cod_c], r, t_ini, pp))
                if nom == "tension_-10%" and cod_c == "CT-" and pf.codigo == pf_peor.codigo:
                    trazas[f"{pf.codigo} · CT- · inicio 18:00 · tensión 10 % baja (4.86 kW)"] = r

    # 4) helada hipotética
    hel = helada_hipotetica()
    for pf in [p for p in PERFILES if p.codigo in ("REF", "P1-C75", "P1-C30")]:
        r = correr(hel.dias(), pf.sp_inicial_c, pf.sp_final_c, pf.caudal_frac, p=p0, t_max_h=400)
        filas.append(fila("helada_hipotetica", pf, hel, r, 0.0, p0))
        if pf.codigo == "REF":
            trazas["REF · helada hipotética (-4 °C)"] = r

    with open(os.path.join(OUT, "casos.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    # ---------- límites declarados ----------
    rho = densidad_aire(20.0)
    g100 = p0.masa_aire_kg_s(20.0) * CP_AIRE + p0.ua_plenum_kw_k
    lim = [
        ("Resistencia", "0 a 6.0 kW (3 × 2 kW a 220 V, Tecnirecambio; equivalente a Tempco 2 kW/240 V)",
         "Enclavamiento con ventilador; potencia integrada = la realmente aplicada; corte térmico a 90 °C que "
         "abre la resistencia (ya no recorta T)", "cotizaciones_bom.md; dinamica_termica.py"),
        ("Tensión", "220 V (alimentación de la finca, supuesto declarado); P ∝ V²",
         "Con 10 % de caída (198 V): 4.86 kW", "Supuesto; sensibilidad abajo"),
        ("Ventilador", "0 apagado; 30–100 % de 8 m³/min (0.1 m³/min/kg; González et al., 2010)",
         "Sistema ≈100 Pa a 480 m³/h; el CBT-80N (0.37 kW, curvas hasta ~1 800 Pa) lo cubre. Con variador, "
         "Q ∝ n solo si la curva del sistema es cuadrática pura; el lecho es casi lineal, así que % de "
         "frecuencia ≠ % de caudal (se declara)", "equipos_energia.md; cotizaciones_bom.md"),
        ("Plenum", f"τ ≈ {p0.capacidad_plenum_kj_k / g100:.0f} s con caudal 100 %",
         "La temperatura no salta: sube en ~2.5 min de 18 a 50 °C (con ventilador) y baja en horas sin él",
         "dinamica_termica.py"),
        ("Temperatura máxima alcanzable", "T_amb + P/(ṁ·cp + UA)",
         f"Caudal 100 %: T_amb + {p0.potencia_resistencia_kw / g100:.1f} °C; 75 %: T_amb + "
         f"{p0.potencia_resistencia_kw / (p0.masa_aire_kg_s(20, .75) * CP_AIRE + p0.ua_plenum_kw_k):.1f} °C; "
         f"30 %: T_amb + {p0.potencia_resistencia_kw / (p0.masa_aire_kg_s(20, .3) * CP_AIRE + p0.ua_plenum_kw_k):.0f} °C",
         "Balance del plenum (Ec. 5)"),
        ("Compuerta", "Cambia de sentido solo con posición confirmada (final de carrera 1B1/1B2)",
         "Tiempo máximo de maniobra 5 s (T_MOV_MAX); sin confirmación → FALLA 2. En la planta Python la "
         "inversión del aire es instantánea (simplificación declarada: 5 s frente a 6 h)", "codesys/SECUENCIA.st"),
    ]

    # ---------- resumen ----------
    def tabla(fs, cols):
        out = ["| " + " | ".join(c for c, _ in cols) + " |", "|" + "---|" * len(cols)]
        for f in fs:
            out.append("| " + " | ".join(str(f[k]) for _, k in cols) + " |")
        return out

    cols = [("Perfil", "perfil"), ("Clima", "clima"), ("Inicio", "hora_inicio"), ("t fin [h]", "t_obj_h"),
            ("kWh/kg", "kwh_kg"), ("Saturado [h]", "horas_saturado"), ("Racha sat. [h]", "racha_saturado_h"),
            ("Fuera de banda [h]", "horas_fuera_banda"), ("Déficit máx. [°C]", "deficit_max_c"),
            ("Margen mín. [°C]", "margen_min_c"), ("Duty medio [%]", "duty_medio_pct"),
            ("Alcanza consigna [min]", "min_alcanzar"),
            ("Grano > 50 °C [h]", "horas_grano_50")]
    L = ["# Límites de actuación", "",
         "Generado por `python/limites_actuacion.py`. Misma física y control que la campaña "
         "(`corrida_instrumentada.py`, verificada: mismo tiempo y energía que `simular_supervisada`). "
         "Saturado = la resistencia está encendida todo el minuto y aun así T queda > 1 °C por debajo de la "
         "consigna. Margen = T máxima alcanzable − consigna (negativo = consigna físicamente inalcanzable en ese "
         "momento). Las métricas de régimen excluyen los primeros 15 min y los 15 min posteriores a cada cambio de consigna (P2/P3); ese transitorio se reporta como «Alcanza consigna» = minutos hasta quedar a ±1 °C (el peor de los transitorios).", "",
         "## Límites declarados y comprobación", "",
         "| Elemento | Límite | Comprobación | Fuente |", "|---|---|---|---|"]
    L += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in lim]
    L += ["", f"Potencia requerida por la Ec. 5 a 50 °C (T_amb 14.3 °C, FS 1.1): "
          f"{potencia_requerida_kw(p0):.2f} kW; a 55 °C: "
          f"{potencia_requerida_kw(replace(p0, t_setpoint_c=55.0)):.2f} kW con FS (> 6 kW instalados; "
          f"{potencia_requerida_kw(replace(p0, t_setpoint_c=55.0)) / 1.1:.2f} kW nominales, sin FS).", "",
          "## 1. Barrido: 10 perfiles en clima nominal (C0) y frío (CT-, p5), arranque 00:00", ""]
    L += tabla([f for f in filas if f["caso"] == "barrido"], cols)
    L += ["", "## 2. Caso más exigente", "", f"Seleccionado del barrido en CT- por horas de saturación y, a igualdad, por el menor margen físico: "
          f"**{pf_peor.codigo}** ({pf_peor.nombre}). Se repite arrancando a las 18:00 para que la fase "
          "de consigna alta caiga en la madrugada.", ""]
    L += tabla([f for f in filas if f["caso"] == "mas_exigente"], cols)
    L += ["", "## 3. Sensibilidades (tensión 10 % baja; ventilador de 0.37 kW)", ""]
    L += tabla([f for f in filas if f["caso"] in ("tension_-10%", "ventilador_0.37kW")],
               [("Caso", "caso")] + cols)
    L += ["", "## 4. Helada hipotética (-4 °C; fuera del clima del sitio)", ""]
    L += tabla([f for f in filas if f["caso"] == "helada_hipotetica"], cols)
    L += ["", "Nota: con -4 °C la isoterma y la cinética trabajan fuera de su dominio en el aire de entrada "
          "frío; el caso solo sirve para mostrar el límite del calentador, no para predecir el secado.", ""]
    with open(os.path.join(OUT, "resumen.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))

    # ---------- figura ----------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(len(trazas), 1, figsize=(11, 3.0 * len(trazas)))
    for ax, (tit, r) in zip(axes, trazas.items()):
        tr = r.traza
        t = [x["t_h"] for x in tr]
        ax2 = ax.twinx()
        ax2.fill_between(t, [100 * x["duty"] for x in tr], color="#f3c27a", alpha=0.45, lw=0, label="Ciclo de trabajo")
        ax2.set_ylim(0, 105)
        ax2.set_ylabel("Resistencia [%]")
        ax.plot(t, [x["sp"] for x in tr], color="#555", ls="--", lw=1, label="Consigna (pedido)")
        ax.plot(t, [x["T_media"] for x in tr], color="#c0392b", lw=1.2, label="T obtenida (aplicado)")
        ax.plot(t, [x["T_max_alc"] for x in tr], color="#8e44ad", ls=":", lw=1.1, label="T máx. alcanzable")
        ax.plot(t, [x["T_amb"] for x in tr], color="#2c3e50", lw=0.9, alpha=0.7, label="T ambiente")
        sat = [x["saturado"] for x in tr]
        for i, sflag in enumerate(sat):
            if sflag:
                ax.axvspan(t[i] - 1 / 60, t[i], color="#e74c3c", alpha=0.25, lw=0)
        ax.set_zorder(ax2.get_zorder() + 1)
        ax.patch.set_visible(False)
        ax.set_ylim(min(-5, min(x["T_amb"] for x in tr) - 2), 80)
        ax.set_ylabel("°C")
        ax.set_title(tit, loc="left", fontsize=10)
        if ax is axes[0]:
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, fontsize=8, ncol=5, loc="upper right")
    axes[-1].set_xlabel("Tiempo de lote [h]   (franjas rojas = resistencia saturada sin alcanzar la consigna)")
    fig.suptitle("Lo pedido frente a lo físicamente aplicado", fontsize=11)
    fig.tight_layout()
    ruta = os.path.normpath(os.path.join(AQUI, "..", "figures", "limites_actuacion.png"))
    fig.savefig(ruta, dpi=140)
    print("Figura:", ruta)


if __name__ == "__main__":
    main()

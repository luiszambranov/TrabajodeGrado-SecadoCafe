"""
figuras_documento.py
====================

Figuras 1 y 3 del documento final, en escala de grises para que combinen con el
texto (fuente serif, símbolos de diagrama de flujo, sombras grises).

- Figura 1: arquitectura implementada y flujo de información (ISO/IEC 30141:
  percepción, red, procesamiento y aplicación).
- Figura 3: frontera de Pareto tiempo–energía de los perfiles supervisados, a
  partir de resultados/campana/resultados.csv (150 realizaciones pareadas).

Uso (desde python/):  python figuras_documento.py
Salida: ../figures/fig1_arquitectura.png y ../figures/fig3_pareto.png
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle

plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = ["Times New Roman", "Liberation Serif", "DejaVu Serif"]
plt.rcParams["mathtext.fontset"] = "stix"

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "..", "figures")

NEGRO, GRIS_OSC, GRIS, GRIS_CLARO, SOMBRA = "#111111", "#4d4d4d", "#bfbfbf", "#e6e6e6", "#9a9a9a"
DX, DY = 0.045, -0.045   # desplazamiento de la sombra [in]


# ----------------------------------------------------------------------------- símbolos
def _sombra_y_figura(ax, crear, fc="white", lw=1.0):
    s = crear(DX, DY)
    s.set(facecolor=SOMBRA, edgecolor="none", zorder=1)
    ax.add_patch(s)
    p = crear(0, 0)
    p.set(facecolor=fc, edgecolor=NEGRO, linewidth=lw, zorder=2)
    ax.add_patch(p)
    return p


def proceso(ax, x, y, w, h, titulo, lineas, predefinido=False, h_tit=0.24):
    """Proceso (rectángulo) o proceso predefinido (con barras laterales dobles)."""
    _sombra_y_figura(ax, lambda dx, dy: Rectangle((x + dx, y + dy), w, h))
    ax.add_patch(Rectangle((x, y + h - h_tit), w, h_tit, facecolor=GRIS_CLARO, edgecolor=NEGRO, lw=1.0, zorder=3))
    if predefinido:
        for xx in (x + 0.07, x + w - 0.07):
            ax.plot([xx, xx], [y, y + h], color=NEGRO, lw=1.0, zorder=4)
    ax.text(x + w / 2, y + h - h_tit / 2, titulo, ha="center", va="center", fontsize=9.6, weight="bold", zorder=5)
    paso = (h - h_tit - 0.08) / max(len(lineas), 1)
    for i, t in enumerate(lineas):
        ax.text(x + (0.15 if predefinido else 0.09), y + h - h_tit - 0.06 - paso * (i + 0.5), "• " + t,
                ha="left", va="center", fontsize=8.7, zorder=5)


def datos(ax, x, y, w, h, texto, sesgo=0.16):
    """Entrada de datos (paralelogramo)."""
    _sombra_y_figura(ax, lambda dx, dy: Polygon([(x + sesgo + dx, y + h + dy), (x + w + dx, y + h + dy),
                                                (x + w - sesgo + dx, y + dy), (x + dx, y + dy)]), fc=GRIS_CLARO)
    ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center", fontsize=7.8, zorder=5, linespacing=1.25)


def documento(ax, x, y, w, h, titulo, texto):
    """Documento (borde inferior ondulado)."""
    def forma(dx, dy):
        xs = np.linspace(x, x + w, 40)
        ys = y + 0.06 * np.sin((xs - x) / w * 2 * np.pi)
        pts = [(x + dx, y + h + dy), (x + w + dx, y + h + dy)] + [(a + dx, b + dy) for a, b in zip(xs[::-1], ys[::-1])]
        return Polygon(pts)
    _sombra_y_figura(ax, forma)
    ax.text(x + w / 2, y + h - 0.15, titulo, ha="center", va="center", fontsize=8.6, weight="bold", zorder=5)
    ax.text(x + w / 2, y + h / 2 - 0.08, texto, ha="center", va="center", fontsize=7.4, zorder=5, linespacing=1.25)


def pantalla(ax, x, y, w, h, titulo, lineas):
    """Visualización / pantalla (punta a la izquierda, lado derecho curvo)."""
    def forma(dx, dy):
        r = h / 2
        ang = np.linspace(np.pi / 2, -np.pi / 2, 30)
        arco = [(x + w - r * 0.45 + 0.45 * r * np.cos(a) + dx, y + r + r * np.sin(a) + dy) for a in ang]
        return Polygon([(x + 0.22 + dx, y + h + dy)] + arco + [(x + 0.22 + dx, y + dy), (x + dx, y + r + dy)])
    _sombra_y_figura(ax, forma)
    ax.text(x + w / 2 + 0.03, y + h - 0.16, titulo, ha="center", va="center", fontsize=8.6, weight="bold", zorder=5)
    for i, t in enumerate(lineas):
        ax.text(x + 0.27, y + h - 0.36 - 0.16 * i, "• " + t, ha="left", va="center", fontsize=7.4, zorder=5)


def terminal(ax, xc, yc, texto, w=1.0, h=0.22):
    """Terminal (rectángulo redondeado): protocolo de comunicación."""
    _sombra_y_figura(ax, lambda dx, dy: FancyBboxPatch((xc - w / 2 + dx, yc - h / 2 + dy), w, h,
                                                        boxstyle="round,pad=0,rounding_size=0.11"))
    ax.text(xc, yc, texto, ha="center", va="center", fontsize=7.8, weight="bold", zorder=5)


def flecha(ax, p0, p1, discontinua=False, doble=False):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="<|-|>" if doble else "-|>", mutation_scale=11,
                                 color=NEGRO, lw=1.1, linestyle=(0, (4, 2.5)) if discontinua else "-",
                                 shrinkA=0, shrinkB=0, zorder=6))


# ----------------------------------------------------------------------------- figura 1
def figura_arquitectura(ruta):
    W, H = 6.6, 4.55
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

    cx0, cw = 1.55, 2.75            # columna central
    rx0, rw = 4.72, 1.80            # columna derecha
    xa, xb = cx0 + 0.75, cx0 + 2.0  # flechas verticales
    hb = 0.86                       # alto de los procesos
    y_fs = 0.06                     # FluidSIM
    y_cd = y_fs + 0.80 + 0.66       # CODESYS
    y_py = y_cd + hb + 0.70         # Python
    y_pe = y_py + hb + 0.18         # perturbaciones

    datos(ax, cx0 - 0.15, y_pe, cw + 0.3, 0.38, "Perturbaciones: clima de Chinchiná (NASA POWER)\ny humedad inicial del lote")
    flecha(ax, (cx0 + cw / 2, y_pe), (cx0 + cw / 2, y_py + hb))

    proceso(ax, cx0, y_py, cw, hb, "Python · planta simulada",
            ["Lecho de 8 capas, cinética Roa–Cenicafé",
             "Resistencia de 6 kW y ventilador de caudal variable",
             "Servidor Modbus TCP (puerto 5020)"])
    documento(ax, rx0, y_py + 0.06, rw, 0.76, "Registro del lote", "CSV y gráfica del lote\ncompleto (histórico)")
    flecha(ax, (cx0 + cw, y_py + hb / 2), (rx0, y_py + hb / 2))

    ym = (y_cd + hb + y_py) / 2
    flecha(ax, (xa, y_py), (xa, y_cd + hb))
    flecha(ax, (xb, y_cd + hb), (xb, y_py), discontinua=True)
    terminal(ax, (xa + xb) / 2, ym, "Modbus TCP", w=0.92)
    ax.text(xa - 0.1, ym, "Temperatura, HR,\nhumedad del café,\nenergía, relojes,\nheartbeat",
            ha="right", va="center", fontsize=8.1, linespacing=1.15)
    ax.text(xb + 0.1, ym, "Consigna, resistencia,\nventilador, caudal,\nsentido del aire,\nnuevo lote",
            ha="left", va="center", fontsize=8.1, linespacing=1.15)

    proceso(ax, cx0, y_cd, cw, hb, "CODESYS V3.5 SP9 · PLC",
            ["PLC_PRG: consigna del perfil y watchdog",
             "SECUENCIA: máquina de estados",
             "Alarmas y fin de secado"], predefinido=True)
    pantalla(ax, rx0, y_cd + 0.03, rw, 0.80, "HMI · operador",
             ["Perfil y caudal del lote", "START, STOP, Nuevo lote", "Variables, tendencias, alarmas"])
    flecha(ax, (cx0 + cw, y_cd + hb / 2), (rx0, y_cd + hb / 2), doble=True)

    yo = (y_cd + y_fs + 0.80) / 2
    flecha(ax, (xa, y_cd), (xa, y_fs + 0.80), discontinua=True)
    flecha(ax, (xb, y_fs + 0.80), (xb, y_cd))
    terminal(ax, (xa + xb) / 2, yo, "OPC DA", w=0.80)
    ax.text(xa - 0.1, yo, "Bobinas de las\nválvulas 5/2,\nrelé K1, semáforo",
            ha="right", va="center", fontsize=8.1, linespacing=1.15)
    ax.text(xb + 0.1, yo, "Pulsadores y\nfinales de carrera",
            ha="left", va="center", fontsize=8.1, linespacing=1.15)

    proceso(ax, cx0, y_fs, cw, 0.80, "FluidSIM · actuación",
            ["Compuerta de inversión del aire (cilindro 1)",
             "Bandeja de carga y descarga (cilindro 2)",
             "Pulsadores y semáforo"])

    lx, ly = rx0 + 0.02, 0.12
    ax.add_patch(Rectangle((lx, ly), rw - 0.04, 0.64, facecolor="white", edgecolor=GRIS_OSC, lw=0.7, zorder=2))
    ax.text(lx + 0.08, ly + 0.52, "Convenciones", fontsize=7.8, weight="bold", va="center")
    flecha(ax, (lx + 0.08, ly + 0.33), (lx + 0.45, ly + 0.33))
    ax.text(lx + 0.52, ly + 0.33, "Mediciones y estados", fontsize=7.5, va="center")
    flecha(ax, (lx + 0.08, ly + 0.13), (lx + 0.45, ly + 0.13), discontinua=True)
    ax.text(lx + 0.52, ly + 0.13, "Órdenes y mandos", fontsize=7.5, va="center")

    capas = [(y_py, y_py + hb, "Percepción\n(planta)"), (y_cd + hb, y_py, "Red"),
             (y_cd, y_cd + hb, "Procesamiento\ny aplicación"), (y_fs + 0.80, y_cd, "Red"),
             (y_fs, y_fs + 0.80, "Percepción\n(actuación)")]
    for y0, y1, t in capas:
        ax.plot([1.08, 1.08], [y0 + 0.03, y1 - 0.03], color=GRIS_OSC, lw=0.8)
        ax.plot([1.08, 1.16], [y0 + 0.03, y0 + 0.03], color=GRIS_OSC, lw=0.8)
        ax.plot([1.08, 1.16], [y1 - 0.03, y1 - 0.03], color=GRIS_OSC, lw=0.8)
        ax.text(0.88, (y0 + y1) / 2, t, rotation=90, ha="center", va="center", fontsize=7.8, color=GRIS_OSC,
                style="italic", linespacing=1.1)

    fig.savefig(ruta, dpi=300)
    plt.close(fig)
    _recortar(ruta)


def _recortar(ruta, margen=12):
    """Quita el margen blanco sobrante alrededor del diagrama."""
    from PIL import Image, ImageOps
    im = Image.open(ruta).convert("RGB")
    x0, y0, x1, y1 = ImageOps.invert(im).getbbox()
    im.crop((max(x0 - margen, 0), max(y0 - margen, 0), min(x1 + margen, im.width), min(y1 + margen, im.height))).save(ruta)


# ----------------------------------------------------------------------------- figura 3
def figura_pareto(ruta):
    import analisis_montecarlo as am

    datos_c, _, sem = am.cargar(os.path.join(AQUI, "resultados", "campana"))
    pts = {}
    for e in ["REF"] + am.FACTORIALES:
        t = float(np.nanmean(am.vector(datos_c, e, "t_obj_h", sem)))
        en = float(np.nanmean(am.vector(datos_c, e, "kwh_por_kg_cps", sem)))
        ok = am.cumplimiento(datos_c, e, sem, am.LIM_CAPA_MIN_B) >= am.FRACCION_CUMPLE
        pts[e] = (t, en, ok)
    frontera = sorted(am.pareto([(c, t, en) for c, (t, en, ok) in pts.items() if ok]), key=lambda c: pts[c][0])

    fig, ax = plt.subplots(figsize=(4.7, 3.0))
    ax.plot([pts[c][0] for c in frontera], [pts[c][1] for c in frontera], "--", color=NEGRO, lw=1.1, zorder=2)
    desplaz = {"REF": (-6, 7, "right"), "P1-C75": (-4, -13, "right"), "P3-C75": (6, -11, "left"),
               "P1-C100": (6, 4, "left"), "P2-C100": (7, -2, "left"), "P2-C75": (7, 2, "left"),
               "P3-C100": (7, 2, "left"), "P1-C30": (-7, 5, "right"), "P2-C30": (-6, 7, "right"),
               "P3-C30": (-7, -8, "right")}
    for c, (t, en, ok) in pts.items():
        enfr = c in frontera
        ax.scatter(t, en, s=40 if enfr else 24, marker="s" if enfr else "o", zorder=3,
                   facecolors=(NEGRO if enfr else GRIS_OSC) if ok else "white",
                   edgecolors=NEGRO, linewidths=1.0)
        dx, dy, ha = desplaz[c]
        ax.annotate(c, (t, en), textcoords="offset points", xytext=(dx, dy), ha=ha, va="center",
                    fontsize=8.6 if enfr else 7.6, weight="bold" if enfr else "normal")
    # Compromiso REF -> P1-C75
    t0, e0, _ = pts["REF"]; t1, e1, _ = pts["P1-C75"]
    ax.annotate("", xy=(t1, e0), xytext=(t0, e0), arrowprops=dict(arrowstyle="-|>", color=GRIS_OSC, lw=0.9))
    ax.annotate("", xy=(t1, e1), xytext=(t1, e0), arrowprops=dict(arrowstyle="-|>", color=GRIS_OSC, lw=0.9))
    ax.text((t0 + t1) / 2, e0 - 0.03, f"+{t1 - t0:.1f} h".replace(".", ","), ha="center", va="top", fontsize=7.6,
            color=GRIS_OSC)
    ax.text(t1 + 0.8, (e0 + e1) / 2, f"−{100 * (e0 - e1) / e0:.1f} % energía".replace(".", ","), ha="left", va="center",
            fontsize=7.6, color=GRIS_OSC)

    ax.scatter([], [], s=40, marker="s", color=NEGRO, label="Frontera de Pareto (cumple el filtro)")
    ax.scatter([], [], s=24, color=GRIS_OSC, label="Cumple el filtro, dominado")
    ax.scatter([], [], s=24, facecolors="white", edgecolors=NEGRO, label="No cumple el filtro (caudal de 30 %)")
    ax.plot([], [], "--", color=NEGRO, lw=1.1, label="Compromiso tiempo–energía")
    ax.set_xlabel("Tiempo medio de secado hasta 11 % b.h. [h]", fontsize=8.6)
    ax.set_ylabel("Energía comprada [kWh/kg c.p.s.]", fontsize=8.6)
    ax.tick_params(labelsize=7.8)
    ax.set_xlim(25, 105); ax.set_ylim(0.9, 2.15)
    from matplotlib.ticker import FuncFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
    ax.grid(color=GRIS_CLARO, lw=0.6)
    ax.legend(fontsize=6.8, loc="upper right", frameon=True, edgecolor=GRIS, borderpad=0.4, labelspacing=0.3)
    fig.tight_layout()
    fig.savefig(ruta, dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(SALIDA, exist_ok=True)
    figura_arquitectura(os.path.join(SALIDA, "fig1_arquitectura.png"))
    figura_pareto(os.path.join(SALIDA, "fig3_pareto.png"))
    print("Figuras en", os.path.abspath(SALIDA))

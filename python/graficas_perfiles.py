"""
graficas_perfiles.py
=====================

Figuras de los perfiles térmicos (perfiles_termicos.py) para el documento:
cómo evolucionan la temperatura del aire (T_process y su setpoint) y la
humedad del café en cada perfil, y en qué instante cambian los perfiles no
constantes (P2 y P3, cuando el promedio del lote llega a 30 % b.h.).

Condiciones: día climático nominal de Chinchiná y M0 = 55 % b.h. (caso
determinista, para leer la forma de cada perfil; la variabilidad está en la
campaña Monte Carlo).

Uso (desde python/):  python graficas_perfiles.py   -> ../figures/perfil_*.png
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import generador_ambiente as amb
from control_supervisado import simular_supervisada
from perfiles_termicos import CAUDALES, HUMEDAD_CAMBIO_BH_PCT, PERFILES_POR_CODIGO, TERMICOS

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures")
# Caudal es ordinal (30 < 75 < 100 %): una sola tonalidad de claro a oscuro.
COLOR_CAUDAL = {"C30": "#5598e7", "C75": "#256abf", "C100": "#0d366b"}
TINTA, TINTA_2, GRIS = "#1f1f1e", "#5f5e58", "#9a998f"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRIS, "axes.labelcolor": TINTA,
                     "xtick.color": TINTA_2, "ytick.color": TINTA_2, "axes.spines.top": False,
                     "axes.spines.right": False})


def correr(codigo):
    r = simular_supervisada([amb.condiciones_nominales()], PERFILES_POR_CODIGO[codigo].parametros_control(),
                            t_max_h=200.0, guardar_traza=True)
    tr = np.array(r.traza)
    # columnas: t, T_amb, T_process, RH_proc, M_prom, M_min, M_max, invertido, setpoint, caudal
    cambio = None
    idx = np.where(tr[:, 4] <= HUMEDAD_CAMBIO_BH_PCT)[0]
    if len(idx):
        cambio = float(tr[idx[0], 0])
    return tr, r, cambio


def promedio_horario(t, y):
    """Promedio por hora de T_process (quita el rizado del todo/nada para leer la tendencia)."""
    h = np.floor(t).astype(int)
    tt = np.array([t[h == k].mean() for k in np.unique(h)])
    yy = np.array([y[h == k].mean() for k in np.unique(h)])
    return tt, yy


def figura_perfil(tc, descripcion, sp0, sp1):
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.5, 7.2), sharex=True, gridspec_kw={"height_ratios": [1, 1.2]})
    constante = sp0 == sp1
    for i, (cc, cf) in enumerate(CAUDALES):
        tr, r, cambio = correr(f"{tc}-{cc}")
        col = COLOR_CAUDAL[cc]
        th, Th = promedio_horario(tr[:, 0], tr[:, 2])
        a1.plot(th, Th, color=col, lw=2, label=f"Caudal {int(cf * 100)} %")
        a1.step(tr[:, 0], tr[:, 8], where="post", color=col, lw=1, ls="--", alpha=0.8)
        a2.plot(tr[:, 0], tr[:, 4], color=col, lw=2)
        a2.fill_between(tr[:, 0], tr[:, 5], tr[:, 6], color=col, alpha=0.12, lw=0)
        a2.annotate(f"{r.t_obj_h:.0f} h", (r.t_obj_h, 11.0), xytext=(0, -16), textcoords="offset points",
                    ha="center", fontsize=8.5, color=TINTA_2)
        if not constante and cambio is not None:
            for ax in (a1, a2):
                ax.axvline(cambio, color=col, lw=1, ls=":")
            a1.text(cambio + 0.8, 46 - 3.2 * i, f"cambio con caudal {int(cf * 100)} %: {cambio:.1f} h",
                    fontsize=8.5, color=col, fontweight="bold")
    a1.axhline(50, color=GRIS, lw=1, ls="-.")
    a1.text(0.99, 50.6, "Límite del grano 50 °C (Cenicafé)", fontsize=8.5, color=TINTA_2,
            transform=a1.get_yaxis_transform(), ha="right")
    a1.set_ylabel("T del aire de secado [°C]")
    a1.set_ylim(15, 62)
    fig.suptitle(f"Perfil {tc}: {descripcion}", x=0.07, ha="left", fontsize=12.5, color=TINTA, fontweight="bold")
    a1.set_title("Línea continua: T_process (promedio horario) · discontinua: setpoint", loc="left",
                 fontsize=8.5, color=TINTA_2)
    a1.legend(frameon=False, loc="lower right", fontsize=9)
    a1.grid(alpha=0.25)

    a2.axhline(HUMEDAD_CAMBIO_BH_PCT, color=GRIS, lw=1, ls="--")
    a2.text(1, HUMEDAD_CAMBIO_BH_PCT + 0.8, "30 % b.h.: punto de cambio de los perfiles escalonados", fontsize=8.5,
            color=TINTA_2)
    a2.axhline(11, color=GRIS, lw=1, ls="-.")
    a2.text(1, 11.8, "Objetivo 11 % b.h.", fontsize=8.5, color=TINTA_2)
    a2.set_ylabel("Humedad del café [% b.h.]")
    a2.set_xlabel("Tiempo de secado [h]")
    a2.set_ylim(4, 57)
    a2.text(0, -0.2, "Banda sombreada: rango entre la capa más seca y la más húmeda del lecho. "
                     "Día nominal de Chinchiná, M0 = 55 % b.h.", transform=a2.transAxes, fontsize=8, color=TINTA_2)
    a2.grid(alpha=0.25)
    fig.tight_layout()
    ruta = os.path.join(SALIDA, f"perfil_{tc}.png")
    fig.savefig(ruta, dpi=170)
    plt.close(fig)
    return ruta


def figura_ref():
    tr, r, _ = correr("REF")
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(9.5, 6.4), sharex=True)
    th, Th = promedio_horario(tr[:, 0], tr[:, 2])
    col = COLOR_CAUDAL["C100"]
    a1.plot(th, Th, color=col, lw=2, label="T_process (promedio horario)")
    a1.step(tr[:, 0], tr[:, 8], where="post", color=col, lw=1, ls="--", label="Setpoint 50 °C")
    a1.plot(tr[:, 0], tr[:, 1], color=GRIS, lw=1.2, label="T ambiente")
    a1.set_ylabel("T [°C]")
    a1.set_ylim(10, 60)
    a1.legend(frameon=False, loc="lower right", fontsize=9)
    a1.set_title("Referencia REF: 50 °C constante, caudal 100 % (práctica de Cenicafé)", loc="left",
                 fontsize=12, color=TINTA, fontweight="bold")
    a1.grid(alpha=0.25)
    a2.plot(tr[:, 0], tr[:, 4], color=col, lw=2, label="Promedio del lote")
    a2.fill_between(tr[:, 0], tr[:, 5], tr[:, 6], color=col, alpha=0.15, lw=0, label="Capa más seca – más húmeda")
    inv = tr[:, 7] > 0.5
    ini = list(tr[1:, 0][np.diff(inv.astype(int)) == 1])
    fin = list(tr[1:, 0][np.diff(inv.astype(int)) == -1])
    if len(fin) < len(ini):
        fin.append(tr[-1, 0])
    for t0, t1 in zip(ini, fin):
        a2.axvspan(t0, t1, color=GRIS, alpha=0.12, lw=0)
    a2.axhline(11, color=GRIS, lw=1, ls="-.")
    a2.set_ylabel("Humedad del café [% b.h.]")
    a2.set_xlabel("Tiempo de secado [h]  (franjas grises: aire invertido)")
    a2.legend(frameon=False, loc="upper right", fontsize=9)
    a2.grid(alpha=0.25)
    fig.tight_layout()
    ruta = os.path.join(SALIDA, "perfil_REF.png")
    fig.savefig(ruta, dpi=170)
    plt.close(fig)
    return ruta


def figura_resumen():
    """Setpoint de los 4 perfiles en función de la humedad del café (caudal 100 %)."""
    fig, ax = plt.subplots(figsize=(9, 4.8))
    estilos = {"REF": ("#1f1f1e", "-"), "P1": ("#2a78d6", "-"), "P2": ("#eb6834", "-"), "P3": ("#1baf7a", "-")}
    m = np.linspace(55, 11, 400)
    for cod, desc, s0, s1 in [("REF", "50 °C constante (Cenicafé)", 50, 50)] + [(t, d, a, b) for t, d, a, b in TERMICOS]:
        sp = np.where(m > HUMEDAD_CAMBIO_BH_PCT, s0, s1)
        col, ls = estilos[cod]
        ax.plot(m, sp + (0.25 if cod == "REF" else 0), color=col, lw=2.2, ls=ls, label=f"{cod}: {desc}")
    ax.axvline(HUMEDAD_CAMBIO_BH_PCT, color=GRIS, lw=1, ls=":")
    ax.text(HUMEDAD_CAMBIO_BH_PCT - 0.5, 52, "cambio al 30 % b.h.", fontsize=9, color=TINTA_2, ha="left")
    ax.axhline(50, color=GRIS, lw=1, ls="-.")
    ax.invert_xaxis()
    ax.set_xlabel("Humedad promedio del café [% b.h.]  (el secado avanza hacia la derecha)")
    ax.set_ylabel("Setpoint de T_process [°C]")
    ax.set_ylim(30, 66)
    ax.set_title("Perfiles térmicos evaluados", loc="left", fontsize=12, color=TINTA, fontweight="bold")
    ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=2)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    ruta = os.path.join(SALIDA, "perfiles_resumen.png")
    fig.savefig(ruta, dpi=170)
    plt.close(fig)
    return ruta


if __name__ == "__main__":
    os.makedirs(SALIDA, exist_ok=True)
    rutas = [figura_resumen(), figura_ref()] + [figura_perfil(tc, d, s0, s1) for tc, d, s0, s1 in TERMICOS]
    for r in rutas:
        print("Figura:", os.path.normpath(r))

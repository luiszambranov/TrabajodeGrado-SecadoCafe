"""
grafica_lote.py
================

Gráfica del lote completo a partir del CSV que escribe ``modbus_server.py --log-csv``.

Por qué existe: la tendencia de la HMI de CODESYS V3.5 SP9 (Trend Recording) muestra
una ventana que se desplaza y en este proyecto no se logró que conservara el lote
completo desde t = 0. El CSV del servidor sí
registra cada ciclo (1 s real = 0,15 h de modelo con factor 540), con lo que el PLC
envió y lo que la planta aplicó, así que la historia completa del lote se reconstruye
aquí. ``modbus_server.py`` la genera solo, sin opciones:
  - al cumplirse el criterio de fin de cada lote (unos 8 ciclos después, para incluir la
    ventilación final) → ``<csv>_loteN.png``, sin cerrar el servidor;
  - al cerrarse (Ctrl+C), si el último lote no había terminado.
Sin ``--log-csv`` el CSV va a ``resultados/lotes/servidor_<fecha>_<hora>.csv``.
También se puede correr a mano:

    python grafica_lote.py resultados/verificacion/V1001_P1C75.csv
    python grafica_lote.py lote.csv --todo          # todo el archivo, no solo el último lote
    python grafica_lote.py lote.csv --salida figura.png

Paneles (eje x: tiempo del lote en horas de modelo):
  1. Temperatura del aire de proceso, consigna aplicada y temperatura ambiente
     (ciclo día/noche), con el estado físico de la planta sombreado.
  2. Humedad del café: promedio, capa más húmeda y capa más seca, con el umbral de
     cambio de consigna (30 % b.h.) y el criterio de fin (11 % promedio, 12 % capa).
  3. Actuación: potencia de la resistencia y caudal de aire.
Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import argparse
import os

import pandas as pd

ESTADOS = {  # estado_planta del servidor (planta_secado.py)
    0: ("Reposo", "#e5e7e9"),
    1: ("Secando", "#fdebd0"),
    2: ("Ventilando", "#d6eaf8"),
    3: ("Post-ventilación", "#d1f2eb"),
    4: ("Falla de comunicación", "#f5b7b1"),
}


def ultimo_lote(d: pd.DataFrame) -> pd.DataFrame:
    """Desde el último «Nuevo lote» (reinicio de t_lote_h) hasta el final del archivo."""
    reinicios = d.index[d.t_lote_h.diff() < 0]
    if len(reinicios):
        d = d.loc[reinicios[-1]:]
    return d.reset_index(drop=True)


def describir_estrategia(d: pd.DataFrame) -> str:
    activo = d[(d.fan_cmd_rx == 1) & (d.setpoint_rx > 0)]
    if activo.empty:
        return "sin secado activo"
    sp = activo.setpoint_rx.astype(int)
    sp_ini, sp_fin = sp.iloc[0], sp.iloc[-1]
    caudal = int(activo.fan_speed_rx.mode().iloc[0])
    consigna = f"{sp_ini} °C constante" if sp_ini == sp_fin else f"{sp_ini} → {sp_fin} °C al 30 % b.h."
    return f"consigna {consigna}, caudal {caudal} %"


def graficar(ruta_csv: str, salida: str | None = None, todo: bool = False) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    d = pd.read_csv(ruta_csv)
    if not todo:
        d = ultimo_lote(d)
    if len(d) < 3:
        raise SystemExit("El CSV tiene muy pocas filas para graficar.")
    x = d.t_planta_h - d.t_planta_h.iloc[0] if todo else d.t_lote_h

    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(11, 8.6), sharex=True,
                                     gridspec_kw={"height_ratios": [3, 3, 1.6]})

    # sombreado por estado físico de la planta
    grupos = (d.estado_planta != d.estado_planta.shift()).cumsum()
    vistos = set()
    for _, g in d.groupby(grupos):
        e = int(g.estado_planta.iloc[0])
        nombre, color = ESTADOS.get(e, (f"Estado {e}", "#ffffff"))
        x0, x1 = x.loc[g.index[0]], x.loc[min(g.index[-1] + 1, len(d) - 1)]
        for ax in (a1, a2, a3):
            ax.axvspan(x0, x1, color=color, alpha=0.6, lw=0)
        vistos.add(e)

    # 1. temperaturas
    a1.plot(x, d.T_process_c, color="#c0392b", lw=1.8, label="T aire de proceso")
    sp = d.setpoint_rx.where(d.fan_cmd_rx == 1)
    a1.step(x, sp, where="post", color="#1f2d3d", lw=1.2, ls="--", label="Consigna enviada por CODESYS")
    a1.plot(x, d.T_ambiente_c, color="#2e86c1", lw=1.2, label="T ambiente (día/noche)")
    a1.axhline(50, color="#7b241c", lw=0.8, ls=":")
    a1.text(x.iloc[-1], 50.4, "límite 50 °C ", ha="right", va="bottom", fontsize=8, color="#7b241c")
    a1.set_ylabel("Temperatura [°C]")
    a1.set_ylim(0, 60)
    a1.legend(loc="upper right", fontsize=8, ncol=3)

    # 2. humedad
    a2.plot(x, d.M_prom_bh, color="#6e2c00", lw=2.0, label="Promedio del lecho")
    a2.plot(x, d.M_max_bh, color="#af601a", lw=1.0, label="Capa más húmeda")
    a2.plot(x, d.M_min_bh, color="#d4ac0d", lw=1.0, label="Capa más seca")
    a2.axhline(30, color="#555", lw=0.8, ls=":")
    a2.text(x.iloc[0], 30.6, " 30 % b.h.: cambio de consigna (P2/P3)", fontsize=8, color="#555")
    a2.axhline(11, color="#1e8449", lw=0.9, ls="--")
    a2.text(x.iloc[0], 11.6, " 11 % b.h.: criterio de fin (promedio)", fontsize=8, color="#1e8449")
    fin = d[(d.M_prom_bh <= 11.0) & (d.M_max_bh <= 12.0) & (d.t_secado_h > 0)]
    if not fin.empty:
        xf = x.loc[fin.index[0]]
        for ax in (a1, a2, a3):
            ax.axvline(xf, color="#1e8449", lw=1.2)
        a2.annotate(f"Fin de secado\n(lote {xf:.1f} h)", (xf, 11), xytext=(-75, 40), textcoords="offset points",
                    fontsize=8, color="#1e8449", arrowprops=dict(arrowstyle="->", color="#1e8449"))
    cambio = d.index[(d.setpoint_rx.diff() != 0) & (d.fan_cmd_rx == 1) & (d.setpoint_rx.shift() > 0)]
    for i in cambio:
        for ax in (a1, a2):
            ax.axvline(x.loc[i], color="#1f2d3d", lw=0.9, ls="-.")
        a1.annotate(f"Cambio de consigna\n{x.loc[i]:.1f} h", (x.loc[i], d.setpoint_rx.loc[i]), xytext=(6, -32),
                    textcoords="offset points", fontsize=8)
    inv = d.index[(d.flujo_invertido_aplicado.diff().fillna(0) != 0)]
    if len(inv):
        a2.plot(x.loc[inv], [3.0] * len(inv), "^", color="#1f2d3d", ms=5, label="Inversión del flujo de aire")
    a2.set_ylabel("Humedad [% b.h.]")
    a2.set_ylim(0, 60)
    a2.legend(loc="upper right", fontsize=8, ncol=3)

    # 3. actuación
    a3.plot(x, d.potencia_res_kw, color="#e67e22", lw=1.0, label="Potencia resistencia [kW]")
    a3.plot(x, d.caudal_m3_min, color="#2471a3", lw=1.2, label="Caudal [m³/min]")
    a3.set_ylabel("kW · m³/min")
    a3.set_ylim(0, 9)
    a3.set_xlabel("Tiempo de planta desde el inicio del archivo [h de modelo]" if todo else "Tiempo del lote [h de modelo]")
    a3.legend(loc="upper right", fontsize=8, ncol=2)

    for ax in (a1, a2, a3):
        ax.grid(alpha=0.3)
        ax.set_xlim(x.iloc[0], x.iloc[-1])
    handles = [Patch(color=ESTADOS[e][1], label=ESTADOS[e][0]) for e in sorted(vistos) if e in ESTADOS]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), fontsize=8, frameon=False)

    u = d.iloc[(fin.index[0] if not fin.empty else len(d) - 1)]
    resumen = (f"Tiempo de secado efectivo {u.t_secado_h:.1f} h · lote {u.t_lote_h:.1f} h · parado {u.t_parado_h:.1f} h · "
               f"energía {u.energia_kwh:.1f} kWh · humedad final {u.M_prom_bh:.1f} % (capas {u.M_min_bh:.1f}–{u.M_max_bh:.1f} %)")
    fig.suptitle(f"Lote completo supervisado por CODESYS: {describir_estrategia(d)}\n{resumen}", fontsize=10)
    fig.tight_layout(rect=(0, 0.03, 1, 1))

    if salida is None:
        salida = os.path.splitext(ruta_csv)[0] + "_lote.png"
    carpeta = os.path.dirname(salida)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    fig.savefig(salida, dpi=140)
    plt.close(fig)
    return salida


def main() -> None:
    ap = argparse.ArgumentParser(description="Gráfica del lote completo desde el CSV del servidor Modbus.")
    ap.add_argument("csv")
    ap.add_argument("--salida", default=None, help="PNG de salida (por defecto <csv>_lote.png)")
    ap.add_argument("--todo", action="store_true", help="Graficar todo el archivo, no solo el último lote")
    a = ap.parse_args()
    print("Figura:", graficar(a.csv, a.salida, a.todo))


if __name__ == "__main__":
    main()

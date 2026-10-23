"""
graficas_ensayos.py
====================

Figuras y tabla resumen de los ensayos de falla F1-F5 a
partir de los CSV que guarda ``modbus_server.py --log-csv`` durante los
ensayos con CODESYS y FluidSIM reales.

    F1  CODESYS detenido (Debug > Stop) y recuperación   -> F1_codesys.csv
    F2  FluidSIM detenido y recuperación                  -> F2_fluidsim.csv
    F3  STOP desde la HMI                                 -> F3_Stop.csv
    F5  Python detenido (el CSV termina; evidencia en la HMI: F5_hmi_python_caido.png)
                                                          -> F5_python.csv
    F4 (recuperación) queda dentro de F1 y F2.

F1_codesys.csv contiene al inicio una corrida de prueba (16:13-16:21, modo
sin FluidSIM); el ensayo empieza a las 16:49:55 y solo se usa esa parte.

Uso:  python graficas_ensayos.py
Salidas: ../figures/ensayos_fallos_F1_F2_F3.png y resultados/ensayos/resumen_ensayos.md
Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import os

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(AQUI, "resultados", "ensayos")

ENSAYOS = [
    ("F1", "CODESYS detenido (Debug > Stop) y recuperación", "F1_codesys.csv", "2026-10-21T16:49:55"),
    ("F2", "FluidSIM detenido y recuperación", "F2_fluidsim.csv", None),
    ("F3", "STOP desde la HMI", "F3_Stop.csv", None),
    ("F5", "Python detenido", "F5_python.csv", None),
]


def cargar(archivo: str, desde: str | None) -> pd.DataFrame:
    d = pd.read_csv(os.path.join(DIR, archivo))
    if desde:
        d = d[d.reloj_iso >= desde].reset_index(drop=True)
    return d


def intervalos(mask: pd.Series, t: pd.Series):
    """Intervalos [t_ini, t_fin] donde mask es True."""
    out, ini = [], None
    for m, tt in zip(mask, t):
        if m and ini is None:
            ini = tt
        if not m and ini is not None:
            out.append((ini, tt))
            ini = None
    if ini is not None:
        out.append((ini, t.iloc[-1]))
    return out


def corte_resistencia(d: pd.DataFrame, i0: int, i1: int) -> str:
    """Segundos de reloj desde el inicio del evento hasta la primera fila con la
    resistencia en 0 (resolución: 1 ciclo del servidor = 1 s)."""
    z = d.loc[i0:i1][d.loc[i0:i1].potencia_res_kw <= 1e-6]
    if not len(z):
        return "no"
    return f"{z.iloc[0].reloj_s - d.loc[i0].reloj_s:.0f}"


def eventos(cod: str, d: pd.DataFrame) -> list[dict]:
    """Cada interrupción: cuándo empezó, cuánto duró y qué pasó con la física."""
    if cod == "F1":
        mask = d.comm_lost == 1
    elif cod == "F2":
        mask = d.fluidsim_estado == 3
    elif cod == "F3":
        # STOP: transición de SECANDO a REPOSO/VENTILANDO con comunicación sana
        mask = (d.estado_planta != 1) & (d.comm_lost == 0) & (d.fluidsim_estado != 3) & (d.t_secado_h > 0)
    else:
        return []
    filas = []
    idx = d.index[mask & ~mask.shift(fill_value=False)]
    for i0 in idx:
        fin = d.index[(d.index > i0) & ~mask]
        i1 = (fin[0] - 1) if len(fin) else d.index[-1]
        pre = d.loc[max(i0 - 1, 0)]
        a, b = d.loc[i0], d.loc[i1]
        # reanudación: primera fila SECANDO después del evento
        rea = d[(d.index > i1) & (d.estado_planta == 1)]
        r = rea.iloc[0] if len(rea) else None
        filas.append({
            "hora": a.reloj_iso[11:19],
            "duracion_reloj_s": round(b.reloj_s - pre.reloj_s, 1),
            "t_planta_h": f"{pre.t_planta_h:.2f} → {b.t_planta_h:.2f}",
            "T_proc": f"{pre.T_process_c:.1f} → {b.T_process_c:.1f}",
            "T_amb": f"{b.T_ambiente_c:.1f}",
            "corte_res_s": corte_resistencia(d, i0, i1),
            "M": f"{pre.M_prom_bh:.2f} → {b.M_prom_bh:.2f}",
            "E": f"{pre.energia_kwh:.2f} → {b.energia_kwh:.2f}",
            "t_secado": f"{pre.t_secado_h:.2f} → {b.t_secado_h:.2f}",
            "t_parado": f"{pre.t_parado_h:.2f} → {b.t_parado_h:.2f}",
            "reanuda": (f"{r.reloj_iso[11:19]} (E {r.energia_kwh:.2f} kWh, M {r.M_prom_bh:.2f} %)"
                        if r is not None else "fin del registro"),
        })
    return filas


def main() -> None:
    datos = {cod: cargar(arch, desde) for cod, _, arch, desde in ENSAYOS}

    # ---------- tabla resumen ----------
    lineas = ["# Ensayos de falla F1–F5", "",
              "Generado por `python/graficas_ensayos.py` a partir de los CSV de "
              "`modbus_server.py --log-csv`, con Python + CODESYS + FluidSIM reales "
              "(factor 540, inicio 08:00, perfil REF, caudal 100 %). F4 (recuperación) está "
              "dentro de F1 y F2.", ""]
    for cod, nombre, arch, _ in ENSAYOS:
        d = datos[cod]
        lineas += [f"## {cod}. {nombre}", "",
                   f"Archivo `{arch}` ({len(d)} filas, {d.reloj_iso.iloc[0][11:19]}–{d.reloj_iso.iloc[-1][11:19]}).", ""]
        ev = eventos(cod, d)
        if ev:
            lineas += ["| Hora | Duración real [s] | Tiempo de planta [h] | T proceso [°C] | T amb. al final [°C] | "
                       "Resistencia en 0 a los [s] | Humedad [% b.h.] | Energía [kWh] | t secado [h] | "
                       "t parado [h] | Reanuda |",
                       "|---|---|---|---|---|---|---|---|---|---|---|"]
            for e in ev:
                lineas.append("| " + " | ".join(str(v) for v in e.values()) + " |")
            lineas.append("")
        if cod == "F3":
            lineas += ["Nota: al inicio de F3 (≈4.7 h de modelo) la máquina ventiló sin calentar porque CODESYS "
                       "seguía en PARO del ensayo anterior y Python se reinició (su reloj volvió a 0 y la "
                       "post-ventilación no terminaba). La secuencia final de `codesys/SECUENCIA.st` lo evita; "
                       "no afecta los cuatro STOP evaluados.", ""]
        if cod == "F5":
            lineas += ["El CSV termina con la planta en SECADO normal: al cerrar Python no hay quién registre "
                       "(si Python termina, la planta deja de calcular). La respuesta de "
                       "CODESYS está en `F5_hmi_python_caido.png`: «Comunicación Python: ERROR» y semáforo rojo "
                       "(FALLA 1) por heartbeat congelado.", ""]
    lineas += ["## Lectura", "",
               "- F1: a los ~5 s sin comandos (`edad_comandos_s` > 5) Python aplica su política local: "
               "resistencia en 0, post-ventilación y reposo. El reloj de la planta sigue y T proceso sigue "
               "a T ambiente (ciclo día/noche). Al volver CODESYS, el lote continúa con la misma energía, "
               "humedad y tiempo de secado (F4).",
               "- F2: FluidSIM detenido → `fluidsim_estado` = 3 y resistencia en 0 en ~1 s (FALLA 5, no "
               "emergencia). Al volver FluidSIM: START reconoce, los cilindros se resincronizan y START reanuda "
               "el lote (F4); la siguiente inversión del aire ocurre a las 6 h de secado efectivo.",
               "- F3: cada STOP apaga la resistencia, ventila un ciclo y deja la máquina en PARO; "
               "`t_secado_h` no avanza en la parada y `t_parado_h` sí.",
               "- F5: CODESYS detecta la caída de Python por el heartbeat y pasa a FALLA 1.", "",
               "Limitaciones: es una función de software demostrada, no una certificación de seguridad "
               "funcional. F1 se hizo con *Debug > Stop* (la aplicación conserva su estado); un reinicio "
               "completo del runtime devolvería CODESYS a REPOSO."]
    with open(os.path.join(DIR, "resumen_ensayos.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    print("\n".join(lineas))

    # ---------- figura ----------
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(11, 10))
    for ax, (cod, nombre, _, _) in zip(axes, ENSAYOS[:3]):
        d = datos[cod]
        t = d.t_planta_h
        # sombreado por condición
        for a, b in intervalos(d.comm_lost == 1, t):
            ax.axvspan(a, b, color="#f6c4c4", lw=0, label="_")
        for a, b in intervalos(d.fluidsim_estado == 3, t):
            ax.axvspan(a, b, color="#f9d9a8", lw=0)
        for a, b in intervalos((d.plant_mode == 1) & (d.comm_lost == 0) & (d.fluidsim_estado != 3), t):
            ax.axvspan(a, b, color="#e4e4e4", lw=0)
        ax.plot(t, d.T_process_c, color="#c0392b", lw=1.3, label="T proceso (plenum)")
        ax.plot(t, d.T_ambiente_c, color="#2c3e50", ls="--", lw=1.1, label="T ambiente")
        ax.set_ylim(10, 60)
        ax.set_ylabel("Temperatura [°C]")
        ax2 = ax.twinx()
        ax2.plot(t, d.M_prom_bh, color="#27ae60", lw=1.2, label="Humedad promedio")
        ax2.set_ylabel("Humedad [% b.h.]", color="#27ae60")
        ax2.tick_params(axis="y", colors="#27ae60")
        ax.set_title(f"{cod}: {nombre}", fontsize=10, loc="left")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc="lower left", fontsize=8, ncol=3)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color="#f6c4c4", label="Sin comunicación con CODESYS (política local de Python)"),
                        Patch(color="#f9d9a8", label="Enlace FluidSIM caído (FALLA 5)"),
                        Patch(color="#e4e4e4", label="HOLD: PARO / FALLA / esperando START")],
               loc="lower center", ncol=3, fontsize=8, frameon=False)
    axes[-1].set_xlabel("Tiempo de planta [h de modelo]")
    fig.suptitle("Ensayos de falla con Python + CODESYS + FluidSIM: la física sigue y el lote se recupera",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    ruta = os.path.normpath(os.path.join(AQUI, "..", "figures", "ensayos_fallos_F1_F2_F3.png"))
    fig.savefig(ruta, dpi=150)
    print(f"\nFigura: {ruta}")


if __name__ == "__main__":
    main()

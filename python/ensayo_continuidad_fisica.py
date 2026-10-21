"""
ensayo_continuidad_fisica.py
=============================

Ensayo de continuidad física de la planta (guía de cierre, R4, 21 oct 2026):
la física NO se pausa con STOP/HOLD, fin de secado ni pérdida de
comunicación. Se maneja ModeloSecadoPlant directamente (sin Modbus ni
CODESYS) con una secuencia de comandos que imita a PLC_PRG/SECUENCIA, con
la cámara caliente y T_proceso distinta de T_ambiente al momento de cada
evento:

    REPOSO -> SECADO -> PARO (HOLD) -> SECADO -> ENFRIAMIENTO (ventilador
    sin resistencia) -> SECADO -> COMUNICACIÓN PERDIDA -> RECUPERACIÓN

Salidas: resultados/ensayos/continuidad_fisica.csv (una fila por ciclo,
mismas columnas que modbus_server.py --log-csv) y
../figures/ensayo_continuidad_fisica.png.

IMPORTANTE: es la comprobación del lado Python con comandos emulados. Los
ensayos F1-F5 con CODESYS y FluidSIM reales se hacen con
``python modbus_server.py --log-csv ...`` y son evidencia aparte.

Uso:  python ensayo_continuidad_fisica.py
Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import csv
import os

from modbus_server import PLANT_MODE_HOLD, PLANT_MODE_RUN, PlantInputs
from planta_secado import ESTADOS_TXT, ModeloSecadoPlant, ParametrosModeloSecadoPlant

FACTOR = 540.0          # mismo factor de la demo con la HMI (0.15 h de modelo por segundo)
PERIODO_S = 1.0
HORA_INICIO = 8.0       # el lote arranca a las 08:00

# (etiqueta, segundos de reloj, heater_permiso, fan, plant_mode, comm_lost)
SECUENCIA = [
    ("REPOSO", 4, 0, 0, PLANT_MODE_HOLD, False),
    ("SECADO", 40, 1, 1, PLANT_MODE_RUN, False),
    ("PARO", 20, 0, 0, PLANT_MODE_HOLD, False),
    ("SECADO", 13, 1, 1, PLANT_MODE_RUN, False),
    ("ENFRIAMIENTO", 5, 0, 1, PLANT_MODE_RUN, False),
    ("SECADO", 8, 1, 1, PLANT_MODE_RUN, False),
    ("COMM PERDIDA", 25, 1, 1, PLANT_MODE_RUN, True),
    ("RECUPERACION", 10, 1, 1, PLANT_MODE_RUN, False),
]


def main() -> None:
    aqui = os.path.dirname(os.path.abspath(__file__))
    plant = ModeloSecadoPlant(ParametrosModeloSecadoPlant(factor_aceleracion=FACTOR, hora_inicio_h=HORA_INICIO),
                              periodo_s=PERIODO_S)
    filas = []
    for etiqueta, segundos, heater, fan, modo, comm_lost in SECUENCIA:
        for _ in range(int(segundos / PERIODO_S)):
            # Con comunicación perdida el servidor ya no recibe comandos: el
            # bucle de modbus_server pasa heater/fan en 0 y comm_lost=True.
            inp = PlantInputs(heater_cmd=0 if comm_lost else heater, fan_cmd=0 if comm_lost else fan,
                              plant_mode=modo, comm_lost=comm_lost, fan_speed_pct=100, setpoint_c=50.0)
            o = plant.step(PERIODO_S, inp)
            filas.append({
                "evento": etiqueta, "t_planta_h": o.t_planta_h, "hora_dia_h": o.hora_dia_h,
                "t_lote_h": o.t_lote_h, "t_proceso_h": o.tiempo_proceso_h, "t_secado_h": o.t_secado_h,
                "t_parado_h": o.t_parado_h, "estado_planta": ESTADOS_TXT[o.estado_planta],
                "plant_mode": modo, "comm_lost": int(comm_lost), "fan_aplicado": o.fan_cmd_aplicado,
                "heater_permiso": o.heater_permiso, "T_ambiente_c": o.t_ambiente_c,
                "RH_ambiente_pct": o.rh_ambient_pct, "T_process_c": o.t_process_c,
                "RH_process_pct": o.rh_process_pct, "M_prom_bh": o.m_coffee_pct, "M_max_bh": o.m_coffee_max_pct,
                "M_min_bh": o.m_coffee_min_pct, "potencia_res_kw": o.potencia_res_kw,
                "caudal_m3_min": o.caudal_m3_min, "caudal_natural_m3_min": o.caudal_natural_m3_min,
                "energia_kwh": o.energia_kwh, "agua_evaporada_kg": plant.contadores.agua_evaporada_kg,
            })

    out_dir = os.path.join(aqui, "resultados", "ensayos")
    os.makedirs(out_dir, exist_ok=True)
    ruta_csv = os.path.join(out_dir, "continuidad_fisica.csv")
    with open(ruta_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        for r in filas:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})

    # Resumen por evento: lo que debe verse en el documento
    print(f"{'evento':<14}{'t_ini[h]':>9}{'T_proc ini->fin [C]':>22}{'M ini->fin [% b.h.]':>22}"
          f"{'agua [kg]':>11}{'E [kWh]':>9}")
    i = 0
    for etiqueta, segundos, *_ in SECUENCIA:
        n = int(segundos / PERIODO_S)
        a, b = filas[i], filas[i + n - 1]
        p = filas[i - 1] if i > 0 else a
        print(f"{etiqueta:<14}{p['t_planta_h']:9.2f}{p['T_process_c']:11.1f} ->{b['T_process_c']:6.1f}"
              f"{p['M_prom_bh']:12.3f} ->{b['M_prom_bh']:7.3f}"
              f"{b['agua_evaporada_kg'] - p['agua_evaporada_kg']:11.3f}{b['energia_kwh'] - p['energia_kwh']:9.2f}")
        i += n
    u = filas[-1]
    print(f"\nRelojes al final: planta {u['t_planta_h']:.2f} h | lote {u['t_lote_h']:.2f} h | "
          f"proceso (RUN) {u['t_proceso_h']:.2f} h | secado {u['t_secado_h']:.2f} h | parado {u['t_parado_h']:.2f} h")
    print(f"CSV: {ruta_csv}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    t = [r["t_planta_h"] for r in filas]
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True,
                                        gridspec_kw={"height_ratios": [3, 2, 1]})
    colores = {"REPOSO": "#e0e0e0", "PARO": "#ffe7a8", "ENFRIAMIENTO": "#cfe3f7",
               "COMM PERDIDA": "#f6c4c4", "RECUPERACION": "#d9f0d3"}
    i = 0
    for etiqueta, segundos, *_ in SECUENCIA:
        n = int(segundos / PERIODO_S)
        if etiqueta in colores:
            for ax in (ax1, ax2, ax3):
                ax.axvspan(filas[i]["t_planta_h"] - FACTOR / 3600, filas[i + n - 1]["t_planta_h"],
                           color=colores[etiqueta], alpha=0.6, lw=0)
            ax1.text(filas[i]["t_planta_h"], 58, etiqueta, fontsize=8, va="top")
        i += n
    ax1.plot(t, [r["T_process_c"] for r in filas], label="T proceso (plenum)", color="#c0392b")
    ax1.plot(t, [r["T_ambiente_c"] for r in filas], label="T ambiente (ciclo día/noche)", color="#2c3e50", ls="--")
    ax1.axhline(50, color="#999", lw=0.8, ls=":")
    ax1.set_ylabel("Temperatura [°C]")
    ax1.set_ylim(10, 60)
    ax1.legend(loc="lower right", fontsize=8)
    ax2.plot(t, [r["M_prom_bh"] for r in filas], label="Humedad promedio", color="#27ae60")
    ax2.plot(t, [r["M_max_bh"] for r in filas], label="Capa más húmeda", color="#27ae60", ls="--", lw=0.8)
    ax2.set_ylabel("Humedad [% b.h.]")
    ax2.legend(loc="upper right", fontsize=8)
    ax3.plot(t, [r["potencia_res_kw"] for r in filas], color="#e67e22", lw=0.9)
    ax3.set_ylabel("Resistencia [kW]")
    ax3.set_xlabel("Tiempo de planta [h de modelo]  (inicio 08:00)")
    fig.suptitle("Continuidad física: la planta sigue evolucionando con PARO, enfriamiento y comunicación perdida",
                 fontsize=10)
    fig.tight_layout()
    ruta_fig = os.path.join(aqui, "..", "figures", "ensayo_continuidad_fisica.png")
    os.makedirs(os.path.dirname(ruta_fig), exist_ok=True)
    fig.savefig(ruta_fig, dpi=150)
    print(f"Figura: {os.path.normpath(ruta_fig)}")


if __name__ == "__main__":
    main()

"""
compara_codesys_replica.py
===========================

Verificación de equivalencia Python+CODESYS+FluidSIM frente a la réplica en
Python de la campaña Monte Carlo.

Procedimiento (en el PC con CODESYS y FluidSIM):
    python modbus_server.py --semilla 1001 --log-csv resultados/verificacion/V1001_REF.csv
    En la HMI: perfil REF, caudal 100 %, «Nuevo lote» y START; dejar llegar a FIN DE SECADO.
    Repetir con otras semillas/perfiles (p. ej. 1002 REF, 1001 P1-C75).
Luego:
    python compara_codesys_replica.py resultados/verificacion/V1001_REF.csv --semilla 1001 --perfil REF

Compara, en el instante en que se cumple el criterio de fin (promedio ≤ 11 % y
capa más húmeda ≤ 12 % b.h.): tiempo de secado efectivo (horas con
calentamiento permitido), energía eléctrica, humedad final y capas, contra
``control_supervisado.simular_supervisada`` con la misma semilla y perfil.
Tolerancia de equivalencia declarada: ±3 % en tiempo y energía (la resolución del
servidor es 0.15 h por ciclo con factor 540 y la compuerta de FluidSIM tarda
segundos reales en invertir, minutos de modelo).

Diferencias esperadas y declaradas: CARGA e INVERSION en CODESYS/FluidSIM
tienen duración real (con factor 540, 1 s = 9 min de modelo); en la réplica la
inversión es instantánea y el secado empieza en t = 0.
Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import argparse
import math

import pandas as pd

TOLERANCIA_PCT = 3.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--semilla", type=int, required=True)
    ap.add_argument("--perfil", default="REF")
    a = ap.parse_args()

    d = pd.read_csv(a.csv)
    # último lote del archivo: desde el último reinicio de t_lote_h
    reinicios = d.index[d.t_lote_h.diff() < 0]
    if len(reinicios):
        d = d.loc[reinicios[-1]:].reset_index(drop=True)
    fin = d[(d.M_prom_bh <= 11.0) & (d.M_max_bh <= 12.0) & (d.t_secado_h > 0)]
    if fin.empty:
        raise SystemExit("El CSV no llega al criterio de fin (promedio ≤ 11 % y capa ≤ 12 %).")
    f = fin.iloc[0]

    from campana_montecarlo import realizacion
    from control_supervisado import simular_supervisada
    from perfiles_termicos import PERFILES_POR_CODIGO
    dias, m0 = realizacion(a.semilla)
    r = simular_supervisada(dias, PERFILES_POR_CODIGO[a.perfil].parametros_control(), t_max_h=720.0, m0_bh_pct=m0)

    filas = [
        ("Tiempo de secado efectivo [h]", f.t_secado_h, r.t_obj_h),
        ("Energía eléctrica [kWh]", f.energia_kwh, r.contadores.energia_electrica_kwh),
        ("Humedad promedio final [% b.h.]", f.M_prom_bh, r.m_final_bh_pct),
        ("Capa más húmeda [% b.h.]", f.M_max_bh, r.m_capa_max_bh_pct),
        ("Capa más seca [% b.h.]", f.M_min_bh, r.m_capa_min_bh_pct),
    ]
    print(f"Semilla {a.semilla}, perfil {a.perfil}, M0 = {m0:.2f} % b.h.   Archivo: {a.csv}")
    print(f"{'Indicador':34s} {'CODESYS':>9s} {'Réplica':>9s} {'Dif.':>8s}")
    ok = True
    for nom, x, y in filas:
        dif = 100 * (x / y - 1) if y else math.nan
        print(f"{nom:34s} {x:9.3f} {y:9.3f} {dif:+7.2f} %")
        if nom.startswith(("Tiempo", "Energía")) and abs(dif) > TOLERANCIA_PCT:
            ok = False
    print(f"\nEquivalencia (±{TOLERANCIA_PCT:.0f} % en tiempo y energía): {'CUMPLE' if ok else 'NO CUMPLE (revisar y declarar)'}")


if __name__ == "__main__":
    main()

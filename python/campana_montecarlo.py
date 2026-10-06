"""
campana_montecarlo.py
======================

Campaña Monte Carlo del proyecto (piloto y campaña final). Corre, para cada
realización aleatoria, las TRES estrategias con exactamente el mismo clima y
la misma humedad inicial (diseño pareado):

    PASIVA  - secado solar pasivo (escenario_sol_abierto.py)
    ACTIVA  - secado solar activo (linea_base_activa.py)
    REF     - supervisada, práctica de Cenicafé (50 °C, caudal 100 %)
    P1..P3 x C30/C75/C100 - supervisada, diseño factorial 3 x 3 de perfil
              térmico x caudal (perfiles_termicos.py; réplica del PLC en
              control_supervisado.py)

Trabajo de grado - Sistema de supervisión digital para el secado de café.
Protocolo: python/metodologia_estadistica_monte_carlo.md, sección 7.

Qué es aleatorio en cada realización (semilla guardada)
--------------------------------------------------------
- Clima: secuencia de días con persistencia AR(1)
  (generador_ambiente.secuencia_dias_perturbados; sigma y persistencia de
  NASA POWER 2005-2024).
- Humedad inicial del café: uniforme entre 52 y 56 % b.h. (rango del café
  lavado al salir del beneficio en Colombia; SECAFÉ, Parra-Coronado et al.,
  2008).

Uso (desde la carpeta python/)
------------------------------
    # Piloto (10 realizaciones, semillas 1-10):
    python campana_montecarlo.py --n 10 --semilla-inicial 1 --salida resultados/piloto
    # Campaña final (N calculado con analisis_montecarlo.py, semillas nuevas):
    python campana_montecarlo.py --n 120 --semilla-inicial 1001 --salida resultados/campana --procesos 4

- Guarda cada realización apenas termina (resultados.csv): si se corta la
  luz o se cierra la terminal, al volver a correr el MISMO comando continúa
  donde iba (se saltan las semillas ya completas).
- metadatos.json: fecha, comando, versiones, distribuciones, perfiles y
  semillas, para reconstruir cualquier corrida.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import subprocess
import sys
import time
from datetime import datetime

import numpy as np

import balance_energia as be
import cinetica_roa as roa
import generador_ambiente as amb
from control_supervisado import simular_supervisada
from escenario_sol_abierto import condiciones_patio
from linea_base_activa import condiciones_activa
from perfiles_termicos import HUMEDAD_CAMBIO_BH_PCT, PERFILES

M0_MIN_BH, M0_MAX_BH = 52.0, 56.0   # SECAFÉ (2008): 52-56 % b.h. al salir del beneficio
T_MAX_H = 720.0                      # horizonte: 30 días (censura)
DIAS_CLIMA = 40                      # días generados por realización (se repiten si hace falta)
ESTRATEGIAS = ["PASIVA", "ACTIVA"] + [p.codigo for p in PERFILES]

CAMPOS = [
    "semilla", "estrategia", "descripcion", "m0_bh_pct", "t_obj_h", "censurado", "m_final_bh_pct",
    "capa_min_bh_pct", "capa_max_bh_pct", "tasa_secado_pct_h", "agua_kg",
    "elec_kwh", "resistencia_kwh", "ventilador_kwh", "solar_kwh", "total_kwh",
    "kwh_por_kg_cps", "sec_total_kj_kg", "sec_comprada_kj_kg", "eficiencia_pct",
    "iae_c_h", "ise_c2_h", "sobreimpulso_c", "error_medio_c",
    "horas_grano_50c", "horas_rehumectacion", "horas_fuera_rango", "n_inversiones",
    "tmin_medio_c", "tmax_medio_c", "ea_medio_kpa", "segundos_computo",
]


def realizacion(semilla: int):
    """Clima y humedad inicial de una realización (reproducible por semilla)."""
    rng = np.random.default_rng(semilla)
    dias = amb.secuencia_dias_perturbados(rng, DIAS_CLIMA)
    m0 = float(rng.uniform(M0_MIN_BH, M0_MAX_BH))
    return dias, m0


def _fila_solar(semilla, codigo, desc, dias, m0, condiciones, balance):
    t0 = time.time()
    r = roa.simular(condiciones, t_max_h=T_MAX_H, m0_bh_pct=m0)
    cens = math.isinf(r.t_objetivo_h)
    t_obj = T_MAX_H if cens else r.t_objetivo_h
    b = balance(t_obj, m0)
    mf = float(r.m_bh_pct[-1])
    return {
        "estrategia": codigo, "descripcion": desc, "t_obj_h": t_obj, "censurado": int(cens),
        "m_final_bh_pct": mf, "capa_min_bh_pct": mf, "capa_max_bh_pct": mf,
        "tasa_secado_pct_h": (m0 - mf) / t_obj, "agua_kg": b.agua_kg,
        "elec_kwh": b.electrica_kwh, "resistencia_kwh": 0.0, "ventilador_kwh": b.electrica_kwh,
        "solar_kwh": b.solar_kwh, "total_kwh": b.total_kwh, "kwh_por_kg_cps": b.comprada_kwh_por_kg_cps,
        "sec_total_kj_kg": b.sec_total_kj_kg_agua, "sec_comprada_kj_kg": b.sec_comprada_kj_kg_agua,
        "eficiencia_pct": b.eficiencia_termica_pct, "iae_c_h": "", "ise_c2_h": "", "sobreimpulso_c": "",
        "error_medio_c": "", "horas_grano_50c": "", "horas_rehumectacion": r.horas_rehumectacion,
        "horas_fuera_rango": r.horas_fuera_de_rango, "n_inversiones": "",
        "segundos_computo": time.time() - t0,
    }


def _fila_supervisada(perfil, dias, m0):
    t0 = time.time()
    r = simular_supervisada(dias, perfil.parametros_control(), t_max_h=T_MAX_H, m0_bh_pct=m0)
    cens = math.isinf(r.t_obj_h)
    t_obj = T_MAX_H if cens else r.t_obj_h
    c = r.contadores
    b = be.BalanceEnergia(perfil.codigo, t_obj, c.agua_evaporada_kg, c.energia_electrica_kwh, 0.0)
    return {
        "estrategia": perfil.codigo, "descripcion": perfil.nombre, "t_obj_h": t_obj, "censurado": int(cens),
        "m_final_bh_pct": r.m_final_bh_pct, "capa_min_bh_pct": r.m_capa_min_bh_pct,
        "capa_max_bh_pct": r.m_capa_max_bh_pct, "tasa_secado_pct_h": (m0 - r.m_final_bh_pct) / t_obj,
        "agua_kg": c.agua_evaporada_kg, "elec_kwh": c.energia_electrica_kwh,
        "resistencia_kwh": c.energia_resistencia_kwh, "ventilador_kwh": c.energia_ventilador_kwh,
        "solar_kwh": 0.0, "total_kwh": b.total_kwh, "kwh_por_kg_cps": b.comprada_kwh_por_kg_cps,
        "sec_total_kj_kg": b.sec_total_kj_kg_agua, "sec_comprada_kj_kg": b.sec_comprada_kj_kg_agua,
        "eficiencia_pct": b.eficiencia_termica_pct, "iae_c_h": r.iae_c_h, "ise_c2_h": r.ise_c2_h,
        "sobreimpulso_c": r.sobreimpulso_c, "error_medio_c": r.error_medio_regimen_c,
        "horas_grano_50c": c.horas_grano_sobre_50c, "horas_rehumectacion": c.horas_rehumectacion,
        "horas_fuera_rango": c.horas_fuera_de_rango, "n_inversiones": r.n_inversiones,
        "segundos_computo": time.time() - t0,
    }


def correr_semilla(semilla: int) -> list[dict]:
    """Corre todas las estrategias para una semilla. Función de módulo
    (necesaria para multiprocessing en Windows)."""
    dias, m0 = realizacion(semilla)
    clima = {
        "tmin_medio_c": float(np.mean([d.t_min for d in dias])),
        "tmax_medio_c": float(np.mean([d.t_max for d in dias])),
        "ea_medio_kpa": float(np.mean([d.ea_kpa for d in dias])),
    }
    filas = [
        _fila_solar(semilla, "PASIVA", "Solar pasiva", dias, m0, condiciones_patio(dias), be.balance_pasiva),
        _fila_solar(semilla, "ACTIVA", "Solar activa", dias, m0, condiciones_activa(dias),
                    lambda t, m: be.balance_activa(t, m0_bh=m)),
    ]
    filas += [_fila_supervisada(p, dias, m0) for p in PERFILES]
    for f in filas:
        f.update({"semilla": semilla, "m0_bh_pct": m0, **clima})
    return filas


def _semillas_completas(ruta_csv: str) -> set[int]:
    if not os.path.exists(ruta_csv):
        return set()
    cuenta: dict[int, int] = {}
    with open(ruta_csv, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            s = int(fila["semilla"])
            cuenta[s] = cuenta.get(s, 0) + 1
    return {s for s, n in cuenta.items() if n >= len(ESTRATEGIAS)}


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL,
                                       cwd=os.path.dirname(os.path.abspath(__file__))).decode().strip()
    except Exception:
        return "desconocido"


def _metadatos(args, semillas) -> dict:
    import scipy

    return {
        "fecha_inicio": datetime.now().isoformat(timespec="seconds"),
        "comando": " ".join(sys.argv),
        "git_commit": _git_commit(),
        "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
        "sistema": platform.platform(),
        "semillas": [semillas[0], semillas[-1]], "n": len(semillas),
        "horizonte_h": T_MAX_H, "dias_clima_por_realizacion": DIAS_CLIMA,
        "aleatorio": {
            "clima": {
                "modelo": "AR(1) sobre anomalías diarias (generador_ambiente.secuencia_dias_perturbados)",
                "sigma_tmin_c": amb.SIGMA_TMIN_C, "sigma_tmax_c": amb.SIGMA_TMAX_C,
                "phi_tmin": amb.PHI_TMIN, "phi_tmax": amb.PHI_TMAX,
                "sigma_ea_resid_frac": amb.SIGMA_EA_RESID_FRAC, "phi_ea": amb.PHI_EA,
                "fuente": "NASA POWER 2005-2024 (4.97 N, 75.65 O), medias de Naranjal (Cenicafé 1998)",
            },
            "m0_bh_pct": {"distribucion": "uniforme", "min": M0_MIN_BH, "max": M0_MAX_BH,
                          "fuente": "SECAFÉ (Parra-Coronado et al., 2008)"},
        },
        "humedad_objetivo_bh_pct": roa.HUMEDAD_OBJETIVO_BH_PCT,
        "perfiles": [vars(p) for p in PERFILES], "humedad_cambio_perfil_bh_pct": HUMEDAD_CAMBIO_BH_PCT,
        "estrategias": ESTRATEGIAS,
    }


def _consola_utf8() -> None:
    try:  # consolas de Windows con codificación antigua
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, required=True, help="número de realizaciones")
    ap.add_argument("--semilla-inicial", type=int, default=1)
    ap.add_argument("--salida", default="resultados/piloto", help="carpeta de resultados")
    ap.add_argument("--procesos", type=int, default=1, help="procesos en paralelo (núcleos del PC)")
    args = ap.parse_args()
    _consola_utf8()

    os.makedirs(args.salida, exist_ok=True)
    ruta_csv = os.path.join(args.salida, "resultados.csv")
    semillas = list(range(args.semilla_inicial, args.semilla_inicial + args.n))
    hechas = _semillas_completas(ruta_csv)
    pendientes = [s for s in semillas if s not in hechas]
    with open(os.path.join(args.salida, "metadatos.json"), "w", encoding="utf-8") as f:
        json.dump(_metadatos(args, semillas), f, indent=2, ensure_ascii=False)

    print(f"Realizaciones: {len(semillas)} | ya completas: {len(hechas & set(semillas))} | "
          f"pendientes: {len(pendientes)} | estrategias por realización: {len(ESTRATEGIAS)}")
    if not pendientes:
        print("Nada pendiente.")
        return

    nuevo = not os.path.exists(ruta_csv)
    t_ini = time.time()
    with open(ruta_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if nuevo:
            w.writeheader()

        def guardar(filas, k):
            for fila in filas:
                w.writerow({c: fila.get(c, "") for c in CAMPOS})
            f.flush()
            dt = time.time() - t_ini
            resto = dt / k * (len(pendientes) - k)
            t = {x["estrategia"]: x["t_obj_h"] for x in filas}
            print(f"[{k}/{len(pendientes)}] semilla {filas[0]['semilla']}: M0 {filas[0]['m0_bh_pct']:.1f} % | "
                  f"PASIVA {t['PASIVA']:.0f} h | ACTIVA {t['ACTIVA']:.0f} h | REF {t['REF']:.1f} h | "
                  f"supervisadas {min(v for e, v in t.items() if '-' in e):.0f}-"
                  f"{max(v for e, v in t.items() if '-' in e):.0f} h | faltan ~{resto / 60:.1f} min", flush=True)

        if args.procesos > 1:
            from multiprocessing import Pool

            with Pool(args.procesos) as pool:
                for k, filas in enumerate(pool.imap_unordered(correr_semilla, pendientes), 1):
                    guardar(filas, k)
        else:
            for k, s in enumerate(pendientes, 1):
                guardar(correr_semilla(s), k)
    print(f"Listo en {(time.time() - t_ini) / 60:.1f} min. Resultados: {ruta_csv}")


if __name__ == "__main__":
    main()

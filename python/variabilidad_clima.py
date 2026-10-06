"""
variabilidad_clima.py
======================

Calcula la VARIABILIDAD DÍA A DÍA del clima de Chinchiná a partir de una
serie diaria real, para reemplazar los supuestos ``sigma_t = 1.5 °C`` y
``sigma_ea_frac = 0.08`` de ``generador_ambiente.condiciones_perturbadas``
(pendiente del 4 oct 2026, punto 1 de la auditoría del modelo).
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Método ("método delta")
------------------------
- Los VALORES MEDIOS siguen siendo los de la estación Naranjal de Cenicafé
  (T_min 16.4 °C, T_max 26.8 °C; Cenicafé 49(4), 1998), que es medición
  en el sitio.
- De la serie diaria se toman solo las DESVIACIONES respecto a la media de
  cada mes (anomalías). Así el sesgo absoluto de un reanálisis en montaña
  (la celda de NASA POWER promedia ~50 km de terreno) no entra al modelo;
  solo entra cuánto varía un día respecto a otro.
- Resultados: sigma de T_min y de T_max, correlación T_min-T_max, sigma
  fraccional de la presión de vapor (ea) y autocorrelación de un día al
  siguiente (persistencia).

Datos de entrada: NASA POWER (diario)
---------------------------------------
Descargar en https://power.larc.nasa.gov/data-access-viewer/
    - Comunidad: Agroclimatology (AG); Temporal: Daily
    - Punto: latitud 4.97, longitud -75.65 (Naranjal, 04°58' N 75°39' O)
    - Fechas: 01/01/2005 a 31/12/2024 (20 años)
    - Parámetros: T2M_MAX, T2M_MIN, QV2M (humedad específica), PS (presión)
    - Formato: CSV
Cita: NASA Langley Research Center (LaRC) POWER Project, funded through the
NASA Earth Science/Applied Science Program. Datos obtenidos de
https://power.larc.nasa.gov el <fecha de descarga>.

Uso:
    python variabilidad_clima.py ruta/al/POWER_Point_Daily.csv

Alternativa con datos de estación (mejor si se consiguen): datos diarios
del IDEAM (plataforma DHIME, estación más cercana en Chinchiná) o de los
Anuarios Meteorológicos Cafeteros de Cenicafé (estación Naranjal). Basta
con un CSV con columnas YEAR, MO, DY, T2M_MAX, T2M_MIN y, si se tiene,
QV2M y PS (o RH2M y T2M).
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd


def leer_power_csv(ruta: str) -> pd.DataFrame:
    """Lee un CSV de NASA POWER (salta el encabezado hasta -END HEADER-)."""
    with open(ruta, encoding="utf-8", errors="ignore") as f:
        lineas = f.readlines()
    inicio = 0
    for i, l in enumerate(lineas):
        if l.strip().startswith("-END HEADER-"):
            inicio = i + 1
            break
    df = pd.read_csv(ruta, skiprows=inicio)
    df = df.replace(-999.0, np.nan)
    if "DOY" in df.columns and "MO" not in df.columns:
        fechas = pd.to_datetime(df["YEAR"].astype(str), format="%Y") + pd.to_timedelta(df["DOY"] - 1, unit="D")
        df["MO"] = fechas.dt.month
    return df


def presion_vapor_kpa(df: pd.DataFrame) -> pd.Series | None:
    """ea [kPa] diaria a partir de QV2M [g/kg] y PS [kPa], o de RH2M y T2M."""
    if {"QV2M", "PS"} <= set(df.columns):
        q = df["QV2M"] / 1000.0  # kg/kg
        return q * df["PS"] / (0.622 + 0.378 * q)
    if {"RH2M", "T2M"} <= set(df.columns):
        es = 0.6108 * np.exp(17.27 * df["T2M"] / (df["T2M"] + 237.3))  # FAO-56 ec. 11
        return df["RH2M"] / 100.0 * es
    return None


def anomalia(serie: pd.Series, mes: pd.Series) -> pd.Series:
    """Desviación respecto a la media de cada mes (quita la estacionalidad)."""
    return serie - serie.groupby(mes).transform("mean")


def analizar(df: pd.DataFrame) -> dict:
    mes = df["MO"]
    a_min = anomalia(df["T2M_MIN"], mes)
    a_max = anomalia(df["T2M_MAX"], mes)
    res = {
        "n_dias": int(df["T2M_MIN"].notna().sum()),
        "sigma_tmin_c": float(a_min.std()),
        "sigma_tmax_c": float(a_max.std()),
        "corr_tmin_tmax": float(a_min.corr(a_max)),
        "autocorr_tmin_1d": float(a_min.autocorr(1)),
        "autocorr_tmax_1d": float(a_max.autocorr(1)),
        "media_tmin_power_c": float(df["T2M_MIN"].mean()),
        "media_tmax_power_c": float(df["T2M_MAX"].mean()),
    }
    ea = presion_vapor_kpa(df)
    if ea is not None:
        frac = ea / ea.groupby(mes).transform("mean")
        res["sigma_ea_frac"] = float(frac.std())
        res["autocorr_ea_1d"] = float((frac - 1.0).autocorr(1))
        res["corr_ea_tmin"] = float((frac - 1.0).corr(a_min))
    return res


def chequeo_extremos(sigma_tmin: float, sigma_tmax: float) -> str:
    """Contraste con los extremos absolutos de Naranjal (Cenicafé, 1998):
    mínima absoluta 11.0 °C, máxima absoluta 33.6 °C (récords de décadas,
    del orden de 3-4 sigma de la distribución diaria)."""
    z_min = (16.4 - 11.0) / sigma_tmin
    z_max = (33.6 - 26.8) / sigma_tmax
    return (f"Récord de mínima (11.0 °C) a {z_min:.1f} sigma y de máxima (33.6 °C) a {z_max:.1f} sigma "
            f"de la media de Naranjal (esperable: ~3-4.5 sigma para récords de ~40 años).")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        print("Chequeo de los supuestos actuales (sigma_t = 1.5 °C):")
        print("  " + chequeo_extremos(1.5, 1.5))
        sys.exit(0)
    df = leer_power_csv(sys.argv[1])
    r = analizar(df)
    print(f"Días analizados: {r['n_dias']}")
    print(f"Media T_min / T_max NASA POWER: {r['media_tmin_power_c']:.1f} / {r['media_tmax_power_c']:.1f} °C "
          f"(Naranjal: 16.4 / 26.8 °C; la diferencia es el sesgo de la celda y NO se usa)")
    print(f"sigma T_min = {r['sigma_tmin_c']:.2f} °C | sigma T_max = {r['sigma_tmax_c']:.2f} °C "
          f"(supuesto actual 1.5 °C para ambas)")
    print(f"Correlación T_min-T_max = {r['corr_tmin_tmax']:.2f} (supuesto actual: 0, independientes)")
    print(f"Autocorrelación de un día al siguiente: T_min {r['autocorr_tmin_1d']:.2f}, T_max {r['autocorr_tmax_1d']:.2f} "
          f"(supuesto actual: 0, días independientes)")
    if "sigma_ea_frac" in r:
        print(f"sigma fraccional de ea = {r['sigma_ea_frac']:.3f} (supuesto actual 0.08); "
              f"autocorrelación {r['autocorr_ea_1d']:.2f}; correlación con T_min {r['corr_ea_tmin']:.2f}")
    print(chequeo_extremos(r["sigma_tmin_c"], r["sigma_tmax_c"]))

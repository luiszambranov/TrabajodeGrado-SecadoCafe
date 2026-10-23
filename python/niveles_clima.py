"""
niveles_clima.py
=================

Niveles de clima para las corridas dirigidas (efecto_clima.py y el caso frío
de limites_actuacion.py), obtenidos de PERCENTILES de la serie diaria NASA POWER
2005-2024 (../data/clima/POWER_Naranjal_diario_2005_2024.csv), con el mismo
«método delta» de ``variabilidad_clima.py``:

1. Anomalías diarias respecto a la media de cada mes (T mín, T máx; ea como
   fracción). El sesgo absoluto del reanálisis no entra; solo cuánto se aparta
   un periodo de lo normal.
2. Media móvil de 2 días (un secado supervisado dura 1.5-2.5 días): el nivel
   representa un periodo sostenido de ese tipo, no un día aislado.
3. Percentiles 5 y 95 de esas anomalías, sumados a las medias de Naranjal
   (T mín 16.4 °C, T máx 26.8 °C; Cenicafé 1998) y aplicados a todos los días
   de la corrida.

Consistencia psicrométrica:
- CT-/CT+ (temperatura): se conserva la trayectoria de HR nocturna del modelo
  (ea = 0.97·es(T mín), como ``generador_ambiente``); ea se recalcula con la
  nueva T mín. Si se dejara ea fija, CT- daría HR > 100 % de madrugada.
- CH-/CH+ (humedad): se conserva la trayectoria de temperatura y cambia ea.
  CH+ al percentil 95 (+7 %) daría HR nocturna de 104 %, imposible a la
  misma temperatura: se toma el máximo físicamente posible, HR = 99.5 % en la
  madrugada (+2.6 % de ea). Es un hallazgo, no un recorte: en Chinchiná el
  aire nocturno ya está casi saturado.
- C* (combinado adverso): en la serie, los periodos fríos son también más
  secos (correlación de las anomalías de T y ea = +0.55). La combinación
  adversa físicamente plausible es FRÍO con la noche saturada: T del CT- y
  ea = 0.995·es(T mín).

Lo que NO son: no son mediciones de la estación (son niveles sintéticos
construidos con percentiles de un reanálisis aplicados a medias medidas).
Trabajo de grado - Sistema de supervisión digital para el secado de café.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

import generador_ambiente as amb

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA_POWER = os.path.join(AQUI, "..", "data", "clima", "POWER_Naranjal_diario_2005_2024.csv")
VENTANA_DIAS = 2
FRAC_NOCHE = 0.97        # = generador_ambiente.FRACCION_SATURACION_NOCTURNA
FRAC_NOCHE_MAX = 0.995   # máximo físico usado para CH+ y C*


@dataclass(frozen=True)
class Nivel:
    codigo: str
    descripcion: str
    t_min: float
    t_max: float
    ea_kpa: float
    origen: str

    def dias(self, n: int = 40):
        c = amb.CondicionesClimaticas(t_min=self.t_min, t_max=self.t_max, ea_kpa=self.ea_kpa)
        return [c] * n

    @property
    def hr_noche(self) -> float:
        return 100.0 * self.ea_kpa / float(amb.es_kpa(self.t_min))

    @property
    def hr_dia(self) -> float:
        return 100.0 * self.ea_kpa / float(amb.es_kpa(self.t_max))


def anomalias_percentiles(ruta: str = RUTA_POWER, ventana: int = VENTANA_DIAS) -> dict:
    from variabilidad_clima import leer_power_csv, presion_vapor_kpa
    df = leer_power_csv(ruta)
    df["ea"] = presion_vapor_kpa(df)
    for c in ("T2M_MIN", "T2M_MAX"):
        df["a_" + c] = df[c] - df.groupby("MO")[c].transform("mean")
    df["a_ea"] = df["ea"] / df.groupby("MO")["ea"].transform("mean") - 1.0
    r = df[["a_T2M_MIN", "a_T2M_MAX", "a_ea"]].rolling(ventana).mean().dropna()
    q = r.quantile([0.01, 0.05, 0.95, 0.99])
    corr = float(np.corrcoef(((df.a_T2M_MIN + df.a_T2M_MAX) / 2).values, df.a_ea.values)[0, 1])
    return {"q": q, "n_dias": len(df), "corr_T_ea": corr}


def niveles() -> list[Nivel]:
    a = anomalias_percentiles()
    q = a["q"]
    tmin0, tmax0 = amb.T_MIN_MEDIO, amb.T_MAX_MEDIO
    ea0 = FRAC_NOCHE * float(amb.es_kpa(tmin0))
    dmin_lo, dmax_lo = float(q.loc[0.05, "a_T2M_MIN"]), float(q.loc[0.05, "a_T2M_MAX"])
    dmin_hi, dmax_hi = float(q.loc[0.95, "a_T2M_MIN"]), float(q.loc[0.95, "a_T2M_MAX"])
    ea_lo = float(q.loc[0.05, "a_ea"])
    ea_hi = float(q.loc[0.95, "a_ea"])
    t_ct_lo = (tmin0 + dmin_lo, tmax0 + dmax_lo)
    t_ct_hi = (tmin0 + dmin_hi, tmax0 + dmax_hi)
    ea_ch_hi = min(ea0 * (1 + ea_hi), FRAC_NOCHE_MAX * float(amb.es_kpa(tmin0)))
    return [
        Nivel("C0", "Nominal de Chinchiná (Naranjal)", tmin0, tmax0, ea0, "Medias de Naranjal; ea = 0.97·es(Tmín)"),
        Nivel("CT-", "Temperatura baja (p5)", *t_ct_lo, FRAC_NOCHE * float(amb.es_kpa(t_ct_lo[0])),
              f"p5 anomalías 2 d: Tmín {dmin_lo:+.2f}, Tmáx {dmax_lo:+.2f} °C; HR nocturna conservada"),
        Nivel("CT+", "Temperatura alta (p95)", *t_ct_hi, FRAC_NOCHE * float(amb.es_kpa(t_ct_hi[0])),
              f"p95 anomalías 2 d: Tmín {dmin_hi:+.2f}, Tmáx {dmax_hi:+.2f} °C; HR nocturna conservada"),
        Nivel("CH-", "Humedad baja (p5)", tmin0, tmax0, ea0 * (1 + ea_lo),
              f"p5 anomalía de ea 2 d: {100 * ea_lo:+.1f} %; T nominal"),
        Nivel("CH+", "Humedad alta (límite físico)", tmin0, tmax0, ea_ch_hi,
              f"p95 de ea ({100 * ea_hi:+.1f} %) imposible a T nominal (HR nocturna > 100 %): "
              f"se usa HR nocturna 99.5 % ({100 * (ea_ch_hi / ea0 - 1):+.1f} %)"),
        Nivel("C*", "Combinado adverso: frío con noche saturada", *t_ct_lo,
              FRAC_NOCHE_MAX * float(amb.es_kpa(t_ct_lo[0])),
              f"T del CT-; ea = 0.995·es(Tmín) (corr. T-ea en la serie = {a['corr_T_ea']:+.2f}: el frío "
              "viene seco; la noche saturada es lo más húmedo físicamente posible)"),
    ]


def helada_hipotetica() -> Nivel:
    """Caso de estrés hipotético (madrugada a -4 °C). NO pertenece al
    clima de Chinchiná (Naranjal, ~1 380 m: mínimas medias de 16 °C); sirve para
    mostrar qué consignas dejan de ser alcanzables con 6 kW."""
    t_min, t_max = -4.0, 8.0
    return Nivel("HELADA", "Hipotética: Tmín -4 °C, Tmáx 8 °C (fuera del clima del sitio)", t_min, t_max,
                 FRAC_NOCHE * float(amb.es_kpa(t_min)), "Caso hipotético; no es un percentil del sitio")


if __name__ == "__main__":
    a = anomalias_percentiles()
    print(f"Serie NASA POWER: {a['n_dias']} días; correlación anomalías T-ea = {a['corr_T_ea']:+.2f}")
    print(a["q"].round(3))
    print(f"\n{'Nivel':7s} {'Tmín':>6s} {'Tmáx':>6s} {'ea kPa':>7s} {'HR noche':>8s} {'HR día':>7s}  Origen")
    for n in niveles() + [helada_hipotetica()]:
        print(f"{n.codigo:7s} {n.t_min:6.2f} {n.t_max:6.2f} {n.ea_kpa:7.3f} {n.hr_noche:7.1f}% {n.hr_dia:6.1f}%  {n.origen}")

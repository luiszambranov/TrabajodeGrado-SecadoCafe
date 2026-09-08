"""
generador_ambiente.py
======================

Generador de temperatura y humedad relativa ambiente (nominal y
perturbado), para alimentar los modelos de secado solar (línea base
pasiva y línea base activa) del proyecto.
Semana 5 - "Modelo base validado".

Zona climática de referencia
-----------------------------
Estación Naranjal, Cenicafé (Centro Nacional de Investigaciones de
Café), Chinchiná, Caldas — zona cafetera central de Colombia,
~1300-1400 msnm. Fuente:

> "El clima de la estación central Naranjal". Revista Cenicafé,
> 49(4), 290-307 (1998). https://www.cenicafe.org/es/publications/arc049(04)290-307.pdf

Datos reportados (usados como constantes de este módulo):
    - Temperatura media anual: 20.8 °C (oscilación estacional ~1.1 °C,
      es decir prácticamente constante mes a mes).
    - Temperatura mínima media: 16.4 °C
    - Temperatura máxima media: 26.8 °C
    - Humedad relativa media anual: 78 % (oscilación estacional < 5 %)
    - HR nocturna: cercana a saturación (> 95 %)
    - HR de la tarde en días soleados: ~40 %
    - HR mínima diaria registrada: 53 %

Alcance v0.1 (simplificaciones explícitas)
--------------------------------------------
1. Ciclo diurno de temperatura: seno SIMÉTRICO, no el modelo asimétrico
   tipo Parton & Logan (1981) que usan algunos estudios agrometeorológicos
   (calentamiento diurno rápido, enfriamiento nocturno más lento). En
   este v0.1 el mínimo de temperatura cae a las 02:00 y el máximo a las
   14:00, en vez del amanecer real (~05:00-06:00, según Cenicafé). Es una
   aproximación aceptable para un primer modelo; se puede refinar después
   si la fidelidad horaria resulta importante para el control.
2. Humedad relativa: se deriva de un enfoque psicrométrico simple. Se
   asume presión de vapor real (ea) aproximadamente constante durante el
   día (aproximación estándar en meteorología agrícola de corto plazo:
   la cantidad absoluta de vapor de agua en el aire cambia poco en un
   día, aunque la temperatura sí), y:

        RH(t) = 100 * ea / es(T(t))

   con ``es(T)`` la presión de saturación (fórmula de Tetens/Magnus,
   FAO56 ecuación 11). Esto conecta el descenso de HR con el aumento de
   T de forma físicamente consistente, en vez de una curva de HR
   independiente que podría contradecir la curva de T. Se ajusta la ea
   nominal para que la HR quede cerca de saturación quer la temperatura
   está en su mínimo (de noche), replicando lo reportado por Cenicafé.
3. La variabilidad día a día (sigma_t, sigma_ea_frac en
   ``condiciones_perturbadas``) es un supuesto razonable, NO un dato
   reportado explícitamente en la fuente climática (que solo da
   promedios mensuales). Ajustar si se consigue un dato de variabilidad
   diaria real (por ejemplo series horarias de una estación).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Constantes climáticas de referencia (Estación Naranjal, Cenicafé)
# ---------------------------------------------------------------------------

T_MIN_MEDIO = 16.4   # °C
T_MAX_MEDIO = 26.8   # °C
HORA_T_MIN = 2.0     # h (0-24), ver simplificación (1) en el docstring
HORA_T_MAX = 14.0    # h

# Fracción de saturación asumida en el momento más frío del día (de
# noche la HR reportada por Cenicafé es > 95%).
FRACCION_SATURACION_NOCTURNA = 0.97


def es_kpa(t_c: np.ndarray) -> np.ndarray:
    """Presión de vapor de saturación [kPa] (fórmula de Tetens/Magnus, FAO56 ec. 11).

    t_c : temperatura del aire [°C].
    """
    t_c = np.asarray(t_c, dtype=float)
    return 0.6108 * np.exp(17.27 * t_c / (t_c + 237.3))


@dataclass
class CondicionesClimaticas:
    """Parámetros de un día de clima (nominal o perturbado).

    t_min, t_max : float
        Temperatura mínima y máxima del día [°C].
    hora_t_min, hora_t_max : float
        Hora del día (0-24) en que ocurren T_min y T_max.
    ea_kpa : float, opcional
        Presión de vapor real del día [kPa], asumida aprox. constante
        durante el día. Si no se da, se calcula para que la HR quede
        cerca de saturación cuando T = t_min (ver
        FRACCION_SATURACION_NOCTURNA).
    """

    t_min: float = T_MIN_MEDIO
    t_max: float = T_MAX_MEDIO
    hora_t_min: float = HORA_T_MIN
    hora_t_max: float = HORA_T_MAX
    ea_kpa: Optional[float] = None

    def __post_init__(self) -> None:
        if self.ea_kpa is None:
            self.ea_kpa = FRACCION_SATURACION_NOCTURNA * float(es_kpa(self.t_min))


def temperatura(t_horas: np.ndarray, cond: CondicionesClimaticas) -> np.ndarray:
    """Temperatura ambiente [°C] según la hora del día (ciclo seno simétrico, v0.1)."""
    t_horas = np.asarray(t_horas, dtype=float)
    t_media = (cond.t_max + cond.t_min) / 2.0
    amplitud = (cond.t_max - cond.t_min) / 2.0
    # sin(pi/2) ocurre 6h despues de la fase => fase = hora_t_max - 6
    fase = cond.hora_t_max - 6.0
    return t_media + amplitud * np.sin(2 * np.pi * (t_horas - fase) / 24.0)


def humedad_relativa(t_horas: np.ndarray, cond: CondicionesClimaticas) -> np.ndarray:
    """Humedad relativa ambiente [%] derivada de T(t) y ea aprox. constante."""
    t_c = temperatura(t_horas, cond)
    rh = 100.0 * cond.ea_kpa / es_kpa(t_c)
    return np.clip(rh, 0.0, 100.0)


def condiciones_nominales() -> CondicionesClimaticas:
    """Día climático nominal: T_min/T_max medios de la estación Naranjal."""
    return CondicionesClimaticas()


def condiciones_perturbadas(
    rng: np.random.Generator,
    sigma_t: float = 1.5,
    sigma_ea_frac: float = 0.08,
) -> CondicionesClimaticas:
    """Genera un día de clima perturbado (variabilidad día a día).

    Parámetros
    ----------
    rng : np.random.Generator
        Generador de números aleatorios (usar np.random.default_rng(seed)
        y GUARDAR la semilla para reproducibilidad, ver
        docs/matriz_comparativa_modelos.md y la guía operativa:
        "Semillas almacenadas").
    sigma_t : float
        Desviación estándar [°C] aplicada a T_min y T_max del día,
        alrededor de los valores medios de la estación Naranjal.
        Supuesto razonable (no reportado explícitamente en la fuente
        climática); ajustar si se consigue un dato de variabilidad
        diaria real.
    sigma_ea_frac : float
        Variabilidad fraccional de la presión de vapor real del día
        (días más húmedos/nublados vs. más secos/despejados).
    """
    t_min = float(rng.normal(T_MIN_MEDIO, sigma_t))
    t_max = float(rng.normal(T_MAX_MEDIO, sigma_t))
    if t_max <= t_min:
        # Evita un día atípico con oscilación invertida; conserva un
        # rango mínimo de 1 C.
        t_max = t_min + 1.0
    cond = CondicionesClimaticas(t_min=t_min, t_max=t_max)
    cond.ea_kpa = cond.ea_kpa * float(rng.normal(1.0, sigma_ea_frac))
    return cond


def generar_dia(cond: CondicionesClimaticas, paso_h: float = 1.0) -> dict:
    """Genera un día completo (0-24 h) de T y HR ambiente para una condición dada."""
    t_horas = np.arange(0.0, 24.0 + 1e-9, paso_h)
    return {
        "hora": t_horas,
        "T": temperatura(t_horas, cond),
        "HR": humedad_relativa(t_horas, cond),
    }


if __name__ == "__main__":
    nominal = condiciones_nominales()
    dia = generar_dia(nominal)
    print("Dia nominal (Estacion Naranjal, Cenicafe):")
    for h, t, hr in zip(dia["hora"][::3], dia["T"][::3], dia["HR"][::3]):
        print(f"  {h:5.1f} h   T={t:5.2f} C   HR={hr:5.1f} %")

    rng = np.random.default_rng(42)
    print("\n3 dias perturbados (T_min, T_max, ea_kpa):")
    for _ in range(3):
        c = condiciones_perturbadas(rng)
        print(f"  T_min={c.t_min:.2f} C  T_max={c.t_max:.2f} C  ea={c.ea_kpa:.4f} kPa")

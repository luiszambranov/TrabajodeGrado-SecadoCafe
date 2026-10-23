"""
generador_ambiente.py
======================

Generador de temperatura y humedad relativa ambiente (nominal y
perturbado), para alimentar los modelos de secado solar (línea base
pasiva y línea base activa) y el aire de entrada del secador eléctrico:
ciclo diurno asimétrico y variabilidad día a día AR(1) ajustada con NASA
POWER 2005-2024 (variabilidad_clima.py, data/reference/chinchina_clima_fuentes.md).

Zona climática de referencia
-----------------------------
Estación Naranjal, Cenicafé (Centro Nacional de Investigaciones de
Café), Chinchiná, Caldas — zona cafetera central de Colombia,
~1300-1400 msnm. Fuente:

> Baldión-Rincón, J. V., & Guzmán-Martínez, O. (1998). El clima de la
> estación central Naranjal en Chinchiná, Caldas, Colombia. Cenicafé,
> 49(4), 290-307. https://www.cenicafe.org/es/publications/arc049(04)290-307.pdf

Datos reportados (usados como constantes de este módulo):
    - Temperatura media anual: 20.8 °C (oscilación estacional ~1.1 °C,
      es decir prácticamente constante mes a mes).
    - Temperatura mínima media: 16.4 °C
    - Temperatura máxima media: 26.8 °C
    - Humedad relativa media anual: 78 % (oscilación estacional < 5 %)
    - HR nocturna: cercana a saturación (> 95 %)
    - HR de la tarde en días soleados: ~40 %
    - HR mínima diaria registrada: 53 %

Simplificaciones explícitas
----------------------------
1. Ciclo diurno de temperatura: curva
   ASIMÉTRICA de dos semicosenos con el mínimo a las 05:30 y el máximo a
   las 15:30, que son los centros de las franjas medidas en la sede de
   Cenicafé en Chinchiná: "La temperatura mínima ocurre entre las 05:00 y
   las 06:00 y la máxima entre las 15:00 y las 16:00" (Guzmán & Ramírez,
   2004, Cenicafé 55(2), p. 112). El calentamiento dura 10 h y el
   enfriamiento 14 h, igual que el patrón descrito por Parton & Logan
   (1981): sube rápido de día y baja lento de noche.
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
3. Variabilidad día a día: calculada de 20 años
   de datos diarios de NASA POWER (2005-2024, punto 4.97 N, 75.65 O,
   reanálisis MERRA-2) con python/variabilidad_clima.py y el "método
   delta": las MEDIAS siguen siendo las de Naranjal y de la serie solo se
   toman las desviaciones de cada día respecto a la media de su mes.
       sigma T_min = 0.97 °C, sigma T_max = 1.36 °C
       correlación T_min-T_max = -0.07 (~0, se tratan independientes)
       persistencia (autocorrelación de un día al siguiente):
           T_min 0.49, T_max 0.39 -> modelo AR(1) en
           ``secuencia_dias_perturbados``
       ea: se deriva de T_min (FRACCION_SATURACION_NOCTURNA); el ruido
           residual de ea/es(T_min) es 4 % con persistencia 0.22.
   Cita: NASA Langley Research Center POWER Project, https://power.larc.nasa.gov
   Datos en data/clima/.
   Limitación: un reanálisis suaviza los extremos (los récords de Naranjal
   quedan a ~5 sigma), así que sigma podría estar algo subestimada; se
   recomienda un análisis de sensibilidad con sigma = 1.5 °C.
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
HORA_T_MIN = 5.5     # h (0-24): 05:00-06:00 (Guzmán & Ramírez, 2004, Cenicafé 55(2):111-129)
HORA_T_MAX = 15.5    # h: 15:00-16:00 (misma fuente)

# Fracción de saturación asumida en el momento más frío del día (de
# noche la HR reportada por Cenicafé es > 95%).
FRACCION_SATURACION_NOCTURNA = 0.97

# Variabilidad día a día (NASA POWER 2005-2024, ver simplificación 3)
SIGMA_TMIN_C = 0.97
SIGMA_TMAX_C = 1.36
PHI_TMIN = 0.49          # autocorrelación de un día al siguiente
PHI_TMAX = 0.39
SIGMA_EA_RESID_FRAC = 0.04
PHI_EA = 0.22


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
    """Temperatura ambiente [°C] según la hora del día.

    Curva asimétrica de dos semicosenos (ver simplificación 1 del
    docstring): sube de T_min (hora_t_min) a T_max (hora_t_max) y baja de
    T_max a T_min del día siguiente en las horas restantes.
    """
    h = np.asarray(t_horas, dtype=float) % 24.0
    h_min, h_max = cond.hora_t_min, cond.hora_t_max
    amp = cond.t_max - cond.t_min
    dur_sube = (h_max - h_min) % 24.0
    dur_baja = 24.0 - dur_sube
    d_sube = (h - h_min) % 24.0
    subiendo = d_sube <= dur_sube
    t_sube = cond.t_min + amp * 0.5 * (1.0 - np.cos(np.pi * d_sube / dur_sube))
    d_baja = (h - h_max) % 24.0
    t_baja = cond.t_max - amp * 0.5 * (1.0 - np.cos(np.pi * d_baja / dur_baja))
    return np.where(subiendo, t_sube, t_baja)


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
    sigma_t: Optional[float] = None,
    sigma_ea_frac: float = SIGMA_EA_RESID_FRAC,
) -> CondicionesClimaticas:
    """Genera UN día de clima perturbado, independiente de los demás.

    Para campañas Monte Carlo usar ``secuencia_dias_perturbados``, que
    respeta la persistencia día a día medida (AR(1)).

    sigma_t : si se da, usa la misma sigma para T_min y T_max (análisis de
        sensibilidad); por defecto SIGMA_TMIN_C y
        SIGMA_TMAX_C (NASA POWER).
    sigma_ea_frac : ruido fraccional de ea alrededor de
        FRACCION_SATURACION_NOCTURNA*es(T_min).
    """
    s_min = SIGMA_TMIN_C if sigma_t is None else sigma_t
    s_max = SIGMA_TMAX_C if sigma_t is None else sigma_t
    return _dia_desde_anomalias(float(rng.normal(0.0, s_min)), float(rng.normal(0.0, s_max)),
                                float(rng.normal(0.0, sigma_ea_frac)))


def _dia_desde_anomalias(a_min: float, a_max: float, a_ea: float) -> CondicionesClimaticas:
    t_min = T_MIN_MEDIO + a_min
    t_max = T_MAX_MEDIO + a_max
    if t_max <= t_min:
        # Evita un día atípico con oscilación invertida; conserva 1 C de rango.
        t_max = t_min + 1.0
    cond = CondicionesClimaticas(t_min=t_min, t_max=t_max)
    cond.ea_kpa = cond.ea_kpa * (1.0 + a_ea)
    return cond


def secuencia_dias_perturbados(
    rng: np.random.Generator,
    n_dias: int,
    sigma_tmin: float = SIGMA_TMIN_C,
    sigma_tmax: float = SIGMA_TMAX_C,
    phi_tmin: float = PHI_TMIN,
    phi_tmax: float = PHI_TMAX,
    sigma_ea_frac: float = SIGMA_EA_RESID_FRAC,
    phi_ea: float = PHI_EA,
) -> list[CondicionesClimaticas]:
    """Secuencia de ``n_dias`` días con persistencia AR(1):

        a[d] = phi * a[d-1] + sqrt(1 - phi^2) * sigma * e[d],   e ~ N(0, 1)

    (la varianza estacionaria de a es sigma^2). Es la realización ambiental
    que reciben LAS TRES estrategias en una corrida Monte Carlo (diseño
    pareado). Parámetros de NASA POWER 2005-2024 (ver simplificación 3).
    """
    a = np.array([rng.normal(0.0, sigma_tmin), rng.normal(0.0, sigma_tmax), rng.normal(0.0, sigma_ea_frac)])
    phi = np.array([phi_tmin, phi_tmax, phi_ea])
    sig = np.array([sigma_tmin, sigma_tmax, sigma_ea_frac])
    dias = []
    for d in range(n_dias):
        if d > 0:
            a = phi * a + np.sqrt(1.0 - phi**2) * sig * rng.normal(0.0, 1.0, 3)
        dias.append(_dia_desde_anomalias(float(a[0]), float(a[1]), float(a[2])))
    return dias


def ambiente_en(t_h: float, clima_dias) -> tuple[float, float, float]:
    """(T_ambiente [°C], HR_ambiente [%], ea [kPa]) en el instante ``t_h``
    [h de proceso, t=0 a medianoche del día 0], usando una SECUENCIA de
    días de clima (``clima_dias``: lista de CondicionesClimaticas, p. ej.
    una realización Monte Carlo de ``condiciones_perturbadas``). Si el
    proceso dura más días que la secuencia, se repite cíclicamente.

    Pensada para que las TRES estrategias reciban exactamente la misma
    realización ambiental (diseño pareado, ver
    metodologia_estadistica_monte_carlo.md).
    """
    cond = clima_dias[int(t_h // 24.0) % len(clima_dias)]
    h = np.asarray([t_h % 24.0])
    return (
        float(temperatura(h, cond)[0]),
        float(humedad_relativa(h, cond)[0]),
        float(cond.ea_kpa),
    )


HORA_AMANECER = 6.0
HORA_OCASO = 18.0
"""Horas de sol aproximadas para Chinchina (~5 N): ~12 h de luz todo el
año por la cercanía al ecuador. Aproximación del modelo."""


def incremento_solar(t_horas: np.ndarray, dt_max_c: float) -> np.ndarray:
    """Incremento de temperatura por radiación solar sobre la ambiente [°C].

    Perfil de medio seno entre ``HORA_AMANECER`` y ``HORA_OCASO`` con
    máximo ``dt_max_c`` al mediodía y 0 de noche. Se usa para representar,
    de forma concentrada (lumped), el calentamiento del grano en patio o
    del aire en la cámara del secador solar activo (ver
    escenario_sol_abierto.py y linea_base_activa.py). ``dt_max_c`` NO es
    un dato climático: es un parámetro de cada estrategia, calibrado
    contra literatura en su módulo correspondiente.
    """
    h = np.asarray(t_horas, dtype=float) % 24.0
    dia = (h >= HORA_AMANECER) & (h <= HORA_OCASO)
    fase = np.pi * (h - HORA_AMANECER) / (HORA_OCASO - HORA_AMANECER)
    return np.where(dia, dt_max_c * np.sin(fase), 0.0)


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

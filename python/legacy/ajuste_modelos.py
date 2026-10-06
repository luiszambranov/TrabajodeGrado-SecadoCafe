"""
ajuste_modelos.py
==================

Ajuste de los modelos candidatos de cinética de secado (Newton,
Logarítmico, Midilli modificado — ver modelo_secado.py) contra una curva
de referencia, con las métricas de error RMSE, MAE y R².
Semana 5 - "Modelo base validado".

Metodología y honestidad de los datos usados
---------------------------------------------
El paper de referencia del proyecto (Phitakwinai, Thepa & Nilnont, 2019,
ver docs/matriz_comparativa_modelos.md) no publica una tabla de puntos
crudos (tiempo, humedad); publica los PARÁMETROS YA AJUSTADOS de 9
modelos bajo 9 condiciones de secado (su Tabla 2, digitalizada en
data/reference/phitakwinai_2019_tabla2_parametros.csv), con r² y RMSE
reportados por los propios autores.

Para no inventar datos ni depender de una digitalización manual (pixel a
pixel) de su Figura 2/3 -que sería imprecisa y difícil de defender en un
trabajo de grado-, este módulo genera la CURVA DE REFERENCIA evaluando
la ecuación Modified-Midilli que los autores ya ajustaron y validaron
(r² = 0.9997, RMSE = 2.323 %) para T = 60 °C, RH = 20 %, y ajusta contra
esa curva nuestras propias implementaciones de los tres modelos
candidatos. Esto es explícitamente una reproducción de la curva de
literatura (no un experimento propio), y así debe citarse en el
documento. El pipeline de ajuste (funciones ``ajustar_modelo`` y las
métricas) es genérico: el día que se consiga o digitalice un dataset de
puntos crudos propios (línea base física, u otra fuente), se usa
exactamente el mismo código sin cambios.

Convención de unidades: igual que modelo_secado.py (t en horas, MR
adimensional). Este módulo trabaja en el espacio de MR porque es en MR
donde el paper reporta sus métricas y donde tiene sentido comparar
modelos con distinta escala de humedad.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Tuple

import numpy as np
from scipy.optimize import curve_fit

from modelo_secado import (
    ParametrosLogaritmico,
    ParametrosMidilliModificado,
    ParametrosNewton,
    mr_logaritmico,
    mr_midilli_modificado,
    mr_newton,
)


# ---------------------------------------------------------------------------
# Curva de referencia: ecuación Modified-Midilli publicada por Phitakwinai
# et al. (2019) para T=60 C, RH=20 % (fila con mejor r^2 de su Tabla 2).
# ---------------------------------------------------------------------------

# Parámetros EXACTOS de la Tabla 2 del paper (no ajustados por nosotros).
K_REF = 0.121461      # 1/h^n
N_REF = 1.179043      # -
B_REF = 0.001722      # 1/h
# a = 1 fijo en el modelo Modified-Midilli del paper (ver Tabla 1 y README
# de data/reference/).
R2_REPORTADO = 0.9997
RMSE_REPORTADO_PCT = 2.323  # %, tal como reportado por los autores


def mr_referencia(t: np.ndarray) -> np.ndarray:
    """MR(t) según la ecuación Modified-Midilli publicada (T=60C, RH=20%).

    Esta es la curva de "literatura" contra la que se validan nuestros
    modelos candidatos. Ver el docstring del módulo para la justificación
    de por qué se usa la ecuación publicada y no una digitalización de
    figura.
    """
    return np.exp(-K_REF * t**N_REF) + B_REF * t


def generar_dataset_referencia(t: np.ndarray) -> Dict[str, np.ndarray]:
    """Genera el dataset (t, MR) de referencia para el ajuste.

    Se muestrea cada 1 h, igual que el intervalo de registro del paper
    ("the mass ... was recorded ... at an interval of 1 hr").
    """
    return {"t": np.asarray(t, dtype=float), "MR": mr_referencia(np.asarray(t, dtype=float))}


# ---------------------------------------------------------------------------
# Métricas de error (definiciones de las ecuaciones 3 y 4 del paper, más
# MAE, que el checklist de la guía operativa pide adicionalmente)
# ---------------------------------------------------------------------------

def r2_score(mr_obs: np.ndarray, mr_pred: np.ndarray) -> float:
    """Coeficiente de determinación R^2 = 1 - SS_res / SS_tot."""
    mr_obs = np.asarray(mr_obs, dtype=float)
    mr_pred = np.asarray(mr_pred, dtype=float)
    ss_res = np.sum((mr_obs - mr_pred) ** 2)
    ss_tot = np.sum((mr_obs - np.mean(mr_obs)) ** 2)
    return 1.0 - ss_res / ss_tot


def rmse(mr_obs: np.ndarray, mr_pred: np.ndarray) -> float:
    """Raíz del error cuadrático medio (ecuación 4 del paper), en MR."""
    mr_obs = np.asarray(mr_obs, dtype=float)
    mr_pred = np.asarray(mr_pred, dtype=float)
    return float(np.sqrt(np.mean((mr_pred - mr_obs) ** 2)))


def mae(mr_obs: np.ndarray, mr_pred: np.ndarray) -> float:
    """Error absoluto medio, en MR."""
    mr_obs = np.asarray(mr_obs, dtype=float)
    mr_pred = np.asarray(mr_pred, dtype=float)
    return float(np.mean(np.abs(mr_pred - mr_obs)))


@dataclass
class ResultadoAjuste:
    modelo: str
    parametros: dict
    r2: float
    rmse: float
    mae: float


# ---------------------------------------------------------------------------
# Ajuste no lineal de cada modelo candidato contra un dataset (t, MR)
# ---------------------------------------------------------------------------

def _ajustar_newton(t: np.ndarray, mr: np.ndarray) -> ResultadoAjuste:
    f = lambda t, k: mr_newton(t, ParametrosNewton(k=k))
    (k,), _ = curve_fit(f, t, mr, p0=[0.1])
    pred = f(t, k)
    return ResultadoAjuste(
        "Newton", {"k": k}, r2_score(mr, pred), rmse(mr, pred), mae(mr, pred)
    )


def _ajustar_logaritmico(t: np.ndarray, mr: np.ndarray) -> ResultadoAjuste:
    f = lambda t, a, k, c: mr_logaritmico(t, ParametrosLogaritmico(a=a, k=k, c=c))
    (a, k, c), _ = curve_fit(f, t, mr, p0=[1.0, 0.1, 0.0], maxfev=10000)
    pred = f(t, a, k, c)
    return ResultadoAjuste(
        "Logaritmico",
        {"a": a, "k": k, "c": c},
        r2_score(mr, pred),
        rmse(mr, pred),
        mae(mr, pred),
    )


def _ajustar_midilli_modificado(t: np.ndarray, mr: np.ndarray) -> ResultadoAjuste:
    # a=1 fijo, replicando la definición del modelo tal como la usa el
    # paper de referencia (ver docstring del módulo).
    f = lambda t, k, n, b: mr_midilli_modificado(
        t, ParametrosMidilliModificado(a=1.0, k=k, n=n, b=b)
    )
    (k, n, b), _ = curve_fit(f, t, mr, p0=[0.1, 1.0, 0.0], maxfev=10000)
    pred = f(t, k, n, b)
    return ResultadoAjuste(
        "Midilli_modificado",
        {"a": 1.0, "k": k, "n": n, "b": b},
        r2_score(mr, pred),
        rmse(mr, pred),
        mae(mr, pred),
    )


AJUSTADORES: Dict[str, Callable[[np.ndarray, np.ndarray], ResultadoAjuste]] = {
    "Newton": _ajustar_newton,
    "Logaritmico": _ajustar_logaritmico,
    "Midilli_modificado": _ajustar_midilli_modificado,
}


def ajustar_todos(t: np.ndarray, mr: np.ndarray) -> Dict[str, ResultadoAjuste]:
    """Ajusta los tres modelos candidatos contra el dataset (t, MR) dado.

    Retorna un diccionario nombre_modelo -> ResultadoAjuste, listo para
    tabular y comparar por RMSE/MAE/R².
    """
    return {nombre: fn(t, mr) for nombre, fn in AJUSTADORES.items()}


if __name__ == "__main__":
    t = np.arange(0, 27, 1.0)  # 0..26 h, igual que el eje de tiempo del paper
    ds = generar_dataset_referencia(t)

    print(
        "Dataset de referencia: ecuacion Modified-Midilli publicada "
        f"(T=60C, RH=20%), r2 reportado={R2_REPORTADO}, "
        f"RMSE reportado={RMSE_REPORTADO_PCT}%\n"
    )

    resultados = ajustar_todos(ds["t"], ds["MR"])
    for nombre, r in resultados.items():
        params_fmt = ", ".join(f"{k}={v:.5f}" for k, v in r.parametros.items())
        print(f"{nombre:20s} R2={r.r2:.5f}  RMSE={r.rmse:.5f}  MAE={r.mae:.5f}  [{params_fmt}]")

    print(
        "\nComprobacion: el ajuste de Midilli_modificado debe recuperar "
        f"aprox. k={K_REF}, n={N_REF}, b={B_REF} (los mismos valores "
        "publicados, ya que el dataset se generó con esa misma ecuación)."
    )

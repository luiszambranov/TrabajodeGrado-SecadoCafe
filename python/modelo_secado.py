"""
modelo_secado.py
=================

Modelo Python v0.1 de cinética de secado en capa delgada para café.
Trabajo de grado - Sistema de supervisión digital para el secado de café.
Semana 5 - "Modelo base validado" (ver Guia_operativa_TG_Pardo_Zambrano.pdf).

Alcance de esta versión (v0.1)
-------------------------------
Este módulo define la ESTRUCTURA MATEMÁTICA y las UNIDADES de los tres
modelos de cinética de secado seleccionados en
``docs/matriz_comparativa_modelos.md``:

    - Newton              (referencia mínima / peor ajuste esperado)
    - Logarítmico         (candidato para la línea base activa, secado
                            solar con temperatura ambiente variable)
    - Midilli modificado  (candidato principal, temperatura y HR
                            controladas; ya validado en el anteproyecto
                            vía Phitakwinai et al., 2019)

Los parámetros por defecto de cada modelo son PRELIMINARES: solo sirven
para poder generar y graficar una curva de secado plausible. No han sido
ajustados contra ningún dataset. El ajuste real (RMSE, MAE, R² contra el
dataset de referencia de Phitakwinai et al., 2019 en ``data/reference/``)
es el SIGUIENTE entregable de la semana 5 y se hará en un módulo aparte
(``ajuste_modelos.py``), que reemplazará estos valores por defecto por los
parámetros ajustados y reportará las métricas de error.

Convención de unidades (fijada para todo el proyecto)
------------------------------------------------------
    t   : tiempo de secado                          [h]   (horas)
    M   : contenido de humedad, base húmeda          [%]   (0-100)
    M0  : contenido de humedad inicial, base húmeda  [%]
    Me  : contenido de humedad de equilibrio, b.h.   [%]
    MR  : razón de humedad (adimensional)            [-]
          MR(t) = (M(t) - Me) / (M0 - Me)

Se usa base húmeda en % porque es la convención de los estudios de
café citados en la matriz comparativa y porque es directamente medible
en campo (báscula + horno) sin requerir masa seca de referencia. Si en
semanas posteriores se digitaliza un dataset en base seca, debe
convertirse a base húmeda antes de usar este módulo (o documentarse
explícitamente el cambio de convención).

Referencias
-----------
Ver docs/matriz_comparativa_modelos.md y docs/seleccion_lineas_base.md
para las fuentes bibliográficas de cada modelo y de los rangos de
variables ambientales.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Dict

import numpy as np


# ---------------------------------------------------------------------------
# Condiciones de secado (comunes a todos los modelos)
# ---------------------------------------------------------------------------

@dataclass
class CondicionesSecado:
    """Condiciones de humedad que fijan la escala física de la curva.

    Atributos
    ---------
    M0 : float
        Humedad inicial, base húmeda [%]. Valor preliminar: 50 %,
        orden de magnitud típico de café pergamino recién despulpado
        (rango usual reportado en la literatura: 45-60 % b.h.).
        PENDIENTE de reemplazar por el valor medido/reportado en el
        dataset de referencia que se digitalice en data/reference/.
    Me : float
        Humedad de equilibrio, base húmeda [%]. Valor preliminar: 12 %,
        objetivo típico de humedad comercial del café pergamino/almendra
        (11-13 % b.h.). PENDIENTE de confirmar contra literatura o norma
        (NTC/ICO) citada en el documento final.
    """

    M0: float = 50.0
    Me: float = 12.0


# ---------------------------------------------------------------------------
# Parámetros de cada modelo (dataclasses documentadas con unidades)
# ---------------------------------------------------------------------------

@dataclass
class ParametrosNewton:
    """Parámetros del modelo de Newton: MR(t) = exp(-k*t)

    k : float
        Constante de secado [1/h]. Valor preliminar: 0.08 1/h (orden de
        magnitud usado en la primera curva exploratoria del proyecto,
        commit "Primera curva de sacado"). Es el único parámetro del
        modelo; según la matriz comparativa, Newton es consistentemente
        el peor ajuste reportado para café (R² desde 0.88), por lo que
        se mantiene solo como referencia mínima de comparación.
    """

    k: float = 0.08  # 1/h


@dataclass
class ParametrosLogaritmico:
    """Parámetros del modelo Logarítmico: MR(t) = a*exp(-k*t) + c

    ADVERTENCIA sobre el caso trivial: si a=1 y c=0, el modelo se reduce
    matemáticamente a Newton (curvas idénticas, no un error de código).
    Para que el v0.1 muestre una forma distinguible mientras se hace el
    ajuste real, se usa a+c=1 (así MR(0)=1, es decir M(0)=M0 se preserva)
    pero con a != 1 y c != 0, de forma arbitraria/ilustrativa.

    a : float
        Factor de amplitud [-]. Valor preliminar: 1.02.
    k : float
        Constante de secado [1/h]. Valor preliminar: 0.082 1/h, mismo
        orden de magnitud que Newton como punto de partida del ajuste.
    c : float
        Término de offset [-]. Valor preliminar: -0.02 (junto con a=1.02
        mantiene MR(0)=a+c=1, es decir M(0)=M0). Según
        docs/matriz_comparativa_modelos.md, este término es el que
        parece capturar la variabilidad de temperatura ambiente en
        secado solar (Icaro, R² = 0.984 reportado), relevante para nuestra
        línea base activa.
    """

    a: float = 1.02  # -
    k: float = 0.082  # 1/h
    c: float = -0.02  # -


@dataclass
class ParametrosMidilliModificado:
    """Parámetros de Midilli modificado: MR(t) = a*exp(-k*t^n) + b*t

    ADVERTENCIA sobre el caso trivial: si n=1 y b=0, el modelo se reduce
    matemáticamente a Newton (curvas idénticas, no un error de código).
    Para que el v0.1 muestre una forma distinguible mientras se hace el
    ajuste real, se aparta n de 1 y se usa un b pequeño y negativo
    (orden de magnitud reportado en literatura de café bajo temperatura
    controlada), de forma arbitraria/ilustrativa; a se deja en 1 para
    que MR(0)=a=1, es decir M(0)=M0 se preserve.

    a : float
        Factor de amplitud [-]. Valor preliminar: 1.0 (fijo para
        preservar MR(0)=1).
    k : float
        Constante de secado [1/h^n] (nótese que la unidad depende de n
        porque multiplica a t^n). Valor preliminar: 0.09.
    n : float
        Exponente adimensional [-] que captura desviaciones del
        comportamiento exponencial simple (difusión, geometría de la
        partícula). Valor preliminar: 1.1 (deliberadamente != 1 para
        no coincidir con Newton; ver advertencia arriba).
    b : float
        Coeficiente lineal [1/h]. Valor preliminar: -0.0001 (pequeño y
        negativo, deliberadamente != 0; ver advertencia arriba). Modelo
        ya validado en el anteproyecto para café pergamino bajo
        temperatura y HR controladas (Phitakwinai et al., 2019,
        R² = 0.9976, RMSE = 6.65 %), por lo que es el candidato
        principal a ajustar.
    """

    a: float = 1.0  # -
    k: float = 0.09  # 1/h^n
    n: float = 1.1  # -
    b: float = -0.0001  # 1/h


# ---------------------------------------------------------------------------
# Modelos de razón de humedad MR(t)
# ---------------------------------------------------------------------------

def mr_newton(t: np.ndarray, p: ParametrosNewton) -> np.ndarray:
    """Razón de humedad según el modelo de Newton.

    Parámetros
    ----------
    t : np.ndarray
        Tiempo [h].
    p : ParametrosNewton

    Retorna
    -------
    np.ndarray
        MR(t), adimensional, en el rango teórico (0, 1].
    """
    return np.exp(-p.k * t)


def mr_logaritmico(t: np.ndarray, p: ParametrosLogaritmico) -> np.ndarray:
    """Razón de humedad según el modelo Logarítmico.

    Parámetros
    ----------
    t : np.ndarray
        Tiempo [h].
    p : ParametrosLogaritmico

    Retorna
    -------
    np.ndarray
        MR(t), adimensional.
    """
    return p.a * np.exp(-p.k * t) + p.c


def mr_midilli_modificado(t: np.ndarray, p: ParametrosMidilliModificado) -> np.ndarray:
    """Razón de humedad según el modelo Midilli modificado.

    Parámetros
    ----------
    t : np.ndarray
        Tiempo [h].
    p : ParametrosMidilliModificado

    Retorna
    -------
    np.ndarray
        MR(t), adimensional.
    """
    return p.a * np.exp(-p.k * t**p.n) + p.b * t


# Registro de modelos disponibles: nombre -> (función MR, clase de parámetros)
# Se usa en el notebook y, más adelante, en el ajuste (ajuste_modelos.py) para
# iterar sobre los tres modelos sin duplicar código.
MODELOS: Dict[str, Callable] = {
    "Newton": mr_newton,
    "Logaritmico": mr_logaritmico,
    "Midilli_modificado": mr_midilli_modificado,
}

PARAMETROS_POR_DEFECTO: Dict[str, object] = {
    "Newton": ParametrosNewton(),
    "Logaritmico": ParametrosLogaritmico(),
    "Midilli_modificado": ParametrosMidilliModificado(),
}


# ---------------------------------------------------------------------------
# Conversión MR <-> contenido de humedad
# ---------------------------------------------------------------------------

def mr_a_humedad(mr: np.ndarray, cond: CondicionesSecado) -> np.ndarray:
    """Convierte razón de humedad MR a contenido de humedad M [% b.h.].

    M(t) = Me + MR(t) * (M0 - Me)
    """
    return cond.Me + mr * (cond.M0 - cond.Me)


def humedad_a_mr(m: np.ndarray, cond: CondicionesSecado) -> np.ndarray:
    """Convierte contenido de humedad M [% b.h.] a razón de humedad MR.

    Función inversa de :func:`mr_a_humedad`. Útil para transformar un
    dataset de literatura (M vs. t) a MR antes de ajustar los modelos.
    """
    return (np.asarray(m) - cond.Me) / (cond.M0 - cond.Me)


# ---------------------------------------------------------------------------
# Curva de secado completa (tiempo -> humedad), para un modelo dado
# ---------------------------------------------------------------------------

def curva_secado(
    nombre_modelo: str,
    t: np.ndarray,
    cond: CondicionesSecado | None = None,
    params: object | None = None,
) -> Dict[str, np.ndarray]:
    """Genera la curva de secado completa para un modelo registrado.

    Parámetros
    ----------
    nombre_modelo : str
        Una de las claves de ``MODELOS`` (Newton, Logaritmico,
        Midilli_modificado).
    t : np.ndarray
        Vector de tiempo [h].
    cond : CondicionesSecado, opcional
        Si no se pasa, se usan los valores preliminares por defecto.
    params : dataclass de parámetros, opcional
        Si no se pasa, se usan los parámetros preliminares por defecto
        del modelo (ver docstrings de cada clase Parametros*).

    Retorna
    -------
    dict con:
        "t"  : tiempo [h]
        "MR" : razón de humedad [-]
        "M"  : contenido de humedad [% b.h.]
    """
    if nombre_modelo not in MODELOS:
        raise ValueError(
            f"Modelo '{nombre_modelo}' no reconocido. "
            f"Opciones: {list(MODELOS)}"
        )

    cond = cond or CondicionesSecado()
    params = params if params is not None else PARAMETROS_POR_DEFECTO[nombre_modelo]

    mr = MODELOS[nombre_modelo](np.asarray(t, dtype=float), params)
    m = mr_a_humedad(mr, cond)

    return {"t": np.asarray(t, dtype=float), "MR": mr, "M": m}


def resumen_parametros(nombre_modelo: str, params: object | None = None) -> dict:
    """Devuelve los parámetros de un modelo como diccionario, para
    imprimir/loguear junto con sus unidades documentadas en el docstring
    de la clase correspondiente. Útil para dejar registro explícito de
    qué parámetros se usaron al generar una figura o un dataset.
    """
    params = params if params is not None else PARAMETROS_POR_DEFECTO[nombre_modelo]
    return asdict(params)


if __name__ == "__main__":
    # Uso mínimo de ejemplo / smoke test manual.
    t = np.linspace(0, 50, 101)
    cond = CondicionesSecado()
    for nombre in MODELOS:
        curva = curva_secado(nombre, t, cond)
        print(nombre, resumen_parametros(nombre))
        print(
            f"  M(0) = {curva['M'][0]:.2f} %  ->  M(50h) = {curva['M'][-1]:.2f} %"
        )

"""
cinetica_dinamica.py
=====================

Extiende el modelo Midilli modificado de modelo_secado.py (validado de
forma ESTÁTICA para T/RH fijos en ajuste_modelos.py) a una forma que
puede integrarse paso a paso cuando T y RH cambian en el tiempo - como
va a pasar en la planta real, donde T_process/RH_process son la salida
de dinamica_termica.py y dependen de heater_cmd/fan_cmd.
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Por qué "tiempo equivalente" y no derivar dMR/dt directamente
-----------------------------------------------------------------
La ecuación de Midilli modificado, MR(t) = a*exp(-k*t^n) + b*t, está
publicada y validada (Phitakwinai et al., 2019) como función de un
tiempo "t" medido desde el inicio del secado BAJO CONDICIONES
CONSTANTES. Si T o RH cambian a mitad de proceso, ese "t" ya no tiene
un significado físico directo (no se puede simplemente seguir sumando
tiempo sobre la misma curva, porque la curva completa cambió).

El método de "tiempo equivalente" (de uso común para simular modelos de
capa delgada bajo condiciones variables, cuando no se dispone de un
modelo mecanístico de difusión completo) resuelve esto sin necesidad de
derivar la ecuación: en cada paso,

    1. Se calculan k, n, b para las condiciones ACTUALES (T_process,
       RH_process) con las ecuaciones generalizadas de la Tabla 3 de
       Phitakwinai et al. (2019).
    2. Se busca el tiempo "equivalente" t_eq tal que, bajo esas MISMAS
       condiciones, la curva ya publicada habría llegado al MR actual
       (MR(t_eq; k,n,b) = MR_actual). Esto "reubica" el estado actual
       sobre la curva correspondiente a las condiciones de este paso.
    3. Se avanza dt horas sobre ESA curva: MR_nuevo = MR(t_eq + dt; k,n,b).

Es una aproximación cuasi-estacionaria (asume que, en cada paso, la
cinética responde como si las condiciones actuales hubieran estado fijas
"desde siempre"), consistente con el nivel de modelo concentrado
(lumped) que ya fijó el proyecto para toda la planta (ver
docs/seleccion_lineas_base.md, sección "Modelo, no CFD"). Se documenta
aquí como una decisión de modelado explícita, a discutir con el asesor
si los perfiles térmicos objetivo cambian T/RH de forma muy abrupta.

Rango válido y extrapolación
--------------------------------
Las ecuaciones de la Tabla 3 son válidas para T: 50-70°C, RH: 10-30%
(rango experimental de Phitakwinai et al., 2019). Este módulo NO
detiene el cálculo fuera de ese rango (para no romper la simulación),
pero marca el resultado como ``fuera_de_rango=True`` para que quien lo
use decida qué hacer (recortar el perfil térmico al rango válido, o
documentar y justificar la extrapolación en el documento final).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

from modelo_secado import ParametrosMidilliModificado, mr_midilli_modificado

# --- Rango experimental valido de la Tabla 3 (Phitakwinai et al., 2019) ---
T_MIN_TABLA3_C = 50.0
T_MAX_TABLA3_C = 70.0
RH_MIN_TABLA3_PCT = 10.0
RH_MAX_TABLA3_PCT = 30.0

# Cota superior de busqueda de tiempo equivalente [h]. 200 h cubre con
# margen el orden de horas de la propuesta supervisada y de la linea
# base activa; revisar si se prueban escenarios mucho mas lentos.
T_EQ_BUSQUEDA_MAX_H = 200.0


def k_generalizado(t_c: float, rh_pct: float) -> float:
    """k(T,RH) del modelo Modified-Midilli generalizado (Tabla 3,
    Phitakwinai et al., 2019, r^2=0.9955)."""
    T, RH = t_c, rh_pct
    return (
        -0.41202 + 0.014457 * T - 6.3162e-4 * RH + 1.0318e-4 * T * RH
        - 8.8133e-5 * T**2 - 2.4318e-5 * RH**2
    )


def n_generalizado(t_c: float, rh_pct: float) -> float:
    """n(T,RH) del modelo Modified-Midilli generalizado (Tabla 3,
    Phitakwinai et al., 2019, r^2=0.9856)."""
    T, RH = t_c, rh_pct
    return (
        2.19467 - 0.033121 * T + 0.001747 * RH - 3.56e-4 * T * RH
        + 3.27e-4 * T**2 + 4.7e-4 * RH**2
    )


def b_generalizado(t_c: float, rh_pct: float) -> float:
    """b(T,RH) del modelo Modified-Midilli generalizado (Tabla 3,
    Phitakwinai et al., 2019, r^2=0.9660)."""
    T, RH = t_c, rh_pct
    return (
        -0.01318 + 5.5127e-4 * T - 1.3408e-4 * RH + 1.7094e-7 * T * RH
        - 4.7207e-6 * T**2 + 3.635e-6 * RH**2
    )


@dataclass
class ResultadoPasoMR:
    mr_nuevo: float
    t_eq_h: float
    params: ParametrosMidilliModificado
    fuera_de_rango: bool


def parametros_generalizados(t_c: float, rh_pct: float) -> tuple[ParametrosMidilliModificado, bool]:
    """Evalua k,n,b (Tabla 3) para las condiciones (T,RH) actuales.

    Retorna (parametros, fuera_de_rango). ``a`` queda fijo en 1.0, igual
    que en el modelo del paper (ver data/reference/README.md).
    """
    fuera_de_rango = not (
        T_MIN_TABLA3_C <= t_c <= T_MAX_TABLA3_C
        and RH_MIN_TABLA3_PCT <= rh_pct <= RH_MAX_TABLA3_PCT
    )
    params = ParametrosMidilliModificado(
        a=1.0,
        k=k_generalizado(t_c, rh_pct),
        n=n_generalizado(t_c, rh_pct),
        b=b_generalizado(t_c, rh_pct),
    )
    return params, fuera_de_rango


def tiempo_equivalente(
    mr_objetivo: float, params: ParametrosMidilliModificado, n_muestras: int = 400
) -> float:
    """Busca t_eq tal que mr_midilli_modificado(t_eq, params) == mr_objetivo.

    MR(0)=a=1 y MR decrece con t en la parte fisicamente relevante de la
    curva, pero OJO: con b>0 (como el b_ref=0.001722 reportado por
    Phitakwinai et al., 2019 -- ver ajuste_modelos.py) el termino b*t
    hace que, para t suficientemente grande, MR vuelva a CRECER (la
    ecuacion, tomada fuera de su rango de ajuste original, implica una
    "rehumidificacion" que no tiene sentido fisico). Esto vuelve la
    funcion NO monotona en la ventana de busqueda, asi que no basta con
    mirar el signo en los dos extremos [0, T_EQ_BUSQUEDA_MAX_H] (puede
    dar positivo en ambos y saltarse una raiz real en el medio -- ver
    commit donde se detecto este bug con el smoke test del modulo).

    En su lugar se muestrea la ventana completa y se toma el PRIMER
    cambio de signo (el t mas pequeno), que es la interpretacion
    fisicamente correcta: "la primera vez que la curva llega a este
    MR", no una coincidencia posterior por el repunte de b*t. Si no hay
    ningun cambio de signo en la ventana, se satura al punto muestreado
    mas cercano al objetivo (mr_objetivo queda fuera de lo que esta
    curva puede representar en [0, T_EQ_BUSQUEDA_MAX_H]).

    Limitacion a documentar en el trabajo si se confirma en la practica:
    esta no-monotonia es una propiedad de la ecuacion publicada con b>0,
    no un error de esta implementacion; si el perfil termico simulado
    pasa horas suficientes cerca de MR bajo, revisar si conviene truncar
    el modelo en el primer minimo de MR(t) en vez de dejarlo "repuntar".
    """
    if abs(mr_objetivo - 1.0) < 1e-9:
        return 0.0

    ts = np.linspace(0.0, T_EQ_BUSQUEDA_MAX_H, n_muestras)
    f_ts = mr_midilli_modificado(ts, params) - mr_objetivo

    cambios = np.where(np.diff(np.sign(f_ts)) != 0)[0]
    if len(cambios) == 0:
        return float(ts[int(np.argmin(np.abs(f_ts)))])

    i = int(cambios[0])
    f = lambda t: float(mr_midilli_modificado(np.asarray([t]), params)[0]) - mr_objetivo
    return brentq(f, float(ts[i]), float(ts[i + 1]))


def paso_mr(mr_actual: float, t_process_c: float, rh_process_pct: float, dt_h: float) -> ResultadoPasoMR:
    """Avanza la razon de humedad MR un paso ``dt_h`` [h], con las
    condiciones ACTUALES de proceso (T_process, RH_process), usando el
    metodo de tiempo equivalente (ver docstring del modulo).
    """
    params, fuera_de_rango = parametros_generalizados(t_process_c, rh_process_pct)
    t_eq = tiempo_equivalente(mr_actual, params)
    mr_nuevo = float(mr_midilli_modificado(np.asarray([t_eq + dt_h]), params)[0])
    # MR es una razon de humedad: no tiene sentido fuera de [0,1] aunque
    # el termino b*t del modelo pueda empujarlo levemente fuera para t
    # grande (ver B_REF positivo en ajuste_modelos.py) - se recorta como
    # salvaguarda numerica, no como afirmacion fisica.
    mr_nuevo = float(np.clip(mr_nuevo, 0.0, 1.0))
    return ResultadoPasoMR(mr_nuevo=mr_nuevo, t_eq_h=t_eq, params=params, fuera_de_rango=fuera_de_rango)


if __name__ == "__main__":
    # Smoke test: condiciones fijas dentro del rango de la Tabla 3 deben
    # reproducir (aprox.) la misma curva que mr_midilli_modificado
    # directo -- es el chequeo de consistencia que se debe repetir de
    # forma mas rigurosa (Etapa 5 del plan) antes de conectar a CODESYS.
    mr = 1.0
    T_FIJA, RH_FIJA = 60.0, 20.0
    dt_h = 1.0
    print(f"Paso a paso (T={T_FIJA}C, RH={RH_FIJA}% fijos, dt={dt_h}h):")
    for i in range(10):
        r = paso_mr(mr, T_FIJA, RH_FIJA, dt_h)
        mr = r.mr_nuevo
        print(
            f"  t~{(i + 1) * dt_h:5.1f} h   MR={mr:.4f}   t_eq={r.t_eq_h:.3f} h   "
            f"fuera_de_rango={r.fuera_de_rango}"
        )

    print("\nComparacion directa (mr_midilli_modificado evaluado de una vez, mismas T/RH):")
    from modelo_secado import mr_midilli_modificado as _mr_directo

    params_ref, _ = parametros_generalizados(T_FIJA, RH_FIJA)
    t_arr = np.arange(1, 11) * dt_h
    mr_directo = _mr_directo(t_arr, params_ref)
    for t_i, mr_i in zip(t_arr, mr_directo):
        print(f"  t={t_i:5.1f} h   MR={mr_i:.4f}")

"""
lineas_base_v01.py  (LEGADO - no se usa en los resultados)
===========================================================

Versiones v0.1 (semana 5, sept 2026) de las dos lineas base, retiradas de
``escenario_sol_abierto.py`` y ``linea_base_activa.py`` el 6 oct 2026:

- Patio: modelo de Newton, MR = exp(-k t), con k calibrado en 2 puntos
  contra Eliseu (2008): T = 26.3 C, HR = 63.3 %, 117.5 h hasta MR = 0.05.
- Solar activa: modelo Logaritmico con los parametros publicados por
  Mackpayen et al. (2017) para el secador solar Icaro mejorado
  (tiempo del articulo en minutos, convertido a horas).

Por que se retiraron: ninguno de los dos responde a la temperatura ni a la
humedad del aire, asi que no pueden recibir el clima de Chinchina ni sus
perturbaciones (Monte Carlo). Desde el 29 sept 2026 las tres estrategias
usan el modelo unico de Roa-Cenicafe (``cinetica_roa.py``). Ver
docs/evolucion_del_modelo.md.

Fuentes: data/reference/eliseu_2008_secado_patio.md y
data/reference/mackpayen_2017_icaro_dryer.md.
Para ejecutarlo: desde python/legacy/ (importa modelo_secado.py de esta
misma carpeta).
"""

from __future__ import annotations

import math

import numpy as np

# ---------------------------------------------------------------------------
# Patio v0.1 (antes en escenario_sol_abierto.py)
# ---------------------------------------------------------------------------
T_AMBIENTE_MEDIA_C = 26.3
HR_AMBIENTE_MEDIA_PCT = 63.3
TIEMPO_TOTAL_SECADO_H = 117.5  # ~4.9 dias
MR_PRACTICAMENTE_SECO = 0.05   # convencion asumida (ver docstring)

K_SOL_ABIERTO = -math.log(MR_PRACTICAMENTE_SECO) / TIEMPO_TOTAL_SECADO_H  # 1/h

from modelo_secado import ParametrosNewton, mr_newton


PARAMETROS_SOL_ABIERTO = ParametrosNewton(k=K_SOL_ABIERTO)


def mr_sol_abierto(t: np.ndarray) -> np.ndarray:
    """Razón de humedad MR(t) de la línea base mínima (Newton, k calibrado).

    Válido como aproximación hasta ~117.5 h (tiempo total reportado en la
    fuente); más allá, MR sigue decayendo asintóticamente hacia 0 sin un
    límite físico explícito en este modelo simplificado.
    """
    return mr_newton(np.asarray(t, dtype=float), PARAMETROS_SOL_ABIERTO)



# ---------------------------------------------------------------------------
# Solar activa v0.1 (antes en linea_base_activa.py)
# ---------------------------------------------------------------------------
from modelo_secado import ParametrosLogaritmico, mr_logaritmico

# --- Parámetros de Mackpayen et al. (2017), convertidos a 1/h ---
K_PAPER_POR_MIN = 0.0031
PARAMETROS_LINEA_ACTIVA = ParametrosLogaritmico(
    a=1.1274,
    k=K_PAPER_POR_MIN * 60.0,  # -> 1/h
    c=-0.1780,
)

# Condiciones del experimento fuente (para referencia/trazabilidad)
T_CAMARA_EQUILIBRIO_C = 54.0   # rango reportado: 50-60 C
VELOCIDAD_AIRE_MS = 1.5
TIEMPO_MAXIMO_AJUSTE_H = 500.0 / 60.0  # ~8.3 h (0-500 min en el paper)


def mr_linea_base_activa(t: np.ndarray) -> np.ndarray:
    """Razón de humedad MR(t) de la línea base activa (modelo Logarítmico,
    parámetros de Mackpayen et al. 2017, t en horas).

    Válido con confianza hasta ~8.3 h (rango del ajuste original); fuera
    de ese rango es extrapolación.
    """
    return mr_logaritmico(np.asarray(t, dtype=float), PARAMETROS_LINEA_ACTIVA)



if __name__ == "__main__":
    t = np.linspace(0, TIEMPO_TOTAL_SECADO_H, 6)
    print("Patio v0.1 (Newton):", np.round(mr_sol_abierto(t), 3))
    t = np.linspace(0, TIEMPO_MAXIMO_AJUSTE_H, 6)
    print("Activa v0.1 (Logaritmico):", np.round(mr_linea_base_activa(t), 3))

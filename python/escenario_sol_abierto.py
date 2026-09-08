"""
escenario_sol_abierto.py
==========================

Línea base mínima: secado tradicional al sol en patio, lazo abierto, sin
control activo del perfil térmico (ver docs/seleccion_lineas_base.md).
Semana 5 - "Modelo base validado".

Modelo usado: Newton (`MR = exp(-k*t)`), el modelo mínimo de referencia
del proyecto (ver docs/matriz_comparativa_modelos.md: "modelo más
simple, útil como referencia mínima"), apropiado para un proceso sin
control activo.

Calibración de k
------------------
NO se usan coeficientes de un ajuste completo (no se consiguió
verificar la tabla de parámetros del paper de referencia, ver
data/reference/eliseu_2008_secado_patio.md). En su lugar se calibra k
con las condiciones generales reportadas para secado en patio de café
(T=26.3°C, RH=63.3%, tiempo total=117.5 h), asumiendo que ese tiempo
total corresponde al punto en que MR≈0.05 ("prácticamente seco", una
convención común en la literatura de cinética de secado):

    k = -ln(0.05) / 117.5 h = 0.0255 1/h

Esto es una calibración de 2 puntos a un resumen de literatura, no un
reajuste de datos punto a punto. Ver el .md de referencia para el
detalle completo y la limitación explícita.

Diferencia esperada frente a las otras dos estrategias
---------------------------------------------------------
Esta línea base mínima seca en el orden de días (k pequeño), mientras la
línea base activa (`linea_base_activa.py`) y la propuesta supervisada
secan en el orden de horas. Esta diferencia de orden de magnitud es una
primera validación de sentido común de los tres modelos.
"""

from __future__ import annotations

import math

import numpy as np

from modelo_secado import ParametrosNewton, mr_newton

# --- Condiciones de referencia (secado en patio, ver .md de referencia) ---
T_AMBIENTE_MEDIA_C = 26.3
HR_AMBIENTE_MEDIA_PCT = 63.3
TIEMPO_TOTAL_SECADO_H = 117.5  # ~4.9 dias
MR_PRACTICAMENTE_SECO = 0.05   # convencion asumida (ver docstring)

K_SOL_ABIERTO = -math.log(MR_PRACTICAMENTE_SECO) / TIEMPO_TOTAL_SECADO_H  # 1/h

PARAMETROS_SOL_ABIERTO = ParametrosNewton(k=K_SOL_ABIERTO)


def mr_sol_abierto(t: np.ndarray) -> np.ndarray:
    """Razón de humedad MR(t) de la línea base mínima (Newton, k calibrado).

    Válido como aproximación hasta ~117.5 h (tiempo total reportado en la
    fuente); más allá, MR sigue decayendo asintóticamente hacia 0 sin un
    límite físico explícito en este modelo simplificado.
    """
    return mr_newton(np.asarray(t, dtype=float), PARAMETROS_SOL_ABIERTO)


if __name__ == "__main__":
    print(f"k calibrado: {K_SOL_ABIERTO:.5f} 1/h "
          f"(secado total asumido en {TIEMPO_TOTAL_SECADO_H} h)")
    t = np.linspace(0, TIEMPO_TOTAL_SECADO_H, 10)
    for ti, mri in zip(t, mr_sol_abierto(t)):
        dias = ti / 24
        print(f"  t={ti:6.1f} h ({dias:4.1f} d)   MR={mri:.4f}")

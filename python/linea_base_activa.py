"""
linea_base_activa.py
=====================

Línea base activa: secado solar activo con ventilación forzada (ver
docs/seleccion_lineas_base.md). Semana 5 - "Modelo base validado".

Modelo usado: Logarítmico, con los parámetros YA AJUSTADOS y publicados
por Mackpayen et al. (2017) para un secador solar de convección forzada
(secador Icaro mejorado) — mismo principio físico que nuestra línea base
activa (placa absorbedora + ventiladores). Es el modelo con mejor ajuste
reportado por esos autores entre los cuatro que probaron (R²=0.984).
Ver data/reference/mackpayen_2017_icaro_dryer.md para el detalle
completo de la fuente y la verificación de estos parámetros.

Importante sobre unidades
--------------------------
El paper de Mackpayen et al. define el tiempo en MINUTOS. Este módulo
sigue la convención del resto del proyecto (tiempo en HORAS, ver
modelo_secado.py) y por eso k se reporta ya convertido:

    k [1/h] = k_paper [1/min] * 60 = 0.0031 * 60 = 0.186 1/h

a y c son adimensionales y no cambian con la conversión.

Limitaciones explícitas (v0.1)
--------------------------------
1. El paper no aclara si M0=70% / Me=12.5% son en base húmeda o base
   seca. Por eso esta función trabaja en el espacio de MR (adimensional,
   sin ambigüedad de convención) y NO convierte a humedad absoluta M(t)
   por defecto; quien la use puede pasar sus propios M0/Me una vez se
   confirme la convención (con el asesor o con literatura adicional).
2. Los parámetros fueron ajustados para un secador con placa absorbedora
   inclinada + cubierta de vidrio que alcanza una temperatura de cámara
   de equilibrio ≈54°C — más alta que la de un diseño de invernadero/
   túnel solar simple sin concentración (ver
   docs/seleccion_lineas_base.md, incrementos de 1-25°C sobre ambiente
   según Meja et al./Duque-Dussán et al.). Se usa como la mejor
   aproximación disponible con parámetros reales y verificados para
   secado solar activo; si el diseño final de la línea base activa del
   proyecto resulta térmicamente muy distinto (p. ej. sin concentrador),
   este ajuste debería revisarse con el asesor.
"""

from __future__ import annotations

import numpy as np

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
    t = np.linspace(0, TIEMPO_MAXIMO_AJUSTE_H, 20)
    mr = mr_linea_base_activa(t)
    print(f"Parametros (convertidos a 1/h): {PARAMETROS_LINEA_ACTIVA}")
    print(f"Rango valido del ajuste original: 0 - {TIEMPO_MAXIMO_AJUSTE_H:.2f} h\n")
    for ti, mri in zip(t[::3], mr[::3]):
        print(f"  t={ti:5.2f} h   MR={mri:.4f}")
    print(f"\nMR final esperado (~12.5% de la humedad inicial, ver fuente): {mr[-1]:.4f}")

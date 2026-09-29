"""
linea_base_activa.py
=====================

ACTUALIZACION 29 sept 2026 (v0.2): el modelo de esta linea base para la
campana Monte Carlo es ahora el modelo UNICO de Roa-Cenicafe
(``cinetica_roa.py``), alimentado con las condiciones de la camara solar
(ver seccion "v0.2" al final del modulo). El modelo Logaritmico de
Mackpayen et al. (2017) de abajo (v0.1, semana 5) se conserva por
trazabilidad y por los notebooks; NO responde a T/HR ni al clima de
Chinchina, por lo que no sirve para Monte Carlo.

--- Docstring original v0.1 ---

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


# ===========================================================================
# v0.2 (29 sept 2026) - Secador solar activo con el modelo unico de Roa
# ===========================================================================
#
# Condiciones que recibe el cafe en la camara solar activa:
#   - Aire de la camara = aire ambiente (misma presion de vapor ea, sin
#     aporte de agua) calentado por el colector/cubierta solar un
#     incremento de medio seno de maximo DT_MAX_ACTIVA_C al mediodia y 0
#     de noche (generador_ambiente.incremento_solar). El ventilador
#     (todo/nada, docs/seleccion_lineas_base.md) garantiza que el cafe
#     recibe ese aire; el modelo de Roa no tiene la velocidad del aire
#     como variable, asi que su efecto queda dentro del incremento
#     concentrado.
#   - HR de la camara por psicrometria (ea / es(T_camara)), igual que
#     dinamica_termica.rh_proceso.
#   - El vapor que libera el cafe no se suma al aire (misma simplificacion
#     ya declarada en dinamica_termica.py).
#
# Calibracion de DT_MAX_ACTIVA_C
# --------------------------------
# docs/seleccion_lineas_base.md cita una reduccion del tiempo de secado
# frente a patio de 30-50 % (Duque-Dussan et al., 2026) y de 40-50 % para
# invernadero activo con ventilacion forzada (Meja et al., 2025), y un
# incremento de temperatura interna de 10-25 C para secadores solares
# activos (Duque-Dussan et al., 2026).
#
# Como el secado solar solo avanza de dia, el tiempo hasta 11 % b.h. cambia
# A SALTOS (el cafe termina en la tarde del dia N o del dia N+1). En el dia
# nominal de Chinchina (tiempo de patio = 130.9 h) el mapa es:
#
#     DT_MAX [C]   15     17     18-22.5        22.8-25       30
#     reduccion    17 %   19 %   34-38 %        50-53 %       56 %
#
# No existe un DT_MAX que de exactamente 40 %: hay un escalon entre 38 % y
# 50 %. Se elige DT_MAX = 20 C, el CENTRO de la meseta 18-22.5 C:
#   - reduccion 36 % frente a patio, dentro del rango 30-50 % de
#     Duque-Dussan et al. (2026) (en el borde inferior del 40-50 % de
#     Meja et al., 2025);
#   - incremento dentro del rango 10-25 C de Duque-Dussan et al. (2026);
#   - estable: +-2 C no cambia el dia de terminacion en el dia nominal.
# Reproducible con mapa_calibracion_activa().
#
# Implicacion para Monte Carlo: por este efecto de escalon, el tiempo a
# humedad objetivo de las estrategias solares es una metrica "discreta"
# (salta de a ~1 dia). Tenerlo en cuenta al fijar la metrica primaria
# (ver metodologia_estadistica_monte_carlo.md).

# Configuracion fisica (29 sept 2026, lote comun de 80 kg c.p.s.)
# ----------------------------------------------------------------------
# Las tres estrategias secan el MISMO lote: 80 kg de cafe pergamino seco
# (158 kg humedos a 55 % b.h.). En secado solar el cafe se extiende en
# CAPA DELGADA de ~2 cm (capacidad estandar de los secadores solares de
# Cenicafe; Guerrero-Aguirre et al., 2025, Avances Tecnicos Cenicafe), de
# modo que cada grano recibe practicamente el aire/sol del ambiente y la
# ecuacion de capa delgada de Roa se aplica directamente, sin el modelo
# por capas que exige el lecho de 20 cm del secador electrico. Area
# necesaria: 158 kg / 696 kg/m3 (densidad aparente, Montoya 1989) / 0.02 m
# = ~12.8 m2, frente a 1.28 m2 del secador electrico (dato para CAPEX).
AREA_CAPA_DELGADA_M2 = 12.8
ESPESOR_CAPA_DELGADA_M = 0.02

import generador_ambiente as _amb
import cinetica_roa as _roa

DT_MAX_ACTIVA_C = 20.0     # C, centro de la meseta 18-22.5 C (ver bloque de arriba)


def condiciones_activa(clima_dias, dt_max_c: float = DT_MAX_ACTIVA_C):
    """Devuelve ``f(t_h) -> (T_camara, HR_camara)`` para cinetica_roa.simular."""

    def f(t_h: float) -> tuple[float, float]:
        t_amb, _, ea = _amb.ambiente_en(t_h, clima_dias)
        t_cam = t_amb + float(_amb.incremento_solar(np.asarray([t_h]), dt_max_c)[0])
        return t_cam, min(100.0 * ea / float(_amb.es_kpa(t_cam)), 100.0)

    return f


def simular_activa(clima_dias, dt_h: float = 0.25, t_max_h: float = 1500.0, **kw):
    """Corrida de la linea base activa con el modelo de Roa."""
    return _roa.simular(condiciones_activa(clima_dias), dt_h=dt_h, t_max_h=t_max_h, **kw)


def mapa_calibracion_activa(valores=(15.0, 17.0, 18.0, 20.0, 22.5, 22.8, 25.0, 30.0)):
    """Reduccion del tiempo a humedad objetivo frente a patio (dia nominal
    de Chinchina) para varios DT_MAX (ver bloque de calibracion)."""
    from escenario_sol_abierto import simular_patio

    nominal = [_amb.condiciones_nominales()]
    t_patio = simular_patio(nominal).t_objetivo_h
    filas = []
    for dt_max in valores:
        t = _roa.simular(condiciones_activa(nominal, dt_max), t_max_h=1500.0).t_objetivo_h
        filas.append((dt_max, t, 1.0 - t / t_patio))
    return t_patio, filas


if __name__ == "__main__":
    print("=== v0.2 (Roa) ===")
    t_patio, filas = mapa_calibracion_activa()
    print(f"Tiempo patio (dia nominal): {t_patio:.1f} h")
    for dt_max, t, red in filas:
        print(f"  DT_MAX={dt_max:5.1f} C -> {t:6.1f} h  reduccion vs patio {100 * red:5.1f} %")
    r = simular_activa([_amb.condiciones_nominales()])
    print(
        f"Chinchina (dia nominal): {_roa.M0_BH_PCT} -> {_roa.HUMEDAD_OBJETIVO_BH_PCT} % b.h. en "
        f"{r.t_objetivo_h:.1f} h ({r.t_objetivo_h / 24:.1f} d); T camara max {r.t_c.max():.1f} C; "
        f"rehumectacion {r.horas_rehumectacion:.1f} h; fuera de rango {r.horas_fuera_de_rango:.1f} h\n"
    )
    print("=== v0.1 (Logaritmico Mackpayen, legado) ===")
    t = np.linspace(0, TIEMPO_MAXIMO_AJUSTE_H, 20)
    mr = mr_linea_base_activa(t)
    print(f"Parametros (convertidos a 1/h): {PARAMETROS_LINEA_ACTIVA}")
    print(f"Rango valido del ajuste original: 0 - {TIEMPO_MAXIMO_AJUSTE_H:.2f} h\n")
    for ti, mri in zip(t[::3], mr[::3]):
        print(f"  t={ti:5.2f} h   MR={mri:.4f}")
    print(f"\nMR final esperado (~12.5% de la humedad inicial, ver fuente): {mr[-1]:.4f}")

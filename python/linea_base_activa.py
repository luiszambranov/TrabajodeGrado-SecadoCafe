"""
linea_base_activa.py
=====================

Linea base ACTIVA: secado solar activo con ventilacion forzada
(invernadero/tunel solar con ventilador todo/nada por horario, 06:00-18:00;
ver docs/seleccion_lineas_base.md).
Trabajo de grado - Sistema de supervision digital para el secado de cafe.

Modelo
------
Modelo cinetico UNICO del proyecto, Roa-Cenicafe (``cinetica_roa.py``).
El aire de la camara es el ambiente de Chinchina (``generador_ambiente.py``)
calentado por la cubierta solar un incremento diurno de maximo
``DT_MAX_ACTIVA_C`` = 12.5 C. Ese valor da una reduccion del 47.5 % del
tiempo frente a la estrategia pasiva, dentro del 30-50 % de
Duque-Dussan et al. (2026) y del 40-50 % de Meja et al. (2025), y dentro
del incremento de 10-25 C reportado para secadores solares activos
(Duque-Dussan et al., 2026). Detalle en el bloque de comentarios de abajo.

Uso principal: ``condiciones_activa(clima_dias)`` (lo llama
``campana_montecarlo.py``) y ``simular_activa``. ``python
linea_base_activa.py`` imprime el mapa de calibracion.

Historial: la v0.1 (semana 5, modelo Logaritmico de Mackpayen et al.,
2017) no respondia a T/HR ni al clima de Chinchina y se retiro del modulo
el 6 oct 2026; se conserva en ``python/legacy/lineas_base_v01.py``. Ver
docs/evolucion_del_modelo.md.

Referencias: ver docs/seleccion_lineas_base.md (Duque-Dussan et al., 2026;
Meja et al., 2025; Penuela-Martinez et al., 2025).
"""

from __future__ import annotations

import numpy as np

# ===========================================================================
# Secador solar activo con el modelo unico de Roa (desde el 29 sept 2026)
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
# Calibracion de DT_MAX_ACTIVA_C (ACTUALIZADO 4 oct 2026)
# --------------------------------------------------------
# docs/seleccion_lineas_base.md cita una reduccion del tiempo de secado
# frente al secado solar pasivo de 30-50 % (Duque-Dussan et al., 2026) y de
# 40-50 % para invernadero activo con ventilacion forzada (Meja et al.,
# 2025), y un incremento de temperatura interna de 10-25 C para secadores
# solares activos (Duque-Dussan et al., 2026).
#
# La linea base pasiva se recalibro el 4 oct 2026 contra Cenicafe (10.6 d,
# ver escenario_sol_abierto.py) y el ciclo diario ahora es asimetrico
# (Guzman & Ramirez, 2004). Mapa en el dia nominal (pasiva = 255.8 h):
#
#     DT_MAX [C]   8.0-9.0     9.5-11.0     11.5-14.0     14.5-16
#     reduccion    28-30 %     37-39 %      45-49 %       55-57 %
#
# Se elige DT_MAX = 12.5 C, dentro de la meseta 11.5-14.0 C:
#   - reduccion 47.5 % (134.3 h = 5.6 d): cumple A LA VEZ el 30-50 % de
#     Duque-Dussan et al. (2026) y el 40-50 % de Meja et al. (2025);
#   - incremento dentro del rango 10-25 C de Duque-Dussan et al. (2026);
#   - estable: +-1 C no cambia el dia de terminacion.
# Igual que en la pasiva, es un parametro efectivo (incluye dias nublados).
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
# CAPA DELGADA de 2 cm (capacidad de diseno de los secadores solares de
# Cenicafe: 7.2 kg c.p.s./m2 con capa de 2.0 cm; Penuela-Martinez et al.,
# 2025, Avances Tecnicos Cenicafe), de modo que cada grano recibe
# practicamente el aire/sol del ambiente y la ecuacion de capa delgada de
# Roa se aplica directamente, sin el modelo por capas que exige el lecho de
# 20 cm del secador electrico. Area necesaria: 80 / 7.2 = 11.1 m2 (antes
# 12.8 m2 por densidad aparente), frente a 1.28 m2 del secador electrico
# (dato para CAPEX).
AREA_CAPA_DELGADA_M2 = 80.0 / 7.2   # 11.1 m2: 7.2 kg c.p.s./m2 (Penuela-Martinez et al., 2025)
ESPESOR_CAPA_DELGADA_M = 0.02

import generador_ambiente as _amb
import cinetica_roa as _roa

DT_MAX_ACTIVA_C = 12.5     # C, meseta 11.5-14.0 C (ver bloque de arriba, 4 oct 2026)


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


def mapa_calibracion_activa(valores=(8.0, 9.0, 9.5, 11.0, 11.5, 12.5, 14.0, 14.5, 16.0)):
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

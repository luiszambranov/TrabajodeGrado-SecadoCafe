"""
escenario_sol_abierto.py
==========================

Linea base minima (estrategia PASIVA): secado tradicional al sol en patio,
lazo abierto, sin control del perfil termico (ver
docs/seleccion_lineas_base.md).
Trabajo de grado - Sistema de supervision digital para el secado de cafe.

Modelo
------
Modelo cinetico UNICO del proyecto, Roa-Cenicafe (``cinetica_roa.py``),
el mismo de las otras dos estrategias; solo cambian las condiciones de
aire que recibe el cafe. El patio recibe el ambiente de Chinchina
(``generador_ambiente.py``) mas un incremento solar diurno sobre la
temperatura del grano, de maximo ``DT_MAX_PATIO_C`` = 4.4 C, calibrado
contra los 10.6 dias de secado solar de Cenicafe (Penuela-Martinez et
al., 2025). Detalle de la calibracion en el bloque de comentarios de
abajo.

Uso principal: ``condiciones_patio(clima_dias)`` (lo llama
``campana_montecarlo.py``) y ``simular_patio``. ``python
escenario_sol_abierto.py`` imprime el mapa de calibracion.

Historial: la v0.1 (semana 5, modelo de Newton calibrado con Eliseu,
2008) no respondia a T/HR y se retiro del modulo el 6 oct 2026; se
conserva en ``python/legacy/lineas_base_v01.py``. Ver
docs/evolucion_del_modelo.md.

Referencias
-----------
- Penuela-Martinez, A. E., Osorio Giraldo, C. V., Guerrero, A., &
  Sanz-Uribe, J. R. (2025). Manejo del cafe en el secado solar. Avances
  Tecnicos Cenicafe. https://doi.org/10.38141/10779/0577
- Eliseu (2008): solo comparacion de legado, ver
  data/reference/eliseu_2008_secado_patio.md.
"""

from __future__ import annotations


import numpy as np

# Condiciones de Eliseu (2008, patio en Brasil). Solo para la comparacion
# de legado calibrar_dt_max_patio_eliseu(); el modelo usa Cenicafe 2025.
T_AMBIENTE_MEDIA_C = 26.3
HR_AMBIENTE_MEDIA_PCT = 63.3
TIEMPO_TOTAL_SECADO_H = 117.5  # ~4.9 dias

# ===========================================================================
# Patio con el modelo unico de Roa-Cenicafe (desde el 29 sept 2026)
# ===========================================================================
#
# Condiciones que recibe el cafe en patio:
#   - Aire: el ambiente (generador_ambiente.ambiente_en), sin
#     calentamiento ni ventilacion forzada.
#   - Grano: expuesto al sol, su temperatura supera la del aire durante el
#     dia. Se representa con un incremento solar de medio seno
#     (generador_ambiente.incremento_solar) de maximo DT_MAX_PATIO_C al
#     mediodia y 0 de noche.
#   - El modelo de Roa se evalua a la temperatura del GRANO con la presion
#     de vapor real del aire (ea): Me(T_grano, HR_superficie) y
#     (Pvs(T_grano) - ea). Es la forma concentrada de decir que el sol
#     calienta la superficie del grano y con eso baja su humedad de
#     equilibrio; sin ese calentamiento, con el clima de Chinchina
#     (Me ~11 % b.h. en la tarde, ~17-19 % b.h. de noche) el cafe no
#     llegaria nunca a 10-12 % b.h.
#
# Calibracion de DT_MAX_PATIO_C (unico parametro libre de la estrategia)
# ------------------------------------------------------------------------
# ACTUALIZADO 4 oct 2026: se calibra con datos COLOMBIANOS de Cenicafe en
# lugar de Eliseu (2008, C. canephora en Brasil).
#
# Fuente: Penuela-Martinez, A. E., Osorio Giraldo, C. V., Guerrero, A., &
# Sanz-Uribe, J. R. (2025). Manejo del cafe en el secado solar. Avances
# Tecnicos Cenicafe. https://doi.org/10.38141/10779/0577
#   - Capacidad de diseno: 7.2 kg c.p.s. por m2, capa de 2.0 cm.
#   - Humedad final 10-12 % b.h. (se usa 11 %).
#   - Tiempo de secado solar con 1 400-1 800 h/ano de brillo solar:
#     10.6 dias en promedio (minimo 6.2, maximo 19.1).
# Brillo solar de la estacion Naranjal: 1 817 h/ano (Cenicafe 49(4), 1998),
# es decir el grupo de 1 400-1 800 h (en su borde superior).
#
# Se busca el DT_MAX con el que el dia nominal de Chinchina (con el ciclo
# asimetrico de generador_ambiente) da ~10.6 dias de 55 a 11 % b.h. Como el
# secado solar solo avanza de dia, el tiempo cambia A SALTOS; hay una
# meseta DT_MAX = 4.0-4.8 C que termina en el dia 10.6-10.8. Se elige el
# CENTRO, 4.4 C (255.8 h = 10.66 d). Reproducible con
# mapa_calibracion_patio().
#
# Interpretacion: DT_MAX es un parametro EFECTIVO. El dia nominal tiene sol
# todos los dias (medio seno de 06:00 a 18:00), pero en Naranjal el brillo
# solar real es solo el 41 % del maximo teorico (Cenicafe, 1998) y hay
# dias de lluvia. El promedio de Cenicafe ya incluye esos dias, asi que el
# DT_MAX calibrado (4.4 C) es menor que el calentamiento en un dia
# despejado. Esto se declara como limitacion.
#
# Legado: la calibracion contra Eliseu (2008) daba 12.9 C con el ciclo
# simetrico anterior; se conserva calibrar_dt_max_patio_eliseu() solo como
# comparacion.

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
ESPESOR_CAPA_DELGADA_M = 0.02       # 2.0 cm (misma fuente)

import generador_ambiente as _amb
import cinetica_roa as _roa

DT_MAX_PATIO_C = 4.4   # C, calibrado contra Cenicafe 2025 (ver bloque de arriba)
TIEMPO_CENICAFE_SOLAR_H = 10.6 * 24.0  # 254.4 h (Penuela-Martinez et al., 2025)
ELISEU_T_MEDIA_C = T_AMBIENTE_MEDIA_C
ELISEU_HR_MEDIA_PCT = HR_AMBIENTE_MEDIA_PCT
ELISEU_M0_BS_PCT = 135.5   # promedio de 1.20-1.51 b.s.
ELISEU_MF_BS_PCT = 10.0    # 0.10 b.s.
ELISEU_OSCILACION_C = 5.2  # +- C, misma amplitud diaria que Naranjal (supuesto)


def condiciones_patio(clima_dias, dt_max_c: float = DT_MAX_PATIO_C):
    """Devuelve ``f(t_h) -> (T_grano, HR_superficie)`` para cinetica_roa.simular."""

    def f(t_h: float) -> tuple[float, float]:
        t_amb, _, ea = _amb.ambiente_en(t_h, clima_dias)
        t_grano = t_amb + float(_amb.incremento_solar(np.asarray([t_h]), dt_max_c)[0])
        hr_sup = 100.0 * ea / float(_amb.es_kpa(t_grano))
        return t_grano, min(hr_sup, 100.0)

    return f


def simular_patio(clima_dias, dt_h: float = 0.25, t_max_h: float = 1500.0, **kw):
    """Corrida de la linea base minima con el modelo de Roa."""
    return _roa.simular(condiciones_patio(clima_dias), dt_h=dt_h, t_max_h=t_max_h, **kw)


def mapa_calibracion_patio(valores=None):
    """Tiempo a 11 % b.h. (dia nominal de Chinchina) para varios DT_MAX.
    Devuelve [(dt_max, t_h)]; la meseta que contiene 10.6 d define DT_MAX."""
    nominal = [_amb.condiciones_nominales()]
    valores = np.arange(3.6, 5.01, 0.1) if valores is None else valores
    return [(float(d), _roa.simular(condiciones_patio(nominal, d), t_max_h=1500.0).t_objetivo_h) for d in valores]


def calibrar_dt_max_patio_eliseu() -> float:
    """LEGADO: DT_MAX contra Eliseu (2008, Brasil). Solo comparacion."""
    from scipy.optimize import brentq

    dia = _amb.CondicionesClimaticas(
        t_min=ELISEU_T_MEDIA_C - ELISEU_OSCILACION_C, t_max=ELISEU_T_MEDIA_C + ELISEU_OSCILACION_C
    )
    dia.ea_kpa = ELISEU_HR_MEDIA_PCT / 100.0 * float(_amb.es_kpa(ELISEU_T_MEDIA_C))
    m0_bh, mf_bh = _roa.bs_a_bh(ELISEU_M0_BS_PCT), _roa.bs_a_bh(ELISEU_MF_BS_PCT)

    def error(dt_max: float) -> float:
        r = _roa.simular(condiciones_patio([dia], dt_max), t_max_h=800.0, m0_bh_pct=m0_bh, m_obj_bh_pct=mf_bh)
        return r.t_objetivo_h - TIEMPO_TOTAL_SECADO_H

    return brentq(error, 8.0, 20.0, xtol=0.01)


if __name__ == "__main__":
    print(f"Calibracion contra Cenicafe 2025 (objetivo {TIEMPO_CENICAFE_SOLAR_H:.1f} h = 10.6 d):")
    for d, t in mapa_calibracion_patio():
        print(f"  DT_MAX={d:4.1f} C -> {t:6.1f} h ({t / 24:5.2f} d)")
    print(f"DT_MAX_PATIO_C usado: {DT_MAX_PATIO_C} C | area {AREA_CAPA_DELGADA_M2:.1f} m2")
    r = simular_patio([_amb.condiciones_nominales()])
    print(
        f"Chinchina (dia nominal): {_roa.M0_BH_PCT} -> {_roa.HUMEDAD_OBJETIVO_BH_PCT} % b.h. en "
        f"{r.t_objetivo_h:.1f} h ({r.t_objetivo_h / 24:.1f} d); rehumectacion {r.horas_rehumectacion:.1f} h; "
        f"fuera de rango {r.horas_fuera_de_rango:.1f} h\n"
    )

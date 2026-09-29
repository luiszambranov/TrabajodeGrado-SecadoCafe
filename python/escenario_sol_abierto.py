"""
escenario_sol_abierto.py
==========================

ACTUALIZACION 29 sept 2026 (v0.2): el modelo de esta linea base para la
campana Monte Carlo es ahora el modelo UNICO de Roa-Cenicafe
(``cinetica_roa.py``), el mismo de las otras dos estrategias, alimentado
con las condiciones del patio (ver seccion "v0.2" al final del modulo).
El modelo Newton de abajo (v0.1, semana 5) se conserva solo por
trazabilidad y porque lo usan los notebooks de la semana 5; NO responde
a T/HR, por lo que no sirve para Monte Carlo.

--- Docstring original v0.1 ---

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


# ===========================================================================
# v0.2 (29 sept 2026) - Patio con el modelo unico de Roa-Cenicafe
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
# Contra el estudio de patio ya usado en v0.1 (Eliseu, 2008; ver
# data/reference/eliseu_2008_secado_patio.md): T media 26.3 C, HR media
# 63.3 %, humedad 1.355 -> 0.10 b.s. (promedio de clones), 117.5 h. Se
# construye un dia tipo con T media 26.3 C, la misma oscilacion diaria que
# Naranjal (+-5.2 C) y ea = 0.633*es(26.3 C), y se busca (brentq) el
# DT_MAX que reproduce 117.5 h con el modelo de Roa. Resultado: 12.9 C.
# Limitaciones: Eliseu es C. canephora en Brasil (clima distinto); la
# calibracion traslada solo el efecto concentrado del sol sobre el grano,
# no los parametros cineticos (esos son de Roa, cafe Caturra colombiano).
# Reproducible con calibrar_dt_max_patio().

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

DT_MAX_PATIO_C = 12.9  # C, calibrado (ver bloque de arriba)
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


def calibrar_dt_max_patio() -> float:
    """Recalcula DT_MAX_PATIO_C contra Eliseu (2008). Ver bloque de arriba."""
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
    print("=== v0.2 (Roa) ===")
    print(f"DT_MAX_PATIO_C recalibrado: {calibrar_dt_max_patio():.2f} C (constante: {DT_MAX_PATIO_C})")
    r = simular_patio([_amb.condiciones_nominales()])
    print(
        f"Chinchina (dia nominal): {_roa.M0_BH_PCT} -> {_roa.HUMEDAD_OBJETIVO_BH_PCT} % b.h. en "
        f"{r.t_objetivo_h:.1f} h ({r.t_objetivo_h / 24:.1f} d); rehumectacion {r.horas_rehumectacion:.1f} h; "
        f"fuera de rango {r.horas_fuera_de_rango:.1f} h\n"
    )
    print("=== v0.1 (Newton, legado) ===")
    print(f"k calibrado: {K_SOL_ABIERTO:.5f} 1/h "
          f"(secado total asumido en {TIEMPO_TOTAL_SECADO_H} h)")
    t = np.linspace(0, TIEMPO_TOTAL_SECADO_H, 10)
    for ti, mri in zip(t, mr_sol_abierto(t)):
        dias = ti / 24
        print(f"  t={ti:6.1f} h ({dias:4.1f} d)   MR={mri:.4f}")

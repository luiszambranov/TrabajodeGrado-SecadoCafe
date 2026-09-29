"""
lecho_secado.py
================

Lecho estático de café pergamino por capas (modelo de Thompson), con la
cinética de capa delgada de Roa-Cenicafé (cinetica_roa.py) en cada capa.
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Por qué hace falta (29 sept 2026)
----------------------------------
Con el caudal específico recomendado por Cenicafé (0.1 m3/min por kg
c.p.s.; González et al., 2010), el aire a 50 °C puede llevarse como
máximo ~0.065 kg de agua por hora y por kg c.p.s. antes de saturarse
(saturación adiabática, bulbo húmedo ~25 °C), mientras la ecuación de
capa delgada pide ~0.127 al inicio del secado. Si cada grano "viera" el
aire del plenum, el modelo secaría ~2 veces más rápido de lo físicamente
posible. El modelo de Thompson (el mismo que usa SECAFÉ para los
secadores de Cenicafé) resuelve esto: el lecho se divide en capas
delgadas; el aire atraviesa la primera, se enfría y se humedece al
secarla, y entra así a la siguiente.

Algoritmo por capa y por paso Δt (Parra-Coronado et al., 2008, ec. 2 y 3,
escritas en SI)
---------------------------------------------------------------------------
    R   = m_aire*Δt / m_materia_seca_capa        [kg aire / kg m.s.]
    CPr = CP(M) / R                               (calor específico del
                                                   café por kg de aire)
 1. Temperatura de equilibrio aire-grano antes de secar:
        Te = [(ca + cv*w)*Ta + CPr*Tg] / (ca + cv*w + CPr)
 2. HR del aire a Te con su razón de humedad w.
 3. Secado de la capa durante Δt a (Te, HR) con la capa delgada de Roa
    (cinetica_roa.paso_humedad): ΔM.
 4. El agua pasa al aire: Δw = ΔM / R.
 5. Balance de calor después de secar (calor latente de Trejos 1989):
        Tf = Te - Δw*L / (ca + cv*(w+Δw) + CPr)
 6. Si el aire de salida quedaría sobresaturado (Pv > Pvs(Tf)), se reduce
    la evaporación hasta que el aire salga exactamente saturado (criterio
    de Thompson: el aire no puede cargar más agua que la de saturación).
 7. Grano y aire salen a Tf; el aire (Tf, w+Δw) entra a la capa siguiente.

Con el ventilador apagado no hay flujo: el lecho no seca ni se
rehumedece (la humedad se conserva) y su temperatura no cambia en este
modelo (simplificación: pausas cortas).

Referencias
------------
Thompson, T. L., Peart, R. M., & Foster, G. H. (1968). Mathematical
    simulation of corn drying: a new model. Transactions of the ASAE,
    11(4), 582-586.
Parra-Coronado, A., Roa-Mejía, G., & Oliveros-Tascón, C. E. (2008).
    SECAFÉ Parte I. Revista Brasileira de Engenharia Agrícola e
    Ambiental, 12(4), 415-427 (ec. 2 y 3; capas de 2.5 cm).
Trejos-Rodríguez, R., Roa-Mejía, G., & Oliveros-Tascón, C. E. (1989).
    Cenicafé, 40(1), 5-15 (calor latente).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq

import cinetica_roa as roa
from dinamica_termica import (
    CP_AIRE,
    CP_VAPOR,
    ParametrosSecador,
    calor_especifico_cafe,
    presion_vapor_de_w,
)
from generador_ambiente import es_kpa

ESPESOR_CAPA_M = 0.025   # 2.5 cm por capa (Thompson, 1968; SECAFÉ 2008)
DT_MAX_H = 0.05          # sub-paso máximo [h] (3 min)


@dataclass
class ResultadoPasoLecho:
    m_bh_prom_pct: float        # humedad promedio del lote [% b.h.]
    t_salida_c: float           # temperatura del aire a la salida del lecho
    w_salida: float             # razón de humedad del aire a la salida
    agua_evaporada_kg: float    # agua retirada en el paso (negativa si rehumectación)
    t_grano_max_c: float        # temperatura máxima de grano en el lecho
    fuera_de_rango: bool        # alguna capa fuera del rango de las fuentes
    rehumectacion: bool         # alguna capa con M < Me


class LechoThompson:
    """Lecho estático de café dividido en capas de 2.5 cm."""

    def __init__(self, p: ParametrosSecador, m0_bh_pct: float = roa.M0_BH_PCT, t_inicial_c: float = 20.0) -> None:
        self.p = p
        self.n_capas = max(1, int(round(p.espesor_lecho_m / ESPESOR_CAPA_M)))
        self.m0_bs = roa.bh_a_bs(m0_bh_pct)
        self.m_bs = np.full(self.n_capas, self.m0_bs)          # % b.s. por capa
        self.t_grano = np.full(self.n_capas, t_inicial_c)      # °C por capa
        self.masa_ms_capa = p.masa_cps_kg * (1.0 - roa.HUMEDAD_OBJETIVO_BH_PCT / 100.0) / self.n_capas
        # masa de MATERIA SECA: c.p.s. se entrega a ~11 % b.h. (por definición
        # comercial de café pergamino seco), así que la materia seca es 89 %.

    # ------------------------------------------------------------------
    @property
    def m_bh_promedio(self) -> float:
        return roa.bs_a_bh(float(np.mean(self.m_bs)))

    @property
    def m_bh_max(self) -> float:
        """Humedad de la capa más húmeda [% b.h.] (riesgo de almacenamiento)."""
        return roa.bs_a_bh(float(np.max(self.m_bs)))

    @property
    def m_bh_min(self) -> float:
        return roa.bs_a_bh(float(np.min(self.m_bs)))

    def _capa(self, i: int, t_aire: float, w: float, dt_h: float, m_aire_kg: float):
        R = m_aire_kg / self.masa_ms_capa
        cpr = calor_especifico_cafe(self.m_bs[i] / 100.0) / R
        ca = CP_AIRE + CP_VAPOR * w
        te = (ca * t_aire + cpr * self.t_grano[i]) / (ca + cpr)
        rh = min(100.0, 100.0 * presion_vapor_de_w(w) / float(es_kpa(te)))
        r = roa.paso_humedad(self.m_bs[i], te, rh, dt_h, m0_bs_pct=self.m0_bs)
        dm_total = (self.m_bs[i] - r.m_bs_pct) / 100.0      # decimal b.s., >0 = secado
        L = roa.calor_latente_kj_kg(te, self.m_bs[i])

        def salida(f: float) -> tuple[float, float]:
            dw = f * dm_total / R
            wf = max(w + dw, 0.0)
            tf = te - dw * L / (CP_AIRE + CP_VAPOR * wf + cpr)
            return tf, wf

        f = 1.0
        tf, wf = salida(1.0)
        if dm_total > 0 and presion_vapor_de_w(wf) > float(es_kpa(tf)):
            g = lambda f_: presion_vapor_de_w(salida(f_)[1]) - float(es_kpa(salida(f_)[0]))
            f = brentq(g, 0.0, 1.0, xtol=1e-6) if g(0.0) < 0 else 0.0
            tf, wf = salida(f)
        self.m_bs[i] -= 100.0 * f * dm_total
        self.t_grano[i] = tf
        return tf, wf, f * dm_total * self.masa_ms_capa, r

    # ------------------------------------------------------------------
    def paso(self, t_entrada_c: float, ea_entrada_kpa: float, fan_cmd: int, dt_h: float,
             m_aire_kg_s: float, flujo_invertido: bool = False) -> ResultadoPasoLecho:
        """Avanza el lecho ``dt_h`` horas con aire de entrada (T, ea) desde el plenum.

        ``flujo_invertido``: el aire entra por la capa SUPERIOR (índice
        n-1) y sale por la inferior. La inversión periódica del sentido del
        aire es la práctica de Cenicafé para uniformizar la humedad del
        lecho estático (SECAFÉ, 2008: inversión cada 6 h).
        """
        from dinamica_termica import razon_humedad

        if not fan_cmd or dt_h <= 0:
            return ResultadoPasoLecho(self.m_bh_promedio, t_entrada_c, razon_humedad(ea_entrada_kpa),
                                      0.0, float(self.t_grano.max()), False, False)
        n_sub = max(1, int(np.ceil(dt_h / DT_MAX_H)))
        h = dt_h / n_sub
        agua = 0.0
        fuera = rehum = False
        t_max = -1e9
        for _ in range(n_sub):
            t_a, w = t_entrada_c, razon_humedad(ea_entrada_kpa)
            m_aire = m_aire_kg_s * h * 3600.0
            orden = range(self.n_capas - 1, -1, -1) if flujo_invertido else range(self.n_capas)
            for i in orden:
                t_a, w, dagua, r = self._capa(i, t_a, w, h, m_aire)
                agua += dagua
                fuera |= r.fuera_de_rango
                rehum |= r.rehumectacion
            t_max = max(t_max, float(self.t_grano.max()))
        return ResultadoPasoLecho(self.m_bh_promedio, t_a, w, agua, t_max, fuera, rehum)


if __name__ == "__main__":
    import generador_ambiente as amb

    p = ParametrosSecador()
    clima = [amb.condiciones_nominales()]

    for espesor in (0.20,):
        p.espesor_lecho_m = espesor
        lecho = LechoThompson(p)
        t, dt = 0.0, 0.25
        agua = 0.0
        while lecho.m_bh_promedio > roa.HUMEDAD_OBJETIVO_BH_PCT and t < 200:
            _, _, ea = amb.ambiente_en(t, clima)
            r = lecho.paso(p.t_setpoint_c, ea, 1, dt, p.masa_aire_kg_s())
            agua += r.agua_evaporada_kg
            t += dt
        print(f"Lecho {espesor * 100:.1f} cm ({lecho.n_capas} capas), aire a {p.t_setpoint_c} C constante: "
              f"{t:.1f} h hasta {lecho.m_bh_promedio:.1f} % b.h.; agua evaporada {agua:.1f} kg; "
              f"humedad capa inferior/superior {roa.bs_a_bh(lecho.m_bs[0]):.1f}/{roa.bs_a_bh(lecho.m_bs[-1]):.1f} % b.h.")
    rh50 = 100.0 * amb.condiciones_nominales().ea_kpa / float(es_kpa(50.0))
    print(f"Referencia capa delgada pura (sin limite del aire) a 50 C: "
          f"{roa.tiempo_hasta_humedad(roa.HUMEDAD_OBJETIVO_BH_PCT, 50.0, rh50):.1f} h")

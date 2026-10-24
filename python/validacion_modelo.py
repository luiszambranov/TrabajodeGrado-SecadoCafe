"""
validacion_modelo.py
=====================

Validación del modelo del proyecto contra datos experimentales que NO se
usaron para construirlo ni calibrarlo.
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Idea: lo común a las tres estrategias es la cinética del café (Roa-Cenicafé)
y el modelo de lecho por capas (Thompson). Se valida cada pieza por separado
y en distintos tipos de secado (capa delgada en laboratorio, secador mecánico
de lecho, secado solar), para no apoyarse en un solo caso.

Casos
-----
V1. Capa delgada a T y HR controladas (laboratorio): Phitakwinai, P., et al.
    (2019). Thin-layer drying of parchment Arabica coffee by controlling
    temperature and relative humidity. Food Science & Nutrition, 7(9),
    2921-2931. Café arábica de Tailandia. Tiempo hasta MR = 0.2 reconstruido
    con su modelo Midilli modificado (Tabla 2), 9 condiciones.
V2. Secador mecánico de lecho (independiente): Martínez-Tovar, D. G., &
    Álvarez-Hernández, J. R. (2006). Aprovechamiento de la energía calórica
    de estufas campesinas para el secado del café en fincas (Escafé).
    Cenicafé, 57(2), 88-99. 125 kg c.p.s. en 1 m² (30 cm), aire a 48.3 °C
    durante 15 h/día (estufa encendida), inversión del aire cada 7.5 h,
    ventilador de 1.15 m³/s nominales con 10 mm c.a. Resultado: ~3 días,
    10 % b.h. final, capas de 8.41 a 12.74 % b.h., 7 297 kJ/kg de agua.
V3. Secado solar, validación cruzada dentro de una misma fuente:
    Peñuela-Martínez et al. (2025), Avances Técnicos No. 577 de Cenicafé. Se calibró con el grupo de 1 400-1 800
    h/año de sol (10.6 d); aquí se PREDICE el grupo de 1 061-1 399 h/año
    (15.5 d, rango 5.2-36.1 d) escalando el calentamiento solar efectivo
    con las horas de sol (1 230/1 600). Regla de escala: supuesto propio.

Caso excluido (antes V2): secado en patio de Resende, O., Arcanjo, R. V.,
Siqueira, V. C., & Rodrigues, S. (2009), Acta Scientiarum. Agronomy, 31(2),
189-196, https://doi.org/10.4025/actasciagron.v31i2.588. Su humedad final,
0.10 b.s., queda por debajo del equilibrio de Roa a 26.3 °C / 63.3 % HR
constantes (~0.126 b.s.): con aire constante el modelo nunca llega a ese
valor, y sin el calentamiento solar del grano el caso no es comparable.
`caso_excluido_resende()` solo imprime ese equilibrio como justificación.

Supuestos propios declarados (V2)
---------------------------------
- Caudal real a través del lecho: el 1.15 m³/s es el dato nominal del
  ventilador; a través de 30 cm de café con 10 mm c.a. (98 Pa) la ecuación
  de Boyce & Pérez-Fonrodona (P/L = 0.0014·V^1.46) da 0.244 m/s
  = 0.117 m³/min por kg c.p.s. (coincide con el 0.1 de Cenicafé).
- Estufa encendida de 05:00 a 20:00 (15 h); el resto del día el ventilador
  sopla aire ambiente.
- Humedad inicial no reportada con precisión: se corre con 44, 48 y 53 % b.h.
"""

from __future__ import annotations

import math

import numpy as np

import cinetica_roa as roa
import generador_ambiente as amb

# V1: tiempo hasta MR = 0.2 [h] con el modelo de Phitakwinai et al. (2019)
PHITAKWINAI_T_MR02_H = {
    (50, 10): 11.4, (60, 10): 7.7, (70, 10): 5.9,
    (50, 20): 12.7, (60, 20): 9.4, (70, 20): 7.3,
    (50, 30): 14.5, (60, 30): 10.2, (70, 30): 8.0,
}


def t_mr_roa(mr: float, t_c: float, rh: float) -> float:
    return (-math.log(mr) / roa.constante_secado(t_c, rh)) ** (1.0 / roa.Q_ROA)


def v1_capa_delgada():
    filas = [(T, RH, t_mr_roa(0.2, T, RH), ref) for (T, RH), ref in PHITAKWINAI_T_MR02_H.items()]
    err = np.array([(m - r) / r for _, _, m, r in filas])
    rmse = float(np.sqrt(np.mean([(m - r) ** 2 for _, _, m, r in filas])))
    return filas, rmse, float(np.mean(np.abs(err)) * 100)


def caso_excluido_resende():
    """Equilibrio de Roa a 26.3 °C / 63.3 % HR frente a la humedad final de Resende et al. (2009), 10 % b.s."""
    return roa.humedad_equilibrio_bs(26.3, 63.3), 10.0


def v2_escafe(m0_bh: float, ventana=(5.0, 20.0), inv_h=7.5, sp=48.3, mf=10.0):
    from dinamica_termica import ParametrosSecador
    from secador_electrico import SecadorElectrico

    v_cfm_ft2 = ((98.0 / 249.09) / 0.984 / 0.0014) ** (1.0 / 1.46)   # Boyce, 10 mm c.a. en 30 cm
    caudal = v_cfm_ft2 * 0.00508 * 60.0 / 125.0                        # m³/min por kg c.p.s.
    p = ParametrosSecador(masa_cps_kg=125.0, caudal_especifico_m3_min_kg=caudal, espesor_lecho_m=0.30,
                          potencia_resistencia_kw=30.0, t_setpoint_c=sp)
    s = SecadorElectrico([amb.condiciones_nominales()], p, m0_bh_pct=m0_bh)
    estado = {"on": 0}

    def control(t_proc: float) -> int:
        if not (ventana[0] <= s.t_h % 24.0 < ventana[1]):
            return 0
        estado["on"] = 1 if t_proc < sp else 0
        return estado["on"]

    while s.t_h < 300.0 and s.lecho.m_bh_promedio > mf:
        s.paso(0, 1, 1.0 / 60.0, control=control, flujo_invertido=int(s.t_h // inv_h) % 2 == 1)
    c = s.c
    return {"t_h": s.t_h, "capa_min": s.lecho.m_bh_min, "capa_max": s.lecho.m_bh_max,
            "sec_kj_kg": 3600.0 * c.energia_resistencia_kwh / c.agua_evaporada_kg, "caudal": caudal}


def v3_solar_cruzada():
    from escenario_sol_abierto import DT_MAX_PATIO_C, condiciones_patio

    dt = DT_MAX_PATIO_C * 1230.0 / 1600.0
    r = roa.simular(condiciones_patio([amb.condiciones_nominales()], dt), t_max_h=2000.0)
    return dt, r.t_objetivo_h / 24.0, 15.5


if __name__ == "__main__":
    filas, rmse, mape = v1_capa_delgada()
    print("V1 Capa delgada vs Phitakwinai et al. (2019), tiempo hasta MR = 0.2")
    for T, RH, m, r in filas:
        print(f"   {T} C / {RH:2d} %: modelo {m:5.1f} h | ref {r:5.1f} h | {100 * (m - r) / r:+5.1f} %")
    print(f"   RMSE = {rmse:.2f} h | error medio absoluto = {mape:.1f} %\n")

    print("V2 Secador Escafé (Martínez-Tovar & Álvarez 2006): ref ~3 d, capas 8.41-12.74 %, 7 297 kJ/kg agua")
    for m0 in (44.0, 48.0, 53.0):
        r = v2_escafe(m0)
        print(f"   M0 {m0:.0f} %: modelo {r['t_h']:5.1f} h ({r['t_h'] / 24:.2f} d) | capas {r['capa_min']:.1f}-"
              f"{r['capa_max']:.1f} % | {r['sec_kj_kg']:.0f} kJ/kg ({100 * (r['sec_kj_kg'] - 7297) / 7297:+.0f} %)")
    print(f"   (caudal a través del lecho: {r['caudal']:.3f} m³/min/kg)\n")

    dt, t_m, t_r = v3_solar_cruzada()
    print(f"V3 Solar, grupo de 1 061-1 399 h/año de sol (Peñuela-Martínez et al. 2025): DT efectivo {dt:.2f} C -> "
          f"modelo {t_m:.1f} d | ref {t_r} d (rango 5.2-36.1) | {100 * (t_m - t_r) / t_r:+.0f} %")

    me, mf = caso_excluido_resende()
    print(f"\nCaso excluido, patio de Resende et al. (2009): equilibrio de Roa a 26.3 C / 63.3 % HR = {me:.2f} % b.s. "
          f"> humedad final medida {mf:.1f} % b.s. -> no comparable con aire constante")

"""
dinamica_termica.py
====================

Secador mecánico con RESISTENCIA ELÉCTRICA de la propuesta supervisada:
dimensionamiento, balance de energía del aire de secado (plenum) y
propiedades físicas del lecho de café. Versión v1 (29 sept 2026), que
reemplaza al esqueleto v0 (ParametrosCamara con valores de orden de
magnitud no calibrados).
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Concepto físico (secador de capa estática, flujo de aire forzado)
------------------------------------------------------------------
    aire ambiente --> ventilador --> resistencia eléctrica --> plenum
         (T_amb, ea)                (heater_cmd)            (T_process)
                                                               |
                                                   lecho de café (20 cm)
                                                   modelo de Thompson por
                                                   capas: lecho_secado.py

- T_process es la temperatura del aire en el plenum, a la ENTRADA del
  lecho: la variable que mide y controla CODESYS (setpoint 50 °C).
- RH_process es la HR de ese mismo aire (misma presión de vapor que el
  ambiente: calentar no agrega agua).
- La cinética y la humedad del café se calculan en lecho_secado.py, que
  hace el balance de humedad y de calor latente del aire capa por capa
  (necesario porque el aire a 0.1 m3/min/kg se satura antes de salir
  del lecho: ver data/reference/secador_electrico_dimensionamiento.md).

Balance de energía del plenum (concentrado)
--------------------------------------------
    C_p * dT/dt = P_res*heater_efectivo + m_aire*cp_aire*(T_amb - T)*fan
                  - UA*(T - T_amb)

    heater_efectivo = heater_cmd AND fan_cmd   (enclavamiento de flujo)

El enclavamiento por flujo de aire es obligatorio en calentadores de
ducto (los fabricantes exigen un interruptor de flujo: sin aire, el
elemento se sobrecalienta). En el modelo, si fan_cmd = 0 la resistencia
no entrega potencia aunque heater_cmd = 1; CODESYS debe replicar ese
enclavamiento (heater_cmd := heater_req AND fan_on).

Con el ventilador encendido y la resistencia siempre encendida, el
equilibrio es T = T_amb + P/(m_aire*cp_aire + UA) = ~20.8 + 6.0/0.14 ~ 63 °C
en el día nominal de Chinchiná, así que la resistencia de 6 kW puede
sostener 50 °C aun en la madrugada más fría (margen FS = 1.1) y el
control (todo/nada a 50 °C) la ciclará.

Fuentes (detalle en data/reference/secador_electrico_dimensionamiento.md)
-------------------------------------------------------------------------
González, Sanz & Oliveros (2010), Cenicafé 61(4): T máx. 50 °C; caudal
    específico 0.1 m3/min por kg c.p.s.; potencia de ventilador del
    secador experimental.
Tempco (catálogo de resistencias tubulares aleteadas): elementos
    comerciales de 2 000 W a 240 V; fórmula de dimensionamiento
    kW = SCFM*(T2-T1)/3190 + factor de seguridad.
Montoya (1989), citado en Parra-Coronado et al. (2008): calor específico
    y densidad aparente del café pergamino.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from generador_ambiente import es_kpa

# ---------------------------------------------------------------------------
# Constantes físicas
# ---------------------------------------------------------------------------
CP_AIRE = 1.006      # kJ/(kg aire seco * K)
CP_VAPOR = 1.86      # kJ/(kg vapor * K)
R_AIRE = 0.287       # kJ/(kg*K)
P_ATM_KPA = 86.6     # kPa, presión barométrica a ~1300-1400 msnm (Naranjal);
                     # atmósfera estándar ISA a 1 350 m: 86.6 kPa.


def densidad_aire(t_c: float, p_kpa: float = P_ATM_KPA) -> float:
    """Densidad del aire seco [kg/m3] (gas ideal)."""
    return p_kpa / (R_AIRE * (t_c + 273.15))


def razon_humedad(ea_kpa: float, p_kpa: float = P_ATM_KPA) -> float:
    """Razón de humedad w [kg agua / kg aire seco] a partir de la presión de vapor."""
    return 0.622 * ea_kpa / (p_kpa - ea_kpa)


def presion_vapor_de_w(w: float, p_kpa: float = P_ATM_KPA) -> float:
    """Presión de vapor [kPa] a partir de la razón de humedad."""
    return w * p_kpa / (0.622 + w)


def rh_proceso(t_process_c: float, ea_kpa: float) -> float:
    """HR del aire del plenum [%]: aire ambiente calentado sin agregar agua."""
    return float(np.clip(100.0 * ea_kpa / es_kpa(t_process_c), 0.0, 100.0))


# ---------------------------------------------------------------------------
# Propiedades del café pergamino (Montoya, 1989, en SECAFÉ 2008)
# ---------------------------------------------------------------------------

def calor_especifico_cafe(m_bs_dec: float) -> float:
    """Calor específico del café pergamino [kJ/(kg materia seca * K)],
    Montoya (1989), ec. 12 de SECAFÉ (2008): CP = 1.3556 + 5.7859*M (M
    decimal b.s.). Medido para 11-45 % b.h.; por encima (inicio del
    secado) se usa extrapolado. Interpretación adoptada: por kg de
    materia seca (el intercepto 1.36 corresponde a la materia seca)."""
    return 1.3556 + 5.7859 * m_bs_dec


def densidad_aparente_cafe(m_bs_pct: float) -> float:
    """Densidad aparente del café pergamino [kg/m3] (Montoya, 1989, ec. 17
    de SECAFÉ 2008): DA = 365.884 + 2.7067*M, M en % b.s."""
    return 365.884 + 2.7067 * m_bs_pct


# ---------------------------------------------------------------------------
# Diseño del secador (lote de 80 kg c.p.s. - decisión de Luis, 29 sept 2026)
# ---------------------------------------------------------------------------

@dataclass
class ParametrosSecador:
    """Parámetros del secador eléctrico de capa estática.

    Todos derivados de fuentes o de un cálculo documentado en
    data/reference/secador_electrico_dimensionamiento.md.
    """

    masa_cps_kg: float = 80.0
    """Café pergamino seco por lote [kg] (decisión de diseño, 29 sept 2026)."""

    caudal_especifico_m3_min_kg: float = 0.1
    """m3/min por kg c.p.s. (óptimo para lecho estático; González et al., 2010)."""

    espesor_lecho_m: float = 0.20
    """20 cm: menor espesor evaluado por González et al. (2010), el de mayor
    ahorro de energía; también es el orden de capa de los secadores
    estáticos de Cenicafé."""

    potencia_resistencia_kw: float = 6.0
    """3 elementos tubulares aleteados de 2 000 W a 240 V (Tempco). Requerido:
    0.0678 kW/kg c.p.s. * 80 kg = 5.43 kW (FS 1.1) -> se instala 6.0 kW."""

    potencia_ventilador_kw: float = 0.20
    """Potencia específica del ventilador del secador de González et al.
    (2010): 4.95 kW para 2 000 kg c.p.s. = 2.475 W/kg -> 80 kg ~ 0.20 kW.
    Escalado lineal con la masa (mismo caudal específico y espesor)."""

    capacidad_plenum_kj_k: float = 15.0
    """Masa térmica de resistencia + plenum: ~30 kg de lámina de acero
    (cp 0.49 kJ/kg K). Estimación geométrica; su efecto es solo una
    constante de tiempo de ~2 min, despreciable frente a horas de secado
    (ver prueba de sensibilidad en el .md)."""

    ua_plenum_kw_k: float = 0.003
    """Pérdidas del plenum aislado: ~3 m2 x ~1 W/(m2 K). Despreciable frente
    a m_aire*cp (~0.14 kW/K); se incluye por completitud."""

    t_max_seguridad_c: float = 90.0
    """Corte por sobretemperatura del elemento (protección), no setpoint."""

    t_setpoint_c: float = 50.0
    """Temperatura máxima del aire/grano sin daño (González et al., 2010)."""

    @property
    def caudal_m3_s(self) -> float:
        return self.caudal_especifico_m3_min_kg * self.masa_cps_kg / 60.0

    def masa_aire_kg_s(self, t_c: float = 20.0) -> float:
        """Flujo másico de aire seco [kg/s], caudal medido a la entrada del ventilador."""
        return self.caudal_m3_s * densidad_aire(t_c)

    def area_lecho_m2(self, m0_bs_pct: float) -> float:
        """Área de la bandeja para que el lote húmedo quepa en espesor_lecho_m."""
        masa_humeda = self.masa_cps_kg * (1.0 + m0_bs_pct / 100.0)
        return masa_humeda / densidad_aparente_cafe(m0_bs_pct) / self.espesor_lecho_m


def potencia_requerida_kw(p: ParametrosSecador, t_amb_min_c: float = 14.3, fs: float = 1.1) -> float:
    """P = rho*V*cp*(T_set - T_amb_min)*FS [kW]. T_amb_min = percentil 1 del
    generador de ambiente de Chinchiná (ver .md)."""
    return p.masa_aire_kg_s(t_amb_min_c) * CP_AIRE * (p.t_setpoint_c - t_amb_min_c) * fs


def paso_plenum(
    t_process_c: float,
    t_ambiente_c: float,
    heater_cmd: int,
    fan_cmd: int,
    dt_h: float,
    p: ParametrosSecador,
) -> tuple[float, float]:
    """Avanza la temperatura del plenum ``dt_h`` horas.

    Integra exactamente la EDO lineal de primer orden en el paso (no Euler),
    por lo que es estable con cualquier dt. Devuelve (T_nueva, potencia
    eléctrica de la resistencia efectivamente entregada [kW]).
    """
    heater = 1 if (heater_cmd and fan_cmd) else 0          # enclavamiento de flujo
    p_res = p.potencia_resistencia_kw * heater
    g = p.ua_plenum_kw_k + (p.masa_aire_kg_s(t_ambiente_c) * CP_AIRE if fan_cmd else 0.0)  # kW/K
    t_eq = t_ambiente_c + p_res / g
    tau_s = p.capacidad_plenum_kj_k / g
    t_nuevo = t_eq + (t_process_c - t_eq) * math.exp(-dt_h * 3600.0 / tau_s)
    return float(min(t_nuevo, p.t_max_seguridad_c)), p_res


if __name__ == "__main__":
    p = ParametrosSecador()
    m0_bs = 100.0 * 55.0 / 45.0
    print(f"Lote: {p.masa_cps_kg} kg c.p.s. | caudal {p.caudal_m3_s * 60:.1f} m3/min "
          f"| aire {p.masa_aire_kg_s():.3f} kg/s | area lecho {p.area_lecho_m2(m0_bs):.2f} m2")
    print(f"Potencia requerida (FS 1.1, T_amb 14.3 C): {potencia_requerida_kw(p):.2f} kW "
          f"-> instalada {p.potencia_resistencia_kw} kW")
    t = 20.8
    for _ in range(40):
        t, _ = paso_plenum(t, 20.8, 1, 1, 0.05, p)
    print(f"Plenum con resistencia siempre encendida (T_amb 20.8 C): {t:.1f} C")
    print(f"HR del plenum a 50 C con ea=1.81 kPa: {rh_proceso(50.0, 1.81):.1f} %")

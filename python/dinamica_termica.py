"""
dinamica_termica.py
====================

Secador mecánico con RESISTENCIA ELÉCTRICA de la propuesta supervisada:
dimensionamiento, balance de energía del aire de secado (plenum) y
propiedades físicas del lecho de café.
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
# Diseño del secador (lote de 80 kg c.p.s.)
# ---------------------------------------------------------------------------

@dataclass
class ParametrosSecador:
    """Parámetros del secador eléctrico de capa estática.

    Todos derivados de fuentes o de un cálculo documentado en
    data/reference/secador_electrico_dimensionamiento.md.
    """

    masa_cps_kg: float = 80.0
    """Café pergamino seco por lote [kg] (decisión de diseño)."""

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
    Escalado lineal con la masa (mismo caudal específico y espesor).
    Equipo comercial: Soler & Palau CBM/6-180/180-N-72W,
    ~118 Pa a 480 m3/h según la curva del fabricante; 220 V x 1.0 A x FP 0.9
    = 0.20 kW de consumo máximo. Ver data/reference/equipos_energia.md."""

    caudal_min_frac: float = 0.30
    """Caudal mínimo del ventilador como fracción del nominal (manipulada 2). Por debajo de ~30 % un ventilador centrífugo con regulador
    de tensión pierde par y el calentador de ducto queda sin flujo seguro;
    se fija como límite de operación (criterio propio, declarado)."""

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

    # --- Reposo (ventilador apagado) --------------------------------------
    # La planta NO se congela al detener el proceso: con el ventilador
    # apagado el lecho sigue intercambiando calor y humedad. Ficha y
    # fuentes: data/reference/reposo_tiro_natural.md.

    presion_sistema_pa: float = 100.0
    """Pérdida de presión de diseño del sistema (lecho + resistencia +
    compuertas + ductos) al caudal nominal de 8 m3/min
    (data/reference/equipos_energia.md). Se usa para estimar el tiro natural
    con una resistencia LINEAL en el caudal (régimen de baja velocidad de
    Shedd en el lecho; para los accesorios turbulentos es conservador)."""

    altura_tiro_natural_m: float = 0.6
    """Altura de la columna de aire caliente plenum + lecho + cámara superior
    que genera el efecto chimenea (estimación geométrica propia, declarada)."""

    h_conv_natural_w_m2k: float = 4.0
    """Coeficiente de convección natural de las superficies del lecho hacia
    el ambiente de la cámara (rango típico 2-25 W/m2K para convección libre
    en gases; Incropera et al., 2007, tabla 1.1). Se toma un valor bajo
    porque la bandeja está dentro de la cámara (criterio propio)."""

    area_perdidas_lecho_m2: float = 2.2
    """Superficie del lecho que pierde calor en reposo: cara superior
    (~1.3 m2, ver area_lecho_m2) + paredes de la bandeja (~0.9 m2 con 20 cm
    de espesor). Con ventilador encendido estas pérdidas (~9 W/K) son <7 %
    del término m_aire*cp (~140 W/K) y se desprecian, como antes."""

    @property
    def caudal_m3_s(self) -> float:
        return self.caudal_especifico_m3_min_kg * self.masa_cps_kg / 60.0

    def masa_aire_kg_s(self, t_c: float = 20.0, fan_frac: float = 1.0) -> float:
        """Flujo másico de aire seco [kg/s], caudal medido a la entrada del
        ventilador. ``fan_frac``: fracción del caudal nominal (manipulada 2)."""
        return self.caudal_m3_s * fan_frac * densidad_aire(t_c)

    def limitar_fan_frac(self, fan_frac: float) -> float:
        """Recorta la consigna de caudal al rango [caudal_min_frac, 1]."""
        return min(1.0, max(self.caudal_min_frac, float(fan_frac)))

    def potencia_ventilador_frac_kw(self, fan_frac: float) -> float:
        """Potencia eléctrica del ventilador a caudal parcial por las leyes de
        afinidad (P proporcional al cubo del caudal; ASHRAE Handbook -
        HVAC Systems and Equipment, cap. Fans). Es el caso ideal (variador
        de frecuencia); con regulador de tensión el ahorro real es menor.
        El ventilador es ~5 % de la energía total del secado, así que esta
        incertidumbre pesa poco en el balance."""
        return self.potencia_ventilador_kw * fan_frac**3

    def area_lecho_m2(self, m0_bs_pct: float) -> float:
        """Área de la bandeja para que el lote húmedo quepa en espesor_lecho_m."""
        masa_humeda = self.masa_cps_kg * (1.0 + m0_bs_pct / 100.0)
        return masa_humeda / densidad_aparente_cafe(m0_bs_pct) / self.espesor_lecho_m


def potencia_requerida_kw(p: ParametrosSecador, t_amb_min_c: float = 14.3, fs: float = 1.1) -> float:
    """P = rho*V*cp*(T_set - T_amb_min)*FS [kW]. T_amb_min = percentil 1 del
    generador de ambiente de Chinchiná (ver .md)."""
    return p.masa_aire_kg_s(t_amb_min_c) * CP_AIRE * (p.t_setpoint_c - t_amb_min_c) * fs


G_GRAVEDAD = 9.81  # m/s2


def masa_aire_tiro_natural_kg_s(t_caliente_c: float, t_ambiente_c: float, p: ParametrosSecador) -> float:
    """Flujo de aire por efecto chimenea con el ventilador APAGADO [kg/s].

    Tiro: dP = g * H * (rho_amb - rho_caliente)  (ASHRAE Fundamentals,
    cap. 16, efecto chimenea). Resistencia del sistema lineal en el caudal,
    anclada en el punto de diseño (presion_sistema_pa a caudal nominal):
    Q = Q_nom * dP / dP_diseño. Si el aire interior no está más caliente
    que el exterior no hay tiro ascendente (0). Ver
    data/reference/reposo_tiro_natural.md.
    """
    if t_caliente_c <= t_ambiente_c:
        return 0.0
    rho_amb = densidad_aire(t_ambiente_c)
    dp = G_GRAVEDAD * p.altura_tiro_natural_m * (rho_amb - densidad_aire(t_caliente_c))
    q_m3_s = p.caudal_m3_s * dp / p.presion_sistema_pa
    return q_m3_s * rho_amb


def paso_plenum(
    t_process_c: float,
    t_ambiente_c: float,
    heater_cmd: int,
    fan_cmd: int,
    dt_h: float,
    p: ParametrosSecador,
    fan_frac: float = 1.0,
    m_aire_natural_kg_s: float = 0.0,
) -> tuple[float, float]:
    """Avanza la temperatura del plenum ``dt_h`` horas.

    Integra exactamente la EDO lineal de primer orden en el paso (no Euler),
    por lo que es estable con cualquier dt. Devuelve (T_nueva, potencia
    eléctrica de la resistencia efectivamente entregada [kW]).

    ``m_aire_natural_kg_s``: con el ventilador apagado, aire que entra por
    tiro natural (masa_aire_tiro_natural_kg_s); 0 = solo pérdidas UA.

    Protección por sobretemperatura: si con la resistencia
    encendida el plenum superaría ``t_max_seguridad_c``, el corte térmico
    abre y el paso se integra con la resistencia APAGADA.
    """
    heater = 1 if (heater_cmd and fan_cmd) else 0          # enclavamiento de flujo
    m_aire = p.masa_aire_kg_s(t_ambiente_c, fan_frac) if fan_cmd else m_aire_natural_kg_s
    g = p.ua_plenum_kw_k + m_aire * CP_AIRE  # kW/K
    tau_s = p.capacidad_plenum_kj_k / g

    def integrar(p_res: float) -> float:
        t_eq = t_ambiente_c + p_res / g
        return t_eq + (t_process_c - t_eq) * math.exp(-dt_h * 3600.0 / tau_s)

    p_res = p.potencia_resistencia_kw * heater
    t_nuevo = integrar(p_res)
    if heater and t_nuevo > p.t_max_seguridad_c:
        p_res = 0.0
        t_nuevo = integrar(0.0)
    return float(t_nuevo), p_res


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

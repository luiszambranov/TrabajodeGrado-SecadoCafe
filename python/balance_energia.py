"""
balance_energia.py
===================

Balance de energía COMÚN a las tres estrategias de secado (solar pasiva,
solar activa y propuesta supervisada con resistencia eléctrica), para
compararlas con la misma métrica.
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Métricas
--------
Para cada corrida (mismo lote de 80 kg c.p.s., de 55 a 11 % b.h.):

1. Energía eléctrica COMPRADA [kWh y kWh/kg c.p.s.]: lo que se paga a la
   red. Alimenta el objetivo 4 (costo de operación).
2. Energía TOTAL aplicada [kWh]: eléctrica + solar que incide sobre el área
   de secado durante el proceso.
3. Consumo específico de energía, SEC [kJ/kg de agua evaporada]: energía
   total / agua evaporada. Es la métrica estándar de eficiencia de un
   secador y permite comparar el sol con la resistencia en la misma unidad.
4. Eficiencia térmica [%]: energía mínima para evaporar el agua (agua x
   calor latente) / energía total aplicada.

Equipos (comerciales, para que el costo sea real)
--------------------------------------------------
Supervisada (secador_electrico.py):
    - Resistencia: 3 elementos tubulares aleteados de 2 000 W / 240 V
      (Tempco), 6 kW. Ver data/reference/secador_electrico_dimensionamiento.md.
    - Ventilador: centrífugo de baja presión Soler & Palau
      CBM/6-180/180-N-72W (motor 72 W, 960 rpm, 1.0 A máx. a 220 V).
      Curva del fabricante: a 480 m3/h (= 8 m3/min, el caudal de diseño)
      entrega ~118 Pa a 220 V; la caída de presión estimada del sistema
      es ~100 Pa (ver data/reference/equipos_energia.md). Potencia
      eléctrica de cálculo: 220 V x 1.0 A x FP 0.9 = 0.20 kW (máximo de
      placa), igual a ParametrosSecador.potencia_ventilador_kw.
Solar activa (linea_base_activa.py):
    - 1 extractor helicoidal Soler & Palau HCM-225N: 40 W, 695 m3/h,
      encendido de 06:00 a 18:00 (todo/nada por horario,
      docs/seleccion_lineas_base.md). Escala con Madhava et al. (2017):
      secador de invernadero de 9.5 m2 con 1 extractor de 40 W.
Solar pasiva: sin consumo eléctrico.

Radiación solar
---------------
Radiación global media en la sede de Cenicafé (Chinchiná): 4 582 Wh/m2/día
(Cenicafé 54(2), 110-133). Se reparte en medio seno de 06:00 a 18:00 (el
mismo perfil de generador_ambiente.incremento_solar):
    G(h) = G_max * sin(pi*(h-6)/12),  G_max = 4.582*pi/24 = 0.600 kW/m2
Área de secado solar: 11.1 m2 (7.2 kg c.p.s./m2; Peñuela-Martínez et
al., 2025).
Limitación: se usa la radiación MEDIA en todos los días (no hay serie de
radiación por realización Monte Carlo).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import cinetica_roa as roa

RADIACION_DIARIA_KWH_M2 = 4.582      # Cenicafé 54(2), media anual, sede Chinchiná
HORA_SALIDA_SOL, HORA_PUESTA_SOL = 6.0, 18.0
AREA_SOLAR_M2 = 80.0 / 7.2           # Peñuela-Martínez et al. (2025)
POTENCIA_EXTRACTOR_ACTIVA_KW = 0.040  # S&P HCM-225N
MASA_CPS_KG = 80.0
CALOR_LATENTE_REF_KJ_KG = 2430.0      # agua libre a ~30 °C (tablas de vapor); el
                                      # agua ligada del café requiere más (Trejos 1989)


def agua_a_evaporar_kg(m0_bh: float = roa.M0_BH_PCT, mf_bh: float = roa.HUMEDAD_OBJETIVO_BH_PCT,
                       masa_cps_kg: float = MASA_CPS_KG) -> float:
    """Agua retirada de 55 a 11 % b.h. [kg]. La materia seca es 89 % del c.p.s."""
    ms = masa_cps_kg * (1.0 - roa.HUMEDAD_OBJETIVO_BH_PCT / 100.0)
    return ms * (roa.bh_a_bs(m0_bh) - roa.bh_a_bs(mf_bh)) / 100.0


def horas_de_sol(t_fin_h: float, t_ini_h: float = 0.0) -> float:
    """Horas entre 06:00 y 18:00 dentro de [t_ini, t_fin] (t=0 a medianoche)."""
    total, d = 0.0, math.floor(t_ini_h / 24.0)
    while d * 24.0 < t_fin_h:
        a = max(t_ini_h, d * 24.0 + HORA_SALIDA_SOL)
        b = min(t_fin_h, d * 24.0 + HORA_PUESTA_SOL)
        total += max(0.0, b - a)
        d += 1
    return total


def radiacion_incidente_kwh_m2(t_fin_h: float, t_ini_h: float = 0.0,
                               diaria_kwh_m2: float = RADIACION_DIARIA_KWH_M2) -> float:
    """Integral exacta de G(h) = G_max*sin(pi*(h-6)/12) entre t_ini y t_fin."""
    largo = HORA_PUESTA_SOL - HORA_SALIDA_SOL
    g_max = diaria_kwh_m2 * math.pi / (2.0 * largo)

    def acumulada(t: float) -> float:
        dias, h = divmod(t, 24.0)
        x = min(max(h - HORA_SALIDA_SOL, 0.0), largo)
        parcial = g_max * largo / math.pi * (1.0 - math.cos(math.pi * x / largo))
        return dias * diaria_kwh_m2 + parcial

    return acumulada(t_fin_h) - acumulada(t_ini_h)


@dataclass
class BalanceEnergia:
    estrategia: str
    t_obj_h: float
    agua_kg: float
    electrica_kwh: float
    solar_kwh: float

    @property
    def total_kwh(self) -> float:
        return self.electrica_kwh + self.solar_kwh

    @property
    def comprada_kwh_por_kg_cps(self) -> float:
        return self.electrica_kwh / MASA_CPS_KG

    @property
    def sec_total_kj_kg_agua(self) -> float:
        return 3600.0 * self.total_kwh / self.agua_kg

    @property
    def sec_comprada_kj_kg_agua(self) -> float:
        return 3600.0 * self.electrica_kwh / self.agua_kg

    @property
    def eficiencia_termica_pct(self) -> float:
        return 100.0 * self.agua_kg * CALOR_LATENTE_REF_KJ_KG / (3600.0 * self.total_kwh)

    def costo_cop(self, tarifa_cop_kwh: float) -> float:
        """Costo de la energía comprada [COP] con la tarifa dada."""
        return self.electrica_kwh * tarifa_cop_kwh


def balance_pasiva(t_obj_h: float, m0_bh: float = roa.M0_BH_PCT) -> BalanceEnergia:
    solar = radiacion_incidente_kwh_m2(t_obj_h) * AREA_SOLAR_M2
    return BalanceEnergia("Solar pasiva", t_obj_h, agua_a_evaporar_kg(m0_bh), 0.0, solar)


def balance_activa(t_obj_h: float, potencia_kw: float = POTENCIA_EXTRACTOR_ACTIVA_KW,
                   m0_bh: float = roa.M0_BH_PCT) -> BalanceEnergia:
    solar = radiacion_incidente_kwh_m2(t_obj_h) * AREA_SOLAR_M2
    elec = potencia_kw * horas_de_sol(t_obj_h)
    return BalanceEnergia("Solar activa", t_obj_h, agua_a_evaporar_kg(m0_bh), elec, solar)


def balance_supervisada(resultado) -> BalanceEnergia:
    """``resultado``: control_supervisado.ResultadoSupervisada."""
    c = resultado.contadores
    return BalanceEnergia("Supervisada", resultado.t_obj_h, c.agua_evaporada_kg, c.energia_electrica_kwh, 0.0)


def balances(clima_dias) -> list[BalanceEnergia]:
    """Corre las tres estrategias con la MISMA realización de clima."""
    from control_supervisado import simular_supervisada
    from escenario_sol_abierto import condiciones_patio
    from linea_base_activa import condiciones_activa

    tp = roa.simular(condiciones_patio(clima_dias), t_max_h=1500.0).t_objetivo_h
    ta = roa.simular(condiciones_activa(clima_dias), t_max_h=1500.0).t_objetivo_h
    return [balance_pasiva(tp), balance_activa(ta), balance_supervisada(simular_supervisada(clima_dias))]


if __name__ == "__main__":
    import generador_ambiente as amb

    print(f"Agua a evaporar (80 kg c.p.s., 55 -> 11 % b.h.): {agua_a_evaporar_kg():.1f} kg")
    print(f"Comprobación: radiación de 1 día = {radiacion_incidente_kwh_m2(24.0):.3f} kWh/m2 "
          f"(dato {RADIACION_DIARIA_KWH_M2})\n")
    print(f"{'Estrategia':14s} {'t_obj':>8s} {'Eléctrica':>10s} {'Solar':>9s} {'Total':>9s} "
          f"{'kWh/kg cps':>11s} {'SEC total':>10s} {'SEC compr.':>11s} {'Efic.':>6s}")
    print(f"{'':14s} {'[h]':>8s} {'[kWh]':>10s} {'[kWh]':>9s} {'[kWh]':>9s} {'(comprada)':>11s} "
          f"{'[kJ/kg]':>10s} {'[kJ/kg]':>11s} {'[%]':>6s}")
    for b in balances([amb.condiciones_nominales()]):
        print(f"{b.estrategia:14s} {b.t_obj_h:8.1f} {b.electrica_kwh:10.2f} {b.solar_kwh:9.1f} {b.total_kwh:9.1f} "
              f"{b.comprada_kwh_por_kg_cps:11.3f} {b.sec_total_kj_kg_agua:10.0f} {b.sec_comprada_kj_kg_agua:11.0f} "
              f"{b.eficiencia_termica_pct:6.1f}")

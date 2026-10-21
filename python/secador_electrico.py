"""
secador_electrico.py
=====================

Núcleo físico de la propuesta supervisada, SIN Modbus: plenum con
resistencia eléctrica (dinamica_termica.py) + lecho de café por capas
(lecho_secado.py, Thompson + Roa-Cenicafé) + contabilidad de energía y
de los indicadores secundarios de la campaña.
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Lo usan dos clientes con la MISMA física:
    - planta_secado.ModeloSecadoPlant: detrás del servidor Modbus, con los
      comandos que escribe CODESYS (demostración de la arquitectura/HMI).
    - control_supervisado.simular_supervisada: réplica en Python de la
      lógica de PLC_PRG para la campaña Monte Carlo (reproducible por
      semilla, sin tiempo real).

Relojes (21 oct 2026)
---------------------
- ``t_fisico_h``: reloj de la PLANTA (hora del clima; t = 0 es la
  medianoche del día 0 más ``t_inicio_h``). Avanza siempre, también con
  el proceso detenido, y NO se reinicia con un lote nuevo: el ambiente
  sigue su ciclo día/noche.
- ``t_h``: tiempo del LOTE (desde que se cargó el café); avanza también
  en las paradas. El tiempo de secado activo lo cuenta quien conoce el
  estado del proceso (planta_secado.py / control_supervisado.py).
En la campaña Monte Carlo el ventilador nunca se apaga y t_inicio_h = 0,
así que t_fisico_h = t_h y los resultados no cambian.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cinetica_roa as roa
import generador_ambiente as amb
from dinamica_termica import ParametrosSecador, masa_aire_tiro_natural_kg_s, paso_plenum, rh_proceso
from lecho_secado import LechoThompson


@dataclass
class EstadoSecador:
    t_h: float                 # tiempo de proceso [h]
    t_ambiente_c: float
    rh_ambiente_pct: float
    t_process_c: float         # aire del plenum (entrada al lecho) - variable controlada
    rh_process_pct: float
    m_coffee_bh_pct: float     # humedad promedio del lote
    m_capa_max_bh_pct: float   # capa más húmeda
    m_capa_min_bh_pct: float   # capa más seca
    t_salida_c: float          # aire a la salida del lecho
    caudal_m3_min: float = 0.0 # caudal de aire real (manipulada 2) [m3/min]
    t_fisico_h: float = 0.0    # reloj de la planta / clima [h]
    potencia_res_kw: float = 0.0   # potencia media de la resistencia en el paso [kW]
    caudal_natural_m3_min: float = 0.0  # tiro natural con ventilador apagado [m3/min]


@dataclass
class Contadores:
    """Indicadores secundarios (metodologia_estadistica_monte_carlo.md, 6.4)."""

    energia_resistencia_kwh: float = 0.0
    energia_ventilador_kwh: float = 0.0
    agua_evaporada_kg: float = 0.0
    horas_grano_sobre_50c: float = 0.0
    horas_rehumectacion: float = 0.0
    horas_fuera_de_rango: float = 0.0

    @property
    def energia_electrica_kwh(self) -> float:
        return self.energia_resistencia_kwh + self.energia_ventilador_kwh


class SecadorElectrico:
    def __init__(
        self,
        clima_dias: Sequence[amb.CondicionesClimaticas] | None = None,
        p: ParametrosSecador | None = None,
        m0_bh_pct: float = roa.M0_BH_PCT,
        t_inicio_h: float = 0.0,
    ) -> None:
        self.p = p or ParametrosSecador()
        self.clima = list(clima_dias or [amb.condiciones_nominales()])
        self.t_fisico_h = float(t_inicio_h)
        t_amb0, _, _ = amb.ambiente_en(self.t_fisico_h, self.clima)
        self.t_h = 0.0
        self.t_process = t_amb0
        self.lecho = LechoThompson(self.p, m0_bh_pct=m0_bh_pct, t_inicial_c=t_amb0)
        self.c = Contadores()
        self._t_salida = t_amb0
        self._caudal_m3_min = 0.0
        self._p_res_kw = 0.0
        self._caudal_nat_m3_min = 0.0

    def nuevo_lote(self, m0_bh_pct: float = roa.M0_BH_PCT) -> None:
        """Carga un lote nuevo: café a la temperatura ambiente con la humedad
        inicial, tiempo del lote y contadores en cero. La CÁMARA (plenum)
        conserva su temperatura y el reloj de la planta sigue: un lote nuevo
        no enfría la cámara instantáneamente (guía de cierre, R4)."""
        t_amb, _, _ = amb.ambiente_en(self.t_fisico_h, self.clima)
        self.lecho = LechoThompson(self.p, m0_bh_pct=m0_bh_pct, t_inicial_c=t_amb)
        self.c = Contadores()
        self.t_h = 0.0

    def paso(self, heater_cmd: int, fan_cmd: int, dt_h: float, control=None, dt_ciclo_s: float = 1.0,
             flujo_invertido: bool = False, fan_frac: float = 1.0) -> EstadoSecador:
        """Avanza ``dt_h`` horas.

        Sin ``control``: heater_cmd/fan_cmd constantes en el paso (uso desde
        Modbus/CODESYS, que decide en cada ciclo del servidor).
        Con ``control`` (función T_process -> heater_cmd): el plenum se
        integra en ciclos de ``dt_ciclo_s`` segundos con el controlador
        evaluado en cada ciclo (como el PLC), y el lecho recibe la
        temperatura PROMEDIO del plenum en el paso. El lecho (horas) y el
        plenum (minutos) tienen escalas de tiempo separadas, así que esto
        conserva la energía y la temperatura media sin integrar el lecho
        cada segundo.
        """
        t_amb, rh_amb, ea = amb.ambiente_en(self.t_fisico_h, self.clima)
        ff = self.p.limitar_fan_frac(fan_frac) if fan_cmd else 0.0
        self._caudal_m3_min = self.p.caudal_m3_s * 60.0 * ff
        self._caudal_nat_m3_min = 0.0
        if not fan_cmd:
            return self._paso_reposo(dt_h, t_amb, rh_amb, ea)
        if control is None:
            self.t_process, p_res = paso_plenum(self.t_process, t_amb, heater_cmd, fan_cmd, dt_h, self.p, ff)
            t_lecho = self.t_process
            e_res = p_res * dt_h
        else:
            n = max(1, int(round(dt_h * 3600.0 / dt_ciclo_s)))
            h = dt_h / n
            suma_t = e_res = 0.0
            for _ in range(n):
                hc = control(self.t_process)
                self.t_process, p_res = paso_plenum(self.t_process, t_amb, hc, fan_cmd, h, self.p, ff)
                suma_t += self.t_process
                e_res += p_res * h
            t_lecho = suma_t / n
        r = self.lecho.paso(t_lecho, ea, fan_cmd, dt_h, self.p.masa_aire_kg_s(t_amb, ff), flujo_invertido)
        self._t_salida = r.t_salida_c

        self.c.energia_resistencia_kwh += e_res
        self.c.energia_ventilador_kwh += self.p.potencia_ventilador_frac_kw(ff) * dt_h if fan_cmd else 0.0
        self.c.agua_evaporada_kg += r.agua_evaporada_kg
        self.c.horas_grano_sobre_50c += dt_h if r.t_grano_max_c > 50.0 + 1e-6 else 0.0
        self.c.horas_rehumectacion += dt_h if r.rehumectacion else 0.0
        self.c.horas_fuera_de_rango += dt_h if r.fuera_de_rango else 0.0
        self._p_res_kw = e_res / dt_h if dt_h > 0 else 0.0
        self.t_h += dt_h
        self.t_fisico_h += dt_h
        return self.estado(t_amb, rh_amb, ea)

    def _paso_reposo(self, dt_h: float, t_amb: float, rh_amb: float, ea: float) -> EstadoSecador:
        """Ventilador apagado (proceso detenido, fallo o fin de secado): la
        resistencia no entrega potencia (enclavamiento de flujo), el plenum
        y el lecho se enfrían hacia el ambiente y el tiro natural produce un
        secado residual pequeño. La física NO se congela."""
        t_col = 0.5 * (self.t_process + float(self.lecho.t_grano.mean()))   # columna caliente
        m_nat = masa_aire_tiro_natural_kg_s(t_col, t_amb, self.p)
        from dinamica_termica import densidad_aire
        self._caudal_nat_m3_min = 60.0 * m_nat / densidad_aire(t_amb)
        t_plenum0 = self.t_process
        self.t_process, _ = paso_plenum(self.t_process, t_amb, 0, 0, dt_h, self.p, m_aire_natural_kg_s=m_nat)
        t_entrada = 0.5 * (t_plenum0 + self.t_process)
        r = self.lecho.paso_reposo(t_entrada, ea, dt_h, m_nat, t_amb)
        self._t_salida = r.t_salida_c
        self.c.agua_evaporada_kg += r.agua_evaporada_kg
        self.c.horas_grano_sobre_50c += dt_h if r.t_grano_max_c > 50.0 + 1e-6 else 0.0
        self.c.horas_rehumectacion += dt_h if r.rehumectacion else 0.0
        self.c.horas_fuera_de_rango += dt_h if r.fuera_de_rango else 0.0
        self._p_res_kw = 0.0
        self.t_h += dt_h
        self.t_fisico_h += dt_h
        return self.estado(t_amb, rh_amb, ea)

    def estado(self, t_amb: float | None = None, rh_amb: float | None = None, ea: float | None = None) -> EstadoSecador:
        if t_amb is None:
            t_amb, rh_amb, ea = amb.ambiente_en(self.t_fisico_h, self.clima)
        return EstadoSecador(
            t_h=self.t_h,
            t_ambiente_c=t_amb,
            rh_ambiente_pct=rh_amb,
            t_process_c=self.t_process,
            rh_process_pct=rh_proceso(self.t_process, ea),
            m_coffee_bh_pct=self.lecho.m_bh_promedio,
            m_capa_max_bh_pct=self.lecho.m_bh_max,
            m_capa_min_bh_pct=self.lecho.m_bh_min,
            t_salida_c=self._t_salida,
            caudal_m3_min=self._caudal_m3_min,
            t_fisico_h=self.t_fisico_h,
            potencia_res_kw=self._p_res_kw,
            caudal_natural_m3_min=self._caudal_nat_m3_min,
        )

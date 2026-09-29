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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import cinetica_roa as roa
import generador_ambiente as amb
from dinamica_termica import ParametrosSecador, paso_plenum, rh_proceso
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
    ) -> None:
        self.p = p or ParametrosSecador()
        self.clima = list(clima_dias or [amb.condiciones_nominales()])
        t_amb0, _, _ = amb.ambiente_en(0.0, self.clima)
        self.t_h = 0.0
        self.t_process = t_amb0
        self.lecho = LechoThompson(self.p, m0_bh_pct=m0_bh_pct, t_inicial_c=t_amb0)
        self.c = Contadores()
        self._t_salida = t_amb0

    def paso(self, heater_cmd: int, fan_cmd: int, dt_h: float, control=None, dt_ciclo_s: float = 1.0,
             flujo_invertido: bool = False) -> EstadoSecador:
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
        t_amb, rh_amb, ea = amb.ambiente_en(self.t_h, self.clima)
        if control is None:
            self.t_process, p_res = paso_plenum(self.t_process, t_amb, heater_cmd, fan_cmd, dt_h, self.p)
            t_lecho = self.t_process
            e_res = p_res * dt_h
        else:
            n = max(1, int(round(dt_h * 3600.0 / dt_ciclo_s)))
            h = dt_h / n
            suma_t = e_res = 0.0
            for _ in range(n):
                hc = control(self.t_process)
                self.t_process, p_res = paso_plenum(self.t_process, t_amb, hc, fan_cmd, h, self.p)
                suma_t += self.t_process
                e_res += p_res * h
            t_lecho = suma_t / n
        r = self.lecho.paso(t_lecho, ea, fan_cmd, dt_h, self.p.masa_aire_kg_s(t_amb), flujo_invertido)
        self._t_salida = r.t_salida_c

        self.c.energia_resistencia_kwh += e_res
        self.c.energia_ventilador_kwh += self.p.potencia_ventilador_kw * dt_h * (1 if fan_cmd else 0)
        self.c.agua_evaporada_kg += r.agua_evaporada_kg
        self.c.horas_grano_sobre_50c += dt_h if r.t_grano_max_c > 50.0 + 1e-6 else 0.0
        self.c.horas_rehumectacion += dt_h if r.rehumectacion else 0.0
        self.c.horas_fuera_de_rango += dt_h if r.fuera_de_rango else 0.0
        self.t_h += dt_h
        return self.estado(t_amb, rh_amb, ea)

    def estado(self, t_amb: float | None = None, rh_amb: float | None = None, ea: float | None = None) -> EstadoSecador:
        if t_amb is None:
            t_amb, rh_amb, ea = amb.ambiente_en(self.t_h, self.clima)
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
        )

"""
estimacion_energia.py
=======================

Primera estimación de energía (piso termodinámico): calor latente
mínimo necesario para evaporar el agua removida en cada una de las tres
estrategias de secado del proyecto (línea base mínima, línea base
activa, propuesta supervisada).
Semana 5 - "Modelo base validado".

Alcance v0.1 (explícito)
--------------------------
Esta es la energía térmica MÍNIMA (el "piso" termodinámico: el calor
de vaporización del agua pura a la temperatura de proceso), NO el
consumo energético real de cada sistema. No incluye:
    - Energía eléctrica de ventiladores/actuadores.
    - Pérdidas térmicas de la cámara, calentamiento del aire seco, del
      producto o de la estructura.
    - El efecto de sorción (el agua ligada en un material higroscópico
      como el café requiere más energía para evaporarse que el agua
      libre; esta estimación usa el calor latente del agua pura, una
      simplificación estándar para un primer cálculo).
Sirve como referencia de orden de magnitud y como piso físico para
comparar contra el consumo real medido/estimado en la semana 9
(economía), no como una comparación final de eficiencia entre
estrategias.

Fórmula del calor latente
----------------------------
Se usa la aproximación lineal estándar (válida 0-100°C):

    L(T) = 2501 - 2.361 * T      [kJ/kg], T en °C

(p. ej. Cengel & Boles, *Thermodynamics: An Engineering Approach* —
ya citado en el paper de Phitakwinai et al. 2019 para las presiones de
vapor del aire de secado).

Nota importante sobre las bases de humedad
---------------------------------------------
Las fuentes de cada estrategia reportan la humedad en bases distintas
y sin M0/Mf equalizados entre sí (ver docstrings de cada
`_agua_removida_*`). Esta primera estimación usa el M0/Mf que reporta
CADA fuente tal cual, por lo que las diferencias de energía entre
estrategias reflejan en parte diferencias de humedad objetivo de cada
fuente bibliográfica, no solo la eficiencia del método. Una comparación
justa (misma M0/Mf para las tres) queda para cuando se fije el diseño
experimental completo (semana 7).
"""

from __future__ import annotations

from dataclasses import dataclass


def calor_latente_kj_kg(t_c: float) -> float:
    """Calor latente de vaporizacion del agua pura [kJ/kg] a temperatura t_c [°C]."""
    return 2501.0 - 2.361 * t_c


@dataclass
class ResultadoEnergia:
    estrategia: str
    masa_dry_matter_kg: float
    agua_removida_kg: float
    temperatura_proceso_c: float
    calor_latente_kj_kg: float
    energia_kj: float
    energia_kwh: float


def _agua_removida_base_seca(masa_humeda_inicial_kg: float, m0_db: float, mf_db: float) -> tuple[float, float]:
    """Agua removida [kg] dado M0/Mf en base seca (decimal, kg agua/kg materia seca).

    masa_humeda_inicial_kg: masa TOTAL (agua + materia seca) al inicio.
    Retorna (masa_materia_seca_kg, agua_removida_kg).
    """
    masa_seca = masa_humeda_inicial_kg / (1.0 + m0_db)
    agua_removida = masa_seca * (m0_db - mf_db)
    return masa_seca, agua_removida


def _agua_removida_base_humeda(masa_humeda_inicial_kg: float, m0_wb: float, mf_wb: float) -> tuple[float, float]:
    """Agua removida [kg] dado M0/Mf en base humeda (decimal, kg agua/kg total).

    Retorna (masa_materia_seca_kg, agua_removida_kg). La materia seca es
    constante durante el secado.
    """
    masa_seca = masa_humeda_inicial_kg * (1.0 - m0_wb)
    masa_total_final = masa_seca / (1.0 - mf_wb)
    agua_removida = masa_humeda_inicial_kg - masa_total_final
    return masa_seca, agua_removida


def estimar_linea_minima(masa_humeda_inicial_kg: float) -> ResultadoEnergia:
    """Línea base mínima (sol, patio). Fuente: data/reference/eliseu_2008_secado_patio.md.

    M0=1.35 (decimal, base seca, promedio del rango 1.20-1.51 reportado
    por clon), Mf=0.10 (base seca). Temperatura de proceso: 26.3°C
    (temperatura ambiente media reportada, ya que no hay calentamiento
    activo).
    """
    m0_db, mf_db = 1.35, 0.10
    t_c = 26.3
    masa_seca, agua = _agua_removida_base_seca(masa_humeda_inicial_kg, m0_db, mf_db)
    l = calor_latente_kj_kg(t_c)
    e_kj = agua * l
    return ResultadoEnergia(
        "Linea_minima_sol_patio", masa_seca, agua, t_c, l, e_kj, e_kj / 3600.0
    )


def estimar_linea_activa(masa_humeda_inicial_kg: float) -> ResultadoEnergia:
    """Línea base activa (solar + ventilación forzada). Fuente:
    data/reference/mackpayen_2017_icaro_dryer.md.

    M0=0.70, Mf=0.125 (decimal, base húmeda -- SUPUESTO explícito: el
    paper no aclara la base, se asume base húmeda por ser la lectura más
    común de "water content" expresado así de forma directa). Temperatura
    de proceso: 54°C (temperatura de equilibrio de la cámara reportada).
    """
    m0_wb, mf_wb = 0.70, 0.125
    t_c = 54.0
    masa_seca, agua = _agua_removida_base_humeda(masa_humeda_inicial_kg, m0_wb, mf_wb)
    l = calor_latente_kj_kg(t_c)
    e_kj = agua * l
    return ResultadoEnergia(
        "Linea_activa_solar_ventilacion", masa_seca, agua, t_c, l, e_kj, e_kj / 3600.0
    )


def estimar_propuesta_supervisada(masa_humeda_inicial_kg: float) -> ResultadoEnergia:
    """Propuesta supervisada (referencia: Phitakwinai et al. 2019, T=60C/RH=20%).

    M0=1.22 (decimal, base seca, valor comun a todas las condiciones del
    paper), Mf=0.085 (base seca -- SUPUESTO: promedio del rango 0.045-0.125
    reportado en el paper, ya que no publican Mf por condicion individual).
    Temperatura de proceso: 60°C (condicion usada en el ajuste de
    ajuste_modelos.py).
    """
    m0_db, mf_db = 1.22, 0.085
    t_c = 60.0
    masa_seca, agua = _agua_removida_base_seca(masa_humeda_inicial_kg, m0_db, mf_db)
    l = calor_latente_kj_kg(t_c)
    e_kj = agua * l
    return ResultadoEnergia(
        "Propuesta_supervisada_Midilli", masa_seca, agua, t_c, l, e_kj, e_kj / 3600.0
    )


def estimar_todas(masa_humeda_inicial_kg: float) -> list[ResultadoEnergia]:
    return [
        estimar_linea_minima(masa_humeda_inicial_kg),
        estimar_linea_activa(masa_humeda_inicial_kg),
        estimar_propuesta_supervisada(masa_humeda_inicial_kg),
    ]


if __name__ == "__main__":
    for masa in (1000.0, 2500.0):
        print(f"\n=== Lote de {masa:.0f} kg de cafe humedo inicial ===")
        for r in estimar_todas(masa):
            print(
                f"{r.estrategia:32s} "
                f"agua_removida={r.agua_removida_kg:7.1f} kg  "
                f"T={r.temperatura_proceso_c:5.1f} C  "
                f"L={r.calor_latente_kj_kg:6.1f} kJ/kg  "
                f"E={r.energia_kwh:7.1f} kWh"
            )

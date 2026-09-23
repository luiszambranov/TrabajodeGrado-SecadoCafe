"""
dinamica_termica.py
====================

Balance de energía concentrado (lumped) de la cámara de secado: produce
T_process [°C] en función de heater_cmd, fan_cmd y las condiciones
ambientales, para reemplazar la dinámica de primer orden "de juguete"
(ToyPlant, en modbus_server.py) por una que responda a los mismos
principios físicos que la propuesta supervisada del proyecto.
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Alcance de esta versión (v0 - ESQUELETO, no calibrado)
---------------------------------------------------------
Este módulo define la ESTRUCTURA del balance de energía (qué variables
entran, cómo se relacionan, en qué unidades) y dos funciones auxiliares
(temperatura del proceso, humedad relativa del proceso). Los parámetros
de ``ParametrosCamara`` son PRELIMINARES: se escogieron para que la
temperatura de equilibrio del modelo (heater encendido, ventilador
apagado, ambiente nominal) caiga en el orden de 55-60°C, coherente con
el punto de calibración real más cercano que tiene el proyecto (cámara
de equilibrio ~=54°C, Mackpayen et al. 2017 - ver
data/reference/mackpayen_2017_icaro_dryer.md) y con el rango válido de
las ecuaciones generalizadas de Phitakwinai et al. (2019, Tabla 3:
50-70°C) que usa ``cinetica_dinamica.py`` para la cinética. NO están
tomados de la ficha técnica de la secadora física de referencia ni de
ninguna fuente bibliográfica específica -- eso es justamente el
siguiente paso (calibrar masa de aire, potencia real del calentador y
coeficiente de pérdidas contra esa ficha técnica o con el asesor) antes
de reportar estos números como resultado en el documento.

Convención de unidades (consistente con modelo_secado.py y
generador_ambiente.py: tiempo en HORAS)
------------------------------------------------------------------------
    T           : temperatura de la cámara/proceso          [°C]
    t           : tiempo                                     [h]
    Q_calentador: energía térmica entregada por el calentador
                  cuando heater_cmd=1                         [kJ/h]
    C_termica   : capacidad térmica efectiva de la cámara
                  (aire + estructura + producto)               [kJ/°C]
    UA_perdidas : coeficiente global de pérdidas hacia el
                  ambiente                                    [kJ/(h*°C)]
    UA_fan      : coeficiente ADICIONAL de pérdidas/enfriamiento
                  cuando el ventilador fuerza más intercambio
                  con el ambiente (fan_cmd=1)                  [kJ/(h*°C)]

Modelo
------
    dT/dt = (Q_calentador*heater_cmd - (UA_perdidas + UA_fan*fan_cmd)
             *(T - T_ambiente)) / C_termica

Integrado con paso de Euler explícito (suficiente para el periodo de
actualización usado por modbus_server.py; si el paso de tiempo del
modelo crece mucho, considerar Runge-Kutta).

Referencias
-----------
Mackpayen, A., et al. (2017) - punto de calibración de temperatura de
equilibrio (ver data/reference/mackpayen_2017_icaro_dryer.md).
Phitakwinai, Thepa & Nilnont (2019) - rango válido de T para la cinética
acoplada (ver data/reference/phitakwinai_2019_tabla3_ecuaciones_generalizadas.md).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from generador_ambiente import es_kpa


@dataclass
class ParametrosCamara:
    """Parámetros del balance de energía concentrado de la cámara.

    TODOS los valores por defecto son PRELIMINARES (orden de magnitud,
    no calibrados) - ver "Alcance de esta versión" en el docstring del
    módulo. Pendiente: calibrar contra la ficha técnica de la secadora
    física de referencia (masa de aire tratable, potencia del
    calentador/resistencias) o con el asesor.
    """

    capacidad_termica_kj_c: float = 500.0       # kJ/°C
    potencia_calentador_kj_h: float = 5500.0    # kJ/h (~1.53 kW)
    ua_perdidas_kj_h_c: float = 150.0           # kJ/(h*°C)
    ua_fan_kj_h_c: float = 100.0                # kJ/(h*°C), adicional con fan_cmd=1
    t_max_seguridad_c: float = 90.0             # límite superior de seguridad (mismo criterio que ToyPlant)


def paso_temperatura(
    t_process_c: float,
    t_ambiente_c: float,
    heater_cmd: int,
    fan_cmd: int,
    dt_h: float,
    params: ParametrosCamara,
) -> float:
    """Avanza la temperatura de la cámara ``dt_h`` horas (Euler explícito).

    Aplica el mismo criterio de seguridad que ``ToyPlant`` en
    modbus_server.py: la temperatura nunca baja de la ambiente ni supera
    ``params.t_max_seguridad_c``.
    """
    q_entra = params.potencia_calentador_kj_h * heater_cmd
    ua_total = params.ua_perdidas_kj_h_c + params.ua_fan_kj_h_c * fan_cmd
    dT_dt = (q_entra - ua_total * (t_process_c - t_ambiente_c)) / params.capacidad_termica_kj_c

    t_nuevo = t_process_c + dt_h * dT_dt
    return float(np.clip(t_nuevo, t_ambiente_c, params.t_max_seguridad_c))


def rh_proceso(t_process_c: float, ea_kpa: float) -> float:
    """Humedad relativa DENTRO de la cámara [%], enfoque psicrométrico
    simple: se asume que la presión de vapor real del aire (``ea_kpa``,
    tomada del ambiente exterior) se conserva aproximadamente al
    calentarse el aire dentro de la cámara (el calentamiento sin
    intercambio de masa no cambia la humedad absoluta).

    Simplificación explícita (v0): NO incluye el vapor de agua que
    libera el café al secarse (efecto de sorción/evaporación del
    producto), que aumentaría la humedad real de la cámara por encima de
    este valor - ver la misma simplificación ya documentada en
    ``estimacion_energia.py`` sobre el efecto de sorción. Refinar si la
    humedad de cámara resulta sensible para el control o la comparación
    de estrategias.

    Reutiliza ``es_kpa`` de generador_ambiente.py (mismo enfoque
    psicrométrico que ya usa el generador de ambiente del proyecto).
    """
    return float(np.clip(100.0 * ea_kpa / es_kpa(t_process_c), 0.0, 100.0))


if __name__ == "__main__":
    # Smoke test manual: calentador encendido, sin ventilador, ambiente
    # nominal de Naranjal (20.8 C) -> deberia estabilizarse en el orden
    # de 55-60 C tras suficientes horas simuladas.
    params = ParametrosCamara()
    t_ambiente = 20.8
    t = t_ambiente
    dt_h = 0.25
    for _ in range(200):
        t = paso_temperatura(t, t_ambiente, heater_cmd=1, fan_cmd=0, dt_h=dt_h, params=params)
    print(f"T_process tras {200 * dt_h:.1f} h con heater=1, fan=0: {t:.2f} C")
    print(
        f"RH_proceso correspondiente (ea de ejemplo, no calibrada): "
        f"{rh_proceso(t, ea_kpa=1.5):.1f} %"
    )

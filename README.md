# Sistema de supervisión digital para el secado de café

**Diseño mediante simulación de un sistema de supervisión digital basado en
arquitectura IoT para el análisis del secado de café bajo diferentes perfiles
térmicos**

Trabajo de grado — Diplomado en Automatización Industrial, Ingeniería
Mecatrónica, Uniagustiniana.
**Estudiantes:** Luis Alejandro Zambrano Valle y Juan Norberto Pardo Robayo

Estado al **6 oct 2026** (semana 9 de la guía: resultados y economía; la
semana 10 es el cierre técnico y documental).

## Objetivos y dónde está cada uno en el repositorio

| Objetivo (literal, aprobado) | Estado | Dónde |
|---|---|---|
| **General:** Desarrollar un sistema de supervisión digital basado en tecnologías IoT para el análisis mediante simulación del proceso de secado de café bajo diferentes perfiles térmicos. | En cierre | Todo el repositorio |
| **1.** Modelar computacionalmente el comportamiento del proceso de secado de café, con el fin de establecer una base para la simulación y el análisis del proceso. | ✅ Cerrado y validado | `python/` (modelo), `data/reference/validacion_modelo.md` |
| **2.** Diseñar una arquitectura de supervisión digital basada en IoT y una interfaz HMI para el monitoreo de las variables del proceso de secado. | 🟡 Funciona; falta HMI final y FluidSIM | `codesys/`, `fluidsim/`, `docs/diagrama_simulacion.png` |
| **3.** Analizar distintos perfiles térmicos mediante la simulación del proceso de secado de café, analizando el comportamiento de sus variables principales. | ✅ Campaña Monte Carlo de 150 realizaciones | `python/resultados/campana/`, `figures/` |
| **4.** Evaluar la viabilidad económica del sistema de supervisión digital para el secado de café, mediante la estimación y análisis de los costos asociados a su implementación. | 🔴 Energía lista; faltan BOM y CAPEX/OPEX | `python/balance_energia.py`, `data/reference/equipos_energia.md` |

## Qué se simula

Un lote de **80 kg de café pergamino seco** (158 kg húmedos, de 55 a 11 % b.h.)
en Chinchiná, Caldas, secado con tres estrategias que reciben **el mismo clima**:

| Estrategia | Descripción | Código |
|---|---|---|
| PASIVA | Secado al sol en patio (línea base mínima) | `python/escenario_sol_abierto.py` |
| ACTIVA | Secador solar con ventilación forzada | `python/linea_base_activa.py` |
| SUPERVISADA | Secador eléctrico de lecho de 20 cm, 6 kW, ventilador de caudal variable, supervisado por PLC | `python/secador_electrico.py`, `codesys/` |

En la supervisada se comparan **perfiles térmicos**: REF (50 °C, práctica de
Cenicafé) y un diseño factorial de 3 perfiles (45 °C constante, 55 → 35 °C,
35 → 55 °C) × 3 caudales (30, 75 y 100 %).

**Modelo:** cinética de Roa–Cenicafé (isoterma de Trejos et al., 1989 + capa
delgada de SECAFÉ, Parra-Coronado et al., 2008) para las tres estrategias;
lecho por capas de Thompson; clima de la estación Naranjal con variabilidad
diaria de NASA POWER 2005–2024.

## Resultados principales (campaña Monte Carlo, 150 realizaciones)

| Estrategia | Tiempo a 11 % b.h. | Energía comprada | Calidad |
|---|---|---|---|
| PASIVA | 258 h (10.8 días) | 0 | Cumple |
| ACTIVA | 136 h (5.7 días) | 0.03 kWh/kg | Cumple |
| REF (50 °C, caudal 100 %) | 32.4 h | 1.76 kWh/kg | Cumple — el más rápido |
| P1-C75 (45 °C, caudal 75 %) | 45.7 h | 1.47 kWh/kg | Cumple — el de menor energía |
| P2 y P3 (escalonados) | 46–94 h | 0.98–2.01 kWh/kg | No cumplen: grano > 50 °C |
| Caudal 30 % | 80–94 h | 0.98–1.08 kWh/kg | No cumplen: capas sobresecadas |

REF y P1-C75 forman la frontera de Pareto (tiempo vs. energía). Detalle y
pruebas estadísticas: `python/resultados/campana/resumen_resultados.md`.

## Arquitectura

```
Clima de Chinchiná ─> Python (planta: secador, lecho, cinética)  ⇄ Modbus TCP ⇄  CODESYS (supervisión, HMI, alarmas)
                                                                                    │ OPC
                                                                                    └─> FluidSIM (compuerta de inversión del aire)
```

- **Python = servidor Modbus** (esclavo): publica temperatura, humedades,
  caudal y estado; recibe comandos. 24 registros (`docs/tabla_variables.md`).
- **CODESYS = cliente** (maestro): RUN/HOLD, ventilador y caudal, inversión
  del aire cada 6 h, parada por humedad, watchdog en los dos sentidos, HMI.
- **Dos niveles de control**, como en un secador real: el termostato del ducto
  (campo) y la supervisión del proceso (PLC). Con la simulación acelerada el
  termostato corre en Python; a tiempo real lo puede cerrar el PLC.
- **Monte Carlo** usa una réplica en Python de la lógica del PLC sobre la misma
  física (`python/control_supervisado.py`), para correr miles de horas sin
  tiempo real.
- Diagrama completo: `docs/diagrama_simulacion.png`.

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `python/` | Modelo, servidor Modbus, campaña Monte Carlo, análisis, validación y energía. Ver `python/README.md`. |
| `python/resultados/` | Piloto (N = 130) y campaña final (150 realizaciones) con su resumen y figuras. |
| `python/legacy/` | Código retirado (modelos v0.1, Midilli). No se usa en los resultados. |
| `codesys/` | `PLC_PRG_v3.st` (vigente), proyecto CODESYS SP9, evidencias y guía Modbus. Ver `codesys/README.md`. |
| `fluidsim/` | Circuito neumático de la compuerta de inversión (en construcción). |
| `data/clima/` | Serie diaria NASA POWER 2005–2024 de Naranjal. |
| `data/reference/` | Fuentes digitalizadas y justificación de cada parámetro (clima, secador, equipos, validación). |
| `docs/` | Tabla de variables, evolución del modelo, selección de líneas base, diagramas. |
| `figures/` | Figuras de los perfiles térmicos para el documento. |
| `apartado_doc/` | Versiones del documento del trabajo de grado. |

## Cómo reproducir

```
cd python
pip install -r requirements.txt
python campana_montecarlo.py --n 150 --semilla-inicial 1001 --salida resultados/campana --procesos 4
python analisis_montecarlo.py resultados/campana
python graficas_perfiles.py
python modbus_server.py          # planta para CODESYS (puerto 5020)
```

Herramientas: Python 3.14 (numpy, scipy, pandas, matplotlib, pymodbus 3.6.9),
CODESYS V3.5 SP9 con CODESYS Control Win V3, FluidSIM (OPC).

## Pendiente (6 oct 2026)

1. **Objetivo 4:** lista de equipos con precios (BOM), CAPEX y OPEX con la
   tarifa de la CHEC, comparación con el secado solar.
2. **CODESYS:** cargar `PLC_PRG_v3` con los canales de caudal, HMI final,
   botón "Nuevo lote" con reinicio de la planta en Python y una verificación
   a tiempo real CODESYS vs. réplica (~60 min).
3. **FluidSIM:** compuerta de inversión (cilindro doble efecto, válvula 5/2
   biestable, finales de carrera, alarma de compuerta trabada).
4. **Con el asesor:** confirmar "variables activas" = manipuladas, criterio de
   convergencia, filtro de calidad y si se hace análisis de sensibilidad
   climática o se declara como limitación.
5. **Documento:** sincronizar con el repositorio (metodología, tabla de
   variables, validación, resultados), referencias (Kumar/Boyle/Zhang,
   NTC-ISO 6673), literatura 2023–2026, justificación IoT/IIoT y conclusiones
   por objetivo.

Cómo se llegó aquí y por qué se descartó cada versión anterior:
`docs/evolucion_del_modelo.md`.

## Alcance

Proyecto de **simulación**. La secadora física solo se usa como referencia
de literatura y ficha técnica; cualquier implementación física queda como
trabajo futuro.

## Roles

| Rol | Responsabilidad principal |
|---|---|
| Estudiante A | Modelado, literatura del secado, Python, validación contra literatura, perturbaciones, campaña Monte Carlo, métricas, estadística y energía. |
| Estudiante B | CODESYS, máquina de estados, alarmas/HMI, FluidSIM, comunicaciones, integración, arquitectura IoT y costos de automatización. |
| Trabajo conjunto | Líneas base, diseño experimental, integración final, documento, APA, sustentación y revisión cruzada. |

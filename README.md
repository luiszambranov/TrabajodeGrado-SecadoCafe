# Sistema de supervisión digital para el secado de café

**Diseño mediante simulación de un sistema de supervisión digital basado en
arquitectura IoT para el análisis del secado de café bajo diferentes perfiles
térmicos**

Trabajo de grado, Ingeniería Mecatrónica, Uniagustiniana.

- **Autores:** Luis Alejandro Zambrano Valle y Juan Norberto Pardo Robayo
- **Asesor:** David Reinerio Yanguas Rojas

El documento final está en [`documento/`](documento/).

## Qué hace el sistema

Simula el secado de un lote de **80 kg de café pergamino seco** (158 kg húmedos,
de 55 a 11 % b.h.) en Chinchiná, Caldas, en un secador eléctrico de lecho de
20 cm (resistencia de 6 kW y ventilador de caudal variable) supervisado por un
PLC, y lo compara con el secado solar pasivo y activo bajo el mismo clima.

```
 Clima de Chinchiná ──> Python: planta simulada        ⇄  Modbus TCP  ⇄   CODESYS: PLC, HMI y alarmas
                        (secador, lecho, cinética)        puerto 5020          │
                                                                               │ OPC
                                                                               ▼
                                                                FluidSIM: compuerta de inversión del aire,
                                                                bandeja, pulsadores y semáforo
```

| Capa | Herramienta | Papel |
|---|---|---|
| Planta (dispositivo de campo simulado) | Python (`python/modbus_server.py`) | Esclavo Modbus TCP: publica temperatura, humedades, caudal, energía, relojes y estado; recibe los mandos y la consigna. La física nunca se pausa: con STOP o una falla solo cambian los mandos. |
| Supervisión y control | CODESYS V3.5 SP9 (`codesys/`) | Maestro Modbus: máquina de estados, perfil térmico y caudal elegidos en la HMI, inversión del aire cada 6 h, fin por humedad, alarmas y watchdog en los dos sentidos. |
| Actuación electroneumática | FluidSIM (`fluidsim/`) | Cilindros de la compuerta y la bandeja, finales de carrera, pulsadores y semáforo, enlazados por OPC. |
| Análisis | Python (`python/`) | Réplica de la lógica del PLC sobre la misma física para la campaña Monte Carlo de 150 realizaciones. |

Mapa completo de registros y variables: [`docs/tabla_variables.md`](docs/tabla_variables.md).
Diagrama: [`docs/diagrama_simulacion.png`](docs/diagrama_simulacion.png).

## Perfiles térmicos comparados

| Código | Consigna del aire | Caudal |
|---|---|---|
| REF | 50 °C constante (práctica de Cenicafé) | 100 % |
| P1 | 45 °C constante | 30, 75 o 100 % |
| P2 | 50 °C que baja a 35 °C cuando el lote llega a 30 % b.h. | 30, 75 o 100 % |
| P3 | 35 °C que sube a 50 °C cuando el lote llega a 30 % b.h. | 30, 75 o 100 % |

Caudal 100 % = 8 m³/min. Ningún perfil supera los 50 °C permitidos para el grano.

## Resultados (campaña Monte Carlo, 150 realizaciones pareadas)

| Estrategia | Tiempo a 11 % b.h. | Energía comprada | Calidad |
|---|---|---|---|
| Solar pasiva | 258 h (10,8 días) | 0 | Cumple |
| Solar activa | 136 h (5,7 días) | 0,03 kWh/kg c.p.s. | Cumple |
| REF (50 °C, 100 %) | 32,4 h | 1,76 kWh/kg c.p.s. | Cumple; el más rápido |
| P1-C75 (45 °C, 75 %) | 45,7 h | 1,47 kWh/kg c.p.s. | Cumple; 16,4 % menos energía que REF |
| P3-C75 (35 → 50 °C, 75 %) | 55,2 h | 1,42 kWh/kg c.p.s. | Cumple; 19,0 % menos energía que REF |
| Caudal 30 % | 80–99 h | 0,99–1,07 kWh/kg c.p.s. | No cumple: sobreseca la capa de entrada |

REF, P1-C75 y P3-C75 forman la frontera de Pareto tiempo–energía con una tolerancia de 9 % b.h. en la capa más seca (criterio propio); con 10 % ningún perfil alcanza el 95 % de realizaciones exigido (el más cercano, P2-C100, llega a 90 %). Detalle:
[`python/resultados/campana/resumen_resultados.md`](python/resultados/campana/resumen_resultados.md).

## Evaluación financiera preliminar (5 años, 12 % real, 40 lotes/año)

Implementación recomendada: controlador CODESYS WAGO Compact Controller 100 con HMI web (WebVisu),
actuador eléctrico y el mismo programa del proyecto. La máquina trabaja sola: reemplaza la supervisión
manual del secado (horas calculadas a partir de la simulación; el muestreo final de humedad sigue siendo manual y no se cuenta).

| Alternativa | Inversión incremental | VPN | TIR | Recuperación descontada |
|---|---|---|---|---|
| A: automatizar un secador existente | 11,8 M COP | +8,3 M COP | 36,7 % | 2,8 años |
| B: secador nuevo automatizado frente a uno manual | 9,5 M COP | +10,7 M COP | 50,2 % | 2,1 años |
| Sistema completo frente a seguir secando al sol | 16,8 M COP | −21,1 M COP | — | No se recupera |

Supuestos, fuentes y flujos: [`python/resultados/financiero/`](python/resultados/financiero/).

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| [`documento/`](documento/) | Documento final del trabajo de grado (PDF). |
| [`python/`](python/) | Modelo de la planta, servidor Modbus, campaña Monte Carlo, análisis y gráficas. Cada archivo explicado en su README. |
| [`python/resultados/`](python/resultados/) | Resultados de la campaña, de los análisis, de los ensayos de falla y de la verificación con CODESYS. |
| [`codesys/`](codesys/) | Proyecto de CODESYS, programas en texto (`.st`), mapa de canales Modbus, HMI y ensayos de falla. |
| [`fluidsim/`](fluidsim/) | Circuito electroneumático y su enlace OPC. |
| [`data/`](data/) | Serie de clima NASA POWER y fuentes de cada parámetro del modelo, cotizaciones y validación. |
| [`docs/`](docs/) | Tabla de variables, selección de líneas base y diagramas de la arquitectura. |
| [`figures/`](figures/) | Figuras del documento. |

## Cómo ejecutarlo

Requisitos: Python 3.10 o superior, CODESYS V3.5 SP9 con CODESYS Control Win V3
y FluidSIM con servidor OPC (solo para la demostración con PLC).

```
cd python
pip install -r requirements.txt

# Demostración con el PLC: planta en el puerto 5020 (después abrir CODESYS y FluidSIM)
python modbus_server.py

# Campaña Monte Carlo completa sin PLC (unos 15 min con 4 núcleos) y su análisis
python campana_montecarlo.py --n 150 --semilla-inicial 1001 --salida resultados/campana --procesos 4
python analisis_montecarlo.py resultados/campana
```

Pasos de CODESYS y FluidSIM: [`codesys/README.md`](codesys/README.md).
Todos los scripts de Python: [`python/README.md`](python/README.md).

## Alcance

Es un proyecto de **simulación**: el secador, los sensores y los actuadores son
modelos; las cotizaciones de equipos sirven para estimar la viabilidad económica.
La implementación física queda como trabajo futuro.

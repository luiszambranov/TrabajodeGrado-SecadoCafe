# Sistema de supervisión digital para el secado de café

Trabajo de grado — Diplomado en Automatización Industrial
Ingeniería Mecatrónica | Ruta de ejecución: semana 4 a semana 10 | Holgura y radicación: semanas 11-12

**Estudiantes:** Luis Alejandro Zambrano Valle y Juan Norberto Pardo Robayo

## Alcance comprometido
Simulación completa y reproducible. La secadora física se mantiene como referente y
oportunidad de validación incremental, pero no como dependencia para cumplir los objetivos.

## Arquitectura fijada
`Python + CODESYS + FluidSIM`

- **Python**: modela la planta (dinámica térmica/secado) y procesa resultados.
- **CODESYS**: implementa lógica, control y HMI.
- **FluidSIM**: representa la actuación neumática.

Flujo lógico: `Perturbaciones y parámetros → Python (planta térmica/secado) → variables de
proceso → CODESYS (lógica/control/HMI) → comandos → FluidSIM (actuación neumática) →
estados de actuadores → Python`.

## Meta interna
Cerrar técnicamente el proyecto y tener el documento completo al terminar la semana 10.
Las semanas 11 y 12 son para corrección, sustentación y radicación, no para construir lo esencial.

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `/python` | Modelo de la planta (cinética de secado + dinámica térmica/energética), scripts de ajuste, generación de perturbaciones, campañas Monte Carlo. |
| `/codesys` | Proyecto de máquina de estados, lógica de control (PID), HMI, alarmas y tendencias. |
| `/fluidsim` | Circuito neumático de actuación (ventilación/compuertas de la secadora). |
| `/data` | Datos de referencia (literatura), datasets generados por las campañas de simulación, diccionario de variables. |
| `/figures` | Gráficas y figuras generadas para el documento final. |
| `/docs` | Documento del trabajo de grado, anteproyecto, actas, diagramas de arquitectura, tabla de variables. |

## Estado — Semana 4 (Fundamentos + primer hilo ejecutable)
- [ ] Documento pasado a limpio en la plantilla final; objetivos copiados literalmente.
- [x] Repositorio compartido con /python, /codesys, /fluidsim, /data, /figures, /docs y README.
- [x] Matriz comparativa de 4-5 modelos de secado con fuentes.
- [x] Selección preliminar de línea base solar y alternativa activa.
- [x] Diagrama de arquitectura Python-CODESYS-FluidSIM.
- [x] Prueba mínima de comunicación. Interfaz elegida: **Modbus TCP** (Python = servidor/slave, CODESYS = cliente/master; ver `codesys/comunicacion_modbus.md`). **Verificada end-to-end el 9-10 sept 2026, con HMI**: `T_process` y `heater_cmd` confirmados en ambos sentidos entre `python/modbus_server.py` y `codesys/ModbusPhytoon.project` (CODESYS V3.5 SP15), y mostrados en vivo en un HMI mínimo dentro de CODESYS (valor numérico de `T_process` + piloto del calentador). Evidencia en `codesys/evidencia_hmi_modbus.png` (HMI y consola de Python con el mismo valor en el mismo instante). Hay además una prueba de conexión CODESYS-FluidSIM, `codesys/ConcexionOPC.png`, pendiente de formalizar por separado.
- [x] **v1 — interfaz modular + 6 variables, verificada end-to-end (14-15 sept 2026).** `python/modbus_server.py` desacopla la planta detrás de una interfaz (`Plant`/`ToyPlant`, lista para enchufar `modelo_secado.py` real) y agrega `fan_cmd`, `RH_ambient`, `plant_mode` y `safety_ok` (con watchdog: si CODESYS deja de escribir comandos, los actuadores pasan a valor seguro y `safety_ok=0` — el ítem de "pérdida de comunicación" que quedaba pendiente). El 15 sept se rehizo el proyecto CODESYS desde cero en SP9 (`codesys/SecadoCafe_ModbusV1.project`, ya que SP15 se desinstaló) con las 6 variables, y se encontró y resolvió un bug del driver Modbus de SP9 con canales de más de 1 registro (ver `codesys/comunicacion_modbus.md`, sección 0.6). Verificado end-to-end: `T_process`/`RH_ambient` con valores reales en el Watch de CODESYS, coincidentes con la consola de Python, y `heater_cmd` respondiendo correctamente. **HMI visual y prueba con el modelo real: ✔ ver "Estado — 23 sept 2026" más abajo.** Prueba del watchdog forzando la pérdida real de comunicación con CODESYS: sigue pendiente.
- [x] HMI en CODESYS (v0, SP15): valor numérico de `T_process` en vivo + piloto del calentador (`codesys/comunicacion_modbus.md`, sección 5). **HMI de v1/SP9 con las variables nuevas, Trend y modelo real: ✔ ver "Estado — 23 sept 2026" más abajo.**
- [x] Primer script Python que reproduzca una curva de secado. (`python/CurvaSecado.ipynb`, modelo de Newton)
- [ ] Ficha de inspección de la secadora física.

## Estado — Semana 5 (Modelo base validado)
- [x] Modelo Python v0.1 con unidades y parámetros documentados. (`python/modelo_secado.py`: Newton, Logarítmico y Midilli modificado, con docstrings de unidades y procedencia de cada parámetro; parámetros aún preliminares, no ajustados)
- [x] Ajuste de modelos candidatos con RMSE, MAE y R². (`python/ajuste_modelos.py` + `python/AjusteModelos.ipynb`: ajuste no lineal de los 3 modelos contra la curva de referencia de Phitakwinai et al. 2019, T=60°C/RH=20%; Midilli modificado recupera los parámetros publicados con R²≈1)
- [x] Reproducción de datos/curva de literatura. (Tabla 2 completa del paper digitalizada en `data/reference/phitakwinai_2019_tabla2_parametros.csv`; curva de referencia generada con la ecuación ya publicada y validada por los autores)
- [x] Escenario de secado al sol en lazo abierto. (`python/escenario_sol_abierto.py` + `python/EscenarioSolAbierto.ipynb`: modelo Newton calibrado con condiciones reales de secado en patio, T=26.3°C/HR=63.3%/117.5h — ver limitación documentada sobre la tabla de parámetros Page no verificada)
- [x] Primera línea base activa (código). (`python/linea_base_activa.py` + `python/LineaBaseActiva.ipynb`: modelo Logarítmico con parámetros reales de Mackpayen et al. 2017, secador solar Icaro mejorado, verificados contra el PDF original)
- [x] Generador de T ambiente/HR ambiente nominal y perturbado. (`python/generador_ambiente.py` + `python/GeneradorAmbiente.ipynb`: ciclo diurno de T y HR con la Estación Naranjal, Cenicafé, Chinchiná/Caldas como referencia climática; enfoque psicrométrico simple para HR a partir de T)
- [x] Primera estimación de energía. (`python/estimacion_energia.py` + `python/EstimacionEnergia.ipynb`: calor latente mínimo de vaporización para las 3 estrategias, ~300-450 kWh/tonelada; explícitamente NO es el consumo real — falta electricidad de ventiladores, pérdidas térmicas y efecto de sorción)
- [ ] Puerta física: datos que realmente podrían obtenerse. (a cargo del equipo)

## Estado — 23 sept 2026 (Modelo real conectado a CODESYS + integración OPC/FluidSIM validada)
- [x] Esqueleto del modelo real conectado a la interfaz `Plant` de `modbus_server.py`: `dinamica_termica.py` (balance de energía concentrado de la cámara: `T_process` a partir de `heater_cmd`/`fan_cmd` y ambiente) + `cinetica_dinamica.py` (Midilli modificado dinámico, método de "tiempo equivalente" con las ecuaciones generalizadas k/n/b(T,RH) de la Tabla 3 de Phitakwinai et al. 2019) + `planta_secado.py` (`ModeloSecadoPlant`, reemplaza a la planta de juguete). Seleccionable con `python modbus_server.py --plant modelo`. **Esqueleto v0, no calibrado** — ver `python/README.md` para el detalle y los pendientes de calibración.
- [x] `modbus_server.py` extendido con `M_coffee` (registros 8-9, % b.h.) y `tiempo_proceso_h` (registros 10-11, horas de MODELO — no de reloj real, ver `factor_aceleracion` en `planta_secado.py`).
- [x] **Verificado end-to-end con CODESYS v1 (SP9), con HMI en vivo.** `T_process`, "humedad café" (decreciendo desde la humedad inicial) y "tiempo de secado" mostrados en el HMI, coincidentes con la consola de Python. Se depuraron en vivo tres fallos de configuración (desplazamiento de canal Modbus incorrecto, variables sin asignar en el IO Mapping, campos de texto del HMI enlazados a la variable equivocada) y se ajustó el eje X del Trend (mostraba fecha/hora del sistema en cada muestra en vez de una escala legible).
- [x] **Prueba de integración concurrente**: Modbus (Python) + OPC (FluidSIM) + lógica de control, sobre el mismo runtime CODESYS Control Win V3. Circuito mínimo en FluidSIM (botón → cilindro accionado desde la programación de CODESYS) corriendo al mismo tiempo que la planta Python vía Modbus, sin conflictos de puerto ni de tiempos. **Decisión: GO para FluidSIM vía OPC.**
- [ ] Subir a `codesys/` el proyecto CODESYS v1 actualizado (canales `M_coffee`/`tiempo_proceso_h`, HMI, Trend corregido) — todavía no está commiteado en el repositorio (a cargo de Luis).
- [ ] Circuito neumático completo en FluidSIM (cilindros de carga/expulsión de bandeja, motor del ventilador) y máquina de estados (IDLE → CARGA → SECANDO → DESCARGA → IDLE) con botones de arranque/paro/emergencia.
- [ ] Calibración de `ParametrosCamara` y de `CondicionesSecado` (M0/Me reales) contra la ficha técnica de la secadora de referencia o con el asesor, y campaña Monte Carlo sobre la planta ya validada.

**Alcance confirmado esta semana:** el proyecto es de simulación pura — no hay secadora física involucrada; la mención a la secadora física en "Alcance comprometido" (arriba) es solo como referencia de literatura/ficha técnica para calibrar parámetros, no un equipo que se vaya a instrumentar.

## Roles
| Rol | Responsabilidad principal |
|---|---|
| Estudiante A | Modelado, literatura del secado, Python, validación contra literatura, perturbaciones, campaña Monte Carlo, métricas, estadística y energía. |
| Estudiante B | CODESYS, máquina de estados, PID, alarmas/HMI, FluidSIM, comunicaciones, integración, arquitectura IoT y costos de automatización. |
| Trabajo conjunto | Secadora física, líneas base, diseño experimental, integración final, documento, APA, sustentación y revisión cruzada. |


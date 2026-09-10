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
- [x] Prueba mínima de comunicación. Interfaz elegida: **Modbus TCP** (Python = servidor/slave, CODESYS = cliente/master; ver `codesys/comunicacion_modbus.md`). **Verificada end-to-end el 9-10 sept 2026**: `T_process` y `heater_cmd` confirmados en ambos sentidos entre `python/modbus_server.py` y `codesys/ModbusPhytoon.project` (CODESYS V3.5 SP15). Pendiente: dejar captura/video como evidencia en el repo, y el comportamiento ante pérdida de comunicación. Hay además una prueba de conexión CODESYS-FluidSIM, `codesys/ConcexionOPC.png`, pendiente de formalizar por separado.
- [ ] HMI en CODESYS (indicadores, tendencia, "pilotos" de actuadores) + más variables simuladas en Python (`fan_cmd`, `RH_ambient`) para la próxima demo — plan detallado en `codesys/comunicacion_modbus.md`, sección 5.
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

## Roles
| Rol | Responsabilidad principal |
|---|---|
| Estudiante A | Modelado, literatura del secado, Python, validación contra literatura, perturbaciones, campaña Monte Carlo, métricas, estadística y energía. |
| Estudiante B | CODESYS, máquina de estados, PID, alarmas/HMI, FluidSIM, comunicaciones, integración, arquitectura IoT y costos de automatización. |
| Trabajo conjunto | Secadora física, líneas base, diseño experimental, integración final, documento, APA, sustentación y revisión cruzada. |


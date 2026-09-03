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
- [ ] Prueba mínima de comunicación (OPC UA listo) o informe de limitación/licencia. (Falta trabajar sobre comunicacion con phyton)
- [ ] Primer script Python que reproduzca una curva de secado.
- [ ] Ficha de inspección de la secadora física.

## Roles
| Rol | Responsabilidad principal |
|---|---|
| Estudiante A | Modelado, literatura del secado, Python, validación contra literatura, perturbaciones, campaña Monte Carlo, métricas, estadística y energía. |
| Estudiante B | CODESYS, máquina de estados, PID, alarmas/HMI, FluidSIM, comunicaciones, integración, arquitectura IoT y costos de automatización. |
| Trabajo conjunto | Secadora física, líneas base, diseño experimental, integración final, documento, APA, sustentación y revisión cruzada. |


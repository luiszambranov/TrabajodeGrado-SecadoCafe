# Bitácora de uso de inteligencia artificial

Trabajo de grado *Diseño mediante simulación de un sistema de supervisión digital basado en
arquitectura IoT para el análisis del secado de café bajo diferentes perfiles térmicos*.
Autores: Luis Alejandro Zambrano Valle y Juan Norberto Pardo Robayo.

## Herramienta y alcance

- **Herramienta:** Claude (Anthropic), asistente conversacional con acceso de lectura y escritura a
  la carpeta local del repositorio y a un entorno de ejecución de Python.
- **Periodo:** septiembre a noviembre de 2026.
- **Áreas que cubre esta bitácora:** estructura y organización del repositorio, archivos README,
  organización de los datos, generación de código en Python y elaboración de esquemas, tablas y
  figuras.
- **No cubre la redacción del documento.**

**Criterio de uso.** Las decisiones de ingeniería las tomaron los autores con el asesor: el modelo
cinético, los perfiles térmicos, la arquitectura, los criterios de aceptación y los supuestos
económicos. La IA propuso estructuras, escribió borradores de código y documentación, y ejecutó
cálculos. Los autores revisaron, corrigieron y aprobaron cada entrega antes de subirla al
repositorio. Todos los commits los hicieron los autores.

**Lo que la IA no hizo:**
- No ejecutó CODESYS ni FluidSIM. Los ensayos con el sistema integrado, las capturas de la HMI y los
  registros de falla los hicieron los autores; la IA solo procesó los CSV resultantes.
- No inventó datos. Cada parámetro proviene de una fuente citada o está declarado como supuesto en
  `data/reference/` o en el script que lo usa.

## 1. Estructura y organización del repositorio

| Fecha | Actividad | Referencia |
|---|---|---|
| 23 sep 2026 | Esqueleto del modelo físico (dinámica térmica, cinética, planta) y `.gitignore` inicial. | `3b70775`, `efe6565` |
| 5 oct 2026 | Reorganización general: modelos de la primera versión retirados, resultados agrupados en `python/resultados/<análisis>/`, fuentes de parámetros en `data/reference/`. | `f7e5822` |
| 21–22 oct 2026 | Limpieza para la entrega: un archivo por programa de CODESYS, figuras del documento en `figures/`, resultados de verificación y ensayos con nombres consistentes. | `26fd5c7`, `3972f27`, `251f53e` |
| 23 oct 2026 | Etiquetas de entrega (`entrega-final`, `entrega-final-v2`) para que el Anexo A del documento cite un commit fijo. `.gitignore` ampliado para excluir archivos temporales de CODESYS (`*.opt`, `*.~u`, `*.compileinfo`) y FluidSIM (`*.bak`). | `02791ea`, `1b974e2` |
| 23 oct 2026 | Comentarios del código de CODESYS (`codesys/*.st`) depurados: se quitaron las marcas de versión y se dejaron solo los comentarios descriptivos. Se comprobó, eliminando todos los comentarios, que el código es idéntico al que funciona en el proyecto. | `1b974e2` |

Estructura resultante: `python/` (modelo, servidor, análisis y resultados), `codesys/`, `fluidsim/`,
`data/` (clima y fuentes), `docs/` (variables, diagramas, bitácora), `figures/` y `documento/`.

## 2. Archivos README

- **README principal:** descripción del sistema, diagrama de capas, tabla de perfiles, resultados de
  la campaña, resumen financiero, estructura de carpetas y comandos de ejecución. Se actualizó en
  cada corrección para que coincidiera con el documento (rango de validación, criterio del 95 % y
  cifras de VPN y TIR).
- **`python/README.md`:** cada script con su función, comando y salida; requisitos y versión fijada
  de `pymodbus`.
- **`codesys/README.md`:**
  - pasos de ejecución;
  - mapa de los 41 registros Modbus;
  - bits del intercambio OPC con FluidSIM;
  - variables de la HMI;
  - política de parada y procedimiento de los ensayos de falla;
  - notas técnicas, como el orden de palabras de los REAL y los canales de un registro en SP9.
- **README de `data/reference/`, `figures/`, `docs/` y `documento/`:** índice de cada archivo y del
  script que lo genera.

## 3. Organización de los datos

- **`data/clima/`:** serie diaria NASA POWER 2005–2024 del punto de Naranjal, con la consulta
  documentada en `data/reference/chinchina_clima_fuentes.md`.
- **`data/reference/`:** un archivo por fuente o grupo de parámetros. Ejemplos:
  - isoterma y capa delgada de Roa–Cenicafé;
  - dimensionamiento del secador;
  - equipos y energía;
  - validación del modelo;
  - cotizaciones del BOM (`cotizaciones_bom.csv`, generado por `generar_cotizaciones_bom.py`).

  Cada archivo trae la cita APA y el enlace de la fuente, según la regla del proyecto de subir la
  cita junto con cada dato.
- **Resultados con formato tabular fijo:**
  - `resultados.csv` de la campaña: una fila por realización y estrategia, con columnas
    documentadas;
  - registros CSV por ciclo del servidor Modbus;
  - un `resumen.md` por análisis.
- **Evaluación financiera:** `flujos_financieros.xlsx`, con hojas de supuestos, flujos, CAPEX,
  comparación con el secado solar, operación de P1-C75 y costo académico. Cada dato está marcado
  como dato con fuente o como supuesto, y el VPN y la TIR se calculan con fórmulas de Excel.
- **Correcciones de datos:**
  - Se retiró el caso de validación del patio (Resende et al., 2009) porque su humedad final está
    por debajo del equilibrio del modelo.
  - Se actualizaron las citas del Avances Técnicos 577 de Cenicafé con su autoría oficial.

## 4. Generación de código en Python

Los autores definieron el comportamiento esperado de cada módulo y la IA escribió los borradores. Los
autores los ejecutaron, compararon los resultados con las fuentes y pidieron correcciones.

| Grupo | Scripts | Aporte de la IA |
|---|---|---|
| Modelo físico | `cinetica_roa.py`, `lecho_secado.py`, `dinamica_termica.py`, `secador_electrico.py`, `planta_secado.py`, `generador_ambiente.py` | Implementación de las ecuaciones de las fuentes citadas (Roa–Cenicafé, Thompson, balance del plenum) y de la errata corregida de la isoterma. |
| Líneas base | `escenario_sol_abierto.py`, `linea_base_activa.py` | Calibración del incremento solar con los 10,6 días de Cenicafé. |
| Servidor e integración | `modbus_server.py`, `control_supervisado.py`, `compara_codesys_replica.py`, `grafica_lote.py` | Servidor Modbus TCP con 41 registros, factor de aceleración, registro CSV y gráfica automática del lote. También la réplica en Python de la lógica del PLC y la comparación con las corridas de CODESYS. |
| Campaña y estadística | `campana_montecarlo.py`, `analisis_montecarlo.py`, `analisis_pareado.py` | Diseño pareado por semillas, cálculo de N, pruebas de Shapiro-Wilk y Wilcoxon con corrección de Holm, filtro de calidad y frontera de Pareto. |
| Robustez | `limites_actuacion.py`, `efecto_clima.py`, `niveles_clima.py`, `variabilidad_clima.py`, `sensibilidad_tornado.py` | Saturación de la resistencia, niveles de clima p5/p95 y sensibilidad ±20 %. |
| Validación y economía | `validacion_modelo.py`, `analisis_financiero.py` | Contraste con datos independientes; flujos de caja incrementales, VPN, TIR, recuperación y escenarios, con exportación a Excel. |
| Figuras | `graficas_perfiles.py`, `graficas_ensayos.py`, `figuras_documento.py` | Figuras del documento a partir de los resultados guardados. |

**Errores detectados y corregidos durante el proceso:**
- errata en un coeficiente de la isoterma;
- respaldo indebido en el caso V2 de la validación;
- perfiles P2 y P3 a 55 °C que superaban el límite del grano (se corrigieron a 50 °C y se repitió la
  campaña);
- hora de muestreo contada como ahorro en la evaluación financiera.

## 5. Esquemas, tablas y figuras

- **Diagramas:**
  - arquitectura y flujo de simulación (`docs/diagrama_arquitectura.py`,
    `docs/diagrama_simulacion.py`);
  - Figura 1 del documento en escala de grises con símbolos de diagrama de flujo
    (`python/figuras_documento.py`).
- **Tablas del repositorio:**
  - `docs/tabla_variables.md`: mapa de registros, con tipo, unidad, sentido y papel de cada
    variable;
  - tablas de los README;
  - tablas de resultados en cada `resumen.md`.
- **Cuadros del documento armados a partir de los resultados:**
  - validación del modelo;
  - diseño de perfiles;
  - resultados Monte Carlo;
  - equivalencia entre CODESYS y la réplica;
  - inversión por grupo de componentes;
  - evaluación financiera por escenario;
  - política de parada (Tabla C1);
  - mapa de registros del Anexo B.
- **Figuras:** perfiles térmicos, Pareto tiempo–energía, diferencias pareadas, límites de actuación,
  efecto del clima, sensibilidad tipo tornado, ensayos de falla y lote completo. Todas se regeneran
  con los scripts indicados en `figures/README.md`.

## 6. Verificación aplicada a lo generado

- Ejecución de cada script en un entorno limpio y comparación de sus cifras con las del documento
  (resumen, tablas y conclusiones).
- Comparación del código de CODESYS del repositorio con el del proyecto en ejecución.
- Revisión, en cada entrega, de que el repositorio etiquetado contuviera el Excel, los resultados y
  el código citados en el Anexo A.
- Revisión de enlaces, DOI y autoría de las fuentes de `data/reference/` por parte de los autores.

# docs — Documentación técnica de apoyo

| Archivo | Qué contiene |
|---|---|
| `tabla_variables.md` | Tabla de variables del sistema: clasificación (controladas, manipuladas, perturbaciones, parámetros), mapa completo de registros Modbus 0–40 con unidad, sentido y variable de CODESYS, parámetros del modelo con su fuente y salidas de la campaña Monte Carlo. |
| `seleccion_lineas_base.md` | Por qué las líneas base son el secado solar pasivo (patio) y el solar activo con ventilación forzada, y en qué se diferencian de la propuesta supervisada. |
| `diagrama_arquitectura.png` / `.svg` | Diagrama simplificado de la arquitectura y el flujo de información (Python ⇄ CODESYS ⇄ FluidSIM). |
| `diagrama_arquitectura.py` | Genera el diagrama anterior. Uso: `python diagrama_arquitectura.py` (requiere `pip install cairosvg`). |
| `diagrama_simulacion.png` / `.svg` / `.pdf` | Diagrama completo de la simulación: bloques, variables que intercambian, registros Modbus y señales OPC. |
| `diagrama_simulacion.py` | Genera el diagrama anterior. Uso: `python diagrama_simulacion.py` (requiere `cairosvg`). |

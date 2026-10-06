# /docs

Material de soporte para el documento del trabajo de grado.

| Archivo | Contenido |
|---|---|
| `tabla_variables.md` | Clasificación de variables (controladas, manipuladas, perturbaciones), mapa Modbus, parámetros con fuente y salidas de Monte Carlo. Base de la "tabla de variables operacionalizada" que pide el asesor. |
| `evolucion_del_modelo.md` | Línea de tiempo del proyecto y por qué se descartó cada versión anterior (Newton, Logarítmico, Midilli → Roa–Cenicafé; lazo térmico local; caudal variable). |
| `seleccion_lineas_base.md` | Por qué la línea base activa es secado solar con ventilación forzada, y diferencias con la propuesta supervisada. |
| `matriz_comparativa_modelos.md` | Comparación inicial de modelos de capa delgada (semana 4). Histórico: la decisión final fue Roa–Cenicafé. |
| `diagrama_simulacion.png` / `.pdf` / `.svg` | **Diagrama vigente** de la simulación (bloques, variables y flujo de datos). Se regenera con `python diagrama_simulacion.py` (requiere `cairosvg`). |
| `diagrama_arquitectura.svg` | Diagrama conceptual de la primera semana (Python → CODESYS → FluidSIM). Reemplazado por `diagrama_simulacion`. |

El documento en Word está en `../apartado_doc/`.

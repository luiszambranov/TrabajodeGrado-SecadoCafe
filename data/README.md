# /data

| Carpeta | Contenido |
|---|---|
| `clima/` | `POWER_Naranjal_diario_2005_2024.csv`: serie diaria de NASA POWER (T mín, T máx, humedad) en las coordenadas de la estación Naranjal, Chinchiná. Con ella `python/variabilidad_clima.py` calcula la variabilidad día a día del generador de clima. Fuente y consulta en `reference/chinchina_clima_fuentes.md`. |
| `reference/` | Datos de literatura y justificación de parámetros (ver `reference/README.md`). |

Los datos **simulados** (campañas Monte Carlo) están en `python/resultados/`.
Siempre se distinguen tres tipos de datos: de literatura (`reference/`),
climáticos medidos (`clima/`) y simulados (`python/resultados/`). El proyecto
no tiene datos físicos propios.

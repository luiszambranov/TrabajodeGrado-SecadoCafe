# data — Datos de entrada

| Carpeta | Contenido |
|---|---|
| `clima/` | `POWER_Naranjal_diario_2005_2024.csv`: serie diaria de NASA POWER (7 305 días) en las coordenadas de la estación Naranjal de Cenicafé, Chinchiná (4,97 N; 75,65 O). Trae el encabezado estándar de NASA POWER y luego una fila por día con la temperatura máxima y mínima a 2 m (`T2M_MAX`, `T2M_MIN`), la humedad específica (`QV2M`) y la presión (`PS`). La usan `python/variabilidad_clima.py` y `python/niveles_clima.py` para obtener cuánto varía el clima de un día a otro. Fuente y forma de consulta: `reference/chinchina_clima_fuentes.md`. |
| `reference/` | Datos tomados de la literatura y la justificación de cada parámetro del modelo, las cotizaciones de equipos y la validación. Ver `reference/README.md`. |

El proyecto distingue tres tipos de datos: de literatura (`reference/`), climáticos
medidos (`clima/`) y simulados (`python/resultados/`). No hay mediciones físicas propias.

# Matriz comparativa de modelos de secado

Semana 4 - Fundamentos + primer hilo ejecutable

Comparación de 5 modelos de cinética de secado en capa delgada (razón de
humedad MR), candidatos para el modelo Python de la planta. La selección
final del modelo (o combinación) se hará en la semana 5 al ajustar contra el
dataset de referencia, según RMSE, MAE y R².

## Tabla comparativa

| Modelo | Forma | Parámetros | N.º de parámetros | Evidencia en café (R² / RMSE reportado) | Contexto del estudio | Ventajas | Limitaciones |
|---|---|---|---|---|---|---|---|
| Newton | MR = exp(-k·t) | k | 1 | R² desde 0.88 (bajando con la temperatura) en secado de café con microondas; entre 0.94-0.98 según la masa de muestra en otro estudio con aire caliente. | Café en microondas / aire caliente | Más simple, útil como referencia mínima | Asume un solo mecanismo de secado; no captura difusión interna ni offset; es consistentemente el peor ajuste en los estudios revisados |
| Page | MR = exp(-k·tⁿ) | k, n | 2 | R² entre 0.97-0.99 en café con microondas, mejora clara sobre Newton en todos los estudios revisados | Café en microondas | Flexible con pocos parámetros; buen equilibrio ajuste/parsimonia | No incluye término de amplitud ni offset; puede quedarse corto si hay comportamiento no monótono |
| Henderson-Pabis | MR = a·exp(-k·t) | a, k | 2 | R² entre 0.94-0.96 en café con microondas, consistentemente por debajo de Page y Midilli | Café en microondas | Añade factor de amplitud `a`; interpretación física simple | Rendimiento intermedio en café; rara vez es el mejor modelo en los estudios revisados |
| Logarítmico | MR = a·exp(-k·t) + c | a, k, c | 3 | R² = 0.984, mejor modelo entre Newton, Page y Henderson-Pabis, en café secado en secador solar (Icaro) | Café en secador solar (temperatura variable) | Mejor ajuste reportado justo en secado **solar**, el contexto de nuestra línea base activa; el offset `c` parece capturar la variabilidad de temperatura ambiente | Más parámetros que Newton/Page; menos evidencia bajo temperatura controlada |
| Midilli (modificado) | MR = a·exp(-k·tⁿ) + b·t | a, k, n, b | 4 | R² = 0.9976, RMSE = 6.65 % en café pergamino Arábica bajo temperatura y HR controladas; R² hasta 0.9995 en otro estudio de aire caliente con 10 modelos comparados | Café bajo temperatura/HR controladas | El más flexible; mejor ajuste reportado bajo condiciones controladas; ya validado en el anteproyecto | Más parámetros, mayor riesgo de sobreajuste; requiere más datos para identificar los 4 parámetros con confianza |

## Lectura de la comparación

Hay un patrón claro según el tipo de secado:

- **Bajo temperatura y humedad relativa controladas** (p. ej. cámara con setpoints fijos), **Midilli modificado** es sistemáticamente el mejor en la literatura revisada.
- **Bajo temperatura variable** (secado solar, como nuestra línea base activa), el modelo **logarítmico** superó a Newton, Page y Henderson-Pabis en el único estudio de secador solar de café que encontramos con esa comparación directa.

Esto sugiere una estrategia de dos frentes para la semana 5: ajustar **Midilli
modificado** como modelo principal (aprovechando que ya está validado en el
anteproyecto vía Phitakwinai et al., 2019) y **logarítmico** como candidato
específico para el escenario de la línea base activa (temperatura variable),
comparando ambos con RMSE/MAE/R² contra el dataset de referencia antes de
fijar el modelo definitivo, en línea con el criterio de "ajuste" y
"parsimonia" de la guía operativa.

## Referencias

1. Phitakwinai, S., Thepa, S., & Nilnont, W. (2019). Thin-layer drying of parchment Arabica coffee by controlling temperature and relative humidity. *Food Science & Nutrition, 7*(9), 2921-2931. https://doi.org/10.1002/fsn3.1144
2. Microwave-assisted drying of arabica coffee beans: Coupled drying kinetics, color-based moisture monitoring, and energy assessment. *ScienceDirect.* https://www.sciencedirect.com/science/article/pii/S2666016426001118
3. Effect of temperature on drying kinetics and quality attributes of coffee beans during hot air drying. https://www.researchgate.net/publication/396597634_Effect_of_temperature_on_drying_kinetics_and_quality_attributes_of_coffee_beans_during_hot_air_drying
4. Modeling of profile temperature and kinetics of coffee beans drying using solar dryer Icaro improved. https://zenodo.org/records/1050268
5. Performance analysis and kinetic modeling of coffee beans in microwave convective dryer integrated photovoltaic system. *IIETA.* https://iieta.org/download/file/fid/80394

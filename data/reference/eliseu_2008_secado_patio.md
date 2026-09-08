# Secado en patio (línea base mínima) — condiciones de referencia

Fuente:

> Estudio de cinética de secado de clones de café (*Coffea canephora*
> Pierre) en terreiro de concreto (patio de secado tradicional).
> Redalyc: https://www.redalyc.org/pdf/3030/303026587001.pdf

## Por qué esta fuente

Es exactamente la condición de la línea base mínima
(`docs/seleccion_lineas_base.md`: "secado tradicional al sol, lazo
abierto, sin control activo del perfil térmico"): café secado
directamente al sol en un patio, sin ningún tipo de calentamiento o
ventilación forzada.

## Condiciones reportadas (verificadas, alta confianza)

| Variable | Valor |
|---|---|
| Temperatura ambiente media | 26.3 °C |
| Humedad relativa media | 63.3 % |
| Humedad inicial | 1.20 - 1.51 (decimal, base seca) según el clon |
| Humedad final | ≈ 0.10 (decimal, base seca) |
| Tiempo total de secado | 117.5 h (~4.9 días) — igual para los 4 clones |
| Modelo de mejor ajuste (los autores) | Page (R² ≥ 0.9997) |

## Por qué NO se usan los parámetros exactos de Page del paper

La tabla de coeficientes k y n del modelo Page (por clon) se extrajo
mediante una herramienta automática de lectura de PDF, y los valores de
k obtenidos (orden de 10⁻⁷ a 10⁻⁹) no pasan una prueba de sanidad física
básica: con esos valores casi no habría secado en 117.5 h. Es muy
probable que sea un error de OCR/extracción con la notación científica
de la tabla (no necesariamente un error del paper), pero no se pudo
verificar contra el PDF original línea por línea. Para no meter un
número no verificado al repositorio, **no se usan los coeficientes
exactos de Page**; en su lugar se usan solo las condiciones generales
(T, RH, tiempo total, humedad inicial/final), que sí se consideran
confiables porque se repiten de forma consistente en el resumen y en el
cuerpo del texto.

## Calibración usada en `escenario_sol_abierto.py`

Se usa el modelo **Newton** (`MR = exp(-k·t)`) — el modelo mínimo de
referencia del proyecto (ver `docs/matriz_comparativa_modelos.md`),
apropiado para un proceso sin control activo. Como no se tienen puntos
intermedios (solo el resumen: tiempo total y humedad inicial/final), se
calibra k con una convención explícita de "prácticamente seco": se
asume que las 117.5 h reportadas corresponden al punto en que
MR ≈ 0.05 (5 % de la humedad removible restante — convención común en
la literatura de cinética de secado para terminar un experimento, y
consistente con que los autores definen la humedad final como el punto
en que la masa deja de cambiar, es decir, cerca del equilibrio).

```
k = -ln(0.05) / 117.5 h = 0.0255 1/h
```

**Esto es una calibración de 2 puntos a las condiciones resumen del
paper, NO un reajuste de los datos completos de los autores.** Se deja
explícito en el código y aquí. Si más adelante se consigue el PDF
original verificado línea por línea (o un dataset punto a punto), debe
reemplazarse por el ajuste real de Page con sus parámetros exactos.

Nótese que k=0.0255 1/h (secado en ~117 h, varios días) es mucho más
lento que la línea base activa (k efectivo del orden de 0.1-0.2 1/h,
secado en ~8 h) y que la propuesta supervisada — es la relación
cualitativa esperada entre las tres estrategias y una primera
validación de sentido común del modelo.

# Mackpayen et al. (2017) — secador solar Icaro mejorado (línea base activa)

Fuente:

> Mackpayen, A. O., M'Boliguipa, J., Malenguinza, S., Bara, L. M., & Napo,
> K. (2017). Modeling of profile temperature and kinetics of coffee beans
> drying using solar dryer Icaro improved. *International Journal of
> Engineering Sciences & Research Technology, 6*(11), 359-371.
> DOI: 10.5281/zenodo.1050268

## Por qué esta fuente para la línea base activa

Es un secador solar de **convección forzada** (ventiladores + placa
absorbedora inclinada con cubierta de vidrio), el mismo principio físico
que nuestra línea base activa (`docs/seleccion_lineas_base.md`:
"secado solar activo con ventilación forzada"). De los cuatro modelos
que los autores probaron (Newton, Henderson-Pabis, Page, Logarítmico),
el **Logarítmico** fue el de mejor ajuste (R²=0.984, χ²=0.0064,
RMSE=0.06), igual que en el estudio del secador Icaro citado en
`docs/matriz_comparativa_modelos.md`.

## Parámetros del modelo Logarítmico (Tabla 3 del paper)

Modelo: `MR = a·exp(-k·t) + c`, con **t en minutos** (aclarado
explícitamente en el paper: "t: time put in the drier (min)").

| Parámetro | Valor | Unidad |
|---|---|---|
| a | 1.1274 | - |
| k | 0.0031 | 1/min |
| c | -0.1780 | - |

Condiciones del experimento: masa de café = 2 kg, velocidad del aire =
1.5 m/s, rango de tiempo del ajuste: 0-500 min (~8.3 h), temperatura de
equilibrio de la cámara ≈ 54 °C (dentro del rango reportado de 50-60 °C).
Contenido de humedad: de 70 % (fresco) a 12.5 % (final recomendado) —
el paper no aclara explícitamente si estos porcentajes son en base
húmeda o base seca; pendiente de confirmar antes de usarlos para
convertir MR a M(t) en unidades absolutas (ver nota en
`python/linea_base_activa.py`).

**Conversión de unidades usada en el proyecto** (el resto del código
usa horas, no minutos, ver `python/modelo_secado.py`):

```
k [1/h] = k [1/min] * 60 = 0.0031 * 60 = 0.186 1/h
```

`a` y `c` son adimensionales y no cambian con la conversión de tiempo.

## Otros resultados del paper (no usados directamente en el código)

- Modelo de calentamiento de la cámara (sin masa): `T(t) = a·(2 - exp(-b·t))`,
  con `a = 27 - 0.99·(H/100000) - 0.0123·H - 5/t`, `b = 0.0123·H`, H =
  distancia al absorbedor [m]. Valida contra Kuitche et al. (2006).
  Es un modelo propio de esa geometría de secador (placa absorbedora +
  distancia a la bandeja); no se reutiliza aquí porque nuestra cámara no
  tiene esa geometría, pero queda documentado por si sirve de referencia
  para el diseño térmico de la línea base activa.
- Efecto de la masa de café sobre la temperatura de equilibrio: de 54 °C
  (0 kg) a 48.12 °C (20 kg) — a mayor masa, menor temperatura de
  equilibrio y mayor tiempo para alcanzarla.

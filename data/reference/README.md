# /data/reference

Datos y parámetros digitalizados de la literatura, usados para validar el
modelo Python del proyecto. Distinguir siempre esto de `/data/simulations`
(datasets generados por nuestras propias campañas de simulación).

## phitakwinai_2019_tabla2_parametros.csv

Transcripción literal de la **Tabla 2** de:

> Phitakwinai, S., Thepa, S., & Nilnont, W. (2019). Thin-layer drying of
> parchment Arabica coffee by controlling temperature and relative
> humidity. *Food Science & Nutrition, 7*(9), 2921-2931.
> https://doi.org/10.1002/fsn3.1144

Contiene los parámetros ya ajustados por los autores (regresión no lineal
por mínimos cuadrados) de los 9 modelos de capa delgada de su Tabla 1,
para las 9 combinaciones de temperatura (50/60/70 °C) y humedad relativa
(10/20/30 %) de su diseño experimental, junto con el r² y el RMSE (%) de
cada ajuste reportados por los propios autores.

**No son lecturas manuales de una gráfica**: son los coeficientes de
regresión publicados directamente en la tabla del paper, por lo que son
exactos (no aproximados por digitalización visual).

Convenciones del paper (importante, distintas de `python/modelo_secado.py`):

- Humedad en **base seca** (% d.b.), no base húmeda. `M0 = 122 % d.b.`
  (común a todas las corridas); `Me` final entre 4.5 % y 12.5 % d.b.
  según la condición (no tabulado por condición individual en el paper).
- MR = (Mt - Me) / (M0 - Me), igual definición funcional que en nuestro
  módulo, pero sobre base seca.
- El modelo "Modified Midilli" del paper es `MR = exp(-k·tⁿ) + b·t`, es
  decir usan **a = 1 fijo** (no reportan columna `a` para ese modelo en la
  Tabla 2) — consistente con el valor por defecto que fijamos en
  `ParametrosMidilliModificado.a` en `modelo_secado.py`.
- Mejor ajuste global reportado por los autores: **Modified Midilli**,
  r² = 0.9976, RMSE = 6.65 % (promediando todas las condiciones), seguido
  de Page.

## phitakwinai_2019_tabla3_ecuaciones_generalizadas.md

Transcripción de la **Tabla 3** del mismo paper: ecuaciones de segundo
orden que expresan k, n y b del modelo Modified-Midilli en función de la
temperatura T (°C) y la humedad relativa RH (%) del aire de secado,
válidas en el rango experimental (T: 50-70 °C, RH: 10-30 %). Permiten
predecir los parámetros del modelo para cualquier combinación de T/RH
dentro de ese rango, sin necesidad de interpolar entre las 9 condiciones
discretas de la Tabla 2. Es un insumo directo para el generador de
perturbaciones ambientales (T/HR ambiente nominal y perturbado) pendiente
en la semana 5.

## Uso en el ajuste (semana 5)

`python/ajuste_modelos.py` usa la fila `Modified_Midilli, T=60, RH=20`
(mejor r² individual: 0.9997, RMSE = 2.323 %) para generar una curva de
referencia MR(t) con la ecuación *ya publicada y validada* por los
autores, y ajusta contra ella nuestros tres modelos candidatos (Newton,
Logarítmico, Midilli modificado) calculando RMSE, MAE y R² con nuestra
propia implementación. Ver el docstring de ese módulo para el detalle
completo de esta metodología y sus limitaciones (no son lecturas punto a
punto de un experimento propio, sino la reproducción de la curva que el
paper ya validó).

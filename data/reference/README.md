# /data/reference

Datos y parámetros tomados de la literatura, con la justificación de cada
valor del modelo. Distinguir siempre de `python/resultados/` (datos
generados por nuestras simulaciones).

## Vigentes (los usa el modelo actual)

| Archivo | Para qué |
|---|---|
| `roa_cenicafe_isoterma_capa_delgada.md` | Isoterma de Roa (Trejos et al., 1989) y ecuación de capa delgada de SECAFÉ: el modelo cinético único. Erratas detectadas y verificación cruzada. |
| `secador_electrico_dimensionamiento.md` | Dimensionamiento del secador supervisado (lote, caudal, lecho, resistencia, plenum) con fuentes. |
| `equipos_energia.md` | Equipos comerciales (ventilador S&P, resistencias Tempco, extractor de la activa) y su consumo. Insumo del objetivo 4. |
| `chinchina_clima_fuentes.md` | Clima de Chinchiná: medias de Naranjal, horas de T mín/máx, variabilidad con NASA POWER. |
| `validacion_modelo.md` | Validación contra 4 casos independientes (laboratorio, patio, secador Escafé, secado solar). |
| `phitakwinai_2019_tabla2_parametros.csv` | Tabla 2 de Phitakwinai et al. (2019). La usa `python/validacion_modelo.py` (caso V1). |
| `eliseu_2008_secado_patio.md` | Secado en patio en Brasil. Hoy solo validación independiente (caso V2). |

## Históricos (modelos retirados, ver `docs/evolucion_del_modelo.md`)

| Archivo | Para qué se usó |
|---|---|
| `phitakwinai_2019_tabla3_ecuaciones_generalizadas.md` | Midilli generalizado de la planta del 23 sept 2026 (`python/legacy/cinetica_dinamica.py`). |
| `mackpayen_2017_icaro_dryer.md` | Línea base activa v0.1 (modelo Logarítmico, `python/legacy/lineas_base_v01.py`). |

---

Detalle histórico de la Tabla 2 y 3 de Phitakwinai et al. (2019):

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

Convenciones del paper (importante, distintas de `python/legacy/modelo_secado.py`):

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

## Uso en el ajuste (semana 5, histórico)

`python/legacy/ajuste_modelos.py` usa la fila `Modified_Midilli, T=60, RH=20`
(mejor r² individual: 0.9997, RMSE = 2.323 %) para generar una curva de
referencia MR(t) con la ecuación *ya publicada y validada* por los
autores, y ajusta contra ella nuestros tres modelos candidatos (Newton,
Logarítmico, Midilli modificado) calculando RMSE, MAE y R² con nuestra
propia implementación. Ver el docstring de ese módulo para el detalle
completo de esta metodología y sus limitaciones (no son lecturas punto a
punto de un experimento propio, sino la reproducción de la curva que el
paper ya validó).

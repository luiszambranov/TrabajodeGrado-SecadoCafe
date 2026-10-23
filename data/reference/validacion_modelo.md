# Validación del modelo contra datos independientes

Script: `python/validacion_modelo.py` (reproduce todos los números).

**Criterio:** solo cuentan como validación los datos que **no** se usaron
para construir ni calibrar el modelo. Se valida en cuatro tipos de secado
distintos, para no apoyarse en un solo caso.

| Pieza del modelo | Usada en |
|---|---|
| Cinética de Roa (capa delgada + isoterma) | Las 3 estrategias |
| Lecho por capas (Thompson) + balance del aire | Supervisada |
| Clima de Chinchiná + calentamiento solar efectivo | Solares |

## 1. Resultados

| # | Tipo de secado | Fuente (independiente) | Dato real | Modelo | Error |
|---|---|---|---|---|---|
| V1 | Capa delgada en laboratorio, 9 condiciones (50–70 °C, 10–30 % HR) | Phitakwinai et al. (2019), *Food Sci. Nutr.* 7(9) | Tiempo hasta MR = 0.2: 5.9–14.5 h | 5.4–14.3 h | **7.2 % medio**, RMSE 0.76 h (≤ 2 % a 50 °C; hasta −19 % a 70 °C) |
| V2 | Patio al sol, condiciones medias | Resende et al. (2009), café robusta, Brasil | 117.5 h | 125.6 h | **+6.9 %** |
| V3 | Secador mecánico de lecho estático (30 cm, 125 kg, 48 °C, 15 h/día, inversión cada 7.5 h) | Martínez-Tovar & Álvarez-Hernández (2006), *Cenicafé* 57(2) — Escafé | ~3 d; 7 297 kJ/kg agua; capas 8.4–12.7 % | 1.7–2.3 d; **6 962–8 560 kJ/kg**; capas 9.3–10.4 % | Tiempo **−25 a −45 %**; energía **−5 a +17 %** |
| V4 | Secado solar, grupo de 1 061–1 399 h/año de sol (predicho, no calibrado) | Guerrero-Aguirre et al. (2025), Avances Técnicos Cenicafé | 15.5 d (rango 5.2–36.1) | 11.7 d | **−24 %**, dentro del rango |

Contraste adicional (no son validación estricta, ver sección 2):

| Tipo | Fuente | Dato real | Modelo | Lectura |
|---|---|---|---|---|
| Silos de Cenicafé de 2–3 pisos, 50 °C | Roa et al. (2000) AVT 282; Oliveros et al. (2009) AVT 380; Oliveros et al. (2010) *Cenicafé* 61(2) | 18–24 h | 33.1 h (nuestro secador, 1 capa) | Modelo más lento: diferencia de configuración (varios pisos que reaprovechan el aire) |
| Secador parabólico en estación experimental, volteo 4 veces/día | Oliveros et al. (2013), *Secado solar y secado mecánico del café*; Gallego, Imbachi & Osorio (2023), *Cenicafé* 74(1) | 3–7 d; 2–5 d (promedio 4 d) | 10.7 d (calibrado al promedio de fincas) | El modelo representa la finca promedio, no la estación experimental con manejo óptimo |

## 2. Interpretación

1. **La cinética (lo que comparten las 3 estrategias) está validada:** error
   medio de 7 % en laboratorio y de 7 % en patio, con datos de otros países y
   otra especie. A 70 °C el modelo es hasta 19 % más rápido, pero la
   supervisada trabaja a 50 °C, donde el error es ≤ 2 %.
2. **La energía del secador mecánico está validada:** contra el Escafé, el
   modelo da entre −5 y +17 % del consumo específico medido. Es el resultado
   más importante para el objetivo 4 y para la comparación energética.
3. **El tiempo del secador mecánico tiene una incertidumbre de ±30–45 %, pero
   SIN sesgo sistemático:** contra los silos de Cenicafé el modelo es más
   lento (+35–80 %), y contra el Escafé es más rápido (−25 a −45 %). Que el
   error cambie de signo según el secador indica que viene de la
   configuración de cada equipo (pisos, caudal real, horas de calor,
   humedad inicial no reportada), no de un error de la física del modelo.
4. **Uniformidad del lecho:** el modelo predice capas más parejas (9.3–10.4 %)
   que las medidas en el Escafé (8.4–12.7 %), porque supone que el aire se
   reparte igual en toda la bandeja. Es una limitación declarada.
5. **Secado solar:** la predicción cruzada cae dentro del rango real
   (−24 % frente al promedio). El tiempo solar depende mucho del manejo
   (volteos, carga): de 4 días en estación experimental a 10.6 días de
   promedio en fincas. El modelo representa la finca promedio. Para el
   análisis de sensibilidad se puede correr también un escenario de
   "buenas prácticas" (DT_MAX ≈ 13–15 °C, ~4.5–5 días).

**Conclusión para el documento:** el modelo reproduce la cinética con ~7 %
de error y la energía con ±17 %. El tiempo absoluto de los secadores tiene
una incertidumbre de ±30–45 % que depende de la configuración y no tiene
sesgo. Como la propuesta supervisada es de 4 a 8 veces más rápida que las
solares, esa incertidumbre no cambia la conclusión de la comparación.

## 3. Supuestos propios en V3 y V4

- V3: caudal real a través del lecho deducido de la presión del ventilador
  (10 mm c.a.) con la ecuación de Boyce & Pérez-Fonrodona → 0.117 m³/min/kg.
  El dato de 1.15 m³/s es el caudal nominal del ventilador, no el que pasa
  por 30 cm de café. Estufa encendida de 05:00 a 20:00. Humedad inicial de
  44, 48 y 53 % b.h. (la fuente no la da con precisión).
- V4: calentamiento solar efectivo escalado con las horas de sol
  (4.4 °C × 1 230/1 600 = 3.38 °C).

## 4. Referencias

- Phitakwinai, P., Thepa, S., & Nilnont, W. (2019). Thin-layer drying of
  parchment Arabica coffee by controlling temperature and relative humidity.
  *Food Science & Nutrition, 7*(9), 2921–2931. https://doi.org/10.1002/fsn3.1144
- Resende et al. (2009): ver `resende_2009_secado_patio.md`.
- Martínez-Tovar, D. G., & Álvarez-Hernández, J. R. (2006). Aprovechamiento
  de la energía calórica de estufas campesinas para el secado del café en
  fincas. *Cenicafé, 57*(2), 88–99.
  https://www.cenicafe.org/es/publications/arc057%2802%29088-099.pdf
- Guerrero-Aguirre, Á., Sanz-Uribe, J. R., Peñuela-Martínez, A. E., &
  Osorio-G., C. V. (2025). *Manejo del café en el secado solar* (Avances
  Técnicos No. 577). Cenicafé. https://doi.org/10.38141/10779/0577
- Oliveros-Tascón, C. E., Ramírez-Gómez, C. A., Sanz-Uribe, J. R.,
  Peñuela-Martínez, A. E., & Pabón-Usaquén, J. (2013). Secado solar y
  secado mecánico del café. Cenicafé.
  https://biblioteca.cenicafe.org/bitstream/10778/4345/1/cenbook-0026_29.pdf
- Gallego, C. P., Imbachi, L. C., & Osorio, V. (2023). Influencia del
  proceso de secado del café natural en las características físicas del
  grano y la calidad sensorial. *Cenicafé, 74*(1), e74107.
  https://cenicafe.org/es/publications/Articulo_Influencia.pdf
- Roa et al. (2000), Oliveros et al. (2009) y (2010): ver
  `secador_electrico_dimensionamiento.md`, sección 6.
- Boyce & Pérez-Fonrodona: ver `equipos_energia.md`.

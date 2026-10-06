# Clima de Chinchiná y secado solar: fuentes y ajustes del 4 oct 2026

Resumen de qué dato del modelo sale de qué fuente, después de ajustar el
modelo a Chinchiná (punto 3 de la auditoría del modelo).

## 1. Valores medios del clima (estación Naranjal, Cenicafé)

Fuente: "El clima de la estación central Naranjal". *Cenicafé, 49*(4),
290–307 (1998). https://www.cenicafe.org/es/publications/arc049%2804%29290-307.pdf

| Dato | Valor | Uso |
|---|---|---|
| Ubicación | 04°58' N, 75°39' O, 1 381 msnm | Punto de referencia del modelo |
| T mínima / máxima media anual | 16.4 / 26.8 °C | `T_MIN_MEDIO`, `T_MAX_MEDIO` |
| Variación estacional | mínimas 0.7 °C, máximas 1.6 °C | Justifica usar un día tipo todo el año |
| Extremos absolutos | 11.0 °C (1963) / 33.6 °C (1973) | Chequeo de plausibilidad de sigma |
| HR media | 76–81 %, saturación (> 95 %) de noche | `FRACCION_SATURACION_NOCTURNA = 0.97` |
| Brillo solar | 1 817 h/año (41 % del máximo teórico) | Grupo de 1 400–1 800 h para el secado solar |

## 2. Forma del ciclo diario de temperatura (NUEVO)

Fuente: Guzmán Martínez, O., & Ramírez Gaviria, J. J. (2004). Cálculo de la
temperatura en dos localidades cafeteras de Colombia. *Cenicafé, 55*(2),
111–129. https://www.cenicafe.org/es/publications/arc055%2802%29111-129.pdf

> "La temperatura mínima ocurre entre las 05:00 y las 06:00 y la máxima
> entre las 15:00 y las 16:00" (p. 112, sede Cenicafé, Chinchiná).

**Cambio en `generador_ambiente.py`:** curva asimétrica de dos semicosenos con
el mínimo a las 05:30 y el máximo a las 15:30. Antes era un seno simétrico
con el mínimo a las 02:00 y el máximo a las 14:00.
Limitación: la media de la curva es (T_min + T_max)/2 = 21.6 °C, 0.8 °C
por encima de la media medida (20.8 °C), porque el día real pasa más horas
cerca de la mínima.

## 3. Radiación solar (para el balance de energía de las estrategias solares)

Fuente: *Cenicafé, 54*(2), 110–133 (2003).
https://www.cenicafe.org/es/publications/arc054%2802%29110-133.pdf
Radiación global en la sede Cenicafé (Chinchiná): **4 582 Wh/m²/día** de
media anual (≈ 16.5 MJ/m²/día); de 4 295 (octubre) a 4 999 Wh/m²/día (marzo).

## 4. Secado solar en Colombia (calibración de las líneas base, NUEVO)

Fuente: Peñuela-Martínez, A. E., Osorio Giraldo, C. V., Guerrero, A., &
Sanz-Uribe, J. R. (2025). *Manejo del café en el secado solar*. Avances
Técnicos Cenicafé. https://doi.org/10.38141/10779/0577

| Dato | Valor | Uso |
|---|---|---|
| Capacidad de diseño | 7.2 kg c.p.s./m², capa de 2.0 cm | Área solar = 80/7.2 = **11.1 m²** (antes 12.8 m²) |
| Humedad final | 10–12 % b.h. | Objetivo 11 % |
| Tiempo con 1 400–1 800 h/año de sol | **10.6 días** promedio (6.2–19.1) | Calibración de la línea base pasiva |
| Tiempo con 1 061–1 399 h/año de sol | 15.5 días promedio (5.2–36.1) | Sensibilidad |

**Cambios:**
- Línea base pasiva (`escenario_sol_abierto.py`): `DT_MAX_PATIO_C` 12.9 → **4.4 °C**,
  calibrado para que el día nominal dé 10.6 días (resultado 255.8 h = 10.66 d).
  Antes se calibraba contra Eliseu (2008), café robusta en Brasil.
- Línea base activa (`linea_base_activa.py`): `DT_MAX_ACTIVA_C` 20 → **12.5 °C**.
  Da una reducción del 47.5 % frente a la pasiva (134.3 h = 5.6 d), dentro del
  30–50 % de Duque-Dussan et al. (2026) y del 40–50 % de Meja et al. (2025).
- Ambos DT_MAX son **parámetros efectivos**: el día nominal tiene sol todos
  los días, mientras que el promedio de Cenicafé incluye días nublados y de
  lluvia.

## 5. Variabilidad día a día (RESUELTO 4 oct 2026)

Datos: NASA Langley Research Center POWER Project, serie diaria 2005–2024,
punto 4.97 N / 75.65 O (reanálisis MERRA-2, celda de 0.5° × 0.625°,
elevación media de la celda 2 138 m), parámetros T2M_MAX, T2M_MIN, QV2M y PS.
https://power.larc.nasa.gov (consultado el 4 oct 2026). Archivo:
`data/clima/POWER_Naranjal_diario_2005_2024.csv` (7 305 días).

Método delta (`python/variabilidad_clima.py`): las medias se quedan de
Naranjal y de la serie solo se toman las anomalías respecto a la media de
cada mes. La celda es 4–6 °C más fría que Naranjal (12.7 / 20.8 °C contra
16.4 / 26.8 °C) por su mayor elevación; ese sesgo no entra al modelo.

| Parámetro | Antes (supuesto) | Ahora (NASA POWER) |
|---|---|---|
| sigma T_min | 1.5 °C | **0.97 °C** |
| sigma T_max | 1.5 °C | **1.36 °C** |
| Correlación T_min–T_max | 0 | −0.07 (≈ 0) |
| Persistencia de un día al siguiente | 0 (días independientes) | **T_min 0.49, T_max 0.39** → modelo AR(1) |
| Ruido de ea | 8 % | **4 %** residual sobre ea = f(T_min), persistencia 0.22 |

Implementado en `generador_ambiente.secuencia_dias_perturbados()` (AR(1)).
Limitación: un reanálisis suaviza los extremos (los récords de Naranjal
quedan a ~5 sigma), así que sigma podría estar algo subestimada. Se recomienda
correr la sensibilidad con sigma = 1.5 °C.

Piloto rápido (8 realizaciones de 40 días): pasiva 244.5 ± 22.6 h, activa
135.9 ± 14.3 h, supervisada 33.2 ± 0.39 h.

## 6. Resultados del día nominal después de los ajustes

| Estrategia | Antes (29 sept) | Después (4 oct) |
|---|---|---|
| Solar pasiva | 130.9 h (5.5 d) | **255.8 h (10.7 d)** |
| Solar activa | 84.2 h (3.5 d) | **134.3 h (5.6 d)** |
| Supervisada (eléctrica, 50 °C) | 33.2 h | **33.1 h** |

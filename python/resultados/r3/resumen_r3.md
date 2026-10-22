# R3 · Efecto del clima: prueba dirigida (21 oct 2026)

Generado por `python/r3_sensibilidad_clima.py` (12 corridas dirigidas + 4 solares). Mismo lote, M0 = 55 % b.h., inicio 00:00, criterio de fin promedio ≤ 11 % y capa más húmeda ≤ 12 % b.h.

## Cadena de datos

| Paso | Qué | Archivo / función | Unidades |
|---|---|---|---|
| Fuente 1 (medición) | Medias de T mín y T máx de la estación Naranjal (Cenicafé) | `generador_ambiente.T_MIN_MEDIO`, `T_MAX_MEDIO` (Baldión-Rincón y Guzmán-Martínez, 1998) | °C |
| Fuente 2 (reanálisis) | Serie diaria NASA POWER 2005-2024, punto 4.97 N, 75.65 O: `T2M_MAX`, `T2M_MIN`, `QV2M`, `PS` | `data/clima/POWER_Naranjal_diario_2005_2024.csv`; `variabilidad_clima.leer_power_csv` | °C, g/kg, kPa |
| Transformación | ea = q·PS/(0.622+0.378q); anomalías respecto a la media mensual; media móvil de 2 días; percentiles 5 y 95 (7305 días) | `niveles_clima.anomalias_percentiles` | °C, fracción |
| Niveles (sintéticos) | Medias de Naranjal + anomalía percentil; ea con consistencia psicrométrica | `niveles_clima.niveles` | °C, kPa |
| Perturbación horaria | Ciclo diario asimétrico (mín. 05:30, máx. 15:30); HR = ea/es(T) | `generador_ambiente.temperatura`, `humedad_relativa`, `ambiente_en` | °C, % |
| Entrada a la planta | T_amb y ea entran al balance del plenum (Ec. 5) y al aire del lecho (misma ea; HR de proceso = ea/es(T_proceso)) | `dinamica_termica.paso_plenum`, `rh_proceso`; `lecho_secado.LechoThompson.paso` | °C, kPa |
| Salidas | Humedad del café por capa, tiempo hasta el criterio, energía, ciclo de trabajo | `corrida_instrumentada.correr` | % b.h., h, kWh |

Los niveles son realizaciones sintéticas construidas con percentiles; no son mediciones de la estación.

## Niveles de clima

| Nivel | T mín [°C] | T máx [°C] | ea [kPa] | HR madrugada | HR tarde | Origen |
|---|---|---|---|---|---|---|
| C0 | 16.40 | 26.80 | 1.809 | 97.0 % | 51.3 % | Medias de Naranjal; ea = 0.97·es(Tmín) |
| CT- | 14.95 | 24.91 | 1.649 | 97.0 % | 52.3 % | p5 anomalías 2 d: Tmín -1.45, Tmáx -1.89 °C; HR nocturna conservada |
| CT+ | 17.69 | 28.61 | 1.964 | 97.0 % | 50.1 % | p95 anomalías 2 d: Tmín +1.29, Tmáx +1.81 °C; HR nocturna conservada |
| CH- | 16.40 | 26.80 | 1.664 | 89.2 % | 47.2 % | p5 anomalía de ea 2 d: -8.1 %; T nominal |
| CH+ | 16.40 | 26.80 | 1.856 | 99.5 % | 52.7 % | p95 de ea (+7.3 %) imposible a T nominal (HR nocturna > 100 %): se usa HR nocturna 99.5 % (+2.6 %) |
| C* | 14.95 | 24.91 | 1.691 | 99.5 % | 53.7 % | T del CT-; ea = 0.995·es(Tmín) (corr. T-ea en la serie = +0.50: el frío viene seco; la noche saturada es lo más húmedo físicamente posible) |

## Resultados (supervisadas)

| Estrategia | Clima | t fin [h] | Δt vs C0 | kWh/kg | ΔE vs C0 | Humedad a 24 h [% b.h.] | Ciclo de trabajo [%] | P media [kW] | Saturado [h] | Margen mín. [°C] | Grano > 50 °C [h] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| REF | C0 | 33.15 | +0.0 % | 1.8045 | +0.0 % | 20.11 | 69.2 | 4.15 | 0.0 | 8.42 | 0.0 |
| P1-C75 | C0 | 46.75 | +0.0 % | 1.5029 | +0.0 % | 30.74 | 41.4 | 2.48 | 0.0 | 27.04 | 0.0 |
| REF | CT- | 32.4 | -2.3 % | 1.8627 | +3.2 % | 19.51 | 73.3 | 4.4 | 0.0 | 6.76 | 0.0 |
| P1-C75 | CT- | 45.4 | -2.9 % | 1.5686 | +4.4 % | 30.06 | 44.6 | 2.68 | 0.0 | 25.32 | 0.0 |
| REF | CT+ | 33.88 | +2.2 % | 1.7486 | -3.1 % | 20.67 | 65.4 | 3.93 | 0.0 | 9.9 | 0.0 |
| P1-C75 | CT+ | 48.08 | +2.8 % | 1.4427 | -4.0 % | 31.38 | 38.6 | 2.31 | 0.0 | 28.57 | 0.0 |
| REF | CH- | 32.48 | -2.0 % | 1.7663 | -2.1 % | 19.58 | 69.1 | 4.15 | 0.0 | 8.42 | 0.0 |
| P1-C75 | CH- | 45.55 | -2.6 % | 1.4651 | -2.5 % | 30.13 | 41.4 | 2.49 | 0.0 | 27.04 | 0.0 |
| REF | CH+ | 33.37 | +0.7 % | 1.8166 | +0.7 % | 20.28 | 69.2 | 4.15 | 0.0 | 8.42 | 0.0 |
| P1-C75 | CH+ | 47.13 | +0.8 % | 1.5155 | +0.8 % | 30.93 | 41.4 | 2.49 | 0.0 | 27.04 | 0.0 |
| REF | C* | 32.58 | -1.7 % | 1.8739 | +3.8 % | 19.67 | 73.3 | 4.4 | 0.0 | 6.76 | 0.0 |
| P1-C75 | C* | 45.75 | -2.1 % | 1.5802 | +5.1 % | 30.24 | 44.6 | 2.68 | 0.0 | 25.32 | 0.0 |

## Ahorro de P1-C75 frente a REF en cada clima (pareado: mismo clima)

| Clima | Ahorro de energía | Tiempo adicional |
|---|---|---|
| C0 | 16.7 % | +13.6 h (+41 %) |
| CT- | 15.8 % | +13.0 h (+40 %) |
| CT+ | 17.5 % | +14.2 h (+42 %) |
| CH- | 17.1 % | +13.1 h (+40 %) |
| CH+ | 16.6 % | +13.8 h (+41 %) |
| C* | 15.7 % | +13.2 h (+40 %) |

## Líneas solares (contraste nominal / adverso)

| Estrategia | Clima | t fin [h] | Δt vs C0 | Humedad a 24 h [% b.h.] | kWh/kg comprados |
|---|---|---|---|---|---|
| PASIVA | C0 | 255.84 | +0.0 % | 45.47 | 0.0 |
| ACTIVA | C0 | 134.33 | +0.0 % | 40.98 | 0.0342 |
| PASIVA | C* | 327.2 | +27.9 % | 46.8 | 0.0 |
| ACTIVA | C* | 157.35 | +17.1 % | 42.58 | 0.0397 |

# Equipos comerciales y balance de energía de las tres estrategias

Implementado en `python/balance_energia.py`. Todas las estrategias secan el
mismo lote de 80 kg c.p.s. de 55 a 11 % b.h. (78.2 kg de agua).

## 1. Equipos seleccionados

| Estrategia | Equipo | Dato de catálogo | Uso en el modelo |
|---|---|---|---|
| Supervisada | **Resistencia**: 3 elementos tubulares aleteados Tempco de 2 000 W / 240 V | 6 kW instalados | Ver `secador_electrico_dimensionamiento.md` |
| Supervisada | **Ventilador centrífugo Soler & Palau CBM/6-180/180-N-72W** | Motor 72 W (1/10 CV), 960 rpm, 1.0 A máx., caudal máx. 1 400 m³/h; curva a 220 V: **~118 Pa a 480 m³/h** | 0.20 kW de consumo (220 V × 1.0 A × FP 0.9) |
| Solar activa | **Extractor helicoidal Soler & Palau HCM-225N** | 40 W, 695 m³/h, 230 V | 1 unidad, encendida de 06:00 a 18:00 |
| Solar pasiva | — | — | Sin consumo eléctrico |

Fuentes:
- Soler & Palau. *Serie CBM Grande – Ventiladores centrífugos de baja
  presión* (catálogo técnico, curvas características según UNE 100-212-89,
  AMCA 210-85 y ASHRAE 51-1985), pp. 392–393.
  https://documentacion.generadordeprecios.info/documentaciontecnica/soler-palau/solerpalau_cbm.pdf
- Soler & Palau HCM-225N, ref. 5201421400 (ficha de distribuidor).
  https://groupsumi.es/en/home-and-kitchen/industrial-air-extraction/helical-extractor/helical-window-extractor-hcm-225n-230v-1700rpm-5201421400
- Madhava, M., et al. (2017). Performance evaluation of photovoltaic
  ventilated hybrid greenhouse dryer under no-load condition. *Agricultural
  Engineering International: CIGR Journal*. Secador de invernadero de
  ~9.5 m² con un extractor de 40 W (criterio de escala para la solar activa).
  https://cigrjournal.org/index.php/Ejounral/article/download/4146/2548/18805

Nota: los catálogos son de 50 Hz (Europa). Soler & Palau tiene distribución
en Colombia y versiones de 60 Hz; a 60 Hz el motor gira ~20 % más rápido, lo
que da más caudal y presión (margen a favor). Para el objetivo 4 hay que
cotizar la versión de 60 Hz.

## 2. Caída de presión del sistema (selección del ventilador)

**Lecho de café pergamino:** Boyce, D. S., & Pérez-Fonrodona, A. A.
*Observations on the resistance to vertical airflow of green and parchment
coffees*. Journal of Agriculture of the University of Puerto Rico, pp. 55–64.
https://revistas.upr.edu/index.php/jaupr/article/view/12294

    P_av = 0.0014 · V^1.46   [pulg. de agua por pie de lecho; V en cfm/ft²]

| Paso | Valor |
|---|---|
| Velocidad del aire: 8 m³/min ÷ 1.28 m² | 0.104 m/s = 20.5 cfm/ft² |
| Caída por pie de lecho | 0.0014 × 20.5^1.46 = 0.115 pulg. agua/pie |
| Lecho de 20 cm (0.656 pie) | 0.076 pulg. agua ≈ **19 Pa** |
| Con factor 1.5 (café húmedo y compactado) | ~28 Pa |
| Resistencia aleteada, compuertas de inversión, ductos y plenum (estimación propia) | ~70 Pa |
| **Total de diseño** | **~100 Pa** |

El CBM/6-180/180-N-72W entrega ~118 Pa a 480 m³/h (curva a 220 V): cubre el
sistema con ~18 % de margen. Si hiciera falta más presión, el siguiente
modelo de la misma serie es el CBM/4-180/180-N-150W (~255 Pa a 480 m³/h).

## 3. Radiación solar

Radiación global media anual en la sede de Cenicafé (Chinchiná):
**4 582 Wh/m²/día** (de 4 295 en octubre a 4 999 en marzo). *Cenicafé, 54*(2),
110–133. https://www.cenicafe.org/es/publications/arc054%2802%29110-133.pdf
Se reparte en medio seno de 06:00 a 18:00 sobre los 11.1 m² de secado solar.

## 4. Resultados (día nominal de Chinchiná)

| Estrategia | t_obj | Eléctrica comprada | Solar incidente | Total | kWh/kg c.p.s. comprado | SEC total [kJ/kg agua] | Eficiencia térmica |
|---|---|---|---|---|---|---|---|
| Solar pasiva | 255.8 h | 0 kWh | 556 kWh | 556 kWh | 0.000 | 25 591 | 9.5 % |
| Solar activa | 134.3 h | 2.7 kWh | 295 kWh | 297 kWh | 0.034 | 13 684 | 17.8 % |
| Supervisada | 33.1 h | 144.4 kWh | 0 | 144 kWh | 1.804 | 6 643 | 36.6 % |

**Lectura:** el sol es gratis pero se aprovecha poco (9.5–18 %). La
supervisada usa ~4 veces menos energía total por kg de agua, pero toda es
comprada. Ese es el contraste para el objetivo 4: costo de operación contra
tiempo y control del proceso.

**Chequeo de orden de magnitud:** en el secado mecánico con carbón, Cenicafé
reporta 2.8 kg de carbón por arroba (12.5 kg) de c.p.s. con un intercambiador
del 52 % de eficiencia (Oliveros et al., 2009, Avances Técnicos 380). Con un
poder calorífico de ~26 MJ/kg (carbón bituminoso, supuesto propio), eso da
~5 900 kJ/kg de agua, del mismo orden que los 6 643 kJ/kg del modelo.

## 5. Limitaciones

- La radiación es la media anual en todos los días; no varía por realización
  Monte Carlo.
- La eficiencia térmica usa el calor latente del agua libre (2 430 kJ/kg); el
  agua ligada del café requiere algo más (Trejos et al., 1989).
- La caída de presión de accesorios (~70 Pa) es una estimación propia.
- Costo: `BalanceEnergia.costo_cop(tarifa)`. La tarifa de energía de la CHEC
  (Caldas) se fija en el objetivo 4.


## 6. Caudal variable: manipulada 2

El modelo tiene dos variables manipuladas: (1) potencia/estado del
calentamiento y (2) velocidad o caudal del ventilador.

- **Fuente del criterio:** González, Sanz & Oliveros (2010), *Cenicafé*
  61(4): controlan el caudal con un PI y un variador de frecuencia para
  mantener 0.1 m³/min/kg según la masa cargada. Reportan hasta 84 % menos
  energía eléctrica y 28 % menos combustible en el lecho de 20 cm.
- **Rango:** 30–100 % del caudal nominal (8 m³/min). El mínimo del 30 % es un
  criterio propio: protege el calentador de ducto y el par del motor.
- **Potencia del ventilador a caudal parcial:** leyes de afinidad,
  P ∝ (Q/Q_nom)³ (ASHRAE Handbook – HVAC Systems and Equipment, cap. Fans).
  Es el caso ideal con variador; con regulador de tensión (Soler & Palau
  serie REB, curvas del catálogo CBM a 130/180/220 V) el ahorro real es menor.
  El ventilador pesa ~5 % de la energía total, así que esta incertidumbre
  importa poco.
- **Implementación:** `ParametrosSecador.caudal_min_frac`,
  `SecadorElectrico.paso(fan_frac=...)`, `ParametrosControl.caudal_frac`
  (número fijo o función del tiempo y la humedad, para perfiles de caudal).
  Modbus: consigna en el registro 20 (%), caudal real en los registros 22-23 (m³/min).

Efecto en el día nominal (50 °C, inversión cada 6 h, caudal fijo durante todo el secado):

| Caudal | t_obj | Resistencia | Ventilador | Total | Capas finales |
|---|---|---|---|---|---|
| 100 % (8 m³/min) | 33.1 h | 137.7 kWh | 6.63 kWh | 144.4 kWh | 9.4–11.8 % |
| 75 % | 37.6 h | 117.1 kWh | 3.17 kWh | 120.3 kWh | 9.0–12.0 % |
| 50 % | 47.5 h | 97.2 kWh | 1.19 kWh | 98.4 kWh | 8.2–12.0 % |
| 30 % | 69.1 h | 87.4 kWh | 0.37 kWh | 87.8 kWh | 6.8–12.0 % |

**Lectura:** con menos aire el secado es más lento pero gasta menos energía,
porque el aire sale más cargado de humedad (se aprovecha mejor). El costo es
un lecho menos parejo. Este compromiso entre tiempo, energía y uniformidad es
el que se explora con los perfiles térmicos y de caudal.

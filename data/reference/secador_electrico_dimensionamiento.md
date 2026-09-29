# Secador eléctrico de la propuesta supervisada — dimensionamiento y fuentes

Decisión de diseño (29 sept 2026): **lote de 80 kg de café pergamino seco
(c.p.s.)**, calentamiento con **resistencia eléctrica**. Implementado en
`python/dinamica_termica.py` (`ParametrosSecador`), `python/lecho_secado.py`
(lecho por capas) y `python/secador_electrico.py`.

## 1. Criterios de Cenicafé

Fuente: González S., C. A., Sanz U., J. R., & Oliveros T., C. E. (2010).
Control de caudal y temperatura de aire en el secado mecánico de café.
*Cenicafé, 61*(4), 281–296. https://biblioteca.cenicafe.org/handle/10778/503

| Criterio | Valor | Uso en el modelo |
|---|---|---|
| Temperatura máxima del grano sin daño irreversible | **50 °C** | Setpoint del control (`t_setpoint_c`) y métrica "horas grano > 50 °C" |
| Caudal específico óptimo, lecho estático | **0.1 m³/min por kg c.p.s.** | 80 kg → 8.0 m³/min |
| Espesores evaluados | 20, 30, 40, 54 cm (menor espesor = mayor ahorro) | Lecho de **20 cm** |
| Ventilador del secador experimental | 4.95 kW para 2 000 kg c.p.s. (2.475 W/kg) | 80 kg → **0.20 kW** (escalado lineal, mismo caudal específico y espesor) |
| Resultado experimental | ~49 h promedio, 53 % → 10–12 % b.h. (lotes de ~1 500 kg, 20–54 cm) | Referencia de validación |

## 2. Potencia de la resistencia

Balance de energía sobre el aire que atraviesa el café:

```
P = ρ · V̇ · cp · (T_set − T_amb,mín) · FS
```

| Variable | Valor | Fuente |
|---|---|---|
| ρ | 1.03 kg/m³ | Gas ideal a 86.6 kPa (atmósfera estándar a ~1 350 msnm, Naranjal) y 14.3 °C |
| V̇ | 8.0 m³/min = 0.133 m³/s | 0.1 m³/min/kg × 80 kg (Cenicafé) |
| cp | 1.006 kJ/(kg·K) | Aire seco |
| T_set | 50 °C | Cenicafé |
| T_amb,mín | 14.3 °C | Percentil 1 del generador de ambiente de Chinchiná (`generador_ambiente.py`) |
| FS | 1.1 | Factor de seguridad, práctica de fabricantes (Tempco) |

Resultado: **5.5 kW requeridos → 6.0 kW instalados** = 3 elementos tubulares
aleteados de 2 000 W a 240 V.

Verificación con la fórmula del fabricante: `kW = SCFM·ΔT(°F)/3190 + FS`
(Tempco, *Finned Tubular Watt Density*; Marley: `kW = CFM·ΔT/3160`), que es
la misma ecuación en unidades inglesas.

Fuentes de fabricante:
- Tempco. *Finned Tubular Heaters* (catálogo): elementos de 1 000–2 000 W a
  240 V, vaina de acero o inoxidable, densidad máx. 62–64 W/in².
  https://www.tempco.com/Tempco/Resources/10-Tubular-Resources/FinnedTubularCatalogPages.pdf
- Tempco. *Finned Tubular Watt Density* (fórmula de dimensionamiento).
  https://www.tempco.com/Tempco/Resources/10-Tubular-Resources/FinnedTubularWattDnsty.pdf
- Marley Engineered Products. *Duct Heater — How to Size*.
  https://www.marleymep.com/wp-content/uploads/zbr-mdhht_how-to-size_0.pdf

**Enclavamiento de flujo:** los calentadores de ducto exigen interruptor de
flujo de aire (sin aire, el elemento se sobrecalienta). En el modelo, la
resistencia solo entrega potencia si `fan_cmd = 1`; el PLC debe replicarlo
(`heater_cmd := heater_req AND fan_on`).

## 3. Lecho de café

| Parámetro | Valor | Fuente |
|---|---|---|
| Densidad aparente | DA = 365.884 + 2.7067·M (% b.s.) → 696 kg/m³ al inicio | Montoya (1989), en SECAFÉ (2008), ec. 17 |
| Área de bandeja | 1.28 m² (158 kg húmedos, 20 cm) | Calculada |
| Calor específico | CP = 1.3556 + 5.7859·M (decimal b.s.), kJ/(kg m.s.·K) | Montoya (1989), en SECAFÉ (2008), ec. 12 (medido 11–45 % b.h.) |
| Capas | 8 × 2.5 cm | Thompson et al. (1968); SECAFÉ (2008) |

### Por qué el lecho por capas (Thompson)

Con 0.1 m³/min/kg, el aire a 50 °C puede llevarse como máximo
**~0.065 kg de agua/h por kg c.p.s.** antes de saturarse (saturación
adiabática, bulbo húmedo ≈ 25 °C), pero la capa delgada de Roa pide
**~0.127** al inicio. Sin el balance de humedad del aire, el modelo secaría
unas 2 veces más rápido de lo posible. El modelo de Thompson (el que usa
SECAFÉ) hace el balance de calor latente y de humedad capa por capa.

Resultados con aire a 50 °C constante, día nominal de Chinchiná:

| Modelo | Tiempo 55 → 11 % b.h. |
|---|---|
| Capa delgada pura (sin límite del aire) | 20.7 h |
| **Lecho de 20 cm, 8 capas (Thompson), sin inversión, parada por promedio** | **32.5 h** |
| Cenicafé, lechos de 20–54 cm y ~1 500 kg (promedio) | ~49 h |

Convergencia numérica: con capas de 1.25 cm o subpasos de 1.2–6 min el
resultado cambia ≤ 0.25 h.

Sin inversión del aire, al final la capa inferior queda en 6.6 % b.h. y la
superior en 16.9 % b.h. (gradiente típico de lecho estático).

### Inversión del sentido del aire (modelada el 29 sept 2026)

Cenicafé invierte el sentido del aire en los secadores estáticos cada 6 h
(SECAFÉ, 2008: secador estático con "inversión del sentido del flujo de aire
cada 6 h"). En `lecho_secado.py`, con `flujo_invertido=True` el aire entra
por la capa superior. Con la parada exigiendo promedio ≤ 11 % y capa más
húmeda ≤ 12 % b.h. (control a 50 °C, día nominal):

| Operación | t_obj | Capas al final (% b.h.) | kWh/kg c.p.s. |
|---|---|---|---|
| Sin inversión | 38.0 h | 6.0 – 12.0 (promedio 8.3: sobresecado) | 2.01 |
| **Inversión cada 6 h** | **33.2 h** | **9.4 – 11.8** (promedio 11.0) | **1.79** |

La inversión acorta el secado un 13 %, ahorra un 11 % de energía y deja todo
el lote dentro de 10–12 % b.h. Sin inversión, para que la capa húmeda llegue
a 12 % hay que sobresecar la inferior hasta 6 %, lo que implica pérdida de
peso vendible y de calidad.

**Implementación física (nota para FluidSIM):** en la práctica el sentido del
aire en el lecho no se invierte cambiando el giro del motor del ventilador.
Un ventilador centrífugo que gira al revés sigue soplando en el mismo
sentido, con mucho menos caudal. Se invierte con **compuertas (dampers)** que
redirigen el aire del plenum hacia arriba o hacia abajo del lecho. En FluidSIM
esto se representa naturalmente con **un cilindro neumático de doble efecto
que mueve la compuerta** (vástago afuera = flujo normal, adentro = flujo
invertido), comandado desde CODESYS por `flow_dir_cmd`.

## 4. Plenum (masa térmica y pérdidas)

| Parámetro | Valor | Justificación |
|---|---|---|
| Capacidad térmica | 15 kJ/K | ~30 kg de lámina de acero (cp 0.49): estimación geométrica |
| UA | 0.003 kW/K | ~3 m² aislados × ~1 W/(m²·K) |

Sensibilidad: con C = 5, 15 o 45 kJ/K, el plenum tarda 1, 3 o 7 min en
llegar a 50 °C. Es despreciable frente a las ~33 h de secado. UA es el 2 % de
ṁ·cp.

## 5. Resultado de la propuesta supervisada (todo/nada a 50 °C, inversión cada 6 h, día nominal)

`python/control_supervisado.py`:
- t_obj = **33.2 h** (patio 130.9 h; solar activa 84.2 h).
- Energía: resistencia 136.7 kWh + ventilador 6.6 kWh = **1.79 kWh/kg c.p.s.**
- Energía térmica específica: **~6 290 kJ/kg de agua evaporada**.
- Capas al final entre 9.4 y 11.8 % b.h.; ninguna hora con el grano > 50 °C;
  sin rehumectación ni horas fuera de rango.

## Otras referencias

- Parra-Coronado, A., Roa-Mejía, G., & Oliveros-Tascón, C. E. (2008). SECAFÉ
  Parte I. *Revista Brasileira de Engenharia Agrícola e Ambiental, 12*(4),
  415–427.
- Thompson, T. L., Peart, R. M., & Foster, G. H. (1968). Mathematical
  simulation of corn drying: a new model. *Transactions of the ASAE, 11*(4),
  582–586.

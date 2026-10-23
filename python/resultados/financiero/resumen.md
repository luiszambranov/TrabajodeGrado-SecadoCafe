# Evaluación financiera preliminar

Generado por `python/analisis_financiero.py`. Pesos constantes de octubre de 2026, tasa real, horizonte de 5 años, antes de impuestos y sin financiación. Detalle con fórmulas en `flujos_financieros.xlsx`.

Costo de una hora de operario: 12,673 COP/h. Tasa real central: 12.0 %.

| Alt. | Escenario | Inversión [COP] | Lotes/año | Beneficio/lote [COP] | Egreso variable/lote [COP] | Costo fijo [COP/año] | Tasa | VPN [COP] | TIR | Recuperación simple / desc. | Beneficio/lote para VPN = 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | Conservador | 11,806,944 | 20 | 103,944 | 0 | 376,278 | 16.0 % | -6,232,110 | -10.0 % | > 5 años / > 5 años | 199,111 |
| A | Central | 11,806,944 | 40 | 152,136 | 0 | 282,208 | 12.0 % | 10,176,754 | 41.7 % | 2.0 años / 2.5 años | 81,548 |
| A | Favorable | 11,806,944 | 60 | 187,080 | 0 | 188,139 | 8.0 % | 34,820,090 | 90.9 % | 1.1 años / 1.2 años | 41,731 |
| B | Conservador | 9,475,713 | 20 | 103,944 | 0 | 283,029 | 16.0 % | -3,595,554 | -1.8 % | > 5 años / > 5 años | 158,850 |
| B | Central | 9,475,713 | 40 | 152,136 | 0 | 212,271 | 12.0 % | 12,495,563 | 56.2 % | 1.6 años / 1.9 años | 65,464 |
| B | Favorable | 9,475,713 | 60 | 187,080 | 0 | 141,514 | 8.0 % | 36,702,841 | 115.2 % | 0.9 años / 0.9 años | 33,872 |

## Flujos anuales

- A Conservador: año 0: -11,806,944; año 1: 1,702,606; año 2: 1,702,606; año 3: 1,702,606; año 4: 1,702,606; año 5: 1,702,606
- A Central: año 0: -11,806,944; año 1: 5,803,230; año 2: 5,803,230; año 3: 5,803,230; año 4: 5,803,230; año 5: 7,684,619
- A Favorable: año 0: -11,806,944; año 1: 11,036,652; año 2: 11,036,652; año 3: 11,036,652; año 4: 11,036,652; año 5: 14,799,430
- B Conservador: año 0: -9,475,713; año 1: 1,795,856; año 2: 1,795,856; año 3: 1,795,856; año 4: 1,795,856; año 5: 1,795,856
- B Central: año 0: -9,475,713; año 1: 5,873,167; año 2: 5,873,167; año 3: 5,873,167; año 4: 5,873,167; año 5: 7,288,309
- B Favorable: año 0: -9,475,713; año 1: 11,083,277; año 2: 11,083,277; año 3: 11,083,277; año 4: 11,083,277; año 5: 13,913,562

## Cambio operativo REF -> P1-C75 (mismo equipo, sin inversión)

Ahorro: 23.00 kWh/lote = 26,318 COP/lote con tarifa no residencial (21,932 con residencial), a cambio de 13.3 h más por lote.

| Lotes/año | Ahorro anual [COP] | VP 5 años a 8 % | a 12 % | a 16 % |
|---|---|---|---|---|
| 20 | 526,362 | 2,101,612 | 1,897,153 | 1,723,465 |
| 40 | 1,052,725 | 4,203,224 | 3,794,305 | 3,446,929 |
| 60 | 1,579,087 | 6,304,836 | 5,691,458 | 5,170,394 |

## Sensibilidad de un factor a la vez (alternativa A, caso central)

| Factor | Valor bajo | VPN | Valor alto | VPN |
|---|---|---|---|---|
| Lotes/año | 20 | -790,032 | 60 | 18,297,812 |
| Tasa real | 16.0 % | 8,090,288 | 8.0 % | 12,644,111 |
| Min. de supervisión por hora | 5 | 4,380,987 | 15 | 15,972,521 |
| Sobresecado evitado [pts] | 0.0 | 9,024,676 | 1.0 | 11,316,032 |
| Mantenimiento [% equipos] | 4.0 % | 9,837,703 | 2.0 % | 10,515,806 |
| Valor residual [% equipos] | 0.0 % | 9,109,473 | 40.0 % | 11,244,036 |

Ocupación del secador a 60 lotes/año: REF 1,944 h, P1-C75 2,741 h de secado.

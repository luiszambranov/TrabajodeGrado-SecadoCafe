# Evaluación financiera preliminar

Generado por `python/analisis_financiero.py`. Pesos constantes de octubre de 2026, tasa real, horizonte de 5 años, antes de impuestos y sin financiación. Detalle con fórmulas en `flujos_financieros.xlsx`.

Costo de una hora de operario: 12,673 COP/h. Tasa real central: 12.0 %.

| Alt. | Escenario | Inversión [COP] | Lotes/año | Beneficio/lote [COP] | Egreso variable/lote [COP] | Costo fijo [COP/año] | Tasa | VPN [COP] | TIR | Recuperación simple / desc. | Beneficio/lote para VPN = 0 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | Conservador | 11,806,944 | 20 | 91,271 | 0 | 376,278 | 16.0 % | -7,062,027 | -14.3 % | > 5 años / > 5 años | 199,111 |
| A | Central | 11,806,944 | 40 | 139,463 | 0 | 282,208 | 12.0 % | 8,349,646 | 36.7 % | 2.2 años / 2.8 años | 81,548 |
| A | Favorable | 11,806,944 | 60 | 174,407 | 0 | 188,139 | 8.0 % | 31,784,061 | 84.2 % | 1.1 años / 1.3 años | 41,731 |
| B | Conservador | 9,475,713 | 20 | 91,271 | 0 | 283,029 | 16.0 % | -4,425,471 | -6.5 % | > 5 años / > 5 años | 158,850 |
| B | Central | 9,475,713 | 40 | 139,463 | 0 | 212,271 | 12.0 % | 10,668,454 | 50.2 % | 1.8 años / 2.1 años | 65,464 |
| B | Favorable | 9,475,713 | 60 | 174,407 | 0 | 141,514 | 8.0 % | 33,666,812 | 106.9 % | 0.9 años / 1.0 años | 33,872 |

## Flujos anuales

- A Conservador: año 0: -11,806,944; año 1: 1,449,142; año 2: 1,449,142; año 3: 1,449,142; año 4: 1,449,142; año 5: 1,449,142
- A Central: año 0: -11,806,944; año 1: 5,296,301; año 2: 5,296,301; año 3: 5,296,301; año 4: 5,296,301; año 5: 7,177,690
- A Favorable: año 0: -11,806,944; año 1: 10,276,259; año 2: 10,276,259; año 3: 10,276,259; año 4: 10,276,259; año 5: 14,039,037
- B Conservador: año 0: -9,475,713; año 1: 1,542,391; año 2: 1,542,391; año 3: 1,542,391; año 4: 1,542,391; año 5: 1,542,391
- B Central: año 0: -9,475,713; año 1: 5,366,238; año 2: 5,366,238; año 3: 5,366,238; año 4: 5,366,238; año 5: 6,781,381
- B Favorable: año 0: -9,475,713; año 1: 10,322,884; año 2: 10,322,884; año 3: 10,322,884; año 4: 10,322,884; año 5: 13,153,169

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
| Lotes/año | 20 | -1,703,586 | 60 | 15,557,149 |
| Tasa real | 16.0 % | 6,430,455 | 8.0 % | 10,620,092 |
| Min. de supervisión por hora | 5 | 2,553,879 | 15 | 14,145,413 |
| Sobresecado evitado [pts] | 0.0 | 7,197,567 | 1.0 | 9,488,923 |
| Mantenimiento [% equipos] | 4.0 % | 8,010,594 | 2.0 % | 8,688,697 |
| Valor residual [% equipos] | 0.0 % | 7,282,364 | 40.0 % | 9,416,927 |

Ocupación del secador a 60 lotes/año: REF 1,944 h, P1-C75 2,741 h de secado.

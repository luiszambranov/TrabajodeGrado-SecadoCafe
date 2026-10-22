# R1 · Mejoría relevante con el diseño corregido (21 oct 2026)

Generado por `python/r1_analisis_pareado.py` sobre `resultados/campana/resultados.csv` (150 realizaciones pareadas, semillas 1001–1150; perfiles corregidos: P2 50 → 35 °C, P3 35 → 50 °C). Todas son del secador eléctrico simulado: no es el contraste eléctrico–solar.

Frontera de Pareto (tiempo–energía) entre las supervisadas que cumplen el filtro de calidad: **REF, P1-C75 y P3-C75**. Se analizan P1-C75 (la candidata de la guía) y P3-C75 frente a REF, y P3-C75 frente a P1-C75.

## P1-C75 frente a REF

| | REF | P1-C75 |
|---|---|---|
| Energía por lote [kWh] | 140.6 ± 4.9 | 117.6 ± 4.2 |
| Energía por kg c.p.s. [kWh/kg] | 1.757 | 1.469 |
| Tiempo hasta el criterio de fin [h] | 32.4 ± 1.1 | 45.7 ± 1.7 |

| Diferencia pareada | Media | Desv. | IC 95 % (t) | IC 95 % bootstrap por pares | p5 | p50 | p95 |
|---|---|---|---|---|---|---|---|
| Ahorro ΔE [kWh/lote] | 23.00 | 2.02 | 22.67 – 23.32 | — | 19.67 | 23.07 | 26.09 |
| Ahorro por semilla s [%] | 16.36 | 1.23 | 16.16 – 16.56 | 16.16 – 16.56 | 14.36 | 16.32 | 18.18 |
| Tiempo adicional Δt [h] | 13.29 | 0.64 | 13.18 – 13.39 | 13.19 – 13.39 | 12.33 | 13.25 | 14.37 |

- Semillas con ahorro positivo: **150 de 150**. Wilcoxon: p = 2.3e-26 (complementario; no basta el valor p).
- Porcentaje con las medias = 16.36 %; media de los porcentajes individuales s̄ = 16.36 %. Son cálculos distintos; se reporta s̄ con su IC.
- Costo temporal: +13.3 h por lote (+41 % con las medias); un lote individual ahorra entre 14.4 % y 18.2 % (p5–p95; no es el IC de la media).
- Ahorro: **21.932 COP/lote** (tarifa CHEC 953.62 COP/kWh); **1.652 COP por hora adicional** de máquina (umbral de valor de ocupación, no salario ni beneficio); en cosecha procesa 29 % menos lotes en el mismo tiempo.
- Umbral de relevancia propuesto (límite inferior del IC 95 % de s̄ ≥ 10 %): límite inferior = 16.16 % → **cumple**.

## P3-C75 frente a REF

| | REF | P3-C75 |
|---|---|---|
| Energía por lote [kWh] | 140.6 ± 4.9 | 113.9 ± 4.9 |
| Energía por kg c.p.s. [kWh/kg] | 1.757 | 1.423 |
| Tiempo hasta el criterio de fin [h] | 32.4 ± 1.1 | 55.2 ± 2.7 |

| Diferencia pareada | Media | Desv. | IC 95 % (t) | IC 95 % bootstrap por pares | p5 | p50 | p95 |
|---|---|---|---|---|---|---|---|
| Ahorro ΔE [kWh/lote] | 26.68 | 1.92 | 26.37 – 26.99 | — | 23.48 | 26.76 | 29.92 |
| Ahorro por semilla s [%] | 19.00 | 1.42 | 18.77 – 19.23 | 18.77 – 19.22 | 16.91 | 19.04 | 21.41 |
| Tiempo adicional Δt [h] | 22.78 | 1.59 | 22.52 – 23.04 | 22.53 – 23.03 | 20.42 | 22.79 | 25.48 |

- Semillas con ahorro positivo: **150 de 150**. Wilcoxon: p = 2.3e-26 (complementario; no basta el valor p).
- Porcentaje con las medias = 18.98 %; media de los porcentajes individuales s̄ = 19.00 %. Son cálculos distintos; se reporta s̄ con su IC.
- Costo temporal: +22.8 h por lote (+70 % con las medias); un lote individual ahorra entre 16.9 % y 21.4 % (p5–p95; no es el IC de la media).
- Ahorro: **25.441 COP/lote** (tarifa CHEC 953.62 COP/kWh); **1.122 COP por hora adicional** de máquina (umbral de valor de ocupación, no salario ni beneficio); en cosecha procesa 41 % menos lotes en el mismo tiempo.
- Umbral de relevancia propuesto (límite inferior del IC 95 % de s̄ ≥ 10 %): límite inferior = 18.77 % → **cumple**.

## P3-C75 frente a P1-C75

| | P1-C75 | P3-C75 |
|---|---|---|
| Energía por lote [kWh] | 117.6 ± 4.2 | 113.9 ± 4.9 |
| Energía por kg c.p.s. [kWh/kg] | 1.469 | 1.423 |
| Tiempo hasta el criterio de fin [h] | 45.7 ± 1.7 | 55.2 ± 2.7 |

| Diferencia pareada | Media | Desv. | IC 95 % (t) | IC 95 % bootstrap por pares | p5 | p50 | p95 |
|---|---|---|---|---|---|---|---|
| Ahorro ΔE [kWh/lote] | 3.68 | 1.19 | 3.49 – 3.87 | — | 2.14 | 3.55 | 5.76 |
| Ahorro por semilla s [%] | 3.15 | 1.09 | 2.98 – 3.33 | 2.98 – 3.33 | 1.76 | 3.00 | 5.11 |
| Tiempo adicional Δt [h] | 9.49 | 1.00 | 9.33 – 9.65 | 9.33 – 9.65 | 8.03 | 9.48 | 11.36 |

- Semillas con ahorro positivo: **150 de 150**. Wilcoxon: p = 2.3e-26 (complementario; no basta el valor p).
- Porcentaje con las medias = 3.13 %; media de los porcentajes individuales s̄ = 3.15 %. Son cálculos distintos; se reporta s̄ con su IC.
- Costo temporal: +9.5 h por lote (+21 % con las medias); un lote individual ahorra entre 1.8 % y 5.1 % (p5–p95; no es el IC de la media).
- Ahorro: **3.509 COP/lote** (tarifa CHEC 953.62 COP/kWh); **383 COP por hora adicional** de máquina (umbral de valor de ocupación, no salario ni beneficio); en cosecha procesa 17 % menos lotes en el mismo tiempo.
- Umbral de relevancia propuesto (límite inferior del IC 95 % de s̄ ≥ 10 %): límite inferior = 2.98 % → **no cumple**.

## Restricciones y criterio de calidad más estricto

Filtro: grano > 50 °C = 0 h, capa más húmeda ≤ 12 % b.h. y capa más seca ≥ umbral, por realización. El 9 % se fijó el 5 oct 2026 antes de la campaña (1 punto bajo el 10 % del rango de almacenamiento 10–12 %, SECAFÉ 2008), por la sobresecación inherente de la capa de entrada en un lecho estático de 20 cm. No se afirma que el café cumpla calidad integral sin ensayos físicos.

| Estrategia | Cumple (capa ≥ 8.5 %) | Cumple (capa ≥ 9 %) | Cumple (capa ≥ 9.5 %) | Cumple (capa ≥ 10 %) |
|---|---|---|---|---|
| REF | 100 % | 100 % | 13 % | 0 % |
| P1-C75 | 100 % | 100 % | 89 % | 0 % |
| P1-C100 | 100 % | 100 % | 100 % | 2 % |
| P2-C75 | 100 % | 100 % | 100 % | 6 % |
| P2-C100 | 100 % | 100 % | 100 % | 90 % |
| P3-C75 | 100 % | 100 % | 69 % | 3 % |
| P3-C100 | 100 % | 100 % | 100 % | 74 % |

Con 9,5 % y 10 % los perfiles con caudal 100 % y escalonados (P2-C100, P3-C100) son los más uniformes; los de la frontera (REF, P1-C75, P3-C75) sobresecan más la capa de entrada.

## Tabla 5 reorganizada (una fila por configuración; media ± desviación, 150 realizaciones)

| Estrategia | t fin [h] | kWh/kg c.p.s. | Grano > 50 °C [h] | Capa más seca [% b.h.] | Capa más húmeda [% b.h.] | Cumple filtro (9 %) |
|---|---|---|---|---|---|---|
| PASIVA | 258.2 ± 35.6 | 0.000 ± 0.000 | — | 10.99 ± 0.01 | 10.99 ± 0.01 | 100 % |
| ACTIVA | 136.1 ± 10.4 | 0.034 ± 0.003 | — | 10.97 ± 0.02 | 10.97 ± 0.02 | 100 % |
| REF | 32.4 ± 1.1 | 1.757 ± 0.061 | 0.0 ± 0.0 | 9.40 ± 0.09 | 11.78 ± 0.04 | 100 % |
| P1-C30 | 80.0 ± 3.7 | 1.062 ± 0.050 | 0.0 ± 0.0 | 7.75 ± 0.15 | 12.00 ± 0.00 | 0 % |
| P1-C75 | 45.7 ± 1.7 | 1.469 ± 0.053 | 0.0 ± 0.0 | 9.63 ± 0.10 | 11.79 ± 0.05 | 100 % |
| P1-C100 | 41.0 ± 1.4 | 1.814 ± 0.054 | 0.0 ± 0.0 | 9.85 ± 0.09 | 11.55 ± 0.04 | 100 % |
| P2-C30 | 98.5 ± 3.9 | 1.068 ± 0.054 | 0.0 ± 0.0 | 9.07 ± 0.19 | 12.00 ± 0.00 | 63 % |
| P2-C75 | 63.6 ± 2.4 | 1.620 ± 0.055 | 0.0 ± 0.0 | 9.90 ± 0.06 | 11.57 ± 0.04 | 100 % |
| P2-C100 | 58.8 ± 2.3 | 2.036 ± 0.070 | 0.0 ± 0.0 | 10.13 ± 0.10 | 11.41 ± 0.05 | 100 % |
| P3-C30 | 98.7 ± 5.7 | 0.986 ± 0.050 | 0.0 ± 0.0 | 7.34 ± 0.24 | 12.00 ± 0.00 | 0 % |
| P3-C75 | 55.2 ± 2.7 | 1.423 ± 0.062 | 0.0 ± 0.0 | 9.61 ± 0.22 | 11.76 ± 0.04 | 100 % |
| P3-C100 | 49.2 ± 2.3 | 1.709 ± 0.073 | 0.0 ± 0.0 | 10.15 ± 0.23 | 11.47 ± 0.06 | 100 % |

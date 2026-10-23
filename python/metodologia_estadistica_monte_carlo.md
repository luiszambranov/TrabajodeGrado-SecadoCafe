# Metodología estadística de la campaña Monte Carlo

Protocolo fijado antes del piloto. Implementado en `campana_montecarlo.py`
(corridas) y `analisis_montecarlo.py` (estadística y figuras).

## 1. Qué se compara

Doce estrategias por realización:

| Código | Estrategia |
|---|---|
| PASIVA | Secado solar pasivo (`escenario_sol_abierto.py`, calibrado con Cenicafé) |
| ACTIVA | Secado solar activo con extractor (`linea_base_activa.py`) |
| REF | Supervisada, práctica de Cenicafé: 50 °C constante, caudal 100 % (González et al., 2010) |
| P{1,2,3}-C{30,75,100} | Supervisada, diseño factorial 3 × 3: perfil térmico × caudal |

- **Perfil térmico** (consigna de T_process, manipulada 1):
  P1 = 45 °C constante; P2 = 50 °C que baja a 35 °C cuando el promedio del lote
  llega a 30 % b.h.; P3 = 35 °C que sube a 50 °C al 30 % b.h.
- **Caudal** (manipulada 2), constante en todo el secado: 30, 75 y 100 % de 8 m³/min.
- Justificación de los niveles: `perfiles_termicos.py`. Ningún nivel supera los
  50 °C permitidos para el grano.

Comparación primaria (dimensiona N): **REF frente a ACTIVA**. Secundarias, con
corrección de Holm: REF frente a PASIVA, ACTIVA frente a PASIVA y cada una de las
9 combinaciones frente a REF.

## 2. Qué es aleatorio

Una semilla por realización, guardada en el CSV.

| Variable | Distribución | Fuente |
|---|---|---|
| Clima día a día (T mín, T máx, ea) | AR(1): σ 0,97 / 1,36 °C, persistencia 0,49 / 0,39; ea residual 4 % | NASA POWER 2005–2024 sobre medias de Naranjal (`variabilidad_clima.py`) |
| Humedad inicial M0 | Uniforme 52–56 % b.h. | SECAFÉ (Parra-Coronado et al., 2008) |

Las doce estrategias reciben exactamente el mismo clima y el mismo M0 en cada
realización (diseño pareado). Los parámetros del modelo no se perturban: su
incertidumbre se cubre con la validación (`data/reference/validacion_modelo.md`)
y con la sensibilidad ±20 % (`sensibilidad_tornado.py`).

## 3. Métricas

**Métrica primaria: `t_obj` [h]**, tiempo hasta que la humedad promedio llega a
11 % b.h. y la capa más húmeda queda en ≤ 12 % b.h. (rango seguro de 10–12 % b.h.;
FNC, 2013). En las estrategias solares (capa delgada uniforme) ambas condiciones
coinciden. Horizonte máximo: 720 h; una realización que no llega se registra como
censurada.

Métricas secundarias (se reportan, no dimensionan N):

| Métrica | Unidad | Para qué |
|---|---|---|
| Energía eléctrica comprada (resistencia + ventiladores) | kWh/kg c.p.s. | Costo de operación |
| Energía total (eléctrica + solar incidente) | kJ/kg de agua evaporada | Eficiencia comparable entre estrategias |
| Horas con el grano > 50 °C | h | Calidad (González et al., 2010) |
| Capa más húmeda y más seca al final | % b.h. | Uniformidad del lote |
| Horas fuera del dominio del modelo | h | Control de extrapolación |
| IAE, ISE, sobreimpulso y error medio de T_process | °C·h, °C | Desempeño del control |

**Filtro de calidad** (fijado antes de la campaña): un perfil cumple si en al
menos el 95 % de las realizaciones tiene 0 h con el grano por encima de 50 °C,
capa más húmeda ≤ 12 % b.h. y capa más seca ≥ 9 % b.h. (sin sobresecado).

## 4. Tamaño de muestra

**Diferencia mínima relevante Δ = 12 h** en `t_obj`: una jornada de trabajo; una
diferencia menor no cambia la programación de lotes en finca.

N = max(N_potencia, N_precisión, 30), redondeado a decenas:
- **N_potencia:** comparación primaria, α = 0,05 bilateral, potencia 0,80, prueba
  pareada con d_z = Δ/σ_d (σ_d del piloto), dividido entre 0,955 (eficiencia
  relativa de Wilcoxon; Lehmann, 1975).
- **N_precisión:** semiancho del IC 95 % de la media de `t_obj` de **cada**
  estrategia ≤ Δ/2 = 6 h.
- **Mínimo de 30** por estabilidad de la dispersión y de los percentiles.

Piloto de 10 realizaciones (semillas 1–10, `resultados/piloto/calculo_N.md`):
N_potencia = 12, N_precisión = 126 → N = 130. Con 130 la estrategia PASIVA quedó
con un semiancho de 6,37 h, así que la campaña se extendió a **N = 150**
(semillas 1001–1150; semiancho 5,74 h).

## 5. Análisis estadístico

- Diferencias pareadas por semilla. Normalidad de las diferencias con Shapiro-Wilk
  (Shapiro & Wilk, 1965); prueba de Wilcoxon de rangos con signo (Wilcoxon, 1945),
  que tolera los saltos de un día de las estrategias solares; corrección de Holm
  (1979) para comparaciones múltiples.
- Frontera de Pareto tiempo–energía entre los perfiles que cumplen el filtro.
- Mejoría relevante frente a REF (`analisis_pareado.py`): media e IC 95 % de la
  diferencia pareada (t y remuestreo de pares), con un umbral de relevancia
  propuesto de 10 % de ahorro de energía.

## 6. Cómo reproducir

```
python campana_montecarlo.py --n 10 --semilla-inicial 1 --salida resultados/piloto --procesos 4
python analisis_montecarlo.py resultados/piloto --piloto
python campana_montecarlo.py --n 150 --semilla-inicial 1001 --salida resultados/campana --procesos 4
python analisis_montecarlo.py resultados/campana
python analisis_pareado.py
```

Cada realización se guarda al terminar; si se interrumpe, el mismo comando sigue
donde iba. Con 4 procesos la campaña completa (1 800 simulaciones) tarda unos
15 min.

## 7. Resultados

Medias de 150 realizaciones; detalle en `resultados/campana/resumen_resultados.md`
y `resultados/analisis_pareado/resumen.md`.

| Estrategia | Tiempo a 11 % b.h. [h] | Energía comprada [kWh/kg c.p.s.] | Filtro de calidad |
|---|---|---|---|
| PASIVA | 258,2 | 0 | Cumple |
| ACTIVA | 136,1 | 0,034 | Cumple |
| REF (50 °C, caudal 100 %) | 32,4 | 1,757 | Cumple (frontera) |
| P1-C75 (45 °C, caudal 75 %) | 45,7 | 1,469 | Cumple (frontera) |
| P3-C75 (35 → 50 °C, caudal 75 %) | 55,2 | 1,423 | Cumple (frontera) |
| P1-C100, P2-C75, P2-C100, P3-C100 | 41,0–63,6 | 1,62–2,04 | Cumplen (dominados) |
| Caudal 30 % (P1, P2, P3) | 80–99 | 0,99–1,07 | No cumplen (sobresecado de la capa de entrada) |

Ningún perfil supera 50 °C de grano. La frontera de Pareto la forman **REF** (el
más rápido), **P1-C75** (16,4 % menos energía con 13,3 h más) y **P3-C75**
(19,0 % menos energía con 22,8 h más). P3 (bajo → alto) es más rápido y gasta
menos que P2 (alto → bajo) con el mismo caudal.

## Referencias

- Cohen, J. (1988). *Statistical power analysis for the behavioral sciences* (2nd ed.). Lawrence Erlbaum Associates.
- de Oliveira, P. D., Biaggioni, M. A. M., Borém, F. M., Isquierdo, E. P., & Damasceno, M. de O. V. (2018). Quality of natural and pulped coffee as a function of temperature changes during mechanical drying. *Coffee Science, 13*(4), 415–425. https://doi.org/10.25186/cs.v13i4.1435
- Federación Nacional de Cafeteros de Colombia. (2013). *Manual del cafetero colombiano*. Cenicafé. https://doi.org/10.38141/cenbook-0026
- González S., C. A., Sanz U., J. R., & Oliveros T., C. E. (2010). Control de caudal y temperatura de aire en el secado mecánico de café. *Cenicafé, 61*(4), 281–296.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics, 6*(2), 65–70.
- Lehmann, E. L. (1975). *Nonparametrics: Statistical methods based on ranks*. Holden-Day.
- Parra-Coronado, A., Roa-Mejía, G., & Oliveros-Tascón, C. E. (2008). SECAFÉ Parte I: Modelamiento y simulación matemática en el secado mecánico de café pergamino. *Revista Brasileira de Engenharia Agrícola e Ambiental, 12*(4), 415–427.
- Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality (complete samples). *Biometrika, 52*(3–4), 591–611.
- Wilcoxon, F. (1945). Individual comparisons by ranking methods. *Biometrics Bulletin, 1*(6), 80–83.

# Metodología estadística — comparación de perfiles térmicos (campaña Monte Carlo)

**Estado: diseño definido, no ejecutado (24-25 sept 2026). Métrica primaria,
comparación primaria y Δ fijados el 29 sept 2026 (sección 6).** Esqueleto de la
planta dinámica ya existe (`dinamica_termica.py` + `cinetica_dinamica.py` +
`planta_secado.py`), pero **falta calibrar `ParametrosCamara` y
`CondicionesSecado`** antes de que un piloto real tenga sentido — ver
`python/README.md`, sección "Contenido esperado (pendiente)". Este documento
fija el protocolo para cuando esa calibración esté lista; no reemplaza la
implementación, la antecede.

## Por qué existe este documento

La revisión del asesor del 15 sept 2026
(`Informe_revision_documento_secado_cafe.pdf`, sección 5.6) marcó el tamaño de
muestra de la campaña Monte Carlo como **el mayor vacío del anteproyecto**: el
texto original decía "si se realizan repeticiones..." sin definir cuántas ni
por qué. El 24-25 sept el asesor compartió además una infografía de otro
proyecto del diplomado (comparación de hélices en un ROV) con un marco de
potencia estadística y tamaño muestral pareado, que se adapta aquí a la
comparación de perfiles térmicos.

## 1. Diseño experimental: comparación pareada, no independiente

La campaña corre las tres estrategias (secado al sol/patio, solar
activo/ventilación, propuesta supervisada) usando **las mismas realizaciones
aleatorias** de perturbaciones ambientales (T/RH ambiente vía
`generador_ambiente.py`, y posiblemente M0) para las tres. Esta decisión ya
estaba tomada informalmente (para que la comparación sea justa), pero tiene
una consecuencia estadística que antes no se había hecho explícita: al aplicar
la misma perturbación a las tres estrategias, cada realización deja de ser
una observación independiente y pasa a ser **un conjunto de observaciones
pareadas** entre estrategias. Esto importa por dos razones. Primero, reduce la
variabilidad que ve el análisis: la diferencia entre dos estrategias para la
misma realización aísla el efecto de la estrategia de control, sin mezclarlo
con el ruido de que una realización tuvo un ambiente más favorable que otra.
Segundo, obliga a que tanto el cálculo del tamaño de muestra como la prueba de
comparación final traten los datos como pares, no como dos grupos sueltos —
si se ignora esto y se analiza como si fueran independientes, se pierde
potencia estadística y, en el peor caso, la conclusión deja de ser válida.

## 2. Justificación estadística del número de corridas (potencia estadística)

La pregunta que hay que responder no es "¿cuántas simulaciones alcanzan?" en
abstracto, sino "¿cuántas realizaciones se necesitan para detectar, con
confianza razonable, una diferencia entre estrategias del tamaño que de verdad
nos importa?". Eso es exactamente lo que calcula un análisis de potencia, y
se construye en cinco pasos.

**Paso 1 — Fijar el riesgo de error que se está dispuesto a aceptar.** Toda
prueba estadística puede fallar de dos maneras: concluir que hay diferencia
entre estrategias cuando en realidad no la hay (error tipo I, su probabilidad
se llama α), o no detectar una diferencia que sí existe (error tipo II, su
probabilidad se llama β). No se eliminan los dos errores a la vez — hay que
decidir de antemano cuánto riesgo de cada uno se acepta. El estándar en
ingeniería y ciencias aplicadas es α = 0.05 (5% de riesgo de falso positivo) y
una potencia objetivo de 1-β = 0.80 (80% de probabilidad de detectar la
diferencia si realmente existe). Estos valores se fijan antes de correr nada,
no se ajustan después de ver los resultados — hacerlo al revés (cambiar α o
la potencia buscada para que los datos "den bien") invalida la prueba.

**Paso 2 — Correr un piloto pequeño para estimar cuánto varía el resultado de
forma natural.** No se puede calcular cuántas corridas hacen falta sin saber
antes cuánta dispersión hay entre realizaciones — esa dispersión es la que
compite con el efecto que se quiere detectar. Por eso se corre un piloto de
pocas realizaciones (del orden de 6 a 10, no la campaña completa) bajo las
mismas condiciones que tendrá la campaña real, y con esas corridas se calcula
la desviación estándar de las diferencias pareadas entre estrategias, σ_d,
para la métrica de interés (tiempo de secado, o consumo energético). Este
piloto cumple una función exclusivamente exploratoria: estimar σ_d, no sacar
conclusiones todavía.

**Paso 3 — Definir Δ, la diferencia mínima que de verdad importa.** Esta
decisión no es estadística, es de criterio de ingeniería del propio proyecto:
¿a partir de qué diferencia en tiempo de secado (u otra métrica) se considera
que la propuesta supervisada representa una mejora real frente a una línea
base, y no una fluctuación sin relevancia práctica? Δ debe quedar justificado
con un argumento técnico (por ejemplo, referido a costos de energía, calidad
del grano, o tiempos de proceso reportados en la literatura de referencia del
proyecto), nunca elegido de forma arbitraria ni ajustado después de ver los
datos del piloto.

**Paso 4 — Calcular el tamaño de efecto.** Se combina la dispersión estimada
en el paso 2 con la diferencia de interés definida en el paso 3:

```
d_z = Δ / σ_d
```

Este número estandariza qué tan grande es el efecto que se busca en relación
con el ruido natural del sistema. Un d_z grande significa que la diferencia
que importa se distingue con claridad de la variabilidad de fondo, y por lo
tanto hacen falta pocas realizaciones para detectarla con confianza; un d_z
pequeño significa que el efecto buscado es sutil frente al ruido, y hacen
falta muchas más realizaciones para poder afirmar algo con la potencia fijada
en el paso 1.

**Paso 5 — Calcular N, el número de realizaciones (pares) necesarias.** Con
α, la potencia objetivo y d_z ya definidos, el número de pares necesario se
obtiene de la relación estándar para una prueba pareada:

```
N ≈ ((z_(α/2) + z_(β)) / d_z)²
```

En la práctica este cálculo no se hace a mano con la aproximación normal de
arriba, sino con software (por ejemplo `statsmodels.stats.power` en Python, o
G*Power), porque el cálculo exacto usa la distribución t no central en vez de
la normal, y da un N ligeramente mayor y más conservador. El resultado de este
paso es el N que justifica, con matemáticas y no con una cifra arbitraria, el
tamaño de la campaña Monte Carlo — que es precisamente lo que el asesor marcó
como ausente en el anteproyecto.

## 3. El criterio de convergencia se mantiene, como verificación posterior

El análisis de potencia da un N calculado *antes* de correr la campaña
completa, a partir de una estimación de σ_d obtenida con pocas corridas. Como
esa estimación inicial puede ser imprecisa, conviene mantener también el
criterio de convergencia que ya se había planteado: a medida que se acumulan
realizaciones más allá del piloto, se revisa si el intervalo de confianza de
la métrica principal se estabiliza alrededor del N calculado; si no se
estabiliza, se agregan realizaciones adicionales. El análisis de potencia fija
cuántas corridas hacer falta *a priori* con una justificación formal; la
convergencia funciona como una verificación empírica de que esa estimación
fue razonable, no como un método alternativo o competidor.

## 4. Corrección de la prueba de comparación final

El anteproyecto original proponía Shapiro-Wilk (normalidad) y Levene
(homogeneidad de varianzas) para decidir entre una prueba paramétrica o
Mann-Whitney (no paramétrica) al comparar los perfiles térmicos. Mann-Whitney
está pensada para **dos muestras independientes**, y como se estableció en la
sección 1, el diseño real es pareado — usar Mann-Whitney ahí ignoraría el
apareamiento y perdería la reducción de variabilidad que ese diseño ofrece,
además de no ser la prueba estadísticamente correcta para datos pareados. El
ajuste es: se calculan las diferencias pareadas entre cada dos estrategias
para cada realización, se aplica Shapiro-Wilk a esas diferencias (no a cada
grupo de estrategia por separado) para verificar su normalidad, y según el
resultado se usa una prueba t pareada (si las diferencias son razonablemente
normales) o la prueba de rangos con signo de Wilcoxon (si no lo son, como
alternativa no paramétrica pensada específicamente para datos pareados). La
prueba de Levene deja de ser necesaria en este esquema, porque no se están
comparando varianzas entre grupos independientes, sino evaluando una única
serie de diferencias.

## 5. Qué reportar

Para cada comparación entre dos estrategias: media y desviación estándar de
la métrica por estrategia, media y desviación estándar (o intervalo de
confianza) de las diferencias pareadas, el tamaño de efecto d_z observado, el
estadístico de la prueba usada y su valor p, y el intervalo de confianza de la
diferencia — no solo el valor p aislado.

## 6. Métricas, comparaciones y Δ fijados antes del piloto (29 sept 2026)

Este bloque cumple el control de calidad del asesor "métrica primaria y
comparación primaria fijadas antes de calcular potencia" (informe de
prioridades, 25 sept 2026, sección 5). Se fija **antes** de correr el piloto y
no se cambia después de ver datos.

### 6.1 Métrica primaria

**Tiempo de secado hasta la humedad objetivo, `t_obj` [h]**: horas de proceso
desde M0 = 55 % b.h. hasta 11 % b.h. (centro del rango 10–12 % b.h. de
almacenamiento seguro; Parra-Coronado et al., 2008), calculado por
`cinetica_roa.simular` (interpolación lineal dentro del paso). En la propuesta supervisada (lecho de 20 cm por capas),
`t_obj` es el instante en que el **promedio** del lote llega a 11 % b.h. **y la
capa más húmeda** queda en ≤ 12 % b.h. (límite superior del rango seguro), para
que ninguna parte del lote quede húmeda (precisión del 29 sept 2026, antes de
cualquier corrida del piloto). En las estrategias solares (capa delgada de
2 cm, uniforme) ambas condiciones coinciden. Si una
realización no alcanza el objetivo dentro del horizonte máximo (400 h), se
registra como censurada en 400 h y se reporta aparte.

Por qué esta y no otra:
- Es la variable que Cenicafé usa para evaluar secadores (horas o días de
  secado; González et al., 2010; Parra-Coronado et al., 2008) y la que
  responde directamente a la pregunta técnica del informe del asesor
  ("¿cómo cambia el desempeño del secado entre las estrategias?").
- Todas las estrategias la tienen definida con el mismo modelo cinético.
- La energía no sirve como métrica primaria porque la comparación sería
  trivial (las estrategias solares no compran energía térmica): se reporta
  como secundaria y alimenta el objetivo 4 (viabilidad económica).

Nota: en las estrategias solares `t_obj` avanza a saltos de ~1 día (el
secado solo progresa de día). Esto produce diferencias pareadas con colas
pesadas y posibles empates; por eso la prueba por defecto es Wilcoxon de
rangos con signo (sección 4), que tolera ambos, y la t pareada solo si
Shapiro-Wilk sobre las diferencias no rechaza normalidad.

### 6.2 Comparación primaria y secundarias

- **Primaria (una sola, para el cálculo de N):** propuesta supervisada vs.
  **línea base solar activa** — la alternativa más fuerte; si la supervisada
  no se distingue de ella, compararla contra patio no aporta.
- **Secundarias:** supervisada vs. patio; solar activa vs. patio. Se
  reportan con corrección de Holm (Holm, 1979) para comparaciones
  múltiples y no se usan para dimensionar N.

### 6.3 Diferencia mínima de interés Δ

**Δ = 12 h** en `t_obj`. Justificación de ingeniería:
- 12 h equivale a una jornada diurna de trabajo/sol: una diferencia menor
  no cambia la programación de lotes en finca (el café se carga y
  descarga por jornadas).
- SECAFÉ (Parra-Coronado et al., 2008) señala riesgo alto de hongos y
  ocratoxina si el café pergamino húmedo espera más de 48 h para secarse;
  12 h es una fracción operativamente relevante de esa ventana (una
  cuarta parte).
- Es un criterio fijado antes del piloto, no derivado de sus datos.

### 6.4 Métricas secundarias (se reportan, no dimensionan N)

| Métrica | Unidad | Para qué |
|---|---|---|
| Energía eléctrica comprada (resistencia + ventilador) | kWh por kg de café pergamino seco | Objetivo 4 (costo de operación, OPEX) |
| Energía térmica específica | kJ por kg de agua evaporada | Eficiencia térmica (comparable con SECAFÉ) |
| Horas con temperatura del grano > 50 °C | h | Calidad: límite de Cenicafé (González et al., 2010) |
| Horas de rehumectación (M < Me) | h | Riesgo en estrategias solares |
| Horas fuera del rango de las fuentes | h | Control de extrapolación (sección 5 del informe del asesor) |

### 6.5 Parámetros fijos de la prueba

α = 0.05 (bilateral), potencia 1−β = 0.80, prueba pareada (Wilcoxon por
defecto). N se calcula con `statsmodels.stats.power.TTestPower` usando
d_z = Δ/σ_d con σ_d del piloto, y se aplica la corrección por eficiencia
relativa asintótica de Wilcoxon (N_W ≈ N_t / 0.955; Lehmann, 1975) si la
prueba final es Wilcoxon.

### Referencias de esta sección

- González S., C. A., Sanz U., J. R., & Oliveros T., C. E. (2010). Control de
  caudal y temperatura de aire en el secado mecánico de café. *Cenicafé,
  61*(4), 281–296. https://biblioteca.cenicafe.org/handle/10778/503
- Parra-Coronado, A., Roa-Mejía, G., & Oliveros-Tascón, C. E. (2008). SECAFÉ
  Parte I. *Revista Brasileira de Engenharia Agrícola e Ambiental, 12*(4),
  415–427.
- Holm, S. (1979). A simple sequentially rejective multiple test procedure.
  *Scandinavian Journal of Statistics, 6*(2), 65–70.
- Lehmann, E. L. (1975). *Nonparametrics: Statistical Methods Based on
  Ranks*. Holden-Day. (eficiencia relativa de Wilcoxon, 3/π ≈ 0.955)

## Referencias

- Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for
  normality (complete samples). *Biometrika*, 52(3/4), 591-611.
- Wilcoxon, F. (1945). Individual comparisons by ranking methods. *Biometrics
  Bulletin*, 1(6), 80-83. (prueba pareada no paramétrica; reemplaza a
  Mann-Whitney para este diseño)
- Cohen, J. (1988). *Statistical Power Analysis for the Behavioral Sciences*
  (2nd ed.). Lawrence Erlbaum Associates. (tamaño de efecto d_z, convención de
  α y potencia)
- Mann, H. B., & Whitney, D. R. (1947). On a test of whether one of two random
  variables is stochastically larger than the other. *Annals of Mathematical
  Statistics*, 18(1), 50-60. (referencia histórica del anteproyecto original;
  ya no aplica directamente a este diseño pareado, se mantiene la cita para
  trazabilidad de la decisión)
- Levene, H. (1960). Robust tests for equality of variances. En *Contributions
  to Probability and Statistics: Essays in Honor of Harold Hotelling*.
  Stanford University Press. (usada en el anteproyecto original; ya no
  necesaria bajo el diseño pareado, se mantiene la cita para trazabilidad)

## Pendiente

- Calibrar `ParametrosCamara`/`CondicionesSecado` (bloqueante, ver
  `python/README.md`).
- Correr el piloto de 6-10 realizaciones una vez calibrado el modelo, y
  calcular N real con `statsmodels` (o equivalente) en vez de la aproximación
  a mano de la sección 2.
- Escribir el script de la campaña Monte Carlo (`python/`, aparte, no pasa
  por CODESYS/Modbus) que genere las realizaciones, guarde las semillas, y
  corra las tres estrategias con cada una.

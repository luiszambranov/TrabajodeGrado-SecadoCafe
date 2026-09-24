# Metodología estadística — comparación de perfiles térmicos (campaña Monte Carlo)

**Estado: diseño definido, no ejecutado (24-25 sept 2026).** Esqueleto de la
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

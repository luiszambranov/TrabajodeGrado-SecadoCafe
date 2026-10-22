# Cierre de simulación para radicación: R1, R2, R3, R4 y sensibilidad

Estado al 21 oct 2026, noche. Guía de cierre del asesor (entrega jueves 22 oct, 22:00).
Todo se regenera con los scripts indicados; cada uno escribe su resumen `.md` y su figura.

**Corrección de perfiles (21 oct 2026, noche):** P2 pasa de 55 → 35 °C a **50 → 35 °C** y P3 de 35 → 55 °C a **35 → 50 °C**. El diseño inicial excedía el límite de 50 °C del grano que adopta el propio trabajo (González et al., 2010) y no correspondía a la fuente de los escalonados (de Oliveira et al., 2018, que usó 50 °C). La corrección se decidió por esa razón de seguridad, antes de ver los nuevos resultados. Después se repitieron el piloto (sigue dando N = 130) y la campaña de 150 realizaciones con las mismas semillas.
- Las estrategias que no cambian (solares, REF y los tres P1) dan lo mismo que antes (diferencia < 1e-12).
- Los resultados del diseño inicial quedan en `resultados/diseno_inicial_55/` como evidencia de por qué se descartó: 6–22 h de grano > 50 °C.

| Requisito | Estado | Evidencia |
|---|---|---|
| R4 · Física autónoma + F1–F5 | **Cumple** (falta el tag de git) | `resultados/ensayos/resumen_ensayos.md`, `figures/ensayos_fallos_F1_F2_F3.png`, `figures/ensayo_continuidad_fisica.png` |
| R2 · Actuación | **Cumple** | `resultados/r2/resumen_r2.md`, `figures/r2_trazas_actuacion.png` |
| R3 · Clima | **Cumple** | `resultados/r3/resumen_r3.md`, `figures/r3_efecto_clima.png` |
| R1 · Mejoría y variabilidad | **Cumple** (falta confirmar el umbral de relevancia con el asesor) | `resultados/r1/resumen_r1.md`, `figures/r1_diferencias_pareadas.png`, `resultados/campana/resumen_resultados.md` |
| Sensibilidad ±20 % (evaluador §3.6) | Hecho | `resultados/sensibilidad/resumen_tornado.md`, `figures/sensibilidad_tornado.png` |
| Python vs. CODESYS (guía p. 10; evaluador §3.1) | **Hecho (22 oct): 3 corridas, diferencias ≤ 0,21 % en tiempo y ≤ 0,14 % en energía** | Tabla V1; `compara_codesys_replica.py`; `resultados/verificacion/*.csv` |
| R5 · Tendencias HMI | **Resuelto con limitación declarada (22 oct):** la tendencia de CODESYS muestra una ventana móvil; el lote completo se grafica desde el CSV del servidor | `python/grafica_lote.py`, `figures/lote_codesys_*.png`, `figures/hmi_secado_terminado_REF.png` |
| R6 · Economía | Juan (lista en `Tareas_documento_Juan.pdf`) | — |

---

## Por qué estos perfiles (justificación para el documento)

La pregunta es cómo responde el secado (tiempo, energía y restricciones de calidad) a **cuándo** y **cuánto** calor se aplica:
- **REF (50 °C, 100 %):** la práctica de Cenicafé; es la línea de comparación.
- **P1 (45 °C constante):** cuánto se ahorra bajando la temperatura 5 °C de forma sostenida, y cuánto tiempo cuesta.
- **P2 (50 → 35 °C, alto al inicio y bajo al final):** aplica el calor con el grano húmedo, cuando la evaporación lo enfría, y lo baja al final para proteger el grano seco.
- **P3 (35 → 50 °C, bajo al inicio y alto al final):** presecado suave y aceleración del secado final. Junto con P2 permite ver cómo reacciona el café a temperaturas bajas al inicio y altas después, y viceversa.
  - El cambio al 30 % b.h. es el de de Oliveira et al. (2018) y coincide con la separación presecado / secado final de Cenicafé.
- **Caudal 30 / 75 / 100 %:** la potencia para calentar el aire es proporcional al caudal. Se busca si reducirlo ahorra energía sin sobresecar la capa de entrada.
- **Niveles:** 35 °C es el más bajo de la fuente; 50 °C es el máximo permitido para el grano y el nivel alto de la fuente; 45 °C es el constante intermedio. Ninguno sale del dominio medido del modelo (isoterma 5–55 °C).

## Resultados de los 10 perfiles (campaña corregida, 150 realizaciones)

| Perfil | t fin [h] | kWh/kg | Capas [% b.h.] | Resultado |
|---|---|---|---|---|
| REF | 32,4 | 1,757 | 9,4–11,8 | **Frontera de Pareto** (el más rápido) |
| P1-C75 | 45,7 | 1,469 | 9,6–11,8 | **Frontera de Pareto** (compromiso) |
| P3-C75 | 55,2 | 1,423 | 9,6–11,8 | **Frontera de Pareto** (el de menos energía que cumple) |
| P1-C100 | 41,0 | 1,814 | 9,8–11,5 | Cumple; dominado por REF |
| P3-C100 | 49,2 | 1,709 | 10,1–11,5 | Cumple; dominado por P1-C75. Capas muy uniformes |
| P2-C75 | 63,6 | 1,620 | 9,9–11,6 | Cumple; dominado (más lento y con más energía que P1-C75 y P3-C75) |
| P2-C100 | 58,8 | 2,036 | 10,1–11,4 | Cumple; el de más energía. Capas las más uniformes |
| P1-C30 / P2-C30 / P3-C30 | 80,0 / 98,5 / 98,7 | 1,06 / 1,07 / 0,99 | 7,7 / 9,1 / 7,3 (capa más seca) | No cumplen: sobresecan la capa de entrada (P2-C30 cumple en 63 % de las semillas) |

Con 50 °C, **ningún perfil supera el límite del grano** (0 h > 50 °C en todos).

**Cómo reacciona el café al orden de las temperaturas** (P3 bajo → alto frente a P2 alto → bajo, pareado por semilla):
- Con caudal 75 %, P3 termina **8,4 h antes** y gasta **12,1 % menos** que P2, en las 150 semillas. Con caudal 100 %: 9,6 h antes y 16,1 % menos.
- En el modelo, el calor rinde más **al final**. En esa etapa el secado lo controla la difusión interna del grano, que depende fuertemente de su temperatura. Al inicio, el aire sale casi saturado del lecho y el calor extra se aprovecha menos.
- P2, al dejar los 35 °C para la parte lenta del secado, alarga la cola y la energía.
- Los escalonados con caudal 100 % dejan las capas más parejas (capa más seca ≥ 10 % en 90 % de las semillas con P2-C100 y 74 % con P3-C100, frente a 0 % con REF). Es la ventaja de calidad que muestran, aunque no ganan en tiempo ni energía.
- Es un resultado del modelo; no se verificó con ensayos físicos.

---

## R1 · Mejoría relevante

**Cifras** (150 realizaciones pareadas, `r1_analisis_pareado.py`):

| Frente a REF | P1-C75 (45 °C, 75 %) | P3-C75 (35 → 50 °C, 75 %) |
|---|---|---|
| Energía [kWh/kg] | 1,469 (REF 1,757) | 1,423 |
| Ahorro por semilla s̄ (IC 95 %) | **16,4 %** (16,2–16,6) | **19,0 %** (18,8–19,2) |
| Ahorro de un lote (p5–p95) | 14,4–18,2 % | 16,9–21,4 % |
| Tiempo adicional (IC 95 %) | **+13,3 h** (13,2–13,4), +41 % | **+22,8 h** (22,5–23,0), +70 % |
| COP/lote · COP por hora adicional | 21 932 · 1 652 | 25 441 · 1 122 |
| Capacidad en cosecha | −29 % de lotes | −41 % de lotes |
| Semillas con ahorro | 150/150 | 150/150 |

- **P3-C75 frente a P1-C75:** ahorra solo **3,2 %** más (IC 95 % 3,0–3,3) a cambio de **9,5 h** más (+21 %). No supera el umbral de relevancia propuesto.
- **P1-C75 sigue siendo la mejor opción de compromiso,** como señaló la guía. P3-C75 es el extremo de mínima energía, para cuando el tiempo de máquina no importa.
- **Restricciones:** las tres cumplen el filtro de 9 % en el 100 % de las semillas.
  - Con 9,5 %: REF 13 %, P1-C75 89 %, P3-C75 69 %.
  - Con 10 %: ninguna de la frontera cumple (0–3 %); P2-C100 (90 %) y P3-C100 (74 %) sí en su mayoría.
- **Umbral de relevancia propuesto** (confirmar con el asesor): límite inferior del IC 95 % de s̄ ≥ 10 %. P1-C75 y P3-C75 lo cumplen frente a REF.

**Párrafo para el documento (Resultados, objetivo 3):**
> De los diez perfiles evaluados, siete cumplieron el filtro de calidad (grano ≤ 50 °C, capa más húmeda ≤ 12 % y capa más seca ≥ 9 % b.h.). Los tres con caudal de 30 % no lo cumplieron por sobresecar la capa de entrada. La frontera de Pareto tiempo–energía quedó formada por REF (32,4 h; 1,757 kWh/kg), P1-C75 (45,7 h; 1,469 kWh/kg) y P3-C75 (55,2 h; 1,423 kWh/kg). Frente a REF, P1-C75 redujo la energía en todas las 150 realizaciones pareadas: ahorro medio de 16,4 % (IC 95 %: 16,2–16,6 %), 23,0 kWh por lote. Ese ahorro cuesta 13,3 h más por lote (+41 %), es decir, una mejora energética con penalización de tiempo. P3-C75 llega a 19,0 % de ahorro, pero con 22,8 h adicionales (+70 %): frente a P1-C75 solo agrega 3,2 % de ahorro por 9,5 h más, por lo que P1-C75 es el mejor compromiso. Entre los escalonados, aplicar la temperatura baja al inicio y la alta al final (P3) fue más rápido y eficiente que el orden inverso (P2) en todas las realizaciones: 8,4 h menos y 12 % menos energía con caudal de 75 %. En el modelo, el calor se aprovecha mejor en la etapa final, controlada por la difusión interna del grano.

**Tabla 5 reorganizada** (una fila por configuración): `resultados/r1/resumen_r1.md`.

---

## R2 · Límites de actuación

- **Resistencia:** 3 × 2 kW **a 220 V** (cotización Tecnirecambio). Así entrega los 6 kW a la tensión de la finca, que es el supuesto declarado. Las Tempco de 240 V del dimensionamiento darían 5,04 kW a 220 V; el documento debe decirlo explícitamente (evaluador §3.5).
- **Ec. 5:** 5,53 kW a 50 °C con la densidad a 1 350 m (86,6 kPa) y 14,3 °C, o 5,43 kW con ρ = 1,03 como hace la guía. A 55 °C serían 6,30 / 6,19 kW, más que los 6 kW instalados: otra razón para no pasar de 50 °C. Hay que usar una sola convención.
- **Temperatura máxima alcanzable:** T_amb + 42,5 °C con caudal 100 %; T_amb + 56 °C con 75 %; con 30 % la limita el corte de 90 °C.
- **Barrido de los 10 perfiles corregidos** en clima nominal y frío (p5): **ninguna consigna satura**. El margen mínimo es **6,8 °C** (REF y P2-C100, madrugada fría). Ciclo de trabajo entre 13 y 73 %. Cada consigna se alcanza en 2–5 min tras el arranque o el cambio de perfil (τ ≈ 106 s).
- **Con 10 % de caída de tensión** (4,86 kW): REF en frío con inicio a las 18:00 satura **1,95 h** (déficit ≤ 1,2 °C); P1-C75 nunca.
- **Ventilador de 0,37 kW** (CBT-80N) en lugar de 0,20 kW: +3,9 % de energía en REF y +2,8 % en P1-C75. El ahorro sube a 17,6 %.
- **Helada hipotética** (−4 °C, fuera del clima del sitio): REF no alcanza 50 °C en todo el lote (saturada, déficit hasta 14,9 °C); P1-C75 sí mantiene 45 °C.
- **Compuerta:** cambia de sentido solo con posición confirmada; maniobra máxima de 5 s (FALLA 2). En Python la inversión es instantánea (simplificación declarada).

**Párrafo para el documento:**
> La respuesta simulada respeta las capacidades declaradas. La resistencia (0–6 kW, 3 × 2 kW a 220 V) solo entrega potencia con el ventilador encendido, y la energía se integra con la potencia realmente aplicada. La temperatura no salta a la consigna: con caudal nominal sube de 18 a 50 °C en unos 2,5 min (τ ≈ 106 s). Con 6 kW, la máxima temperatura alcanzable es la ambiente más 42,5 °C con caudal de 100 %. En el clima de Chinchiná, incluido un periodo frío de percentil 5, ninguno de los diez perfiles satura la resistencia; el menor margen fue de 6,8 °C. Con una caída de tensión del 10 % (4,86 kW), REF satura cerca de 2 h en madrugadas frías, mientras P1-C75 conserva su consigna. En una helada hipotética de −4 °C, ajena al sitio, 50 °C con caudal de 100 % deja de ser alcanzable. Una consigna de 55 °C requeriría 6,2–6,3 kW, más que lo instalado.

---

## R3 · Efecto del clima

**Niveles** (NASA POWER 2005–2024; anomalías mensuales; ventana de 2 días; p5/p95 sobre las medias de Naranjal):
- **CT−:** Tmín 14,95 / Tmáx 24,91 °C. **CT+:** 17,69 / 28,61 °C. En los dos se conserva la HR nocturna del 97 %.
- **CH−:** ea −8,1 %.
- **CH+:** el p95 (+7,3 %) daría HR nocturna de 104 %, imposible a la misma temperatura. Se usa el máximo físico (HR 99,5 %, +2,6 %).
- **C\*:** frío con la noche saturada. En la serie, los periodos fríos son más secos (correlación T–ea +0,50).

**Resultados** (12 corridas dirigidas):

| | Δ tiempo vs. C0 | Δ energía vs. C0 | Ciclo de trabajo REF | Ahorro P1-C75/REF |
|---|---|---|---|---|
| CT− (frío) | −2,3 % (REF) / −2,9 % (P1) | **+3,2 % / +4,4 %** | 73 % | 15,8 % |
| CT+ (calor) | +2,2 % / +2,8 % | −3,1 % / −4,0 % | 65 % | 17,5 % |
| CH− (seco) | **−2,0 % / −2,6 %** | −2,1 % / −2,5 % | 69 % | 17,1 % |
| CH+ (húmedo) | +0,7 % / +0,8 % | +0,7 % / +0,8 % | 69 % | 16,6 % |
| C\* (adverso) | −1,7 % / −2,1 % | **+3,8 % / +5,1 %** | 73 % | 15,7 % |
| Solar pasiva C\* | **+27,9 %** | — | — | — |
| Solar activa C\* | **+17,1 %** | — | — | — |

**Lectura (efectos separados):**
- La **temperatura ambiente** actúa sobre la **energía y el esfuerzo**, no sobre la temperatura de proceso. El control mantiene la consigna en todos los climas: margen mínimo de 6,8 °C en REF y sin saturación. Lo que sube es el ciclo de trabajo (69 → 73 %) y la energía (hasta +5 %).
- La **humedad absoluta** actúa sobre el **tiempo**: aire más seco seca antes (CH−: −2 %).
- En CT− el tiempo baja porque, al conservar la HR nocturna, el aire frío lleva menos agua. Es consistencia psicrométrica, no un efecto directo del frío.
- El ahorro de P1-C75 frente a REF se mantiene en todos los climas (15,7–17,5 %).

**Conclusión cuantificada** (reemplaza "deja de depender del clima"):
> Dentro del rango de percentiles 5–95 del clima de Chinchiná, el control mantiene la temperatura del aire de secado en la consigna. El clima se traslada al esfuerzo de la resistencia y al consumo (hasta +5 % de energía en un periodo frío) y, por la humedad absoluta, al tiempo (±3 %). En el caso adverso, el secado solar se alarga entre 17 y 28 %. La independencia es parcial y condicionada a que la potencia instalada cubra la consigna: fuera de ese rango (helada hipotética de −4 °C) o con caída de tensión, las consignas altas con caudal de 100 % dejan de ser alcanzables.

---

## Sensibilidad ±20 % (respuesta a la incertidumbre del tiempo absoluto)

- El tiempo de REF se mueve entre **28,6 y 37,2 h** (base 32,0 h) al variar la cinética ±20 %, y entre 30 y 35 h con el caudal ±20 %. El valor absoluto es incierto, como mostró la validación.
- El **ahorro relativo** queda entre **12,7 y 16,0 %**, y **P1-C75 gasta menos y tarda más que REF en las 180 corridas**. El orden y la frontera de Pareto REF–P1-C75 se conservan. UA del plenum y espesor del lecho casi no influyen.

> Frase para el documento: La validación muestra que el tiempo absoluto del secador mecánico es incierto. Por eso las conclusiones se apoyan en la comparación relativa entre perfiles, que comparten modelo, clima y semillas. Una sensibilidad de un factor a la vez (±20 % en la cinética, el caudal efectivo, las pérdidas del plenum y el espesor del lecho) desplazó el tiempo de REF entre 28,6 y 37,2 h, pero el ahorro de P1-C75 se mantuvo entre 12,7 y 16,0 %. En las 180 corridas P1-C75 consumió menos energía y tardó más que REF.

---

## Equivalencia Python vs. CODESYS (verificada el 22 oct 2026)

Tres corridas completas con CODESYS v8 y FluidSIM reales (`modbus_server.py --semilla N --log-csv ...`). Cada una se compara con la réplica de la campaña (`control_supervisado.simular_supervisada`) con la misma semilla, el mismo clima y la misma M0, en el instante en que se cumple el criterio de fin (promedio ≤ 11 % y capa más húmeda ≤ 12 % b.h.). Script: `compara_codesys_replica.py`. CSV: `resultados/verificacion/`.

**Tabla V1. Equivalencia entre la simulación supervisada (Python + CODESYS + FluidSIM) y la réplica de la campaña Monte Carlo**

| Corrida | Semilla / M0 | Estrategia | Tiempo de secado CODESYS / réplica [h] | Dif. | Energía CODESYS / réplica [kWh] | Dif. | Humedad final [% b.h.] | Capa más seca [% b.h.] |
|---|---|---|---|---|---|---|---|---|
| 1 | 1001 / 53,8 % | REF (50 °C, 100 %) | 32,55 / 32,48 | +0,21 % | 138,65 / 138,48 | +0,13 % | 10,97 / 10,99 | 9,29 / 9,46 |
| 2 | 1002 / 52,1 % | REF (50 °C, 100 %) | 31,35 / 31,35 | 0,00 % | 140,05 / 139,86 | +0,14 % | 11,00 / 10,99 | 9,36 / 9,46 |
| 3 | 1001 / 53,8 % | P1-C75 (45 °C, 75 %) | 46,05 / 46,02 | +0,07 % | 117,97 / 117,98 | 0,00 % | 10,99 / 11,00 | 9,69 / 9,72 |

Tolerancia declarada: ±3 % en tiempo y energía. **Las tres corridas cumplen**, con diferencias de 0,2 % o menos.

**Párrafo para el documento (objetivo 2, observación §3.1 del evaluador):**

> Para comprobar que los resultados de la campaña Monte Carlo, ejecutada con la réplica en Python del lazo supervisado, representan el comportamiento del sistema integrado, se repitieron tres lotes completos con la arquitectura Python–CODESYS–FluidSIM: dos con la estrategia REF y semillas distintas, y uno con P1-C75, que cambia tanto la consigna como el caudal. El servidor de la planta recibió la misma semilla de la campaña, de modo que el clima horario y la humedad inicial fueron idénticos, y se registró cada ciclo en un archivo CSV. En el instante en que se cumplió el criterio de fin, las diferencias frente a la réplica fueron de 0,0 a 0,21 % en el tiempo de secado y de 0,0 a 0,14 % en la energía eléctrica (Tabla V1), dentro de la tolerancia de ±3 % declarada. Las diferencias residuales provienen de la resolución temporal del servidor (0,15 h de modelo por ciclo con factor de aceleración 540) y de que en el sistema integrado la carga y la inversión de flujo tienen duración real en FluidSIM; en la capa más seca la diferencia llega a 1,8 % (0,17 puntos de humedad). Con esto, las conclusiones de la campaña son válidas para el sistema supervisado por el PLC.

Nota de procedimiento: un primer intento de la corrida 3 quedó con REF porque el selector de perfil de la HMI no estaba escribiendo en `PLC_PRG.perfil_sel`; se corrigió y se repitió. El perfil y el caudal solo se aceptan en REPOSO (`codesys/v8/README.md`, sección 3.1).

---

## R5 · Historia del lote completo (22 oct 2026)

La tendencia de la HMI (Trend Recording de CODESYS V3.5 SP9) muestra una ventana de tiempo que se desplaza, y no se logró configurarla para conservar el lote completo desde t = 0. Como el servidor de la planta registra cada ciclo en un CSV (lo que CODESYS envió y lo que la planta aplicó), la historia completa se reconstruye con `python/grafica_lote.py`, que `modbus_server.py` ejecuta solo al terminar cada lote, aunque se arranque sin opciones (CSV y figura en `python/resultados/lotes/`). Figura principal: `figures/lote_codesys_P3C100.png` (lote con P3 y caudal 100 %, sin paradas: se ve el cambio de 35 a 50 °C a las 40,2 h, cuando el promedio baja a 29,7 % b.h., y cómo la potencia de la resistencia sube con la nueva consigna). Complementarias: `figures/lote_codesys_P1C75.png` y `figures/lote_codesys_REF.png` (corridas de verificación con CODESYS y FluidSIM reales); la HMI al final del lote está en `figures/hmi_secado_terminado_REF.png`.

**Párrafo para el documento (resultados del objetivo 2):**

> La HMI de CODESYS presenta las variables en línea y sus tendencias en una ventana de tiempo móvil, adecuada para la operación pero insuficiente para revisar un lote completo, que con el factor de aceleración de 540 dura entre 4 y 7 minutos reales. Para conservar la historia del lote, el servidor de la planta registra en cada ciclo (0,15 h de modelo) las órdenes recibidas del PLC, el estado de la planta, las temperaturas, la humedad por capas, la potencia y la energía, y al terminar genera la gráfica del lote completo (Figura X). En ella se observa la respuesta del sistema durante todo el proceso: la temperatura del aire sigue la consigna enviada por CODESYS, incluido el cambio de 35 a 50 °C del perfil P3 cuando la humedad promedio cruza el 30 % b.h., sin superar el límite de 50 °C más allá de la oscilación del control (máximo 50,2 °C), la potencia de la resistencia varía con el ciclo día/noche de la temperatura ambiente, cada inversión del flujo de aire cambia la pendiente de secado de las capas extremas y el lote termina cuando la humedad promedio llega a 11 % b.h. con la capa más húmeda por debajo de 12 % b.h.

**Limitación (para la sección de limitaciones):**

> La tendencia nativa de la HMI no conserva el lote completo; la historia del lote se presenta a partir del registro del servidor de la planta y no desde el histórico del PLC. En una implementación real, este registro correspondería al histórico del sistema SCADA o a un servicio de base de datos de series de tiempo en la capa IoT.

---

## Cifras que deben coincidir en todo el documento

| Cifra | Valor |
|---|---|
| Energía REF / P1-C75 | 1,757 / 1,469 kWh/kg c.p.s. (140,6 / 117,6 kWh/lote) |
| Ahorro P1-C75 | 16,4 % (IC 95 % 16,2–16,6 %); 23,0 kWh/lote; 21 932 COP/lote |
| P3-C75 | 1,423 kWh/kg; 55,2 h; ahorro 19,0 % frente a REF; +3,2 % frente a P1-C75 con +9,5 h |
| Perfiles | P2 50 → 35 °C; P3 35 → 50 °C (corregidos); 7 de 9 cumplen el filtro; frontera REF, P1-C75, P3-C75 |
| Tiempo REF / P1-C75 | 32,4 / 45,7 h; +13,3 h (+41 %) |
| Potencia requerida (Ec. 5) | 5,43 kW (ρ = 1,03) o 5,53 kW (ρ a 86,6 kPa); a 55 °C 6,19 / 6,30 kW |
| Instalada | 6 kW (3 × 2 kW a 220 V) |
| Clima p5–p95 | tiempo ±3 %, energía hasta +5 %; ahorro 15,7–17,5 % |
| Sensibilidad ±20 % | ahorro 12,7–16,0 %; tiempo REF 28,6–37,2 h |

## Lo que queda para el jueves

**Luis (PC):**
1. ~~CODESYS: líneas de P2 y P3 y selector de perfil~~ **Hecho**; falta commit y tag.
2. ~~Corridas de equivalencia con CODESYS~~ **Hecho el 22 oct: las 3 cumplen (Tabla V1).**
3. ~~R5 en CODESYS~~ **Resuelto con `grafica_lote.py` (limitación declarada abajo).** Opcional: correr un lote con P3 (`python modbus_server.py`, sin opciones) para tener la figura con el cambio de consigna; aparece sola en `resultados/lotes/` al terminar el lote.
4. Confirmar con el asesor el umbral de relevancia (10 %) y la convención de la Ec. 5.
5. Grabar el video de la simulación con la versión final (anexo en Drive).

**Juan (documento):** pasar las cifras y párrafos de este archivo a Resultados, Resumen/Abstract y conclusiones del objetivo 3, junto con la Tabla 5 reorganizada, la Tabla V1 de equivalencia con su párrafo y las figuras `lote_codesys_P3C100.png` (con el párrafo y la limitación de R5), `r1_diferencias_pareadas.png`, `r2_trazas_actuacion.png`, `r3_efecto_clima.png`, `sensibilidad_tornado.png` y `ensayos_fallos_F1_F2_F3.png`.

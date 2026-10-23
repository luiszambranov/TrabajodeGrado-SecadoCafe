# Selección de líneas base

Este documento fija las dos líneas base contra las que se
compara la estrategia supervisada (Python + CODESYS + FluidSIM). La campaña
Monte Carlo compara las tres estrategias bajo el mismo clima y la
misma humedad inicial: sol abierto (PASIVA), solar activa (ACTIVA) y propuesta
supervisada con sus perfiles térmicos (ver
`python/metodologia_estadistica_monte_carlo.md`).

## 1. Línea base mínima: secado tradicional al sol (lazo abierto)

Sin control activo del perfil térmico. La temperatura y humedad relativa
ambiente son las entradas dominantes. Se documentarán la humedad inicial y la
exposición/ventilación. El indicador principal es el tiempo para alcanzar el
rango objetivo de humedad. La dependencia del clima se reportará
explícitamente; el modelo no se presentará como una finca específica si no hay
medición real.

## 2. Línea base activa: secado solar activo con ventilación forzada

### Selección

Se elige el **secado solar activo con ventilación forzada** (invernadero/túnel
solar con ventilador) como alternativa activa, sobre las otras tres opciones
consideradas (convectivo con aire caliente, mecánico/híbrido, asistido por
bomba de calor).

### Justificación frente a los criterios de diseño

| Criterio | Por qué cumple |
|---|---|
| Ajuste | Existen datos publicados de incremento de temperatura sobre ambiente y reducción de tiempo de secado que permiten validar el modelo contra literatura. |
| Parsimonia | Se modela con un balance de energía concentrado (lumped) de la cámara más la cinética de capa delgada; no requiere modelar combustión, ciclo de refrigeración ni CFD. |
| Ambiente | La fuente de calor es la radiación solar, ya presente en el modelo de perturbaciones ambientales del proyecto (T y HR ambiente). |
| Control | Usa una lógica de activación simple (ventilador todo/nada por temperatura u horario), lo que la distingue claramente de la propuesta supervisada (máquina de estados, HMI, alarmas). |
| Energía | Permite estimar el consumo del ventilador y compararlo con el de la propuesta. |
| Trazabilidad | Los parámetros provienen de fuentes citadas (ver sección 4). |

Se descartaron:
- **Secador mecánico/híbrido**: requiere modelar una segunda fuente de energía (biomasa o resistencia eléctrica), lo que añade parámetros sin aportar proporcionalmente al análisis.
- **Sistema asistido por bomba de calor**: literatura específica para café escasa; alto riesgo de abrir un subproyecto de modelado nuevo.
- **Convectivo con aire caliente**: viable, pero depende de una fuente térmica externa (no solar), lo que lo aleja del enfoque de sostenibilidad del proyecto.

### Rangos de referencia usados para calibrar

| Variable | Rango de referencia | Fuente |
|---|---|---|
| Incremento de temperatura de cámara sobre ambiente (invernadero, convección forzada) | 1-4.5 °C | Meja et al. (2025) |
| Incremento de temperatura interna en secadores solares activos en general | 10-25 °C | Duque-Dussán et al. (2026) |
| Reducción de tiempo de secado vs. patio/túnel pasivo | 30-50 % | Duque-Dussán et al. (2026) |
| Reducción de tiempo de secado, invernadero activo con ventilación forzada (café) | 40-50 % | Meja et al. (2025) |
| Modelo de capa delgada (todas las estrategias) | Roa–Cenicafé (antes: Midilli modificado) | Trejos et al. (1989); Parra-Coronado et al. (2008) |

Nota: los dos rangos de incremento de temperatura difieren porque corresponden
a diseños distintos (invernadero de baja ganancia vs. secador solar activo en
general). La estrategia propuesta fijará un valor de diseño propio dentro de
un rango razonable, no copiará un único número de la literatura.

### Diferencia con la propuesta supervisada

| | Línea base activa | Propuesta supervisada |
|---|---|---|
| Fuente de calor | Solar | Resistencia eléctrica (ver `python/dinamica_termica.py`) |
| Movimiento de aire | Extractor todo/nada por horario (06:00–18:00) | Ventilador de caudal variable (30–100 %) e inversión del aire cada 6 h con compuerta neumática (FluidSIM) |
| Control | Ninguno (horario fijo) | Termostato del ducto + supervisión en CODESYS: perfiles térmicos, parada por humedad, alarmas, watchdog y enclavamiento resistencia–ventilador |
| Supervisión | No | HMI con tendencias, alarmas y estado |
| Registro de datos | No necesariamente | Sí, integrado (Python) |

### Modelo cinético común

Las tres estrategias (sol/patio, solar activa y propuesta supervisada) usan
el **mismo** modelo cinético de Roa–Cenicafé (`python/cinetica_roa.py`;
fuentes en `data/reference/roa_cenicafe_isoterma_capa_delgada.md`); solo
cambian las condiciones de aire que recibe el café. El incremento solar de
cada línea base se calibró contra literatura (datos de Cenicafé): solar pasiva 4.4 °C, para reproducir los 10.6 días de
secado solar de Cenicafé con 1 400–1 800 h/año de brillo solar
(Guerrero-Aguirre et al., 2025); solar activa 12.5 °C (reducción de 47.5 %
frente a la pasiva, dentro del 30–50 % de Duque-Dussán et al., 2026 y del
40–50 % de Meja et al., 2025; incremento dentro de 10–25 °C). Fuentes y
detalle en `data/reference/chinchina_clima_fuentes.md`. Ver los
docstrings de `escenario_sol_abierto.py` y `linea_base_activa.py`.

### Configuración física común

| | Patio | Solar activa | Supervisada (eléctrica) |
|---|---|---|---|
| Lote | 80 kg c.p.s. | 80 kg c.p.s. | 80 kg c.p.s. |
| Disposición del café | Capa delgada 2 cm, 11.1 m² (7.2 kg c.p.s./m², Cenicafé 2025) | Capa delgada 2 cm, 11.1 m² | Lecho de 20 cm, 1.28 m², aire forzado a través del lecho |
| Modelo | Capa delgada de Roa | Capa delgada de Roa | Lecho de Thompson (8 capas) + Roa, inversión del aire cada 6 h |
| Fuente de calor | Sol sobre el grano (ΔT efectivo 4.4 °C) | Sol en cámara (ΔT efectivo 12.5 °C) | Resistencia de 6 kW, 50 °C |

La capa de 2 cm es la capacidad estándar de los secadores solares de Cenicafé
(Guerrero-Aguirre et al., 2025). El lecho de 20 cm es el menor espesor evaluado
por González et al. (2010) para secado mecánico estático.

## 3. Modelo, no CFD

Los estudios que modelan este tipo de secador con dinámica de fluidos
computacional (CFD) resuelven las ecuaciones de Navier-Stokes completas, un
nivel de detalle que excede el alcance de este trabajo. Se usará un modelo
concentrado: balance de energía de la cámara + cinética de capa delgada,
consistente con la recomendación de mantener un modelo de complejidad acotada.

## 4. Fuentes

1. Duque-Dussán, E., Figueroa-Varela, P. A., Cruz-Ospina, V., & Banout, J. (2026). Advances in coffee drying: A comprehensive review of traditional, solar, mechanical, hybrid, and emerging methods. *Foods, 15*(10), 1737. https://doi.org/10.3390/foods15101737
2. Meja et al. (2025). Investigating the performance and optimization of solar coffee drying technologies-A systematic review. *Journal of Food Processing and Preservation.* https://onlinelibrary.wiley.com/doi/10.1155/jfpp/7907660
3. Phitakwinai, S., Thepa, S., & Nilnont, W. (2019). Thin-layer drying of parchment Arabica coffee by controlling temperature and relative humidity. *Food Science & Nutrition, 7*(9), 2921-2931. https://doi.org/10.1002/fsn3.1144
4. Design and evaluation of a hybrid solar dryer for postharvesting processing of parchment coffee. *ScienceDirect.* https://www.sciencedirect.com/science/article/abs/pii/S0960148123008674
5. Solar drying technology for agricultural products: A review. https://arccjournals.com/journal/agricultural-reviews/R-2457
6. Mathematical modeling of greenhouse solar dryers with natural and forced convection for agricultural products: state of the art. https://www.scielo.org.mx/scielo.php?script=sci_arttext&pid=S2007-40262017000100019
7. Design and optimization of an active and passive mode indirect solar dryer to improve energy efficiency and sustainability. *International Journal of Low-Carbon Technologies.* https://academic.oup.com/ijlct/article/doi/10.1093/ijlct/ctag056/8703217
8. Guerrero-Aguirre, A., Sanz-Uribe, J. R., Peñuela-Martínez, A. E., & Osorio-G., C. V. (2025). Manejo del café en el secado solar. *Avances Técnicos Cenicafé*. https://publicaciones.cenicafe.org/index.php/avances_tecnicos/article/view/4247
9. González S., C. A., Sanz U., J. R., & Oliveros T., C. E. (2010). Control de caudal y temperatura de aire en el secado mecánico de café. *Cenicafé, 61*(4), 281–296. https://biblioteca.cenicafe.org/handle/10778/503

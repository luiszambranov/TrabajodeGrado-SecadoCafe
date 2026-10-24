# python — Planta simulada, campaña Monte Carlo y análisis

Aquí está todo lo que corre en Python: el modelo físico del secado, el servidor
Modbus que hace de planta para CODESYS, la campaña Monte Carlo que compara las
estrategias y los scripts que generan las tablas y figuras del documento.

Todos los comandos se ejecutan **desde esta carpeta** (`cd python`).

## Instalación

```
pip install -r requirements.txt
```

`requirements.txt`: `pymodbus==3.6.9`, `numpy`, `scipy`, `pandas`, `matplotlib`.
`pymodbus` va fijado en 3.6.9 porque desde la 3.7 cambió de lugar `ModbusSlaveContext`
y el servidor deja de arrancar.

## Cómo encajan los módulos

```
generador_ambiente (clima de Chinchiná)
   ├─> escenario_sol_abierto ........ estrategia PASIVA ─┐
   ├─> linea_base_activa ............ estrategia ACTIVA ─┤   las tres usan cinetica_roa
   └─> secador_electrico ............ estrategia SUPERVISADA
          ├─ dinamica_termica  (aire de la cámara)       │
          └─ lecho_secado      (8 capas de grano)        │
                                                         ▼
control_supervisado (réplica del PLC) + perfiles_termicos ─> campana_montecarlo ─> analisis_montecarlo
planta_secado (misma física) ─> modbus_server ⇄ CODESYS
```

`secador_electrico.py` es el núcleo común: lo usan el servidor (para CODESYS) y la
réplica del PLC (para Monte Carlo), así que los dos ven exactamente la misma planta.

## 1. Modelo físico

| Archivo | Qué hace |
|---|---|
| `cinetica_roa.py` | Velocidad de secado de un grano. Isoterma de equilibrio de Roa para café pergamino (Trejos et al., 1989) y ecuación de capa delgada de SECAFÉ (Parra-Coronado et al., 2008). Humedad inicial 55 % b.h. y objetivo 11 % b.h.; permite rehumectación cuando el aire está más húmedo que el grano y cuenta las horas fuera del rango validado. Fuentes: `../data/reference/roa_cenicafe_isoterma_capa_delgada.md`. |
| `dinamica_termica.py` | Parámetros del secador (`ParametrosSecador`: 80 kg c.p.s., 0,1 m³/min por kg, lecho de 20 cm, resistencia de 6 kW, ventilador de 0,20 kW, caudal 30–100 %) y temperatura del aire en la cámara (plenum) con constante de tiempo de ~2 min. Incluye el enclavamiento resistencia–ventilador, el corte térmico de 90 °C y el tiro natural con el ventilador apagado. Dimensionamiento: `../data/reference/secador_electrico_dimensionamiento.md`. |
| `lecho_secado.py` | Lecho de 8 capas de 2,5 cm (modelo de Thompson, como SECAFÉ): en cada capa aplica la cinética de Roa y hace el balance de humedad y calor del aire que la atraviesa. `paso_reposo` simula el enfriamiento y el secado residual con el ventilador apagado. |
| `secador_electrico.py` | Secador completo: cámara + lecho + contadores de energía, agua evaporada y horas con el grano sobre 50 °C. Lleva por separado el reloj de la planta y el del lote. |

## 2. Clima

| Archivo | Qué hace |
|---|---|
| `generador_ambiente.py` | Temperatura y humedad del aire de Chinchiná (estación Naranjal, Cenicafé): ciclo diario asimétrico con mínima a las 05:30 y máxima a las 15:30, y días perturbados con un modelo AR(1). Fuentes: `../data/reference/chinchina_clima_fuentes.md`. |
| `variabilidad_clima.py` | Calcula la desviación y la persistencia día a día de T mín, T máx y presión de vapor con la serie NASA POWER 2005–2024. Uso: `python variabilidad_clima.py ../data/clima/POWER_Naranjal_diario_2005_2024.csv`. |
| `niveles_clima.py` | Niveles de clima seco, húmedo, frío y caliente (percentiles 5 y 95 de NASA POWER, con consistencia psicrométrica) y un caso hipotético de helada. Lo usan `efecto_clima.py` y `limites_actuacion.py`. |

## 3. Estrategias de secado

| Archivo | Qué hace | Comando |
|---|---|---|
| `escenario_sol_abierto.py` | **PASIVA**: secado al sol en patio, capa de 2 cm, con un incremento solar de 4,4 °C calibrado para dar los 10,6 días de Cenicafé (Peñuela-Martínez et al., 2025). | `python escenario_sol_abierto.py` (imprime la calibración) |
| `linea_base_activa.py` | **ACTIVA**: secador solar con ventilación forzada, incremento de 12,5 °C (47,5 % menos tiempo que la pasiva, dentro del 30–50 % de Duque-Dussán et al., 2026). | `python linea_base_activa.py` |
| `control_supervisado.py` | **SUPERVISADA**: réplica en Python de la lógica de `PLC_PRG` y `SECUENCIA` (termostato todo/nada cada 1 s, inversión del aire cada 6 h, fin con promedio ≤ 11 % y capa más húmeda ≤ 12 % b.h.). Calcula también IAE, ISE, sobreimpulso y error de temperatura. | Se usa desde otros scripts |
| `perfiles_termicos.py` | Define los 10 perfiles supervisados (REF y P1/P2/P3 × caudal 30/75/100 %) con la fuente de cada nivel. | `python perfiles_termicos.py` (tabla con el día nominal) |

## 4. Planta para CODESYS

| Archivo | Qué hace |
|---|---|
| `modbus_server.py` | Servidor Modbus TCP (Python es el esclavo, CODESYS el maestro). Publica 41 registros (0–40), vigila que CODESYS siga escribiendo (watchdog) y publica un `heartbeat` para que CODESYS vigile a Python. Arranca en HOLD; la física avanza siempre. Guarda un CSV con una fila por ciclo y, al terminar cada lote, la gráfica del lote completo. |
| `planta_secado.py` | Pone la física de `secador_electrico.py` detrás de la interfaz que usa el servidor. Con la simulación acelerada cierra el termostato del ducto en Python (con la consigna que manda el PLC en el registro 26 y solo si el PLC da permiso con `heater_cmd`). También lleva los relojes, el estado de la planta y la política local ante pérdida de comunicación (resistencia en 0 y post-ventilación). |
| `grafica_lote.py` | Gráfica de un lote completo a partir del CSV del servidor: temperatura, consigna y ambiente; humedad promedio y por capas con las inversiones y el fin; potencia y caudal; estado de la planta sombreado. El servidor la llama solo; a mano: `python grafica_lote.py <archivo.csv>` (`--todo` para todo el archivo, `--salida` para elegir el PNG). |

### Opciones de `modbus_server.py`

```
python modbus_server.py                       # lo normal: modelo, factor 540, puerto 5020
python modbus_server.py --hora-inicio 8       # la planta arranca a las 08:00 (clima de día)
python modbus_server.py --semilla 1001        # clima y humedad inicial de la realización 1001 (verificación)
python modbus_server.py --log-csv ruta.csv    # elegir dónde se guarda el registro
python modbus_server.py --plant toy           # planta mínima, solo para probar la comunicación
```

| Opción | Valor por defecto | Qué cambia |
|---|---|---|
| `--port`, `--host` | 5020, 127.0.0.1 | Dónde escucha el servidor. |
| `--factor-aceleracion` | 540 | Segundos de modelo por segundo real (540 = 9 min de modelo por segundo; 1 = tiempo real). |
| `--lazo-termico` | `auto` | `local`: el termostato corre en Python. `plc`: lo cierra CODESYS (solo a tiempo real). `auto` elige según el factor. |
| `--hora-inicio` | 0 | Hora del día con la que arranca el clima. |
| `--semilla` | — | Usa el clima y la humedad inicial de esa realización de Monte Carlo. |
| `--post-ventilacion-min` | 10 | Minutos de modelo de ventilación tras perder la comunicación. |
| `--watchdog-timeout` | 5 s | Tiempo sin escrituras de CODESYS antes de aplicar la política local. |
| `--log-csv` | `resultados/lotes/servidor_<fecha>_<hora>.csv` | Archivo de registro. |
| `--sin-log`, `--sin-grafica` | — | No guardar CSV / no generar la gráfica del lote. |

Para cerrar el servidor: `Ctrl+C`.

## 5. Campaña Monte Carlo

| Archivo | Qué hace | Salida |
|---|---|---|
| `campana_montecarlo.py` | Corre las 12 estrategias (PASIVA, ACTIVA y los 10 perfiles supervisados) con el mismo clima y la misma humedad inicial en cada realización (diseño pareado). Guarda cada realización al terminar: si se interrumpe, el mismo comando sigue donde iba. | `resultados/<carpeta>/resultados.csv`, `metadatos.json` |
| `analisis_montecarlo.py` | Con `--piloto` calcula el tamaño de muestra N. Sin él: estadística descriptiva, pruebas de Wilcoxon con corrección de Holm, filtro de calidad, frontera de Pareto, convergencia y figuras. | `calculo_N.md` o `resumen_resultados.md` + figuras |
| `metodologia_estadistica_monte_carlo.md` | Protocolo estadístico completo y tabla de resultados. | — |

```
python campana_montecarlo.py --n 10  --semilla-inicial 1    --salida resultados/piloto  --procesos 4
python analisis_montecarlo.py resultados/piloto --piloto
python campana_montecarlo.py --n 150 --semilla-inicial 1001 --salida resultados/campana --procesos 4
python analisis_montecarlo.py resultados/campana
```

`--procesos` es el número de núcleos que se usan en paralelo. Con 4, la campaña de
150 realizaciones (1 800 simulaciones) tarda unos 15 minutos.

## 6. Análisis complementarios

Cada uno se corre sin argumentos y escribe su resumen en Markdown, su CSV y su
figura en `../figures/`.

| Archivo | Qué responde | Salida |
|---|---|---|
| `analisis_pareado.py` | ¿P1-C75 y P3-C75 mejoran a REF de forma relevante? Diferencias por semilla con IC 95 % (t y remuestreo), percentiles y un criterio de calidad más estricto. | `resultados/analisis_pareado/` |
| `limites_actuacion.py` | ¿Hasta dónde llega el calentador? Saturación de la resistencia, consignas no alcanzables, caída de tensión y ventilador degradado. | `resultados/limites_actuacion/` |
| `efecto_clima.py` | ¿Cambia el orden de las estrategias con clima seco, húmedo, frío o caliente? 12 corridas dirigidas para REF, P1-C75 y las solares. | `resultados/efecto_clima/` |
| `sensibilidad_tornado.py` | ¿Qué parámetro del modelo pesa más? ±20 % de la cinética, el caudal, las pérdidas de calor y el espesor del lecho, uno a la vez. | `resultados/sensibilidad/` |
| `corrida_instrumentada.py` | La corrida supervisada registrada minuto a minuto (consigna, temperatura lograda, potencia, ciclo de trabajo, saturación). La usa `limites_actuacion.py`. | — |
| `balance_energia.py` | Energía eléctrica, solar y por kg de agua de las tres estrategias en el día nominal. | Imprime la tabla |
| `analisis_financiero.py` | Evaluación financiera preliminar: VPN, TIR y recuperación (simple y descontada) de la adaptación (A) y del sistema completo (B) en escenarios conservador, central y favorable; valor presente del cambio REF → P1-C75; sensibilidad de un factor a la vez y costo académico de la asesoría. Cada dato está marcado como dato (con fuente) o supuesto. | `resultados/financiero/flujos_financieros.xlsx` (con fórmulas VNA y TIR) y `resumen.md` |
| `validacion_modelo.py` | Compara el modelo con 3 casos independientes: laboratorio (Phitakwinai et al., 2019), secador Escafé (Martínez-Tovar y Álvarez, 2006) y secado solar (Peñuela-Martínez et al., 2025). Imprime también por qué se excluyó el patio de Resende et al. (2009): su humedad final está bajo el equilibrio del modelo. | Imprime la tabla; detalle en `../data/reference/validacion_modelo.md` |
| `graficas_perfiles.py` | Figuras de cada perfil térmico en el día nominal, con el instante de cambio de consigna. | `../figures/perfil_*.png`, `perfiles_resumen.png` |

## 7. Pruebas con CODESYS y FluidSIM

| Archivo | Qué hace | Comando |
|---|---|---|
| `compara_codesys_replica.py` | Verifica que CODESYS y la réplica dan el mismo resultado con la misma semilla (tolerancia ±3 % en tiempo y energía). | `python modbus_server.py --semilla 1001 --log-csv resultados/verificacion/V1001_REF.csv`, correr el lote en CODESYS y luego `python compara_codesys_replica.py resultados/verificacion/V1001_REF.csv --semilla 1001 --perfil REF` |
| `graficas_ensayos.py` | Tabla y figura de los ensayos de falla F1–F5 a partir de sus CSV. | `python graficas_ensayos.py` → `resultados/ensayos/resumen_ensayos.md`, `../figures/ensayos_fallos_F1_F2_F3.png` |
| `ensayo_continuidad_fisica.py` | Ensayo sin CODESYS: paro, enfriamiento, pérdida de comunicación y recuperación con la cámara caliente. | `python ensayo_continuidad_fisica.py` → `resultados/ensayos/continuidad_fisica.csv`, `../figures/ensayo_continuidad_fisica.png` |

Valores de `--perfil`: `REF`, `P1-C30`, `P1-C75`, `P1-C100`, `P2-…`, `P3-…`.

## 8. Resultados (`resultados/`)

| Carpeta | Contenido |
|---|---|
| `piloto/` | Piloto de 10 realizaciones (semillas 1–10) y `calculo_N.md` con el tamaño de muestra. |
| `campana/` | Campaña final de 150 realizaciones (semillas 1001–1150): `resultados.csv` (una fila por estrategia y realización), `metadatos.json`, `resumen_resultados.md` y figuras de convergencia, cajas y Pareto. |
| `analisis_pareado/` | Diferencias pareadas frente a REF (`resumen.md`, `diferencias_pareadas.csv`). |
| `limites_actuacion/` | Casos de límites de actuación (`resumen.md`, `casos.csv`). |
| `efecto_clima/` | Corridas con los niveles de clima (`resumen.md`, `corridas.csv`). |
| `sensibilidad/` | Sensibilidad ±20 % (`resumen_tornado.md`, `tornado.csv`). |
| `financiero/` | Flujos de caja, VPN, TIR y recuperación por escenario (`flujos_financieros.xlsx`, `resumen.md`). |
| `ensayos/` | CSV de los ensayos de falla con CODESYS y FluidSIM (`F1_codesys`, `F2_fluidsim`, `F3_Stop`, `F5_python`), captura de la HMI en F5, ensayo de continuidad y `resumen_ensayos.md`. |
| `verificacion/` | Tres lotes completos supervisados por CODESYS (semillas 1001 y 1002, perfiles REF y P1-C75) con su gráfica, para comparar con la réplica. |
| `lotes/` | Lote completo P3-C100 supervisado por CODESYS (CSV y gráfica). Aquí guarda el servidor cada nueva corrida. |

## Limitaciones del modelo

- El vapor que libera el café no se suma a la humedad del aire a la entrada del lecho
  (sí dentro del lecho, por el modelo de Thompson).
- Los incrementos solares de las líneas base son parámetros efectivos que ya incluyen
  días nublados; la radiación del balance es la media anual.
- La validación tiene sesgos conocidos según el tipo de secado
  (`../data/reference/validacion_modelo.md`); no cambian el orden de las estrategias.
- Con el ventilador apagado el tiro natural y las pérdidas del lecho son supuestos
  declarados con su sensibilidad (`../data/reference/reposo_tiro_natural.md`).

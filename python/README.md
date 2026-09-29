# /python

Modelo de la planta (Python) y procesamiento de resultados.

## Archivos

- `modelo_secado.py` — **v0.1** del modelo de cinética de secado en capa
  delgada. Implementa Newton, Logarítmico y Midilli modificado (los
  candidatos seleccionados en `docs/matriz_comparativa_modelos.md`), con
  unidades y procedencia de cada parámetro documentadas en los docstrings.
  Los parámetros por defecto son preliminares (no ajustados); ver la
  sección "Alcance de esta versión" al inicio del archivo. Se eligieron
  deliberadamente distintos del caso trivial en que Logarítmico y
  Midilli modificado se reducen matemáticamente a Newton (a=1,c=0 y
  n=1,b=0 respectivamente), para que las tres curvas sean visualmente
  distinguibles mientras se hace el ajuste real.
- `CurvaSecado.ipynb` — notebook que usa `modelo_secado.py` para generar y
  comparar las curvas de secado de los tres modelos.
- `ajuste_modelos.py` — ajuste no lineal (RMSE, MAE, R²) de los tres
  modelos candidatos contra una curva de referencia. La curva de
  referencia se genera con la ecuación Modified-Midilli ya publicada y
  validada por Phitakwinai et al. (2019) para T=60°C/RH=20%
  (r²=0.9997), digitalizada en `data/reference/`. Ver el docstring del
  módulo para la justificación de por qué se usa la ecuación publicada
  en vez de digitalizar manualmente su figura.
- `AjusteModelos.ipynb` — notebook que corre el ajuste, tabula
  R²/RMSE/MAE de los tres modelos, comprueba que Midilli modificado
  recupera los parámetros publicados, y grafica la comparación.
- `generador_ambiente.py` — generador de temperatura y humedad relativa
  ambiente (nominal y perturbado), con la Estación Naranjal (Cenicafé,
  Chinchiná, Caldas) como zona climática de referencia. HR derivada de T
  con un enfoque psicrométrico simple (presión de vapor aprox. constante
  en el día). Ver docstring para las simplificaciones de este v0.1.
- `GeneradorAmbiente.ipynb` — notebook que genera y grafica el ciclo
  diurno nominal y varios días perturbados de T/HR.
- `linea_base_activa.py` — modelo de la línea base activa (secado solar
  + ventilación forzada): modelo Logarítmico con los parámetros ya
  ajustados y publicados por Mackpayen et al. (2017) para un secador
  solar de convección forzada real (secador Icaro mejorado). Ver
  `data/reference/mackpayen_2017_icaro_dryer.md` para la fuente y la
  verificación de los parámetros (unidad de tiempo del paper: minutos,
  convertida a horas en el código).
- `LineaBaseActiva.ipynb` — notebook que grafica la curva de la línea
  base activa y una comparación preliminar contra Midilli modificado.
- `escenario_sol_abierto.py` — línea base mínima (secado al sol en
  patio, lazo abierto): modelo Newton calibrado con las condiciones
  generales (T, HR, tiempo total, humedad inicial/final) de un estudio
  real de secado de café en patio. Ver
  `data/reference/eliseu_2008_secado_patio.md` para la fuente y la
  limitación explícita (calibración de 2 puntos, no un reajuste
  completo — no se pudo verificar la tabla de parámetros originales del
  modelo Page).
- `EscenarioSolAbierto.ipynb` — notebook que grafica la línea base
  mínima y compara las tres estrategias (mínima, activa, propuesta
  supervisada) en la misma ventana de tiempo.
- `estimacion_energia.py` — primera estimación de energía: calor
  latente MÍNIMO (piso termodinámico) para evaporar el agua removida en
  cada una de las tres estrategias. No es el consumo real (falta
  electricidad de ventiladores, pérdidas térmicas, efecto de sorción);
  ver el docstring del módulo para el detalle completo de supuestos.
- `EstimacionEnergia.ipynb` — notebook que tabula la energía para lotes
  de 1000 y 2500 kg de café húmedo inicial.

- `modbus_server.py` — **v1** de la comunicación Python-CODESYS. Servidor
  Modbus TCP (esclavo) con interfaz de planta modular (`Plant`) y 8
  variables: `T_process`, `heater_cmd`, `fan_cmd`, `RH_ambient`,
  `plant_mode`, `safety_ok` (con watchdog de pérdida de comunicación) y,
  desde la incorporación del modelo real (ver abajo), `M_coffee`
  (registros 8-9, float32) y `tiempo_proceso_h` (registros 10-11,
  float32 -- horas de MODELO transcurridas, para mostrar "tiempo de
  secado" en el HMI en vez de fecha/hora del sistema; NO son segundos
  de reloj real, ver `factor_aceleracion` en `planta_secado.py`).
  Desde el 24 sept 2026, además `heartbeat` (registro 12, WORD 0-65535):
  contador que el servidor incrementa en CADA ciclo, publicado siempre
  (incluso con comm_lost=True) -- es la señal para que CODESYS detecte
  que el servidor Python se cayó (watchdog en el sentido contrario al
  de `safety_ok`, que solo cubre pérdida de escritura de CODESYS hacia
  Python). Ver docstring del módulo, sección "Señal de latido", y
  `codesys/comunicacion_modbus.md` para la lógica ST del lado CODESYS.
  Selecciona la planta con `--plant toy`
  (planta de juguete, default) o `--plant modelo`
  (`ModeloSecadoPlant`, ver `planta_secado.py`). Ver
  `codesys/comunicacion_modbus.md` para el lado CODESYS (cliente/master)
  y el procedimiento de prueba completo.
- `dinamica_termica.py` — **v1 (29 sept 2026)**: secador eléctrico de la
  propuesta supervisada. `ParametrosSecador`: lote de 80 kg c.p.s., caudal
  0.1 m³/min/kg, lecho de 20 cm, resistencia de 6 kW (3 × 2 kW), ventilador
  de 0.20 kW, setpoint de 50 °C (González et al., 2010, Cenicafé). Plenum
  con integración exacta y enclavamiento de flujo (resistencia solo con
  ventilador). Dimensionamiento y fuentes en
  `data/reference/secador_electrico_dimensionamiento.md`.
- `lecho_secado.py` — lecho estático por capas de 2.5 cm (modelo de
  Thompson, como SECAFÉ) con la cinética de Roa en cada capa. Hace el
  balance de humedad y de calor latente del aire, necesario porque con
  0.1 m³/min/kg el aire se satura dentro del lecho (sin él, el secado
  temprano salía ~2× más rápido).
- `secador_electrico.py` — núcleo físico sin Modbus (plenum + lecho +
  contadores de energía, agua evaporada, horas con grano > 50 °C,
  rehumectación y horas fuera de rango). Lo comparten `planta_secado.py`
  y `control_supervisado.py`.
- `control_supervisado.py` — réplica en Python de la lógica de `PLC_PRG`
  (ventilador encendido, todo/nada a 50 °C con ciclo de 1 s, inversión
  del sentido del aire cada 6 h, parada con promedio ≤ 11 % y capa más
  húmeda ≤ 12 % b.h.) para la campaña Monte Carlo (reproducible por
  semilla, sin tiempo real). Día nominal: 33.2 h, 1.79 kWh/kg c.p.s.,
  capas finales 9.4–11.8 % b.h.
- `cinetica_roa.py` — **modelo cinético único del proyecto (29 sept
  2026)**: isoterma de equilibrio de Roa para café pergamino (Trejos et
  al., 1989) + ecuación unificada de capa delgada de Roa (SECAFÉ,
  Parra-Coronado et al., 2008). Cubre T 10–70 °C y HR 5–100 % (isoterma
  medida a 5–55 °C), es decir todo el dominio de las tres estrategias.
  La HR entra por la humedad de equilibrio Me(T,HR) y por el déficit de
  presión de vapor del aire. Paso dinámico por tiempo equivalente
  (reproduce la solución analítica a T/HR constantes, error ~1e-14),
  rehumectación cuando M < Me, contadores de horas fuera de rango y
  función `simular()` para las líneas base. M0 = 55 % b.h.; humedad
  objetivo 11 % b.h. como criterio de parada (separada de Me). Fuentes,
  erratas detectadas y verificación cruzada contra Phitakwinai y Eliseu
  en `data/reference/roa_cenicafe_isoterma_capa_delgada.md`.
- `cinetica_dinamica.py` — Midilli modificado generalizado de
  Phitakwinai et al. (2019, Tabla 3), válido solo en T 50–70 °C / RH
  10–30 %. **Desde el 29 sept 2026 ya no es la cinética de la planta**;
  se conserva como validación independiente. Ese día se corrigió
  `k_generalizado` (coeficiente de T mal transcrito y errata del
  artículo en el término T·RH: 1.0318e-4 → 1.0318e-7; ver
  `data/reference/phitakwinai_2019_tabla3_ecuaciones_generalizadas.md`).
- `planta_secado.py` — `ModeloSecadoPlant(Plant)`: pone
  `secador_electrico.py` (plenum + lecho Thompson + Roa) detrás de la interfaz
  `Plant` de `modbus_server.py`. Publica `RH_ambient` (exterior) y
  `RH_process` (cámara) por separado, acepta una secuencia de días de
  clima (`clima_dias`) para recibir la misma realización Monte Carlo que
  las líneas base, y cuenta horas fuera de rango / en rehumectación.
  Con factores de aceleración altos, el control todo/nada desde CODESYS
  oscila artificialmente (τ del plenum ≈ 2 min): sirve para ver la HMI; los
  resultados salen de `control_supervisado.py`.
- `escenario_sol_abierto.py` / `linea_base_activa.py` — desde el 29 sept
  2026 incluyen una versión v0.2 con el modelo de Roa (`simular_patio`,
  `simular_activa`), alimentada con el ambiente de Chinchiná más un
  incremento solar diurno calibrado contra literatura (patio 12.9 °C vs.
  Eliseu 2008; solar activa 20 °C, reducción 36 % frente a patio dentro de
  30–50 % de Duque-Dussán et al., 2026). Las versiones v0.1 (Newton,
  Logarítmico) se conservan para los notebooks de la semana 5, pero no
  responden a T/HR y no deben usarse en Monte Carlo.
- `metodologia_estadistica_monte_carlo.md` — **diseño definido, no
  ejecutado (24-25 sept 2026)**: protocolo estadístico para la campaña
  Monte Carlo de comparación de perfiles térmicos. Fija el diseño como
  comparación pareada (misma realización de perturbaciones corrida bajo
  las 3 estrategias), el cálculo del número de realizaciones necesarias
  vía análisis de potencia estadística (en vez de un número arbitrario),
  el criterio de convergencia como verificación complementaria, y la
  corrección de la prueba de comparación final (Wilcoxon pareada en vez
  de Mann-Whitney, que asume muestras independientes). Responde
  directamente a la observación del asesor sobre tamaño de muestra
  (`Informe_revision_documento_secado_cafe.pdf`, sección 5.6).
- `requirements.txt` — dependencias Python del proyecto (`pymodbus`,
  fijado en `pymodbus==3.6.9`: versiones ≥3.7 cambiaron la ubicación de
  `ModbusSlaveContext` en `pymodbus.datastore` y rompen `modbus_server.py`).

Contenido esperado (pendiente):
- Ajustar `PLC_PRG` (ventilador encendido durante el secado, enclavamiento
  resistencia–ventilador, parada a 11 % b.h.) y verificar CODESYS contra
  `control_supervisado.py` a tiempo real (ver
  `codesys/comunicacion_modbus.md`).
- CODESYS/FluidSIM: canales `flow_dir_cmd` (15) y `M_coffee_max` (16-17),
  lógica de inversión cada 6 h y compuerta neumática en FluidSIM (ver
  `codesys/comunicacion_modbus.md`).
- Prueba repetible (automatizada) de consistencia dinámico vs. estático:
  hoy la verifica el smoke test de `cinetica_roa.py`.
- Agregar en CODESYS los canales de `RH_process` (registros 13-14), ver
  `codesys/comunicacion_modbus.md`.
- Timeout del canal master en CODESYS (pendiente de
  `codesys/comunicacion_modbus.md`, sección 6; no bloqueante, `heartbeat`
  ya cubre el mismo caso).
- Script de campaña Monte Carlo (sobre la planta dinámica ya validada):
  protocolo estadístico ya definido en
  `metodologia_estadistica_monte_carlo.md`; falta la calibración previa
  y la implementación del script.
- RH_process usa una aproximación psicrométrica simple sin el aporte de
  vapor del café (efecto de sorción) — ver limitación documentada en
  `dinamica_termica.py`.

Entregable semana 4: primer script que reproduzca una curva de secado. ✅
Entregable semana 5: modelo Python v0.1 con unidades y parámetros
documentados. ✅ Ajuste de modelos candidatos con RMSE/MAE/R². ✅
Reproducción de datos/curva de literatura. ✅ Generador de T/HR ambiente
nominal y perturbado. ✅ Primera línea base activa. ✅ Escenario de secado
al sol en lazo abierto. ✅ Primera estimación de energía. ✅
Prueba mínima de comunicación con CODESYS (Modbus TCP, servidor
Python): verificada end-to-end con CODESYS real (v1, 6 variables, ver
`codesys/comunicacion_modbus.md`).
Esqueleto del modelo real conectado a la interfaz `Plant`
(`dinamica_termica.py` + `cinetica_dinamica.py` + `planta_secado.py`):
✅ — **verificado end-to-end con CODESYS real y HMI el 23 sept 2026**
(`T_process`, `M_coffee`, `tiempo_proceso_h` en vivo, coincidentes con
la consola de Python). El 29 sept 2026 se reemplazó por el modelo
definitivo (Roa-Cenicafé + lecho Thompson + secador eléctrico de 80 kg
c.p.s. dimensionado con fuentes); `ParametrosCamara`/`CondicionesSecado`
ya no existen como valores de relleno.
Prueba de integración concurrente Modbus (este servidor) + OPC
(FluidSIM) + lógica de control, sobre el mismo runtime CODESYS Control
Win V3: ✅ — corrida en paralelo con `modbus_server.py --plant modelo`
sin conflictos de puerto ni de tiempos (detalle del lado CODESYS/OPC en
`codesys/`).

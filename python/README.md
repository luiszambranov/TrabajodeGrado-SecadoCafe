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
- `dinamica_termica.py` — balance de energía concentrado (lumped) de la
  cámara: produce `T_process` a partir de `heater_cmd`/`fan_cmd` y la
  temperatura ambiente. **Esqueleto v0, no calibrado**: los parámetros
  de `ParametrosCamara` son de orden de magnitud (elegidos para una
  temperatura de equilibrio plausible, ~55-60°C), pendientes de
  calibrar contra la ficha técnica de la secadora física de referencia
  o con el asesor — ver docstring del módulo.
- `cinetica_dinamica.py` — extiende Midilli modificado
  (`modelo_secado.py`) a una forma que se puede integrar paso a paso
  cuando T/RH cambian en el tiempo, usando las ecuaciones generalizadas
  k(T,RH), n(T,RH), b(T,RH) de la Tabla 3 de Phitakwinai et al. (2019) y
  el método de "tiempo equivalente" (justificación completa en el
  docstring del módulo). Válido dentro de T:50-70°C/RH:10-30%; fuera de
  ese rango marca `fuera_de_rango=True` en vez de fallar. El smoke test
  del módulo verifica que, con T/RH fijos, este método reproduce
  exactamente la curva estática ya validada por `ajuste_modelos.py`.
- `planta_secado.py` — `ModeloSecadoPlant(Plant)`: conecta
  `dinamica_termica.py` + `cinetica_dinamica.py` + `modelo_secado.py`
  (conversión MR → `M_coffee`) detrás de la interfaz `Plant` de
  `modbus_server.py`, reemplazando la planta de juguete. **Esqueleto
  v0**: antes de usarla para resultados o con CODESYS real falta (ver
  docstring del módulo) verificar consistencia contra el modelo
  estático, fijar M0/Me reales del caso de estudio, calibrar
  `ParametrosCamara`, y decidir el factor de aceleración temporal para
  las pruebas (hoy 1 s de reloj real = 1 h de modelo, por defecto).
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
- Calibración de `ParametrosCamara` (dinamica_termica.py) y de
  `CondicionesSecado` (M0/Me reales) contra la ficha técnica de la
  secadora física o con el asesor. **Bloqueante** antes del piloto de la
  campaña Monte Carlo (ver `metodologia_estadistica_monte_carlo.md`).
- Verificación rigurosa de consistencia planta dinámica vs. modelo
  estático (Etapa 5 del plan de implementación) — el smoke test de
  `cinetica_dinamica.py` ya lo comprueba de forma manual con T/RH
  fijos, falta automatizarlo como prueba repetible.
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
la consola de Python). Sigue pendiente la calibración de
`ParametrosCamara`/`CondicionesSecado` antes de usar la planta para
resultados o campañas de la propuesta final.
Prueba de integración concurrente Modbus (este servidor) + OPC
(FluidSIM) + lógica de control, sobre el mismo runtime CODESYS Control
Win V3: ✅ — corrida en paralelo con `modbus_server.py --plant modelo`
sin conflictos de puerto ni de tiempos (detalle del lado CODESYS/OPC en
`codesys/`).

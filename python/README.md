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

- `modbus_server.py` — **v0** de la comunicación Python-CODESYS.
  Servidor Modbus TCP (esclavo) que expone `T_process` (float32, °C) en
  los holding registers 0-1 y recibe `heater_cmd` (0/1) en el registro
  2. Corre una planta térmica de juguete (primer orden, todavía sin la
  cinética real de `modelo_secado.py`) solo para demostrar que la
  comunicación funciona en ambos sentidos. Ver
  `codesys/comunicacion_modbus.md` para el lado CODESYS (cliente/master)
  y el procedimiento de prueba completo.
- `requirements.txt` — dependencias Python del proyecto (`pymodbus`
  para la comunicación Modbus).

Contenido esperado (pendiente):
- Modelo térmico/energético concentrado completo (balance de aire,
  producto, pérdidas, potencia de calentamiento/ventilación) — la
  estimación de energía actual es solo el piso termodinámico.
- Scripts de campaña Monte Carlo.
- Integrar `modbus_server.py` con `modelo_secado.py` (reemplazar la
  planta de juguete por la cinética real) y sumar el resto de tags de
  la tabla de señales (`RH_ambient`, `M_coffee`, `fan_cmd`,
  `safety_ok`).

Entregable semana 4: primer script que reproduzca una curva de secado. ✅
Entregable semana 5: modelo Python v0.1 con unidades y parámetros
documentados. ✅ Ajuste de modelos candidatos con RMSE/MAE/R². ✅
Reproducción de datos/curva de literatura. ✅ Generador de T/HR ambiente
nominal y perturbado. ✅ Primera línea base activa. ✅ Escenario de secado
al sol en lazo abierto. ✅ Primera estimación de energía. ✅
Prueba mínima de comunicación con CODESYS (Modbus TCP, servidor
Python): v0 lista en `modbus_server.py`, pendiente evidencia end-to-end
con CODESYS (ver checklist en `codesys/comunicacion_modbus.md`).

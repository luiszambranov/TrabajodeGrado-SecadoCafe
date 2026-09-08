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

Contenido esperado (pendiente):
- Ajuste de parámetros contra el dataset de referencia y métricas de error
  (RMSE, MAE, R²) — próximo entregable de la semana 5 (`ajuste_modelos.py`).
- Modelo térmico/energético concentrado (balance de aire, producto, pérdidas,
  potencia de calentamiento/ventilación).
- Generador de perturbaciones ambientales (T y HR ambiente, nominal y perturbado).
- Scripts de campaña Monte Carlo.
- Cliente de comunicación (OPC UA u otra interfaz soportada) con CODESYS.

Entregable semana 4: primer script que reproduzca una curva de secado. ✅
Entregable semana 5 (parcial): modelo Python v0.1 con unidades y parámetros
documentados. ✅

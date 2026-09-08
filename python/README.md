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

Contenido esperado (pendiente):
- Modelo térmico/energético concentrado (balance de aire, producto, pérdidas,
  potencia de calentamiento/ventilación).
- Generador de perturbaciones ambientales (T y HR ambiente, nominal y
  perturbado) — puede apoyarse en las ecuaciones generalizadas de la
  Tabla 3 del paper (`data/reference/phitakwinai_2019_tabla3_ecuaciones_generalizadas.md`).
- Scripts de campaña Monte Carlo.
- Cliente de comunicación (OPC UA u otra interfaz soportada) con CODESYS.

Entregable semana 4: primer script que reproduzca una curva de secado. ✅
Entregable semana 5: modelo Python v0.1 con unidades y parámetros
documentados. ✅ Ajuste de modelos candidatos con RMSE/MAE/R². ✅
Reproducción de datos/curva de literatura. ✅

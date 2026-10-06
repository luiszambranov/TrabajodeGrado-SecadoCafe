# /python/legacy — código retirado (no se usa en los resultados)

Versiones anteriores del modelo, guardadas por trazabilidad. **Ningún script
vigente importa nada de esta carpeta** y no se mantiene ejecutable.

| Archivo | Qué era | Por qué se retiró |
|---|---|---|
| `modelo_secado.py` | v0.1 (semana 5): Newton, Logarítmico y Midilli modificado | Newton y Logarítmico no responden a T/HR; Midilli solo vale en 50–70 °C |
| `ajuste_modelos.py` | Ajuste RMSE/MAE/R² contra Phitakwinai et al. (2019) | El modelo elegido pasó a ser Roa–Cenicafé |
| `cinetica_dinamica.py` | Midilli generalizado dinámico (planta del 23 sept 2026) | Fuera de dominio para las líneas base solares |
| `estimacion_energia.py` | Piso termodinámico (solo calor latente) | Reemplazado por `../balance_energia.py` |
| `lineas_base_v01.py` | Patio (Newton, Eliseu 2008) y activa (Logarítmico, Mackpayen 2017) | No responden al clima de Chinchiná |
| `CurvaSecado.ipynb`, `AjusteModelos.ipynb`, `EscenarioSolAbierto.ipynb`, `LineaBaseActiva.ipynb`, `GeneradorAmbiente.ipynb`, `EstimacionEnergia.ipynb` | Notebooks de la semana 5 | Dependen de las versiones v0.1 |

Explicación completa de cada decisión: `docs/evolucion_del_modelo.md`.

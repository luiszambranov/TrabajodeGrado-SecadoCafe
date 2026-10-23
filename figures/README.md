# figures — Figuras del documento

Todas se regeneran con los scripts de `python/` (entre paréntesis), salvo las
capturas de pantalla.

| Archivo | Qué muestra |
|---|---|
| `perfiles_resumen.png` | Consigna de los cuatro perfiles (REF, P1, P2, P3) en función de la humedad del lote (`graficas_perfiles.py`). |
| `perfil_REF.png` | Perfil de referencia de Cenicafé en el día nominal: temperatura del aire, consigna, ambiente, humedad del lote y de las capas, y franjas con el aire invertido (`graficas_perfiles.py`). |
| `perfil_P1.png`, `perfil_P2.png`, `perfil_P3.png` | Cada perfil con los tres caudales: temperatura, humedad y el instante del cambio de consigna en P2 y P3 (`graficas_perfiles.py`). |
| `diferencias_pareadas.png` | Diferencias de tiempo y energía de P1-C75 y P3-C75 frente a REF, realización por realización (`analisis_pareado.py`). |
| `limites_actuacion.png` | Lo pedido frente a lo físicamente aplicado: consigna, temperatura lograda, ciclo de trabajo y saturación de la resistencia (`limites_actuacion.py`). |
| `efecto_clima.png` | Efecto separado de la temperatura y la humedad ambiente (niveles p5/p95 de NASA POWER): humedad del lote, esfuerzo de la resistencia y cambio de tiempo y energía frente al clima nominal (`efecto_clima.py`). |
| `sensibilidad_tornado.png` | Efecto de variar ±20 % cada parámetro del modelo (`sensibilidad_tornado.py`). |
| `ensayos_fallos_F1_F2_F3.png` | Ensayos de falla con CODESYS y FluidSIM: CODESYS detenido, FluidSIM detenido y STOP desde la HMI (`graficas_ensayos.py`). |
| `ensayo_continuidad_fisica.png` | La planta sigue evolucionando durante un paro, una pérdida de comunicación y la recuperación (`ensayo_continuidad_fisica.py`). |
| `lote_codesys_P3C100.png` | Lote completo P3-C100 supervisado por CODESYS y FluidSIM: temperatura, humedad por capas, potencia y caudal (`grafica_lote.py`, generada por el servidor). |
| `hmi_secado.png` | Captura de la HMI de CODESYS al terminar un lote. |

Las figuras de la campaña Monte Carlo (convergencia, cajas y Pareto) están en
`python/resultados/campana/`; el circuito de FluidSIM en `fluidsim/` y los diagramas
de la arquitectura en `docs/`.

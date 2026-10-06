# /figures

Figuras para el documento final. Se regeneran con `python/graficas_perfiles.py`.

| Archivo | Contenido |
|---|---|
| `perfiles_resumen.png` | Setpoint de los 4 perfiles (REF, P1, P2, P3) en función de la humedad del café. |
| `perfil_REF.png` | Referencia de Cenicafé: T_process, setpoint, T ambiente, humedad del lote y de las capas, franjas de aire invertido. |
| `perfil_P1.png`, `perfil_P2.png`, `perfil_P3.png` | Cada perfil con los 3 caudales: temperatura, humedad y el instante de cambio de setpoint (P2 y P3, al 30 % b.h.). |

Caso determinista: día nominal de Chinchiná y M0 = 55 % b.h. Las figuras de
la campaña Monte Carlo (convergencia, cajas, Pareto) están en
`python/resultados/campana/`. El diagrama de la simulación está en `docs/`.

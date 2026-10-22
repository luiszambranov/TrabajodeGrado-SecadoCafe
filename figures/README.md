# /figures

Figuras para el documento final. Se regeneran con `python/graficas_perfiles.py`.

| Archivo | Contenido |
|---|---|
| `perfiles_resumen.png` | Setpoint de los 4 perfiles (REF, P1, P2, P3) en función de la humedad del café. |
| `perfil_REF.png` | Referencia de Cenicafé: T_process, setpoint, T ambiente, humedad del lote y de las capas, franjas de aire invertido. |
| `ensayo_continuidad_fisica.png` | Ensayo de continuidad física (21 oct 2026, `python/ensayo_continuidad_fisica.py`): paro, enfriamiento, comunicación perdida y recuperación con la cámara caliente; la planta sigue evolucionando. |
| `perfil_P1.png`, `perfil_P2.png`, `perfil_P3.png` | Cada perfil con los 3 caudales: temperatura, humedad y el instante de cambio de setpoint (P2 y P3, al 30 % b.h.). |

Caso determinista: día nominal de Chinchiná y M0 = 55 % b.h. Las figuras de
la campaña Monte Carlo (convergencia, cajas, Pareto) están en
`python/resultados/campana/`. El diagrama de la simulación está en `docs/`.

## Capturas de la HMI de CODESYS (22 oct 2026)

| Archivo | Contenido |
|---|---|
| `hmi_secado_terminado_REF.png` | HMI v8 al terminar un lote REF (50 °C, 100 %): pilotos «Secado terminado», «Bandeja adentro», «Aire invertido», comunicación con Python OK, energía 143,3 kWh, selector de perfil y caudal. Las tendencias de la HMI muestran solo una ventana móvil (limitación de R5); el lote completo está en `lote_codesys_*.png`. |
| `lote_codesys_P1C75.png`, `lote_codesys_REF.png` | Lote completo supervisado por CODESYS + FluidSIM (corridas de verificación, semilla 1001), generado por `python/grafica_lote.py` desde el CSV del servidor: temperatura, consigna y ambiente; humedad promedio y por capas con inversiones de flujo y fin de secado; potencia y caudal. |

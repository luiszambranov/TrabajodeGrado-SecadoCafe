# codesys/v6 — programa vigente (19 oct 2026)

Juego completo y único del programa CODESYS. Copiar cada archivo en su objeto
del proyecto (o pegar `CODIGOS_CODESYS_v6.txt`, que trae los cuatro juntos).

| Archivo | Objeto en CODESYS |
|---|---|
| `E_ESTADO.st` | DUT (enumeración) `E_ESTADO` |
| `GVL_SECUENCIA.st` | Lista de variables globales `GVL_SECUENCIA` |
| `PLC_PRG.st` | Programa `PLC_PRG` (1.º en la MainTask) |
| `SECUENCIA.st` | Programa `SECUENCIA` (2.º en la MainTask) |

## Cambios respecto a v5 (14 oct 2026)

- `GVL_SECUENCIA.sin_fluidsim` (TRUE por defecto): el PLC simula los pulsadores de
  campo (EMERGENCIA y STOP en reposo) y los finales de carrera de los dos cilindros,
  para probar la HMI sin FluidSIM. Con FluidSIM conectado por OPC: poner FALSE.
- `GVL_SECUENCIA.lote_preparado := TRUE` al arrancar: START funciona sin pulsar antes
  "Nuevo lote" (tras descargar un lote sí se pide).
- `PLC_PRG`: sin cambios de lógica respecto a v5.
- Lado Python (`python/modbus_server.py`, 19 oct): el server arranca en HOLD y el modelo
  se congela en HOLD (REPOSO, PARO, FIN_SECADO); solo avanza tras START.

Tras cargar v6: **Reiniciar en frío** y descargar (hay variables nuevas con valor inicial).

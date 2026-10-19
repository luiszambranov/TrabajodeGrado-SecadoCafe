# /fluidsim

Circuito electroneumático de actuación (FluidSIM-P 4.2), conectado a CODESYS por OPC (`CoDeSys.OPC.DA`). Estado: **funcionando con la HMI final (19 oct 2026)**.

## Qué contiene el circuito

- **Compuerta de inversión del aire** (cilindro 1, doble efecto) con válvula 5/2 biestable (bobinas 1S1/2S1) y finales de carrera 1B1 (normal) y 1B2 (invertida). El sentido del aire que recibe Python sale de 1B2, no del reloj de 6 h: si la compuerta se traba, el aire no se invierte y el PLC pasa a FALLA.
- **Bandeja de café** (cilindro 2, doble efecto) con válvula 5/2 biestable (1S2/2S2) y finales 2B1 (afuera) y 2B2 (adentro).
- Pulsadores EMERGENCIA (NC), START (NA) y STOP (NC); relé K1 del ventilador; semáforo verde, amarillo y rojo.
- Unidad de mantenimiento y reguladores de caudal.

## Enlace OPC

| Bloque FluidSIM | Variable CODESYS | Bits |
|---|---|---|
| FluidSIM Out | `GVL_SECUENCIA.INPUT0` | 0 EMERGENCIA, 1 START, 2 STOP, 3 1B1, 4 1B2, 5 2B1, 6 2B2 |
| FluidSIM In | `GVL_SECUENCIA.OUTPUT0` | 0 1S1, 1 2S1, 2 1S2, 3 2S2, 4 K1, 5 verde, 6 amarillo, 7 rojo |

En reposo (compuerta normal y bandeja afuera), `INPUT0` = 45: EMERGENCIA (1) + STOP (4) + 1B1 (8) + 2B1 (32). En CODESYS, `GVL_SECUENCIA.sin_fluidsim` debe estar en FALSE.

Evidencia: `../codesys/evidencia_fluidsim_circuito_v7.png`.

**Pendiente:** subir aquí el archivo del circuito (`.ct`).

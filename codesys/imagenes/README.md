# Iconos de la HMI (ImagePool de CODESYS)

Estilo plano en grises según ANSI/ISA-101 (HMI de alto desempeño): el color solo
marca estado (verde = activo). Cada icono está en SVG y en PNG (2×). Usar PNG si
el SVG no se ve en el runtime (el soporte SVG depende del sistema operativo).
Creados para este proyecto (sin licencias de terceros).

| Archivo | Elemento CODESYS | Propiedad / variable |
|---|---|---|
| ventilador_carcasa | Imagen (estática) | — |
| ventilador_rotor_on / _off | Imagen encima de la carcasa, mismo tamaño y posición | Movimiento absoluto → Rotación interior = `SECUENCIA.angulo_vent`; ID de imagen según `GVL_SECUENCIA.Q_K1` |
| resistencia_on / _off | Imagen | ID de imagen según `PLC_PRG.heater_on` |
| camara_secado | Imagen (estática) | — |
| aire_normal / aire_invertido | Imagen encima del lecho | ID de imagen según `PLC_PRG.aire_invertido` |
| compuerta_marco | Imagen (estática) | — |
| compuerta_hoja | Imagen encima del marco | Rotación interior = 0° (normal) / 90° (invertida) |
| bandeja | Imagen | Movimiento absoluto → X según `GVL_SECUENCIA.I_2B2` |
| boton_start / _pulsado | Conmutador de imagen, comportamiento "Pulsador de imagen" | `GVL_SECUENCIA.hmi_start` |
| boton_stop / _pulsado | Conmutador de imagen, comportamiento "Pulsador de imagen" | `GVL_SECUENCIA.hmi_stop` |

`_vista_previa_sinoptico.png` / `.svg` y `_hoja_iconos.png`: cómo queda el sinóptico armado y todos los iconos juntos (referencia, no van al ImagePool).

`ConductoInversion.png`, `CompuertaInversion.png`, `Invertidoabajo.png` y `Flecha.png`: piezas del dibujo del conducto de inversión del aire y la flecha de sentido usadas en la pantalla final.

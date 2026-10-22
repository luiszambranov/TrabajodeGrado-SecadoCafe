# codesys/v8 — programa vigente (21 oct 2026)

Responde a la guía de cierre del asesor, R4 («la planta no se pausa con el PLC»).
Un archivo por objeto de CODESYS (copiar el contenido completo en su objeto):
`E_ESTADO.st`, `GVL_SECUENCIA.st`, `PLC_PRG.st`, `SECUENCIA.st`. `CODIGOS_CODESYS_v8.txt` trae
los cuatro juntos (mismo contenido).

| Objeto en CODESYS | ¿Cambia? |
|---|---|
| DUT `E_ESTADO` (`E_ESTADO.st`) | No (igual a v7) |
| GVL `GVL_SECUENCIA` (`GVL_SECUENCIA.st`) | **Sí**: `I_FLUIDSIM_PULSO` (INPUT0.7) y `fluidsim_estado` |
| Programa `PLC_PRG` (`PLC_PRG.st`) | **Sí**: relojes y estado de la planta (27–39), estado FluidSIM → Python (40), textos HMI |
| Programa `SECUENCIA` (`SECUENCIA.st`) | **Sí**: falla 5 (FluidSIM), post-ventilación en PARO/FALLA, EMERGENCIA todo en cero, inversión con el tiempo de secado efectivo |

> **Si el proyecto está en v6**, también falta lo de v7: perfil térmico y caudal en la HMI y
> el canal 26 (`setpoint_cmd`). Al pegar v8 completo ya queda incluido; solo hay que crear
> el canal 26 (está en la tabla de abajo).

## 0. Antes de pegar: quitar el bloqueo que se agregó el 20 oct

El asesor pidió que la simulación **no deje de correr** por no tener los tres programas
conectados. Borrar la variable o condición que se agregó el 20 oct para «no correr si
FluidSIM no está conectado» (no está en el repositorio: está solo en el proyecto). En v8
la física corre siempre en Python; lo único que exige FluidSIM vivo es el **START** de la
máquina (enclavamiento de máquina: una secadora real no arranca sin sus E/S de campo). Si
se quiere probar sin FluidSIM, se usa `GVL_SECUENCIA.sin_fluidsim := TRUE`, que queda
**declarado** a Python (registro 40 = 2) y en el CSV del ensayo.

## 1. Canales nuevos en IO Mapping (dispositivo Modbus esclavo, puerto 5020)

Igual que los anteriores: cada REAL va partido en **dos canales de 1 registro** (FC03),
`_hi` en la dirección par → `[0]` y `_lo` en la impar → `[1]` (bug del maestro Modbus de SP9,
`codesys/comunicacion_modbus.md`, sección 0.6).

| Canal | Access type | Dirección (dec / hex) | Long. | Variable PLC |
|---|---|---|---|---|
| `setpoint_cmd` *(solo si vienes de v6)* | Write Single Register (FC06) | 26 / `16#001A` | 1 | `Application.PLC_PRG.setpoint_cmd` |
| `t_lote_hi` | Read Holding Registers (FC03) | 27 / `16#001B` | 1 | `Application.PLC_PRG.t_lote_raw[0]` |
| `t_lote_lo` | Read Holding Registers (FC03) | 28 / `16#001C` | 1 | `Application.PLC_PRG.t_lote_raw[1]` |
| `t_secado_ef_hi` | Read Holding Registers (FC03) | 29 / `16#001D` | 1 | `Application.PLC_PRG.t_secado_ef_raw[0]` |
| `t_secado_ef_lo` | Read Holding Registers (FC03) | 30 / `16#001E` | 1 | `Application.PLC_PRG.t_secado_ef_raw[1]` |
| `t_parado_hi` | Read Holding Registers (FC03) | 31 / `16#001F` | 1 | `Application.PLC_PRG.t_parado_raw[0]` |
| `t_parado_lo` | Read Holding Registers (FC03) | 32 / `16#0020` | 1 | `Application.PLC_PRG.t_parado_raw[1]` |
| `t_planta_hi` | Read Holding Registers (FC03) | 33 / `16#0021` | 1 | `Application.PLC_PRG.t_planta_raw[0]` |
| `t_planta_lo` | Read Holding Registers (FC03) | 34 / `16#0022` | 1 | `Application.PLC_PRG.t_planta_raw[1]` |
| `estado_planta` | Read Holding Registers (FC03) | 35 / `16#0023` | 1 | `Application.PLC_PRG.estado_planta` |
| `T_amb_hi` | Read Holding Registers (FC03) | 36 / `16#0024` | 1 | `Application.PLC_PRG.T_amb_raw[0]` |
| `T_amb_lo` | Read Holding Registers (FC03) | 37 / `16#0025` | 1 | `Application.PLC_PRG.T_amb_raw[1]` |
| `hora_hi` | Read Holding Registers (FC03) | 38 / `16#0026` | 1 | `Application.PLC_PRG.hora_raw[0]` |
| `hora_lo` | Read Holding Registers (FC03) | 39 / `16#0027` | 1 | `Application.PLC_PRG.hora_raw[1]` |
| `fluidsim_estado` | Write Single Register (FC06) | 40 / `16#0028` | 1 | `Application.PLC_PRG.fluidsim_estado_cmd` |

Son 13 canales de lectura y 1 de escritura (14 con el 26 si vienes de v6). Python
(`modbus_server.py`) ya publica 41 registros (0–40); hay que usar la versión del 21 oct.

**Importante:** la post-ventilación se mide con `t_planta_h` (registros 33–34); sin esos canales no hay post-ventilación. Para el campo «Tiempo de secado» de la HMI conviene usar `PLC_PRG.t_secado_efectivo_h` (no cuenta paradas ni post-ventilación) en lugar de `tiempo_secado_h` (registro 10, cuenta todo el tiempo con ventilador en RUN).

**Importante:** v8 usa `t_secado_efectivo_h` (registros 29–30) para el reloj de inversión.
Si esos dos canales no se crean, la compuerta no se invierte.

## 2. FluidSIM: detección de enlace caído

**Sin oscilador (ya funciona):** cuando se detiene la simulación de FluidSIM, INPUT0 llega en 0:
ningún final de carrera y los NC de STOP/EMERGENCIA abiertos, algo físicamente imposible con el
enlace vivo. SECUENCIA lo detecta en 1 s (`entradas_muertas`) y pasa a **FALLA 5** (no a
EMERGENCIA): resistencia en 0, post-ventilación, Python recibe `fluidsim_estado` = 3. Al volver
FluidSIM: START reconoce la falla → PARO y **resincroniza los cilindros** a la última posición
válida (FluidSIM reinicia sus cilindros a la posición inicial del circuito) → START reanuda el
lote donde iba.

**Con oscilador (opcional, más completo):** detecta además un enlace congelado (INPUT0 se queda
con el último valor). Ver abajo.

### Pulso de vida en la entrada 7 (opcional)

Un final de carrera estable no prueba que el enlace esté vivo (guía de cierre, ensayo F2).
Se agrega en el circuito eléctrico de FluidSIM un **oscilador con dos temporizadores** que
hace cambiar la entrada 7 del bloque «FluidSIM Out» cada ~1 s:

- `KT1`: relé temporizador con retardo a la conexión, **1 s**. Bobina alimentada a través de
  un contacto **NC de KT2**.
- `KT2`: relé temporizador con retardo a la conexión, **1 s**. Bobina alimentada a través de
  un contacto **NA de KT1**.
- Un contacto **NA de KT1** a la **entrada 7** del bloque «FluidSIM Out» (INPUT0.7).

Así INPUT0.7 queda 1 s en 1 y 1 s en 0. Si FluidSIM se detiene o el OPC se cae, el bit deja
de cambiar y en 5 s (`T_FS_MAX`) SECUENCIA pasa a **FALLA 5 «Sin enlace con FluidSIM»** y
avisa a Python (registro 40 = 3), que conserva el último sentido de aire válido.

**Activar la vigilancia:** mientras el oscilador no esté armado, dejar
`VIGILAR_PULSO_FS := FALSE` (constante de SECUENCIA, valor por defecto). Con FALSE, FluidSIM
funciona normal pero sin vigilancia del enlace (Python recibe 0 = no informado). Cuando el
oscilador esté listo, cambiar a TRUE, compilar y hacer el ensayo F2. Con TRUE y sin oscilador,
a los 5 s aparece FALLA 5 y START queda bloqueado.

**Modo FluidSIM / sin FluidSIM:** `GVL_SECUENCIA.sin_fluidsim` arranca en **FALSE**
(E/S de FluidSIM). Para probar sin FluidSIM, escribir TRUE en línea (Ctrl+F7). El cambio se
aplica de inmediato en cualquier estado. Al pasar a FluidSIM, el PLC **sincroniza solo** los
cilindros (activa las bobinas hasta que los finales de carrera de FluidSIM confirman la posición
que tenía la simulación); mientras tanto START no hace nada y `SECUENCIA.txt_modo` muestra
«Sincronizando cilindros de FluidSIM...». Si FluidSIM no está en simulación, STOP y EMERGENCIA
(contactos NC) se leen como pulsados.

## 3. HMI: variables nuevas para mostrar (sugerido, sin rediseñar)

| Qué | Variable |
|---|---|
| Tiempo de planta (desde el arranque) | `PLC_PRG.t_planta_h` |
| Tiempo del lote (incluye paradas) | `PLC_PRG.t_lote_h` |
| Tiempo de secado efectivo | `PLC_PRG.t_secado_efectivo_h` |
| Tiempo parado | `PLC_PRG.t_parado_h` |
| Hora y día/noche | `PLC_PRG.hora_txt`, `PLC_PRG.periodo_txt` |
| Temperatura ambiente | `PLC_PRG.T_ambiente` |
| Estado físico de la planta | `PLC_PRG.estado_planta_txt` |
| Enlace FluidSIM | `PLC_PRG.fluidsim_txt` |
| Piloto «Bandeja adentro» | `SECUENCIA.piloto_bandeja_adentro` |
| Estado de la máquina | `GVL_SECUENCIA.estado_txt` |
| Alarma activa (texto de la falla) | `SECUENCIA.txt_alarma` |
| Comunicación con Python (OK / ERROR) | `SECUENCIA.txt_comm` |
| Aviso de datos vencidos (R5) | `PLC_PRG.txt_datos`; `PLC_PRG.datos_validos` para ocultar/atenuar valores |

> **R5, lote completo (22 oct 2026):** la tendencia (Trend Recording) muestra una ventana móvil y no se logró conservar el lote desde t = 0. La historia del lote se grafica desde el CSV del servidor con `python/grafica_lote.py`, que `modbus_server.py` genera sola al terminar cada lote (CSV y PNG en `python/resultados/lotes/`, o junto al `--log-csv` indicado). Se declara como limitación.
| Modo de E/S / sincronización | `SECUENCIA.txt_modo` |

El campo de «Tiempo de secado» que ya existe sigue en `PLC_PRG.tiempo_secado_h` (registro 10,
horas en RUN). Para la tendencia, agregar `T_ambiente` a la gráfica de temperatura sirve para
que se vea el efecto día/noche.

### 3.1 Selector de perfil y caudal (si viene de v6 hay que crearlo)

El código solo copia `perfil_sel` → `perfil_activo` y `caudal_sel` → `caudal_activo` **en
REPOSO**. Si la HMI no escribe en esas dos variables, el lote corre siempre con REF (50 °C, 100 %).

| Elemento HMI | Propiedad «Variable» | Configuración |
|---|---|---|
| Cuadro combinado – entero (perfil) | `PLC_PRG.perfil_sel` | Lista de textos `TL_Perfiles`: ID `0` REF 50 °C, `1` P1 45 °C, `2` P2 50→35 °C, `3` P3 35→50 °C |
| Cuadro combinado – entero (caudal) | `PLC_PRG.caudal_sel` | Lista de textos `TL_Caudal` con **ID = valor**: `30`, `75`, `100` (si los ID son 0/1/2 el PLC recibe 0/1/2 y lo limita a 30 %) |
| Texto «Perfil activo» | `PLC_PRG.perfil_txt` | `%s` |
| Campo «SetPoint» | `PLC_PRG.setpoint` | `%.1f` |

Alternativa sin cuadro combinado: 4 botones en modo **«Asignar valor»** (Tap / Write value) que
escriben 0, 1, 2, 3 en `PLC_PRG.perfil_sel`, y 3 que escriben 30, 75, 100 en `PLC_PRG.caudal_sel`.

Prueba rápida para separar código de HMI: en el Watch, en REPOSO, escribir `perfil_sel = 1`
(doble clic en «Valor preparado», Ctrl+F7). Si `setpoint` pasa a 45 y Python muestra SP45, el
código está bien y el problema es el enlace del elemento de la HMI.

## 4. Política de parada (para la Tabla C1 del documento)

| Situación | Resistencia | Ventilador | Planta Python |
|---|---|---|---|
| PARO (STOP) | 0 de inmediato | Post-ventilación 10 min de modelo si venía calentando, luego 0 | Sigue: se enfría hacia el ambiente |
| FALLA (cilindro, finales de carrera, FluidSIM) | 0 de inmediato | Post-ventilación 10 min, luego 0 | Sigue |
| FALLA de comunicación con Python | La apaga Python (política local) | Post-ventilación de Python 10 min, luego 0 | Sigue |
| EMERGENCIA | 0 | **0** (parada de todo movimiento) | Sigue; el corte térmico de 90 °C protege la resistencia |
| FIN DE SECADO | 0 (antes: 0.5 h de ENFRIAMIENTO con ventilador) | 0 | Sigue |

Es una función de software demostrada, no una certificación de seguridad funcional. En una
implementación real, la salida del ventilador en emergencia se define con la evaluación de
riesgos (ISO 12100).

## 5. Ensayos F1–F5 (guía de cierre, pág. 6)

**Preparación (una vez):**
1. (Opcional) Oscilador KT1/KT2 en FluidSIM y `VIGILAR_PULSO_FS := TRUE`: detecta también un
   enlace congelado. F2 ya funciona sin él, por la detección de entradas muertas.
2. Modo FluidSIM: `sin_fluidsim` ya arranca en FALSE. Los ensayos no requieren cambiar de modo.
3. Python con registro CSV, un archivo por ensayo:
   `python modbus_server.py --hora-inicio 8 --log-csv resultados/ensayos/F1_codesys.csv`
4. Nuevo lote → START → dejar secar hasta que la cámara esté caliente (T_process ≈ consigna y
   distinta de T_ambiente). Ahí se provoca la falla.

| Ensayo | Cómo se provoca | Qué debe verse | Recuperación (F4) |
|---|---|---|---|
| F1 | CODESYS: *Debug → Stop* (Shift+F8). Detiene la aplicación sin borrar variables | CSV: a los 5 s `comm_lost` = 1, `estado_planta` 3 (post-ventilación) → 4, resistencia 0, `t_planta_h` sigue, `T_process_c` baja hacia `T_ambiente_c`. FluidSIM deja de recibir salidas | *Debug → Start* (F5): CODESYS sigue en el mismo estado, Python vuelve a `comm_lost` = 0; si había pasado a FALLA, START reconoce (PARO) y START reanuda |
| F2 | Detener la simulación de FluidSIM (Python y CODESYS siguen) | HMI: FALLA 5 «Sin enlace con FluidSIM» en ~1 s (roja intermitente, no emergencia); resistencia 0, post-ventilación. CSV: `fluidsim_estado` = 3 y `flujo_invertido_aplicado` queda en el último válido | Reanudar FluidSIM → START reconoce (PARO, los cilindros vuelven solos a su posición) → START reanuda el secado |
| F3 | STOP en la HMI | PARO → «PARO - POST-VENTILACION» → PARO; `t_parado_h` crece y `t_secado_h` no | START reanuda |
| F4 | Es la recuperación de F1 y F2 (columna derecha) | Sin salto de estado, sin borrar energía ni humedad, sin «Nuevo lote» oculto; el lote continúa | — |
| F5 | Cerrar `modbus_server.py` (Ctrl+C) | CODESYS: heartbeat congelado → `comm_error` en 4 s → FALLA 1 «Sin comunicación con Python», salidas en 0. (Si Python termina, no se exige que la planta siga calculando.) | Volver a arrancar Python (empieza un lote nuevo: es otra planta) |

Notas:
- F1 con *Stop* (no apagar el runtime): al reiniciar el runtime completo las variables vuelven
  a su valor inicial (`sin_fluidsim` vuelve a TRUE y la máquina a REPOSO) y el lote de CODESYS
  se pierde, aunque Python lo conserva. Si se hace así, declararlo en el documento.
- Guardar el CSV de cada ensayo y, si se puede, un video corto. Al terminar: commit y tag.

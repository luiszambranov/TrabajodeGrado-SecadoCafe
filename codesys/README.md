# codesys — Supervisión en CODESYS V3.5 SP9

Controlador del secador: lee la planta simulada en Python por Modbus TCP,
ejecuta la máquina de estados, las alarmas y la HMI, y mueve los cilindros de
FluidSIM por OPC.

## Archivos

| Archivo | Qué es |
|---|---|
| `archivo_codesys/SecadoCafe_Terminado.project` | Proyecto completo de CODESYS (aplicación, IO Mapping Modbus, HMI, configuración de símbolos para OPC). Es el que se abre para ejecutar el sistema. |
| `PLC_PRG.st` | Programa de comunicación con la planta: convierte registros Modbus a REAL, vigila el heartbeat de Python, calcula la consigna del perfil térmico, detecta el fin del secado y prepara los textos y relojes de la HMI. |
| `SECUENCIA.st` | Máquina de estados (CASE OF): REPOSO, CARGA, SECADO, INVERSIÓN, ENFRIAMIENTO, FIN DE SECADO, DESCARGA, PARO, FALLA y EMERGENCIA; mandos, cilindros, ventilador, semáforo, post-ventilación y vigilancia del enlace con FluidSIM. |
| `GVL_SECUENCIA.st` | Variables globales compartidas entre FluidSIM (OPC), la HMI, `SECUENCIA` y `PLC_PRG`. |
| `E_ESTADO.st` | Enumeración de los estados de la máquina. |
| `imagenes/` | Imágenes de la HMI (sinóptico, ventilador, resistencia, compuerta, bandeja, botones), en PNG y SVG. |
| `conexion_opc.png` | Configuración del enlace OPC entre CODESYS y FluidSIM. |

Los cuatro `.st` son el mismo código que está dentro del proyecto, exportado como
texto para leerlo sin abrir CODESYS.

## Cómo ejecutarlo

1. Arrancar la planta: en `python/`, `python modbus_server.py` (puerto 5020).
2. Iniciar CODESYS Control Win V3 (bandeja del sistema → *Start PLC*). La versión del
   runtime debe ser la misma del IDE (SP9).
3. Abrir `archivo_codesys/SecadoCafe_Terminado.project`, en *Device* elegir el PLC
   local (*Establecer ruta activa*), compilar, iniciar sesión con descarga, *Reiniciar en
   frío* y RUN. MainTask llama primero `PLC_PRG` y luego `SECUENCIA`.
4. Abrir `fluidsim/SecadoCafeFLM.ct` en FluidSIM e iniciar la simulación (servidor OPC
   `CoDeSys.OPC.DA`).
5. En la HMI, en REPOSO: elegir el perfil y el caudal, pulsar **Nuevo lote** y **START**.

Sin FluidSIM: escribir `GVL_SECUENCIA.sin_fluidsim := TRUE` en línea (Ctrl+F7); el PLC
simula los pulsadores de campo y los cilindros.

## Canales Modbus (IO Mapping del esclavo Modbus TCP, 127.0.0.1:5020)

Cada REAL se lee con **dos canales de un registro** (FC03): `_hi` en la dirección par →
`[0]` y `_lo` en la impar → `[1]`. Las escrituras usan FC06.

| Dir. | Canal(es) | Función | Variable en `PLC_PRG` |
|---|---|---|---|
| 0–1 | `T_process_hi/lo` | FC03 | `T_process_raw[0..1]` → `T_process` |
| 2 | `heater_cmd` | FC06 | `heater_cmd` |
| 3 | `fan_cmd` | FC06 | `fan_cmd` |
| 4–5 | `RH_ambient_hi/lo` | FC03 | `RH_ambient_raw[0..1]` |
| 6 | `plant_mode` | FC06 | `plant_mode` (0 RUN, 1 HOLD) |
| 7 | `safety_ok` | FC03 | `safety_ok` |
| 8–9 | `M_coffee_hi/lo` | FC03 | `M_coffee_raw[0..1]` → `M_coffee` |
| 10–11 | `tiempo_proceso_hi/lo` | FC03 | `tiempo_proceso_raw[0..1]` → `tiempo_secado_h` |
| 12 | `heartbeat` | FC03 | `heartbeat_actual` |
| 13–14 | `RH_process_hi/lo` | FC03 | `RH_process_raw[0..1]` |
| 15 | `flow_dir_cmd` | FC06 | `flow_dir_cmd` |
| 16–17 | `M_coffee_max_hi/lo` | FC03 | `M_coffee_max_raw[0..1]` |
| 18–19 | `heater_duty_hi/lo` | FC03 | `heater_duty_raw[0..1]` |
| 20 | `fan_speed_pct` | FC06 | `fan_speed_pct` (30–100 %) |
| 21 | `reset_lote_cmd` | FC06 | `reset_lote_cmd` (pulso de nuevo lote) |
| 22–23 | `caudal_hi/lo` | FC03 | `caudal_raw[0..1]` |
| 24–25 | `energia_hi/lo` | FC03 | `energia_raw[0..1]` |
| 26 | `setpoint_cmd` | FC06 | `setpoint_cmd` (°C enteros) |
| 27–28 | `t_lote_hi/lo` | FC03 | `t_lote_raw[0..1]` → `t_lote_h` |
| 29–30 | `t_secado_ef_hi/lo` | FC03 | `t_secado_ef_raw[0..1]` → `t_secado_efectivo_h` (reloj de la inversión del aire) |
| 31–32 | `t_parado_hi/lo` | FC03 | `t_parado_raw[0..1]` → `t_parado_h` |
| 33–34 | `t_planta_hi/lo` | FC03 | `t_planta_raw[0..1]` → `t_planta_h` (reloj de la post-ventilación) |
| 35 | `estado_planta` | FC03 | `estado_planta` |
| 36–37 | `T_amb_hi/lo` | FC03 | `T_amb_raw[0..1]` → `T_ambiente` |
| 38–39 | `hora_hi/lo` | FC03 | `hora_raw[0..1]` → `hora_dia` |
| 40 | `fluidsim_estado` | FC06 | `fluidsim_estado_cmd` |

Significado y unidades de cada registro: `docs/tabla_variables.md`.

## Señales con FluidSIM (OPC, un byte por sentido)

| Bit | `GVL_SECUENCIA.INPUT0` (bloque FluidSIM Out) | `GVL_SECUENCIA.OUTPUT0` (bloque FluidSIM In) |
|---|---|---|
| 0 | Emergencia (NC) | Bobina: cilindro 1 sale (compuerta invertida) |
| 1 | START (NA) | Bobina: cilindro 1 entra (compuerta normal) |
| 2 | STOP (NC) | Bobina: cilindro 2 sale (bandeja adentro) |
| 3 | 1B1: compuerta normal | Bobina: cilindro 2 entra (bandeja afuera) |
| 4 | 1B2: compuerta invertida | Relé K1: ventilador |
| 5 | 2B1: bandeja afuera | Lámpara verde |
| 6 | 2B2: bandeja adentro | Lámpara amarilla |
| 7 | Pulso de vida (opcional) | Lámpara roja |

**Enlace caído.** Si la simulación de FluidSIM se detiene, `INPUT0` llega en 0 (ningún
final de carrera y los NC abiertos), algo imposible con el enlace vivo. `SECUENCIA` lo
detecta en 1 s (`entradas_muertas`) y pasa a FALLA 5 «Sin enlace con FluidSIM»: resistencia
en 0, post-ventilación y `fluidsim_estado` = 3 hacia Python. Al volver FluidSIM, START
reconoce la falla (PARO), el PLC lleva los cilindros a su última posición válida y otro
START reanuda el lote.

**Pulso de vida (opcional).** Un oscilador de dos temporizadores en FluidSIM (KT1 y KT2 de
1 s, KT1 alimentado por un NC de KT2 y KT2 por un NA de KT1; un NA de KT1 a la entrada 7)
hace cambiar `INPUT0.7` cada segundo y permite detectar también un enlace congelado. Se
activa con la constante `VIGILAR_PULSO_FS := TRUE` en `SECUENCIA`.

## HMI

| Qué muestra o mueve | Variable |
|---|---|
| Selector de perfil (cuadro combinado entero, IDs 0–3) | `PLC_PRG.perfil_sel` |
| Selector de caudal (IDs = 30, 75, 100) | `PLC_PRG.caudal_sel` |
| Consigna aplicada / texto del perfil activo | `PLC_PRG.setpoint`, `PLC_PRG.perfil_txt` |
| START / STOP / Nuevo lote | `GVL_SECUENCIA` (botones en modo pulsar) |
| Tiempos: planta, lote, secado efectivo, parado | `PLC_PRG.t_planta_h`, `t_lote_h`, `t_secado_efectivo_h`, `t_parado_h` |
| Hora y día/noche, temperatura ambiente | `PLC_PRG.hora_txt`, `periodo_txt`, `T_ambiente` |
| Estado físico de la planta / enlace FluidSIM | `PLC_PRG.estado_planta_txt`, `PLC_PRG.fluidsim_txt` |
| Estado de la máquina / alarma / comunicación | `GVL_SECUENCIA.estado_txt`, `SECUENCIA.txt_alarma`, `SECUENCIA.txt_comm` |
| Aviso de datos vencidos | `PLC_PRG.txt_datos`, `PLC_PRG.datos_validos` |
| Piloto «Bandeja adentro» | `SECUENCIA.piloto_bandeja_adentro` |

El perfil y el caudal se aceptan solo en REPOSO y quedan fijos durante el lote. La
tendencia de la HMI muestra una ventana de tiempo móvil; la historia completa de cada lote
la grafica el servidor de Python al terminar (`python/grafica_lote.py`).

## Política de parada

| Situación | Resistencia | Ventilador | Planta en Python |
|---|---|---|---|
| PARO (STOP) | 0 de inmediato | Post-ventilación de 10 min de modelo si venía calentando, luego 0 | Sigue: se enfría hacia el ambiente |
| FALLA (cilindro, finales de carrera, FluidSIM) | 0 de inmediato | Post-ventilación de 10 min, luego 0 | Sigue |
| FALLA de comunicación con Python | La apaga Python (política local) | Post-ventilación de Python, luego 0 | Sigue |
| EMERGENCIA | 0 | 0 | Sigue; el corte térmico de 90 °C protege la resistencia |
| FIN DE SECADO | 0 | 0 | Sigue |

Es una función de software demostrada, no una certificación de seguridad funcional.

## Ensayos de falla F1–F5

Se registran con `python modbus_server.py --hora-inicio 8 --log-csv resultados/ensayos/<ensayo>.csv`,
con el lote ya caliente. Resultados en `python/resultados/ensayos/`.

| Ensayo | Cómo se provoca | Qué se observa | Recuperación (F4) |
|---|---|---|---|
| F1 | CODESYS: *Debug → Stop* | A los 5 s Python aplica su política local (resistencia en 0, post-ventilación); la planta sigue | *Debug → Start*; START reconoce y START reanuda |
| F2 | Detener la simulación de FluidSIM | FALLA 5 en ~1 s, resistencia en 0, `fluidsim_estado` = 3 | Reanudar FluidSIM; START reconoce, los cilindros se resincronizan y START reanuda |
| F3 | STOP en la HMI | PARO con post-ventilación; el tiempo de secado se detiene y el tiempo parado crece | START reanuda |
| F5 | Cerrar `modbus_server.py` | Heartbeat congelado → FALLA 1 «Sin comunicación con Python» en 4 s, salidas en 0 | Arrancar de nuevo Python |

## Notas técnicas

- **Orden de palabras del REAL.** Python envía la palabra alta primero; en CODESYS (Windows,
  little-endian) el `UNION` se arma con la palabra **baja** en `words[0]`.
- **Canales de un registro.** El maestro Modbus de SP9 no actualiza bien canales FC03 de
  longitud 2; por eso cada REAL usa dos canales de longitud 1.
- **Heartbeat.** Se compara con el valor anterior y **después** se actualiza el anterior; si
  no cambia en 4 s, `comm_error` = TRUE y todas las salidas van a valor seguro.
- **Una sola instancia del servidor.** Antes de arrancar, `netstat -an | findstr 5020` no debe
  mostrar otro proceso escuchando.
- **HMI.** Las lámparas solo aceptan BOOL (por eso existen auxiliares como `heater_on`); un
  valor numérico dentro de un texto va en *Variables de texto* con formato `%.1f`.

# /codesys

Controlador de supervisión en CODESYS V3.5 SP9 (runtime CODESYS Control Win
V3): cliente Modbus TCP de la planta Python, lógica de supervisión, alarmas
y HMI. Estado al 6 oct 2026.

## Archivos

| Archivo | Qué es |
|---|---|
| `PLC_PRG_v3.st` | **Programa vigente** (5 oct 2026). RUN/HOLD, ventilador y consigna de caudal (`fan_speed_pct`), inversión del aire cada 6 h (`flow_dir_cmd`, piloto `aire_invertido`), parada por humedad (promedio ≤ 11 % y capa más húmeda ≤ 12 % b.h.) con `fin_secado` enclavado y `reset_lote`, watchdog `heartbeat`/`comm_error`, selección `lazo_local` (termostato en Python en la demo acelerada / en el PLC a tiempo real). Pendiente de cargarlo en el proyecto. |
| `PLC_PRG_v2.st` | Versión anterior (4 oct 2026), sin caudal variable. Histórico. |
| `archivo_codesys/SecadoCafe_ModbusV1.project` | Proyecto CODESYS SP9 (HMI, canales Modbus, IO Mapping). Se actualiza al cargar v3. |
| `ModbusPhytoon.project` | Proyecto v0 (SP15, 10 sept 2026), ya no instalado. Histórico. |
| `comunicacion_modbus.md` | Guía paso a paso del cliente Modbus en CODESYS, código ST y **sección 0 con los errores que más tiempo costaron** (léela si algo deja de funcionar). Secciones 7–8: lazo térmico local y caudal variable. Es una bitácora: conserva el historial de cada cambio. |
| `evidencia_*.png`, `ConcexionOPC.png` | Evidencias de comunicación, HMI, watchdog y prueba OPC con FluidSIM. |

Mapa de registros y variables: `../docs/tabla_variables.md`.

## Cómo se prueba

1. `cd python` y `python modbus_server.py` (modelo, factor 540, puerto 5020).
2. En CODESYS: el cliente Modbus apunta a `127.0.0.1:5020`; iniciar sesión y
   RUN.
3. Verificación a tiempo real (una vez, ~60 min):
   `python modbus_server.py --factor-aceleracion 1 --lazo-termico plc` y
   `lazo_local := FALSE` en el PLC; comparar T_process y energía con
   `python/control_supervisado.py`.

## Pendiente (6 oct 2026)

- Cargar `PLC_PRG_v3` y crear los canales de caudal (dir. 20 escritura,
  22–23 lectura) en el IO Mapping.
- HMI final: caudal, `aire_invertido`, `fin_secado`, botón "Nuevo lote",
  revisión de ergonomía visual; lámpara "Planta en funcionamiento" que
  reaccione a `comm_error`.
- "Nuevo lote" debe reiniciar también la planta en Python (falta un registro
  de reinicio en `modbus_server.py`).
- Verificación a tiempo real CODESYS vs. réplica (arriba).
- Compuerta de inversión en FluidSIM vía OPC (ver `../fluidsim/README.md`).

---

# Historial (bitácora hasta el 24 sept 2026)

## Comunicación con Python

`comunicacion_modbus.md` — mapa de registros Modbus TCP, procedimiento
paso a paso para configurar el cliente/master en CODESYS (device tree,
canales, mapeo IO), código ST, el HMI, y **una sección 0 con seis
errores/hallazgos que costaron más tiempo** (versión de CODESYS vs.
runtime, orden de palabras del REAL, procesos Python duplicados, tipo
BOOL requerido por la Lámpara, dónde va la variable de texto en vivo
del Campo de texto, y un bug del driver Modbus de SP9 con canales de
más de 1 registro) — léela antes de tocar nada si algo deja de
funcionar. Ver `python/modbus_server.py` para el lado servidor. Se
eligió Modbus TCP en vez de OPC UA como interfaz de esta capa
(arquitectura modular de la guía vigente, sección 3): CODESYS =
cliente/master, Python = servidor/slave.

`SecadoCafe_ModbusV1.project` — **proyecto CODESYS vigente**, en
**CODESYS V3.5 SP9** (no SP15 — SP15 se desinstaló el 15 sept 2026 por
problemas con OPC). Tiene las 6 variables de v1 funcionando end-to-end
(`T_process`, `RH_ambient`, `heater_cmd`, `fan_cmd`, `plant_mode`,
`safety_ok`), verificadas en el Watch de CODESYS, y desde el 23 sept
2026 además `M_coffee` y `tiempo_proceso_h` (ver
`python/planta_secado.py`), con HMI visual propia funcionando
(`T_process`, humedad del café decreciendo desde la humedad inicial, y
tiempo de secado en vivo — coincidentes con la consola de Python) y un
Trend ya legible en el eje X (antes mostraba fecha/hora del sistema en
cada muestra y se veía "escalonado"). **✅ Ya subido al repositorio
(24 sept 2026)**, junto con sus archivos de sesión de CODESYS
(`.opt`, `.~u` — dependencias propias del entorno de trabajo del
proyecto). **⚠️ Ubicación:** quedó en `codesys/archivo_codesys/
SecadoCafe_ModbusV1.project`, no directo en `codesys/` como lo
referencian este documento y `comunicacion_modbus.md` — decidir si se
mueve un nivel arriba (para que coincida con las referencias) o se
actualizan las referencias a la nueva ruta.

Al verificar esta versión se depuraron en vivo tres fallos de
configuración típicos de CODESYS (quedan documentados aquí para no
repetirlos):
- Desplazamiento (`Desplazamiento`) de un canal Modbus copiado mal al
  duplicar un canal existente para crear uno nuevo — revisar siempre
  la tabla completa de offsets contra el mapa de registros si un valor
  se queda en 0 sin motivo aparente.
- Canales creados en el árbol de dispositivos pero sin asignar en el
  **IO Mapping** (columna "Variable"/"Asignación" vacía) — el canal
  Modbus y la variable ST del programa son dos pasos distintos, es
  fácil crear uno y olvidar el otro.
- Campos de texto del HMI enlazados a la variable equivocada (rastro
  de copiar el campo de texto del Setpoint para crear los nuevos
  campos, sin cambiar la propiedad "Variables de texto") — si un
  campo nuevo siempre muestra el mismo valor que otro ya existente,
  revisar esa propiedad primero.

`ModbusPhytoon.project` — proyecto histórico de v0 (SP15, ya no
instalado en este equipo). Tiene la HMI original (`T_process` + piloto
del calentador) y es la fuente de `evidencia_hmi_modbus.png`. Se deja
como referencia, no es el proyecto activo.

**Evidencia:** `evidencia_hmi_modbus.png` — captura del HMI de CODESYS
(`T_process` en vivo + piloto del calentador) junto a la consola de
`modbus_server.py` mostrando el mismo valor en el mismo instante
(10 sept 2026, v0/SP15). **Pendiente:** captura equivalente para
v1/SP9 con las 6+2 variables y el Trend corregido.

## Integración con FluidSIM (OPC)

Se probó hacer correr, sobre el mismo runtime **CODESYS Control Win
V3**, Modbus TCP (cliente CODESYS ↔ servidor `modbus_server.py`) y OPC
(hacia FluidSIM) **al mismo tiempo**: un circuito mínimo en FluidSIM
(botón → cilindro, accionado desde la programación de CODESYS)
corriendo en paralelo con la planta Python vía Modbus, sin conflictos
de puerto ni de tiempos entre ambos protocolos. **Decisión: GO para
FluidSIM vía OPC.** Queda pendiente documentar el detalle de esta
conexión (versión/tipo de OPC, configuración del lado FluidSIM) en un
archivo aparte — hoy solo consta esta nota y `ConcexionOPC.png`.

Entregable semana 4: prueba mínima de comunicación — **verificada
end-to-end el 9-10 sept 2026 (v0)** y **re-verificada el 15 sept 2026
con las 6 variables de v1 en SP9** — checklist completo en
`comunicacion_modbus.md`, sección 4.
Entregable semana 7 (cierre del corte): integración CODESYS↔Python
demostrada con HMI real — **✅ verificada el 23 sept 2026**. Decisión
GO/NO-GO de FluidSIM — **✅ GO**.

## Pérdida de comunicación — watchdog en ambos sentidos (24 sept 2026)

**✅ Resuelto y verificado con CODESYS real.** Se agregó el registro
`heartbeat` (dirección 12) del lado Python: un contador que
`modbus_server.py` incrementa en cada ciclo, publicado siempre. Del
lado CODESYS, `comm_error` compara `heartbeat_actual` contra el ciclo
anterior con un `TON`, y se integró directo en la condición de RUN del
control bang-bang (no como override aparte) para que `heater_cmd`/
`fan_cmd` se fuercen a 0 de verdad, no solo la alarma visual. Detalle
completo, código ST y los dos bugs encontrados en el camino (orden de
comparación del heartbeat, orden de la lógica de override) en
`comunicacion_modbus.md`, sección 2.3 y puntos 7-8 de la sección 0.
Evidencia: `evidencia_watchdog_comm_on.png` / `evidencia_watchdog_comm_off.png`.

Con esto, el watchdog de pérdida de comunicación queda cerrado en los
dos sentidos: Python detecta si CODESYS deja de escribir (`safety_ok`,
ya desde el 14 sept), y CODESYS detecta si Python se cae (`comm_error`,
hoy).

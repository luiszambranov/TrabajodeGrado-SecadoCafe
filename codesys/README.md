# /codesys

Proyecto CODESYS: lógica de control, máquina de estados y HMI.

Contenido esperado:
- Máquina de estados del proceso de secado.
- Lógica de control (PID).
- HMI con tendencias, alarmas y estado.
- Configuración de comunicación (Modbus TCP u otra interfaz) con Python y FluidSIM.

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
`safety_ok`), verificadas en el Watch de CODESYS. Todavía sin HMI
visual propia (ver `comunicacion_modbus.md`, sección 5).

`ModbusPhytoon.project` — proyecto histórico de v0 (SP15, ya no
instalado en este equipo). Tiene la HMI original (`T_process` + piloto
del calentador) y es la fuente de `evidencia_hmi_modbus.png`. Se deja
como referencia, no es el proyecto activo.

**Evidencia:** `evidencia_hmi_modbus.png` — captura del HMI de CODESYS
(`T_process` en vivo + piloto del calentador) junto a la consola de
`modbus_server.py` mostrando el mismo valor en el mismo instante
(10 sept 2026, v0/SP15). **Pendiente:** captura equivalente para
v1/SP9 con las 6 variables.

Entregable semana 4: prueba mínima de comunicación — **verificada
end-to-end el 9-10 sept 2026 (v0)** y **re-verificada el 15 sept 2026
con las 6 variables de v1 en SP9** — checklist completo en
`comunicacion_modbus.md`, sección 4.

**Pendiente (en orden, sección 6 de `comunicacion_modbus.md`):** HMI
visual para v1, evidencia nueva, prueba del watchdog con CODESYS real,
timeout del canal master, y conectar `modelo_secado.py` real en vez de
la planta de juguete.

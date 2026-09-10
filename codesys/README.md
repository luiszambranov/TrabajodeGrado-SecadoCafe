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
canales, mapeo IO), código ST, y **una sección 0 con los tres errores
que costaron más tiempo la primera vez** (versión de CODESYS vs.
runtime, orden de palabras del REAL, procesos Python duplicados) — léela
antes de tocar nada si algo deja de funcionar. Ver `python/modbus_server.py`
para el lado servidor. Se eligió Modbus TCP en vez de OPC UA como
interfaz de esta capa (arquitectura modular de la guía vigente, sección
3): CODESYS = cliente/master, Python = servidor/slave.

`ModbusPhytoon.project` — el proyecto CODESYS que ya funciona
end-to-end. Ábrelo con **CODESYS V3.5 SP15 Patch 4** (no SP9 — ver
`comunicacion_modbus.md` sección 0.1 sobre por qué la versión importa).

Entregable semana 4: prueba mínima de comunicación — **verificada
end-to-end el 9-10 sept 2026**: `T_process` e intercambio de
`heater_cmd` confirmados en ambos sentidos entre Python y CODESYS
(checklist en `comunicacion_modbus.md`, sección 4). Pendiente: dejar
evidencia (captura/video) en el repo, comportamiento ante pérdida de
comunicación, y el plan de la sección 5 del mismo documento (HMI +
más actuadores) para la próxima demo.

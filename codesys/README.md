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
canales, mapeo IO), código ST, el HMI, y **una sección 0 con cinco
errores que costaron más tiempo la primera vez** (versión de CODESYS vs.
runtime, orden de palabras del REAL, procesos Python duplicados, tipo
BOOL requerido por la Lámpara, y dónde va la variable de texto en vivo
del Campo de texto) — léela antes de tocar nada si algo deja de
funcionar. Ver `python/modbus_server.py` para el lado servidor. Se
eligió Modbus TCP en vez de OPC UA como interfaz de esta capa
(arquitectura modular de la guía vigente, sección 3): CODESYS =
cliente/master, Python = servidor/slave.

`ModbusPhytoon.project` — el proyecto CODESYS que ya funciona
end-to-end, incluido el HMI. Ábrelo con **CODESYS V3.5 SP15 Patch 4**
(no SP9 — ver `comunicacion_modbus.md` sección 0.1 sobre por qué la
versión importa).

**Evidencia:** `evidencia_hmi_modbus.png` — captura del HMI de CODESYS
(`T_process` en vivo + piloto del calentador) junto a la consola de
`modbus_server.py` mostrando el mismo valor en el mismo instante
(10 sept 2026).

Entregable semana 4: prueba mínima de comunicación — **verificada
end-to-end el 9-10 sept 2026, con HMI**: `T_process` e intercambio de
`heater_cmd` confirmados en ambos sentidos entre Python y CODESYS, y
mostrados en un HMI mínimo en CODESYS (valor numérico + piloto del
calentador) — checklist en `comunicacion_modbus.md`, sección 4.
Pendiente: comportamiento ante pérdida de comunicación, y el plan de
la sección 6 del mismo documento (más actuadores/variables) para la
próxima demo.

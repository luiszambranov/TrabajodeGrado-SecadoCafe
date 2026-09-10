"""
modbus_server.py
=================

Servidor Modbus TCP (esclavo/slave) en Python — v0: prueba mínima de
comunicación Python <-> CODESYS.
Trabajo de grado - Sistema de supervisión digital para el secado de café.
(ver Guia_vigente_TG_Secado_Cafe_Pardo_Zambrano.pdf, sección 3, "Prueba
mínima del corte").

Alcance de esta versión (v0)
-----------------------------
El objetivo de este script NO es simular el secado de café todavía (eso
lo hace ``modelo_secado.py``). El objetivo es demostrar, con la menor
complejidad posible, que la comunicación Modbus TCP entre Python y
CODESYS funciona en ambos sentidos, tal como lo exige la guía vigente:

    1. Un cambio generado en Python debe verse en CODESYS.
    2. Un comando emitido desde CODESYS debe volver a Python y modificar
       de manera observable el estado de la "planta" simulada.

Para eso, este script implementa una planta térmica de juguete (primer
orden, sin física real del café todavía): una variable ``T_process`` que
sube si ``heater_cmd = 1`` y se enfría hacia la temperatura ambiente si
``heater_cmd = 0``. Cuando se integre con ``modelo_secado.py`` en una
siguiente iteración, ``T_process`` pasará a alimentarse del modelo real
de cinética de secado en vez de esta dinámica de juguete.

Arquitectura y por qué Python es el servidor (slave)
------------------------------------------------------
Según la tabla de capas de la guía vigente, CODESYS es el
**Controlador** (estados, lógica/PID, alarmas, HMI) y Python es la
**Planta** (dinámica térmica) + **Análisis**. Se mantiene ese reparto de
responsabilidades usando Modbus TCP como interfaz:

    - Python  = servidor Modbus TCP (slave): publica el estado de la
      planta simulada en registros, y expone registros de escritura
      para los comandos de control.
    - CODESYS = cliente Modbus TCP (master): sondea esos registros en
      su ciclo de tarea y escribe los comandos, exactamente como lo
      haría contra un sensor/actuador Modbus real. Así, cuando se pase
      de la planta simulada a la secadora física, el lado CODESYS casi
      no cambia (solo se re-apunta la IP del cliente).

Mapa de registros Modbus (holding registers, function code 03/06/16)
----------------------------------------------------------------------
    Dirección   Tag           Tipo              Unidad   Origen -> Destino
    ---------   -----------   ---------------   ------   -----------------
    0-1         T_process     REAL (float32)    °C       Python -> CODESYS (solo lectura desde CODESYS)
    2           heater_cmd    WORD (0 o 1)      -        CODESYS -> Python (Python solo lee)

    Direcciones 3-7 quedan reservadas para la siguiente iteración
    (RH_ambient, M_coffee, fan_cmd, safety_ok — ver tabla completa de
    señales de la guía vigente, sección 3.1).

El float32 se codifica como dos registros de 16 bits en orden de palabra
big-endian ("word swap" = NO, orden natural): registro alto primero,
registro bajo después. CODESYS en Windows guarda un REAL en memoria en
orden little-endian a nivel de palabra, así que del lado ST hay que
armar el UNION con la palabra BAJA primero (`words[0] := T_process_lo`).
Ver codesys/comunicacion_modbus.md, sección 0, para este y otros dos
detalles (versión de CODESYS vs. runtime, procesos duplicados) que
costaron la mayor parte del tiempo de depuración la primera vez que se
hizo funcionar esto.

Cómo correrlo
--------------
    pip install -r requirements.txt
    python modbus_server.py                  # 127.0.0.1:502 (puede requerir admin en Windows)
    python modbus_server.py --port 5020       # alternativa sin privilegios

IMPORTANTE: no dejes más de una instancia corriendo a la vez (verifica
con ``netstat -an | findstr 5020`` en Windows antes de arrancar otra) —
varias instancias compitiendo por el mismo puerto causaron horas de
depuración confusa por conexiones "zombie".

Con el servidor corriendo, la consola debe imprimir cada segundo el valor
de T_process y el heater_cmd recibido — esa salida de consola ES la
evidencia mínima de que la planta está viva, incluso antes de conectar
CODESYS.
"""

from __future__ import annotations

import argparse
import logging
import struct
import threading
import time

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import StartTcpServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("modbus_server")

# --- Mapa de registros (ver docstring del módulo) --------------------------
REG_T_PROCESS = 0    # 2 registros: float32
REG_HEATER_CMD = 2   # 1 registro: 0/1
NUM_HOLDING_REGS = 16  # margen para las variables de la siguiente iteración

# --- Parámetros de la planta de juguete (v0, sin física real todavía) ------
T_AMBIENTE_C = 25.0   # temperatura ambiente de referencia [°C]
T_MAX_C = 90.0        # límite superior de seguridad de la planta de juguete [°C]
K_CALENTAMIENTO = 1.5  # ganancia de calentamiento cuando heater_cmd=1 [°C/s aprox.]
K_ENFRIAMIENTO = 0.05  # ganancia de enfriamiento hacia T_AMBIENTE_C [1/s aprox.]
PERIODO_ACTUALIZACION_S = 1.0  # frecuencia de actualización de la planta


def float_to_registers(value: float) -> list[int]:
    """Codifica un float32 IEEE754 como [registro_alto, registro_bajo]."""
    packed = struct.pack(">f", value)
    high, low = struct.unpack(">HH", packed)
    return [high, low]


def registers_to_float(regs: list[int]) -> float:
    """Decodifica [registro_alto, registro_bajo] a float32 IEEE754."""
    packed = struct.pack(">HH", regs[0], regs[1])
    return struct.unpack(">f", packed)[0]


def bucle_planta(slave_ctx: ModbusSlaveContext, stop_event: threading.Event) -> None:
    """Actualiza T_process cada PERIODO_ACTUALIZACION_S segundos.

    Dinámica de primer orden de juguete (NO es el modelo de secado):
        dT/dt = K_CALENTAMIENTO * heater_cmd - K_ENFRIAMIENTO * (T - T_AMBIENTE_C)

    heater_cmd se lee de los registros Modbus, es decir, de lo que CODESYS
    haya escrito la última vez. Este es el punto exacto donde, en la
    siguiente iteración, se reemplaza la dinámica de juguete por una
    llamada al modelo real de ``modelo_secado.py``.
    """
    t_process = T_AMBIENTE_C
    while not stop_event.is_set():
        heater_cmd = slave_ctx.getValues(3, REG_HEATER_CMD, count=1)[0]

        t_process += PERIODO_ACTUALIZACION_S * (
            K_CALENTAMIENTO * heater_cmd - K_ENFRIAMIENTO * (t_process - T_AMBIENTE_C)
        )
        t_process = max(T_AMBIENTE_C, min(t_process, T_MAX_C))

        slave_ctx.setValues(3, REG_T_PROCESS, float_to_registers(t_process))

        log.info("T_process=%6.2f degC | heater_cmd=%s", t_process, heater_cmd)
        stop_event.wait(PERIODO_ACTUALIZACION_S)


def construir_contexto() -> ModbusServerContext:
    hr_block = ModbusSequentialDataBlock(0, [0] * NUM_HOLDING_REGS)
    slave_ctx = ModbusSlaveContext(hr=hr_block, zero_mode=True)
    # T_process inicial = temperatura ambiente, heater_cmd inicial = apagado
    slave_ctx.setValues(3, REG_T_PROCESS, float_to_registers(T_AMBIENTE_C))
    slave_ctx.setValues(3, REG_HEATER_CMD, [0])
    return ModbusServerContext(slaves=slave_ctx, single=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1", help="IP donde escucha el servidor (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=502, help="Puerto TCP (default: 502; usar 5020 si 502 requiere permisos de administrador)")
    args = parser.parse_args()

    context = construir_contexto()
    stop_event = threading.Event()

    hilo_planta = threading.Thread(
        target=bucle_planta,
        args=(context[0], stop_event),
        daemon=True,
    )
    hilo_planta.start()

    log.info("Servidor Modbus TCP escuchando en %s:%s", args.host, args.port)
    log.info("Mapa: holding[0-1]=T_process (float32, degC) | holding[2]=heater_cmd (0/1)")
    log.info("Presiona Ctrl+C para detener.")

    try:
        StartTcpServer(context=context, address=(args.host, args.port))
    except PermissionError:
        log.error(
            "Sin permisos para abrir el puerto %s. En Windows, corre la terminal como "
            "administrador o usa --port 5020.",
            args.port,
        )
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        hilo_planta.join(timeout=2)


if __name__ == "__main__":
    main()

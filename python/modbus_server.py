"""
modbus_server.py
=================

Servidor Modbus TCP (esclavo/slave) en Python — v1: interfaz modular
Python <-> CODESYS, con más variables y comportamiento ante pérdida de
comunicación.
Trabajo de grado - Sistema de supervisión digital para el secado de café.
(ver Guia_vigente_TG_Secado_Cafe_Pardo_Zambrano.pdf, sección 3,
"Arquitectura modular objetivo" y "Prueba mínima del corte").

Qué cambió respecto a v0
-------------------------
v0 demostró que la comunicación Modbus TCP funciona en ambos sentidos
con una sola variable de proceso (T_process) y un solo comando
(heater_cmd), usando una planta de juguete cableada directo en el bucle
del servidor. Esta v1 dos cosas:

    1. Separa la planta detrás de una **interfaz modular** (clase
       ``Plant``, ver abajo): el bucle del servidor ya no conoce la
       física, solo llama ``plant.step(...)``. Así, cuando
       ``modelo_secado.py`` esté listo para conectarse, se agrega una
       clase ``ModeloSecadoPlant(Plant)`` nueva y se cambia una línea
       en ``main()`` — el mapa de registros y el lado CODESYS no
       cambian. Esto es exactamente el desacople controlador/planta
       que pide la sección 3 de la guía vigente.
    2. Amplía el mapa de registros con ``fan_cmd``, ``RH_ambient``,
       ``plant_mode`` y ``safety_ok`` (ver tabla abajo), y agrega el
       ítem que quedaba pendiente del checklist de la guía:
       comportamiento ante pérdida de comunicación (watchdog).

Sigue sin ser el modelo real de secado de café — eso lo hace
``modelo_secado.py`` — esta v1 sigue usando una planta de juguete
(``ToyPlant``), pero ahora una que cumple la interfaz que ``modelo_secado.py``
tendrá que implementar en la siguiente iteración.

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
    3           fan_cmd       WORD (0 o 1)      -        CODESYS -> Python (Python solo lee)
    4-5         RH_ambient    REAL (float32)    %        Python -> CODESYS (solo lectura desde CODESYS)
    6           plant_mode    WORD (0=RUN,      -        CODESYS -> Python, Python refleja el modo
                               1=HOLD)                    aplicado (bidireccional, ver sección "Modo").
    7           safety_ok     WORD (0 o 1)      -        Python -> CODESYS (1=comunicación sana,
                                                           0=watchdog activado / valor seguro aplicado)

    Direcciones 8-9 quedan reservadas para M_coffee (contenido de
    humedad del café), que todavía NO está implementado: requiere el
    modelo real de secado (``modelo_secado.py``) o el sensor físico
    (sección 6 de la guía vigente), ninguno de los dos conectado aún a
    este servidor. Direcciones 10-19 quedan libres para futuras
    variables.

Modo de planta (plant_mode) y valor seguro (safety_ok)
--------------------------------------------------------
CODESYS escribe ``plant_mode`` para indicarle a Python en qué modo
operar:

    - 0 = RUN: la planta responde normalmente a heater_cmd/fan_cmd.
    - 1 = HOLD: la planta ignora heater_cmd/fan_cmd (los trata como 0)
      y se limita a enfriarse/relajarse hacia el ambiente. Pensado para
      que CODESYS pueda forzar un estado seguro conocido sin tener que
      dejar de escribir en el registro.

Independientemente de lo que escriba CODESYS, el servidor tiene un
**watchdog**: si no recibe ninguna escritura en heater_cmd, fan_cmd o
plant_mode durante más de ``WATCHDOG_TIMEOUT_S`` segundos, asume que la
comunicación con CODESYS se perdió (o que CODESYS está detenido) y:

    1. Fuerza heater_cmd y fan_cmd efectivos a 0 (valor seguro) para el
       cálculo de la planta, sin necesidad de que nadie los escriba.
    2. Publica ``safety_ok = 0`` para que CODESYS (o cualquier cliente
       Modbus) pueda mostrar una alarma de "comunicación perdida".

Este es el ítem que quedaba pendiente en el checklist de la guía
("Pérdida de comunicación con comportamiento definido"). Nota
importante: esto cubre el lado Python (qué hace la planta simulada si
deja de recibir comandos). Del lado CODESYS falta, aparte, configurar
el timeout propio del canal Modbus master (para que el HMI muestre el
canal en error si Python se cae) — ver comunicacion_modbus.md, sección
6, para ese pendiente específico.

El float32 se codifica como dos registros de 16 bits en orden de palabra
big-endian ("word swap" = NO, orden natural): registro alto primero,
registro bajo después. CODESYS en Windows guarda un REAL en memoria en
orden little-endian a nivel de palabra, así que del lado ST hay que
armar el UNION con la palabra BAJA primero (`words[0] := T_process_lo`).
Ver codesys/comunicacion_modbus.md, sección 0, para este y otros
detalles que costaron la mayor parte del tiempo de depuración la
primera vez que se hizo funcionar esto.

Cómo correrlo
--------------
    pip install -r requirements.txt
    python modbus_server.py                  # 127.0.0.1:502 (puede requerir admin en Windows)
    python modbus_server.py --port 5020       # alternativa sin privilegios

IMPORTANTE: no dejes más de una instancia corriendo a la vez (verifica
con ``netstat -an | findstr 5020`` en Windows antes de arrancar otra) —
varias instancias compitiendo por el mismo puerto causaron horas de
depuración confusa por conexiones "zombie".

Con el servidor corriendo, la consola debe imprimir cada segundo el
estado completo de la planta (T_process, RH_ambient, heater_cmd,
fan_cmd, plant_mode, safety_ok) — esa salida de consola ES la evidencia
mínima de que la planta está viva, incluso antes de conectar CODESYS.
"""

from __future__ import annotations

import abc
import argparse
import logging
import struct
import threading
import time
from dataclasses import dataclass

from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import StartTcpServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("modbus_server")

# --- Mapa de registros (ver docstring del módulo) --------------------------
REG_T_PROCESS = 0     # 2 registros: float32
REG_HEATER_CMD = 2    # 1 registro: 0/1
REG_FAN_CMD = 3       # 1 registro: 0/1
REG_RH_AMBIENT = 4    # 2 registros: float32
REG_PLANT_MODE = 6    # 1 registro: 0=RUN, 1=HOLD
REG_SAFETY_OK = 7     # 1 registro: 0/1 (publicado por Python)
REG_M_COFFEE = 8      # 2 registros: float32 (v2 -- ver planta_secado.ModeloSecadoPlant)
NUM_HOLDING_REGS = 20  # margen para variables futuras

# Direcciones que, al ser escritas por el cliente Modbus (CODESYS), cuentan
# como "señal de vida" para el watchdog de comunicación.
ACTUATOR_ADDRESSES = frozenset({REG_HEATER_CMD, REG_FAN_CMD, REG_PLANT_MODE})

PLANT_MODE_RUN = 0
PLANT_MODE_HOLD = 1

WATCHDOG_TIMEOUT_S = 5.0  # sin escrituras de CODESYS durante este tiempo -> comm_lost


def float_to_registers(value: float) -> list[int]:
    """Codifica un float32 IEEE754 como [registro_alto, registro_bajo]."""
    packed = struct.pack(">f", value)
    high, low = struct.unpack(">HH", packed)
    return [high, low]


def registers_to_float(regs: list[int]) -> float:
    """Decodifica [registro_alto, registro_bajo] a float32 IEEE754."""
    packed = struct.pack(">HH", regs[0], regs[1])
    return struct.unpack(">f", packed)[0]


class WatchedDataBlock(ModbusSequentialDataBlock):
    """Bloque de holding registers que registra CUÁNDO fue la última vez
    que el cliente Modbus (CODESYS) escribió en una dirección de actuador.

    Esto es lo que le permite al bucle de la planta implementar el
    watchdog de pérdida de comunicación sin depender de que CODESYS
    "avise" de alguna forma especial: cualquier escritura normal de
    heater_cmd/fan_cmd/plant_mode ya cuenta como señal de vida.
    """

    def __init__(self, address: int, values: list[int]) -> None:
        super().__init__(address, values)
        self.last_actuator_write_ts = time.time()
        self._lock = threading.Lock()

    def setValues(self, address: int, values) -> None:  # noqa: N802 (nombre exigido por pymodbus)
        super().setValues(address, values)
        # zero_mode=True en el slave context => `address` ya viene 0-based,
        # igual que nuestras constantes REG_*.
        touched = set(range(address, address + (len(values) if hasattr(values, "__len__") else 1)))
        if touched & ACTUATOR_ADDRESSES:
            with self._lock:
                self.last_actuator_write_ts = time.time()

    def seconds_since_last_actuator_write(self) -> float:
        with self._lock:
            return time.time() - self.last_actuator_write_ts


# --- Interfaz modular de planta ---------------------------------------------
@dataclass
class PlantInputs:
    """Comandos que llegan desde CODESYS, ya resueltos por el watchdog
    (es decir: si hay pérdida de comunicación, heater_cmd/fan_cmd ya
    vienen forzados a 0 antes de llegar aquí)."""

    heater_cmd: int
    fan_cmd: int
    plant_mode: int
    comm_lost: bool


@dataclass
class PlantOutputs:
    """Variables de proceso que la planta publica hacia CODESYS."""

    t_process_c: float
    rh_ambient_pct: float
    m_coffee_pct: float | None = None
    # M_coffee (contenido de humedad del cafe, % b.h.) -- direcciones
    # 8-9. Solo lo publican plantas que modelan la cinetica real del
    # cafe (ver planta_secado.ModeloSecadoPlant); ToyPlant lo deja en
    # None y el registro Modbus simplemente no se actualiza (ver
    # bucle_planta).


class Plant(abc.ABC):
    """Interfaz modular planta <-> servidor Modbus.

    Esta es la pieza central del desacople que pide la sección 3 de la
    guía vigente ("Arquitectura modular objetivo"): el bucle del
    servidor Modbus (``bucle_planta``) solo conoce esta interfaz, nunca
    la física concreta. Eso permite:

        - Seguir usando ``ToyPlant`` (dinámica de juguete) para pruebas
          rápidas de comunicación, como en v0.
        - Cambiar a una implementación respaldada por
          ``modelo_secado.py`` (cinética real de secado + dinámica
          térmica) sin tocar el mapa de registros ni el lado CODESYS.
        - Más adelante, cambiar a una implementación que en vez de
          calcular la física lea sensores reales de la secadora física,
          de nuevo sin tocar CODESYS (ver tabla de capas, sección 3 de
          la guía: "Simulación" vs. "Planta real" son la misma fila de
          Controlador/Interfaz).

    Cualquier planta nueva solo necesita implementar ``step()``.
    """

    @abc.abstractmethod
    def step(self, dt_s: float, inputs: PlantInputs) -> PlantOutputs:
        """Avanza la planta ``dt_s`` segundos dados los comandos actuales
        y devuelve las variables de proceso resultantes."""
        raise NotImplementedError


class ToyPlant(Plant):
    """Planta de juguete (primer orden, sin física real de café todavía).

    T_process sube si heater_cmd=1 y se enfría hacia la temperatura
    ambiente si heater_cmd=0; fan_cmd acelera el enfriamiento. RH_ambient
    solo oscila de forma simple alrededor de un valor nominal — todavía
    no representa el clima real de Chinchiná (eso vive en
    ``generador_ambiente.py`` y se conectará cuando se implemente
    ``ModeloSecadoPlant``).

    En modo HOLD (plant_mode=1), la planta ignora heater_cmd/fan_cmd
    (ya vienen forzados a 0 por ``PlantInputs`` de todas formas cuando
    hay comm_lost, pero HOLD es una orden explícita de CODESYS, no solo
    un efecto del watchdog).
    """

    T_AMBIENTE_C = 25.0     # temperatura ambiente de referencia [°C]
    T_MAX_C = 90.0          # límite superior de seguridad de la planta de juguete [°C]
    K_CALENTAMIENTO = 1.5   # ganancia de calentamiento cuando heater_cmd=1 [°C/s aprox.]
    K_ENFRIAMIENTO_BASE = 0.05   # ganancia de enfriamiento hacia T_AMBIENTE_C [1/s aprox.]
    K_ENFRIAMIENTO_FAN = 0.08    # ganancia adicional de enfriamiento cuando fan_cmd=1 [1/s aprox.]
    RH_NOMINAL_PCT = 55.0   # RH ambiente nominal de referencia [%]
    RH_AMPLITUD_PCT = 5.0   # amplitud de la oscilación simple [%]
    RH_PERIODO_S = 120.0    # periodo de la oscilación simple [s]

    def __init__(self) -> None:
        self._t_process = self.T_AMBIENTE_C
        self._t_acumulado_s = 0.0

    def step(self, dt_s: float, inputs: PlantInputs) -> PlantOutputs:
        self._t_acumulado_s += dt_s

        heater_cmd = 0 if inputs.plant_mode == PLANT_MODE_HOLD else inputs.heater_cmd
        fan_cmd = 0 if inputs.plant_mode == PLANT_MODE_HOLD else inputs.fan_cmd

        k_enfriamiento = self.K_ENFRIAMIENTO_BASE + (self.K_ENFRIAMIENTO_FAN if fan_cmd else 0.0)
        self._t_process += dt_s * (
            self.K_CALENTAMIENTO * heater_cmd - k_enfriamiento * (self._t_process - self.T_AMBIENTE_C)
        )
        self._t_process = max(self.T_AMBIENTE_C, min(self._t_process, self.T_MAX_C))

        # Oscilación simple, solo para tener algo con qué llenar el HMI;
        # NO es el generador climático real de generador_ambiente.py.
        fase = (2.0 * 3.141592653589793 * self._t_acumulado_s) / self.RH_PERIODO_S
        rh_ambient = self.RH_NOMINAL_PCT + self.RH_AMPLITUD_PCT * _sin_aprox(fase)

        return PlantOutputs(t_process_c=self._t_process, rh_ambient_pct=rh_ambient)


def _sin_aprox(x: float) -> float:
    """Seno vía math.sin — función separada solo para dejar explícito que
    es un placeholder de oscilación, no un modelo climático."""
    import math

    return math.sin(x)


def construir_contexto() -> tuple[ModbusServerContext, WatchedDataBlock]:
    hr_block = WatchedDataBlock(0, [0] * NUM_HOLDING_REGS)
    slave_ctx = ModbusSlaveContext(hr=hr_block, zero_mode=True)
    # Estado inicial: T_process/RH_ambient a valores de reposo, comandos
    # apagados, modo RUN, comunicación asumida sana hasta que el watchdog
    # diga lo contrario.
    slave_ctx.setValues(3, REG_T_PROCESS, float_to_registers(ToyPlant.T_AMBIENTE_C))
    slave_ctx.setValues(3, REG_HEATER_CMD, [0])
    slave_ctx.setValues(3, REG_FAN_CMD, [0])
    slave_ctx.setValues(3, REG_RH_AMBIENT, float_to_registers(ToyPlant.RH_NOMINAL_PCT))
    slave_ctx.setValues(3, REG_PLANT_MODE, [PLANT_MODE_RUN])
    slave_ctx.setValues(3, REG_SAFETY_OK, [1])
    # M_coffee: valor inicial 0.0 -- solo tiene significado real cuando
    # la planta es ModeloSecadoPlant (ver planta_secado.py); con
    # ToyPlant queda sin usar (nunca se sobreescribe, ver bucle_planta).
    slave_ctx.setValues(3, REG_M_COFFEE, float_to_registers(0.0))
    return ModbusServerContext(slaves=slave_ctx, single=True), hr_block


def bucle_planta(
    plant: Plant,
    slave_ctx: ModbusSlaveContext,
    watched_block: WatchedDataBlock,
    stop_event: threading.Event,
    periodo_s: float,
) -> None:
    """Lee comandos, aplica el watchdog de comunicación, avanza la planta
    (a través de la interfaz ``Plant``, ver más arriba) y publica el
    resultado — cada ``periodo_s`` segundos."""

    while not stop_event.is_set():
        heater_cmd_bruto = slave_ctx.getValues(3, REG_HEATER_CMD, count=1)[0]
        fan_cmd_bruto = slave_ctx.getValues(3, REG_FAN_CMD, count=1)[0]
        plant_mode = slave_ctx.getValues(3, REG_PLANT_MODE, count=1)[0]

        comm_lost = watched_block.seconds_since_last_actuator_write() > WATCHDOG_TIMEOUT_S
        heater_cmd = 0 if comm_lost else heater_cmd_bruto
        fan_cmd = 0 if comm_lost else fan_cmd_bruto

        outputs = plant.step(
            periodo_s,
            PlantInputs(heater_cmd=heater_cmd, fan_cmd=fan_cmd, plant_mode=plant_mode, comm_lost=comm_lost),
        )

        slave_ctx.setValues(3, REG_T_PROCESS, float_to_registers(outputs.t_process_c))
        slave_ctx.setValues(3, REG_RH_AMBIENT, float_to_registers(outputs.rh_ambient_pct))
        slave_ctx.setValues(3, REG_SAFETY_OK, [0 if comm_lost else 1])
        if outputs.m_coffee_pct is not None:
            slave_ctx.setValues(3, REG_M_COFFEE, float_to_registers(outputs.m_coffee_pct))

        estado = "COMM_LOST(valor seguro)" if comm_lost else "OK"
        m_coffee_str = f"{outputs.m_coffee_pct:5.1f}%" if outputs.m_coffee_pct is not None else "  n/a"
        log.info(
            "T_process=%6.2fC | RH_ambient=%5.1f%% | M_coffee=%s | heater_cmd=%s | fan_cmd=%s | "
            "plant_mode=%s | safety=%s",
            outputs.t_process_c,
            outputs.rh_ambient_pct,
            m_coffee_str,
            heater_cmd_bruto,
            fan_cmd_bruto,
            plant_mode,
            estado,
        )
        stop_event.wait(periodo_s)


def main() -> None:
    global WATCHDOG_TIMEOUT_S
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1", help="IP donde escucha el servidor (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=502, help="Puerto TCP (default: 502; usar 5020 si 502 requiere permisos de administrador)")
    parser.add_argument("--periodo", type=float, default=1.0, help="Periodo de actualización de la planta, en segundos (default: 1.0)")
    parser.add_argument(
        "--watchdog-timeout",
        type=float,
        default=WATCHDOG_TIMEOUT_S,
        help=f"Segundos sin escritura de CODESYS antes de forzar valor seguro (default: {WATCHDOG_TIMEOUT_S})",
    )
    parser.add_argument(
        "--plant",
        choices=["toy", "modelo"],
        default="toy",
        help=(
            "Planta a usar: 'toy' = planta de juguete (default, sin cambios de comportamiento). "
            "'modelo' = ModeloSecadoPlant (planta_secado.py), cinetica real + dinamica termica -- "
            "ESQUELETO v0, leer planta_secado.py antes de usarla para resultados o con CODESYS real."
        ),
    )
    parser.add_argument(
        "--factor-aceleracion",
        type=float,
        default=3600.0,
        help="Solo con --plant modelo: horas de modelo por segundo de reloj real (default: 3600.0, ver planta_secado.py)",
    )
    args = parser.parse_args()
    WATCHDOG_TIMEOUT_S = args.watchdog_timeout

    context, watched_block = construir_contexto()
    if args.plant == "modelo":
        # Import diferido: planta_secado.py importa de este modulo, asi
        # que se importa aqui (cuando main() corre, este modulo ya esta
        # completamente cargado) para evitar un import circular.
        from planta_secado import ModeloSecadoPlant, ParametrosModeloSecadoPlant

        plant: Plant = ModeloSecadoPlant(ParametrosModeloSecadoPlant(factor_aceleracion=args.factor_aceleracion))
        log.info(
            "Usando ModeloSecadoPlant (ESQUELETO v0, no calibrado) con factor_aceleracion=%.1f",
            args.factor_aceleracion,
        )
    else:
        plant: Plant = ToyPlant()
    stop_event = threading.Event()

    hilo_planta = threading.Thread(
        target=bucle_planta,
        args=(plant, context[0], watched_block, stop_event, args.periodo),
        daemon=True,
    )
    hilo_planta.start()

    log.info("Servidor Modbus TCP escuchando en %s:%s", args.host, args.port)
    log.info(
        "Mapa: hr[0-1]=T_process | hr[2]=heater_cmd | hr[3]=fan_cmd | "
        "hr[4-5]=RH_ambient | hr[6]=plant_mode | hr[7]=safety_ok | hr[8-9]=M_coffee (v2)"
    )
    log.info("Watchdog de comunicación: %.1f s sin escritura de actuadores => valor seguro.", WATCHDOG_TIMEOUT_S)
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

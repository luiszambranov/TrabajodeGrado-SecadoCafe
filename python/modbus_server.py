"""
modbus_server.py
=================

Servidor Modbus TCP (esclavo/slave) en Python — v1: interfaz modular
Python <-> CODESYS, con más variables y comportamiento ante pérdida de
comunicación.
Trabajo de grado - Sistema de supervisión digital para el secado de café.
(ver Guia_vigente_TG_Secado_Cafe_Pardo_Zambrano.pdf, sección 3,
"Arquitectura modular objetivo" y "Prueba mínima del corte").

Cambio del 21 oct 2026 (guía de cierre, R4): la planta NO se pausa
--------------------------------------------------------------------
Python representa la planta física, no una animación subordinada a
CODESYS. Mientras el servidor esté corriendo, el tiempo físico y las
ecuaciones avanzan SIEMPRE, con o sin CODESYS/FluidSIM:
- RUN: integra con los comandos vigentes y los límites de actuación.
- HOLD (REPOSO, PARO, FIN_SECADO, FALLA, EMERGENCIA en CODESYS):
  resistencia y ventilador apagados, pero la cámara y el café siguen
  evolucionando (enfriamiento hacia el ambiente, ciclo día/noche,
  secado residual por tiro natural; ver secador_electrico.py).
- Comunicación perdida: política de fallo LOCAL (planta_secado.py):
  resistencia apagada ya, post-ventilación y luego todo apagado. La
  física sigue; el ciclo no se bloquea esperando la red.
- Nuevo lote: reinicia humedad, tiempo del lote y energía, pero NO
  enfría la cámara.
Hasta el 20 oct 2026 el bucle hacía dt = 0 en HOLD (modelo congelado).
Relojes y estado publicados en los registros 27-39 (ver mapa).
Registro CSV por ciclo con ``--log-csv`` (evidencia de los ensayos F1-F5
y archivo de histórico del lote).

Estado anterior (6 oct 2026)
---------------------------
- La planta está detrás de una **interfaz modular** (clase ``Plant``):
  el bucle del servidor solo llama ``plant.step(...)``. La planta por
  defecto es ``ModeloSecadoPlant`` (``planta_secado.py``): secador
  eléctrico de 80 kg c.p.s. con resistencia de 6 kW, ventilador de
  caudal variable, lecho de 20 cm por capas (Thompson) y cinética de
  Roa-Cenicafé. ``ToyPlant`` (la planta de juguete de v0, 9-10 sept
  2026) queda solo para probar la comunicación (``--plant toy``).
- Mapa de 24 registros (0-23), tabla abajo. Resumen para el documento
  en ``docs/tabla_variables.md``.
- Pérdida de comunicación cubierta en los dos sentidos: watchdog de
  Python (``safety_ok``) y ``heartbeat`` para CODESYS.
- Lazo térmico local (corrección del 4 oct 2026, ver
  ``planta_secado.py``): con factor de aceleración alto el termostato
  del ducto corre en Python cada 1 s de modelo y CODESYS supervisa.

Historial: v0 (9-10 sept 2026) = una variable y un comando con planta de
juguete; v1 (14-15 sept) = interfaz ``Plant`` + watchdog; 23 sept =
primera planta física; 29 sept = modelo Roa + secador eléctrico; 4 oct =
lazo térmico local; 5 oct = caudal variable (registros 20-23).

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
      haría contra un sensor/actuador Modbus real. La interfaz facilita
      reutilizar la lógica de CODESYS con una planta real, pero NO
      sustituye la adaptación: adquisición, escalado y calibración de
      sensores, adaptación de actuadores y evaluación de seguridad
      (corregido 21 oct 2026; antes decía "solo se re-apunta la IP").

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

    8-9         M_coffee      REAL (float32)    % b.h.   Python -> CODESYS (v2, ver planta_secado.py)
    10-11       tiempo_proceso_h REAL (float32) h         Python -> CODESYS: horas de MODELO en RUN con
                                                           ventilador (secado + inversión + enfriamiento)
                                                           del lote actual. CODESYS lo usa para la
                                                           inversión cada 6 h y el enfriamiento.
    12          heartbeat     WORD (0-65535)    -        Python -> CODESYS (contador que se
                                                           incrementa cada ciclo del servidor;
                                                           ver "Señal de latido" más abajo)
    13-14       RH_process    REAL (float32)    %        Python -> CODESYS (desde 29 sept 2026,
                                                           HR del aire DENTRO de la cámara)
    15          flow_dir_cmd  WORD (0 o 1)      -        CODESYS -> Python (29 sept 2026): sentido
                                                           del aire en el lecho, 0=abajo->arriba,
                                                           1=invertido (arriba->abajo)
    18-19       heater_duty   REAL (float32)    %        Python -> CODESYS (4 oct 2026): fraccion
                                                           del ultimo ciclo con la resistencia
                                                           encendida (lazo termico local; ver
                                                           planta_secado.py, "CORRECCION 4 oct 2026")
    16-17       M_coffee_max  REAL (float32)    % b.h.   Python -> CODESYS (29 sept 2026): humedad
                                                           de la capa más húmeda del lecho

    20          fan_speed_pct WORD (0-100)      %        CODESYS -> Python (5 oct 2026): consigna de
                                                           caudal del ventilador (manipulada 2), % del
                                                           nominal (8 m3/min). 0 = no configurado ->
                                                           100 %; 1-29 se recorta a 30 % (mínimo).
    21          reset_lote_cmd WORD (0 o 1)     -        CODESYS -> Python (14 oct 2026): flanco 0->1
                                                           = "Nuevo lote". Python reinicia el lote
                                                           (humedad inicial, tiempo y energía a cero).
                                                           CODESYS lo mantiene en 1 unos segundos
                                                           (pulso) y luego vuelve a 0.
    22-23       caudal        REAL (float32)    m3/min   Python -> CODESYS (5 oct 2026): caudal real
                                                           aplicado (0 con el ventilador apagado)
    24-25       energia_kWh   REAL (float32)    kWh      Python -> CODESYS (14 oct 2026): energía
                                                           eléctrica acumulada del lote (resistencia
                                                           + ventilador). Vuelve a 0 con "Nuevo lote".
    26          setpoint_cmd  WORD (°C entero)  °C       CODESYS -> Python (19 oct 2026): consigna de
                                                           T_process que calcula el PLC según el perfil
                                                           térmico elegido en la HMI (REF 50, P1 45,
                                                           P2 55->35, P3 35->55). La usa el termostato
                                                           local. 0 = no configurado -> 50 °C.

    Relojes y estado (21 oct 2026), todos Python -> CODESYS, horas de MODELO:
    27-28       tiempo_lote_h   REAL  h      desde el último "Nuevo lote"; incluye paradas
    29-30       tiempo_secado_h REAL  h      horas con calentamiento permitido (secado efectivo)
    31-32       tiempo_parado_h REAL  h      tiempo_lote_h - tiempo_proceso_h (paro, falla, fin)
    33-34       tiempo_planta_h REAL  h      desde que arrancó el servidor; nunca se reinicia
    35          estado_planta   WORD  -      0=REPOSO, 1=SECANDO, 2=VENTILANDO (sin calor),
                                             3=POST-VENTILACION (comm perdida), 4=FALLA_COMM
    36-37       T_ambiente      REAL  °C     temperatura exterior (clima de Chinchiná)
    38-39       hora_dia        REAL  h      hora del día 0-24 del reloj de la planta (día/noche)
    40          fluidsim_estado WORD  -      CODESYS -> Python: salud del enlace OPC con FluidSIM
                                             (guía de cierre, ensayo F2). 0 = no informado
                                             (CODESYS sin el canal), 1 = FluidSIM vivo (pulso de
                                             vida en INPUT0.7), 2 = modo sin_fluidsim DECLARADO
                                             (actuadores emulados por el PLC), 3 = enlace caído.
                                             Con 3, Python marca los datos de actuación como no
                                             válidos: conserva el último sentido de aire válido
                                             (no inventa confirmaciones de posición) y lo registra.

    RH_ambient vs RH_process (separados el 29 sept 2026)
    ------------------------------------------------------
    - RH_ambient (4-5): HR del aire EXTERIOR (clima de Chinchiná,
      generador_ambiente.py). Condición de frontera.
    - RH_process (13-14): HR del aire DENTRO de la cámara, la que recibe
      el café y la que entra al modelo cinético (psicrometría: aire
      exterior calentado a T_process, dinamica_termica.rh_proceso).
    Hasta el 29 sept, ModeloSecadoPlant publicaba la HR de proceso en el
    registro RH_ambient (TODO anotado en planta_secado.py); ahora cada
    tag tiene un solo significado. ToyPlant no publica RH_process.
    Del lado CODESYS hay que agregar la lectura de 13-14 (ver
    codesys/comunicacion_modbus.md).

Señal de latido (heartbeat) y detección de caída del servidor
----------------------------------------------------------------
El watchdog descrito arriba cubre un solo sentido: qué hace la planta
Python si CODESYS deja de escribir. Falta el sentido contrario: cómo
se entera CODESYS de que el servidor Python (la planta) se cayó o se
quedó colgado, para poder mostrar una alarma y pasar a un estado
seguro del lado del PLC en vez de seguir mostrando en el HMI el
último valor leído como si nada hubiera pasado.

``heartbeat`` (registro 12) es un contador de 16 bits que el servidor
incrementa (con acarreo a 0) en CADA ciclo de ``bucle_planta``,
publicado siempre, incluso si hay ``comm_lost`` del otro sentido — es
una señal de "el proceso Python sigue vivo y su bucle sigue
corriendo", independiente del watchdog de actuadores.

Del lado CODESYS, la detección es simple y no depende de ninguna
función de diagnóstico específica del driver Modbus (que en SP9 ya
dio un bug real, ver comunicacion_modbus.md sección 0.6): basta con
leer ``heartbeat`` cada ciclo de tarea y compararlo con el valor del
ciclo anterior. Si el valor lleva más de un umbral de tiempo (p. ej.
3-5 s) sin cambiar, es porque el servidor Python dejó de escribir —
ya sea porque el proceso se cerró, o porque el canal Modbus master
perdió la conexión TCP — y ese es el momento de declarar
``comm_error`` y forzar un estado seguro en el PLC (más allá de lo
que el registro ``safety_ok`` diga, porque si el servidor está
caído, ``safety_ok`` tampoco se está actualizando). Ver
comunicacion_modbus.md para el código ST exacto de esta lógica.

Modo de planta (plant_mode) y valor seguro (safety_ok)
--------------------------------------------------------
CODESYS escribe ``plant_mode`` para indicarle a Python en qué modo
operar:

    - 0 = RUN: la planta responde normalmente a heater_cmd/fan_cmd.
    - 1 = HOLD: la planta ignora heater_cmd/fan_cmd (los trata como 0)
      y se enfría hacia el ambiente. La física NO se congela (21 oct
      2026): el tiempo, el clima y el café siguen evolucionando.

Independientemente de lo que escriba CODESYS, el servidor tiene un
**watchdog**: si no recibe ninguna escritura en heater_cmd, fan_cmd o
plant_mode durante más de ``WATCHDOG_TIMEOUT_S`` segundos, asume que la
comunicación con CODESYS se perdió (o que CODESYS está detenido) y:

    1. Aplica la política de fallo local (planta_secado.py): resistencia
       apagada de inmediato aunque haya una consigna vieja, ventilador en
       post-ventilación (``--post-ventilacion-min``) y luego apagado. La
       planta sigue integrando.
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
    python modbus_server.py      # = --plant modelo --factor-aceleracion 540 --port 5020
    python modbus_server.py --factor-aceleracion 1 --lazo-termico plc   # verificación a tiempo real
    python modbus_server.py --plant toy                                 # solo prueba de comunicación

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
REG_M_COFFEE = 8       # 2 registros: float32 (v2 -- ver planta_secado.ModeloSecadoPlant)
REG_TIEMPO_PROCESO = 10  # 2 registros: float32, horas de MODELO transcurridas (v2)
REG_HEARTBEAT = 12     # 1 registro: contador 0-65535, incrementa cada ciclo del servidor (v2)
REG_RH_PROCESS = 13    # 2 registros: float32, HR dentro de la cámara (29 sept 2026)
REG_FLOW_DIR_CMD = 15  # 1 registro: 0/1, sentido del aire en el lecho (CODESYS -> Python)
REG_M_COFFEE_MAX = 16  # 2 registros: float32, humedad de la capa más húmeda (% b.h.)
REG_HEATER_DUTY = 18   # 2 registros: float32, ciclo de trabajo de la resistencia [%] (4 oct 2026)
REG_FAN_SPEED_CMD = 20 # 1 registro: consigna de caudal 0-100 % (CODESYS -> Python, 5 oct 2026)
REG_RESET_LOTE_CMD = 21  # 1 registro: flanco 0->1 = nuevo lote (CODESYS -> Python, 14 oct 2026)
REG_CAUDAL = 22        # 2 registros: float32, caudal real [m3/min] (Python -> CODESYS, 5 oct 2026)
REG_ENERGIA = 24       # 2 registros: float32, energía eléctrica del lote [kWh] (Python -> CODESYS, 14 oct 2026)
REG_SETPOINT_CMD = 26  # 1 registro: consigna de T_process en °C enteros (CODESYS -> Python, 19 oct 2026)
# 21 oct 2026: relojes y estado de la planta (Python -> CODESYS)
REG_TIEMPO_LOTE = 27     # 2 registros: float32 [h de modelo] desde "Nuevo lote", incluye paradas
REG_TIEMPO_SECADO = 29   # 2 registros: float32 [h] con calentamiento permitido
REG_TIEMPO_PARADO = 31   # 2 registros: float32 [h] lote - proceso
REG_TIEMPO_PLANTA = 33   # 2 registros: float32 [h] desde que arrancó el servidor
REG_ESTADO_PLANTA = 35   # 1 registro: 0 REPOSO, 1 SECANDO, 2 VENTILANDO, 3 POST-VENT, 4 FALLA_COMM
REG_T_AMBIENTE = 36      # 2 registros: float32 [°C]
REG_HORA_DIA = 38        # 2 registros: float32 [h, 0-24]
REG_FLUIDSIM_ESTADO = 40 # 1 registro: 0 no informado, 1 vivo, 2 sin_fluidsim declarado, 3 caído (CODESYS -> Python)
NUM_HOLDING_REGS = 41    # 0-40 (21 oct 2026)
FLUIDSIM_TXT = {0: "no informado", 1: "vivo", 2: "SIN_FLUIDSIM (emulado)", 3: "CAIDO"}

HEARTBEAT_MAX = 0xFFFF  # 16 bits; el contador da la vuelta a 0 al llegar aquí

# Direcciones que, al ser escritas por el cliente Modbus (CODESYS), cuentan
# como "señal de vida" para el watchdog de comunicación.
ACTUATOR_ADDRESSES = frozenset({REG_HEATER_CMD, REG_FAN_CMD, REG_PLANT_MODE, REG_FLOW_DIR_CMD, REG_FAN_SPEED_CMD})

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
    flow_dir_cmd: int = 0  # 0 = aire de abajo hacia arriba, 1 = invertido
    fan_speed_pct: int = 0  # consigna de caudal 0-100 % (0 = no configurado -> 100 %)
    setpoint_c: float = 0.0  # consigna de T_process desde el PLC (0 = no configurado -> valor por defecto)
    fluidsim_estado: int = 0  # registro 40 (21 oct 2026): 0 no informado, 1 vivo, 2 emulado, 3 caído


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
    tiempo_proceso_h: float | None = None
    # Horas de MODELO transcurridas desde que arranco la planta (NO
    # segundos de reloj real -- ver factor_aceleracion en
    # planta_secado.py) -- direcciones 10-11. Pensado para mostrar
    # "tiempo de secado" en el HMI en vez de fecha/hora del sistema.
    # Mismo criterio que m_coffee_pct: None -> ToyPlant no lo publica.
    rh_process_pct: float | None = None
    m_coffee_max_pct: float | None = None
    heater_duty_pct: float | None = None
    caudal_m3_min: float | None = None
    energia_kwh: float | None = None
    # Energía eléctrica acumulada del lote [kWh] -- 24-25 (14 oct 2026). None -> ToyPlant.
    # Caudal real aplicado [m3/min] -- 22-23 (5 oct 2026). None -> ToyPlant.
    # Ciclo de trabajo de la resistencia en el ultimo ciclo [%] -- 18-19
    # (4 oct 2026, lazo termico local). None -> ToyPlant.
    # Humedad de la capa más húmeda del lecho [% b.h.] -- 16-17. None -> ToyPlant.
    # HR del aire DENTRO de la cámara [%] -- direcciones 13-14 (29 sept
    # 2026). rh_ambient_pct es SOLO la HR exterior. None -> ToyPlant.
    # --- 21 oct 2026: relojes, estado y variables para el registro CSV ---
    t_ambiente_c: float | None = None
    hora_dia_h: float | None = None
    t_planta_h: float | None = None
    t_lote_h: float | None = None
    t_secado_h: float | None = None
    t_parado_h: float | None = None
    estado_planta: int | None = None
    m_coffee_min_pct: float | None = None
    potencia_res_kw: float | None = None
    caudal_natural_m3_min: float | None = None
    setpoint_aplicado_c: float | None = None
    fan_cmd_aplicado: int | None = None
    heater_permiso: int | None = None
    flujo_invertido_aplicado: int | None = None


class Plant(abc.ABC):
    """Interfaz modular planta <-> servidor Modbus.

    Esta es la pieza central del desacople que pide la sección 3 de la
    guía vigente ("Arquitectura modular objetivo"): el bucle del
    servidor Modbus (``bucle_planta``) solo conoce esta interfaz, nunca
    la física concreta. Eso permite:

        - Usar ``ModeloSecadoPlant`` (planta_secado.py, el modelo del
          proyecto) o ``ToyPlant`` (dinámica de juguete, solo para
          pruebas de comunicación) sin tocar el mapa de registros ni el
          lado CODESYS.
        - Más adelante, cambiar a una implementación que en vez de
          calcular la física lea sensores reales de la secadora física,
          de nuevo sin tocar CODESYS (ver tabla de capas, sección 3 de
          la guía: "Simulación" vs. "Planta real" son la misma fila de
          Controlador/Interfaz).

    Cualquier planta nueva solo necesita implementar ``step()``.
    """

    def reset_lote(self) -> None:
        """Reinicia la planta para un lote nuevo (registro 21, "Nuevo lote"
        en la HMI). Por defecto no hace nada (ToyPlant no tiene lote)."""
        return None

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


class RegistroCSV:
    """Una fila por ciclo del servidor (21 oct 2026). Sirve como evidencia de
    los ensayos de fallo F1-F5 (guía de cierre, R4) y como archivo de
    histórico del lote completo (R5): tiempo de reloj y de modelo, estado,
    salud del enlace, edad de comandos, comandos recibidos y aplicados,
    clima, proceso, humedad, potencia y energía."""

    COLUMNAS = [
        "reloj_iso", "reloj_s", "t_planta_h", "hora_dia_h", "t_lote_h", "t_proceso_h", "t_secado_h",
        "t_parado_h", "estado_planta", "plant_mode", "comm_lost", "edad_comandos_s", "heartbeat",
        "heater_cmd_rx", "fan_cmd_rx", "fan_speed_rx", "setpoint_rx", "flow_dir_rx", "fluidsim_estado",
        "flujo_invertido_aplicado",
        "fan_aplicado", "heater_permiso", "setpoint_aplicado_c",
        "T_ambiente_c", "RH_ambiente_pct", "T_process_c", "RH_process_pct",
        "M_prom_bh", "M_max_bh", "M_min_bh", "potencia_res_kw", "duty_pct",
        "caudal_m3_min", "caudal_natural_m3_min", "energia_kwh",
    ]

    def __init__(self, ruta: str) -> None:
        import csv
        import os
        nuevo = not os.path.exists(ruta)
        self._f = open(ruta, "a", newline="", encoding="utf-8")
        self._w = csv.writer(self._f)
        if nuevo:
            self._w.writerow(self.COLUMNAS)
        self._t0 = time.time()

    def escribir(self, o: "PlantOutputs", **k) -> None:
        from datetime import datetime

        def f(v, nd=4):
            return "" if v is None else (round(v, nd) if isinstance(v, float) else v)

        self._w.writerow([
            datetime.now().isoformat(timespec="milliseconds"), round(time.time() - self._t0, 3),
            f(o.t_planta_h), f(o.hora_dia_h), f(o.t_lote_h), f(o.tiempo_proceso_h), f(o.t_secado_h),
            f(o.t_parado_h), f(o.estado_planta), k["plant_mode"], int(k["comm_lost"]),
            round(k["edad_comandos_s"], 2), k["heartbeat"],
            k["heater_cmd"], k["fan_cmd"], k["fan_speed_pct"], k["setpoint_cmd"], k["flow_dir_cmd"],
            k["fluidsim_estado"], f(o.flujo_invertido_aplicado),
            f(o.fan_cmd_aplicado), f(o.heater_permiso), f(o.setpoint_aplicado_c),
            f(o.t_ambiente_c), f(o.rh_ambient_pct), f(o.t_process_c), f(o.rh_process_pct),
            f(o.m_coffee_pct), f(o.m_coffee_max_pct), f(o.m_coffee_min_pct), f(o.potencia_res_kw),
            f(o.heater_duty_pct), f(o.caudal_m3_min), f(o.caudal_natural_m3_min), f(o.energia_kwh),
        ])
        self._f.flush()

    def cerrar(self) -> None:
        self._f.close()


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
    # 19 oct 2026: arranca en HOLD; solo pasa a RUN cuando CODESYS lo pide (START).
    slave_ctx.setValues(3, REG_PLANT_MODE, [PLANT_MODE_HOLD])
    slave_ctx.setValues(3, REG_SAFETY_OK, [1])
    # M_coffee: valor inicial 0.0 -- solo tiene significado real cuando
    # la planta es ModeloSecadoPlant (ver planta_secado.py); con
    # ToyPlant queda sin usar (nunca se sobreescribe, ver bucle_planta).
    slave_ctx.setValues(3, REG_M_COFFEE, float_to_registers(0.0))
    slave_ctx.setValues(3, REG_TIEMPO_PROCESO, float_to_registers(0.0))
    slave_ctx.setValues(3, REG_HEARTBEAT, [0])
    slave_ctx.setValues(3, REG_RH_PROCESS, float_to_registers(0.0))
    slave_ctx.setValues(3, REG_FLOW_DIR_CMD, [0])
    slave_ctx.setValues(3, REG_M_COFFEE_MAX, float_to_registers(0.0))
    slave_ctx.setValues(3, REG_HEATER_DUTY, float_to_registers(0.0))
    slave_ctx.setValues(3, REG_FAN_SPEED_CMD, [0])
    slave_ctx.setValues(3, REG_CAUDAL, float_to_registers(0.0))
    slave_ctx.setValues(3, REG_RESET_LOTE_CMD, [0])
    slave_ctx.setValues(3, REG_ENERGIA, float_to_registers(0.0))
    slave_ctx.setValues(3, REG_SETPOINT_CMD, [0])
    return ModbusServerContext(slaves=slave_ctx, single=True), hr_block


def bucle_planta(
    plant: Plant,
    slave_ctx: ModbusSlaveContext,
    watched_block: WatchedDataBlock,
    stop_event: threading.Event,
    periodo_s: float,
    registro_csv: "RegistroCSV | None" = None,
) -> None:
    """Lee comandos, aplica el watchdog de comunicación, avanza la planta
    (a través de la interfaz ``Plant``, ver más arriba) y publica el
    resultado — cada ``periodo_s`` segundos."""

    heartbeat = 0
    reset_anterior = 0
    fluidsim_previo = 0
    while not stop_event.is_set():
        # "Nuevo lote" (registro 21): se actúa en el FLANCO 0 -> 1, porque
        # CODESYS escribe el registro en cada ciclo; mientras siga en 1 no
        # se vuelve a reiniciar.
        reset_cmd = slave_ctx.getValues(3, REG_RESET_LOTE_CMD, count=1)[0]
        if reset_cmd == 1 and reset_anterior == 0:
            plant.reset_lote()
            log.info("NUEVO LOTE: planta reiniciada (humedad inicial, tiempo y energía a cero).")
        reset_anterior = reset_cmd

        heater_cmd_bruto = slave_ctx.getValues(3, REG_HEATER_CMD, count=1)[0]
        fan_cmd_bruto = slave_ctx.getValues(3, REG_FAN_CMD, count=1)[0]
        plant_mode = slave_ctx.getValues(3, REG_PLANT_MODE, count=1)[0]
        flow_dir_bruto = slave_ctx.getValues(3, REG_FLOW_DIR_CMD, count=1)[0]
        fan_speed_bruto = slave_ctx.getValues(3, REG_FAN_SPEED_CMD, count=1)[0]
        setpoint_bruto = slave_ctx.getValues(3, REG_SETPOINT_CMD, count=1)[0]
        fluidsim_estado = slave_ctx.getValues(3, REG_FLUIDSIM_ESTADO, count=1)[0]
        if fluidsim_estado != fluidsim_previo:
            log.warning("Enlace FluidSIM: %s -> %s", FLUIDSIM_TXT.get(fluidsim_previo, "?"),
                        FLUIDSIM_TXT.get(fluidsim_estado, "?"))
            fluidsim_previo = fluidsim_estado

        comm_lost = watched_block.seconds_since_last_actuator_write() > WATCHDOG_TIMEOUT_S
        heater_cmd = 0 if comm_lost else heater_cmd_bruto
        fan_cmd = 0 if comm_lost else fan_cmd_bruto

        # 21 oct 2026: la planta NUNCA se congela. HOLD y comm_lost solo
        # cambian los comandos (ver planta_secado.ModeloSecadoPlant.step);
        # el tiempo físico avanza siempre ``periodo_s`` por ciclo.
        # (Hasta el 20 oct: dt = 0 en HOLD, modelo congelado.)
        dt_paso_s = periodo_s
        edad_comandos_s = watched_block.seconds_since_last_actuator_write()
        outputs = plant.step(
            dt_paso_s,
            PlantInputs(heater_cmd=heater_cmd, fan_cmd=fan_cmd, plant_mode=plant_mode, comm_lost=comm_lost,
                        flow_dir_cmd=0 if comm_lost else flow_dir_bruto,
                        fan_speed_pct=fan_speed_bruto, setpoint_c=float(setpoint_bruto),
                        fluidsim_estado=fluidsim_estado),
        )

        slave_ctx.setValues(3, REG_T_PROCESS, float_to_registers(outputs.t_process_c))
        slave_ctx.setValues(3, REG_RH_AMBIENT, float_to_registers(outputs.rh_ambient_pct))
        slave_ctx.setValues(3, REG_SAFETY_OK, [0 if comm_lost else 1])
        if outputs.m_coffee_pct is not None:
            slave_ctx.setValues(3, REG_M_COFFEE, float_to_registers(outputs.m_coffee_pct))
        if outputs.tiempo_proceso_h is not None:
            slave_ctx.setValues(3, REG_TIEMPO_PROCESO, float_to_registers(outputs.tiempo_proceso_h))
        if outputs.rh_process_pct is not None:
            slave_ctx.setValues(3, REG_RH_PROCESS, float_to_registers(outputs.rh_process_pct))
        if outputs.m_coffee_max_pct is not None:
            slave_ctx.setValues(3, REG_M_COFFEE_MAX, float_to_registers(outputs.m_coffee_max_pct))
        if outputs.heater_duty_pct is not None:
            slave_ctx.setValues(3, REG_HEATER_DUTY, float_to_registers(outputs.heater_duty_pct))
        if outputs.caudal_m3_min is not None:
            slave_ctx.setValues(3, REG_CAUDAL, float_to_registers(outputs.caudal_m3_min))
        if outputs.energia_kwh is not None:
            slave_ctx.setValues(3, REG_ENERGIA, float_to_registers(outputs.energia_kwh))
        for reg, val in ((REG_TIEMPO_LOTE, outputs.t_lote_h), (REG_TIEMPO_SECADO, outputs.t_secado_h),
                         (REG_TIEMPO_PARADO, outputs.t_parado_h), (REG_TIEMPO_PLANTA, outputs.t_planta_h),
                         (REG_T_AMBIENTE, outputs.t_ambiente_c), (REG_HORA_DIA, outputs.hora_dia_h)):
            if val is not None:
                slave_ctx.setValues(3, reg, float_to_registers(val))
        if outputs.estado_planta is not None:
            slave_ctx.setValues(3, REG_ESTADO_PLANTA, [int(outputs.estado_planta)])

        # Heartbeat: se incrementa y publica SIEMPRE, incluso con
        # comm_lost=True -- es la señal de "el proceso Python sigue
        # vivo", independiente del watchdog de actuadores (ver
        # docstring del módulo, "Señal de latido").
        heartbeat = (heartbeat + 1) % (HEARTBEAT_MAX + 1)
        slave_ctx.setValues(3, REG_HEARTBEAT, [heartbeat])

        if registro_csv is not None:
            registro_csv.escribir(outputs, plant_mode=plant_mode, comm_lost=comm_lost,
                                  edad_comandos_s=edad_comandos_s, heater_cmd=heater_cmd_bruto,
                                  fan_cmd=fan_cmd_bruto, fan_speed_pct=fan_speed_bruto,
                                  setpoint_cmd=setpoint_bruto, flow_dir_cmd=flow_dir_bruto,
                                  heartbeat=heartbeat, fluidsim_estado=fluidsim_estado)

        estado = "COMM_LOST(politica de fallo)" if comm_lost else "OK"
        if outputs.t_planta_h is not None:
            from planta_secado import ESTADOS_TXT
            log.info("planta=%6.2fh lote=%6.2fh secado=%6.2fh parado=%6.2fh hora=%5.2f T_amb=%5.1fC estado=%s",
                     outputs.t_planta_h, outputs.t_lote_h, outputs.t_secado_h, outputs.t_parado_h,
                     outputs.hora_dia_h, outputs.t_ambiente_c, ESTADOS_TXT.get(outputs.estado_planta, "?"))
        m_coffee_str = f"{outputs.m_coffee_pct:5.1f}%" if outputs.m_coffee_pct is not None else "  n/a"
        tiempo_str = f"{outputs.tiempo_proceso_h:6.2f}h" if outputs.tiempo_proceso_h is not None else "    n/a"
        rh_proc_str = f"{outputs.rh_process_pct:5.1f}%" if outputs.rh_process_pct is not None else "  n/a"
        duty_str = f"{outputs.heater_duty_pct:5.1f}%" if outputs.heater_duty_pct is not None else "  n/a"
        caudal_str = f"{outputs.caudal_m3_min:4.1f}" if outputs.caudal_m3_min is not None else " n/a"
        log.info(
            "t=%s | T_process=%6.2fC | RH_ambient=%5.1f%% | RH_process=%s | M_coffee=%s | heater_duty=%s | caudal=%s m3/min | heater_cmd=%s | "
            "fan_cmd=%s | plant_mode=%s | SP=%s C | caudal_cmd=%s %% | safety=%s | heartbeat=%s",
            tiempo_str,
            outputs.t_process_c,
            outputs.rh_ambient_pct,
            rh_proc_str,
            m_coffee_str,
            duty_str,
            caudal_str,
            heater_cmd_bruto,
            fan_cmd_bruto,
            plant_mode,
            setpoint_bruto,
            fan_speed_bruto,
            estado,
            heartbeat,
        )
        stop_event.wait(periodo_s)


def main() -> None:
    global WATCHDOG_TIMEOUT_S
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default="127.0.0.1", help="IP donde escucha el servidor (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5020, help="Puerto TCP (default: 5020, el que usa el proyecto CODESYS; 502 requiere permisos de administrador en Windows)")
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
        default="modelo",
        help=(
            "Planta a usar: 'modelo' (default) = ModeloSecadoPlant (planta_secado.py): secador electrico de "
            "80 kg c.p.s., 6 kW, lecho Thompson + cinetica Roa-Cenicafe. 'toy' = planta de juguete de v0, "
            "solo para probar la comunicacion."
        ),
    )
    parser.add_argument(
        "--factor-aceleracion",
        type=float,
        default=540.0,
        help="Solo con --plant modelo: segundos de modelo por segundo de reloj real (default: 540 = 0.15 h de modelo por segundo, la demo con el HMI; 1 = tiempo real)",
    )
    parser.add_argument(
        "--lazo-termico",
        choices=["auto", "plc", "local"],
        default="auto",
        help=(
            "Solo con --plant modelo. 'plc' = CODESYS decide heater_cmd (valido solo a tiempo real, "
            "--factor-aceleracion <= ~10). 'local' = termostato del ducto en Python cada 1 s de modelo; "
            "CODESYS supervisa (RUN/HOLD, ventilador, flujo, parada). 'auto' (default) elige segun el "
            "factor de aceleracion. Ver planta_secado.py, 'CORRECCION 4 oct 2026'."
        ),
    )
    parser.add_argument("--setpoint", type=float, default=50.0,
                        help="Solo con --lazo-termico local: setpoint del termostato del ducto [C] (default 50)")
    parser.add_argument("--hora-inicio", type=float, default=0.0,
                        help="Hora del día (0-24) en que arranca la planta; el clima sigue el ciclo día/noche "
                             "desde ahí (default 0 = medianoche, igual que la campaña Monte Carlo)")
    parser.add_argument("--post-ventilacion-min", type=float, default=10.0,
                        help="Minutos de MODELO de post-ventilación al perder la comunicación (resistencia ya "
                             "apagada); 0 = todo apagado de inmediato (default 10)")
    parser.add_argument("--log-csv", default=None,
                        help="Ruta de un CSV con una fila por ciclo (relojes, estado, enlaces, comandos, "
                             "T, HR, humedad, potencia, energía). Evidencia de los ensayos F1-F5.")
    args = parser.parse_args()
    WATCHDOG_TIMEOUT_S = args.watchdog_timeout

    context, watched_block = construir_contexto()
    if args.plant == "modelo":
        # Import diferido: planta_secado.py importa de este modulo, asi
        # que se importa aqui (cuando main() corre, este modulo ya esta
        # completamente cargado) para evitar un import circular.
        from planta_secado import ModeloSecadoPlant, ParametrosModeloSecadoPlant

        plant: Plant = ModeloSecadoPlant(
            ParametrosModeloSecadoPlant(
                factor_aceleracion=args.factor_aceleracion,
                lazo_termico=args.lazo_termico,
                setpoint_c=args.setpoint,
                hora_inicio_h=args.hora_inicio,
                post_ventilacion_h=args.post_ventilacion_min / 60.0,
            ),
            periodo_s=args.periodo,
        )
        log.info(
            "Usando ModeloSecadoPlant (secador electrico 80 kg c.p.s., lecho Thompson + Roa-Cenicafe) con factor_aceleracion=%.1f",
            args.factor_aceleracion,
        )
    else:
        plant: Plant = ToyPlant()
    stop_event = threading.Event()
    registro_csv = RegistroCSV(args.log_csv) if args.log_csv else None
    if registro_csv:
        log.info("Registro CSV por ciclo en %s", args.log_csv)

    hilo_planta = threading.Thread(
        target=bucle_planta,
        args=(plant, context[0], watched_block, stop_event, args.periodo, registro_csv),
        daemon=True,
    )
    hilo_planta.start()

    log.info("Servidor Modbus TCP escuchando en %s:%s", args.host, args.port)
    log.info(
        "Mapa: hr[0-1]=T_process | hr[2]=heater_cmd | hr[3]=fan_cmd | "
        "hr[4-5]=RH_ambient | hr[6]=plant_mode | hr[7]=safety_ok | hr[8-9]=M_coffee (v2) | "
        "hr[10-11]=tiempo_proceso_h (v2) | hr[12]=heartbeat (v2) | hr[13-14]=RH_process | "
        "hr[15]=flow_dir_cmd | hr[16-17]=M_coffee_max | hr[18-19]=heater_duty | "
        "hr[20]=fan_speed_pct | hr[21]=reset_lote_cmd | hr[22-23]=caudal | hr[24-25]=energia_kWh | hr[26]=setpoint_cmd | "
        "hr[27-28]=tiempo_lote_h | hr[29-30]=tiempo_secado_h | hr[31-32]=tiempo_parado_h | hr[33-34]=tiempo_planta_h | "
        "hr[35]=estado_planta | hr[36-37]=T_ambiente | hr[38-39]=hora_dia | hr[40]=fluidsim_estado"
    )
    log.info("Watchdog de comunicación (CODESYS->Python): %.1f s sin escritura de actuadores => valor seguro.", WATCHDOG_TIMEOUT_S)
    log.info("Heartbeat (Python->CODESYS): hr[12] se incrementa cada ciclo; si CODESYS lo ve congelado, el servidor Python se cayó.")
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
        if registro_csv:
            registro_csv.cerrar()


if __name__ == "__main__":
    main()

"""
modbus_server.py
=================

Servidor Modbus TCP (esclavo) que ejecuta la planta simulada del secador de
café y la expone a CODESYS (maestro Modbus).
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Reparto de funciones
--------------------
- Python = planta: integra el modelo físico (``planta_secado.py``) cada ciclo
  y publica sus variables en registros holding.
- CODESYS = controlador: lee esas variables, ejecuta la secuencia, las alarmas
  y la HMI, y escribe los comandos (resistencia, ventilador, sentido del aire,
  caudal, consigna, nuevo lote).

La física avanza siempre mientras el servidor corre, con o sin CODESYS o
FluidSIM conectados:
- RUN: integra con los comandos vigentes y los límites de actuación.
- HOLD (REPOSO, PARO, FIN DE SECADO, FALLA o EMERGENCIA en CODESYS): resistencia
  y ventilador apagados; la cámara y el café siguen evolucionando (enfriamiento
  hacia el ambiente, ciclo día/noche y secado residual por tiro natural).
- Comunicación perdida (watchdog): resistencia apagada de inmediato,
  post-ventilación y luego todo apagado; la física sigue.
- Nuevo lote: reinicia la humedad, el tiempo del lote y la energía.

Mapa de registros (holding registers; CODESYS lee con FC03 y escribe con FC06)
-------------------------------------------------------------------------------
Cada REAL ocupa dos registros (float32, palabra alta primero).

    Dir.    Tag               Tipo    Unidad   Sentido
    0-1     T_process         REAL    °C       Python -> CODESYS
    2       heater_cmd        WORD    0/1      CODESYS -> Python
    3       fan_cmd           WORD    0/1      CODESYS -> Python
    4-5     RH_ambient        REAL    %        Python -> CODESYS (aire exterior)
    6       plant_mode        WORD    0 RUN, 1 HOLD   CODESYS -> Python
    7       safety_ok         WORD    0/1      Python -> CODESYS (0 = watchdog activo)
    8-9     M_coffee          REAL    % b.h.   Python -> CODESYS (humedad promedio)
    10-11   tiempo_proceso_h  REAL    h        Python -> CODESYS (horas en RUN con ventilador)
    12      heartbeat         WORD    0-65535  Python -> CODESYS (sube cada ciclo)
    13-14   RH_process        REAL    %        Python -> CODESYS (aire dentro de la cámara)
    15      flow_dir_cmd      WORD    0/1      CODESYS -> Python (0 abajo->arriba, 1 invertido)
    16-17   M_coffee_max      REAL    % b.h.   Python -> CODESYS (capa más húmeda)
    18-19   heater_duty       REAL    %        Python -> CODESYS (ciclo de trabajo de la resistencia)
    20      fan_speed_pct     WORD    30-100   CODESYS -> Python (consigna de caudal; 0 = 100 %)
    21      reset_lote_cmd    WORD    0/1      CODESYS -> Python (flanco 0->1 = nuevo lote)
    22-23   caudal            REAL    m3/min   Python -> CODESYS (caudal real aplicado)
    24-25   energia_kWh       REAL    kWh      Python -> CODESYS (energía del lote)
    26      setpoint_cmd      WORD    °C       CODESYS -> Python (consigna del perfil; 0 = 50 °C)
    27-28   tiempo_lote_h     REAL    h        Python -> CODESYS (desde el último nuevo lote)
    29-30   tiempo_secado_h   REAL    h        Python -> CODESYS (horas con calentamiento permitido)
    31-32   tiempo_parado_h   REAL    h        Python -> CODESYS (paro, falla o fin)
    33-34   tiempo_planta_h   REAL    h        Python -> CODESYS (desde que arrancó el servidor)
    35      estado_planta     WORD    0-4      Python -> CODESYS (0 reposo, 1 secando, 2 ventilando,
                                               3 post-ventilación, 4 falla de comunicación)
    36-37   T_ambiente        REAL    °C       Python -> CODESYS
    38-39   hora_dia          REAL    h        Python -> CODESYS (0-24, ciclo día/noche)
    40      fluidsim_estado   WORD    0-3      CODESYS -> Python (0 no informado, 1 enlace vivo,
                                               2 sin FluidSIM declarado, 3 enlace caído)

Vigilancia de comunicación en los dos sentidos
-----------------------------------------------
- Watchdog de Python: si no recibe escrituras de CODESYS durante
  ``--watchdog-timeout`` segundos, aplica la política de fallo local y publica
  ``safety_ok = 0``.
- Heartbeat: contador que sube cada ciclo. CODESYS compara su valor ciclo a
  ciclo y, si deja de cambiar unos segundos, pasa a FALLA (Python caído).

Registro del lote
-----------------
Cada ciclo se guarda en un CSV (``--log-csv``; sin esa opción va a
``resultados/lotes/servidor_<fecha>_<hora>.csv``). Al cumplirse el criterio de
fin de un lote se genera su gráfica completa (``grafica_lote.py``).

Uso
---
    pip install -r requirements.txt
    python modbus_server.py                      # planta del modelo, factor 540, puerto 5020
    python modbus_server.py --semilla 1001       # clima y humedad inicial de una realización de la campaña
    python modbus_server.py --factor-aceleracion 1 --lazo-termico plc   # tiempo real, lazo en el PLC
    python modbus_server.py --plant toy          # planta mínima para probar la comunicación

Debe haber una sola instancia del servidor usando el puerto.
"""

from __future__ import annotations

import abc
import argparse
import logging
import os
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
REG_M_COFFEE = 8       # 2 registros: float32, humedad promedio [% b.h.]
REG_TIEMPO_PROCESO = 10  # 2 registros: float32, horas de MODELO transcurridas
REG_HEARTBEAT = 12     # 1 registro: contador 0-65535, incrementa cada ciclo del servidor
REG_RH_PROCESS = 13    # 2 registros: float32, HR dentro de la cámara
REG_FLOW_DIR_CMD = 15  # 1 registro: 0/1, sentido del aire en el lecho (CODESYS -> Python)
REG_M_COFFEE_MAX = 16  # 2 registros: float32, humedad de la capa más húmeda (% b.h.)
REG_HEATER_DUTY = 18   # 2 registros: float32, ciclo de trabajo de la resistencia [%]
REG_FAN_SPEED_CMD = 20 # 1 registro: consigna de caudal 0-100 % (CODESYS -> Python)
REG_RESET_LOTE_CMD = 21  # 1 registro: flanco 0->1 = nuevo lote (CODESYS -> Python)
REG_CAUDAL = 22        # 2 registros: float32, caudal real [m3/min] (Python -> CODESYS)
REG_ENERGIA = 24       # 2 registros: float32, energía eléctrica del lote [kWh] (Python -> CODESYS)
REG_SETPOINT_CMD = 26  # 1 registro: consigna de T_process en °C enteros (CODESYS -> Python)
# relojes y estado de la planta (Python -> CODESYS)
REG_TIEMPO_LOTE = 27     # 2 registros: float32 [h de modelo] desde "Nuevo lote", incluye paradas
REG_TIEMPO_SECADO = 29   # 2 registros: float32 [h] con calentamiento permitido
REG_TIEMPO_PARADO = 31   # 2 registros: float32 [h] lote - proceso
REG_TIEMPO_PLANTA = 33   # 2 registros: float32 [h] desde que arrancó el servidor
REG_ESTADO_PLANTA = 35   # 1 registro: 0 REPOSO, 1 SECANDO, 2 VENTILANDO, 3 POST-VENT, 4 FALLA_COMM
REG_T_AMBIENTE = 36      # 2 registros: float32 [°C]
REG_HORA_DIA = 38        # 2 registros: float32 [h, 0-24]
REG_FLUIDSIM_ESTADO = 40 # 1 registro: 0 no informado, 1 vivo, 2 sin_fluidsim declarado, 3 caído (CODESYS -> Python)
NUM_HOLDING_REGS = 41    # 0-40
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
    fluidsim_estado: int = 0  # registro 40: 0 no informado, 1 vivo, 2 emulado, 3 caído


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
    # Energía eléctrica acumulada del lote [kWh] -- 24-25. None -> ToyPlant.
    # Caudal real aplicado [m3/min] -- 22-23. None -> ToyPlant.
    # Ciclo de trabajo de la resistencia en el ultimo ciclo [%] -- 18-19
    # (lazo térmico local). None -> ToyPlant.
    # Humedad de la capa más húmeda del lecho [% b.h.] -- 16-17. None -> ToyPlant.
    # HR del aire DENTRO de la cámara [%] -- direcciones 13-14.
    # rh_ambient_pct es SOLO la HR exterior. None -> ToyPlant.
    # --- relojes, estado y variables para el registro CSV ---
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

    Es la pieza central de la arquitectura modular: el bucle del
    servidor Modbus (``bucle_planta``) solo conoce esta interfaz, nunca
    la física concreta. Eso permite:

        - Usar ``ModeloSecadoPlant`` (planta_secado.py, el modelo del
          proyecto) o ``ToyPlant`` (dinámica de juguete, solo para
          pruebas de comunicación) sin tocar el mapa de registros ni el
          lado CODESYS.
        - Más adelante, cambiar a una implementación que en vez de
          calcular la física lea sensores reales de la secadora física,
          de nuevo sin tocar CODESYS: simulación y planta real comparten
          el mismo controlador y la misma interfaz.

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
    """Planta mínima de primer orden, sin física de café; solo para probar la comunicación.

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
    T_MAX_C = 90.0          # límite superior de seguridad de la planta mínima [°C]
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
    """Una fila por ciclo del servidor. Sirve como evidencia de
    los ensayos de falla F1-F5 y como histórico del lote completo:
    tiempo de reloj y de modelo, estado,
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

    CICLOS_TRAS_FIN = 8   # ciclos (≈1,2 h de modelo) después del fin para que la gráfica muestre la ventilación final

    def __init__(self, ruta: str, grafica_auto: bool = True) -> None:
        import csv
        import os
        self.ruta = ruta
        self.grafica_auto = grafica_auto
        self.n_lote = 1
        self._t_lote_prev = None
        self._fin_visto = False
        self._cuenta_tras_fin = None
        self.lote_graficado = False
        carpeta = os.path.dirname(ruta)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)   # crea resultados/... si no existe
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
        self._vigilar_fin_de_lote(o)

    def _vigilar_fin_de_lote(self, o: "PlantOutputs") -> None:
        """Al cumplirse el criterio de fin (promedio ≤ 11 % y capa más húmeda ≤ 12 % b.h.)
        genera sola la gráfica del lote completo, sin cerrar el servidor."""
        if self._t_lote_prev is not None and o.t_lote_h is not None and o.t_lote_h < self._t_lote_prev:
            self.n_lote += 1                       # «Nuevo lote» en CODESYS
            self._fin_visto, self._cuenta_tras_fin, self.lote_graficado = False, None, False
        self._t_lote_prev = o.t_lote_h
        if not self.grafica_auto or self._fin_visto:
            if self._cuenta_tras_fin is not None:
                self._cuenta_tras_fin += 1
                if self._cuenta_tras_fin >= self.CICLOS_TRAS_FIN:
                    self._cuenta_tras_fin = None
                    self.graficar_en_segundo_plano()
            return
        m, mx, ts = o.m_coffee_pct, o.m_coffee_max_pct, o.t_secado_h
        if None not in (m, mx, ts) and m <= 11.0 and mx <= 12.0 and ts > 0:
            self._fin_visto, self._cuenta_tras_fin = True, 0
            log.info("Fin de secado (lote %d): la gráfica del lote se genera en %d ciclos.", self.n_lote, self.CICLOS_TRAS_FIN)

    def graficar_en_segundo_plano(self) -> None:
        import os
        salida = os.path.splitext(self.ruta)[0] + f"_lote{self.n_lote}.png"
        self.lote_graficado = True

        def tarea():
            try:
                from grafica_lote import graficar
                log.info("Gráfica del lote %d: %s", self.n_lote, graficar(self.ruta, salida))
            except Exception as exc:   # nunca debe afectar al servidor
                log.warning("No se pudo generar la gráfica del lote (%s). A mano: python grafica_lote.py %s",
                            exc, self.ruta)
        threading.Thread(target=tarea, daemon=True).start()

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
    # arranca en HOLD; solo pasa a RUN cuando CODESYS lo pide (START).
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

        # La planta nunca se congela. HOLD y comm_lost solo
        # cambian los comandos (ver planta_secado.ModeloSecadoPlant.step);
        # el tiempo físico avanza siempre ``periodo_s`` por ciclo.
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
            "80 kg c.p.s., 6 kW, lecho Thompson + cinetica Roa-Cenicafe. 'toy' = planta minima, "
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
            "factor de aceleracion (ver planta_secado.py)."
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
    parser.add_argument("--semilla", type=int, default=None,
                        help="Verificación CODESYS vs. réplica: usa el clima y la humedad inicial de la realización "
                             "Monte Carlo con esta semilla (p. ej. 1001) y reinicia el reloj del clima con «Nuevo lote». "
                             "Comparar después con compara_codesys_replica.py")
    parser.add_argument("--log-csv", default=None,
                        help="Ruta de un CSV con una fila por ciclo (relojes, estado, enlaces, comandos, "
                             "T, HR, humedad, potencia, energía). Evidencia de los ensayos F1-F5.")
    parser.add_argument("--sin-grafica", action="store_true",
                        help="No generar la gráfica del lote (por defecto se genera sola al terminar cada lote, "
                             "<csv>_loteN.png, y al cerrar el servidor si el lote no había terminado)")
    parser.add_argument("--sin-log", action="store_true",
                        help="No guardar CSV. Sin --log-csv, el servidor guarda por defecto en "
                             "resultados/lotes/servidor_<fecha>_<hora>.csv")
    args = parser.parse_args()
    WATCHDOG_TIMEOUT_S = args.watchdog_timeout

    context, watched_block = construir_contexto()
    if args.plant == "modelo":
        # Import diferido: planta_secado.py importa de este modulo, asi
        # que se importa aqui (cuando main() corre, este modulo ya esta
        # completamente cargado) para evitar un import circular.
        from planta_secado import ModeloSecadoPlant, ParametrosModeloSecadoPlant

        extra = {}
        if args.semilla is not None:
            from campana_montecarlo import realizacion
            dias, m0 = realizacion(args.semilla)
            extra = {"clima_dias": dias, "m0_bh_pct": m0, "clima_desde_lote": True}
            log.info("Verificación: semilla %d (M0 = %.2f %% b.h., %d días de clima de la campaña)", args.semilla, m0, len(dias))
        plant: Plant = ModeloSecadoPlant(
            ParametrosModeloSecadoPlant(
                **extra,
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
    if not args.log_csv and not args.sin_log and args.plant == "modelo":
        # siempre se registra el lote, aunque se arranque el servidor sin opciones
        from datetime import datetime
        args.log_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados", "lotes",
                                    datetime.now().strftime("servidor_%Y%m%d_%H%M%S.csv"))
    registro_csv = RegistroCSV(args.log_csv, grafica_auto=not args.sin_grafica) if args.log_csv else None
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
        "hr[4-5]=RH_ambient | hr[6]=plant_mode | hr[7]=safety_ok | hr[8-9]=M_coffee | "
        "hr[10-11]=tiempo_proceso_h | hr[12]=heartbeat | hr[13-14]=RH_process | "
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
            if not args.sin_grafica and not registro_csv.lote_graficado:
                # gráfica del lote completo a partir del CSV
                try:
                    from grafica_lote import graficar
                    log.info("Gráfica del lote completo: %s",
                             graficar(args.log_csv, os.path.splitext(args.log_csv)[0] + f"_lote{registro_csv.n_lote}.png"))
                except Exception as exc:  # la gráfica nunca debe impedir cerrar el servidor
                    log.warning("No se pudo generar la gráfica del lote (%s). "
                                "Correr a mano: python grafica_lote.py %s", exc, args.log_csv)


if __name__ == "__main__":
    main()

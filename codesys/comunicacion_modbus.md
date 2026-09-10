# Comunicación CODESYS ↔ Python vía Modbus TCP — v0 (prueba mínima)

**Estado: funcionando end-to-end** (9-10 sept 2026). Este documento
complementa `python/modbus_server.py`. Ahí está el lado Python
(servidor); acá está el lado CODESYS (cliente) y el procedimiento de
prueba. Ver también la guía vigente, sección 3 ("Arquitectura modular
objetivo") y la "Prueba mínima del corte".

El proyecto CODESYS que ya funciona está en `codesys/ModbusPhytoon.project`
(ábrelo con CODESYS **V3.5 SP15 Patch 4** — ver la sección 0 sobre por qué
la versión importa).

## 0. Tres errores que costaron horas — lee esto antes de reproducir

Si vas a rehacer esto desde cero (o le explicas al profe cómo funciona),
estos tres puntos fueron el 90% del tiempo perdido la primera vez:

1. **La versión del IDE CODESYS debe coincidir con la del runtime
   (SoftPLC) al que te conectas.** Hay dos instalaciones en el PC (SP9
   Patch 1 y SP15 Patch 4). El runtime "CODESYS Control Win V3" que
   estaba corriendo era el de **SP15**, pero el proyecto se armó
   inicialmente en el IDE de **SP9** — la conexión se veía "en
   ejecución" y sin errores, pero el driver Modbus TCP nunca mandaba
   ni un solo paquete por la red (verificable con `netstat` mostrando
   la conexión TCP establecida pero cero tráfico Modbus real en los
   logs de `pymodbus`). La solución fue rehacer el proyecto en el IDE
   **SP15**, que es la versión que coincide con el runtime instalado.
   Antes de tocar nada, confirma con qué versión de runtime vas a
   correr (bandeja del sistema → ícono de CODESYS Control Win) y abre
   el proyecto con el IDE de esa misma versión.

2. **El REAL en memoria de CODESYS (Windows x86/x64) es little-endian
   a nivel de palabra**, mientras que `modbus_server.py` codifica el
   float32 en orden big-endian "natural" (registro 0 = palabra alta,
   registro 1 = palabra baja — el orden típico de la mayoría de
   dispositivos Modbus). Al armar el `UNION` en ST, hay que asignar
   **la palabra baja primero**:

   ```st
   conv.words[0] := T_process_lo;   // NO T_process_hi
   conv.words[1] := T_process_hi;
   ```

   Si lo haces al revés, `T_process` sale como un número absurdo tipo
   `2.38E-41` en vez de una temperatura razonable — esa fue la señal
   de alerta.

3. **Nunca dejes más de una instancia de `modbus_server.py` corriendo
   a la vez.** Si abres varias terminales y en cada una corres el
   script sin cerrar la anterior, todas quedan compitiendo por el
   mismo puerto; en Windows esto no siempre falla de forma obvia, y
   CODESYS puede terminar conectado a un proceso "zombie" viejo
   mientras tú miras la consola de uno nuevo que nunca recibe nada.
   Antes de correr el servidor, verifica que no haya otro corriendo:

   ```
   netstat -an | findstr 5020
   ```

   Si sale algo en `LISTENING` de un proceso que ya no reconoces,
   ciérralo (`taskkill /F /IM python.exe` mata todos los procesos de
   Python — úsalo solo si no tienes otra cosa importante corriendo en
   Python al mismo tiempo).

## 1. Arquitectura y roles

| Rol | Papel Modbus | Por qué |
|---|---|---|
| **Python** (`modbus_server.py`) | Servidor / *slave* TCP | Publica el estado de la planta simulada y expone registros de comando. |
| **CODESYS** | Cliente / *master* TCP | Sondea las variables en su ciclo de tarea y escribe los comandos — igual que lo haría contra un sensor/actuador Modbus real. |

Esto respeta el reparto de capas de la guía (CODESYS = Controlador,
Python = Planta) y hace que, cuando se pase de la planta simulada a la
secadora física, en CODESYS solo haya que cambiar la IP del dispositivo
esclavo, no la arquitectura.

## 2. Mapa de registros (v0)

| Dirección Modbus | Tag | Tipo | Unidad | Sentido |
|---|---|---|---|---|
| 0-1 (2 registros) | `T_process` | REAL / float32 IEEE754 | °C | Python → CODESYS (solo lectura) |
| 2 (1 registro) | `heater_cmd` | WORD (0 o 1) | - | CODESYS → Python (solo escritura desde CODESYS) |

Direcciones 3-15 quedan libres para la siguiente iteración
(`RH_ambient`, `M_coffee`, `fan_cmd`, `safety_ok`, `plant_mode` — ver
tabla completa de señales de la guía vigente, sección 3.1).

Unit ID / Slave ID: **1** (el servidor Python responde a cualquier ID
porque corre en modo `single=True`, pero usa 1 para que coincida con las
pruebas ya hechas).

## 3. Paso a paso en CODESYS (v0)

Los nombres exactos de menú pueden variar un poco según la versión de
CODESYS, pero el flujo es el mismo en V3.5:

1. **Verificar que el paquete Modbus esté instalado.** `Tools ▸ Package
   Manager` → buscar "Modbus". Si no aparece como "Add Device" en el
   paso siguiente, instalarlo desde ahí (es gratuito, de CODESYS Store).

2. **Agregar el maestro Modbus TCP.** En el árbol de dispositivos, clic
   derecho sobre el nodo del PLC (`Device`) → `Add Device...` →
   categoría `Fieldbuses ▸ Modbus ▸ Modbus TCP Master` → `Add Device`.

3. **Agregar el esclavo (nuestro servidor Python).** Clic derecho sobre
   el nodo `Modbus_TCP_Master` recién creado → `Add Device...` →
   `Fieldbuses ▸ Modbus ▸ Modbus TCP Slave` → `Add Device`. Doble clic
   sobre el nuevo nodo, pestaña **General**:
   - IP address: `127.0.0.1`
   - Port: `502` (o `5020` si se corrió `modbus_server.py --port 5020`)
   - Slave/Unit ID: `1`

4. **Agregar los canales de lectura/escritura.** Sobre el nodo del
   esclavo, pestaña **Modbus Master Channel** (o clic derecho → `Add
   Object` → `Modbus Master Channel` según la versión):
   - **Canal 1 — lectura de `T_process`**: Access type = `Read Holding
     Registers` (FC03), Start Address = `0`, Length = `2` registros.
     Si tu versión permite elegir el tipo de dato del canal
     directamente, elige `REAL`; si no, déjalo como `WORD` con longitud
     2 (ver conversión en el paso 6).
   - **Canal 2 — escritura de `heater_cmd`**: Access type = `Write
     Single Register` (FC06), Start Address = `2`, Length = `1`,
     tipo `WORD`.

5. **Mapear los canales a variables PLC.** Pestaña **IO Mapping** de
   cada canal: escribe/arrastra el nombre de la variable (por ejemplo
   `T_process_raw` para el canal 1, `heater_cmd` para el canal 2).

6. **Si el canal no soporta `REAL` directamente**, convierte el par de
   `WORD` a `REAL` con un tipo `UNION` en tu proyecto:

   ```st
   TYPE U_WORDS_TO_REAL :
   UNION
       words : ARRAY[0..1] OF WORD;
       value : REAL;
   END_UNION
   END_TYPE
   ```

   Y en `PLC_PRG`:

   ```st
   PROGRAM PLC_PRG
   VAR
       T_process_raw   : ARRAY[0..1] OF WORD;   // mapeado al canal 1
       conv            : U_WORDS_TO_REAL;
       T_process       : REAL;
       heater_cmd      : WORD;                   // mapeado al canal 2
       setpoint        : REAL := 50.0;           // °C, solo para esta prueba
   END_VAR

   conv.words[0] := T_process_raw[1];   // palabra BAJA primero (ver sección 0.2)
   conv.words[1] := T_process_raw[0];   // palabra ALTA segundo
   T_process := conv.value;

   // Control mínimo tipo bang-bang, solo para demostrar la vuelta completa:
   // Python -> CODESYS (lee T_process) -> CODESYS decide -> Python (heater_cmd)
   IF T_process < setpoint THEN
       heater_cmd := 1;
   ELSE
       heater_cmd := 0;
   END_IF;
   ```

   **Nota sobre orden de palabras/bytes:** si `T_process` se ve como un
   número absurdo (exponente enorme o negativo raro), el orden de
   `conv.words[0]`/`conv.words[1]` está al revés — ver sección 0.2 (ya
   corregido arriba: palabra baja en `words[0]`).

   **En esta instalación no hace falta un adaptador Ethernet
   dedicado**, pero en algunas versiones de CODESYS el `Modbus TCP
   Master` solo aparece en el diálogo "Add Device" si primero agregas
   un dispositivo `Ethernet Adapter` y cuelgas el master de ahí (así
   fue necesario aquí, en ambos SP9 y SP15). Si no ves `Modbus TCP
   Master` directo bajo el nodo del PLC, prueba ese camino:
   `Device → Add Device → Ethernet Adapter`, y de ahí
   `Add Device → Modbus TCP Master`. En el Ethernet Adapter, pestaña
   General, botón "..." junto a "Interface", elige una interfaz de
   red con **IP real asignada** (no `0.0.0.0`) — si queda sin
   interfaz, el dispositivo se marca con una advertencia (▲) y el
   master nunca manda tráfico aunque todo lo demás se vea bien.

7. **Compilar, descargar (Login) y correr** en CODESYS Control Win
   (SoftPLC local).

8. **Verificar en un Watch/Trace**: agregar `T_process` y `heater_cmd`
   a una ventana de monitoreo (`Add Watch` o una trace). Con
   `modbus_server.py` corriendo, deberías ver `T_process` subir cuando
   `heater_cmd = 1` y bajar hacia 25 °C cuando `heater_cmd = 0`.

## 4. Checklist de la "prueba mínima del corte"

Copiado de la guía vigente:

- [x] Python y CODESYS intercambian datos en ambos sentidos. **Verificado
      9-10 sept 2026** con `modbus_server.py` (single instance, ver
      sección 0.3) y el proyecto CODESYS SP15 (`ModbusPhytoon.project`).
- [x] El comando (`heater_cmd`) cambia el estado del simulador
      (`T_process`), no solo una variable decorativa — confirmado:
      `T_process` sube en Python cuando CODESYS escribe `heater_cmd=1`,
      y CODESYS lee ese mismo valor de vuelta.
- [x] Frecuencia de actualización y unidades documentadas (este
      documento + docstring de `modbus_server.py`).
- [x] Procedimiento reproducible desde cero (este documento, incluida
      la sección 0 con los tres errores más comunes).
- [ ] Pérdida de comunicación con comportamiento definido — **pendiente**:
      si se cierra `modbus_server.py`, el master de CODESYS debe mostrar
      el canal en error/timeout; falta definir y programar un valor
      seguro explícito (por ejemplo, `heater_cmd := 0` y una alarma)
      cuando eso ocurra.
- [ ] Evidencia en el repositorio (captura de pantalla o video del
      Watch/Trace de CODESYS junto con la consola de `modbus_server.py`
      mostrando los mismos valores) — **pendiente subir el archivo**,
      aunque ya se verificó en vivo.

## 5. Plan para la siguiente sesión (mostrar algo más completo)

Objetivo: pasar de "dos números que coinciden" a algo demostrable con
una interfaz, para la reunión con el profe.

1. **HMI en CODESYS.** Agregar una Visualization (clic derecho en
   `Application` → `Add Object` → `Visualization`). Mínimo:
   - Un indicador numérico o gauge de `T_process`.
   - Una gráfica de tendencia (Trend) de `T_process` en el tiempo.
   - Un indicador tipo "piloto" (círculo que cambia de color, con
     `Text Color`/`Fill Color` condicionados a `heater_cmd = 1`) para
     el calentador — esto es más vistoso que solo ver un `1`/`0` en una
     tabla, y es justo lo que pide la guía como "HMI con tendencias,
     alarmas y estado".
   - Opcional: un botón para forzar `setpoint` desde el HMI en vez de
     tenerlo fijo en el código.

2. **Más "pilotos"/salidas en Python.** Para que el HMI tenga más que
   mostrar, ampliar `modbus_server.py`:
   - Agregar `fan_cmd` (WORD, dirección 3) como segundo actuador
     simulado, con su propio efecto en la planta de juguete (por
     ejemplo, acelera el enfriamiento cuando está encendido).
   - Agregar `RH_ambient` (REAL, direcciones 4-5) como variable de
     solo lectura adicional, aunque sea con un valor fijo o una
     oscilación simple por ahora.
   - Cada actuador nuevo necesita: su propio canal Modbus en CODESYS,
     su variable mapeada, y su "piloto" en el HMI.

3. **Comportamiento ante pérdida de comunicación** (el ítem pendiente
   del checklist de arriba) — con el HMI ya es visualmente evidente
   si se agrega un indicador de "conexión perdida" cuando el canal
   Modbus entra en timeout.

4. Cuando esto esté sólido, recién ahí conectar `modelo_secado.py`
   real en vez de la planta de juguete (ver sección 0 de
   `python/modbus_server.py`).

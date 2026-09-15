# Comunicación CODESYS ↔ Python vía Modbus TCP (con HMI) — funcionando end-to-end

**Estado: funcionando end-to-end, v1 completa (6 variables), verificado
en CODESYS real.** v0 verificada y evidenciada el 9-10 sept 2026 (1
variable + 1 comando, proyecto `ModbusPhytoon.project`, CODESYS SP15).
v1 (14-15 sept 2026) amplía el lado Python con una interfaz de planta
modular (`Plant`/`ToyPlant` en `modbus_server.py`, ver su docstring)
para poder enchufar `modelo_secado.py` más adelante sin tocar el mapa
de registros ni CODESYS, más 4 variables/comandos nuevos (`fan_cmd`,
`RH_ambient`, `plant_mode`, `safety_ok`) y el watchdog de pérdida de
comunicación que quedaba pendiente en el checklist.

**15 sept 2026 — proyecto CODESYS rehecho desde cero en SP9.** Se
desinstaló CODESYS SP15 (problemas con OPC) y solo quedó SP9
disponible. Como el proyecto viejo (`ModbusPhytoon.project`) se armó en
SP15, se rehizo un proyecto nuevo, `SecadoCafe_ModbusV1.project`, en
SP9, con las 6 variables de v1 desde el inicio en vez de solo las 2 de
v0. **Verificado end-to-end en este proyecto nuevo** — ver sección 4.
En el camino se encontró y resolvió un bug real del driver Modbus TCP
Master de CODESYS SP9 con canales de más de 1 registro — ver punto 6
de la sección 0, es importante leerlo antes de tocar los canales de
`T_process`/`RH_ambient`.

Este documento complementa `python/modbus_server.py`. Ahí está el lado
Python (servidor); acá está el lado CODESYS (cliente + HMI) y el
procedimiento de prueba. Ver también la guía vigente, sección 3
("Arquitectura modular objetivo") y la "Prueba mínima del corte".

El proyecto CODESYS vigente es `codesys/SecadoCafe_ModbusV1.project`
(ábrelo con CODESYS **V3.5 SP9**, runtime "CODESYS Control Win V3"
también en SP9 — ver sección 0.1 sobre por qué la versión importa).
`ModbusPhytoon.project` (SP15) queda como referencia histórica de v0,
pero ya no es el proyecto activo porque SP15 no está instalado en este
equipo.

**15 sept 2026 — HMI v1 completo.** Se construyó la Visualization
(`HMI_Secado`) del proyecto SP9 con las 4 piezas mínimas acordadas:
valores en vivo (`T_process`, `RH_ambient`, `Setpoint`), estado
(pilotos `heater_on`/`fan_on` + texto de `plant_mode`), alarma
(`safety_alarm` con lámpara roja/gris + etiqueta "Alarma: comunicación
perdida") y tendencia (objeto `Trend` graficando `T_process` en
`MainTask`). Evidencia nueva capturada y en el repositorio:
`evidencia_hmi_modbus_v1_sp9.png` — reemplaza a `evidencia_hmi_modbus.png`
(v0/SP15) como evidencia vigente. Ver sección 5.

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

4. **En el HMI (Visualization), un elemento "Lámpara" solo acepta una
   variable BOOL, no un WORD.** `heater_cmd` es WORD (0/1), así que
   intentar conectarlo directo a la propiedad "Variable" de la lámpara
   da el error `C0032: ... no puede convertirse en el tipo 'POINTER TO
   BOOL'`. Solución: agregar una variable BOOL auxiliar en `PLC_PRG`
   (`heater_on : BOOL;`) y calcularla en el cuerpo del programa
   (`heater_on := (heater_cmd = 1);`), y conectar la lámpara a
   `PLC_PRG.heater_on` en vez de a `heater_cmd` directamente.

5. **Para meter un valor numérico en vivo dentro de un texto del HMI**
   (ej. `T_process: %.1f`), la variable va en la sección **"Variables
   de texto"** del panel de propiedades del elemento "Campo de texto"
   — específicamente en el campo que se llama igual que la sección
   (`Variables de texto` → `Variables de texto`). **No** va en
   "Textos dinámicos → Lista de texto": ese campo es para mapear un
   entero a una lista de textos fijos (como un enum), y si le pones
   ahí una variable REAL da el error `C0032: El tipo 'REAL' no puede
   convertirse en el tipo 'STRING'`.

6. **El driver Modbus TCP Master de CODESYS SP9 (paquete "Modbus" de
   CODESYS Store) no lee bien canales `Read Holding Registers` de
   longitud > 1.** Con un canal de longitud 2 (por ejemplo `T_process`
   en direcciones 0-1), el "Valor actual" en la pestaña de Asignación
   E/S se queda congelado en un valor fijo sin sentido (ej. `35669` en
   ambos registros, siempre el mismo número sin importar la dirección)
   y nunca se actualiza — aunque el driver reporte "En ejecución" sin
   errores en la pestaña Estado, y aunque un cliente Modbus de prueba
   externo (`pymodbus`) confirme que Python sí está sirviendo datos
   correctos y distintos en esas mismas direcciones. Los canales de
   longitud 1 (`heater_cmd`, `fan_cmd`, `plant_mode`, `safety_ok`) no
   tienen este problema.

   **Solución:** partir cada variable REAL (2 registros) en **dos
   canales separados de longitud 1**, uno por cada palabra, en vez de
   un solo canal de longitud 2. Es decir, para `T_process` (direcciones
   0-1): un canal `T_process_hi` (Read Holding Registers, dirección 0,
   longitud 1) y otro `T_process_lo` (dirección 1, longitud 1), cada
   uno mapeado a su propio elemento del array (`T_process_raw[0]` y
   `T_process_raw[1]`). El código ST de conversión a REAL no cambia en
   absoluto — solo cambia cómo se definen los canales Modbus. Ver
   sección 2 y 3.1 para el mapa de canales ya actualizado con este
   workaround. No se probó si SP15 tiene el mismo problema (en v0 el
   canal de `T_process` era de longitud 2 y sí funcionó en SP15), así
   que esto parece ser específico de esta instalación/versión de SP9.

## 1. Arquitectura y roles

| Rol | Papel Modbus | Por qué |
|---|---|---|
| **Python** (`modbus_server.py`) | Servidor / *slave* TCP | Publica el estado de la planta simulada y expone registros de comando. |
| **CODESYS** | Cliente / *master* TCP | Sondea las variables en su ciclo de tarea y escribe los comandos — igual que lo haría contra un sensor/actuador Modbus real. |

Esto respeta el reparto de capas de la guía (CODESYS = Controlador,
Python = Planta) y hace que, cuando se pase de la planta simulada a la
secadora física, en CODESYS solo haya que cambiar la IP del dispositivo
esclavo, no la arquitectura.

## 2. Mapa de registros (v1)

| Dirección Modbus | Tag | Tipo | Unidad | Sentido |
|---|---|---|---|---|
| 0-1 (2 registros) | `T_process` | REAL / float32 IEEE754 | °C | Python → CODESYS (solo lectura) |
| 2 (1 registro) | `heater_cmd` | WORD (0 o 1) | - | CODESYS → Python (solo escritura desde CODESYS) |
| 3 (1 registro) | `fan_cmd` | WORD (0 o 1) | - | CODESYS → Python (solo escritura desde CODESYS) |
| 4-5 (2 registros) | `RH_ambient` | REAL / float32 IEEE754 | % | Python → CODESYS (solo lectura) |
| 6 (1 registro) | `plant_mode` | WORD (0=RUN, 1=HOLD) | - | CODESYS → Python (Python aplica el modo; ver 2.1) |
| 7 (1 registro) | `safety_ok` | WORD (0 o 1) | - | Python → CODESYS (solo lectura; 0 = watchdog activado, ver 2.2) |

Direcciones 8-9 quedan reservadas para `M_coffee` (pendiente: requiere
`modelo_secado.py` real o el sensor físico de humedad, ninguno
conectado todavía a este servidor). Direcciones 10-19 libres para
variables futuras.

**Nota (SP9):** este mapa de *registros* Modbus no cambió, pero del
lado CODESYS SP9 cada variable REAL de 2 registros se implementa como
**dos canales de 1 registro cada uno**, no uno de longitud 2 — es el
workaround del punto 6 de la sección 0. Ver la tabla de canales en la
sección 3.1.

Unit ID / Slave ID: **1** (el servidor Python responde a cualquier ID
porque corre en modo `single=True`, pero usa 1 para que coincida con las
pruebas ya hechas).

### 2.1 `plant_mode`

CODESYS puede escribir `plant_mode=1` (HOLD) para forzar a la planta
simulada a ignorar `heater_cmd`/`fan_cmd` y simplemente relajarse hacia
el ambiente — útil para dejar la planta en un estado conocido sin
tener que dejar de escribir comandos. `plant_mode=0` (RUN, valor por
defecto) es operación normal.

### 2.2 `safety_ok` y comportamiento ante pérdida de comunicación

Este es el ítem que quedaba pendiente en el checklist de la sección 4:
el servidor Python ahora tiene un **watchdog**. Si no recibe ninguna
escritura en `heater_cmd`, `fan_cmd` o `plant_mode` durante más de 5 s
(configurable con `--watchdog-timeout`), asume que perdió comunicación
con CODESYS y:

1. Fuerza `heater_cmd`/`fan_cmd` efectivos a 0 para el cálculo de la
   planta (aunque el último valor escrito siga mostrándose en el
   registro — eso es intencional, para poder distinguir "lo último que
   pidió CODESYS" de "lo que realmente se está aplicando").
2. Publica `safety_ok = 0`.

**Pendiente del lado CODESYS:** esto cubre la mitad Python del
requisito. Falta, en el proyecto CODESYS, (a) mapear `safety_ok` a una
variable BOOL y mostrar una alarma/piloto de "comunicación perdida" en
el HMI cuando valga 0, y (b) configurar el timeout propio del canal
Modbus master (para que el master también se marque en error si Python
deja de responder del todo, no solo si dejó de recibir escrituras). Ver
sección 6.

## 3. Paso a paso en CODESYS (v0, ya hecho — base para v1)

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

### 3.1 Canales v1 en CODESYS — hecho (15 sept 2026, `SecadoCafe_ModbusV1.project`, SP9)

Tabla de canales **tal como quedaron implementados**, ya con el
workaround del punto 6 de la sección 0 (cada REAL de 2 registros
partido en dos canales de 1 registro):

| Canal | Access type | Dirección | Longitud | Tipo | Variable PLC |
|---|---|---|---|---|---|
| `T_process_hi` | Read Holding Registers (FC03) | 0 | 1 | WORD | `T_process_raw[0]` |
| `T_process_lo` | Read Holding Registers (FC03) | 1 | 1 | WORD | `T_process_raw[1]` |
| `heater_cmd` | Write Single Register (FC06) | 2 | 1 | WORD | `heater_cmd` |
| `fan_cmd` | Write Single Register (FC06) | 3 | 1 | WORD | `fan_cmd` |
| `RH_ambient_hi` | Read Holding Registers (FC03) | 4 | 1 | WORD | `RH_ambient_raw[0]` |
| `RH_ambient_lo` | Read Holding Registers (FC03) | 5 | 1 | WORD | `RH_ambient_raw[1]` |
| `plant_mode` | Write Single Register (FC06) | 6 | 1 | WORD | `plant_mode` |
| `safety_ok` | Read Holding Registers (FC03) | 7 | 1 | WORD | `safety_ok` |

Los dos canales `_hi`/`_lo` de cada REAL se combinan en `PLC_PRG` con
el mismo `UNION` `U_WORDS_TO_REAL` del paso 6, sin cambios respecto al
código original de v0 — el split es solo a nivel de canales Modbus, no
de lógica ST.

**Verificado:** `T_process` y `RH_ambient` muestran valores reales y
coherentes en el Watch de CODESYS (ej. `T_process=48.8°C`,
`RH_ambient=50.1%`), coincidiendo con la consola de Python, y el lazo
completo (`T_process` sube con `heater_cmd=1`, calculado por la
lógica bang-bang) quedó confirmado.

**Hecho el 15 sept 2026 (ver sección 5):** HMI visual completo y
evidencia recapturada (`evidencia_hmi_modbus_v1_sp9.png`).

**Pendiente todavía, sin bloquear lo anterior:**
- Probar el watchdog con CODESYS real (detener `modbus_server.py` y
  confirmar que la alarma se enciende en el HMI) — ver sección 4.1 y 6.
- Configurar el timeout propio del canal Modbus master en CODESYS.

## 4. Checklist de la "prueba mínima del corte"

Copiado de la guía vigente:

- [x] Python y CODESYS intercambian datos en ambos sentidos. **Verificado
      9-10 sept 2026** (v0, SP15) y **re-verificado 15 sept 2026** con
      las 6 variables de v1 en `SecadoCafe_ModbusV1.project` (SP9):
      `T_process`, `RH_ambient`, `heater_cmd`, `fan_cmd`, `plant_mode`,
      `safety_ok` intercambiándose correctamente entre
      `modbus_server.py` y CODESYS.
- [x] El comando (`heater_cmd`) cambia el estado del simulador
      (`T_process`), no solo una variable decorativa — confirmado en
      ambas versiones: `T_process` sube en Python cuando CODESYS
      escribe `heater_cmd=1`, y CODESYS lee ese mismo valor de vuelta
      (verificado con valores reales, ej. `T_process=48.8°C` con
      `heater_cmd=1` porque `48.8 < setpoint=50`).
- [x] Frecuencia de actualización y unidades documentadas (este
      documento + docstring de `modbus_server.py`).
- [x] Procedimiento reproducible desde cero (este documento, incluida
      la sección 0 con los errores más comunes — ahora con el bug del
      driver SP9 del punto 6, encontrado y resuelto reproduciendo el
      proyecto desde cero el 15 sept 2026).
- [x]/[ ] Pérdida de comunicación con comportamiento definido —
      **resuelto del lado Python (14 sept 2026).** `modbus_server.py`
      implementa un watchdog: si no recibe escrituras de
      `heater_cmd`/`fan_cmd`/`plant_mode` por más de 5 s, fuerza los
      actuadores a valor seguro (0) y publica `safety_ok = 0`. Probado
      localmente con un cliente Modbus de prueba (ver sección 4.1).
      **Pendiente en CODESYS:** mapear `safety_ok` a una alarma visible
      en el HMI (el canal ya existe y se lee bien, ver sección 3.1) y
      configurar el timeout propio del canal master — ver sección 2.2.
- [x] Evidencia en el repositorio para v1/SP9. `codesys/evidencia_hmi_modbus_v1_sp9.png`
      (15 sept 2026) — HMI completo del proyecto SP9 en vivo:
      `T_process=49.7°C`, `RH_ambient=59.8%`, `Setpoint=50.0°C`,
      pilotos de heater/fan, modo RUN, alarma "Planta en funcionamiento"
      en verde (sin pérdida de comunicación) y tendencia de `T_process`
      mostrando el ciclo bang-bang alrededor del setpoint.
      `codesys/evidencia_hmi_modbus.png` (v0/SP15, `T_process: 44.2`,
      10 sept 2026) se conserva como evidencia histórica de ese hito.

### 4.1 Verificación de v1

**14 sept 2026, solo del lado Python** (antes de tener CODESYS
reconectado): se probó `modbus_server.py` con un cliente Modbus de
prueba que simula lo que hace CODESYS — escribir `heater_cmd=1`
durante unos segundos (`T_process` sube, confirmado en consola) y
luego dejar de escribir por completo (a los ~3 s del timeout
configurado en la prueba, `safety_ok` pasa a 0 y `T_process` empieza a
bajar aunque el último `heater_cmd` escrito siguiera en 1 —
exactamente el comportamiento esperado del watchdog).

**15 sept 2026, end-to-end con CODESYS real:** proyecto
`SecadoCafe_ModbusV1.project` (SP9) creado desde cero con las 6
variables, canales configurados (con el workaround de canales
partidos del punto 6 de la sección 0), mapeo IO completado, código ST
compilado sin errores. Verificado en el Watch de CODESYS: `T_process`
y `RH_ambient` con valores reales y variables (no los `35669` fijos
del bug), y la lógica bang-bang de `PLC_PRG` respondiendo
correctamente a `T_process`. **Pendiente:** repetir específicamente la
prueba del watchdog (detener `modbus_server.py` y confirmar que
`safety_ok` se refleja en CODESYS) con este proyecto nuevo — antes solo
se probó con un cliente de prueba, no con CODESYS real.

## 5. HMI en CODESYS

**v0 (SP15, `ModbusPhytoon.project`) — hecho:** Visualization
(`HMI_Secado`) con un campo de texto mostrando `T_process` en vivo
(formato `%.1f`) y una lámpara que se enciende cuando `heater_cmd = 1`
(vía la variable auxiliar `heater_on`, sección 0.4). Cumple lo que pide
la guía como mínimo de "HMI con... estado", pero es la versión vieja
en SP15.

**v1 (SP9, `SecadoCafe_ModbusV1.project`) — hecho (15 sept 2026).**
Visualization completa con las 4 piezas del mínimo de la guía
(sección 9.2):

- **Valores en vivo:** campos de texto con `T_process` (°C),
  `RH_ambient` (%) y `Setpoint` (°C), mismo patrón de "Variables de
  texto" que en v0 (sección 0.5).
- **Estado:** pilotos de `heater_on`/`fan_on` (mismo patrón de
  variable BOOL auxiliar que en v0, sección 0.4) y texto del
  `plant_mode` (0=RUN, 1=HOLD).
- **Alarma:** lámpara conectada a `safety_alarm := (safety_ok = 0)`,
  con imagen roja para el estado de alarma (verde/gris en operación
  normal) y etiqueta fija "Alarma: comunicación perdida".
- **Tendencia:** objeto de grabación `HMI_Trend3` (variable
  `PLC_PRG.T_process`, tarea `MainTask`, sin trigger — grabación
  continua) enlazado a un elemento visual `Trend` en el lienzo.

Evidencia: `codesys/evidencia_hmi_modbus_v1_sp9.png`. Se observó el
ciclo bang-bang esperado (`T_process` sube con `heater_cmd=1`, baja al
superar el `setpoint` y apagarse el heater) reflejado como un patrón
escalonado en la tendencia — consistente con el control on/off de
`PLC_PRG` (sección 3, paso 6).

## 6. Plan para la siguiente sesión (subir complejidad)

**Hecho el 14-15 sept 2026:**
- Lado Python: interfaz de planta modular (`Plant`/`ToyPlant`),
  `fan_cmd`, `RH_ambient`, `plant_mode` y `safety_ok` + watchdog de
  pérdida de comunicación. Ver docstring de `python/modbus_server.py`.
- Lado CODESYS: proyecto `SecadoCafe_ModbusV1.project` (SP9) rehecho
  desde cero con las 6 variables, canales, mapeo IO y código ST
  funcionando y verificados end-to-end (sección 3.1 y 4.1). Se
  encontró y resolvió el bug del driver SP9 con canales multi-registro
  (sección 0, punto 6).
- HMI visual v1 completo (valores en vivo, estado, alarma, tendencia)
  y evidencia recapturada. Ver sección 5.

Pendiente, en orden:

1. **Probar el watchdog con CODESYS real** (no solo con el cliente de
   prueba): detener `modbus_server.py` y confirmar que la alarma
   (`safety_alarm`) se enciende en el HMI y `T_process` empieza a
   bajar aunque el último `heater_cmd` siga en 1.
2. **Configurar el timeout propio del canal Modbus master en CODESYS**
   (para que el master se marque en error si Python deja de responder
   del todo, complementando el watchdog que ya corre del lado Python).
3. **Conectar `modelo_secado.py` real** en vez de `ToyPlant`: crear una
   clase `ModeloSecadoPlant(Plant)` en `modbus_server.py` que envuelva
   la cinética de secado real y la dinámica térmica/energética, y
   cambiarla en `main()`. Esto es lo que habilita `M_coffee`
   (direcciones 8-9, hoy reservadas y sin implementar) con un valor
   real en vez de un placeholder.

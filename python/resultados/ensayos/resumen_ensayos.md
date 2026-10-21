# Ensayos de fallo F1–F5 (21 oct 2026)

Generado por `python/graficas_ensayos.py` a partir de los CSV de `modbus_server.py --log-csv`, con Python + CODESYS v8 + FluidSIM reales (factor 540, inicio 08:00, perfil REF, caudal 100 %). F4 (recuperación) está dentro de F1 y F2.

## F1. CODESYS detenido (Debug > Stop) y recuperación

Archivo `F1_codesys.csv` (229 filas, 16:49:55–16:53:46).

| Hora | Duración real [s] | Tiempo de planta [h] | T proceso [°C] | T amb. al final [°C] | Resistencia en 0 a los [s] | Humedad [% b.h.] | Energía [kWh] | t secado [h] | t parado [h] | Reanuda |
|---|---|---|---|---|---|---|---|---|---|---|
| 16:51:11 | 32.4 | 11.25 → 16.05 | 49.8 → 21.3 | 19.8 | 0 | 43.92 → 43.57 | 31.96 → 32.02 | 8.85 → 8.85 | 0.30 → 5.10 | 16:51:55 (E 32.78 kWh, M 43.46 %) |
| 16:52:10 | 28.4 | 19.95 → 24.15 | 49.9 → 17.2 | 18.1 | 0 | 40.39 → 40.05 | 42.94 → 43.00 | 11.10 → 11.10 | 6.75 → 10.95 | 16:52:41 (E 43.76 kWh, M 39.97 %) |

## F2. FluidSIM detenido y recuperación

Archivo `F2_fluidsim.csv` (133 filas, 16:55:15–16:57:29).

| Hora | Duración real [s] | Tiempo de planta [h] | T proceso [°C] | T amb. al final [°C] | Resistencia en 0 a los [s] | Humedad [% b.h.] | Energía [kWh] | t secado [h] | t parado [h] | Reanuda |
|---|---|---|---|---|---|---|---|---|---|---|
| 16:56:02 | 46.6 | 6.90 → 13.80 | 50.1 → 23.8 | 22.4 | 1 | 49.40 → 48.98 | 19.41 → 19.95 | 5.10 → 5.25 | 1.80 → 8.40 | 16:56:54 (E 20.64 kWh, M 48.85 %) |

## F3. STOP desde la HMI

Archivo `F3_Stop.csv` (206 filas, 16:58:18–17:01:46).

| Hora | Duración real [s] | Tiempo de planta [h] | T proceso [°C] | T amb. al final [°C] | Resistencia en 0 a los [s] | Humedad [% b.h.] | Energía [kWh] | t secado [h] | t parado [h] | Reanuda |
|---|---|---|---|---|---|---|---|---|---|---|
| 16:59:18 | 6.1 | 8.85 → 9.75 | 50.0 → 26.5 | 26.2 | 0 | 49.99 → 49.81 | 14.47 → 14.50 | 3.90 → 3.90 | 0.30 → 1.05 | 16:59:24 (E 15.09 kWh, M 49.64 %) |
| 16:59:53 | 5.1 | 14.10 → 14.85 | 50.1 → 21.9 | 21.2 | 0 | 43.82 → 43.61 | 30.94 → 30.97 | 8.25 → 8.25 | 1.05 → 1.65 | 16:59:58 (E 31.67 kWh, M 43.44 %) |
| 17:00:35 | 8.1 | 20.25 → 21.45 | 49.9 → 16.5 | 16.4 | 0 | 35.19 → 34.83 | 56.14 → 56.20 | 13.65 → 13.65 | 1.65 → 2.55 | 17:00:43 (E 57.01 kWh, M 34.74 %) |
| 17:01:17 | 25.3 | 26.55 → 30.30 | 49.9 → 25.1 | 26.4 | 0 | 26.92 → 26.68 | 80.16 → 80.19 | 18.75 → 18.75 | 2.55 → 6.15 | 17:01:42 (E 80.77 kWh, M 26.56 %) |

Nota: al inicio de F3 (≈4.7 h de modelo) la máquina ventiló sin calentar porque CODESYS seguía en PARO del ensayo anterior y Python se reinició (su reloj volvió a 0 y la post-ventilación no terminaba). Corregido en `codesys/v8/SECUENCIA.st` el 21 oct 2026; no afecta los cuatro STOP evaluados.

## F5. Python detenido

Archivo `F4_python.csv` (50 filas, 17:02:27–17:03:17).

El CSV termina con la planta en SECADO normal: al cerrar Python no hay quién registre (la guía no exige que la planta siga calculando si Python termina). La respuesta de CODESYS está en `F5_hmi_python_caido.png`: «Comunicación Python: ERROR» y semáforo rojo (FALLA 1) por heartbeat congelado.

## Lectura

- F1: a los ~5 s sin comandos (`edad_comandos_s` > 5) Python aplica su política local: resistencia en 0, post-ventilación y reposo. El reloj de la planta sigue y T proceso sigue a T ambiente (ciclo día/noche). Al volver CODESYS, el lote continúa con la misma energía, humedad y tiempo de secado (F4).
- F2: FluidSIM detenido → `fluidsim_estado` = 3 y resistencia en 0 en ~1 s (FALLA 5, no emergencia). Al volver FluidSIM: START reconoce, los cilindros se resincronizan y START reanuda el lote (F4); la siguiente inversión del aire ocurre a las 6 h de secado efectivo.
- F3: cada STOP apaga la resistencia, ventila un ciclo y deja la máquina en PARO; `t_secado_h` no avanza en la parada y `t_parado_h` sí.
- F5: CODESYS detecta la caída de Python por el heartbeat y pasa a FALLA 1.

Limitaciones: es una función de software demostrada, no una certificación de seguridad funcional. F1 se hizo con *Debug > Stop* (la aplicación conserva su estado); un reinicio completo del runtime devolvería CODESYS a REPOSO.

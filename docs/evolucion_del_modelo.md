# Evolución del modelo y decisiones del proyecto

Resumen de cómo llegó el proyecto al estado actual y **por qué** se descartó
cada versión anterior. Sirve para la sección de metodología del documento
("se evaluó X, se descartó porque Y") y para responder preguntas del jurado.
Lo que ya no se usa está en `python/legacy/` (código) y en el historial de git.

## Línea de tiempo

| Fecha (2026) | Qué se hizo | Estado hoy |
|---|---|---|
| 7 sept | Modelos candidatos de capa delgada (Newton, Logarítmico, Midilli modificado) y ajuste con RMSE/MAE/R² contra Phitakwinai et al. (2019). Líneas base v0.1: patio con Newton (Eliseu, 2008) y solar activa con Logarítmico (Mackpayen et al., 2017). Primera estimación de energía (solo calor latente). | **Retirado** → `python/legacy/` |
| 9–10 sept | Prueba mínima Python ↔ CODESYS por Modbus TCP (v0: `T_process` y `heater_cmd`, planta de juguete, CODESYS SP15). | Superado por v1 |
| 14–15 sept | v1 de la comunicación: interfaz `Plant`, 6 variables, watchdog de Python; proyecto rehecho en CODESYS SP9. | Vigente (ampliado) |
| 23 sept | Primer modelo físico conectado a CODESYS: cámara concentrada + Midilli modificado generalizado (Phitakwinai, Tabla 3) con parámetros de relleno. Prueba concurrente Modbus + OPC/FluidSIM: GO. | **Retirado** (modelo); OPC vigente |
| 24 sept | `heartbeat` y `comm_error`: pérdida de comunicación cubierta en los dos sentidos. Protocolo estadístico de Monte Carlo (diseño pareado, potencia). | Vigente |
| 29 sept | **Modelo único de Roa–Cenicafé** para las tres estrategias; secador eléctrico de 80 kg c.p.s., 6 kW, lecho de 20 cm por capas (Thompson); RH ambiente y RH de proceso separadas; inversión del aire cada 6 h. | **Vigente** |
| 4 oct | Clima de Chinchiná con datos reales (NASA POWER 2005–2024, AR(1), ciclo asimétrico). Recalibración de las líneas base con Cenicafé (Peñuela-Martínez et al., 2025). Equipos comerciales para la energía. **Lazo térmico local** (corrige la oscilación 22 ↔ 65 °C vista con el tutor). | **Vigente** |
| 5 oct | Validación contra datos independientes. Caudal variable (manipulada 2). Perfiles térmicos (factorial 3 × 3 + REF). Piloto (N = 130) y campaña Monte Carlo de 150 realizaciones. | **Vigente** |
| 6 oct | Organización del repositorio: código antiguo a `legacy/`, tabla de variables, README actualizados. | — |

## Decisiones y por qué

### 1. Un solo modelo cinético (Roa–Cenicafé) en vez de uno por estrategia

- **Antes:** cada estrategia tenía su modelo (Newton para el patio, Logarítmico
  para la activa, Midilli para la supervisada).
- **Problema:** Newton y Logarítmico no dependen de la temperatura ni de la
  humedad del aire, así que no responden al clima ni a sus perturbaciones (no
  sirven para Monte Carlo). Midilli generalizado solo es válido entre 50 y 70 °C
  y 10–30 % HR; el patio y la activa trabajan a 16–40 °C y 40–100 % HR. Además,
  comparar estrategias con modelos distintos mezcla el efecto del modelo con el
  de la estrategia.
- **Decisión (29 sept):** isoterma de Roa (Trejos et al., 1989) + ecuación de
  capa delgada de Roa (SECAFÉ, Parra-Coronado et al., 2008). Es colombiana,
  para café pergamino, y cubre todo el dominio de las tres estrategias. Solo
  cambian las condiciones de aire que recibe el café.
- **Phitakwinai et al. (2019)** quedó como **validación independiente**
  (`python/validacion_modelo.py`, `data/reference/validacion_modelo.md`).

### 2. Lecho por capas (Thompson) en vez de capa delgada para el secador

Con 0.1 m³/min/kg el aire se satura dentro de un lecho de 20 cm. Si cada grano
"viera" el aire del plenum, el secado saldría unas 2 veces más rápido de lo
físicamente posible. El modelo de Thompson (el de SECAFÉ) divide el lecho en
capas de 2.5 cm y hace el balance de humedad y calor del aire entre ellas
(`python/lecho_secado.py`).

### 3. Resistencia eléctrica en vez de solar o biomasa en la supervisada

Permite controlar la temperatura (lo que el proyecto quiere analizar) y
dimensionarla con equipos comerciales para el costo del objetivo 4
(`data/reference/secador_electrico_dimensionamiento.md`).

### 4. Lazo térmico local (corrección del 4 oct)

Con la simulación acelerada (factor 540), CODESYS decide cada 540 s de modelo,
y el plenum responde en ~106 s: el todo/nada solo veía los extremos (22 y
65 °C). Regla de muestreo: el periodo debe ser mucho menor que la constante de
tiempo (Åström & Wittenmark, 1997). Solución en dos niveles, como un secador
real: termostato del ducto en Python cada 1 s (campo) y CODESYS en supervisión
(RUN/HOLD, ventilador, inversión, parada, alarmas). A tiempo real (factor 1) el
PLC puede cerrar el lazo (`--lazo-termico plc`).

### 5. Caudal como segunda variable manipulada (5 oct)

Respuesta a la pregunta del asesor por las "variables activas". González et
al. (2010) controlan el caudal con variador para ahorrar energía. Rango 30–100 %
(mínimo de operación del ventilador centrífugo).

### 6. Perfiles térmicos definidos antes del piloto (5 oct)

P1 45 °C constante; P2 55 → 35 °C y P3 35 → 55 °C con cambio al 30 % b.h. (de
Oliveira et al., 2018); caudal 30/75/100 %; REF = 50 °C y 100 % (Cenicafé).

### 6b. Corrección de los perfiles escalonados (21 oct 2026)

El 55 °C de P2/P3 excedía el límite de 50 °C del grano que adopta el trabajo
(González et al., 2010) y no correspondía a la fuente (de Oliveira et al., 2018,
usó 50 → 35 y 35 → 50 °C). La campaña mostró 6–22 h de grano > 50 °C. Se
corrigió a P2 50 → 35 °C y P3 35 → 50 °C y se repitieron el piloto y la campaña
(mismas semillas). Resultados del diseño inicial: `python/resultados/diseno_inicial_55/`.
Detalle en `python/perfiles_termicos.py`.

### 7. N de la campaña por potencia y precisión, no arbitrario

N = max(potencia, precisión ±6 h, 30) = 130 con el piloto; se extendió a 150
porque la estrategia pasiva no cumplía el criterio de convergencia
(`python/metodologia_estadistica_monte_carlo.md`, secciones 7 y 8).

## Qué hay en `python/legacy/`

| Archivo | Qué era | Por qué se retiró |
|---|---|---|
| `modelo_secado.py` | Newton, Logarítmico y Midilli modificado (v0.1) | No responden a T/HR (Newton, Log.); Midilli fuera de dominio |
| `ajuste_modelos.py` | Ajuste RMSE/MAE/R² contra Phitakwinai | La selección del modelo cambió a Roa |
| `cinetica_dinamica.py` | Midilli generalizado dinámico (planta del 23 sept) | Válido solo en 50–70 °C / 10–30 % HR |
| `estimacion_energia.py` | Piso termodinámico (solo calor latente) | Reemplazado por `balance_energia.py` (equipos reales) |
| `lineas_base_v01.py` | Patio (Newton) y activa (Logarítmico) v0.1 | No responden al clima |
| `*.ipynb` | Notebooks de la semana 5 | Usan los módulos de arriba; no se mantienen |

No se borra porque documenta el proceso y sirve si el jurado pregunta por qué
no se usó un modelo más simple. No se mantiene ejecutable.

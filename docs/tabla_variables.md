# Tabla de variables del sistema

Versión: 21 oct 2026 (la planta ya no se congela en HOLD; registros 27–39 de relojes y estado; registro 40 de enlace FluidSIM; CODESYS v8). Fuente única de verdad en el código:
`python/modbus_server.py` (mapa de registros), `python/dinamica_termica.py`
(`ParametrosSecador`), `python/control_supervisado.py` (`ParametrosControl`),
`python/cinetica_roa.py`, `python/generador_ambiente.py` y
`python/campana_montecarlo.py` (`CAMPOS`). Si un valor cambia allí, se
actualiza aquí.

## 1. Clasificación de variables (para el documento)

| Tipo | Variable | Unidad | Quién la fija o la mide |
|---|---|---|---|
| **Controlada** | Temperatura del aire de secado, `T_process` (plenum, entrada al lecho) | °C | Termostato todo/nada contra la consigna del perfil térmico que calcula el PLC (`setpoint_cmd`, registro 26) |
| **Controlada (criterio de parada)** | Humedad del café: promedio del lote `M_coffee` y capa más húmeda `M_coffee_max` | % b.h. | Parada con promedio ≤ 11 % **y** capa más húmeda ≤ 12 % |
| **Manipulada 1** | Potencia de la resistencia (encendida/apagada, 6 kW), `heater_cmd` / `heater_duty` | – / % | Lazo térmico |
| **Manipulada 2** | Caudal del ventilador, `fan_speed_pct` → `caudal` | % / m³/min | Elegido en la HMI antes de START (30, 75 o 100 % de 8 m³/min), fijo durante el lote |
| **Referencia** | Consigna de temperatura `setpoint_cmd` | °C | Perfil elegido en la HMI (REF 50, P1 45, P2 55→35, P3 35→55 °C; cambio al 30 % b.h.) |
| **Manipulada discreta** | Sentido del aire en el lecho, `flow_dir_cmd` | 0/1 | Inversión cada 6 h (SECAFÉ, 2008) |
| **Perturbación** | Temperatura ambiente | °C | Clima de Chinchiná (Naranjal + NASA POWER), aleatorio día a día |
| **Perturbación** | Humedad relativa ambiente `RH_ambient` (vía presión de vapor `ea`) | % | Ídem |
| **Perturbación** | Humedad inicial del café M0 | % b.h. | Uniforme 52–56 % por realización |
| **Variable de proceso (medida)** | HR del aire de secado `RH_process` | % | Psicrometría del aire exterior calentado |
| **Estado / supervisión** | `plant_mode`, `safety_ok`, `heartbeat`, `tiempo_proceso_h` | – | Ver sección 2 |

"Variables activas" en la conversación con el asesor = las **manipuladas**
(1 y 2): son las que el sistema supervisado mueve para seguir el perfil
térmico. Confirmar la interpretación con el asesor.

## 2. Mapa Modbus TCP (Python = servidor, CODESYS = cliente)

Holding registers, puerto 5020, periodo del servidor 1 s. Los REAL ocupan 2
registros (palabra alta primero); en CODESYS se arma el `UNION` con la
palabra **baja** en `words[0]` (ver `codesys/comunicacion_modbus.md`, sección 0).

| Dir. | Tag | Tipo | Unidad | Sentido | Rango típico | Variable en `PLC_PRG` (v7) |
|---|---|---|---|---|---|---|
| 0–1 | `T_process` | REAL | °C | Python → CODESYS | 15–60 | `T_process` |
| 2 | `heater_cmd` | WORD 0/1 | – | CODESYS → Python | 0/1 | `heater_cmd` |
| 3 | `fan_cmd` | WORD 0/1 | – | CODESYS → Python | 0/1 | `fan_cmd` |
| 4–5 | `RH_ambient` | REAL | % | Python → CODESYS | 40–100 | `RH_ambient` |
| 6 | `plant_mode` | WORD | 0 = RUN, 1 = HOLD | CODESYS → Python | 0/1 | `plant_mode` |
| 7 | `safety_ok` | WORD 0/1 | – | Python → CODESYS | 0/1 | `safety_ok` |
| 8–9 | `M_coffee` | REAL | % b.h. | Python → CODESYS | 11–56 | `M_coffee` |
| 10–11 | `tiempo_proceso_h` | REAL | h de modelo en RUN con ventilador (secado + inversión + enfriamiento) | Python → CODESYS | 0–100 | `tiempo_secado_h` |
| 12 | `heartbeat` | WORD | contador | Python → CODESYS | 0–65535 | `heartbeat_actual` |
| 13–14 | `RH_process` | REAL | % | Python → CODESYS | 5–100 | `RH_process` |
| 15 | `flow_dir_cmd` | WORD 0/1 | 0 = abajo→arriba, 1 = invertido | CODESYS → Python | 0/1 | `flow_dir_cmd` |
| 16–17 | `M_coffee_max` | REAL | % b.h. | Python → CODESYS | 11–56 | `M_coffee_max` |
| 18–19 | `heater_duty` | REAL | % | Python → CODESYS | 0–100 | `heater_duty` |
| 20 | `fan_speed_pct` | WORD | % del nominal | CODESYS → Python | 30–100 (0 = 100 %) | `fan_speed_pct` |
| 21 | `reset_lote_cmd` | WORD 0/1 | – | CODESYS → Python | pulso de 3 s (flanco 0→1 = nuevo lote) | `reset_lote_cmd` (v5) |
| 22–23 | `caudal` | REAL | m³/min | Python → CODESYS | 0–8 | `caudal_m3_min` |
| 24–25 | `energia_kWh` | REAL | kWh | Python → CODESYS | 0–~150 por lote | `energia_kWh` (v5) |
| 26 | `setpoint_cmd` | WORD | °C enteros | CODESYS → Python | 35–55 (0 = 50 °C por defecto) | `setpoint_cmd` (v7) |
| 27–28 | `tiempo_lote_h` | REAL | h de modelo desde "Nuevo lote" (incluye paradas) | Python → CODESYS | 0–200 | `t_lote_raw` (v8) |
| 29–30 | `tiempo_secado_h` | REAL | h con calentamiento permitido (secado efectivo); reloj de inversión desde v8 | Python → CODESYS | 0–100 | `t_secado_ef_raw` (v8) |
| 31–32 | `tiempo_parado_h` | REAL | h del lote sin RUN (paro, falla, fin, reposo) | Python → CODESYS | 0–200 | `t_parado_raw` (v8) |
| 33–34 | `tiempo_planta_h` | REAL | h desde que arrancó la planta (no se reinicia) | Python → CODESYS | 0–… | `t_planta_raw` (v8) |
| 35 | `estado_planta` | WORD | 0 REPOSO, 1 SECANDO, 2 VENTILANDO, 3 POST-VENT., 4 FALLA COMM | Python → CODESYS | 0–4 | `estado_planta` (v8) |
| 36–37 | `T_ambiente` | REAL | °C | Python → CODESYS | 10–35 | `T_amb_raw` (v8) |
| 38–39 | `hora_dia` | REAL | h (0–24) del reloj de la planta | Python → CODESYS | 0–24 | `hora_raw` (v8) |
| 40 | `fluidsim_estado` | WORD | 0 no informado, 1 vivo, 2 sin_fluidsim declarado, 3 enlace caído | CODESYS → Python | 0–3 | `fluidsim_estado_cmd` (v8) |

Modo de planta (21 oct 2026): el servidor arranca en HOLD. En HOLD (REPOSO, PARO, FIN DE SECADO, FALLA, EMERGENCIA) la resistencia y el ventilador quedan apagados, pero **la física sigue**: el reloj y el clima día/noche avanzan, la cámara y el café se enfrían hacia el ambiente y hay un secado residual pequeño por tiro natural (`data/reference/reposo_tiro_natural.md`). Hasta el 20 oct 2026 el modelo se congelaba en HOLD. En lazo local, `heater_cmd` es el permiso de calentar: en ENFRIAMIENTO el ventilador sigue y la resistencia no enciende.

Seguridad: si CODESYS no escribe en 5 s, Python aplica su política de
fallo local: resistencia apagada de inmediato, ventilador en
post-ventilación 10 min de modelo (`--post-ventilacion-min`) y luego
apagado; publica `safety_ok = 0` y la planta sigue integrando. Si `heartbeat` no cambia en 4 s,
CODESYS declara `comm_error` y apaga sus comandos.

## 3. Parámetros del modelo (fijos, con fuente)

| Parámetro | Valor | Fuente |
|---|---|---|
| Lote | 80 kg c.p.s. (158 kg húmedos a 55 % b.h.) | Decisión de diseño (29 sept 2026) |
| Humedad inicial nominal | 55 % b.h. | SECAFÉ (Parra-Coronado et al., 2008) |
| Humedad objetivo | 11 % b.h. (promedio); capa más húmeda ≤ 12 % | SECAFÉ (2008): almacenamiento seguro 10–12 % b.h. |
| Caudal nominal | 0.1 m³/min/kg → 8 m³/min | González, Sanz & Oliveros (2010) |
| Caudal mínimo | 30 % (2.4 m³/min) | Criterio propio de operación del ventilador (declarado) |
| Espesor del lecho | 20 cm, 8 capas de 2.5 cm (Thompson) | González et al. (2010); SECAFÉ (2008) |
| Resistencia | 6 kW (3 × 2 kW, Tempco) | `data/reference/secador_electrico_dimensionamiento.md` |
| Ventilador | 0.20 kW (S&P CBM/6-180/180-N-72W), potencia ∝ caudal³ | `data/reference/equipos_energia.md` |
| Setpoint de referencia | 50 °C | González et al. (2010) |
| Inversión del aire | cada 6 h | SECAFÉ (2008) |
| Isoterma de equilibrio | Roa, medida a 10–55 °C | Trejos, Roa & Oliveros (1989) |
| Cinética de capa delgada | Roa (m = 0.0143, n = 0.87898, q = 1.06439) | Parra-Coronado et al. (2008), SECAFÉ |
| Constante de tiempo del plenum | ≈ 106 s | Calculada (`dinamica_termica.py`) |
| Protección por sobretemperatura | 90 °C: abre la resistencia (ya no recorta el valor) | Criterio de protección (21 oct 2026) |
| Tiro natural (ventilador apagado) | ΔP = g·H·Δρ, H = 0.6 m; resistencia lineal anclada en 100 Pa a 8 m³/min | ASHRAE (2021); ASABE D272; `reposo_tiro_natural.md` |
| Pérdidas del lecho en reposo | h = 4 W/m²K sobre 2.2 m² | Incropera et al. (2007); criterio propio |
| Post-ventilación ante fallo de comunicación | 10 min de modelo | Criterio propio declarado |
| Incremento solar pasiva | 4.4 °C máx. | Calibrado con Peñuela-Martínez et al. (2025): 10.6 días |
| Incremento solar activa | 12.5 °C máx. | Reducción 47.5 % vs. pasiva (Duque-Dussán et al., 2026; Meja et al., 2025) |
| Área solar | 11.1 m² (7.2 kg c.p.s./m², capa de 2 cm) | Peñuela-Martínez et al. (2025) |
| Extractor de la activa | 40 W, 06:00–18:00 | S&P HCM-225N; Madhava et al. (2017) |
| Radiación media | 4.582 kWh/m²/día | Cenicafé 54(2) |

## 4. Clima de Chinchiná (perturbaciones)

| Variable | Valor | Fuente |
|---|---|---|
| T mínima / máxima media | 16.4 / 26.8 °C | Cenicafé 49(4), 1998 (estación Naranjal) |
| Hora de T mín / T máx | 05:30 / 15:30 | Guzmán & Ramírez (2004), Cenicafé 55(2) |
| σ día a día T mín / T máx | 0.97 / 1.36 °C | NASA POWER 2005–2024 (`variabilidad_clima.py`) |
| Persistencia AR(1) T mín / T máx | 0.49 / 0.39 | Ídem |
| σ residual de `ea` / persistencia | 4 % / 0.22 | Ídem |

Fuentes completas: `data/reference/chinchina_clima_fuentes.md`.

## 5. Salidas de la campaña Monte Carlo (`resultados.csv`)

| Columna | Unidad | Significado |
|---|---|---|
| `t_obj_h` | h | Tiempo hasta la humedad objetivo (métrica primaria) |
| `censurado` | 0/1 | 1 si no llegó antes de 720 h |
| `m_final_bh_pct`, `capa_min_bh_pct`, `capa_max_bh_pct` | % b.h. | Humedad final del lote y de las capas extremas |
| `tasa_secado_pct_h` | % b.h./h | (M0 − M final) / tiempo |
| `elec_kwh`, `resistencia_kwh`, `ventilador_kwh` | kWh | Energía eléctrica comprada y su reparto |
| `solar_kwh`, `total_kwh` | kWh | Radiación sobre el área solar; eléctrica + solar |
| `kwh_por_kg_cps` | kWh/kg c.p.s. | Energía comprada por kg de café seco (insumo del objetivo 4) |
| `sec_total_kj_kg`, `sec_comprada_kj_kg` | kJ/kg de agua | Consumo específico de energía |
| `agua_kg` | kg | Agua evaporada del lote |
| `eficiencia_pct` | % | Agua × calor latente / energía total |
| `iae_c_h`, `ise_c2_h`, `sobreimpulso_c`, `error_medio_c` | °C·h, °C²·h, °C, °C | Desempeño del lazo de T_process |
| `horas_grano_50c` | h | Horas con algún grano > 50 °C (filtro de calidad) |
| `horas_rehumectacion`, `horas_fuera_rango` | h | Horas con M < Me; horas fuera del dominio medido del modelo |
| `n_inversiones` | – | Inversiones del aire |
| `tmin_medio_c`, `tmax_medio_c`, `ea_medio_kpa`, `m0_bh_pct` | °C, kPa, % | Perturbaciones de la realización |

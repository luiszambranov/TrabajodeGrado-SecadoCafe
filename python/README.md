# /python — planta simulada, campaña Monte Carlo y análisis

Estado: 6 oct 2026. Modelo cerrado, campaña Monte Carlo ejecutada (150
realizaciones). Lo retirado está en `legacy/` (ver `legacy/README.md` y
`../docs/evolucion_del_modelo.md`).

## Cómo correr

```
pip install -r requirements.txt          # pymodbus==3.6.9, numpy, scipy, pandas, matplotlib

# Planta conectada a CODESYS (HMI). Por defecto: modelo, factor 540, puerto 5020
python modbus_server.py
python modbus_server.py --factor-aceleracion 1 --lazo-termico plc   # verificación a tiempo real
python modbus_server.py --plant toy                                 # solo prueba de comunicación

# Campaña Monte Carlo (sin CODESYS; se reanuda sola si se interrumpe)
python campana_montecarlo.py --n 10  --semilla-inicial 1    --salida resultados/piloto  --procesos 4
python analisis_montecarlo.py resultados/piloto --piloto       # -> calculo_N.md
python campana_montecarlo.py --n 150 --semilla-inicial 1001 --salida resultados/campana --procesos 4
python analisis_montecarlo.py resultados/campana              # -> resumen_resultados.md + figuras

# Figuras de los perfiles térmicos (-> ../figures/)
python graficas_perfiles.py

# Comprobaciones individuales (imprimen tablas)
python validacion_modelo.py          # validación contra datos independientes
python balance_energia.py            # balance de energía de las 3 estrategias, día nominal
python perfiles_termicos.py          # los 10 perfiles supervisados, día nominal
python escenario_sol_abierto.py      # calibración de la línea base pasiva
python linea_base_activa.py          # calibración de la línea base activa
python variabilidad_clima.py ../data/clima/POWER_Naranjal_diario_2005_2024.csv
```

`pymodbus` va fijado en 3.6.9: desde 3.7 cambió la ubicación de
`ModbusSlaveContext` y `modbus_server.py` deja de funcionar.

## Cómo encajan los módulos

```
generador_ambiente ─┬─> escenario_sol_abierto (PASIVA) ─┐
 (clima Chinchiná)  ├─> linea_base_activa    (ACTIVA) ─┤
                    └─> secador_electrico ──────────────┤   todas usan cinetica_roa
                          ├ dinamica_termica (plenum)   │
                          └ lecho_secado (Thompson)     │
                                                        │
 control_supervisado (réplica del PLC) + perfiles_termicos ─> campana_montecarlo ─> analisis_montecarlo
 planta_secado (misma física) ─> modbus_server ─> CODESYS
```

## Archivos

### Modelo físico

| Archivo | Qué hace |
|---|---|
| `cinetica_roa.py` | **Modelo cinético único**: isoterma de Roa para café pergamino (Trejos et al., 1989) + ecuación de capa delgada de Roa (SECAFÉ, Parra-Coronado et al., 2008). M0 = 55 % b.h., objetivo 11 % b.h. Paso por tiempo equivalente, rehumectación cuando M < Me, horas fuera de rango. Fuentes y erratas: `../data/reference/roa_cenicafe_isoterma_capa_delgada.md`. |
| `dinamica_termica.py` | `ParametrosSecador` (80 kg c.p.s., 0.1 m³/min/kg, lecho de 20 cm, resistencia de 6 kW, ventilador de 0.20 kW, caudal 30–100 %) y plenum con enclavamiento de flujo. Dimensionamiento: `../data/reference/secador_electrico_dimensionamiento.md`. |
| `lecho_secado.py` | Lecho de 8 capas de 2.5 cm (modelo de Thompson, como SECAFÉ) con la cinética de Roa en cada capa y balance de humedad y calor del aire. |
| `secador_electrico.py` | Núcleo físico del secador (plenum + lecho + contadores de energía, agua, horas con grano > 50 °C). Lo comparten `planta_secado.py` y `control_supervisado.py`, así que CODESYS y Monte Carlo ven la misma planta. |

### Clima (perturbaciones)

| Archivo | Qué hace |
|---|---|
| `generador_ambiente.py` | Clima de Chinchiná (estación Naranjal): ciclo diario asimétrico (mín. 05:30, máx. 15:30) y días perturbados con AR(1). |
| `variabilidad_clima.py` | Calcula σ y persistencia de T mín, T máx y `ea` a partir de la serie diaria NASA POWER 2005–2024 (`../data/clima/`). |

### Estrategias

| Archivo | Qué hace |
|---|---|
| `escenario_sol_abierto.py` | **PASIVA**: patio, capa de 2 cm, incremento solar de 4.4 °C calibrado contra 10.6 días de Cenicafé (Peñuela-Martínez et al., 2025). |
| `linea_base_activa.py` | **ACTIVA**: secador solar con ventilación forzada, incremento de 12.5 °C (reducción 47.5 % vs. pasiva; Duque-Dussán et al., 2026; Meja et al., 2025). |
| `control_supervisado.py` | **SUPERVISADA**: réplica en Python de `PLC_PRG` (termostato todo/nada cada 1 s, inversión del aire cada 6 h, parada con promedio ≤ 11 % y capa más húmeda ≤ 12 %). Acepta setpoint y caudal como funciones (perfiles). Calcula IAE, ISE, sobreimpulso y error en régimen. |
| `perfiles_termicos.py` | Los 10 perfiles supervisados: REF (50 °C, 100 %) + P1/P2/P3 × caudal 30/75/100 %. Justificación de cada nivel con fuentes. |

### CODESYS (tiempo real)

| Archivo | Qué hace |
|---|---|
| `modbus_server.py` | Servidor Modbus TCP (Python = esclavo). 24 registros, watchdog, `heartbeat`. Mapa completo en `../docs/tabla_variables.md`. |
| `planta_secado.py` | `ModeloSecadoPlant`: la física de `secador_electrico.py` detrás de la interfaz `Plant`. Lazo térmico local cuando la simulación va acelerada (corrección del 4 oct 2026). |

### Campaña, análisis, validación y energía

| Archivo | Qué hace |
|---|---|
| `campana_montecarlo.py` | Corre las 12 estrategias con el mismo clima y M0 por semilla (diseño pareado). Guarda `resultados.csv` y `metadatos.json` (comando, versiones, semillas). |
| `analisis_montecarlo.py` | Piloto → N; final → estadística descriptiva, tablas factoriales, Wilcoxon + Holm, filtro de calidad, Pareto, convergencia y figuras. |
| `metodologia_estadistica_monte_carlo.md` | Protocolo estadístico (sección 7) y resultado de la campaña (sección 8). |
| `balance_energia.py` | Energía eléctrica comprada, solar, SEC (kJ/kg de agua) y eficiencia de las 3 estrategias, con equipos comerciales. Base del objetivo 4. |
| `validacion_modelo.py` | Validación contra 4 casos independientes (laboratorio, patio, secador de lecho Escafé, secado solar). Ver `../data/reference/validacion_modelo.md`. |
| `graficas_perfiles.py` | Figuras de los perfiles térmicos con el instante de cambio (`../figures/`). |

### Resultados

| Carpeta | Contenido |
|---|---|
| `resultados/piloto/` | Piloto de 10 realizaciones (semillas 1–10) y `calculo_N.md` (N = 130). |
| `resultados/campana/` | Campaña final de 150 realizaciones (semillas 1001–1150): `resultados.csv`, `metadatos.json`, `resumen_resultados.md` y figuras (convergencia, cajas, Pareto). |

## Limitaciones declaradas

- El vapor que libera el café no se suma a la HR de proceso a la entrada
  (sí dentro del lecho, por el modelo de Thompson).
- Los incrementos solares de las líneas base son parámetros efectivos
  (incluyen días nublados); la radiación del balance es la media anual.
- La validación muestra sesgos conocidos por tipo de secado
  (`../data/reference/validacion_modelo.md`); no cambian el orden de las
  estrategias.
- Sensibilidad a climas extremos: pendiente de decidir con el asesor.

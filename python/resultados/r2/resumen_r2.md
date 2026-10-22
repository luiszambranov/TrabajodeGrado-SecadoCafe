# R2 · Límites de actuación (21 oct 2026)

Generado por `python/r2_limites_actuacion.py`. Misma física y control que la campaña (`corrida_instrumentada.py`, verificada: mismo tiempo y energía que `simular_supervisada`). Saturado = la resistencia está encendida todo el minuto y aun así T queda > 1 °C por debajo de la consigna. Margen = T máxima alcanzable − consigna (negativo = consigna físicamente inalcanzable en ese momento). Las métricas de régimen excluyen los primeros 15 min y los 15 min posteriores a cada cambio de consigna (P2/P3); ese transitorio se reporta como «Alcanza consigna» = minutos hasta quedar a ±1 °C (el peor de los transitorios).

## Límites declarados y comprobación

| Elemento | Límite | Comprobación | Fuente |
|---|---|---|---|
| Resistencia | 0 a 6.0 kW (3 × 2 kW a 220 V, Tecnirecambio; equivalente a Tempco 2 kW/240 V) | Enclavamiento con ventilador; potencia integrada = la realmente aplicada; corte térmico a 90 °C que abre la resistencia (ya no recorta T) | cotizaciones_bom.md; dinamica_termica.py |
| Tensión | 220 V (alimentación de la finca, supuesto declarado); P ∝ V² | Con 10 % de caída (198 V): 4.86 kW | Supuesto; sensibilidad abajo |
| Ventilador | 0 apagado; 30–100 % de 8 m³/min (0.1 m³/min/kg; González et al., 2010) | Sistema ≈100 Pa a 480 m³/h; el CBT-80N (0.37 kW, curvas hasta ~1 800 Pa) lo cubre. Con variador, Q ∝ n solo si la curva del sistema es cuadrática pura; el lecho es casi lineal, así que % de frecuencia ≠ % de caudal (se declara) | equipos_energia.md; cotizaciones_bom.md |
| Plenum | τ ≈ 106 s con caudal 100 % | La temperatura no salta: sube en ~2.5 min de 18 a 50 °C (con ventilador) y baja en horas sin él | dinamica_termica.py |
| Temperatura máxima alcanzable | T_amb + P/(ṁ·cp + UA) | Caudal 100 %: T_amb + 42.5 °C; 75 %: T_amb + 56.3 °C; 30 %: T_amb + 135 °C | Balance del plenum (Ec. 5) |
| Compuerta | Cambia de sentido solo con posición confirmada (final de carrera 1B1/1B2) | Tiempo máximo de maniobra 5 s (T_MOV_MAX); sin confirmación → FALLA 2. En la planta Python la inversión del aire es instantánea (simplificación declarada: 5 s frente a 6 h) | codesys/v8/SECUENCIA.st |

Potencia requerida por la Ec. 5 a 50 °C (T_amb 14.3 °C, FS 1.1): 5.53 kW; a 55 °C: 6.30 kW (> 6 kW instalados).

## 1. Barrido: 10 perfiles en clima nominal (C0) y frío (CT-, p5), arranque 00:00

| Perfil | Clima | Inicio | t fin [h] | kWh/kg | Saturado [h] | Racha sat. [h] | Fuera de banda [h] | Déficit máx. [°C] | Margen mín. [°C] | Duty medio [%] | Alcanza consigna [min] | Grano > 50 °C [h] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REF | C0 | 0.0 | 33.15 | 1.8045 | 0.0 | 0.0 | 0.0 | 0.14 | 8.42 | 69.2 | 3.0 | 0.0 |
| P1-C30 | C0 | 0.0 | 82.68 | 1.1064 | 0.0 | 0.0 | 0.0 | -0.08 | 104.93 | 17.7 | 2.0 | 0.0 |
| P1-C75 | C0 | 0.0 | 46.75 | 1.5029 | 0.0 | 0.0 | 0.0 | 0.09 | 27.04 | 41.4 | 3.0 | 0.0 |
| P1-C100 | C0 | 0.0 | 41.87 | 1.8453 | 0.0 | 0.0 | 0.0 | 0.13 | 13.42 | 55.4 | 3.0 | 0.0 |
| P2-C30 | C0 | 0.0 | 101.0 | 1.1126 | 0.0 | 0.0 | 0.0 | -0.05 | 99.93 | 14.6 | 5.0 | 0.0 |
| P2-C75 | C0 | 0.0 | 64.2 | 1.6503 | 0.0 | 0.0 | 0.0 | 0.1 | 22.04 | 32.8 | 3.0 | 0.0 |
| P2-C100 | C0 | 0.0 | 59.25 | 2.0781 | 0.0 | 0.0 | 0.0 | 0.14 | 8.42 | 43.4 | 3.0 | 0.0 |
| P3-C30 | C0 | 0.0 | 102.87 | 1.0312 | 0.0 | 0.0 | 0.0 | -0.05 | 99.93 | 13.2 | 2.0 | 0.0 |
| P3-C75 | C0 | 0.0 | 56.85 | 1.4706 | 0.0 | 0.0 | 0.0 | 0.09 | 22.04 | 33.0 | 2.0 | 0.0 |
| P3-C100 | C0 | 0.0 | 50.58 | 1.7521 | 0.0 | 0.0 | 0.0 | 0.14 | 9.66 | 42.7 | 2.0 | 0.0 |
| REF | CT- | 0.0 | 32.4 | 1.8627 | 0.0 | 0.0 | 0.0 | 0.16 | 6.76 | 73.3 | 3.0 | 0.0 |
| P1-C30 | CT- | 0.0 | 80.37 | 1.1533 | 0.0 | 0.0 | 0.0 | -0.09 | 102.85 | 19.0 | 2.0 | 0.0 |
| P1-C75 | CT- | 0.0 | 45.4 | 1.5686 | 0.0 | 0.0 | 0.0 | 0.1 | 25.32 | 44.6 | 3.0 | 0.0 |
| P1-C100 | CT- | 0.0 | 40.67 | 1.9305 | 0.0 | 0.0 | 0.0 | 0.12 | 11.76 | 59.9 | 3.0 | 0.0 |
| P2-C30 | CT- | 0.0 | 96.8 | 1.158 | 0.0 | 0.0 | 0.0 | -0.05 | 97.85 | 15.8 | 5.0 | 0.0 |
| P2-C75 | CT- | 0.0 | 61.18 | 1.7474 | 0.0 | 0.0 | 0.0 | 0.07 | 20.32 | 36.6 | 3.0 | 0.0 |
| P2-C100 | CT- | 0.0 | 56.38 | 2.162 | 0.0 | 0.0 | 0.0 | 0.16 | 6.76 | 47.8 | 3.0 | 0.0 |
| P3-C30 | CT- | 0.0 | 98.42 | 1.075 | 0.0 | 0.0 | 0.0 | -0.06 | 97.85 | 14.4 | 2.0 | 0.0 |
| P3-C75 | CT- | 0.0 | 54.7 | 1.5346 | 0.0 | 0.0 | 0.0 | 0.08 | 20.32 | 35.9 | 2.0 | 0.0 |
| P3-C100 | CT- | 0.0 | 48.72 | 1.8301 | 0.0 | 0.0 | 0.0 | 0.14 | 9.76 | 46.6 | 2.0 | 0.0 |

## 2. Caso más exigente

Seleccionado del barrido en CT- por horas de saturación y, a igualdad, por el menor margen físico: **REF** (Cenicafé: 50 °C constante, caudal 100 %). Se repite arrancando a las 18:00 para que la fase de consigna alta caiga en la madrugada.

| Perfil | Clima | Inicio | t fin [h] | kWh/kg | Saturado [h] | Racha sat. [h] | Fuera de banda [h] | Déficit máx. [°C] | Margen mín. [°C] | Duty medio [%] | Alcanza consigna [min] | Grano > 50 °C [h] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REF | CT- | 18.0 | 32.28 | 1.7858 | 0.0 | 0.0 | 0.0 | 0.16 | 6.76 | 70.5 | 3.0 | 0.0 |

## 3. Sensibilidades (tensión 10 % baja; ventilador de 0.37 kW)

| Caso | Perfil | Clima | Inicio | t fin [h] | kWh/kg | Saturado [h] | Racha sat. [h] | Fuera de banda [h] | Déficit máx. [°C] | Margen mín. [°C] | Duty medio [%] | Alcanza consigna [min] | Grano > 50 °C [h] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tension_-10% | REF | C0 | 0.0 | 33.2 | 1.8049 | 0.0 | 0.0 | 0.0 | 0.17 | 0.44 | 85.3 | 4.0 | 0.0 |
| tension_-10% | REF | CT- | 18.0 | 32.45 | 1.7884 | 1.95 | 1.95 | 1.95 | 1.18 | -1.18 | 86.7 | 3.0 | 0.0 |
| ventilador_0.37kW | REF | C0 | 0.0 | 33.15 | 1.8749 | 0.0 | 0.0 | 0.0 | 0.14 | 8.42 | 69.2 | 3.0 | 0.0 |
| tension_-10% | P1-C75 | C0 | 0.0 | 46.83 | 1.5032 | 0.0 | 0.0 | 0.0 | 0.07 | 16.47 | 51.0 | 3.0 | 0.0 |
| tension_-10% | P1-C75 | CT- | 18.0 | 45.28 | 1.5811 | 0.0 | 0.0 | 0.0 | 0.11 | 14.8 | 55.8 | 3.0 | 0.0 |
| ventilador_0.37kW | P1-C75 | C0 | 0.0 | 46.75 | 1.5448 | 0.0 | 0.0 | 0.0 | 0.09 | 27.04 | 41.4 | 3.0 | 0.0 |

## 4. Helada hipotética (-4 °C; fuera del clima del sitio)

| Perfil | Clima | Inicio | t fin [h] | kWh/kg | Saturado [h] | Racha sat. [h] | Fuera de banda [h] | Déficit máx. [°C] | Margen mín. [°C] | Duty medio [%] | Alcanza consigna [min] | Grano > 50 °C [h] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REF | HELADA | 0.0 | 37.2 | 2.883 | 36.95 | 36.95 | 36.95 | 14.88 | -14.88 | 100.0 | nan | 0.0 |
| P1-C30 | HELADA | 0.0 | 63.45 | 1.6358 | 0.0 | 0.0 | 0.0 | -0.01 | 75.71 | 34.2 | 3.0 | 0.0 |
| P1-C75 | HELADA | 0.0 | 36.1 | 2.3032 | 0.0 | 0.0 | 0.0 | 0.19 | 2.82 | 83.6 | 5.0 | 0.0 |

Nota: con -4 °C la isoterma y la cinética trabajan fuera de su dominio en el aire de entrada frío; el caso solo sirve para mostrar el límite del calentador, no para predecir el secado.


# Física con el ventilador apagado: tiro natural, enfriamiento y secado residual

Versión: 21 oct 2026. Responde a la guía de cierre (R4: «La planta no se pausa
con el PLC») y a la observación del asesor en la asesoría: «la física nunca
para; Python hace las veces del sistema real».

Código: `python/dinamica_termica.py` (`masa_aire_tiro_natural_kg_s`,
`paso_plenum`), `python/lecho_secado.py` (`LechoThompson.paso_reposo`),
`python/secador_electrico.py` (`_paso_reposo`, `nuevo_lote`),
`python/planta_secado.py` (relojes, estado y política de fallo).
Ensayo: `python/ensayo_continuidad_fisica.py` → `python/resultados/ensayos/continuidad_fisica.csv`
y `figures/ensayo_continuidad_fisica.png`.

## Qué cambió

| Antes (hasta el 20 oct 2026) | Ahora |
|---|---|
| En HOLD (REPOSO, PARO, FIN DE SECADO) el servidor avanzaba el modelo con dt = 0: no avanzaban el tiempo, el clima, la temperatura ni la humedad. | El tiempo físico avanza siempre. HOLD y la pérdida de comunicación solo cambian los comandos. |
| Con el ventilador apagado el lecho quedaba congelado (ni se secaba ni se enfriaba). | El lecho se enfría hacia el ambiente y se sigue secando un poco con el calor que conserva (tiro natural). |
| «Nuevo lote» creaba un secador nuevo a temperatura ambiente y reiniciaba el reloj del clima a medianoche. | El café nuevo entra a temperatura ambiente, pero la cámara conserva su temperatura y el reloj del clima sigue (día/noche). |
| La protección de 90 °C recortaba el número (min(T, 90)) sin quitar la potencia. | La protección abre la resistencia y el paso se integra sin potencia. |
| En lazo local la resistencia podía calentar en ENFRIAMIENTO. | `heater_cmd` de CODESYS es el permiso de calentar; en ENFRIAMIENTO solo hay ventilador. |

## Modelo en reposo (ventilador apagado)

1. **Tiro natural (efecto chimenea).** La columna de aire caliente plenum +
   lecho + cámara (altura H) produce un tiro ΔP = g·H·(ρ_amb − ρ_caliente)
   (ASHRAE, 2021, cap. 16). El caudal se obtiene con una resistencia del
   sistema **lineal** en el caudal, anclada en el punto de diseño
   (≈100 Pa a 8 m³/min, `equipos_energia.md`):
   Q = Q_nom · ΔP / ΔP_diseño. Para el lecho, la ecuación de Shedd
   (ASABE D272) es lineal a baja velocidad; para los accesorios turbulentos
   (ΔP ∝ Q²) la suposición lineal **subestima** el caudal natural, así que
   el secado residual queda del lado conservador. Si el aire interior no
   está más caliente que el exterior, el tiro es 0.
   Orden de magnitud: con 50 °C dentro y 20 °C fuera, ΔP ≈ 0.56 Pa y
   Q ≈ 0.04 m³/min (≈0.5 % del nominal).
2. **Pérdidas del lecho.** Cada capa pierde calor por convección natural
   hacia el ambiente: UA = h·A con h = 4 W/m²K (convección libre en gases,
   2–25 W/m²K; Incropera et al., 2007, tabla 1.1) y A = 2.2 m² (cara
   superior ≈1.3 m² + paredes ≈0.9 m²), repartido por igual entre las 8
   capas (simplificación). Con el ventilador encendido estas pérdidas
   (~9 W/K) son <7 % del término m_aire·c_p (~140 W/K) y se siguen
   despreciando, por lo que **la campaña Monte Carlo no cambia** (el
   ventilador nunca se apaga en ella; regresión verificada: 3 semillas × 12
   estrategias, diferencia 0).
3. **Secado residual.** El aire de tiro natural atraviesa el lecho con el
   mismo algoritmo de Thompson que con ventilador (Parra-Coronado et al.,
   2008): el café caliente sigue cediendo agua, limitado por la saturación
   del aire, o se rehumedece si el aire está más húmedo que su equilibrio.
4. **No se reutilizan coeficientes de convección forzada** en reposo.

## Política de fallo local (comunicación perdida)

Si CODESYS no escribe en 5 s: resistencia apagada de inmediato aunque haya
una consigna vieja; el ventilador, si venía encendido, sigue 10 min de
modelo de post-ventilación para sacar el calor del ducto y luego se apaga
(`--post-ventilacion-min`; 0 = todo apagado). Es un criterio propio,
declarado. La planta sigue integrando: un paro simulado es una función de
software demostrada, no una certificación de seguridad funcional.

## Relojes

| Reloj | Significado | Registro |
|---|---|---|
| `tiempo_planta_h` | Desde que arrancó la planta; nunca se reinicia | 33–34 |
| `tiempo_lote_h` | Desde «Nuevo lote»; incluye paradas | 27–28 |
| `tiempo_proceso_h` | En RUN con ventilador (secado + inversión + enfriamiento); lo usa CODESYS para la inversión cada 6 h y el enfriamiento | 10–11 |
| `tiempo_secado_h` | Con calentamiento permitido (secado efectivo) | 29–30 |
| `tiempo_parado_h` | lote − proceso (paro, falla, fin) | 31–32 |

El clima (T y HR ambiente) sigue la hora del día del reloj de la planta
(mín. 05:30, máx. 15:30; `chinchina_clima_fuentes.md`). `--hora-inicio`
fija la hora de arranque (por defecto 0 = medianoche, igual que la campaña,
para poder comparar CODESYS contra la réplica con la misma semilla).

## Resultado del ensayo (comandos emulados, factor 540, inicio 08:00)

| Evento | T proceso inicio → fin | Humedad promedio inicio → fin | Agua evaporada | Energía |
|---|---|---|---|---|
| PARO 3 h (HOLD) | 50.0 → 28.8 °C | 48.02 → 47.97 % b.h. | 0.14 kg | 0 kWh |
| ENFRIAMIENTO 0.75 h | 50.0 → 24.1 °C | 45.28 → 44.62 % b.h. | 1.55 kg | 0.15 kWh (ventilador) |
| COMUNICACIÓN PERDIDA 3.75 h | 50.0 → 19.9 °C | 43.26 → 42.87 % b.h. | 0.84 kg | 0.06 kWh (post-ventilación) |

Relojes al final: planta 18.75 h, lote 18.75 h, proceso 11.40 h, secado
10.65 h, parado 7.35 h.

Sensibilidad del secado residual en 3 h de paro (a las 14:00, lecho a ~38 °C):

| Supuesto | Agua residual | Caída de humedad |
|---|---|---|
| H = 0.6 m, h = 4 W/m²K (nominal) | 0.14 kg | 0.055 puntos |
| H = 0.3 m | 0.08 kg | 0.029 puntos |
| H = 1.2 m | 0.26 kg | 0.099 puntos |
| h = 2 W/m²K | 0.16 kg | 0.059 puntos |
| h = 8 W/m²K | 0.13 kg | 0.048 puntos |

Lectura: el secado residual es real pero pequeño (décimas de kg frente a
~65 kg de agua del lote); duplicar o reducir a la mitad los supuestos no
cambia el orden de magnitud. Lo que sí cambia de forma visible es la
temperatura: la cámara se enfría en ~1–2 h y el lecho, mucho más lento,
en varias horas.

Limitación declarada: con el lote descargado (estado DESCARGA → REPOSO)
Python no sabe que la bandeja salió y sigue simulando el lecho hasta el
siguiente «Nuevo lote»; no afecta los indicadores del lote, que se cierran
en FIN DE SECADO.

## Referencias

- ASABE. (2011). *ASAE D272.3 MAR1996 (R2011): Resistance to airflow of
  grains, seeds, other agricultural products, and perforated metal sheets*.
  American Society of Agricultural and Biological Engineers.
- ASHRAE. (2021). Ventilation and infiltration. En *ASHRAE Handbook—Fundamentals*
  (cap. 16). American Society of Heating, Refrigerating and Air-Conditioning
  Engineers.
- Incropera, F. P., DeWitt, D. P., Bergman, T. L., & Lavine, A. S. (2007).
  *Fundamentals of heat and mass transfer* (6.ª ed.). John Wiley & Sons.
- Parra-Coronado, A., Roa-Mejía, G., & Oliveros-Tascón, C. E. (2008).
  SECAFÉ Parte I: Modelamiento y simulación matemática en el secado mecánico
  de café pergamino. *Revista Brasileira de Engenharia Agrícola e Ambiental,
  12*(4), 415–427.
- Shedd, C. K. (1953). Resistance of grains and seeds to air flow.
  *Agricultural Engineering, 34*(9), 616–619.

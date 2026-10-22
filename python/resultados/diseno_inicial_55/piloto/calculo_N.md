# Piloto Monte Carlo: cálculo de N

Realizaciones del piloto: **10** (semillas 1–10).

## 1. Potencia (comparación primaria)

- Diferencia pareada ACTIVA − REF: media **102.6 h**, σ_d = **12.48 h**
- Δ = 12.0 h → d_z = Δ/σ_d = **0.96**
- N (t pareada, α = 0.05, potencia = 0.8) = 11 → Wilcoxon (÷ 0.955) = **12**

## 2. Precisión de cada media (semiancho IC95 ≤ Δ/2 = 6 h)

| Estrategia | Media t_obj [h] | DE [h] | N necesario |
|---|---|---|---|
| PASIVA (Solar pasiva) | 256.2 | 34.27 | 126 |
| ACTIVA (Solar activa) | 135.3 | 12.66 | 18 |
| REF (Cenicafé: 50 °C constante, caudal 100 %) | 32.6 | 0.93 | 1 |
| P1-C30 (45 °C constante, caudal 30 %) | 81.2 | 2.51 | 1 |
| P1-C75 (45 °C constante, caudal 75 %) | 46.0 | 1.40 | 1 |
| P1-C100 (45 °C constante, caudal 100 %) | 41.2 | 1.22 | 1 |
| P2-C30 (55 → 35 °C al 30 % b.h., caudal 30 %) | 94.4 | 2.33 | 1 |
| P2-C75 (55 → 35 °C al 30 % b.h., caudal 75 %) | 59.8 | 1.48 | 1 |
| P2-C100 (55 → 35 °C al 30 % b.h., caudal 100 %) | 55.3 | 1.46 | 1 |
| P3-C30 (35 → 55 °C al 30 % b.h., caudal 30 %) | 95.8 | 3.96 | 2 |
| P3-C75 (35 → 55 °C al 30 % b.h., caudal 75 %) | 52.1 | 2.15 | 1 |
| P3-C100 (35 → 55 °C al 30 % b.h., caudal 100 %) | 46.2 | 1.93 | 1 |

## 3. Resultado

**N de la campaña final = max(12, 126, 30) → 130 realizaciones**

Comando sugerido (semillas nuevas, independientes del piloto):

```
python campana_montecarlo.py --n 130 --semilla-inicial 1001 --salida resultados/campana --procesos 4
```

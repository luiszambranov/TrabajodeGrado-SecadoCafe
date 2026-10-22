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
| P2-C30 (50 → 35 °C al 30 % b.h., caudal 30 %) | 99.4 | 2.76 | 1 |
| P2-C75 (50 → 35 °C al 30 % b.h., caudal 75 %) | 63.0 | 1.55 | 1 |
| P2-C100 (50 → 35 °C al 30 % b.h., caudal 100 %) | 58.1 | 1.49 | 1 |
| P3-C30 (35 → 50 °C al 30 % b.h., caudal 30 %) | 100.2 | 4.04 | 2 |
| P3-C75 (35 → 50 °C al 30 % b.h., caudal 75 %) | 55.6 | 2.14 | 1 |
| P3-C100 (35 → 50 °C al 30 % b.h., caudal 100 %) | 49.5 | 1.94 | 1 |

## 3. Resultado

**N de la campaña final = max(12, 126, 30) → 130 realizaciones**

Comando sugerido (semillas nuevas, independientes del piloto):

```
python campana_montecarlo.py --n 130 --semilla-inicial 1001 --salida resultados/campana --procesos 4
```

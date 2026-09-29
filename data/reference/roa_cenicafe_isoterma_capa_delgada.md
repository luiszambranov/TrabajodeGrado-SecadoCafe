# Modelo Roa–Cenicafé: isoterma de equilibrio + ecuación de capa delgada (café pergamino)

Candidato a **modelo cinético único** del proyecto (decisión del 29 sept 2026,
paso 2 del informe de prioridades del asesor, 25 sept 2026). Cubre todo el
dominio T–HR que recorren las tres estrategias, a diferencia de Phitakwinai
et al. (2019), válido solo en 50–70 °C / 10–30 % HR.

## Fuentes

1. Trejos-Rodríguez, R., Roa-Mejía, G., & Oliveros-Tascón, C. E. (1989).
   Humedad de equilibrio y calor latente de vaporización del café pergamino
   y del café verde. *Cenicafé, 40*(1), 5–15.
   https://biblioteca.cenicafe.org/handle/10778/841
2. Parra-Coronado, A., Roa-Mejía, G., & Oliveros-Tascón, C. E. (2008).
   SECAFÉ Parte I: modelamiento y simulación matemática en el secado mecánico
   de café pergamino. *Revista Brasileira de Engenharia Agrícola e Ambiental,
   12*(4), 415–427. https://www.scielo.br/j/rbeaa/a/TZ7Sqw8RqZKny4fZh6dHW6j/?lang=es

## 1. Humedad de equilibrio (ecuación de Roa) — Trejos et al. (1989), ec. 2 y Tabla 3

```
Me = (p1·φ + p2·φ² + p3·φ³) · exp[(q0 + q1·φ + q2·φ² + q3·φ³)·(T + q4)]
```

- Me: humedad de equilibrio, **% base seca**; φ: HR decimal; T: °C.
- Café pergamino (*Coffea arabica* var. Caturra, desorción):

| p1 | p2 | p3 | q0 | q1 | q2 | q3 | q4 |
|---|---|---|---|---|---|---|---|
| 61.030848 | -108.371410 | 74.46105 | 0 | **-0.037049** | 0.070114 | -0.035177 | 0 |

- Ajuste reportado: SCR = 12.1, error estándar 0.54 %.
- Rango experimental: **T 5–55 °C** (datos a 10/25/40/55 °C), **HR 5–100 %**,
  M 4.8–25.2 % b.s. Obtenida por **desorción**.

**Errata en SECAFÉ (2008):** transcribe q1 = -0.03049. Verificado contra los
datos de la Tabla 1 de Trejos (1989): con -0.037049 el RMSE es 0.53 % b.s.
(SCR 10.6, coherente con el 12.1 reportado); con -0.03049 el RMSE es 3.26 %
(SCR 403). Se usa el valor original **-0.037049**.

## 2. Ecuación de secado en capa delgada (Roa, unificada) — SECAFÉ (2008), ec. 15

```
dM/dt = -m·q·(M - Me)·(Pvs - Pv)^n · t^(q-1)
m = 0.0143    n = 0.87898    q = 1.06439
```

- M, Me: % b.s.; Pvs, Pv: kPa; t: h.
- Interpretación usada: Pvs = presión de saturación a la temperatura del aire,
  Pv = presión parcial de vapor del aire → (Pvs − Pv) = déficit de presión de
  vapor del aire de secado. *(Supuesto a declarar: el artículo no lo detalla más.)*
- Rango declarado por los autores: **T 10–70 °C**; humedad "5 al 55 %" (el texto
  dice b.s., pero la determinación de López & Ospina (1990) partió de 55 % b.h.
  y la validación cubre 56.3 → 8.1 % b.h.; se interpreta como b.h.).
- Validación (SECAFÉ): secadores mecánicos reales de Cenicafé, R² > 0.93 en el
  92 % de los casos, humedad 56.3 → 8.1 % b.h.
- A condiciones constantes se integra como un modelo de Page con k dependiente
  del déficit de presión de vapor:

```
MR = (M - Me)/(M0 - Me) = exp(-k·t^q),   k = m·(Pvs - Pv)^n
```

## 3. Calor latente de vaporización — Trejos et al. (1989), ec. 6

```
L = (2502.4 - 2.4295·T)·[1 + 1.44408·exp(-21.6011·M)]     (kJ/kg; T °C; M decimal b.s.)
```

SECAFÉ (2008, ec. 14) transcribe 2.42958 y 21.5011; se usa el original.

## 4. Verificación cruzada propia (29 sept 2026)

**Contra Phitakwinai et al. (2019), Tabla 2 (Modified Midilli), tiempo hasta MR = 0.2:**

| T (°C) | HR (%) | Roa (h) | Phitakwinai (h) | Me Roa (% b.s.) |
|---|---|---|---|---|
| 50 | 10 | 11.6 | 11.4 | 4.4 |
| 60 | 10 | 7.8 | 7.7 | 4.2 |
| 70 | 10 | 5.4 | 5.9 | 4.1 |
| 50 | 20 | 12.8 | 12.7 | 6.6 |
| 60 | 20 | 8.6 | 9.4 | 6.3 |
| 70 | 20 | 6.0 | 7.3 | 6.0 |
| 50 | 30 | 14.3 | 14.5 | 7.9 |
| 60 | 30 | 9.6 | 10.2 | 7.5 |
| 70 | 30 | 6.7 | 8.0 | 7.1 |

Diferencia < 10 % a 50–60 °C; a 70 °C Roa es hasta ~18 % más rápido. Me
(4.1–7.9 % b.s.) queda dentro del rango final reportado por Phitakwinai
(4.5–12.5 % b.s.). M0 de ambos estudios coincide (~55 % b.h. ≈ 122 % b.s.).

**Contra secado en patio (Eliseu, ver `eliseu_2008_secado_patio.md`):**
a 26.3 °C / 63.3 % HR constantes, Roa predice MR = 0.05 en ~126 h, frente a
117.5 h reportadas (C. canephora, patio real). Mismo orden y diferencia ~7 %.

## Limitaciones a declarar

- Isoterma medida hasta 55 °C: su uso a 60–65 °C (régimen de la propuesta
  supervisada) es extrapolación leve (5–10 °C), respaldada por la concordancia
  con Phitakwinai en 50–70 °C.
- Isoterma de **desorción**: si M < Me (noche húmeda, patio) el modelo produce
  rehumectación con la misma curva; la histéresis de adsorción no está modelada.
- Validación de SECAFÉ en secadores mecánicos (aire caliente); en baja T la
  evidencia es la validez declarada de la ecuación (10–70 °C) y la verificación
  independiente con el patio.
- Variedad Caturra (Colombia) — coherente con el caso Chinchiná.

# Tabla 3 (Phitakwinai et al., 2019) — ecuaciones generalizadas del modelo Modified-Midilli

Válidas para T en °C (50-70) y RH en % (10-30). r² de cada regresión
polinómica de segundo orden, tal como reportado por los autores.

## Ecuaciones tal como están impresas en el artículo

```
k = -0.41202 + 0.014550*T - 6.3162e-4*RH + 1.0318e-4*T*RH
    - 8.8133e-5*T^2 - 2.4318e-5*RH^2                          (r² = 0.9955)

n = 2.19467 - 0.033121*T + 0.001747*RH - 0.000356*T*RH
    + 0.000327*T^2 + 0.0004677*RH^2                            (r² = 0.9856)

b = -0.01318 + 5.5127e-4*T - 1.3408e-4*RH + 1.7094e-7*T*RH
    - 4.72077e-6*T^2 + 3.6350e-6*RH^2                          (r² = 0.9660)
```

## Errata detectada en k (29 sept 2026) — valor usado en el código

Con el término T·RH impreso (1.0318e-4), la ecuación de k **no reproduce
la Tabla 2 del mismo artículo** (`phitakwinai_2019_tabla2_parametros.csv`,
filas `Modified_Midilli`): el k calculado es 1.6-3.7 veces el publicado
(error absoluto hasta 0.21) y aumenta con RH, lo cual es físicamente
incoherente (más humedad del aire debería frenar el secado).

Verificación:

| Coeficiente T·RH | Error máx. vs Tabla 2 (9 condiciones) |
|---|---|
| 1.0318e-4 (impreso) | 0.212 |
| **1.0318e-7** | **0.005** |

Una regresión propia de segundo orden sobre las 9 filas de la Tabla 2
reproduce los demás coeficientes y da un término T·RH ≈ 1.0e-7. Se
concluye que el exponente impreso (-4) es una errata y el código
(`python/cinetica_dinamica.py`, `k_generalizado`) usa:

```
k = -0.41202 + 0.014550*T - 6.3162e-4*RH + 1.0318e-7*T*RH
    - 8.8133e-5*T^2 - 2.4318e-5*RH^2
```

Nota: la versión anterior del repositorio tenía además 0.014457 como
coeficiente de T (error de transcripción, corregido a 0.014550). Las
curvas dinámicas generadas antes del 29 sept 2026 secaban 1.6-3.7 veces
más rápido de lo que indica el artículo y no deben usarse como resultado.

Con a = 1 fijo (ver README.md de esta carpeta), el modelo Modified-Midilli
generalizado queda: `MR(t; T, RH) = exp(-k(T,RH)·t^n(T,RH)) + b(T,RH)·t`.

Fuente: Phitakwinai, S., Thepa, S., & Nilnont, W. (2019). Thin-layer
drying of parchment Arabica coffee by controlling temperature and
relative humidity. *Food Science & Nutrition, 7*(9), 2921-2931,
Tabla 2 y Tabla 3. https://doi.org/10.1002/fsn3.1144

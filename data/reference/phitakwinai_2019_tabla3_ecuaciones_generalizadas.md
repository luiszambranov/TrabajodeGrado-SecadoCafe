# Tabla 3 (Phitakwinai et al., 2019) — ecuaciones generalizadas del modelo Modified-Midilli

Válidas para T en °C (50-70) y RH en % (10-30). r² de cada regresión
polinómica de segundo orden, tal como reportado por los autores.

```
k = -0.41202 + 0.014457*T - 6.3162e-4*RH + 1.0318e-4*T*RH
    - 8.8133e-5*T^2 - 2.4318e-5*RH^2                          (r² = 0.9955)

n = 2.19467 - 0.033121*T + 0.001747*RH - 3.56e-4*T*RH
    + 3.27e-4*T^2 + 4.7e-4*RH^2                                (r² = 0.9856)

b = -0.01318 + 5.5127e-4*T - 1.3408e-4*RH + 1.7094e-7*T*RH
    - 4.7207e-6*T^2 + 3.635e-6*RH^2                            (r² = 0.9660)
```

Con a = 1 fijo (ver README.md de esta carpeta), el modelo Modified-Midilli
generalizado queda: `MR(t; T, RH) = exp(-k(T,RH)·t^n(T,RH)) + b(T,RH)·t`.

Fuente: Phitakwinai, S., Thepa, S., & Nilnont, W. (2019). Thin-layer
drying of parchment Arabica coffee by controlling temperature and
relative humidity. *Food Science & Nutrition, 7*(9), 2921-2931,
Tabla 3. https://doi.org/10.1002/fsn3.1144

# Sensibilidad tipo tornado ±20 % (21 oct 2026)

Generado por `python/sensibilidad_tornado.py`: 10 realizaciones de la campaña (semillas 1001–1010) × REF y P1-C75 × (base + 8 variantes) = 180 corridas pareadas. Un factor a la vez.

| Parámetro | Factor | t REF [h] | t P1-C75 [h] | kWh/kg REF | kWh/kg P1-C75 | Ahorro medio [%] | Ahorro mínimo [%] | Tiempo adicional [h] (%) | P1-C75 gasta menos en todas | P1-C75 tarda más en todas | Capa más seca REF / P1 [% b.h.] |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 1.0 | 32.0 | 45.2 | 1.752 | 1.472 | 15.9 | 13.5 | +13.2 (+41 %) | sí | sí | 9.42 / 9.67 |
| k_cinetica | 0.8 | 37.2 | 51.9 | 2.022 | 1.706 | 15.6 | 13.0 | +14.8 (+40 %) | sí | sí | 9.92 / 9.91 |
| k_cinetica | 1.2 | 28.6 | 40.7 | 1.544 | 1.348 | 12.7 | 10.9 | +12.2 (+43 %) | sí | sí | 9.03 / 9.27 |
| caudal | 0.8 | 35.0 | 50.0 | 1.561 | 1.327 | 15.0 | 12.2 | +15.0 (+43 %) | sí | sí | 9.37 / 9.38 |
| caudal | 1.2 | 30.0 | 42.2 | 1.936 | 1.644 | 15.1 | 13.5 | +12.1 (+40 %) | sí | sí | 9.55 / 9.77 |
| ua_plenum | 0.8 | 32.0 | 45.2 | 1.744 | 1.464 | 16.0 | 13.6 | +13.2 (+41 %) | sí | sí | 9.42 / 9.67 |
| ua_plenum | 1.2 | 32.0 | 45.2 | 1.759 | 1.480 | 15.8 | 13.4 | +13.2 (+41 %) | sí | sí | 9.42 / 9.67 |
| espesor | 0.8 | 32.2 | 45.5 | 1.764 | 1.481 | 16.0 | 13.5 | +13.3 (+41 %) | sí | sí | 9.60 / 9.84 |
| espesor | 1.2 | 31.9 | 45.0 | 1.744 | 1.467 | 15.9 | 13.4 | +13.2 (+41 %) | sí | sí | 9.30 / 9.56 |

## Lectura

- El tiempo absoluto de REF se mueve entre 28.6 y 37.2 h (base 32.0 h): el modelo tiene incertidumbre en el valor absoluto, como mostró la validación.
- El ahorro relativo de P1-C75 frente a REF queda entre 12.7 % y 16.0 % (base 15.9 %), y P1-C75 gasta menos y tarda más que REF en todas las corridas: la frontera de Pareto REF–P1-C75 se conserva.
- Limitación: un factor a la vez, ±20 %, 10 realizaciones; no explora interacciones.

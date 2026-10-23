# Secado en patio — caso V2 de la validación del modelo

Fuente:

> Resende, O., Arcanjo, R. V., Siqueira, V. C., & Rodrigues, S. (2009).
> Modelagem matemática para a secagem de clones de café (*Coffea canephora*
> Pierre) em terreiro de concreto. *Acta Scientiarum. Agronomy, 31*(2),
> 189–196. https://doi.org/10.4025/actasciagron.v31i2.588
> (PDF: https://www.redalyc.org/pdf/3030/303026587001.pdf)

## Uso en el proyecto

Es el caso **V2** de la validación independiente (`validacion_modelo.md`,
`python/validacion_modelo.py`): café secado directamente al sol en patio, sin
calentamiento ni ventilación forzada. No se usa para calibrar ningún parámetro;
la línea base solar pasiva se calibra con Cenicafé (`python/escenario_sol_abierto.py`).

## Condiciones reportadas

| Variable | Valor |
|---|---|
| Temperatura ambiente media | 26,3 °C |
| Humedad relativa media | 63,3 % |
| Humedad inicial | 1,20–1,51 (decimal, base seca) según el clon |
| Humedad final | ≈ 0,10 (decimal, base seca) |
| Tiempo total de secado | 117,5 h (~4,9 días), igual para los 4 clones |
| Modelo de mejor ajuste (los autores) | Page (R² ≥ 0,9997) |

## Resultado de la validación

El modelo de Roa–Cenicafé a 26,3 °C y 63,3 % HR constantes, desde 1,355 hasta
0,10 b.s., tarda 125,6 h frente a las 117,5 h medidas (+6,9 %).

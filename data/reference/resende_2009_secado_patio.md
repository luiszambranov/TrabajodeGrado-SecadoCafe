# Secado en patio — caso excluido de la validación del modelo

Fuente:

> Resende, O., Arcanjo, R. V., Siqueira, V. C., & Rodrigues, S. (2009).
> Modelagem matemática para a secagem de clones de café (*Coffea canephora*
> Pierre) em terreiro de concreto. *Acta Scientiarum. Agronomy, 31*(2),
> 189–196. https://doi.org/10.4025/actasciagron.v31i2.588
> (PDF: https://www.redalyc.org/pdf/3030/303026587001.pdf)

## Uso en el proyecto

Era el caso V2 de la validación independiente y se **retiró** el 23 oct 2026
(ver abajo): café secado directamente al sol en patio, sin calentamiento ni
ventilación forzada. No se usa para calibrar ningún parámetro; la línea base
solar pasiva se calibra con Cenicafé (`python/escenario_sol_abierto.py`). En el
documento solo se cita como dato de contexto (117,5 h en patio).

## Condiciones reportadas

| Variable | Valor |
|---|---|
| Temperatura ambiente media | 26,3 °C |
| Humedad relativa media | 63,3 % |
| Humedad inicial | 1,20–1,51 (decimal, base seca) según el clon |
| Humedad final | ≈ 0,10 (decimal, base seca) |
| Tiempo total de secado | 117,5 h (~4,9 días), igual para los 4 clones |
| Modelo de mejor ajuste (los autores) | Page (R² ≥ 0,9997) |

## Por qué se retiró

La humedad final de Resende et al., 0,10 b.s. (10 % b.s.), está por debajo de
la humedad de equilibrio de Roa–Cenicafé a 26,3 °C y 63,3 % HR constantes,
12,59 % b.s. (`caso_excluido_resende()` en `python/validacion_modelo.py`). Con
aire constante el modelo nunca llega a ese valor: en el patio el grano se
calienta al sol por encima del aire y baja más, efecto que no entra con las
condiciones medias reportadas. La versión anterior daba 125,6 h (+6,9 %), pero
ese valor salía de un respaldo del script (MR = 0,05, unos 18,7 % b.s.), no de
la humedad final medida, así que no es una comparación válida.

# /fluidsim

Circuito neumático de actuación (FluidSIM), conectado a CODESYS por OPC
(prueba concurrente Modbus + OPC verificada el 23 sept 2026: GO).

## Qué se va a modelar

La **compuerta de inversión del aire** del secador: cada 6 h el aire pasa de
subir por el lecho (abajo → arriba) a bajar (arriba → abajo), como en el
secador estático de Cenicafé (SECAFÉ, 2008). En la simulación la orden la da
CODESYS (`flow_dir_cmd`, registro 15) y Python cambia el sentido del aire en
el modelo del lecho, así que la actuación modifica una variable física de la
planta (no es una animación desconectada).

Circuito previsto:
- Cilindro de doble efecto que mueve la compuerta.
- Válvula 5/2 biestable (mantiene la posición sin señal).
- Dos finales de carrera (compuerta abajo / arriba) que vuelven a CODESYS.
- Alarma "compuerta trabada" si el final de carrera no llega en un tiempo
  máximo después de la orden.

Estado (6 oct 2026): pendiente. Solo existe la prueba mínima de conexión
(botón → cilindro), evidencia en `codesys/ConcexionOPC.png`.

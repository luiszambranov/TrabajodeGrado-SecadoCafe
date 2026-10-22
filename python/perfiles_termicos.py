"""
perfiles_termicos.py
=====================

Perfiles térmicos de la propuesta supervisada (variable independiente del
objetivo general: "análisis ... bajo diferentes perfiles térmicos").
Definidos el 5 oct 2026, ANTES del piloto Monte Carlo.
Trabajo de grado - Sistema de supervisión digital para el secado de café.

Diseño (definido el 5 oct 2026; CORREGIDO el 21 oct 2026)
---------------------------------------------------------
Diseño factorial 3 x 3 + una referencia:

    Factor A, perfil térmico (setpoint de T_process, manipulada 1):
        P1  45 °C constante
        P2  50 °C y baja a 35 °C cuando el promedio del lote llega a 30 % b.h.
        P3  35 °C y sube a 50 °C cuando el promedio del lote llega a 30 % b.h.
    Factor B, caudal del ventilador (manipulada 2), constante en todo el secado:
        C30  30 % (2.4 m³/min)   - mínimo de operación del ventilador
        C75  75 % (6.0 m³/min)
        C100 100 % (8.0 m³/min)  - 0.1 m³/min/kg, óptimo de Cenicafé
    Referencia REF: 50 °C constante y caudal 100 %, la práctica recomendada
        por Cenicafé (González, Sanz & Oliveros, 2010).

CORRECCIÓN del 21 oct 2026: el diseño inicial usaba 55 °C en P2 y P3 para
tener niveles equidistantes (35/45/55). Eso contradecía la restricción que el
propio trabajo adopta (grano <= 50 °C; González et al., 2010) y la fuente de
los escalonados (de Oliveira et al., 2018, que usó 50 -> 35 y 35 -> 50 °C).
La campaña con ese diseño mostró 6-22 h de grano por encima de 50 °C. Se
corrigió el diseño por esa razón de seguridad, antes de ver los resultados
del diseño corregido. Los resultados del diseño inicial se conservan en
resultados/diseno_inicial_55/ y en PERFILES_DISENO_INICIAL_55.

Por qué estos perfiles (qué pregunta responde cada uno)
-------------------------------------------------------
La pregunta del objetivo general es cómo responde el secado (tiempo,
energía y restricciones de calidad) a CUÁNDO y CUÁNTO calor se aplica.
- REF (50 °C, 100 %): la práctica de Cenicafé; es la línea de comparación.
- P1 (45 °C constante): ¿cuánto se ahorra bajando la temperatura de forma
  sostenida 5 °C por debajo de la recomendación, y cuánto tiempo cuesta?
- P2 (50 -> 35 °C, alto al inicio y bajo al final): aplicar el calor cuando
  el grano está húmedo (mucha agua libre: la evaporación lo enfría y el aire
  se aprovecha mejor) y bajarlo cuando el grano ya está seco y se calienta
  más fácil (protege la calidad al final del secado).
- P3 (35 -> 50 °C, bajo al inicio y alto al final): presecado suave del grano
  húmedo y aceleración en el secado final. Es el sentido contrario: permite
  ver cómo reacciona el café a temperaturas bajas al inicio y altas después,
  frente a P2 (altas al inicio y bajas después).
  El cambio al 30 % b.h. es el que usaron de Oliveira et al. (2018), y
  coincide con la separación entre presecado y secado final de Cenicafé
  (Peñuela-Martínez et al., 2025).
- Caudal 30/75/100 %: el ventilador y la carga térmica de la resistencia
  dependen del caudal (la potencia para calentar el aire es proporcional al
  caudal); se busca si reducir caudal ahorra energía sin sobresecar la capa
  de entrada ni alargar demasiado el secado. González et al. (2010)
  controlan el caudal con variador; Alves et al. (2017) no encuentran efecto
  del caudal sobre la calidad del café.

Niveles: 35 °C es el más bajo que probaron de Oliveira et al. (2018); 50 °C
es el máximo permitido para el grano (González et al., 2010) y el nivel alto
de la fuente; 45 °C es el nivel constante intermedio. Ninguno sale del dominio
medido de la isoterma de Roa (5-55 °C; Trejos et al., 1989).

Qué permite responder
---------------------
- Efecto del perfil térmico (constante vs. descendente vs. ascendente).
- Efecto del caudal y si interactúa con el perfil.
- Cada combinación contra la práctica de Cenicafé (REF).

Referencias
-----------
- González S., C. A., Sanz U., J. R., & Oliveros T., C. E. (2010). Control de
  caudal y temperatura de aire en el secado mecánico de café. Cenicafé,
  61(4), 281-296.
- de Oliveira, P. D., et al. (2018). Quality of natural and pulped coffee as
  a function of temperature changes during mechanical drying. Coffee
  Science, 13(4), 415-425. https://doi.org/10.25186/cs.v13i4.1435
- Alves, G. E., Borém, F. M., Isquierdo, E. P., Siqueira, V. C., Cirillo,
  M. Â., & Pinto, A. C. F. (2017). Physiological and sensorial quality of
  Arabica coffee subjected to different temperatures and drying airflows.
  Acta Scientiarum. Agronomy, 39(2), 225-233.
  https://doi.org/10.4025/actasciagron.v39i2.31065
- Gallego, C. P., Imbachi, L. C., & Osorio, V. (2023). Cenicafé, 74(1), e74107.
- Trejos-Rodríguez, R., Roa-Mejía, G., & Oliveros-Tascón, C. E. (1989). Humedad
  de equilibrio y calor latente de vaporización del café pergamino y del café
  verde. Cenicafé, 40(1), 5-15. (isoterma medida a 10-55 °C)
- Oliveros T., C. E., Pabón U., J. P., & Montoya R., E. C. (2016). Evaluación
  de una alternativa para la conservación de la calidad en la
  comercialización del café húmedo. Cenicafé.
- Peñuela-Martínez et al. (2025); Oliveros et al. (2013): ver
  data/reference/validacion_modelo.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from control_supervisado import ParametrosControl

HUMEDAD_CAMBIO_BH_PCT = 30.0  # de Oliveira et al. (2018); Cenicafé (presecado)


@dataclass(frozen=True)
class Perfil:
    codigo: str
    nombre: str
    sp_inicial_c: float
    sp_final_c: float
    caudal_frac: float      # fracción del caudal nominal (1.0 = 8 m³/min), constante
    fuente: str

    def parametros_control(self) -> ParametrosControl:
        def sp(t_h, m_prom, m_max):
            return self.sp_inicial_c if m_prom > HUMEDAD_CAMBIO_BH_PCT else self.sp_final_c

        return ParametrosControl(setpoint_c=sp, caudal_frac=self.caudal_frac)


TERMICOS = [  # (código, descripción, sp inicial, sp final)
    ("P1", "45 °C constante", 45.0, 45.0),
    ("P2", "50 → 35 °C al 30 % b.h.", 50.0, 35.0),
    ("P3", "35 → 50 °C al 30 % b.h.", 35.0, 50.0),
]
TERMICOS_DISENO_INICIAL_55 = [  # diseño del 5 oct 2026, descartado el 21 oct (excede 50 °C de grano)
    ("P1", "45 °C constante", 45.0, 45.0),
    ("P2", "55 → 35 °C al 30 % b.h.", 55.0, 35.0),
    ("P3", "35 → 55 °C al 30 % b.h.", 35.0, 55.0),
]
CAUDALES = [("C30", 0.30), ("C75", 0.75), ("C100", 1.00)]

PERFILES = [Perfil("REF", "Cenicafé: 50 °C constante, caudal 100 %", 50.0, 50.0, 1.0, "González et al. (2010)")]
PERFILES += [
    Perfil(f"{tc}-{cc}", f"{td}, caudal {int(cf * 100)} %", s0, s1, cf, "de Oliveira et al. (2018); González et al. (2010)")
    for tc, td, s0, s1 in TERMICOS for cc, cf in CAUDALES
]
PERFILES_POR_CODIGO = {p.codigo: p for p in PERFILES}
PERFILES_DISENO_INICIAL_55 = [PERFILES[0]] + [
    Perfil(f"{tc}-{cc}", f"{td}, caudal {int(cf * 100)} %", s0, s1, cf, "Diseño inicial (5 oct 2026), descartado")
    for tc, td, s0, s1 in TERMICOS_DISENO_INICIAL_55 for cc, cf in CAUDALES
]


if __name__ == "__main__":
    import time

    import generador_ambiente as amb
    from control_supervisado import simular_supervisada

    nominal = [amb.condiciones_nominales()]
    print(f"{'Perfil':45s} {'t_obj':>7s} {'kWh':>7s} {'kWh/kg':>7s} {'capas':>11s} {'IAE':>6s} {'sobre':>6s} {'grano>50':>8s}")
    for pf in PERFILES:
        t0 = time.time()
        r = simular_supervisada(nominal, pf.parametros_control(), t_max_h=400.0)
        c = r.contadores
        print(f"{pf.codigo:8s} {pf.nombre:36s} {r.t_obj_h:7.1f} {c.energia_electrica_kwh:7.1f} {r.kwh_por_kg_cps:7.3f} "
              f"{r.m_capa_min_bh_pct:4.1f}-{r.m_capa_max_bh_pct:4.1f} {r.iae_c_h:6.2f} {r.sobreimpulso_c:6.2f} "
              f"{c.horas_grano_sobre_50c:8.2f}  ({time.time() - t0:.1f} s)")

"""
analisis_financiero.py
======================

Evaluación financiera preliminar (prefactibilidad) del sistema de supervisión:
VPN, TIR y periodo de recuperación (simple y descontado) de las dos alternativas
de inversión, y valor presente del cambio operativo REF -> P1-C75.

Dos decisiones separadas
------------------------
1. INVERSIÓN (flujo incremental frente a no ejecutar el proyecto)
   A  Adaptar un secador mecánico existente que hoy se opera a mano con la
      práctica de Cenicafé (REF). Situación sin proyecto: el mismo secador, el
      mismo perfil y el mismo calor por lote; cambia la operación.
   B  Sistema completo nuevo. Situación sin proyecto: secado solar activo
      (marquesina con extractor), la línea base ACTIVA de la campaña.
   La venta del café no es ingreso del proyecto: ocurre con o sin secador.
2. OPERACIÓN (mismo equipo): REF frente a P1-C75. No exige inversión, así que
   se reporta el ahorro por lote y su valor presente, sin TIR.

Convenciones
------------
- Pesos colombianos CONSTANTES de octubre de 2026 y tasa de descuento REAL.
- Flujos anuales al cierre del año; FC0 = -I0 (inversión en el año 0).
- Antes de impuestos y sin financiación. Sin capital de trabajo (el café es
  del caficultor y la energía se paga mes a mes).
- No se resta depreciación: el CAPEX ya entra completo en FC0.
- Valor residual en el año H (FCH).
- Cada parámetro está marcado como DATO (con fuente) o SUPUESTO.

Salidas: resultados/financiero/flujos_financieros.xlsx (con fórmulas VNA/TIR
vivas, para revisar en Excel) y resultados/financiero/resumen.md.

Uso (desde python/):  python analisis_financiero.py
"""

from __future__ import annotations

import math
import os

import pandas as pd
import xlsxwriter

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "resultados", "financiero")
CAMPANA = os.path.join(AQUI, "resultados", "campana", "resultados.csv")

# ---------------------------------------------------------------------------
# DATOS (con fuente)
# ---------------------------------------------------------------------------
# CAPEX de la IMPLEMENTACIÓN RECOMENDADA (precios de data/reference/cotizaciones_bom.md, 19-20 oct 2026,
# salvo el controlador). Cambios frente a la cotización de referencia:
#  - Controlador CODESYS: WAGO Compact Controller 100 (751-9301; 8 DI, 4 DO, 2 AI, 2 AO, entradas PT,
#    Modbus TCP, CODESYS V3 y WebVisu) en lugar de S7-1200 + SM 1223 + SM 1231 + licencia STEP 7.
#    El programa del trabajo (CODESYS) se reutiliza; CODESYS Development System es gratuito.
#  - HMI por WebVisu del controlador (navegador del celular o tablet) en lugar del panel Kinco.
#  - Actuador eléctrico Belimo LF24 (con resorte de retorno) en lugar de cilindro, válvula y compresor.
#  - Sin medidor de humedad del grano: la situación sin proyecto también lo necesita (no es incremental).
#  - Ingeniería por unidad: 24 h de adaptación y puesta en marcha (el programa ya existe).
WAGO_CC100_GBP = 468.88         # Farnell UK, 751-9301, sin IVA, consulta 23 oct 2026
FACTOR_IMPORTACION = 1.37       # IVA 19 % x 1,15 envío y arancel (mismo criterio del BOM)
CC100_COP = round(WAGO_CC100_GBP * 4_266.60 * FACTOR_IMPORTACION)
CAPEX_ITEMS = [
    # (grupo, descripción, COP, escenario)
    ("Proceso", "3 resistencias de 2 kW, ventilador trifásico, variador, 3 SSR con disipador, contactor", 4_124_213, "A"),
    ("Seguridad", "Presostato diferencial y termostato de rearme manual", 250_634, "A"),
    ("Instrumentación", "PT100 con transmisor 4-20 mA y transmisor de HR ambiente", 29_900 + 23_969 + 748_287, "A"),
    ("Actuación", "Actuador eléctrico Belimo LF24 para la compuerta de inversión", 1_188_042, "A"),
    ("Control", "WAGO Compact Controller 100 (CODESYS V3, WebVisu), fuente 24 V, pulsadores, paro y torre de luces",
     CC100_COP + 239_000 + 30_000 + 24_000 + 214_400, "A"),
    ("Tablero", "Gabinete, breakers y cableado (10 % de los equipos eléctricos, supuesto)", None, "A"),
    ("Kit de inversión", "Ductos, caja de compuerta, aislamiento y 16 h de taller", 1_203_712, "A"),
    ("Ingeniería", "Adaptación del programa y puesta en marcha, 24 h x 100 000 COP/h (supuesto)", 2_400_000, "A"),
    ("Cámara (solo B)", "Cámara aislada de 1,13 x 1,13 x 0,95 m, bandeja y 40 h de taller", 2_494_370, "B"),
]
_elec = 4_124_213 + 250_634 + (29_900 + 23_969 + 748_287) + 1_188_042 + (CC100_COP + 239_000 + 30_000 + 24_000 + 214_400)
CAPEX_ITEMS[5] = (CAPEX_ITEMS[5][0], CAPEX_ITEMS[5][1], 155_700 + round(0.10 * _elec), "A")
CAPEX_A = sum(c for g, dsc, c, e in CAPEX_ITEMS if e == "A")
CAPEX_B = CAPEX_A + sum(c for g, dsc, c, e in CAPEX_ITEMS if e == "B")
INGENIERIA = 2_400_000
# Secador mecánico MANUAL nuevo del mismo tamaño (situación sin proyecto de B): lo que tienen ambos secadores
CONVENCIONAL_ITEMS = [
    ("Cámara de secado, bandeja y 40 h de taller", 2_494_370),
    ("3 resistencias de 2 kW", 1_014_882),
    ("Ventilador centrífugo", 2_331_231),
    ("Contactor de corte", 52_000),
    ("Termostato de seguridad de rearme manual", 100_652),
    ("Kit de inversión del aire (ductos y compuerta manual)", 1_203_712),
    ("Gabinete y breakers", 155_700),
]
CONVENCIONAL = sum(c for _, c in CONVENCIONAL_ITEMS)
# Lo que ya tiene el secador manual existente de A (no es incremental). El ventilador SÍ se cambia:
# el variador necesita un motor trifásico para operar con caudal variable (P1-C75).
EXISTENTE_A_ITEMS = [it for it in CONVENCIONAL_ITEMS if not it[0].startswith(("Cámara", "Ventilador"))]
EXISTENTE_A = sum(c for _, c in EXISTENTE_A_ITEMS)
CAPEX_REFERENCIA_A, CAPEX_REFERENCIA_B = 22_707_081, 25_201_451   # cotización con S7-1200 (para comparar)
LIC_STEP7_GBP = 441.0           # STEP 7 Basic V19 floating, 6ES7822-0AA23-0YA5 (Parmley Graham, 23 oct 2026)
GBP_COP = 4_266.60              # Pound Sterling Live / Barchart, 23 oct 2026
IVA = 0.19                      # IVA Colombia
TARIFA_NO_RES = 1_144.3472      # CHEC sept 2026, nivel 1, comercial e industrial [COP/kWh]
TARIFA_RES = 953.6227           # CHEC sept 2026, nivel 1, residencial sobre subsistencia
SMMLV = 1_750_905               # Decreto 1469 de 2025
HORAS_MES = 210                 # divisor mensual con jornada de 42 h/semana desde el 15 jul 2026 (Ley 2101 de 2021): hora ordinaria = SMMLV/210
PRECIO_CARGA = 2_235_000        # precio interno de referencia, carga de 125 kg c.p.s. (21 oct 2026)
KG_LOTE = 80.0                  # kg c.p.s. por lote a 11 % b.h.
M_OBJ = 0.11

# Tasa de descuento real: techo Finagro IBR + 6,7 pp (Resolución 10 de 2025) con
# IBR ~ tasa de política 12,25 % (sept 2026) e inflación 6,2 % (ago 2026):
# (1 + 0,1895) / (1 + 0,062) - 1 = 12,0 % real.
TASA_NOMINAL_REF = 0.1225 + 0.067
INFLACION = 0.062
TASA_REAL_CENTRAL = (1 + TASA_NOMINAL_REF) / (1 + INFLACION) - 1

HORA_ASESORIA = 100_000         # supuesto: consultoría especializada (rango 50 000-150 000 COP/h)
HORA_CATEDRA_PUBLICA = 44_973   # Decreto 0301 de 2026, art. 9, profesor asociado con maestría (cota inferior)
# Reconstrucción de las horas de asesoría (estimación de los autores; evidencia = documentos del asesor)
ASESORIA = [
    ("2-8 sep 2026", "Revisión del anteproyecto y guía de trabajo con cronograma", 3, "Guía vigente del trabajo de grado (8 sep)"),
    ("15-23 sep 2026", "Lectura de la primera versión del documento y retroalimentación", 3, "Informe de revisión del documento (23 sep)"),
    ("24-29 sep 2026", "Revisión del modelado y del diseño de la campaña", 3, "Informe de prioridades de modelado y campaña (29 sep)"),
    ("13-21 oct 2026", "Revisión de resultados, repositorio y código; guía de cierre", 3, "Guía de cierre (21 oct)"),
    ("22-23 oct 2026", "Lectura de la versión final y guía de correcciones", 3, "Guía de correcciones exprés (23 oct)"),
    ("sep-oct 2026", "Reuniones y mensajes de seguimiento", 1, "Correos y mensajes"),
]

# ---------------------------------------------------------------------------
# SUPUESTOS (sin dato de una finca concreta)
# ---------------------------------------------------------------------------
FACTOR_PRESTACIONAL = 1.52      # salario + prestaciones + seguridad social
H = 5                           # horizonte [años]
ESCENARIOS = {
    #              lotes  tasa   h_A  merma_A  h_B  mant   residual
    "Conservador": (20,   0.16,  5.0, 0.000,   4.0, 0.04,  0.00),
    "Central":     (40,   None, 10.0, 0.005,   8.0, 0.03,  0.20),
    "Favorable":   (60,   0.08, 15.0, 0.010,  12.0, 0.02,  0.40),
}
# h_A: MINUTOS de supervisión manual por hora de secado que el sistema automatiza (revisar la
#      temperatura y ajustar el calor). Las horas por lote salen de la simulación (horas_supervision).
# merma_A: puntos de humedad de sobresecado evitados al detener el lote en 11 %
#      (fracción; 0,005 = 0,5 puntos b.h.).
# h_B: horas evitadas frente al secado solar (revolver el café varias veces al
#      día durante ~5,7 días).
# mant: mantenimiento y calibración anual como fracción de los equipos.
# residual: valor residual en el año H como fracción de los equipos.


MIN_INVERSION = 20.0     # supuesto: minutos de operario por inversión manual del aire
H_MUESTREO = 1.0         # supuesto: horas de muestreo de humedad al final del lote
FRACCION_NOCHE = 0.5     # el lote dura más de un día: la mitad de las horas cae de 18:00 a 06:00
RECARGO_NOCTURNO = 0.35  # Código Sustantivo del Trabajo, art. 168
# Fracción de lotes que se pueden secar con P1-C75 sin superar la capacidad en el pico de cosecha
# (octubre concentra 29-35 % de la cosecha en Naranjal; Alvarado-Alvarado y Moreno-Ruiz, 1999):
# con 20 y 40 lotes/año cabe todo con P1-C75 (~15 lotes/mes); con 60 lotes, sep-oct van con REF.
FRACCION_P1 = {20: 1.0, 40: 1.0, 60: 0.5}


def horas_supervision(min_por_hora: float) -> float:
    """Horas-equivalentes de operario por lote de un secador manual con REF, a partir de la
    simulación: revisiones durante el tiempo de secado, inversiones del aire y muestreo final;
    las horas nocturnas con recargo."""
    d = pd.read_csv(CAMPANA)
    ref = d[d.estrategia == "REF"]
    t, n_inv = ref.t_obj_h.mean(), ref.n_inversiones.mean()
    tareas = t * min_por_hora / 60 + n_inv * MIN_INVERSION / 60
    return H_MUESTREO + tareas * (1 + FRACCION_NOCHE * RECARGO_NOCTURNO)


def hora_operario() -> float:
    return SMMLV * FACTOR_PRESTACIONAL / HORAS_MES


def kg_merma(puntos: float) -> float:
    """kg c.p.s. que se dejan de vender por secar 'puntos' por debajo de 11 % b.h."""
    seco = KG_LOTE * (1 - M_OBJ)
    return KG_LOTE - seco / (1 - (M_OBJ - puntos))


def energia_por_lote() -> dict:
    d = pd.read_csv(CAMPANA)
    return d.groupby("estrategia")["elec_kwh"].mean().to_dict()


def tiempo_por_lote() -> dict:
    d = pd.read_csv(CAMPANA)
    return d.groupby("estrategia")["t_obj_h"].mean().to_dict()


def vpn(r: float, flujos: list[float]) -> float:
    return sum(f / (1 + r) ** t for t, f in enumerate(flujos))


def tir(flujos: list[float]) -> float | None:
    """TIR por bisección en (-0,99; 10). None si no hay cambio de signo."""
    f = lambda r: vpn(r, flujos)
    lo, hi = -0.99, 10.0
    if f(lo) * f(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def recuperacion(flujos: list[float], r: float = 0.0) -> float | None:
    """Años hasta que el acumulado (descontado a r) llega a 0, interpolando."""
    acum = 0.0
    for t, f in enumerate(flujos):
        fd = f / (1 + r) ** t
        if acum < 0 <= acum + fd and t > 0:
            return t - 1 + (-acum) / fd
        acum += fd
    return None


def casos() -> list[dict]:
    e = energia_por_lote()
    hora = hora_operario()
    precio_kg = PRECIO_CARGA / 125
    lic = 0.0   # CODESYS Development System es gratuito
    res = []
    for alt, capex in (("A", CAPEX_A - EXISTENTE_A), ("B", CAPEX_B - CONVENCIONAL)):
        equipos = capex - INGENIERIA
        for esc, (lotes, tasa, h_a, merma_a, h_b, mant, resid) in ESCENARIOS.items():
            r = TASA_REAL_CENTRAL if tasa is None else tasa
            fp1 = FRACCION_P1[lotes]
            e_proy = fp1 * e["P1-C75"] + (1 - fp1) * e["REF"]   # energía por lote con el sistema
            # A: sin proyecto, el mismo secador manejado a mano con REF y caudal fijo.
            # B: sin proyecto, la finca compra un secador mecánico MANUAL nuevo del mismo tamaño;
            #    la inversión incremental es la diferencia (control, instrumentación, variador, actuador,
            #    ingeniería). En ambos casos el sistema reemplaza la supervisión manual y el variador
            #    permite operar con P1-C75.
            beneficio = horas_supervision(h_a) * hora + kg_merma(merma_a) * precio_kg \
                + (e["REF"] - e_proy) * TARIFA_NO_RES
            egreso_var = 0.0
            neto_lote = beneficio - egreso_var
            fijo = mant * equipos
            i0 = capex + lic
            anual = lotes * neto_lote - fijo
            flujos = [-i0] + [anual] * H
            flujos[-1] += resid * equipos
            res.append(dict(alternativa=alt, escenario=esc, inversion=i0, lotes=lotes,
                            beneficio_lote=beneficio, egreso_lote=egreso_var, neto_lote=neto_lote,
                            costo_fijo=fijo, residual=resid * equipos, tasa=r, flujos=flujos,
                            vpn=vpn(r, flujos), tir=tir(flujos),
                            pb=recuperacion(flujos), pbd=recuperacion(flujos, r),
                            umbral_lote=(i0 - resid * equipos / (1 + r) ** H) / (lotes * sum(1 / (1 + r) ** t for t in range(1, H + 1)))
                                        + fijo / lotes + egreso_var))
    return res


def b_frente_solar() -> list[dict]:
    """Contraste: sistema completo frente a seguir secando al sol (solar activo)."""
    e = energia_por_lote(); hora = hora_operario(); out = []
    for esc, (lotes, tasa, h_a, merma_a, h_b, mant, resid) in ESCENARIOS.items():
        r = TASA_REAL_CENTRAL if tasa is None else tasa
        fp1 = FRACCION_P1[lotes]
        e_proy = fp1 * e["P1-C75"] + (1 - fp1) * e["REF"]
        neto = h_b * hora - (e_proy - e["ACTIVA"]) * TARIFA_NO_RES
        equipos = CAPEX_B - INGENIERIA
        fl = [-CAPEX_B] + [lotes * neto - mant * equipos] * H
        fl[-1] += resid * equipos
        out.append(dict(escenario=esc, lotes=lotes, neto=neto, vpn=vpn(r, fl), tir=tir(fl), flujos=fl, tasa=r))
    return out


def vpn_a(p: tuple) -> float:
    """VPN de la alternativa A con un juego de parámetros de escenario."""
    lotes, tasa, h_a, merma_a, _h_b, mant, resid = p
    r = TASA_REAL_CENTRAL if tasa is None else tasa
    i0 = CAPEX_A - EXISTENTE_A
    equipos = i0 - INGENIERIA
    e = energia_por_lote()
    fp1 = FRACCION_P1.get(lotes, 1.0 if lotes <= 40 else 0.5)
    ahorro = (e["REF"] - (fp1 * e["P1-C75"] + (1 - fp1) * e["REF"])) * TARIFA_NO_RES
    anual = lotes * (horas_supervision(h_a) * hora_operario() + kg_merma(merma_a) * PRECIO_CARGA / 125
                     + ahorro) - mant * equipos
    flujos = [-i0] + [anual] * H
    flujos[-1] += resid * equipos
    return vpn(r, flujos)


def fmt_pct(x):
    return "no existe (todos los flujos ≤ 0)" if x is None else f"{100 * x:.1f} %"


def fmt_pb(x):
    return f"> {H} años" if x is None else f"{x:.1f} años"


def escribir_excel(res: list[dict], ruta: str) -> None:
    e = energia_por_lote()
    t = tiempo_por_lote()
    wb = xlsxwriter.Workbook(ruta)
    b = wb.add_format({"bold": True})
    cop = wb.add_format({"num_format": "#,##0"})
    pct = wb.add_format({"num_format": "0.0%"})
    num = wb.add_format({"num_format": "0.00"})
    wrap = wb.add_format({"text_wrap": True, "valign": "top"})

    # --- Supuestos ---
    s = wb.add_worksheet("Supuestos")
    s.set_column(0, 0, 46); s.set_column(1, 1, 16); s.set_column(2, 2, 11); s.set_column(3, 3, 80)
    filas = [
        ("Parámetro", "Valor", "Tipo", "Fuente o justificación"),
        ("CAPEX A, implementación recomendada [COP]", CAPEX_A, "Cálculo", "Hoja CAPEX_implementacion; precios de data/reference/cotizaciones_bom.md (19-20 oct 2026)"),
        ("CAPEX B, implementación recomendada [COP]", CAPEX_B, "Cálculo", "A + cámara de secado"),
        ("Componentes que ya tiene el secador existente de A [COP]", EXISTENTE_A, "Cálculo", "Resistencias, contactor, termostato, kit de inversión manual y tablero básico; el ventilador se cambia por uno trifásico para el variador"),
        ("Inversión incremental de A [COP]", CAPEX_A - EXISTENTE_A, "Cálculo", "CAPEX A - componentes existentes"),
        ("Secador mecánico manual nuevo (sin proyecto de B) [COP]", CONVENCIONAL, "Cálculo", "Hoja CAPEX_implementacion: cámara, resistencias, ventilador, contactor, termostato, kit de inversión y tablero"),
        ("Inversión incremental de B [COP]", CAPEX_B - CONVENCIONAL, "Cálculo", "CAPEX B - secador manual: control, instrumentación, variador, actuador, ingeniería"),
        ("CAPEX de referencia con S7-1200 (A / B) [COP]", f"{CAPEX_REFERENCIA_A:,} / {CAPEX_REFERENCIA_B:,}", "Dato", "Cotización completa, para comparar"),
        ("Controlador WAGO Compact Controller 100 [GBP]", WAGO_CC100_GBP, "Dato", "Farnell UK, 751-9301, sin IVA, 23 oct 2026; CODESYS V3, 8 DI, 4 DO, 2 AI, 2 AO, Modbus TCP, WebVisu"),
        ("Tasa GBP/COP", GBP_COP, "Dato", "Pound Sterling Live (Barchart), 23 oct 2026"),
        ("Controlador con IVA, envío y arancel [COP]", CC100_COP, "Cálculo", "x 1,37, mismo criterio del BOM"),
        ("Licencias de software [COP]", 0, "Dato", "CODESYS Development System gratuito; WebVisu incluido en el controlador"),
        ("Ingeniería por unidad [COP]", INGENIERIA, "Supuesto", "24 h x 100 000 COP/h: adaptación del programa existente y puesta en marcha"),
        ("Minutos por inversión manual del aire", MIN_INVERSION, "Supuesto", "Mover la compuerta y verificar"),
        ("Muestreo de humedad al final del lote [h]", H_MUESTREO, "Supuesto", "Varias muestras para decidir el fin"),
        ("Recargo nocturno", RECARGO_NOCTURNO, "Dato", "Código Sustantivo del Trabajo, art. 168; la mitad de las horas del lote es nocturna"),
        ("Tarifa no residencial [COP/kWh]", TARIFA_NO_RES, "Dato", "CHEC, sept 2026, nivel 1, comercial e industrial (uso productivo del secador)"),
        ("Tarifa residencial (sensibilidad) [COP/kWh]", TARIFA_RES, "Dato", "CHEC, sept 2026, nivel 1, residencial sobre subsistencia"),
        ("Salario mínimo 2026 [COP/mes]", SMMLV, "Dato", "Decreto 1469 de 2025"),
        ("Factor prestacional", FACTOR_PRESTACIONAL, "Supuesto", "Prestaciones sociales y seguridad social sobre el salario"),
        ("Horas laborales por mes (divisor)", HORAS_MES, "Dato", "42 h/semana desde el 15 jul 2026 (Ley 2101 de 2021); hora ordinaria = SMMLV/210 = 8 338 COP"),
        ("Costo hora de operario [COP/h]", hora_operario(), "Cálculo", "Hora ordinaria (SMMLV/210) x factor prestacional"),
        ("Precio interno café pergamino [COP/carga 125 kg]", PRECIO_CARGA, "Dato", "Precio interno de referencia, 21 oct 2026 (La República con dato FNC)"),
        ("Tasa nominal de referencia", TASA_NOMINAL_REF, "Dato", "Techo Finagro IBR + 6,7 pp (Res. 10 de 2025) con IBR ~ 12,25 % (BanRep, sept 2026)"),
        ("Inflación anual", INFLACION, "Dato", "6,2 % (agosto 2026)"),
        ("Tasa real central", TASA_REAL_CENTRAL, "Cálculo", "(1 + nominal)/(1 + inflación) - 1; sensibilidad 8 % y 16 %"),
        ("Horizonte [años]", H, "Supuesto", "Ruta acotada propuesta por la guía"),
        ("Energía REF por lote [kWh]", e["REF"], "Resultado", "Campaña Monte Carlo, media de 150 realizaciones"),
        ("Energía P1-C75 por lote [kWh]", e["P1-C75"], "Resultado", "Ídem"),
        ("Energía ACTIVA por lote [kWh]", e["ACTIVA"], "Resultado", "Ídem (extractor solar)"),
        ("Tiempo REF / P1-C75 [h]", f"{t['REF']:.1f} / {t['P1-C75']:.1f}", "Resultado", "Ídem"),
        ("Impuestos y financiación", "Excluidos", "Supuesto", "Cálculo antes de impuestos, sin crédito"),
        ("Capital de trabajo", 0, "Supuesto", "Sin inventario propio; la energía se paga mensual"),
    ]
    for i, fila in enumerate(filas):
        for j, v in enumerate(fila):
            f = b if i == 0 else (cop if isinstance(v, (int, float)) and abs(v) > 100 else (pct if isinstance(v, float) and v < 1 and j == 1 else None))
            s.write(i, j, v, f)
    s.write(len(filas) + 1, 0, "Escenarios (supuestos por escenario)", b)
    cab = ["Escenario", "Lotes/año", "Tasa real", "Min. de supervisión por hora (A)", "Sobresecado evitado A [pts]",
           "h evitadas B", "Mantenimiento [% equipos/año]", "Valor residual [% equipos]"]
    for j, c in enumerate(cab):
        s.write(len(filas) + 2, j, c, b)
    for i, (esc, p) in enumerate(ESCENARIOS.items()):
        lotes, tasa, h_a, m_a, h_b, mant, resid = p
        fila = [esc, lotes, TASA_REAL_CENTRAL if tasa is None else tasa, h_a, 100 * m_a, h_b, mant, resid]
        for j, v in enumerate(fila):
            s.write(len(filas) + 3 + i, j, v, pct if j in (2, 6, 7) else None)

    # --- Flujos con fórmulas ---
    w = wb.add_worksheet("Flujos")
    w.set_column(0, 0, 34); w.set_column(1, 7, 14)
    fila = 0
    for c in res:
        w.write(fila, 0, f"Alternativa {c['alternativa']} — escenario {c['escenario']}", b)
        fila += 1
        w.write_row(fila, 0, ["Año"] + list(range(H + 1)), b)
        f_flujo = fila + 1
        w.write(f_flujo, 0, "Flujo de caja [COP]")
        for k, v in enumerate(c["flujos"]):
            w.write(f_flujo, 1 + k, round(v), cop)
        w.write(f_flujo + 1, 0, "Tasa real")
        w.write(f_flujo + 1, 1, c["tasa"], pct)
        col_ini = xlsxwriter.utility.xl_rowcol_to_cell(f_flujo, 1)
        col_1 = xlsxwriter.utility.xl_rowcol_to_cell(f_flujo, 2)
        col_fin = xlsxwriter.utility.xl_rowcol_to_cell(f_flujo, 1 + H)
        tasa_c = xlsxwriter.utility.xl_rowcol_to_cell(f_flujo + 1, 1)
        w.write(f_flujo + 2, 0, "VPN = VNA(tasa; FC1:FCH) + FC0")
        w.write_formula(f_flujo + 2, 1, f"=NPV({tasa_c},{col_1}:{col_fin})+{col_ini}", cop, round(c["vpn"]))
        w.write(f_flujo + 3, 0, "TIR(FC0:FCH)")
        if c["tir"] is None:
            w.write(f_flujo + 3, 1, "No existe: todos los flujos son negativos")
        else:
            w.write_formula(f_flujo + 3, 1, f"=IRR({col_ini}:{col_fin})", pct, c["tir"])
        w.write(f_flujo + 4, 0, "Acumulado simple")
        w.write(f_flujo + 5, 0, "Acumulado descontado")
        acum_s = acum_d = 0.0
        for k in range(H + 1):
            celda = xlsxwriter.utility.xl_rowcol_to_cell(f_flujo, 1 + k)
            acum_s += c["flujos"][k]
            acum_d += c["flujos"][k] / (1 + c["tasa"]) ** k
            if k == 0:
                w.write_formula(f_flujo + 4, 1, f"={celda}", cop, round(acum_s))
                w.write_formula(f_flujo + 5, 1, f"={celda}", cop, round(acum_d))
            else:
                prev_s = xlsxwriter.utility.xl_rowcol_to_cell(f_flujo + 4, k)
                prev_d = xlsxwriter.utility.xl_rowcol_to_cell(f_flujo + 5, k)
                w.write_formula(f_flujo + 4, 1 + k, f"={prev_s}+{celda}", cop, round(acum_s))
                w.write_formula(f_flujo + 5, 1 + k, f"={prev_d}+{celda}/(1+{tasa_c})^{k}", cop, round(acum_d))
        w.write(f_flujo + 6, 0, "Recuperación simple / descontada")
        w.write(f_flujo + 6, 1, f"{fmt_pb(c['pb'])} / {fmt_pb(c['pbd'])}")
        w.write(f_flujo + 7, 0, "Beneficio neto por lote [COP]")
        w.write(f_flujo + 7, 1, round(c["neto_lote"]), cop)
        w.write(f_flujo + 8, 0, "Beneficio por lote necesario para VPN = 0")
        w.write(f_flujo + 8, 1, round(c["umbral_lote"]), cop)
        fila = f_flujo + 10

    # --- CAPEX de la implementación recomendada ---
    k = wb.add_worksheet("CAPEX_implementacion")
    k.set_column(0, 0, 22); k.set_column(1, 1, 95); k.set_column(2, 3, 14)
    k.write_row(0, 0, ["Grupo", "Componentes", "COP", "Escenario"], b)
    for i, (g, dsc, c, esc) in enumerate(CAPEX_ITEMS):
        k.write_row(1 + i, 0, [g, dsc]); k.write(1 + i, 2, c, cop); k.write(1 + i, 3, esc)
    n = 1 + len(CAPEX_ITEMS)
    k.write(n, 1, "CAPEX A", b); k.write_formula(n, 2, f'=SUMIF(D2:D{n},"A",C2:C{n})', cop, CAPEX_A)
    k.write(n + 1, 1, "CAPEX B", b); k.write_formula(n + 1, 2, f"=C{n + 1}+SUMIF(D2:D{n},\"B\",C2:C{n})", cop, CAPEX_B)
    k.write(n + 9, 0, "Cambios frente a la cotización con S7-1200: controlador CODESYS WAGO CC100 y WebVisu en lugar de "
                      "S7-1200, módulos, STEP 7 y panel HMI; actuador eléctrico en lugar de neumático; sin medidor de "
                      "humedad (también lo requiere la situación sin proyecto); ingeniería de 24 h (el programa ya existe).")
    k.write(n + 8, 1, "Componentes existentes en A / inversión incremental de A", b)
    k.write(n + 8, 2, EXISTENTE_A, cop); k.write(n + 8, 3, CAPEX_A - EXISTENTE_A, cop)
    k.write(n + 2, 1, "Secador manual nuevo (situación sin proyecto de B)", b)
    k.write(n + 2, 2, CONVENCIONAL, cop)
    k.write(n + 3, 1, "Inversión incremental de B", b)
    k.write_formula(n + 3, 2, f"=C{n + 2}-C{n + 3}", cop, CAPEX_B - CONVENCIONAL)
    fila_c = n + 12
    k.write(fila_c, 0, "Componentes del secador manual nuevo", b)
    for j, (dsc, c) in enumerate(CONVENCIONAL_ITEMS):
        k.write(fila_c + 1 + j, 1, dsc); k.write(fila_c + 1 + j, 2, c, cop)
    k.write(n + 4, 0, "Horas de supervisión manual evitadas por lote (de la simulación, REF):")
    for j, m in enumerate((5.0, 10.0, 15.0)):
        k.write(n + 5 + j, 1, f"{m:g} min de revisión por hora de secado"); k.write(n + 5 + j, 2, round(horas_supervision(m), 2))

    # --- Contraste: B frente al secado solar ---
    sb = wb.add_worksheet("B_frente_solar")
    sb.set_column(0, 0, 16); sb.set_column(1, 10, 14)
    sb.write(0, 0, "Sistema completo frente a seguir secando al sol: cada lote eléctrico cuesta más energía de la que "
                   "ahorra en mano de obra, así que no se recupera. Aplica a fincas que pueden seguir secando al sol.", b)
    sb.write_row(2, 0, ["Escenario", "Lotes/año", "Neto por lote", "Tasa", "VPN", "TIR", "FC0", "FC1-FC4", "FC5"], b)
    for i, c in enumerate(b_frente_solar()):
        sb.write_row(3 + i, 0, [c["escenario"], c["lotes"]])
        sb.write(3 + i, 2, round(c["neto"]), cop); sb.write(3 + i, 3, c["tasa"], pct)
        sb.write(3 + i, 4, round(c["vpn"]), cop)
        sb.write(3 + i, 5, "No existe" if c["tir"] is None else c["tir"], None if c["tir"] is None else pct)
        sb.write(3 + i, 6, round(c["flujos"][0]), cop); sb.write(3 + i, 7, round(c["flujos"][1]), cop)
        sb.write(3 + i, 8, round(c["flujos"][5]), cop)

    # --- Operación REF -> P1-C75 ---
    o = wb.add_worksheet("Operacion_P1C75")
    o.set_column(0, 0, 40); o.set_column(1, 6, 14)
    ahorro_kwh = e["REF"] - e["P1-C75"]
    o.write_row(0, 0, ["Ahorro de energía P1-C75 frente a REF [kWh/lote]", ahorro_kwh], None)
    o.write_row(1, 0, ["Tiempo adicional por lote [h]", t["P1-C75"] - t["REF"]], None)
    o.write_row(3, 0, ["Tarifa [COP/kWh]", "Ahorro/lote", "Lotes/año", "Ahorro anual", "VP 5 años 8 %", "VP 5 años 12 %", "VP 5 años 16 %"], b)
    fila = 4
    for tarifa in (TARIFA_NO_RES, TARIFA_RES):
        for lotes in (20, 40, 60):
            anual = ahorro_kwh * tarifa * lotes
            o.write_row(fila, 0, [tarifa, ahorro_kwh * tarifa, lotes, anual] +
                        [vpn(r, [0] + [anual] * H) for r in (0.08, TASA_REAL_CENTRAL, 0.16)], cop)
            fila += 1

    # --- Asesoría (costo académico) ---
    a = wb.add_worksheet("Costo_academico")
    a.set_column(0, 3, 40)
    a.set_column(0, 0, 18); a.set_column(1, 1, 62); a.set_column(2, 2, 10); a.set_column(3, 3, 48)
    a.write(0, 0, "Costo académico del desarrollo (perspectiva de la universidad). No entra al flujo de caja del implementador.", b)
    a.write_row(2, 0, ["Periodo", "Actividad", "Horas", "Evidencia"], b)
    for i, fila in enumerate(ASESORIA):
        a.write_row(3 + i, 0, fila)
    n = 3 + len(ASESORIA)
    a.write(n, 1, "Total de horas (estimación)", b)
    a.write_formula(n, 2, f"=SUM(C4:C{n})", None, sum(f[2] for f in ASESORIA))
    a.write(n + 1, 1, "Valor de referencia de la hora [COP/h] (supuesto: consultoría especializada; la hora cátedra pública del Decreto 0301 de 2026 es 44 973 COP/h)")
    a.write(n + 1, 2, HORA_ASESORIA, cop)
    a.write(n + 2, 1, "Valor de la asesoría [COP]", b)
    a.write_formula(n + 2, 2, f"=C{n + 1}*C{n + 2}", cop, sum(f[2] for f in ASESORIA) * HORA_ASESORIA)
    a.write(n + 4, 0, "La tarifa es una referencia de valoración del recurso consumido, no el salario real del asesor. "
                      "La ingeniería de implementación (60 h) está en el CAPEX y no se cruza con estas horas.", wrap)
    wb.close()


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    res = casos()
    escribir_excel(res, os.path.join(OUT, "flujos_financieros.xlsx"))
    e = energia_por_lote(); t = tiempo_por_lote()
    L = ["# Evaluación financiera preliminar", "",
         "Generado por `python/analisis_financiero.py`. Pesos constantes de octubre de 2026, tasa real, "
         f"horizonte de {H} años, antes de impuestos y sin financiación. Detalle con fórmulas en "
         "`flujos_financieros.xlsx`.", "",
         f"Costo de una hora de operario: {hora_operario():,.0f} COP/h. Tasa real central: {100 * TASA_REAL_CENTRAL:.1f} %.", "",
         "| Alt. | Escenario | Inversión [COP] | Lotes/año | Beneficio/lote [COP] | Egreso variable/lote [COP] | Costo fijo [COP/año] | Tasa | VPN [COP] | TIR | Recuperación simple / desc. | Beneficio/lote para VPN = 0 |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in res:
        L.append(f"| {c['alternativa']} | {c['escenario']} | {c['inversion']:,.0f} | {c['lotes']} | {c['beneficio_lote']:,.0f} | {c['egreso_lote']:,.0f} | "
                 f"{c['costo_fijo']:,.0f} | {100 * c['tasa']:.1f} % | {c['vpn']:,.0f} | {fmt_pct(c['tir'])} | "
                 f"{fmt_pb(c['pb'])} / {fmt_pb(c['pbd'])} | {c['umbral_lote']:,.0f} |")
    L += ["", "## Flujos anuales", ""]
    for c in res:
        L.append(f"- {c['alternativa']} {c['escenario']}: " + "; ".join(f"año {k}: {v:,.0f}" for k, v in enumerate(c['flujos'])))
    ahorro = e["REF"] - e["P1-C75"]
    L += ["", "## Cambio operativo REF -> P1-C75 (mismo equipo, sin inversión)", "",
          f"Ahorro: {ahorro:.2f} kWh/lote = {ahorro * TARIFA_NO_RES:,.0f} COP/lote con tarifa no residencial "
          f"({ahorro * TARIFA_RES:,.0f} con residencial), a cambio de {t['P1-C75'] - t['REF']:.1f} h más por lote.", "",
          "| Lotes/año | Ahorro anual [COP] | VP 5 años a 8 % | a 12 % | a 16 % |", "|---|---|---|---|---|"]
    for lotes in (20, 40, 60):
        anual = ahorro * TARIFA_NO_RES * lotes
        L.append(f"| {lotes} | {anual:,.0f} | " + " | ".join(f"{vpn(r, [0] + [anual] * H):,.0f}" for r in (0.08, TASA_REAL_CENTRAL, 0.16)) + " |")
    L += ["", "## Sensibilidad de un factor a la vez (alternativa A, caso central)", "",
          "| Factor | Valor bajo | VPN | Valor alto | VPN |", "|---|---|---|---|---|"]
    for nombre, idx, bajo, alto in (("Lotes/año", 0, 20, 60), ("Tasa real", 1, 0.16, 0.08),
                                    ("Min. de supervisión por hora", 2, 5.0, 15.0), ("Sobresecado evitado [pts]", 3, 0.0, 0.010),
                                    ("Mantenimiento [% equipos]", 5, 0.04, 0.02), ("Valor residual [% equipos]", 6, 0.0, 0.40)):
        vals = []
        for v in (bajo, alto):
            p = list(ESCENARIOS["Central"]); p[idx] = v
            vals.append(vpn_a(tuple(p)))
        fb = f"{100 * bajo:.1f} %" if idx in (1, 5, 6) else (f"{100 * bajo:.1f}" if idx == 3 else f"{bajo:g}")
        fa = f"{100 * alto:.1f} %" if idx in (1, 5, 6) else (f"{100 * alto:.1f}" if idx == 3 else f"{alto:g}")
        L.append(f"| {nombre} | {fb} | {vals[0]:,.0f} | {fa} | {vals[1]:,.0f} |")
    L += ["", f"Ocupación del secador a 60 lotes/año: REF {60 * t['REF']:,.0f} h, P1-C75 {60 * t['P1-C75']:,.0f} h de secado."]
    with open(os.path.join(OUT, "resumen.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()

"""Genera el diagrama técnico de la simulación (SVG, PNG y PDF)."""
from xml.sax.saxutils import escape

W, H = 2000, 1330
FONT = "DejaVu Sans, Arial, sans-serif"

C_PY = ("#1b5e20", "#e8f5e9", "#2e7d32")     # borde, fondo, cabecera
C_MB = ("#424242", "#f5f5f5", "#616161")
C_CS = ("#0d47a1", "#e3f2fd", "#1565c0")
C_EXT = ("#6a1b9a", "#f3e5f5", "#7b1fa2")

out = []


def t(x, y, s, size=15, weight="normal", color="#212121", anchor="start", style=""):
    out.append(f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
               f'fill="{color}" text-anchor="{anchor}" {style}>{escape(s)}</text>')


def caja(x, y, w, h, num, titulo, archivo, secciones, col, lh=21):
    borde, fondo, cab = col
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fondo}" stroke="{borde}" stroke-width="2.5"/>')
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="58" rx="10" fill="{cab}"/>')
    out.append(f'<rect x="{x}" y="{y + 40}" width="{w}" height="18" fill="{cab}"/>')
    out.append(f'<circle cx="{x + 26}" cy="{y + 29}" r="17" fill="#ffffff"/>')
    t(x + 26, y + 35, str(num), 17, "bold", cab, "middle")
    t(x + 52, y + 27, titulo, 17, "bold", "#ffffff")
    t(x + 52, y + 49, archivo, 13, "normal", "#ffffffdd", style='font-style="italic"')
    yy = y + 84
    for nombre, lineas in secciones:
        t(x + 14, yy, nombre, 14, "bold", borde)
        yy += lh
        for l in lineas:
            t(x + 22, yy, "• " + l if not l.startswith("  ") else l, 14)
            yy += lh
        yy += 6
    return yy


MARCAS = {"#37474f": "m", "#2e7d32": "mg", "#1565c0": "mb"}


def flecha(x1, y1, x2, y2, color="#37474f", w=3):
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" '
               f'marker-end="url(#{MARCAS[color]})"/>')


def pastilla(cx, cy, l1, l2):
    out.append(f'<rect x="{cx - 46}" y="{cy - 44}" width="92" height="36" rx="8" fill="#ffffff" stroke="#37474f" stroke-width="1.5"/>')
    t(cx, cy - 29, l1, 12, "bold", "#37474f", "middle")
    t(cx, cy - 14, l2, 12, "bold", "#37474f", "middle")


out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
out.append('<defs>' + "".join(
    f'<marker id="{i}" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto">'
    f'<path d="M0,0 L12,6 L0,12 z" fill="{c}"/></marker>' for c, i in (("#37474f", "m"), ("#2e7d32", "mg"), ("#1565c0", "mb"))) + '</defs>')
out.append(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

t(W / 2, 46, "Simulación del secado de café con supervisión IoT: flujo de información y variables", 26, "bold",
  "#212121", "middle")
t(W / 2, 76, "Lote de 80 kg c.p.s. · humedad 55 % → 11 % b.h. · Chinchiná (Caldas) · Python (planta) ↔ Modbus TCP ↔ CODESYS (supervisión y HMI)",
  16, "normal", "#455a64", "middle")

# ---------------- Banda Python ----------------
out.append(f'<rect x="20" y="100" width="{W - 40}" height="575" rx="14" fill="none" stroke="{C_PY[0]}" '
           'stroke-width="2" stroke-dasharray="8 6"/>')
t(40, 126, "PYTHON — PLANTA SIMULADA  (python modbus_server.py --plant modelo --factor-aceleracion 540 --port 5020)", 16,
  "bold", C_PY[0])

bw, bh, by = 334, 520, 140
xs = [40 + i * (334 + 60) for i in range(5)]

caja(xs[0], by, bw, bh, 1, "CLIMA DE CHINCHINÁ", "generador_ambiente.py", [
    ("Datos de entrada", ["T mín 16.4 °C / T máx 26.8 °C", "  (estación Naranjal, Cenicafé)",
                          "Hora T mín 05:30, T máx 15:30", "Variación día a día: NASA POWER",
                          "  σ T mín 0.97 °C, σ T máx 1.36 °C"]),
    ("Calcula", ["T(t): curva diaria asimétrica", "ea = 0.97 · es(T mín)",
                 "  (vapor del aire ≈ constante)", "RH = ea / es(T)"]),
    ("Salidas", ["T_ambiente  [°C]  16 – 27", "RH_ambient [%]   50 – 97", "ea [kPa]  (agua en el aire)"]),
], C_PY)

caja(xs[1], by, bw, bh, 2, "VENTILADOR", "Manipulada 2 · S&P CBM/6-180/180-N-72W", [
    ("Entradas (desde CODESYS)", ["fan_cmd  (0 apagado / 1 encendido)", "fan_speed_pct  (30 – 100 %)"]),
    ("Calcula", ["caudal = 8 m³/min × pct / 100", "  (0.1 m³/min por kg, Cenicafé)",
                 "ṁ_aire = caudal × ρ_aire  [kg/s]", "P_vent = 0.20 kW × (pct/100)³",
                 "Sin ventilador → resistencia", "  bloqueada (enclavamiento)"]),
    ("Salidas", ["caudal_m3_min  (2.4 – 8.0)", "ṁ_aire → plenum y lecho", "P_vent → energía"]),
], C_PY)

caja(xs[2], by, bw, bh, 3, "RESISTENCIA + PLENUM", "dinamica_termica.py · Manipulada 1", [
    ("Entradas", ["T_ambiente, ea, ṁ_aire", "Permiso: RUN y fan_cmd = 1", "Setpoint 50 °C (máx. del grano)"]),
    ("Calcula (cada 1 s de modelo)", ["Termostato: ON si T_process < 50", "Balance de energía del aire:",
                                      "  C·dT/dt = P_res − ṁ·cp·(T − T_amb)", "P_res = 6 kW (3 × 2 kW, Tempco)",
                                      "Constante de tiempo ≈ 106 s", "RH_process = ea / es(T_process)"]),
    ("Salidas", ["T_process  ≈ 50 °C  (CONTROLADA)", "RH_process ≈ 15 %", "heater_duty  [% tiempo ON]"]),
], C_PY)

caja(xs[3], by, bw, bh, 4, "LECHO DE CAFÉ: 8 CAPAS", "lecho_secado.py + cinetica_roa.py", [
    ("Entradas", ["T_process, ea, ṁ_aire", "flow_dir_cmd: sentido del aire", "  (se invierte cada 6 h)"]),
    ("Calcula en cada capa (paso 1 min)", ["Me(T, RH): humedad de equilibrio", "  (isoterma de Roa, Cenicafé)",
                                           "k = m·(Pvs − Pv)^n  (velocidad)", "M → Me según la ecuación de Roa",
                                           "El aire sale más frío y húmedo", "  y entra a la capa siguiente"]),
    ("Salidas", ["M_coffee  promedio [% b.h.]", "M_coffee_max  capa más húmeda", "Agua evaporada [kg]"]),
], C_PY)

caja(xs[4], by, bw, bh, 5, "ENERGÍA Y TIEMPO", "secador_electrico.py", [
    ("Calcula", ["E_resistencia = Σ P_res · Δt", "E_ventilador = Σ P_vent · Δt", "kWh por kg de café",
                 "kJ por kg de agua evaporada", "tiempo_proceso_h (horas de modelo)"]),
    ("Escala de tiempo", ["1 ciclo = 1 s real", "factor 540 → 0.15 h de modelo", "Secado completo ≈ 3.7 min reales",
                          "Termostato: 1 s · Lecho: 1 min"]),
    ("Salidas", ["tiempo_proceso_h", "heartbeat (+1 cada ciclo)", "safety_ok (watchdog Python)"]),
], C_PY)

# flechas entre cajas de la planta
ay = 400
for i in range(4):
    flecha(xs[i] + bw + 2, ay, xs[i + 1] - 4, ay)
lab = [("T_amb, ea", "RH_amb"), ("ṁ_aire", "caudal"), ("T_process", "RH_process"), ("agua", "evaporada")]
for i, (a, b) in enumerate(lab):
    pastilla(xs[i] + bw + 30, ay - 6, a, b)

# ---------------- Banda Modbus ----------------
my = 700
out.append(f'<rect x="20" y="{my}" width="{W - 40}" height="150" rx="14" fill="{C_MB[1]}" stroke="{C_MB[0]}" stroke-width="2.5"/>')
t(W / 2, my + 30, "MODBUS TCP · 127.0.0.1 : 5020 · Python = esclavo · CODESYS = maestro · sondeo cada 100 ms", 17, "bold",
  C_MB[0], "middle")
t(50, my + 62, "Flechas verdes: Python → CODESYS (lectura FC03, cada REAL = 2 registros):", 15, "bold", C_PY[0])
t(50, my + 86, "0-1 T_process · 4-5 RH_ambient · 7 safety_ok · 8-9 M_coffee · 10-11 tiempo_proceso_h · 12 heartbeat", 14)
t(50, my + 108, "13-14 RH_process · 16-17 M_coffee_max · 18-19 heater_duty · 22-23 caudal_m3_min", 14)
t(1080, my + 62, "Flechas azules: CODESYS → Python (escritura FC06):", 15, "bold", C_CS[0])
t(1080, my + 86, "2 heater_cmd · 3 fan_cmd · 6 plant_mode (0 RUN / 1 HOLD)", 14)
t(1080, my + 108, "15 flow_dir_cmd · 20 fan_speed_pct", 14)
t(50, my + 136, "Watchdog Python: si CODESYS no escribe en 5 s → heater y fan forzados a 0, safety_ok = 0.   "
                "Watchdog CODESYS: si heartbeat no cambia en 4 s → comm_error.", 13, "normal", "#455a64")
GV, AZ = "#2e7d32", "#1565c0"
c = lambda i: xs[i] + bw / 2
# CODESYS -> Python (escrituras): suben a ventilador, resistencia y lecho
for x in (c(1), c(2) - 60, c(3) - 60):
    flecha(x, my - 2, x, by + bh + 6, AZ)
# Python -> CODESYS (lecturas): bajan desde resistencia, lecho y energía
for x in (c(2) + 60, c(3) + 60, c(4)):
    flecha(x, by + bh + 2, x, my - 6, GV)
# Modbus <-> CODESYS
for x in (150, 360):
    flecha(x, my + 152, x, 916, GV)
for x in (760, 980):
    flecha(x, 914, x, my + 154, AZ)

# ---------------- Banda CODESYS ----------------
cy = 880
out.append(f'<rect x="20" y="{cy}" width="{W - 40}" height="405" rx="14" fill="none" stroke="{C_CS[0]}" '
           'stroke-width="2" stroke-dasharray="8 6"/>')
t(W - 40, cy + 26, "CODESYS CONTROL WIN V3 — SUPERVISIÓN (PLC_PRG v3) Y HMI", 16, "bold", C_CS[0], "end")
cby, cbh = cy + 40, 350
caja(40, cby, 470, cbh, 6, "COMUNICACIÓN Y SEGURIDAD", "PLC_PRG · canales Modbus_TCP_Slave", [
    ("Recibe y convierte", ["2 WORD → REAL (U_WORDS_TO_REAL)", "T_process, M_coffee, M_coffee_max,",
                            "  tiempo_secado_h, heater_duty, caudal"]),
    ("Vigila", ["heartbeat congelado 4 s → comm_error", "safety_alarm = (safety_ok = 0) OR comm_error",
                "Con comm_error todo pasa a valor seguro"]),
], C_CS)
caja(530, cby, 640, cbh, 7, "LÓGICA DE SUPERVISIÓN", "PLC_PRG v3 · decide los comandos", [
    ("Condición de marcha", ["en_marcha = RUN AND NOT comm_error AND NOT fin_secado"]),
    ("Comandos que envía a Python", ["fan_cmd = en_marcha", "heater_cmd = en_marcha  (permiso; Python regula a 50 °C)",
                                    "flow_dir_cmd = (TRUNC(tiempo)/6) MOD 2 → invierte el aire cada 6 h",
                                    "fan_speed_pct = consigna del HMI, limitada a 30 – 100 %"]),
    ("Fin del secado (se enclava)", ["M_coffee ≤ 11 %  Y  M_coffee_max ≤ 12 %  →  apaga todo",
                                     "reset_lote: borra fin_secado (nuevo lote)"]),
], C_CS)
caja(1190, cby, 400, cbh, 8, "HMI", "Visualización de destino / web", [
    ("Muestra", ["T_process · RH_ambient · RH_process", "M_coffee · M_coffee_max · tiempo",
                 "heater_duty · caudal_m3_min · setpoint"]),
    ("Pilotos", ["Heater · Fan · Comunicación", "Planta en marcha · Aire invertido", "Secado terminado"]),
    ("Mandos y gráfica", ["Modo RUN/HOLD · caudal % · Nuevo lote", "Tendencia: curva de secado"]),
], C_CS)
caja(1610, cby, 330, cbh, 9, "FLUIDSIM (OPC)", "Actuación neumática", [
    ("Recibe de CODESYS", ["flow_dir_cmd → cilindro", "  doble efecto que mueve", "  la compuerta del aire",
                           "Ciclo carga / descarga", "  (máquina de estados)"]),
    ("Estado", ["Integración OPC probada;", "  circuito completo en", "  desarrollo"]),
], C_EXT)
flecha(511, cby + 175, 527, cby + 175)
flecha(1171, cby + 175, 1187, cby + 175)
flecha(1591, cby + 175, 1607, cby + 175)

# ---------------- Pie: clasificación de variables ----------------
t(40, H - 14, "Clasificación (Guía 9.1):  Controlada: T_process  ·  Salida: M_coffee / M_coffee_max  ·  Manipulada 1: resistencia (heater)  ·  "
              "Manipulada 2: caudal (fan_speed_pct)  ·  Perturbación: clima de Chinchiná  ·  Restricciones: 50 °C máx., enclavamiento, watchdog",
  14, "bold", "#37474f")

out.append("</svg>")
svg = "\n".join(out)
open("diagrama_simulacion.svg", "w", encoding="utf-8").write(svg)
import cairosvg

cairosvg.svg2png(bytestring=svg.encode(), write_to="diagrama_simulacion.png", output_width=W * 1.5)
cairosvg.svg2pdf(bytestring=svg.encode(), write_to="diagrama_simulacion.pdf")
print("ok")

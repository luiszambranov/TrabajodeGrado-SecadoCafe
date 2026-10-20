"""Genera la Figura 1 simplificada: arquitectura y flujo de información."""
import cairosvg, sys

F = "Liberation Sans, Arial, Helvetica, sans-serif"
GREEN, BLUE = "#2E7D32", "#1565C0"
INK, MUTED, LINE = "#212121", "#424242", "#616161"

# (color de cabecera, fondo del cuerpo)
PY = ("#2E7D32", "#E8F5E9")
CS = ("#1565C0", "#E3F2FD")
FS = ("#6A1B9A", "#F3E5F5")
HM = ("#455A64", "#ECEFF1")

out = []
def a(s): out.append(s)

def box(x, y, w, h, title, lines, col, fs=21):
    head, bg = col
    hh = 50
    a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{bg}" stroke="{head}" stroke-width="2"/>')
    a(f'<path d="M{x} {y+hh} V{y+10} Q{x} {y} {x+10} {y} H{x+w-10} Q{x+w} {y} {x+w} {y+10} V{y+hh} Z" fill="{head}"/>')
    a(f'<text x="{x+w/2}" y="{y+33}" text-anchor="middle" font-family="{F}" font-size="24" font-weight="bold" fill="#FFFFFF">{title}</text>')
    ty = y + hh + 38
    for ln in lines:
        a(f'<text x="{x+22}" y="{ty}" font-family="{F}" font-size="{fs}" fill="{INK}">• {ln}</text>')
        ty += 33

def arrow(x1, y1, x2, y2, color, w=3.5):
    mid = "g" if color == GREEN else "b"
    a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{w}" marker-end="url(#ar{mid})"/>')

def label(x, y, lines, color, anchor):
    for i, ln in enumerate(lines):
        a(f'<text x="{x}" y="{y+i*24}" text-anchor="{anchor}" font-family="{F}" font-size="19" fill="{color}">{ln}</text>')

def chip(cx, cy, text, w):
    a(f'<rect x="{cx-w/2}" y="{cy-19}" width="{w}" height="38" rx="19" fill="#FFFFFF" stroke="{LINE}" stroke-width="1.5"/>')
    a(f'<text x="{cx}" y="{cy+7}" text-anchor="middle" font-family="{F}" font-size="19" font-weight="bold" fill="{MUTED}">{text}</text>')

W, H = 1000, 975
a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
a('<defs>')
for k, c in (("g", GREEN), ("b", BLUE), ("k", LINE)):
    a(f'<marker id="ar{k}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 Z" fill="{c}"/></marker>')
a('</defs>')
a(f'<rect width="{W}" height="{H}" fill="#FFFFFF"/>')

BX, BW = 110, 450          # columna principal
CX = BX + BW / 2
XD, XU = CX - 80, CX + 80   # flecha que baja / flecha que sube

# Perturbaciones
a(f'<rect x="{BX+40}" y="15" width="{BW-80}" height="78" rx="39" fill="#FAFAFA" stroke="{LINE}" stroke-width="1.5" stroke-dasharray="7 5"/>')
a(f'<text x="{CX}" y="47" text-anchor="middle" font-family="{F}" font-size="20" font-weight="bold" fill="{MUTED}">Perturbaciones</text>')
a(f'<text x="{CX}" y="74" text-anchor="middle" font-family="{F}" font-size="19" fill="{MUTED}">clima de Chinchiná y humedad inicial</text>')
a(f'<line x1="{CX}" y1="93" x2="{CX}" y2="140" stroke="{LINE}" stroke-width="3.5" marker-end="url(#ark)"/>')

# Python
box(BX, 145, BW, 172, "Python · planta simulada",
    ["Clima, lecho de 8 capas y cinética", "Resistencia de 6 kW y ventilador", "Servidor Modbus TCP (puerto 5020)"], PY)

# Enlace Modbus
arrow(XD, 319, XD, 459, GREEN)
arrow(XU, 459, XU, 319, BLUE)
chip(CX, 389, "Modbus TCP", 150)
label(XD - 16, 371, ["Temperatura, HR,", "humedad, energía,", "heartbeat"], GREEN, "end")
label(XU + 16, 371, ["Consigna, resistencia,", "ventilador, sentido", "del aire"], BLUE, "start")

# CODESYS
box(BX, 464, BW, 172, "CODESYS · supervisión (PLC)",
    ["PLC_PRG: consigna y watchdog", "SECUENCIA: máquina de estados", "Alarmas y fin de secado"], CS)

# HMI
HX, HW = 680, 300
box(HX, 464, HW, 172, "HMI · operador",
    ["Elige perfil y caudal", "START, STOP, Nuevo lote", "Ve variables y alarmas"], HM, fs=19)
a(f'<line x1="{BX+BW+4}" y1="550" x2="{HX-4}" y2="550" stroke="{LINE}" stroke-width="3.5" marker-start="url(#ark)" marker-end="url(#ark)"/>')

# Enlace OPC
arrow(XD, 638, XD, 778, BLUE)
arrow(XU, 778, XU, 638, GREEN)
chip(CX, 708, "OPC", 90)
label(XD - 16, 690, ["Bobinas de válvulas,", "relé K1, semáforo"], BLUE, "end")
label(XU + 16, 690, ["Pulsadores y", "finales de carrera"], GREEN, "start")

# FluidSIM
box(BX, 783, BW, 172, "FluidSIM · actuación",
    ["Compuerta de inversión del aire", "Entrada y salida de la bandeja", "Pulsadores y semáforo"], FS)

# Lazo de supervisión
LX, LY, LW, LH = 680, 700, 300, 255
a(f'<rect x="{LX}" y="{LY}" width="{LW}" height="{LH}" rx="10" fill="#FFFDE7" stroke="#F9A825" stroke-width="2"/>')
a(f'<text x="{LX+LW/2}" y="{LY+36}" text-anchor="middle" font-family="{F}" font-size="22" font-weight="bold" fill="{INK}">Ciclo de supervisión</text>')
steps = ["1. Python mide la planta", "2. CODESYS decide el estado", "3. FluidSIM mueve la", "    compuerta", "4. El final de carrera fija", "    el sentido del aire", "    en la planta"]
for i, s in enumerate(steps):
    ind = 22 if s.startswith("    ") else 0
    a(f'<text x="{LX+20+ind}" y="{LY+72+i*26}" font-family="{F}" font-size="19" fill="{INK}">{s.strip()}</text>')

a('</svg>')
svg = "\n".join(out)
open(sys.argv[1] + ".svg", "w", encoding="utf8").write(svg)
cairosvg.svg2png(bytestring=svg.encode(), write_to=sys.argv[1] + ".png", output_width=2400)

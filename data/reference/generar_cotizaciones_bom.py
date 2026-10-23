"""Genera data/reference/cotizaciones_bom.md y cotizaciones_bom.csv.

Precios consultados el 19-20 oct 2026. COP con IVA. Importados: precio sin IVA
x tasa x 1,37 (IVA 19 % x 1,15 por envio y arancel; supuesto propio).
"""
import csv, math, sys

EUR, USD, F_IMP = 3569.90, 3170.46, 1.37

def imp_eur(p): return round(p * EUR * F_IMP)
def imp_usd(p): return round(p * USD * F_IMP)

OK, CONF = "Cumple", "Cumple; confirmar"
# grupo, componente, requisito del diseño, producto cotizado, cant, precio unit COP,
# origen del precio, enlace, verificacion, escenario, electrico?
R = [
 # ---------------- Proceso
 ("Proceso", "Resistencia tubular aleteada", "3 x 2 kW = 6 kW instalados (5,5 kW requeridos, Ec. 5)",
  "Resistencia aleteada 40x80 2000 W 220 V", 3, imp_eur(69.17), "Tecnirecambio (España), 69,17 € sin IVA",
  "https://www.tecnirecambio.com/resistencia_aleteada_40x80_2000w_220v",
  OK + ": 2 kW a 220 V, equivalente a la Tempco de 240 V del dimensionamiento", "A", True),
 ("Proceso", "Ventilador centrífugo trifásico", "≥ 100 Pa a 480 m³/h (8 m³/min); motor trifásico para el variador",
  "Soler & Palau CBT-80N, 0,37 kW, trifásico 230/400 V, 2 800 rpm, 730 m³/h máx.", 1, imp_eur(476.66),
  "Distribuidor Eléctrico (España), 476,66 € sin IVA",
  "https://distribuidorelectrico.com/cbt-n-ventiladores-centrifugos-sp/13825-ventilador-centrifugo-cbt-80n-solerpalau-8413893155726.html",
  CONF + ": serie de media presión (curvas hasta ~1 800 Pa, ficha EN_CBT-N de S&P); motor de 50 Hz alimentado por el variador; verificar el punto exacto en la curva", "A", True),
 ("Proceso", "Variador de frecuencia", "Entrada monofásica 220 V, salida trifásica, ≥ 0,37 kW, 30–100 % de caudal",
  "Delta VFD015M21A (VFD-M), 1,5 kW, entrada 1F 220 V, salida 3F 0–400 Hz", 1, 595000,
  "Industriales Andes (Colombia)",
  "https://industrialesandes.co/es/motores-y-drivers/170-variador-de-frecuencia-vfd015m21a-2hp-220vac-15kw-salida-trifasica.html",
  OK + ": 7 A de salida para un motor de 0,37 kW; control analógico y digital", "A", True),
 ("Proceso", "Relé de estado sólido", "Una por resistencia: 9,1 A a 220 V; mando 24 VDC desde el PLC",
  "SSR-40DA, 40 A, carga 24–380 VAC, mando 3–32 VDC", 3, 33900, "Electronilab (Colombia)",
  "https://electronilab.co/tienda/rele-estado-solido-24-380vac-40a-ssr-40da/",
  OK + ": margen de 4x en corriente; necesita disipador", "A", True),
 ("Proceso", "Disipador para relé de estado sólido", "Disipar el calor de cada SSR (≈ 1 W/A)",
  "Disipador de aluminio para SSR, base 80 x 50 mm", 3, 9800, "Industriales Andes (Colombia)",
  "https://industrialesandes.co/en/maniobra/128-disipador-de-aluminio-para-rele-de-estado-solido-ssr.html",
  OK + " (agregado en la verificación)", "A", True),
 ("Proceso", "Contactor de seguridad", "Corte general de las resistencias: 27,3 A resistivos (6 kW / 220 V)",
  "CJX2-2510, bobina 220 VAC, Ith 40 A", 1, 52000, "Industriales Andes (Colombia)",
  "https://industrialesandes.co/en/maniobra/117-contactor-cjx2-2510-bobina-a-220v.html",
  OK + ": 40 A en carga resistiva (AC-1); 25 A en AC-3 no aplica a resistencias", "A", True),
 # ---------------- Seguridad
 ("Seguridad", "Presostato diferencial de aire", "Confirmar flujo de aire antes de calentar (≈ 100 Pa de diseño)",
  "Belimo 01APS-10R, 20–300 Pa, 1 A a 250 VAC", 1, imp_usd(34.53), "Tameson, 34,53 USD sin IVA",
  "https://tameson.com/products/differential-pressure-switch-20-300pa-m27jr", OK, "A", True),
 ("Seguridad", "Termostato de seguridad", "Límite alto en la caja de resistencias, rearme manual",
  "Termostato capilar 90–110 °C, rearme manual", 1, imp_eur(20.58), "Sercatec (España), 24,90 € con IVA de España",
  "https://www.sercatec.com/termostato-capilar-90-110-c-rearme.html",
  OK + ": dispara si falla el aire (operación normal ≈ 55 °C)", "A", True),
 # ---------------- Instrumentacion
 ("Instrumentación", "Sonda PT100", "Temperatura del plenum, 35–55 °C", "PT100 3 hilos, rosca M6, 2 m",
  1, 29900, "Electronilab (Colombia)",
  "https://electronilab.co/tienda/sensor-de-temperatura-rtd-platino-pt100-tornillo-m6-3-hilos-2-metros/", OK, "A", True),
 ("Instrumentación", "Transmisor PT100", "Señal 4–20 mA para la entrada analógica", "Transmisor PT100 0–100 °C, 4–20 mA, 24 V",
  1, 23969, "Industriales Andes (Colombia)",
  "https://industrialesandes.co/es/sensores/749-transmisor-de-temperatura-pt100-0-100-grados-4-20ma.html", OK, "A", True),
 ("Instrumentación", "Transmisor de humedad relativa ambiente", "RH_ambient (registro 4–5), 4–20 mA",
  "Comet P3110E, 0–100 % HR (±3 %), −30 a 80 °C, salida 4–20 mA configurable, IP65", 1, imp_eur(153.00),
  "Didactum (Alemania), 153 € sin IVA",
  "https://didactum-security.com/en/P3110E_comet-p3110e-4-20ma-transmitter-for-temperature-30-to-80-0c-humidity-0-100-rh",
  OK + ": una salida, configurada como HR (la temperatura ambiente no tiene registro)", "A", True),
 ("Instrumentación", "Medidor de humedad del grano", "Confirmar el fin del secado (10–12 % b.h.) en café pergamino; contrastar con ISO 6673",
  "Agratronix 08150, café verde y pergamino, 8–38 %, ±0,5 %", 1, imp_usd(650.00), "Tecfresh, 650 USD",
  "https://tecfresh.com/producto/medidor-de-humedad-de-cafe-08150/",
  OK + ": declara curva para café pergamino y cubre el rango final (8–38 %). Reemplaza al medidor genérico de 817 000 COP, que no indica rango ni curva para pergamino", "A", False),
 # ---------------- Actuacion
 ("Actuación", "Cilindro de la compuerta", "Doble efecto; finales de carrera magnéticos 1B1/1B2",
  "Cilindro SAI doble efecto Ø32 x 125 mm", 1, 401876, "Industriales Andes (Colombia)",
  "https://industrialesandes.co/es/neumatica/706-cilindro-neumatico-sai-32-x-125.html",
  CONF + " con el proveedor que el pistón es magnético (la ficha solo indica ranuras para sensor)", "A", False),
 ("Actuación", "Electroválvula 5/2 biestable", "Mantener posición sin señal; bobinas 24 VDC",
  "Electroválvula biestable 5/2, 1/4\" NPT, 24 VDC, 1,5–8 bar", 1, 109000, "Ingecom (Colombia)",
  "https://ingecomsas.com/producto/electrovalvula-biestable-1-4-npt-5-2-24vdc-stnc/", OK, "A", True),
 ("Actuación", "Sensor magnético de cilindro", "Finales de carrera 1B1 y 1B2", "CS1-J", 2, 15646,
  "Industriales Andes (Colombia)", "https://industrialesandes.co/es/sensores/", "Cumple; sin página propia del producto", "A", True),
 ("Actuación", "Sensor inductivo de bandeja", "Posición de la bandeja manual 2B1 y 2B2", "PL-05N", 2, 25000,
  "Industriales Andes (Colombia)", "https://industrialesandes.co/es/sensores/", "Cumple; sin página propia del producto", "A", True),
 ("Actuación", "Regulador de caudal", "Velocidad del cilindro", "Racor SL6-02 con control de flujo, 1/4\", tubo 6 mm",
  2, 10800, "Industriales Andes (Colombia)",
  "https://industrialesandes.co/es/neumatica/281-racor-14-abertura-6mm-con-control-de-flujo-sl6-02.html", OK, "A", False),
 ("Actuación", "Unidad de mantenimiento", "Filtrar y regular el aire a la válvula", "Filtro + regulador 1/4\"",
  1, 68000, "Ingecom (Colombia)", "https://ingecomsas.com/", "Cumple; sin página propia del producto", "A", False),
 ("Actuación", "Manguera neumática", "Tubo de 6 mm", "Manguera resorte 6 mm x 15 m", 1, 72000,
  "Industriales Andes (Colombia)",
  "https://industrialesandes.co/es/neumatica/373-manguera-resorte-neumatica-6mm-15-metros.html", OK, "A", False),
 ("Actuación", "Compresor", "Aire a ≥ 1,5 bar para la válvula (consumo muy bajo)", "Fujita FGM1524L, 2 HP, 24 L, 120 psi, 120 V",
  1, 844900, "Homecenter (Colombia); precio normal (en oferta a 593 900 hasta el 28 oct)",
  "https://www.homecenter.com.co/homecenter-co/product/616954/compresor-de-aire-de-2hp-y-24-litros/616954/",
  OK + ": sobredimensionado para un cilindro; ver alternativa eléctrica", "A", False),
 # ---------------- Control
 ("Control", "PLC", "≥ 9 entradas y 7 salidas digitales, Ethernet (referencia de cálculo)",
  "Siemens S7-1200 CPU 1212C (8 DI, 6 DO, 2 AI 0–10 V)", 1, 1765000, "Industriales Andes (Colombia)",
  "https://industrialesandes.co/en/plc/471-plc-s7-1200-cpu-1212c-6es7-212-1ae40-0xb0.html",
  OK + " con los módulos de expansión; decisión del controlador abierta", "A", True),
 ("Control", "Módulo E/S digital", "Completar entradas (START, STOP, emergencia, 4 finales, presostato, termostato)",
  "Siemens SM 1223, 8 DI / 8 DO relé", 1, imp_eur(169.86), "Relepro (España), 169,86 € sin IVA",
  "https://relepro.com/plc-simatic-s7-1200/277/siemens_simatic-s7-1200-es-digital-sm-1223-8di8do_6es7223-1ph32-0xb0.html", OK, "A", True),
 ("Control", "Módulo de entradas analógicas", "2 señales de 4–20 mA (temperatura del plenum y HR)",
  "Siemens SM 1231, 4 AI", 1, imp_eur(217.76), "Relepro (España), 217,76 € sin IVA",
  "https://relepro.com/plc-simatic-s7-1200/283/siemens_simatic-s7-1200-entrada-analog-sm-1231-4ai_6es7231-4hd32-0xb0.html",
  OK + ": la hoja de datos de Siemens admite 4–20 mA", "A", True),
 ("Control", "HMI", "Pantalla de operador con Ethernet", "Kinco GL070E, 7\", Ethernet", 1, 570000,
  "Industriales Andes (Colombia)", "https://industrialesandes.co/en/13-pantallas-hmi",
  CONF + " el driver del PLC elegido con el proveedor", "A", True),
 ("Control", "Fuente 24 VDC", "PLC, sensores, válvula y torre de luces (< 3 A)", "Mean Well EDR-120-24, 5 A, riel DIN",
  1, 239000, "Industriales Andes (Colombia)",
  "https://industrialesandes.co/es/plc/194-fuente-conmutada-24v-5a-edr-120-24-mw-para-riel.html", OK, "A", True),
 ("Control", "Pulsadores START y STOP", "START NA y STOP NC (Anexo D)", "LA38, 22 mm, 1 NA + 1 NC", 2, 15000,
  "Industriales Andes (Colombia)",
  "https://industrialesandes.co/es/maniobra/335-pulsador-la38-rojo-de-22mm-1-nc-1-no.html", OK, "A", True),
 ("Control", "Paro de emergencia", "Hongo con enclavamiento y contacto NC (Anexo D)", "Autonics S2ER-E3RB, 22 mm, 1 NC",
  1, 24000, "Ingecom (Colombia)", "https://ingecomsas.com/producto/pulsador-parada-de-emergencia-40-mm-autonics/",
  OK + ". Reemplaza al de DynamoElectronics, que solo tiene contactos NA", "A", True),
 ("Control", "Torre de luces", "Semáforo verde, amarillo y rojo a 24 VDC", "TA-205-3WJ, 3 colores, 24 VDC",
  1, 214400, "Industriales Andes (Colombia)",
  "https://industrialesandes.co/es/sensores/105-baliza-de-senal-multiple-ta-205-3wj-dc24v.html", OK, "A", True),
 # ---------------- Tablero
 ("Tablero", "Gabinete metálico", "Alojar PLC, fuente, SSR y protecciones", "Caja 40 x 40 x 20 cm, lámina CR cal. 20",
  1, 119900, "Homecenter (Colombia); agotado el 20 oct",
  "https://www.homecenter.com.co/homecenter-co/product/290309/caja-de-paso-40x40x20-cm-c20/290309/",
  "Cumple en tamaño; precio de referencia (agotado)", "A", False),
 ("Tablero", "Mini breaker 2 polos", "Resistencias (27,3 A) y mando", "Schneider Easy9 2P 32 A curva C",
  2, 17900, "Homecenter (Colombia); agotado el 20 oct",
  "https://www.homecenter.com.co/homecenter-co/product/136015/mini-breaker-easy9-2-polos-32-a-10-ka-230-400-v-ac-curva-c-riel-din/136015/",
  "Cumple; precio de referencia (agotado)", "A", False),
 # ---------------- Estructura: kit de inversion (A) y camara (B)
 ("Estructura", "Lámina galvanizada (ductos y caja de inversión)", "≈ 7 m² + 15 % de desperdicio",
  "Lámina galvanizada cal. 20 (0,9 mm) 4 x 8 pies, 20,1 kg", 3, 132040, "Aceros Bonilla (Bogotá), IVA incluido",
  "https://www.acerosbonilla.com/shop/lgv48c20-lamina-galvanizada-4-x-8-cal-20-20-07kg-2179?category=9",
  OK + ": ductos de 25 x 25 cm, aire a 2,1 m/s", "A", False),
 ("Estructura", "Ángulo de acero (soportes de ductos)", "≈ 6 m", "Ángulo 1\" x 1/8\" x 6 m", 1, 33900,
  "Homecenter (Colombia)", "https://www.homecenter.com.co/homecenter-co/product/103061/angulo-6m-x-1-x-1-8-pg/103061/", OK, "A", False),
 ("Estructura", "Aislamiento térmico", "≈ 14 m² (cámara y ductos)", "Lana de vidrio 50 mm R13.9, rollo 1,2 x 24 m (28,8 m²)",
  1, 227900, "Homecenter (Colombia)",
  "https://www.homecenter.com.co/homecenter-co/product/916375/lana-vidrio-50mm-r139-12x24m/916375/",
  CONF + " la temperatura máxima de servicio en la ficha del fabricante (operación ≤ 60 °C)", "A", False),
 ("Estructura", "Lámina galvanizada (cámara de secado)", "Doble pared, fondo y tapa: ≈ 12,4 m² + 15 %",
  "Lámina galvanizada cal. 20 (0,9 mm) 4 x 8 pies, 20,1 kg", 5, 132040, "Aceros Bonilla (Bogotá), IVA incluido",
  "https://www.acerosbonilla.com/shop/lgv48c20-lamina-galvanizada-4-x-8-cal-20-20-07kg-2179?category=9", OK, "B", False),
 ("Estructura", "Ángulo de acero (marco de la cámara y de la bandeja)", "≈ 27 m", "Ángulo 1\" x 1/8\" x 6 m", 4, 33900,
  "Homecenter (Colombia)", "https://www.homecenter.com.co/homecenter-co/product/103061/angulo-6m-x-1-x-1-8-pg/103061/", OK, "B", False),
 ("Estructura", "Malla de la bandeja", "1,28 m² (1,13 x 1,13 m); abertura menor que el grano (≈ 4,5 mm)",
  "Malla galvanizada 3 x 3 mm, rollo 10 x 0,9 m", 1, 380900, "Homecenter (Colombia)",
  "https://www.homecenter.com.co/homecenter-co/product/662103/malla-ferretera-ligera-3-x-3-mm-toolcraft-10-m-x-09-m/662103/",
  OK + " en abertura; apoyada sobre la parrilla de ángulos para soportar 158 kg", "B", False),
]

SUP = []  # (grupo, concepto, base, valor, escenario)

def tot(rows): return sum(r[4] * r[5] for r in rows)
A = [r for r in R if r[9] == "A"]
B = [r for r in R if r[9] == "B"]
elec = sum(r[4] * r[5] for r in R if r[10])
struct_A = tot([r for r in A if r[0] == "Estructura"])
struct_B = tot(B)
cable = round(0.10 * elec)
cons_A = round(0.10 * struct_A)
cons_B = round(0.10 * struct_B)
taller_A, taller_B = 16 * 30000, 40 * 30000
ing = 60 * 60000
mat_A = tot(A)
capex_A = mat_A + cable + cons_A + taller_A + ing
capex_B = capex_A + tot(B) + cons_B + taller_B

groups = {}
for r in R:
    key = (r[0], r[9])
    groups[key] = groups.get(key, 0) + r[4] * r[5]

if __name__ == "__main__":
    # uso: python generar_cotizaciones_bom.py [ruta_base]  (por defecto, junto a este archivo)
    import os
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "cotizaciones_bom")
    with open(out + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["grupo", "componente", "requisito_diseno", "producto_cotizado", "cantidad",
                    "precio_unitario_cop", "total_cop", "proveedor", "enlace", "verificacion", "escenario"])
        for r in R:
            w.writerow([r[0], r[1], r[2], r[3], r[4], r[5], r[4] * r[5], r[6], r[7], r[8], r[9]])
    print("elec", elec, "cable", cable)
    print("mat_A", mat_A, "struct_A", struct_A, "cons_A", cons_A)
    print("struct_B", struct_B, "cons_B", cons_B)
    print("CAPEX_A", capex_A, "CAPEX_B", capex_B)
    for k, v in groups.items(): print(k, v)

def cop(v): return f"{v:,.0f}".replace(",", " ")

def write_md(path):
    L = []
    a = L.append
    a("# Cotizaciones del BOM — análisis económico (objetivo 4)")
    a("")
    a("Consulta de precios: 19–20 oct 2026. Precios en COP con IVA. Cada ítem tiene el requisito que")
    a("sale del dimensionamiento (`secador_electrico_dimensionamiento.md`, `equipos_energia.md`), el")
    a("producto cotizado, el enlace donde se encontró y la verificación de que sirve para este secador.")
    a("")
    a("- **Importados:** precio sin IVA × tasa × 1,37 (IVA 19 % × 1,15 por envío y arancel; supuesto propio).")
    a("  Tasas: dólar 3 170,46 COP y euro 3 569,90 COP.")
    a("- **Escenario A:** adaptar un secador mecánico existente (control, instrumentación, seguridad,")
    a("  actuación y kit de inversión del aire). **Escenario B:** A + cámara de secado propia de 1,28 m² y 20 cm de lecho,")
    a("  igual a la simulada (reemplaza a la Penagos SC-10 de la versión anterior, que es a gas y de 3 pisos).")
    a("- La tabla completa en formato de datos está en `cotizaciones_bom.csv`.")
    a("")
    order = ["Proceso", "Seguridad", "Instrumentación", "Actuación", "Control", "Tablero", "Estructura"]
    for g in order:
        rows = [r for r in R if r[0] == g]
        a(f"## {g}")
        a("")
        a("| Componente | Requisito del diseño | Producto cotizado | Cant. | Precio unit. | Total | Fuente | Verificación | Esc. |")
        a("|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            a(f"| {r[1]} | {r[2]} | {r[3]} | {r[4]} | {cop(r[5])} | {cop(r[4]*r[5])} | [{r[6]}]({r[7]}) | {r[8]} | {r[9]} |")
        a("")
    a("## Geometría usada para la estructura (estimación propia)")
    a("")
    a("- Cámara de 1,13 × 1,13 m interior (1,28 m²) y 0,95 m de alto: plenum inferior de 0,30 m, lecho de 0,20 m")
    a("  con 0,10 m de borde y plenum superior de 0,35 m. Doble pared de lámina con lana de vidrio de 50 mm.")
    a("- Inversión del aire: el ventilador y la caja de resistencias alimentan una caja con la compuerta, de la que")
    a("  salen dos ductos de 25 × 25 cm, uno a cada plenum; la compuerta la mueve el cilindro de doble efecto.")
    a("- Lámina: cámara ≈ 12,4 m² y ductos con caja de inversión ≈ 7 m², más 15 % de desperdicio = 8 láminas de 2,98 m².")
    a("- Ángulo 1\" × 1/8\": marco (4 verticales y 3 anillos), parrilla de la bandeja y soportes ≈ 33 m = 5 barras de 6 m.")
    a("- La malla de 3 mm retiene el grano (café pergamino ≈ 10 × 7 × 4,5 mm) y descansa sobre la parrilla de ángulos.")
    a("")
    a("## Totales")
    a("")
    a("| Concepto | Base | COP |")
    a("|---|---|---|")
    for g in order:
        v = groups.get((g, "A"), 0)
        if v: a(f"| {g} (A) | Tabla | {cop(v)} |")
    a(f"| Cableado, borneras, canaleta y riel | 10 % de los equipos eléctricos ({cop(elec)}); supuesto | {cop(cable)} |")
    a(f"| Consumibles del kit de inversión | 10 % de su estructura (tornillería, remaches, silicona de alta temperatura, pintura); supuesto | {cop(cons_A)} |")
    a(f"| Fabricación del kit de inversión | 16 h × 30 000 COP/h de taller metalmecánico; supuesto | {cop(taller_A)} |")
    a(f"| Ingeniería, programación y puesta en marcha | 60 h × 60 000 COP/h; supuesto | {cop(ing)} |")
    a(f"| **CAPEX A** | | **{cop(capex_A)}** |")
    a(f"| Estructura de la cámara (B) | Tabla | {cop(struct_B)} |")
    a(f"| Consumibles de la cámara | 10 % de su estructura; supuesto | {cop(cons_B)} |")
    a(f"| Fabricación de la cámara | 40 h × 30 000 COP/h; supuesto | {cop(taller_B)} |")
    a(f"| **CAPEX B** | | **{cop(capex_B)}** |")
    a("")
    a("## Alternativas y notas")
    a("")
    a("- **Controlador:** el S7-1200 es la referencia de cálculo; con un WAGO PFC100 (programable en CODESYS) la CPU sola cuesta ~2,86 M COP.")
    a("- **Confirmar con el proveedor:** pistón magnético del cilindro SAI, driver de la HMI Kinco para el PLC elegido,")
    a("  punto de operación del CBT-80N a 480 m³/h y temperatura máxima de la lana de vidrio.")
    a("- **Gabinete y breakers:** agotados en Homecenter el día de la consulta; se mantienen como precio de referencia.")
    a("- **Compuerta eléctrica:** actuador Belimo LF24 (273,52 USD ≈ " + cop(imp_usd(273.52)) + " COP) en lugar de la compuerta neumática con")
    a("  compresor (≈ 1,55 M COP). https://www.kele.com/product/actuators-and-dampers/spring-return/belimo/lf24")
    a("- **Energía del ventilador:** el modelo usa 0,20 kW nominales; el CBT-80N tiene 0,37 kW, pero con el variador a ~66 %")
    a("  de velocidad consume del orden de 0,1–0,2 kW. El ventilador pesa ~5 % de la energía, así que no cambia los resultados.")
    a("")
    a("## Tarifa de energía")
    a("")
    a("CHEC, septiembre de 2026, nivel 1, propiedad CHEC: 953,6227 COP/kWh (residencial estrato 4 y consumo por encima de")
    a("subsistencia); 1 144,3472 COP/kWh (comercial e industrial, con contribución).")
    a("")
    a("## Fuentes generales")
    a("")
    a("- Central Hidroeléctrica de Caldas (2026). Tarifas septiembre 2026. https://www.chec.com.co/content/dam/chec/documentos/main/transparencia/planeacion-presupuestos-e-informes/publicaciones-de-tarifas/2026/20260901_Tarifas_septiembre_2026.pdf")
    a("- Portafolio (2026a). Euro en Colombia hoy. https://www.portafolio.co/economia/finanzas/euro-en-colombia-hoy-15-de-octubre-cotizacion-sube-y-se-ubica-en-3-569-504526")
    a("- Portafolio (2026b). Precio del dólar hoy en Colombia. https://www.portafolio.co/economia/finanzas/precio-del-dolar-hoy-en-colombia-asi-cotiza-la-divisa-este-16-de-octubre-tras-perder-casi-504569")
    a("- Soler & Palau. Serie CBT-N/CBB-N (ficha técnica). https://statics.solerpalau.com/media/import/documentation/EN_CBT-N.pdf")
    a("- Siemens. SM 1231 AI 4, 6ES7231-4HD32-0XB0 (hoja de datos). https://www.elemon.com.ar/images/productos/hojas-de-datos/siemens/6es7231-4hd32-0xb0.pdf")
    a("- Los enlaces de cada producto están en las tablas.")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")

if __name__ == "__main__":
    write_md(out + ".md")

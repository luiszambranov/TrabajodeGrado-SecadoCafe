"""
cinetica_roa.py
================

Modelo cinetico UNICO del proyecto para el secado de cafe pergamino:
isoterma de equilibrio de Roa (Trejos et al., 1989) + ecuacion unificada de
secado en capa delgada de Roa (Parra-Coronado et al., 2008 - SECAFE).
Trabajo de grado - Sistema de supervision digital para el secado de cafe.

Por que este modelo (decision del 29 sept 2026)
-------------------------------------------------
El informe de prioridades del asesor (25 sept 2026) pide cerrar el dominio
T-HR del modelo antes del Monte Carlo. Phitakwinai et al. (2019), usado en
cinetica_dinamica.py, solo es valido en 50-70 C / 10-30 % HR, mientras las
tres estrategias recorren aprox. 15-65 C / 5-100 % HR (ambiente de
Chinchina, secado en patio, solar activo, calentamiento y enfriamiento de
la propuesta supervisada). El modelo de Roa-Cenicafe:

    - fue obtenido para cafe pergamino colombiano (var. Caturra, Cenicafe,
      Chinchina), el mismo caso de estudio del proyecto;
    - cubre T 10-70 C (capa delgada) y HR 5-100 % (isoterma, medida a
      5-55 C);
    - hace depender el secado de la HR de forma fisica, por dos vias: la
      humedad de equilibrio Me(T,HR) y el deficit de presion de vapor del
      aire (Pvs - Pv).

Permite usar EL MISMO modelo en las tres estrategias (sol/patio, solar
activo, propuesta supervisada con resistencia electrica), de modo que la
comparacion Monte Carlo refleje la estrategia y no diferencias entre
modelos de fuentes distintas. Phitakwinai et al. (2019) queda como
validacion independiente en 50-70 C (ver verificacion en
data/reference/roa_cenicafe_isoterma_capa_delgada.md).

Ecuaciones
-----------
1) Humedad de equilibrio (Roa; Trejos et al., 1989, ec. 2 y Tabla 3):

       Me = (p1*phi + p2*phi^2 + p3*phi^3) * exp[(q1*phi + q2*phi^2 + q3*phi^3) * T]

   Me en % base seca, phi = HR decimal, T en C. q1 = -0.037049 (valor
   ORIGINAL; SECAFE 2008 transcribe -0.03049 por error, ver .md).

2) Capa delgada unificada de Roa (SECAFE 2008, ec. 15):

       dM/dt = -m*q*(M - Me)*(Pvs - Pv)^n * t^(q-1)
       m = 0.0143, n = 0.87898, q = 1.06439

   M, Me en % b.s.; Pvs, Pv en kPa; t en h. A condiciones constantes se
   integra como un modelo de Page:

       MR = (M - Me)/(M0 - Me) = exp(-k*t^q),   k = m*(Pvs - Pv)^n

   Interpretacion adoptada: (Pvs - Pv) = deficit de presion de vapor del
   aire de secado (Pvs a la temperatura del aire, Pv presion parcial del
   vapor en el aire).

3) Calor latente de vaporizacion (Trejos et al., 1989, ec. 6):

       L = (2502.4 - 2.4295*T) * [1 + 1.44408*exp(-21.6011*M)]   [kJ/kg]

   T en C, M decimal b.s. Se incluye para el balance de energia de la
   camara / estimacion de energia (no lo usa el paso cinetico).

Integracion bajo condiciones variables (tiempo equivalente, Thompson)
-----------------------------------------------------------------------
Mismo criterio cuasi-estacionario que cinetica_dinamica.py y que el modelo
de Thompson usado en SECAFE: en cada paso, con las condiciones ACTUALES
(T, HR) se calculan Me y k, se busca el tiempo equivalente

       tau = [-ln(MR) / k]^(1/q),   MR = (M - Me)/(M0 - Me)

y se avanza el paso de forma EXACTA para la ecuacion lineal en (M - Me):

       M_nuevo - Me = (M - Me) * exp(-k * [(tau + dt)^q - tau^q])

Con condiciones constantes esto reproduce exactamente la curva analitica
MR = exp(-k*t^q) (chequeo de consistencia dinamico vs estatico que pide
el asesor; ver el smoke test al final del modulo).

Rehumectacion (M < Me): ocurre en patio o con el calentador apagado en
noches humedas (Me de hasta ~19 % b.h. a 20 C / 97 % HR). La isoterma de
Roa es de DESORCION; la histeresis de adsorcion no esta modelada. En ese
caso se usa la misma ecuacion lineal con tau^(q-1) = 1 (es decir, tasa
q*k*(M - Me)), aproximacion que se declara como limitacion. Como en
noches humedas (Pvs - Pv) es pequeno, la rehumectacion resulta lenta.

Convencion de unidades
-----------------------
    Internamente: M, Me en % base SECA (como las fuentes).
    Interfaz: funciones de conversion a/desde % base humeda, que es la
    convencion de reporte del proyecto (modelo_secado.py).
    T en C, HR en % (0-100), t en h.

Referencias
------------
Trejos-Rodriguez, R., Roa-Mejia, G., & Oliveros-Tascon, C. E. (1989).
    Humedad de equilibrio y calor latente de vaporizacion del cafe
    pergamino y del cafe verde. Cenicafe, 40(1), 5-15.
    https://biblioteca.cenicafe.org/handle/10778/841
Parra-Coronado, A., Roa-Mejia, G., & Oliveros-Tascon, C. E. (2008).
    SECAFE Parte I: modelamiento y simulacion matematica en el secado
    mecanico de cafe pergamino. Revista Brasileira de Engenharia Agricola
    e Ambiental, 12(4), 415-427.
    https://www.scielo.br/j/rbeaa/a/TZ7Sqw8RqZKny4fZh6dHW6j/?lang=es
Allen, R. G., et al. (1998). FAO Irrigation and Drainage Paper 56, ec. 11
    (presion de saturacion, reutilizada de generador_ambiente.es_kpa).
Ver data/reference/roa_cenicafe_isoterma_capa_delgada.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from generador_ambiente import es_kpa

# ---------------------------------------------------------------------------
# Coeficientes (fuentes en el docstring del modulo)
# ---------------------------------------------------------------------------

# Isoterma de Roa, cafe pergamino (Trejos et al., 1989, Tabla 3)
P1, P2, P3 = 61.030848, -108.371410, 74.46105
Q1, Q2, Q3 = -0.037049, 0.070114, -0.035177  # q0 = q4 = 0

# Capa delgada unificada de Roa (SECAFE 2008, ec. 15)
M_ROA = 0.0143
N_ROA = 0.87898
Q_ROA = 1.06439

# Rangos de validez reportados por las fuentes
T_MIN_ISOTERMA_C, T_MAX_ISOTERMA_C = 5.0, 55.0     # Trejos et al. (1989)
RH_MIN_ISOTERMA_PCT, RH_MAX_ISOTERMA_PCT = 5.0, 100.0
T_MIN_CAPA_C, T_MAX_CAPA_C = 10.0, 70.0            # SECAFE (2008)

# Condiciones del caso de estudio
M0_BH_PCT = 55.0
"""Humedad inicial del cafe pergamino lavado [% b.h.]. SECAFE (2008) reporta
52-56 % b.h. al salir del beneficio en Colombia; Phitakwinai et al. (2019)
usan M0 = 122 % b.s. (= 54.95 % b.h.). Se fija 55 % b.h."""

HUMEDAD_OBJETIVO_BH_PCT = 11.0
"""Humedad final objetivo [% b.h.], centro del rango 10-12 % b.h. de
almacenamiento seguro (SECAFE, 2008, introduccion). Es un CRITERIO DE
PARADA, no la humedad de equilibrio (Me depende de T y HR)."""


# ---------------------------------------------------------------------------
# Conversiones de base de humedad
# ---------------------------------------------------------------------------

def bh_a_bs(m_bh_pct: float) -> float:
    """% base humeda -> % base seca."""
    return 100.0 * m_bh_pct / (100.0 - m_bh_pct)


def bs_a_bh(m_bs_pct: float) -> float:
    """% base seca -> % base humeda."""
    return 100.0 * m_bs_pct / (100.0 + m_bs_pct)


# ---------------------------------------------------------------------------
# Propiedades
# ---------------------------------------------------------------------------

def humedad_equilibrio_bs(t_c: float, rh_pct: float) -> float:
    """Me [% b.s.] del cafe pergamino (isoterma de Roa, Trejos et al. 1989).

    Fuera de 5-55 C es extrapolacion (ver ``fuera_de_rango`` en
    :func:`paso_humedad`)."""
    phi = float(np.clip(rh_pct, 0.0, 100.0)) / 100.0
    poli = P1 * phi + P2 * phi**2 + P3 * phi**3
    expo = (Q1 * phi + Q2 * phi**2 + Q3 * phi**3) * t_c
    return poli * math.exp(expo)


def deficit_presion_vapor_kpa(t_c: float, rh_pct: float) -> float:
    """(Pvs - Pv) [kPa] del aire: Pvs a la temperatura del aire, Pv = HR*Pvs."""
    pvs = float(es_kpa(t_c))
    return pvs * (1.0 - float(np.clip(rh_pct, 0.0, 100.0)) / 100.0)


def constante_secado(t_c: float, rh_pct: float) -> float:
    """k = m*(Pvs - Pv)^n  [1/h^q] de la forma integrada tipo Page."""
    return M_ROA * deficit_presion_vapor_kpa(t_c, rh_pct) ** N_ROA


def calor_latente_kj_kg(t_c: float, m_bs_pct: float) -> float:
    """Calor latente de vaporizacion del agua en cafe pergamino [kJ/kg]
    (Trejos et al., 1989, ec. 6). ``m_bs_pct`` en % b.s."""
    m_dec = m_bs_pct / 100.0
    return (2502.4 - 2.4295 * t_c) * (1.0 + 1.44408 * math.exp(-21.6011 * m_dec))


# ---------------------------------------------------------------------------
# Paso dinamico
# ---------------------------------------------------------------------------

@dataclass
class ResultadoPasoRoa:
    m_bs_pct: float          # humedad nueva [% b.s.]
    me_bs_pct: float         # humedad de equilibrio en las condiciones del paso [% b.s.]
    k: float                 # constante de secado del paso [1/h^q]
    tau_h: float             # tiempo equivalente al inicio del paso [h]
    rehumectacion: bool      # True si M < Me (adsorcion, ver docstring)
    fuera_de_rango: bool     # True si T/HR fuera del rango de las fuentes

    @property
    def m_bh_pct(self) -> float:
        return bs_a_bh(self.m_bs_pct)


def fuera_de_rango(t_c: float, rh_pct: float) -> bool:
    """True si (T, HR) sale del rango respaldado: capa delgada 10-70 C,
    isoterma 5-55 C y 5-100 % HR. Entre 55 y 70 C la isoterma se usa
    extrapolada (5-15 C), lo que se marca aqui para poder cuantificar en
    la campana cuanto tiempo de proceso ocurre en esa zona."""
    return not (
        max(T_MIN_CAPA_C, T_MIN_ISOTERMA_C) <= t_c <= min(T_MAX_CAPA_C, T_MAX_ISOTERMA_C)
        and RH_MIN_ISOTERMA_PCT <= rh_pct <= RH_MAX_ISOTERMA_PCT
    )


def paso_humedad(
    m_bs_pct: float,
    t_c: float,
    rh_pct: float,
    dt_h: float,
    m0_bs_pct: float | None = None,
) -> ResultadoPasoRoa:
    """Avanza la humedad del cafe ``dt_h`` horas con las condiciones del aire
    ACTUALES (T, HR), por tiempo equivalente (ver docstring del modulo).

    Parametros
    ----------
    m_bs_pct : humedad actual [% b.s.]
    t_c, rh_pct : temperatura [C] y humedad relativa [%] del aire que
        recibe el cafe (T_process/RH_process en la propuesta supervisada;
        ambiente o camara solar en las lineas base).
    dt_h : paso [h]
    m0_bs_pct : humedad inicial de referencia [% b.s.] para el tiempo
        equivalente; por defecto M0_BH_PCT convertido.
    """
    m0 = bh_a_bs(M0_BH_PCT) if m0_bs_pct is None else m0_bs_pct
    me = humedad_equilibrio_bs(t_c, rh_pct)
    k = constante_secado(t_c, rh_pct)
    oor = fuera_de_rango(t_c, rh_pct)

    if k <= 0.0 or dt_h <= 0.0:
        return ResultadoPasoRoa(m_bs_pct, me, k, 0.0, m_bs_pct < me, oor)

    if m_bs_pct >= me:
        # Desorcion (secado): tiempo equivalente sobre la curva de estas condiciones.
        mr = (m_bs_pct - me) / (m0 - me) if m0 > me else 0.0
        mr = min(max(mr, 1e-12), 1.0)
        tau = (-math.log(mr) / k) ** (1.0 / Q_ROA)
        factor = math.exp(-k * ((tau + dt_h) ** Q_ROA - tau**Q_ROA))
        rehum = False
    else:
        # Adsorcion (rehumectacion): aproximacion con tau^(q-1) = 1.
        tau = 0.0
        factor = math.exp(-Q_ROA * k * dt_h)
        rehum = True

    m_nuevo = me + (m_bs_pct - me) * factor
    return ResultadoPasoRoa(m_nuevo, me, k, tau, rehum, oor)


def mr_analitico(t_h: np.ndarray, t_c: float, rh_pct: float) -> np.ndarray:
    """MR(t) = exp(-k*t^q) a condiciones constantes (forma integrada)."""
    t_h = np.asarray(t_h, dtype=float)
    return np.exp(-constante_secado(t_c, rh_pct) * t_h**Q_ROA)


def tiempo_hasta_humedad(
    m_obj_bh_pct: float, t_c: float, rh_pct: float, m0_bh_pct: float = M0_BH_PCT
) -> float:
    """Tiempo [h] para llegar a ``m_obj_bh_pct`` a condiciones constantes.
    Devuelve ``inf`` si la humedad objetivo es <= Me (no alcanzable)."""
    me = humedad_equilibrio_bs(t_c, rh_pct)
    m0, mo = bh_a_bs(m0_bh_pct), bh_a_bs(m_obj_bh_pct)
    if mo <= me:
        return math.inf
    mr = (mo - me) / (m0 - me)
    return (-math.log(mr) / constante_secado(t_c, rh_pct)) ** (1.0 / Q_ROA)


@dataclass
class ResultadoSimulacion:
    """Trayectoria de una corrida de secado con el modelo de Roa."""

    t_h: np.ndarray               # tiempo [h]
    m_bh_pct: np.ndarray          # humedad del cafe [% b.h.]
    t_c: np.ndarray               # temperatura del aire que recibe el cafe [C]
    rh_pct: np.ndarray            # HR del aire que recibe el cafe [%]
    t_objetivo_h: float           # tiempo hasta HUMEDAD_OBJETIVO (inf si no se alcanza)
    horas_fuera_de_rango: float   # horas simuladas fuera del rango de las fuentes
    horas_rehumectacion: float    # horas con M < Me (adsorcion)


def simular(
    condiciones,
    dt_h: float = 0.25,
    t_max_h: float = 400.0,
    m0_bh_pct: float = M0_BH_PCT,
    m_obj_bh_pct: float = HUMEDAD_OBJETIVO_BH_PCT,
    detener_en_objetivo: bool = True,
) -> ResultadoSimulacion:
    """Simula el secado bajo condiciones variables en el tiempo.

    ``condiciones(t_h) -> (T_c, RH_pct)`` devuelve las condiciones del
    aire que recibe el cafe en el instante t_h; cada estrategia define la
    suya (ver escenario_sol_abierto.py, linea_base_activa.py). La planta
    supervisada NO usa esta funcion: avanza paso a paso con
    :func:`paso_humedad` dentro de ModeloSecadoPlant (planta_secado.py),
    porque sus condiciones dependen de los comandos de CODESYS.
    """
    m0 = bh_a_bs(m0_bh_pct)
    m = m0
    ts, ms, Ts, RHs = [0.0], [m0_bh_pct], [], []
    fuera = rehum = 0.0
    t_obj = math.inf
    t = 0.0
    while t < t_max_h - 1e-9:
        T, RH = condiciones(t)
        r = paso_humedad(m, T, RH, dt_h, m0_bs_pct=m0)
        m = r.m_bs_pct
        fuera += dt_h if r.fuera_de_rango else 0.0
        rehum += dt_h if r.rehumectacion else 0.0
        t += dt_h
        Ts.append(T)
        RHs.append(RH)
        ts.append(t)
        ms.append(bs_a_bh(m))
        if math.isinf(t_obj) and ms[-1] <= m_obj_bh_pct:
            # interpolacion lineal dentro del paso
            m_prev = ms[-2]
            t_obj = t - dt_h + dt_h * (m_prev - m_obj_bh_pct) / (m_prev - ms[-1])
            if detener_en_objetivo:
                break
    Ts.append(Ts[-1] if Ts else float("nan"))
    RHs.append(RHs[-1] if RHs else float("nan"))
    return ResultadoSimulacion(
        np.array(ts), np.array(ms), np.array(Ts), np.array(RHs), t_obj, fuera, rehum
    )


if __name__ == "__main__":
    # 1) Isoterma contra datos de Trejos et al. (1989), Tabla 1 (algunos puntos)
    print("Isoterma de Roa vs Trejos (1989), Tabla 1:")
    for t, rh, m_exp in [(10, 52.0, 11.6), (25, 72.5, 14.6), (40, 42.5, 9.4), (55, 88.0, 18.0)]:
        print(f"  T={t:2d} C HR={rh:5.1f} %  Me={humedad_equilibrio_bs(t, rh):5.2f} % b.s.  (exp {m_exp})")

    # 2) Consistencia dinamico vs analitico a condiciones constantes
    T_FIJA, RH_FIJA, DT = 60.0, 20.0, 0.25
    m0 = bh_a_bs(M0_BH_PCT)
    me = humedad_equilibrio_bs(T_FIJA, RH_FIJA)
    m = m0
    err_max = 0.0
    for i in range(1, 81):
        m = paso_humedad(m, T_FIJA, RH_FIJA, DT).m_bs_pct
        m_an = me + (m0 - me) * float(mr_analitico(np.array([i * DT]), T_FIJA, RH_FIJA)[0])
        err_max = max(err_max, abs(m - m_an))
    print(f"\nDinamico vs analitico (T={T_FIJA} C, HR={RH_FIJA} %, 20 h): error max = {err_max:.2e} % b.s.")

    # 3) Tiempos a humedad objetivo en condiciones tipicas de cada estrategia
    print(f"\nTiempo hasta {HUMEDAD_OBJETIVO_BH_PCT} % b.h. desde {M0_BH_PCT} % b.h. (condiciones constantes):")
    for nombre, t, rh in [
        ("Supervisada 60 C / 9 %", 60.0, 9.0),
        ("Solar activo 40 C / 25 %", 40.0, 25.0),
        ("Patio 26.3 C / 63.3 %", 26.3, 63.3),
        ("Noche 20 C / 90 %", 20.0, 90.0),
    ]:
        me_bh = bs_a_bh(humedad_equilibrio_bs(t, rh))
        tt = tiempo_hasta_humedad(HUMEDAD_OBJETIVO_BH_PCT, t, rh)
        print(f"  {nombre:26s} Me={me_bh:5.2f} % b.h.  t={tt:7.1f} h  fuera_de_rango={fuera_de_rango(t, rh)}")

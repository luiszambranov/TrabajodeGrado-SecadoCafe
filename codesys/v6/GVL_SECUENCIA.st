// GVL_SECUENCIA v6 (19 oct 2026) — Variables compartidas entre FluidSIM (OPC), la HMI,
// el programa SECUENCIA y PLC_PRG.
// Todas deben estar marcadas en "Symbol configuration" para que el
// servidor OPC de CODESYS las publique a FluidSIM.
//
// Cambios v6:
//   - sin_fluidsim: TRUE = el PLC simula pulsadores de campo y cilindros (pruebas sin FluidSIM).
//   - lote_preparado arranca en TRUE: el server recién iniciado ya es un lote nuevo,
//     así que START funciona sin pulsar antes "Nuevo lote".
//
// Intercambio con FluidSIM por OPC: un BYTE por módulo de 8 bits.
//   INPUT0  <- bloque "FluidSIM Out" (pulsadores, finales de carrera) -> se lee INPUT0.n
//   OUTPUT0 -> bloque "FluidSIM In"  (bobinas, relé, lámparas)        -> se escribe OUTPUT0.n
// En SECUENCIA se copian bit a bit a las variables I_ / Q_ con nombre.
VAR_GLOBAL
    // ===== Modo de prueba (v6) =====
    sin_fluidsim    : BOOL := TRUE;   // TRUE = sin FluidSIM (el PLC simula); FALSE = todo viene de FluidSIM

    // ===== Módulo 0 de FluidSIM (OPC) =====
    INPUT0          : BYTE;   // desde FluidSIM Out (módulo 1, puerto 1)
    OUTPUT0         : BYTE;   // hacia FluidSIM In  (módulo 1, puerto 1)

    // ===== Entradas con nombre (copia de INPUT0.n, o simuladas si sin_fluidsim) =====
    I_EMERGENCIA_NC : BOOL;   // INPUT0.0  Paro de emergencia, contacto NC (TRUE = normal, FALSE = pulsado)
    I_START         : BOOL;   // INPUT0.1  Pulsador START, NA
    I_STOP_NC       : BOOL;   // INPUT0.2  Pulsador STOP, contacto NC (TRUE = normal, FALSE = pulsado)
    I_1B1           : BOOL;   // INPUT0.3  Cilindro 1 (compuerta) atrás   -> aire normal (abajo -> arriba)
    I_1B2           : BOOL;   // INPUT0.4  Cilindro 1 (compuerta) adelante -> aire invertido
    I_2B1           : BOOL;   // INPUT0.5  Cilindro 2 (bandeja) atrás   -> bandeja afuera
    I_2B2           : BOOL;   // INPUT0.6  Cilindro 2 (bandeja) adelante -> bandeja adentro

    // ===== Salidas con nombre (se copian a OUTPUT0.n) =====
    Q_1S1           : BOOL;   // OUTPUT0.0 Bobina: cilindro 1 sale (compuerta -> invertida)
    Q_2S1           : BOOL;   // OUTPUT0.1 Bobina: cilindro 1 entra (compuerta -> normal)
    Q_1S2           : BOOL;   // OUTPUT0.2 Bobina: cilindro 2 sale (bandeja entra al secador)
    Q_2S2           : BOOL;   // OUTPUT0.3 Bobina: cilindro 2 entra (bandeja sale del secador)
    Q_K1            : BOOL;   // OUTPUT0.4 Relé K1: ventilador ON/OFF
    Q_H1_VERDE      : BOOL;   // OUTPUT0.5 Ciclo en marcha (fija) / fin de secado (intermitente)
    Q_H2_AMARILLA   : BOOL;   // OUTPUT0.6 Reposo o paro
    Q_H3_ROJA       : BOOL;   // OUTPUT0.7 Emergencia (fija) / falla (intermitente)

    // ===== HMI (botones con "Pulsar", NO "Alternar") =====
    hmi_start       : BOOL;
    hmi_stop        : BOOL;
    hmi_nuevo_lote  : BOOL;   // botón "Nuevo lote"

    // ===== Estado (para la HMI) =====
    estado          : E_ESTADO := E_ESTADO.REPOSO;
    estado_txt      : STRING(30) := 'REPOSO';
    falla_codigo    : INT;    // 0 = sin falla, 1 = comunicación Python, 2 = compuerta trabada,
                              // 3 = bandeja trabada, 4 = finales de carrera incoherentes
    falla_txt       : STRING(40);

    // ===== Interfaz SECUENCIA -> PLC_PRG (las escribe SOLO SECUENCIA) =====
    ventilador      : BOOL;   // pide ventilador encendido
    calentar        : BOOL;   // permiso de resistencias (PLC_PRG aplica el lazo térmico)
    planta_run      : BOOL;   // TRUE -> plant_mode = 0 (RUN); FALSE -> 1 (HOLD)
    aire_invertido  : BOOL;   // sentido del aire = posición REAL de la compuerta (1B2)
    nuevo_lote      : BOOL;   // pulso de un ciclo al pulsar "Nuevo lote" (PLC_PRG reinicia Python)
    lote_preparado  : BOOL := TRUE;   // v6: TRUE al arrancar; START solo arranca si está en TRUE
END_VAR

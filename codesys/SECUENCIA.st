// =====================================================================
// SECUENCIA — Máquina de estados del secador de café (CASE OF)
// Proyecto: Supervisión IoT del secado de café (CODESYS V3.5 SP9)
// Versión: 14 oct 2026 (botón Nuevo lote + auxiliares HMI)
//
// Llamar en la MainTask DESPUÉS de PLC_PRG:
//   MainTask: 1) PLC_PRG   (lee Python por Modbus, watchdog, fin_secado)
//             2) SECUENCIA (decide estado, cilindros, ventilador, semáforo)
//
// Dueño de variables: SECUENCIA escribe solo en GVL_SECUENCIA.
// De PLC_PRG solo LEE: comm_error, safety_ok, fin_secado, tiempo_secado_h.
//
// Fuentes:
// - Inversión del aire cada 6 h: Parra-Coronado et al. (2008), SECAFÉ, Cenicafé.
// - Colores del semáforo (verde normal, amarillo atención, rojo emergencia):
//   IEC 60204-1, apartado de colores de indicadores luminosos.
// =====================================================================
PROGRAM SECUENCIA
VAR
    // --- Mandos ---
    rt_start         : R_TRIG;
    rt_nuevo         : R_TRIG;   // flanco del botón "Nuevo lote"
    start_pulso      : BOOL;   // flanco de START (FluidSIM O HMI)
    stop_activo      : BOOL;   // STOP pulsado (FluidSIM O HMI)
    emergencia       : BOOL;   // emergencia pulsada (solo FluidSIM)

    // --- Diagnóstico ---
    falla_comm       : BOOL;
    falla_fc         : BOOL;   // los dos finales de carrera de un cilindro activos a la vez
    en_ciclo         : BOOL;   // estados donde una falla debe detener el proceso

    // --- Tiempos de lote (horas de MODELO, vienen de Python) ---
    t0_lote_h        : REAL;   // tiempo de modelo al iniciar el secado del lote
    t_lote_h         : REAL;   // horas de secado del lote actual
    t_fin_h          : REAL;   // tiempo de modelo al entrar en ENFRIAMIENTO

    // --- Compuerta de inversión ---
    sentido_pedido      : BOOL;  // TRUE = el reloj de 6 h pide aire invertido
    compuerta_invertida : BOOL;  // posición real: 1B2 activo y 1B1 inactivo
    compuerta_normal    : BOOL;  // posición real: 1B1 activo y 1B2 inactivo

    // --- Órdenes de movimiento (se calculan a partir del estado) ---
    mov_compuerta_inv   : BOOL;
    mov_compuerta_norm  : BOOL;
    mov_bandeja_adentro : BOOL;
    mov_bandeja_afuera  : BOOL;

    // --- Temporizadores (se llaman SIEMPRE, fuera del CASE) ---
    tmr_mov          : TON;    // vigila que el cilindro llegue al final de carrera
    tmr_blink        : TON;    // base de la intermitencia
    parpadeo         : BOOL;

    estado_previo    : E_ESTADO := E_ESTADO.REPOSO;  // para volver después de PARO

    // --- Auxiliares de la HMI (animaciones y textos) ---
    tmr_anim         : TON;
    angulo_vent      : REAL;          // rotor del ventilador
    angulo_compuerta : REAL;          // hoja de la compuerta 0 / 90
    x_bandeja        : INT;           // desplazamiento de la bandeja
    txt_comm         : STRING(10);
    txt_aire         : STRING(30);
    txt_bandeja      : STRING(15);
    txt_vent         : STRING(12);
    txt_resist       : STRING(12);
    txt_alarma       : STRING(50);
    lim_objetivo     : REAL := 11.0;  // línea de referencia en la tendencia
    lim_capa         : REAL := 12.0;  // línea de referencia en la tendencia
END_VAR
VAR CONSTANT
    T_MOV_MAX                 : TIME := T#5S;   // tiempo máximo de carrera de un cilindro (real)
    T_ENFRIAMIENTO_H          : REAL := 0.5;    // h de modelo con ventilador sin resistencia (supuesto propio)
    PERIODO_INVERSION_H       : DINT := 6;      // SECAFÉ (2008)
    PAUSA_RESIST_EN_INVERSION : BOOL := FALSE;  // FALSE en la demo acelerada (factor 540);
                                                // TRUE solo en la verificación a tiempo real
END_VAR

// =====================================================================
// 0. LECTURA DE FLUIDSIM (INPUT0 <- bloque "FluidSIM Out")
// =====================================================================
GVL_SECUENCIA.I_EMERGENCIA_NC := GVL_SECUENCIA.INPUT0.0;   // EMERGENCY (NC)
GVL_SECUENCIA.I_START         := GVL_SECUENCIA.INPUT0.1;   // START (NA)
GVL_SECUENCIA.I_STOP_NC       := GVL_SECUENCIA.INPUT0.2;   // STOP (NC)
GVL_SECUENCIA.I_1B1           := GVL_SECUENCIA.INPUT0.3;   // compuerta atrás
GVL_SECUENCIA.I_1B2           := GVL_SECUENCIA.INPUT0.4;   // compuerta adelante
GVL_SECUENCIA.I_2B1           := GVL_SECUENCIA.INPUT0.5;   // bandeja afuera
GVL_SECUENCIA.I_2B2           := GVL_SECUENCIA.INPUT0.6;   // bandeja adentro
// INPUT0.7 libre

// =====================================================================
// 1. ENTRADAS Y MANDOS
// =====================================================================
GVL_SECUENCIA.nuevo_lote := FALSE;   // pulso de un solo ciclo

rt_start(CLK := GVL_SECUENCIA.I_START OR GVL_SECUENCIA.hmi_start);
start_pulso := rt_start.Q;
rt_nuevo(CLK := GVL_SECUENCIA.hmi_nuevo_lote);

// STOP y EMERGENCIA son NC: el contacto abierto (FALSE) significa pulsado.
// Si el cable se corta o FluidSIM no está conectado, el PLC lo ve como pulsado (falla segura).
stop_activo := (NOT GVL_SECUENCIA.I_STOP_NC) OR GVL_SECUENCIA.hmi_stop;
emergencia  := NOT GVL_SECUENCIA.I_EMERGENCIA_NC;

// Posición real de la compuerta
compuerta_invertida := GVL_SECUENCIA.I_1B2 AND NOT GVL_SECUENCIA.I_1B1;
compuerta_normal    := GVL_SECUENCIA.I_1B1 AND NOT GVL_SECUENCIA.I_1B2;

// Reloj de inversión: cada 6 h de lote cambia el sentido pedido
t_lote_h := PLC_PRG.tiempo_secado_h - t0_lote_h;
IF t_lote_h < 0.0 THEN
    t_lote_h := 0.0;
END_IF
sentido_pedido := ((TRUNC(t_lote_h) / PERIODO_INVERSION_H) MOD 2) = 1;

// =====================================================================
// 2. DIAGNÓSTICO (usa las órdenes de movimiento del ciclo anterior)
// =====================================================================
falla_comm := PLC_PRG.comm_error OR (PLC_PRG.safety_ok = 0);
falla_fc   := (GVL_SECUENCIA.I_1B1 AND GVL_SECUENCIA.I_1B2)
           OR (GVL_SECUENCIA.I_2B1 AND GVL_SECUENCIA.I_2B2);

en_ciclo := (GVL_SECUENCIA.estado = E_ESTADO.CARGA)
         OR (GVL_SECUENCIA.estado = E_ESTADO.SECADO)
         OR (GVL_SECUENCIA.estado = E_ESTADO.INVERSION)
         OR (GVL_SECUENCIA.estado = E_ESTADO.ENFRIAMIENTO)
         OR (GVL_SECUENCIA.estado = E_ESTADO.FIN_SECADO)
         OR (GVL_SECUENCIA.estado = E_ESTADO.DESCARGA)
         OR (GVL_SECUENCIA.estado = E_ESTADO.PARO);

// =====================================================================
// 3. PRIORIDADES: EMERGENCIA > FALLA > PARO (antes del CASE)
// =====================================================================
IF emergencia THEN
    GVL_SECUENCIA.estado := E_ESTADO.EMERGENCIA;

ELSIF en_ciclo AND (falla_comm OR falla_fc OR tmr_mov.Q) THEN
    IF falla_comm THEN
        GVL_SECUENCIA.falla_codigo := 1;
    ELSIF tmr_mov.Q AND (mov_compuerta_inv OR mov_compuerta_norm) THEN
        GVL_SECUENCIA.falla_codigo := 2;
    ELSIF tmr_mov.Q THEN
        GVL_SECUENCIA.falla_codigo := 3;
    ELSE
        GVL_SECUENCIA.falla_codigo := 4;
    END_IF
    GVL_SECUENCIA.estado := E_ESTADO.FALLA;

ELSIF stop_activo AND (
         (GVL_SECUENCIA.estado = E_ESTADO.CARGA)
      OR (GVL_SECUENCIA.estado = E_ESTADO.SECADO)
      OR (GVL_SECUENCIA.estado = E_ESTADO.INVERSION)
      OR (GVL_SECUENCIA.estado = E_ESTADO.ENFRIAMIENTO)
      OR (GVL_SECUENCIA.estado = E_ESTADO.DESCARGA)) THEN
    estado_previo := GVL_SECUENCIA.estado;
    GVL_SECUENCIA.estado := E_ESTADO.PARO;
END_IF

// =====================================================================
// 4. MÁQUINA DE ESTADOS: aquí solo se deciden las TRANSICIONES
// =====================================================================
CASE GVL_SECUENCIA.estado OF

E_ESTADO.REPOSO:
    // Amarilla fija.
    // 1) "Nuevo lote": reinicia la planta en Python (humedad 55 %, tiempo y energía a 0).
    IF rt_nuevo.Q THEN
        GVL_SECUENCIA.nuevo_lote := TRUE;      // PLC_PRG manda el pulso al registro 21
        GVL_SECUENCIA.lote_preparado := TRUE;
        GVL_SECUENCIA.falla_codigo := 0;
    // 2) START: arranca el ciclo solo si hay un lote preparado y todo está sano.
    ELSIF start_pulso AND GVL_SECUENCIA.lote_preparado
          AND NOT stop_activo AND NOT falla_comm AND NOT falla_fc THEN
        GVL_SECUENCIA.estado := E_ESTADO.CARGA;
    END_IF

E_ESTADO.CARGA:
    // Bandeja adentro (2B2) y compuerta en posición normal (1B1)
    IF GVL_SECUENCIA.I_2B2 AND NOT GVL_SECUENCIA.I_2B1 AND compuerta_normal THEN
        t0_lote_h := PLC_PRG.tiempo_secado_h;  // el reloj de inversión empieza en 0
        GVL_SECUENCIA.estado := E_ESTADO.SECADO;
    END_IF

E_ESTADO.SECADO:
    IF PLC_PRG.fin_secado THEN
        t_fin_h := PLC_PRG.tiempo_secado_h;
        GVL_SECUENCIA.estado := E_ESTADO.ENFRIAMIENTO;
    ELSIF sentido_pedido <> compuerta_invertida THEN
        GVL_SECUENCIA.estado := E_ESTADO.INVERSION;
    END_IF

E_ESTADO.INVERSION:
    // Vuelve a SECADO cuando la compuerta llega a la posición pedida
    IF (sentido_pedido AND compuerta_invertida)
       OR (NOT sentido_pedido AND compuerta_normal) THEN
        GVL_SECUENCIA.estado := E_ESTADO.SECADO;
    END_IF

E_ESTADO.ENFRIAMIENTO:
    IF (PLC_PRG.tiempo_secado_h - t_fin_h) >= T_ENFRIAMIENTO_H THEN
        GVL_SECUENCIA.estado := E_ESTADO.FIN_SECADO;
    END_IF

E_ESTADO.FIN_SECADO:
    // Verde intermitente. START = autorizar la descarga.
    IF start_pulso AND NOT stop_activo THEN
        GVL_SECUENCIA.estado := E_ESTADO.DESCARGA;
    END_IF

E_ESTADO.DESCARGA:
    IF GVL_SECUENCIA.I_2B1 AND NOT GVL_SECUENCIA.I_2B2 THEN
        GVL_SECUENCIA.lote_preparado := FALSE;  // el lote ya salió: hay que pulsar "Nuevo lote"
        GVL_SECUENCIA.estado := E_ESTADO.REPOSO;
    END_IF

E_ESTADO.PARO:
    // Amarilla fija. START (con STOP ya suelto) continúa donde iba.
    IF start_pulso AND NOT stop_activo THEN
        GVL_SECUENCIA.estado := estado_previo;
    END_IF

E_ESTADO.FALLA:
    // Roja intermitente. START reconoce la falla si la causa ya desapareció.
    IF start_pulso AND NOT falla_comm AND NOT falla_fc THEN
        GVL_SECUENCIA.falla_codigo := 0;
        GVL_SECUENCIA.estado := E_ESTADO.REPOSO;
    END_IF

E_ESTADO.EMERGENCIA:
    // Roja fija. Hay que desenclavar el pulsador y luego pulsar START.
    // Vuelve a REPOSO (nunca reanuda solo).
    IF NOT emergencia AND start_pulso THEN
        GVL_SECUENCIA.estado := E_ESTADO.REPOSO;
    END_IF

END_CASE

// =====================================================================
// 5. SALIDAS: se calculan a partir del estado (nada queda "pegado")
// =====================================================================
// --- Interfaz con PLC_PRG / Python ---
GVL_SECUENCIA.ventilador := (GVL_SECUENCIA.estado = E_ESTADO.SECADO)
                         OR (GVL_SECUENCIA.estado = E_ESTADO.INVERSION)
                         OR (GVL_SECUENCIA.estado = E_ESTADO.ENFRIAMIENTO);

GVL_SECUENCIA.calentar := (GVL_SECUENCIA.estado = E_ESTADO.SECADO)
                       OR ((GVL_SECUENCIA.estado = E_ESTADO.INVERSION) AND NOT PAUSA_RESIST_EN_INVERSION);

GVL_SECUENCIA.planta_run := GVL_SECUENCIA.ventilador;

// El sentido del aire que recibe Python sale del FINAL DE CARRERA, no del reloj:
// si la compuerta no se mueve, el aire no se invierte.
GVL_SECUENCIA.aire_invertido := compuerta_invertida;

// --- Órdenes de movimiento (la bobina se apaga al llegar al final de carrera) ---
mov_compuerta_inv := (GVL_SECUENCIA.estado = E_ESTADO.INVERSION)
                     AND sentido_pedido AND NOT GVL_SECUENCIA.I_1B2;

mov_compuerta_norm := (((GVL_SECUENCIA.estado = E_ESTADO.INVERSION) AND NOT sentido_pedido)
                       OR (GVL_SECUENCIA.estado = E_ESTADO.CARGA))
                      AND NOT GVL_SECUENCIA.I_1B1;

// La bandeja solo se mueve con el ventilador apagado (CARGA y DESCARGA no lo encienden)
mov_bandeja_adentro := (GVL_SECUENCIA.estado = E_ESTADO.CARGA) AND NOT GVL_SECUENCIA.I_2B2;
mov_bandeja_afuera  := (GVL_SECUENCIA.estado = E_ESTADO.DESCARGA) AND NOT GVL_SECUENCIA.I_2B1;

// --- Bobinas de las válvulas 5/2 biestables (nunca las dos de una válvula a la vez) ---
GVL_SECUENCIA.Q_1S1 := mov_compuerta_inv   AND NOT mov_compuerta_norm;
GVL_SECUENCIA.Q_2S1 := mov_compuerta_norm  AND NOT mov_compuerta_inv;
GVL_SECUENCIA.Q_1S2 := mov_bandeja_adentro AND NOT mov_bandeja_afuera;
GVL_SECUENCIA.Q_2S2 := mov_bandeja_afuera  AND NOT mov_bandeja_adentro;

// --- Ventilador en FluidSIM ---
GVL_SECUENCIA.Q_K1 := GVL_SECUENCIA.ventilador;

// --- Semáforo (IEC 60204-1) ---
tmr_blink(IN := NOT tmr_blink.Q, PT := T#500MS);
IF tmr_blink.Q THEN
    parpadeo := NOT parpadeo;
END_IF

GVL_SECUENCIA.Q_H1_VERDE := (GVL_SECUENCIA.estado = E_ESTADO.CARGA)
                         OR (GVL_SECUENCIA.estado = E_ESTADO.SECADO)
                         OR (GVL_SECUENCIA.estado = E_ESTADO.INVERSION)
                         OR (GVL_SECUENCIA.estado = E_ESTADO.ENFRIAMIENTO)
                         OR (GVL_SECUENCIA.estado = E_ESTADO.DESCARGA)
                         OR ((GVL_SECUENCIA.estado = E_ESTADO.FIN_SECADO) AND parpadeo);

GVL_SECUENCIA.Q_H2_AMARILLA := (GVL_SECUENCIA.estado = E_ESTADO.REPOSO)
                            OR (GVL_SECUENCIA.estado = E_ESTADO.PARO);

GVL_SECUENCIA.Q_H3_ROJA := (GVL_SECUENCIA.estado = E_ESTADO.EMERGENCIA)
                        OR ((GVL_SECUENCIA.estado = E_ESTADO.FALLA) AND parpadeo);

// --- Vigilancia de carrera: se llama en cada ciclo ---
tmr_mov(IN := mov_compuerta_inv OR mov_compuerta_norm OR mov_bandeja_adentro OR mov_bandeja_afuera,
        PT := T_MOV_MAX);

// =====================================================================
// 6. ESCRITURA A FLUIDSIM (OUTPUT0 -> bloque "FluidSIM In")
// =====================================================================
GVL_SECUENCIA.OUTPUT0.0 := GVL_SECUENCIA.Q_1S1;           // 1S1 cilindro 1 sale
GVL_SECUENCIA.OUTPUT0.1 := GVL_SECUENCIA.Q_2S1;           // 2S1 cilindro 1 entra
GVL_SECUENCIA.OUTPUT0.2 := GVL_SECUENCIA.Q_1S2;           // 1S2 cilindro 2 sale
GVL_SECUENCIA.OUTPUT0.3 := GVL_SECUENCIA.Q_2S2;           // 2S2 cilindro 2 entra
GVL_SECUENCIA.OUTPUT0.4 := GVL_SECUENCIA.Q_K1;            // K1 ventilador
GVL_SECUENCIA.OUTPUT0.5 := GVL_SECUENCIA.Q_H1_VERDE;      // lámpara verde
GVL_SECUENCIA.OUTPUT0.6 := GVL_SECUENCIA.Q_H2_AMARILLA;   // lámpara amarilla
GVL_SECUENCIA.OUTPUT0.7 := GVL_SECUENCIA.Q_H3_ROJA;       // lámpara roja

// --- Textos para la HMI ---
CASE GVL_SECUENCIA.estado OF
    E_ESTADO.REPOSO:
        IF GVL_SECUENCIA.lote_preparado THEN
            GVL_SECUENCIA.estado_txt := 'LOTE LISTO - PULSE START';
        ELSE
            GVL_SECUENCIA.estado_txt := 'REPOSO - PULSE NUEVO LOTE';
        END_IF
    E_ESTADO.CARGA:        GVL_SECUENCIA.estado_txt := 'CARGA';
    E_ESTADO.SECADO:       GVL_SECUENCIA.estado_txt := 'SECADO';
    E_ESTADO.INVERSION:    GVL_SECUENCIA.estado_txt := 'INVERSION DEL AIRE';
    E_ESTADO.ENFRIAMIENTO: GVL_SECUENCIA.estado_txt := 'ENFRIAMIENTO';
    E_ESTADO.FIN_SECADO:   GVL_SECUENCIA.estado_txt := 'FIN DE SECADO';
    E_ESTADO.DESCARGA:     GVL_SECUENCIA.estado_txt := 'DESCARGA';
    E_ESTADO.PARO:         GVL_SECUENCIA.estado_txt := 'PARO';
    E_ESTADO.FALLA:        GVL_SECUENCIA.estado_txt := 'FALLA';
    E_ESTADO.EMERGENCIA:   GVL_SECUENCIA.estado_txt := 'EMERGENCIA';
END_CASE

CASE GVL_SECUENCIA.falla_codigo OF
    0: GVL_SECUENCIA.falla_txt := '';
    1: GVL_SECUENCIA.falla_txt := 'Sin comunicacion con Python';
    2: GVL_SECUENCIA.falla_txt := 'Compuerta trabada (1B1/1B2)';
    3: GVL_SECUENCIA.falla_txt := 'Bandeja trabada (2B1/2B2)';
    4: GVL_SECUENCIA.falla_txt := 'Finales de carrera incoherentes';
END_CASE

// =====================================================================
// 7. AUXILIARES DE LA HMI (animaciones y textos que cambian)
// =====================================================================
tmr_anim(IN := NOT tmr_anim.Q, PT := T#100MS);
IF tmr_anim.Q AND GVL_SECUENCIA.Q_K1 THEN
    angulo_vent := angulo_vent + 30.0;
    IF angulo_vent >= 360.0 THEN angulo_vent := angulo_vent - 360.0; END_IF
END_IF
IF GVL_SECUENCIA.I_1B2 THEN angulo_compuerta := 90.0; ELSE angulo_compuerta := 0.0; END_IF
IF GVL_SECUENCIA.I_2B2 THEN x_bandeja := 0; ELSE x_bandeja := -220; END_IF

IF PLC_PRG.comm_error THEN txt_comm := 'ERROR'; ELSE txt_comm := 'OK'; END_IF

IF PLC_PRG.aire_invertido THEN
    txt_aire := 'INVERTIDO (arriba -> abajo)';
ELSE
    txt_aire := 'NORMAL (abajo -> arriba)';
END_IF

IF GVL_SECUENCIA.I_2B2 AND NOT GVL_SECUENCIA.I_2B1 THEN
    txt_bandeja := 'ADENTRO';
ELSIF GVL_SECUENCIA.I_2B1 AND NOT GVL_SECUENCIA.I_2B2 THEN
    txt_bandeja := 'AFUERA';
ELSE
    txt_bandeja := 'EN MOVIMIENTO';
END_IF

IF PLC_PRG.fan_on THEN txt_vent := 'ENCENDIDO'; ELSE txt_vent := 'APAGADO'; END_IF
IF PLC_PRG.heater_on THEN txt_resist := 'ENCENDIDA'; ELSE txt_resist := 'APAGADA'; END_IF

IF GVL_SECUENCIA.estado = E_ESTADO.EMERGENCIA THEN
    txt_alarma := 'PARO DE EMERGENCIA ACTIVO';
ELSIF GVL_SECUENCIA.falla_txt <> '' THEN
    txt_alarma := GVL_SECUENCIA.falla_txt;
ELSE
    txt_alarma := 'Sin alarmas activas';
END_IF

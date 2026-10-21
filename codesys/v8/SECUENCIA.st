// =====================================================================
// SECUENCIA — Máquina de estados del secador de café (CASE OF)
// Proyecto: Supervisión IoT del secado de café (CODESYS V3.5 SP9)
// Versión: v8, 21 oct 2026
//   v8: pulso de vida de FluidSIM (falla 5), post-ventilación en PARO y FALLA,
//       EMERGENCIA con todas las salidas en cero, reloj de inversión con el tiempo de
//       secado efectivo (registro 29). La física de la planta NO depende de este programa:
//       Python sigue integrando aunque CODESYS o FluidSIM se detengan.
//   v6: modo sin_fluidsim (el PLC simula pulsadores de campo y cilindros).
//   14 oct: botón Nuevo lote + auxiliares HMI.
//
// Llamar en la MainTask DESPUÉS de PLC_PRG:
//   MainTask: 1) PLC_PRG   (lee Python por Modbus, watchdog, fin_secado)
//             2) SECUENCIA (decide estado, cilindros, ventilador, semáforo)
//
// Dueño de variables: SECUENCIA escribe solo en GVL_SECUENCIA.
// De PLC_PRG solo LEE: comm_error, safety_ok, fin_secado, tiempo_secado_h, t_secado_efectivo_h, t_planta_h.
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
    falla_fluidsim   : BOOL;   // v8: el pulso de vida de FluidSIM dejó de cambiar
    tmr_fs           : TON;    // v8: vigila el pulso de vida de FluidSIM
    pulso_fs_anterior: BOOL;   // v8

    // --- v8: post-ventilación (resistencia en 0, ventilador sigue un tiempo) ---
    calentaba        : BOOL;   // la resistencia tenía permiso justo antes de la parada
    pv_activa        : BOOL;   // hay post-ventilación pendiente en PARO / FALLA
    t_pv_ini_h       : REAL;   // tiempo de planta al empezar la post-ventilación
    post_vent        : BOOL;   // ventilador encendido por post-ventilación
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
    piloto_bandeja_adentro : BOOL;    // v8: piloto HMI "Bandeja adentro" (2B2 activo y 2B1 inactivo)
    txt_vent         : STRING(12);
    txt_resist       : STRING(12);
    txt_alarma       : STRING(50);
    lim_objetivo     : REAL := 11.0;  // línea de referencia en la tendencia
    lim_capa         : REAL := 12.0;  // línea de referencia en la tendencia

    // --- v8: modo de E/S aplicado (copia de sin_fluidsim que solo cambia sin movimiento) ---
    modo_sim         : BOOL := TRUE;  // TRUE = E/S emuladas por el PLC; FALSE = E/S de FluidSIM
    modo_sim_ant     : BOOL := TRUE;
    txt_modo         : STRING(50);    // texto para la HMI
    sincronizando    : BOOL;          // v8: llevando los cilindros de FluidSIM a la posición del PLC
    entradas_muertas : BOOL;          // v8: INPUT0 sin ningún final de carrera ni NC cerrado = enlace caído
    tmr_muertas      : TON;           // v8: filtro de 1 s para entradas_muertas
    resinc_pendiente : BOOL;          // v8: al reconocer una caída de FluidSIM, resincronizar cilindros
    ult_band_adentro : BOOL;          // v8: última posición VÁLIDA de la bandeja (enlace vivo)
    ult_comp_inv     : BOOL;          // v8: última posición VÁLIDA de la compuerta (enlace vivo)
    obj_band_adentro : BOOL;          // posición objetivo de la bandeja al sincronizar
    obj_comp_inv     : BOOL;          // posición objetivo de la compuerta al sincronizar

    // --- v6: simulación de cilindros cuando sin_fluidsim = TRUE ---
    sim_comp_inv     : BOOL;          // TRUE = compuerta invertida (1B2)
    sim_band_adentro : BOOL;          // TRUE = bandeja adentro (2B2)
END_VAR
VAR CONSTANT
    T_MOV_MAX                 : TIME := T#5S;   // tiempo máximo de carrera de un cilindro (real)
    T_ENFRIAMIENTO_H          : REAL := 0.5;    // h de modelo con ventilador sin resistencia (supuesto propio)
    T_POSTVENT_H              : REAL := 0.1667; // v8: 10 min de modelo de post-ventilación tras PARO o FALLA
                                                // (práctica de calentadores de ducto; criterio propio declarado)
    T_FS_MAX                  : TIME := T#5S;   // v8: sin cambio del pulso de FluidSIM en 5 s -> enlace caído
    VIGILAR_PULSO_FS          : BOOL := FALSE;  // v8: poner TRUE cuando el oscilador KT1/KT2 esté armado en
                                                // FluidSIM (entrada 7). Con FALSE no se vigila el enlace
                                                // (Python recibe 0 = no informado) y el ensayo F2 no aplica.
    PERIODO_INVERSION_H       : DINT := 6;      // SECAFÉ (2008)
    PAUSA_RESIST_EN_INVERSION : BOOL := FALSE;  // FALSE en la demo acelerada (factor 540);
                                                // TRUE solo en la verificación a tiempo real
END_VAR

// =====================================================================
// 0. LECTURA DE FLUIDSIM (INPUT0 <- bloque "FluidSIM Out") o SIMULACIÓN (v6)
// =====================================================================
// v8: el modo se aplica DE INMEDIATO, en cualquier estado (igual que v6). Al pasar a FluidSIM,
// el PLC SINCRONIZA: mueve los cilindros de FluidSIM hasta la posición que tenía la simulación
// (sección 5). Al volver a emulado, el PLC parte de la última posición real leída de FluidSIM.
modo_sim := GVL_SECUENCIA.sin_fluidsim;
IF modo_sim <> modo_sim_ant THEN
    IF NOT modo_sim THEN
        obj_band_adentro := sim_band_adentro;
        obj_comp_inv     := sim_comp_inv;
        sincronizando    := TRUE;
    ELSE
        sim_band_adentro := GVL_SECUENCIA.I_2B2;   // última posición real (ciclo anterior)
        sim_comp_inv     := GVL_SECUENCIA.I_1B2;
    END_IF
    modo_sim_ant := modo_sim;
END_IF

IF modo_sim THEN
    // Pulsadores de campo en reposo: solo manda la HMI
    GVL_SECUENCIA.I_EMERGENCIA_NC := TRUE;
    GVL_SECUENCIA.I_START         := FALSE;
    GVL_SECUENCIA.I_STOP_NC       := TRUE;
    // Cilindros simulados: llegan al final de carrera en cuanto se activa la bobina
    // (usa las bobinas del ciclo anterior)
    IF GVL_SECUENCIA.Q_1S1 THEN sim_comp_inv := TRUE;  END_IF
    IF GVL_SECUENCIA.Q_2S1 THEN sim_comp_inv := FALSE; END_IF
    IF GVL_SECUENCIA.Q_1S2 THEN sim_band_adentro := TRUE;  END_IF
    IF GVL_SECUENCIA.Q_2S2 THEN sim_band_adentro := FALSE; END_IF
    GVL_SECUENCIA.I_1B1 := NOT sim_comp_inv;
    GVL_SECUENCIA.I_1B2 := sim_comp_inv;
    GVL_SECUENCIA.I_2B1 := NOT sim_band_adentro;
    GVL_SECUENCIA.I_2B2 := sim_band_adentro;
ELSE
    GVL_SECUENCIA.I_EMERGENCIA_NC := GVL_SECUENCIA.INPUT0.0;   // EMERGENCY (NC)
    GVL_SECUENCIA.I_START         := GVL_SECUENCIA.INPUT0.1;   // START (NA)
    GVL_SECUENCIA.I_STOP_NC       := GVL_SECUENCIA.INPUT0.2;   // STOP (NC)
    GVL_SECUENCIA.I_1B1           := GVL_SECUENCIA.INPUT0.3;   // compuerta atrás
    GVL_SECUENCIA.I_1B2           := GVL_SECUENCIA.INPUT0.4;   // compuerta adelante
    GVL_SECUENCIA.I_2B1           := GVL_SECUENCIA.INPUT0.5;   // bandeja afuera
    GVL_SECUENCIA.I_2B2           := GVL_SECUENCIA.INPUT0.6;   // bandeja adentro
    GVL_SECUENCIA.I_FLUIDSIM_PULSO := GVL_SECUENCIA.INPUT0.7;  // v8: pulso de vida
END_IF

// v8: VIGILANCIA DEL ENLACE CON FLUIDSIM (dos criterios):
//  a) Entradas muertas: si INPUT0 no trae ningún final de carrera (1B1, 1B2, 2B1, 2B2) NI los
//     contactos NC de STOP y EMERGENCIA cerrados (bits 0, 2, 3, 4, 5, 6 en 0), el enlace está
//     caído: físicamente cada cilindro siempre tiene un final de carrera activo, salvo en
//     movimiento, y nunca los dos cilindros a la vez con los dos NC abiertos. Es lo que
//     llega cuando se detiene la simulación de FluidSIM. Filtro de 1 s.
//  b) Pulso de vida (opcional, VIGILAR_PULSO_FS): detecta además un enlace CONGELADO, en el que
//     INPUT0 se queda con su último valor válido.
// Con el enlace caído, STOP y EMERGENCIA de campo NO se interpretan como pulsados (sección 1):
// la máquina pasa a FALLA 5 (recuperable), no a EMERGENCIA.
entradas_muertas := (NOT modo_sim) AND ((GVL_SECUENCIA.INPUT0 AND 16#7D) = 0);
tmr_muertas(IN := entradas_muertas, PT := T#1S);
IF modo_sim OR NOT VIGILAR_PULSO_FS THEN
    tmr_fs(IN := FALSE);
ELSIF GVL_SECUENCIA.I_FLUIDSIM_PULSO <> pulso_fs_anterior THEN
    tmr_fs(IN := FALSE);
ELSE
    tmr_fs(IN := TRUE, PT := T_FS_MAX);
END_IF
pulso_fs_anterior := GVL_SECUENCIA.I_FLUIDSIM_PULSO;
falla_fluidsim := (NOT modo_sim) AND (tmr_muertas.Q OR tmr_fs.Q);
IF falla_fluidsim THEN
    resinc_pendiente := TRUE;                    // al reconocer: resincronizar cilindros
END_IF

IF modo_sim THEN
    GVL_SECUENCIA.fluidsim_estado := 2;          // modo emulado, DECLARADO a Python
ELSIF falla_fluidsim OR entradas_muertas THEN
    GVL_SECUENCIA.fluidsim_estado := 3;          // enlace caído
ELSE
    GVL_SECUENCIA.fluidsim_estado := 1;          // vivo
END_IF

// Última posición VÁLIDA de los cilindros (solo con el enlace vivo y finales coherentes)
IF NOT entradas_muertas AND NOT falla_fluidsim THEN
    IF GVL_SECUENCIA.I_2B2 AND NOT GVL_SECUENCIA.I_2B1 THEN ult_band_adentro := TRUE;  END_IF
    IF GVL_SECUENCIA.I_2B1 AND NOT GVL_SECUENCIA.I_2B2 THEN ult_band_adentro := FALSE; END_IF
    IF GVL_SECUENCIA.I_1B2 AND NOT GVL_SECUENCIA.I_1B1 THEN ult_comp_inv := TRUE;  END_IF
    IF GVL_SECUENCIA.I_1B1 AND NOT GVL_SECUENCIA.I_1B2 THEN ult_comp_inv := FALSE; END_IF
END_IF

IF sincronizando THEN
    txt_modo := 'Sincronizando cilindros de FluidSIM...';
ELSIF modo_sim THEN
    txt_modo := 'MODO: SIN FLUIDSIM (E/S emuladas)';
ELSIF falla_fluidsim OR entradas_muertas THEN
    txt_modo := 'MODO: FLUIDSIM - SIN ENLACE';
ELSE
    txt_modo := 'MODO: FLUIDSIM';
END_IF

// =====================================================================
// 1. ENTRADAS Y MANDOS
// =====================================================================
GVL_SECUENCIA.nuevo_lote := FALSE;   // pulso de un solo ciclo

rt_start(CLK := GVL_SECUENCIA.I_START OR GVL_SECUENCIA.hmi_start);
start_pulso := rt_start.Q;
rt_nuevo(CLK := GVL_SECUENCIA.hmi_nuevo_lote);

// STOP y EMERGENCIA son NC: el contacto abierto (FALSE) significa pulsado.
// v8: si el ENLACE con FluidSIM está caído (entradas muertas), esos contactos no se interpretan
// como pulsados: la máquina va a FALLA 5 (recuperable, resistencia en 0 y post-ventilación) en
// lugar de EMERGENCIA. Un pulsador realmente oprimido con el enlace vivo sigue funcionando,
// porque los finales de carrera mantienen INPUT0 distinto de cero.
stop_activo := ((NOT GVL_SECUENCIA.I_STOP_NC) AND NOT entradas_muertas) OR GVL_SECUENCIA.hmi_stop;
emergencia  := (NOT GVL_SECUENCIA.I_EMERGENCIA_NC) AND NOT entradas_muertas;

// Posición real de la compuerta
compuerta_invertida := GVL_SECUENCIA.I_1B2 AND NOT GVL_SECUENCIA.I_1B1;
compuerta_normal    := GVL_SECUENCIA.I_1B1 AND NOT GVL_SECUENCIA.I_1B2;

// Reloj de inversión: cada 6 h de SECADO EFECTIVO cambia el sentido pedido.
// v8: usa el registro 29 (horas con calentamiento permitido) para que la post-ventilación
// de un PARO no corra el reloj de inversión.
t_lote_h := PLC_PRG.t_secado_efectivo_h - t0_lote_h;
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
// v8: ¿la resistencia tenía permiso justo antes? (salida del ciclo anterior)
calentaba := GVL_SECUENCIA.calentar;

IF emergencia THEN
    GVL_SECUENCIA.estado := E_ESTADO.EMERGENCIA;
    pv_activa := FALSE;   // EMERGENCIA: todo en cero, sin post-ventilación (ver sección 5)

ELSIF en_ciclo AND (falla_comm OR falla_fluidsim OR falla_fc OR tmr_mov.Q) THEN
    pv_activa  := calentaba;            // v8: post-ventilación si venía calentando
    t_pv_ini_h := PLC_PRG.t_planta_h;
    // v8: recordar dónde iba el lote para la recuperación (ensayo F4). Si la falla llega
    // estando en PARO, se conserva el estado_previo que ya tenía el PARO.
    IF GVL_SECUENCIA.estado <> E_ESTADO.PARO THEN
        estado_previo := GVL_SECUENCIA.estado;
    END_IF
    IF falla_comm THEN
        GVL_SECUENCIA.falla_codigo := 1;
    ELSIF falla_fluidsim THEN
        GVL_SECUENCIA.falla_codigo := 5;
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
    pv_activa  := calentaba;            // v8: post-ventilación si venía calentando
    t_pv_ini_h := PLC_PRG.t_planta_h;
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
          AND NOT stop_activo AND NOT falla_comm AND NOT falla_fc AND NOT falla_fluidsim
          AND NOT sincronizando THEN
        // v8: es un ENCLAVAMIENTO DE MÁQUINA (no arrancar sin E/S de campo), no una pausa de la
        // física: Python sigue integrando la planta con o sin CODESYS/FluidSIM.
        GVL_SECUENCIA.estado := E_ESTADO.CARGA;
    END_IF

E_ESTADO.CARGA:
    // Bandeja adentro (2B2) y compuerta en posición normal (1B1)
    IF GVL_SECUENCIA.I_2B2 AND NOT GVL_SECUENCIA.I_2B1 AND compuerta_normal THEN
        t0_lote_h := PLC_PRG.t_secado_efectivo_h;  // v8: el reloj de inversión empieza en 0
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
    // v8: no reanuda mientras se sincronizan los cilindros de FluidSIM.
    IF start_pulso AND NOT stop_activo AND NOT sincronizando THEN
        GVL_SECUENCIA.estado := estado_previo;
    END_IF

E_ESTADO.FALLA:
    // Roja intermitente. START reconoce la falla si la causa ya desapareció.
    // v8 (ensayo F4, recuperación controlada): el lote NO se reinicia. El primer START
    // reconoce la falla y deja la máquina en PARO; un segundo START reanuda donde iba
    // (mismo lote, misma energía y mismo reloj de inversión). Python nunca dejó de integrar.
    IF start_pulso AND NOT falla_comm AND NOT falla_fc AND NOT falla_fluidsim
       AND NOT entradas_muertas THEN
        GVL_SECUENCIA.falla_codigo := 0;
        GVL_SECUENCIA.estado := E_ESTADO.PARO;
        // v8: si FluidSIM se cayó, al reiniciarse sus cilindros vuelven a la posición inicial
        // del circuito: se llevan a la última posición válida antes de reanudar.
        IF resinc_pendiente THEN
            obj_band_adentro := ult_band_adentro;
            obj_comp_inv     := ult_comp_inv;
            sincronizando    := TRUE;
            resinc_pendiente := FALSE;
        END_IF
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
// v8: POLÍTICA DE PARADA (guía de cierre, R4; Tabla C1 del documento)
//   - PARO y FALLA: resistencia en cero de inmediato; si venía calentando, el ventilador
//     sigue T_POSTVENT_H para sacar el calor del ducto (evita sobretemperatura de los
//     elementos) y luego se apaga. Si la falla es la comunicación con Python, CODESYS no
//     puede mandar nada útil: aplica la política local de Python (misma post-ventilación).
//   - EMERGENCIA: TODAS las salidas en cero, incluido el ventilador (parada de todo
//     movimiento; el sobrecalentamiento lo cubre el corte térmico de la resistencia). En una
//     implementación real, la salida del ventilador en emergencia se decide con la evaluación
//     de riesgos (ISO 12100); esto es una función de software demostrada, no una
//     certificación de seguridad.
post_vent := ((GVL_SECUENCIA.estado = E_ESTADO.PARO) OR (GVL_SECUENCIA.estado = E_ESTADO.FALLA))
             AND pv_activa AND NOT falla_comm
             AND (PLC_PRG.t_planta_h > 0.0)   // sin los canales 33-34 no hay reloj: sin post-ventilación
             AND (PLC_PRG.t_planta_h >= t_pv_ini_h) // si Python se reinició, su reloj volvió a 0: se termina
             AND ((PLC_PRG.t_planta_h - t_pv_ini_h) < T_POSTVENT_H);
GVL_SECUENCIA.ventilador := (GVL_SECUENCIA.estado = E_ESTADO.SECADO)
                         OR (GVL_SECUENCIA.estado = E_ESTADO.INVERSION)
                         OR (GVL_SECUENCIA.estado = E_ESTADO.ENFRIAMIENTO)
                         OR post_vent;

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

// v8: SINCRONIZACIÓN al pasar a FluidSIM. Mueve cada cilindro de FluidSIM hasta la posición que
// tenía la simulación y termina cuando los finales de carrera la confirman. Si un cilindro no
// llega en T_MOV_MAX, la vigilancia de carrera (tmr_mov) lleva a FALLA 2 o 3. Se cancela en
// FALLA o EMERGENCIA (en EMERGENCIA no se mueve nada).
IF sincronizando THEN
    IF (GVL_SECUENCIA.estado = E_ESTADO.FALLA) OR (GVL_SECUENCIA.estado = E_ESTADO.EMERGENCIA)
       OR entradas_muertas THEN
        sincronizando := FALSE;
    ELSE
        mov_bandeja_adentro := obj_band_adentro AND NOT GVL_SECUENCIA.I_2B2;
        mov_bandeja_afuera  := (NOT obj_band_adentro) AND NOT GVL_SECUENCIA.I_2B1;
        mov_compuerta_inv   := obj_comp_inv AND NOT GVL_SECUENCIA.I_1B2;
        mov_compuerta_norm  := (NOT obj_comp_inv) AND NOT GVL_SECUENCIA.I_1B1;
        IF NOT (mov_bandeja_adentro OR mov_bandeja_afuera OR mov_compuerta_inv OR mov_compuerta_norm) THEN
            sincronizando := FALSE;   // FluidSIM ya está donde estaba la simulación
        END_IF
    END_IF
END_IF

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
    E_ESTADO.PARO:
        IF post_vent THEN
            GVL_SECUENCIA.estado_txt := 'PARO - POST-VENTILACION';
        ELSE
            GVL_SECUENCIA.estado_txt := 'PARO';
        END_IF
    E_ESTADO.FALLA:        GVL_SECUENCIA.estado_txt := 'FALLA';
    E_ESTADO.EMERGENCIA:   GVL_SECUENCIA.estado_txt := 'EMERGENCIA';
END_CASE

CASE GVL_SECUENCIA.falla_codigo OF
    0: GVL_SECUENCIA.falla_txt := '';
    1: GVL_SECUENCIA.falla_txt := 'Sin comunicacion con Python';
    2: GVL_SECUENCIA.falla_txt := 'Compuerta trabada (1B1/1B2)';
    3: GVL_SECUENCIA.falla_txt := 'Bandeja trabada (2B1/2B2)';
    4: GVL_SECUENCIA.falla_txt := 'Finales de carrera incoherentes';
    5: GVL_SECUENCIA.falla_txt := 'Sin enlace con FluidSIM (OPC)';
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

piloto_bandeja_adentro := GVL_SECUENCIA.I_2B2 AND NOT GVL_SECUENCIA.I_2B1;   // v8
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

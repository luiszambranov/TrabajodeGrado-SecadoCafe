// PLC_PRG v8 (21 oct 2026): v7 + relojes y estado de la planta (registros 27-39) y estado del
//   enlace FluidSIM hacia Python (registro 40). Python ya no congela la física en HOLD:
//   con STOP, falla o fin de secado la planta sigue enfriándose y el clima sigue su ciclo.
// PLC_PRG v7 (19 oct 2026): v6 + selección de PERFIL TÉRMICO y CAUDAL en la HMI.
//   - perfil_sel (HMI): 0 = REF 50 °C, 1 = P1 45 °C, 2 = P2 55 -> 35 °C, 3 = P3 35 -> 55 °C.
//     El cambio de P2/P3 ocurre cuando la humedad PROMEDIO del lote llega a 30 % b.h.
//     (de Oliveira et al., 2018; diseño en python/perfiles_termicos.py).
//   - caudal_sel (HMI): 30, 75 o 100 %.
//   - Ambos se toman SOLO en REPOSO; al pulsar START quedan fijos todo el lote (perfil_activo,
//     caudal_activo), como en el diseño experimental.
//   - El PLC calcula la consigna y la envía a Python (registro 26, setpoint_cmd), que la usa
//     en el termostato. Así la consigna de la HMI es la que se aplica de verdad.
// SECUENCIA se llama DESPUÉS de PLC_PRG en la MainTask.
PROGRAM PLC_PRG
VAR
    // --- Crudo Modbus (words) que se mapean en IO Mapping ---
    T_process_raw   : ARRAY[0..1] OF WORD;
    RH_ambient_raw  : ARRAY[0..1] OF WORD;
    heater_cmd      : WORD;
    fan_cmd         : WORD;
    plant_mode      : WORD;
    safety_ok       : WORD;

    // --- Conversión a REAL ---
    conv_T          : U_WORDS_TO_REAL;
    conv_RH         : U_WORDS_TO_REAL;
    T_process       : REAL;
    RH_ambient      : REAL;

    // --- Auxiliares para el HMI ---
    heater_on       : BOOL;
    fan_on          : BOOL;
    safety_alarm    : BOOL;
    planta_on       : BOOL;   // piloto "Planta en funcionamiento"
    aire_invertido  : BOOL;   // piloto HMI: sentido del aire invertido

    setpoint        : REAL := 50.0;   // °C, consigna aplicada (v7: la calcula el perfil; REF = 50 °C, González et al., 2010)
    tiempo_proceso_raw : ARRAY[0..1] OF WORD;  // [0]=tiempo_proceso_hi, [1]=tiempo_proceso_lo
    conv_tiempo         : U_WORDS_TO_REAL;
    tiempo_secado_h     : REAL;

    M_coffee_raw  : ARRAY[0..1] OF WORD;
    conv_mcoffee  : U_WORDS_TO_REAL;
    M_coffee      : REAL;

    heartbeat_actual   : WORD;   // viene del IO Mapping
    heartbeat_anterior : WORD;
    tmr_comm           : TON;
    comm_error         : BOOL;

    RH_process_raw  : ARRAY[0..1] OF WORD;   // [0] <- RH_process_hi (dir 13), [1] <- RH_process_lo (dir 14)
    conv_RH_process : U_WORDS_TO_REAL;
    RH_process      : REAL;                   // % HR dentro de la cámara

    // ===== NUEVO (4 oct 2026) =====
    flow_dir_cmd      : WORD;                  // canal FC06, dir 15
    M_coffee_max_raw  : ARRAY[0..1] OF WORD;   // [0] <- dir 16 (_hi), [1] <- dir 17 (_lo)
    conv_mcoffee_max  : U_WORDS_TO_REAL;
    M_coffee_max      : REAL;                  // % b.h. de la capa más húmeda
    heater_duty_raw   : ARRAY[0..1] OF WORD;   // [0] <- dir 18 (_hi), [1] <- dir 19 (_lo)
    conv_duty         : U_WORDS_TO_REAL;
    heater_duty       : REAL;                  // % del ciclo con la resistencia encendida

    // ===== NUEVO (5 oct 2026): manipulada 2, caudal variable =====
    fan_speed_pct     : WORD := 100;           // canal FC06, dir 20: consigna de caudal 30-100 % (HMI)
    caudal_raw        : ARRAY[0..1] OF WORD;   // [0] <- dir 22 (_hi), [1] <- dir 23 (_lo)
    conv_caudal       : U_WORDS_TO_REAL;
    caudal_m3_min     : REAL;                  // caudal real aplicado (8.0 = 100 %)

    // ===== NUEVO v5 (14 oct 2026) =====
    caudal_sel        : INT := 100;            // selector de la HMI (cuadro combinado): 30, 75 o 100 %
    reset_lote_cmd    : WORD;                  // canal FC06, dir 21: pulso "Nuevo lote" hacia Python
    tp_reset          : TP;                    // mantiene el pulso 3 s para que Python lo vea
    energia_raw       : ARRAY[0..1] OF WORD;   // [0] <- dir 24 (_hi), [1] <- dir 25 (_lo)
    conv_energia      : U_WORDS_TO_REAL;
    energia_kWh       : REAL;                  // energía eléctrica del lote (resistencia + ventilador)

    // ===== NUEVO v7 (19 oct 2026): perfiles térmicos =====
    perfil_sel        : INT := 0;              // selector HMI: 0 REF, 1 P1, 2 P2, 3 P3
    perfil_activo     : INT := 0;              // copia fija durante el lote
    caudal_activo     : INT := 100;            // copia fija durante el lote
    sp_inicial        : REAL := 50.0;          // °C antes del cambio
    sp_final          : REAL := 50.0;          // °C después del cambio (30 % b.h.)
    cambio_perfil     : BOOL;                  // TRUE cuando el promedio ya bajó de 30 % b.h. (enclavado)
    setpoint_cmd      : WORD;                  // canal FC06, dir 26: consigna hacia Python (°C enteros)
    perfil_txt        : STRING(40);            // texto para la HMI

    // ===== NUEVO v8 (21 oct 2026): relojes y estado de la planta (Python -> CODESYS) =====
    t_lote_raw        : ARRAY[0..1] OF WORD;   // [0] <- dir 27 (_hi), [1] <- dir 28 (_lo)
    t_secado_ef_raw   : ARRAY[0..1] OF WORD;   // [0] <- dir 29, [1] <- dir 30
    t_parado_raw      : ARRAY[0..1] OF WORD;   // [0] <- dir 31, [1] <- dir 32
    t_planta_raw      : ARRAY[0..1] OF WORD;   // [0] <- dir 33, [1] <- dir 34
    estado_planta     : WORD;                  // dir 35: 0 REPOSO, 1 SECANDO, 2 VENTILANDO, 3 POST-VENT, 4 FALLA COMM
    T_amb_raw         : ARRAY[0..1] OF WORD;   // [0] <- dir 36, [1] <- dir 37
    hora_raw          : ARRAY[0..1] OF WORD;   // [0] <- dir 38, [1] <- dir 39
    conv_t_lote       : U_WORDS_TO_REAL;
    conv_t_secado_ef  : U_WORDS_TO_REAL;
    conv_t_parado     : U_WORDS_TO_REAL;
    conv_t_planta     : U_WORDS_TO_REAL;
    conv_T_amb        : U_WORDS_TO_REAL;
    conv_hora         : U_WORDS_TO_REAL;
    t_lote_h          : REAL;                  // h desde "Nuevo lote" (incluye paradas)
    t_secado_efectivo_h : REAL;                // h con calentamiento permitido (reloj de inversión)
    t_parado_h        : REAL;                  // h del lote sin secar (paro, falla, fin)
    t_planta_h        : REAL;                  // h desde que arrancó la planta (no se reinicia)
    T_ambiente        : REAL;                  // °C exterior (Chinchiná)
    hora_dia          : REAL;                  // 0-24 h del reloj de la planta
    estado_planta_txt : STRING(20);
    hora_txt          : STRING(8);             // 'HH:MM'
    periodo_txt       : STRING(8);             // 'DIA' / 'NOCHE'
    fluidsim_estado_cmd : WORD;                // canal FC06, dir 40: estado del enlace FluidSIM hacia Python
    fluidsim_txt      : STRING(20);
    datos_validos     : BOOL;                  // v8 (R5): FALSE = sin comunicación con Python, valores vencidos
    txt_datos         : STRING(40);            // v8 (R5): aviso para la HMI
    hh                : INT;
    mm                : INT;

    lazo_local        : BOOL := TRUE;          // TRUE = termostato en Python (demo acelerada)
                                               // FALSE = el PLC conmuta la resistencia (solo con --factor-aceleracion 1 --lazo-termico plc)
    fin_secado        : BOOL;                  // se enclava al llegar a la humedad objetivo
    reset_lote        : BOOL;                  // botón HMI: nuevo lote (borra fin_secado)
                                               // v4: también lo borra GVL_SECUENCIA.nuevo_lote
    en_marcha         : BOOL;
END_VAR

// ================== CONVERSIONES (palabra BAJA en words[0]) ==================
conv_T.words[0] := T_process_raw[1];
conv_T.words[1] := T_process_raw[0];
T_process := conv_T.value;

conv_RH.words[0] := RH_ambient_raw[1];
conv_RH.words[1] := RH_ambient_raw[0];
RH_ambient := conv_RH.value;

conv_tiempo.words[0] := tiempo_proceso_raw[1];
conv_tiempo.words[1] := tiempo_proceso_raw[0];
tiempo_secado_h := conv_tiempo.value;

conv_mcoffee.words[0] := M_coffee_raw[1];
conv_mcoffee.words[1] := M_coffee_raw[0];
M_coffee := conv_mcoffee.value;

conv_RH_process.words[0] := RH_process_raw[1];
conv_RH_process.words[1] := RH_process_raw[0];
RH_process := conv_RH_process.value;

conv_mcoffee_max.words[0] := M_coffee_max_raw[1];
conv_mcoffee_max.words[1] := M_coffee_max_raw[0];
M_coffee_max := conv_mcoffee_max.value;

conv_duty.words[0] := heater_duty_raw[1];
conv_duty.words[1] := heater_duty_raw[0];
heater_duty := conv_duty.value;

conv_caudal.words[0] := caudal_raw[1];
conv_caudal.words[1] := caudal_raw[0];
caudal_m3_min := conv_caudal.value;

conv_energia.words[0] := energia_raw[1];   // v5
conv_energia.words[1] := energia_raw[0];
energia_kWh := conv_energia.value;

// ================== RELOJES Y ESTADO DE LA PLANTA (v8) ==================
conv_t_lote.words[0] := t_lote_raw[1];
conv_t_lote.words[1] := t_lote_raw[0];
t_lote_h := conv_t_lote.value;

conv_t_secado_ef.words[0] := t_secado_ef_raw[1];
conv_t_secado_ef.words[1] := t_secado_ef_raw[0];
t_secado_efectivo_h := conv_t_secado_ef.value;

conv_t_parado.words[0] := t_parado_raw[1];
conv_t_parado.words[1] := t_parado_raw[0];
t_parado_h := conv_t_parado.value;

conv_t_planta.words[0] := t_planta_raw[1];
conv_t_planta.words[1] := t_planta_raw[0];
t_planta_h := conv_t_planta.value;

conv_T_amb.words[0] := T_amb_raw[1];
conv_T_amb.words[1] := T_amb_raw[0];
T_ambiente := conv_T_amb.value;

conv_hora.words[0] := hora_raw[1];
conv_hora.words[1] := hora_raw[0];
hora_dia := conv_hora.value;

CASE estado_planta OF
    0: estado_planta_txt := 'REPOSO';
    1: estado_planta_txt := 'SECANDO';
    2: estado_planta_txt := 'VENTILANDO';
    3: estado_planta_txt := 'POST-VENTILACION';
    4: estado_planta_txt := 'FALLA COMUNICACION';
ELSE
    estado_planta_txt := '?';
END_CASE

// Hora del día como texto HH:MM y periodo día/noche (sol de 06:00 a 18:00 en Chinchiná, ~5° N)
hh := DINT_TO_INT(TRUNC(hora_dia));
mm := DINT_TO_INT(TRUNC((hora_dia - DINT_TO_REAL(TRUNC(hora_dia))) * 60.0));
IF hh > 23 THEN hh := 0; END_IF
hora_txt := CONCAT(CONCAT(SEL(hh < 10, INT_TO_STRING(hh), CONCAT('0', INT_TO_STRING(hh))), ':'),
                   SEL(mm < 10, INT_TO_STRING(mm), CONCAT('0', INT_TO_STRING(mm))));
IF (hora_dia >= 6.0) AND (hora_dia < 18.0) THEN
    periodo_txt := 'DIA';
ELSE
    periodo_txt := 'NOCHE';
END_IF

// v8 (guía de cierre R5): marcar los datos vencidos. Si Python no responde, los valores que se
// ven en la HMI son los últimos recibidos y NO deben parecer una medición válida.
datos_validos := NOT comm_error AND (safety_ok = 1);
IF datos_validos THEN
    txt_datos := '';
ELSE
    txt_datos := 'DATOS VENCIDOS - sin comunicacion con Python';
END_IF

// Estado del enlace FluidSIM hacia Python (lo calcula SECUENCIA en el ciclo anterior)
fluidsim_estado_cmd := GVL_SECUENCIA.fluidsim_estado;
CASE GVL_SECUENCIA.fluidsim_estado OF
    1: fluidsim_txt := 'OK';
    2: fluidsim_txt := 'SIN FLUIDSIM (emulado)';
    3: fluidsim_txt := 'SIN ENLACE';
    0: fluidsim_txt := 'FLUIDSIM (sin vigilar)';
ELSE
    fluidsim_txt := '-';
END_CASE

// ================== PERFIL Y CAUDAL (v7) ==================
// Se leen de la HMI solo en REPOSO; durante el lote quedan fijos.
IF GVL_SECUENCIA.estado = E_ESTADO.REPOSO THEN
    IF (perfil_sel >= 0) AND (perfil_sel <= 3) THEN
        perfil_activo := perfil_sel;
    END_IF
    caudal_activo := caudal_sel;
    cambio_perfil := FALSE;
END_IF

CASE perfil_activo OF
    0: sp_inicial := 50.0; sp_final := 50.0; perfil_txt := 'REF: 50 C constante';
    1: sp_inicial := 45.0; sp_final := 45.0; perfil_txt := 'P1: 45 C constante';
    2: sp_inicial := 55.0; sp_final := 35.0; perfil_txt := 'P2: 55 C -> 35 C al 30 % b.h.';
    3: sp_inicial := 35.0; sp_final := 55.0; perfil_txt := 'P3: 35 C -> 55 C al 30 % b.h.';
END_CASE

// Cambio al 30 % b.h. (humedad promedio). Se enclava: no vuelve atrás en el mismo lote.
// M_coffee > 0 evita disparar con el registro aún en 0.0 al arrancar.
IF (M_coffee > 0.0) AND (M_coffee <= 30.0) AND (GVL_SECUENCIA.estado <> E_ESTADO.REPOSO) THEN
    cambio_perfil := TRUE;
END_IF

IF cambio_perfil THEN
    setpoint := sp_final;
ELSE
    setpoint := sp_inicial;
END_IF
setpoint_cmd := REAL_TO_WORD(setpoint);

// v5/v7: consigna de caudal fija del lote
fan_speed_pct := INT_TO_WORD(caudal_activo);
// Consigna de caudal limitada a 30-100 % (mínimo de operación del ventilador)
IF fan_speed_pct > 100 THEN fan_speed_pct := 100; END_IF
IF fan_speed_pct < 30 THEN fan_speed_pct := 30; END_IF

// ================== WATCHDOG (heartbeat de Python) ==================
IF heartbeat_actual <> heartbeat_anterior THEN
    tmr_comm(IN := FALSE);
ELSE
    tmr_comm(IN := TRUE, PT := T#4S);
END_IF
heartbeat_anterior := heartbeat_actual;   // DESPUÉS de comparar
comm_error := tmr_comm.Q;

// ================== NUEVO LOTE (v5) ==================
// SECUENCIA pone nuevo_lote un ciclo al pulsar el botón; el TP lo alarga a 3 s
// para que Python (periodo 1 s) vea el flanco 0 -> 1 en el registro 21.
tp_reset(IN := GVL_SECUENCIA.nuevo_lote, PT := T#3S);
reset_lote_cmd := BOOL_TO_WORD(tp_reset.Q);

// ================== FIN DE SECADO (enclavado) ==================
// Promedio <= 11 % b.h. Y capa más húmeda <= 12 % b.h. (SECAFÉ, 2008).
// M_coffee > 0 evita disparar con el registro aún en 0.0 al arrancar.
// v5: no se enclava mientras dura el pulso de nuevo lote (Python aún publica el lote anterior).
IF (NOT tp_reset.Q) AND (M_coffee > 0.0) AND (M_coffee <= 11.0)
   AND (M_coffee_max > 0.0) AND (M_coffee_max <= 12.0) THEN
    fin_secado := TRUE;
END_IF
IF reset_lote OR tp_reset.Q THEN   // v5
    fin_secado := FALSE;
    reset_lote := FALSE;
END_IF

// ================== SUPERVISIÓN (v4) ==================
// La máquina de estados (SECUENCIA) decide CUÁNDO hay ventilador, resistencia y RUN.
// PLC_PRG solo agrega la seguridad de comunicación y el lazo térmico.
plant_mode := BOOL_TO_WORD(NOT GVL_SECUENCIA.planta_run);   // 0 = RUN, 1 = HOLD
en_marcha  := GVL_SECUENCIA.ventilador AND NOT comm_error;

fan_cmd := BOOL_TO_WORD(en_marcha);

IF lazo_local THEN
    // Python regula a 50 °C cada segundo de modelo; el PLC solo da el permiso.
    heater_cmd := BOOL_TO_WORD(en_marcha AND GVL_SECUENCIA.calentar);
ELSE
    // Todo/nada en el PLC: válido SOLO a tiempo real (factor 1).
    heater_cmd := BOOL_TO_WORD(en_marcha AND GVL_SECUENCIA.calentar AND (T_process < setpoint));
END_IF

// v4: el sentido del aire sale de la POSICIÓN REAL de la compuerta (final de carrera 1B2
// en FluidSIM), no del reloj. El reloj de 6 h (SECAFÉ, 2008) está ahora en SECUENCIA.
flow_dir_cmd := BOOL_TO_WORD(GVL_SECUENCIA.aire_invertido AND NOT comm_error);

// ================== AUXILIARES HMI ==================
IF lazo_local THEN
    heater_on := en_marcha AND (heater_duty > 0.5);
ELSE
    heater_on := (heater_cmd = 1);
END_IF
fan_on       := (fan_cmd = 1);
safety_alarm := (safety_ok = 0) OR comm_error;
planta_on    := en_marcha;
aire_invertido := (flow_dir_cmd = 1);

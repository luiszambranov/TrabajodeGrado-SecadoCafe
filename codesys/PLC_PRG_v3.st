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

    setpoint        : REAL := 50.0;   // °C (González et al., 2010)
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

    lazo_local        : BOOL := TRUE;          // TRUE = termostato en Python (demo acelerada)
                                               // FALSE = el PLC conmuta la resistencia (solo con --factor-aceleracion 1 --lazo-termico plc)
    fin_secado        : BOOL;                  // se enclava al llegar a la humedad objetivo
    reset_lote        : BOOL;                  // botón HMI: nuevo lote (borra fin_secado)
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

// ================== FIN DE SECADO (enclavado) ==================
// Promedio <= 11 % b.h. Y capa más húmeda <= 12 % b.h. (SECAFÉ, 2008).
// M_coffee > 0 evita disparar con el registro aún en 0.0 al arrancar.
IF (M_coffee > 0.0) AND (M_coffee <= 11.0) AND (M_coffee_max > 0.0) AND (M_coffee_max <= 12.0) THEN
    fin_secado := TRUE;
END_IF
IF reset_lote THEN
    fin_secado := FALSE;
    reset_lote := FALSE;
END_IF

// ================== SUPERVISIÓN ==================
// Una sola condición para todo: RUN, comunicación sana y secado sin terminar.
en_marcha := (plant_mode = 0) AND NOT comm_error AND NOT fin_secado;

fan_cmd := BOOL_TO_WORD(en_marcha);

IF lazo_local THEN
    // Python regula a 50 °C cada segundo de modelo; el PLC solo da el permiso.
    heater_cmd := BOOL_TO_WORD(en_marcha);
ELSE
    // Todo/nada en el PLC: válido SOLO a tiempo real (factor 1).
    heater_cmd := BOOL_TO_WORD(en_marcha AND (T_process < setpoint));
END_IF

// Inversión del sentido del aire cada 6 h de modelo (SECAFÉ, 2008)
flow_dir_cmd := BOOL_TO_WORD(en_marcha AND ((TRUNC(tiempo_secado_h) / 6) MOD 2 = 1));

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

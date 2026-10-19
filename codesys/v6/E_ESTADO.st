// DUT (Enumeración) — Estados de la máquina de estados del secador
// Crear en CODESYS: Application > Agregar objeto > DUT > Enumeración, nombre E_ESTADO
{attribute 'qualified_only'}
{attribute 'strict'}
TYPE E_ESTADO :
(
    REPOSO       := 0,   // Listo, esperando START (amarilla fija)
    CARGA        := 1,   // Bandeja entra, compuerta a posición normal
    SECADO       := 2,   // Ventilador + resistencias, perfil térmico
    INVERSION    := 3,   // Cambio de sentido del aire (cada 6 h de lote)
    ENFRIAMIENTO := 4,   // Ventilador sin resistencia
    FIN_SECADO   := 5,   // Lote seco, esperando START para descargar (verde intermitente)
    DESCARGA     := 6,   // Bandeja sale
    PARO         := 7,   // Pausa por STOP (amarilla fija)
    FALLA        := 8,   // Comunicación o cilindro trabado (roja intermitente)
    EMERGENCIA   := 9    // Pulsador de emergencia (roja fija)
);
END_TYPE

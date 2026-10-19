# codesys/v7 — programa vigente (19 oct 2026)

Juego completo del programa CODESYS. Copiar cada archivo en su objeto (o pegar
`CODIGOS_CODESYS_v7.txt`, que trae los cuatro juntos).

| Archivo | Objeto en CODESYS |
|---|---|
| `E_ESTADO.st` | DUT (enumeración) `E_ESTADO` — igual a v6 |
| `GVL_SECUENCIA.st` | GVL `GVL_SECUENCIA` — igual a v6 |
| `PLC_PRG.st` | Programa `PLC_PRG` (1.º en la MainTask) — **cambia** |
| `SECUENCIA.st` | Programa `SECUENCIA` (2.º en la MainTask) — igual a v6 |

## Cambios respecto a v6: perfil térmico y caudal desde la HMI

- `PLC_PRG.perfil_sel` (selector HMI): 0 = REF 50 °C, 1 = P1 45 °C, 2 = P2 55 → 35 °C,
  3 = P3 35 → 55 °C. En P2/P3 la consigna cambia cuando la humedad promedio del lote
  llega a 30 % b.h. (de Oliveira et al., 2018); el cambio queda enclavado en el lote.
  Diseño y fuentes: `python/perfiles_termicos.py`.
- `PLC_PRG.caudal_sel` (selector HMI, ya existía): 30, 75 o 100 %.
- Perfil y caudal se toman solo en REPOSO; al pulsar START quedan fijos todo el lote
  (`perfil_activo`, `caudal_activo`).
- El PLC calcula `setpoint` y lo envía a Python por el **registro 26** (`setpoint_cmd`,
  °C enteros). Python lo usa en el termostato (0 = 50 °C por defecto).
- IO Mapping: canal nuevo **Write Single Register (FC06), desplazamiento 16#001A**,
  variable `Application.PLC_PRG.setpoint_cmd`.
- HMI: cuadro combinado "Perfil térmico" → `PLC_PRG.perfil_sel`; texto del perfil →
  `PLC_PRG.perfil_txt`; el campo "Setpoint" sigue en `PLC_PRG.setpoint` (ahora es la
  consigna real aplicada).

Lado Python (19 oct 2026): `modbus_server.py` (registro 26, 27 registros en total) y
`planta_secado.py` (el termostato usa la consigna del PLC).

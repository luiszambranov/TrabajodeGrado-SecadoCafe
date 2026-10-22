# Diseño inicial de perfiles (5 oct 2026) — DESCARTADO el 21 oct 2026

Campaña Monte Carlo (150 realizaciones, semillas 1001–1150) y piloto (semillas 1–10)
con el diseño inicial: P2 55 → 35 °C y P3 35 → 55 °C.

Se descartó porque 55 °C excede el límite de 50 °C del grano que adopta el trabajo
(González et al., 2010) y no corresponde a la fuente de los escalonados (de Oliveira
et al., 2018, que usó 50 → 35 y 35 → 50 °C). Resultado: P2 y P3 con 6–22 h de grano
por encima de 50 °C (ver `campana/resumen_resultados.md`, tabla "Horas con grano > 50 °C").

El diseño vigente (P2 50 → 35 °C, P3 35 → 50 °C) está en `../campana/` y `../piloto/`.
Las estrategias que no cambiaron (solares, REF, P1-*) son idénticas en ambas campañas.
Se conserva como evidencia de por qué se corrigió el diseño (anexo del documento).

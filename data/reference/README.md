# data/reference — Fuentes de cada parámetro del modelo

Cada archivo reúne los datos de una fuente (o de un grupo de fuentes) con la cita
completa en APA, la tabla de valores que se tomaron y en qué archivo de Python se usan.
Los datos generados por las simulaciones no están aquí, sino en `python/resultados/`.

| Archivo | Qué contiene | Dónde se usa |
|---|---|---|
| `roa_cenicafe_isoterma_capa_delgada.md` | Modelo cinético del secado: isoterma de Roa para café pergamino (Trejos et al., 1989) y ecuación de capa delgada de SECAFÉ (Parra-Coronado et al., 2008), con sus constantes, el dominio de validez y la verificación cruzada de las ecuaciones. | `python/cinetica_roa.py` |
| `secador_electrico_dimensionamiento.md` | Dimensionamiento del secador supervisado: tamaño del lote (80 kg c.p.s.), caudal específico, espesor del lecho, potencia de la resistencia, cámara de aire, con la fuente de cada valor. | `python/dinamica_termica.py`, `python/secador_electrico.py` |
| `equipos_energia.md` | Equipos comerciales de referencia (ventilador, resistencias, extractor de la solar activa) y su consumo; balance de energía de las tres estrategias. | `python/balance_energia.py` |
| `cotizaciones_bom.md` / `.csv` | Lista de materiales cotizada: componente, requisito de diseño, producto, cantidad, precio, proveedor con enlace y fecha de consulta; tasas de cambio, tarifa eléctrica y CAPEX de los escenarios A (20,3 M COP) y B (22,8 M COP). Base del análisis económico. | Documento, capítulo económico |
| `generar_cotizaciones_bom.py` | Genera `cotizaciones_bom.md` y `cotizaciones_bom.csv` a partir de los datos escritos en el propio script. Uso: `python generar_cotizaciones_bom.py` (desde esta carpeta). | — |
| `chinchina_clima_fuentes.md` | Clima de Chinchiná: medias de la estación Naranjal, horas de temperatura mínima y máxima, radiación solar, tiempos del secado solar de Cenicafé y variabilidad diaria calculada con NASA POWER. | `python/generador_ambiente.py`, `python/variabilidad_clima.py`, líneas base solares |
| `reposo_tiro_natural.md` | Qué pasa en la planta cuando el ventilador se apaga (paro, falla o fin de lote): tiro natural, enfriamiento de la cámara, secado residual y post-ventilación, con los supuestos y su sensibilidad. | `python/dinamica_termica.py`, `python/lecho_secado.py`, `python/planta_secado.py` |
| `resende_2009_secado_patio.md` | Secado de café en patio de concreto (Resende et al., 2009): condiciones y tiempo medido. | Caso V2 de `python/validacion_modelo.py` |
| `validacion_modelo.md` | Validación del modelo frente a 4 casos independientes (laboratorio, patio, secador Escafé y secado solar): datos de referencia, resultado del modelo, error y lectura de los sesgos. | `python/validacion_modelo.py` |

# Índice técnico de entrega

| Área | Documentación y fuente editable | Evidencias |
|---|---|---|
| Requisitos / alcance | requisitos-y-plan.md, modelo-ventas.md | guía extraída y hash en evidence/ |
| Arquitectura | arquitectura.md, diagramas/arquitectura.mmd | reconstrucción y recorrido local |
| Fuente | erd-fuente.md, diccionario-fuente.md, diagramas/erd-fuente.mmd | source-profile.json, backup-sha256.txt |
| Modelo dimensional | modelo-ventas.md, diagramas/modelo-ventas.mmd, database/ | diccionario-analitico.md y reconciliación |
| ETL / SCD | incremental-y-scd.md, calidad.md, etl/, database/ | incremental-tests.json y reportes de reconstrucción |
| API / dashboard | contratos.md, openapi.json, dashboard.md, backend/, frontend/ | reportes y capturas Chrome |
| Machine Learning | ../machine-learning/ML.md, machine_learning/ | ml-training.json, métricas y artefactos locales ignorados |
| Generative AI | ../generative-ai/GENAI.md, generative_ai/ | genai-evaluation.json, genai-review.md |
| Alertas | ../notifications/README.md, notifications/, diagramas/alertas.mmd | alert-tests.json, alert-demo.json, entrega y estados |
| Operación | operacion.md, deployment/ | readiness, persistencia, aceptación y secretos |
| Usuario | manual-usuario.md | recorrido de seis secciones |
| Aceptación | revision-final.md, pruebas.md, tests/ | evidence/day4-rebuild/, delivery-check.json |
| Presentación | guion-video.md, demo.md | video a grabar por el autor; no se declara grabado |

Las rutas de esta tabla son relativas a documentation/ salvo las carpetas de código,
que están en la raíz. Los reportes históricos originales se conservan; los de la
reconstrucción están separados en evidence/day4-rebuild/. Fechas técnicas UTC;
interfaz en Tegucigalpa. Los seis archivos .mmd preservan la edición de los diagramas
aunque el usuario incorpore imágenes en los documentos principales.

Limitaciones explícitas: dataset de ejemplo histórico; SCD2 observado y no
reconstrucción temporal de todas las ventas; notas de crédito futuras en cuarentena;
pronóstico de cuatro semanas sin intervalos ni ventaja garantizada sobre baseline;
asistente acotado sin memoria conversacional; canal de alertas exclusivamente web;
ejecución batch local; sin alojamiento público, scheduler ni backup operativo completo
del DW. Estas decisiones están justificadas en los documentos de cada componente.

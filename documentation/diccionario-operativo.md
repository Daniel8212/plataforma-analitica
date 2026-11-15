# Semántica operativa de ML, asistente y alertas

El catálogo exacto de columnas, tipos y nulabilidad se regenera mediante
`python -m deployment.catalog_warehouse`; incluye raw, clean, dw, audit, ml y notify.
Las claves y restricciones están en el DDL versionado de database/.

| Tabla | Identificación | Semántica |
|---|---|---|
| ml.ModelRun | Version; FK ejecución origen | Algoritmo, parámetros, fechas, métricas JSON, artefacto/hashes, versión activa única |
| ml.Prediction | PredictionID; UNIQUE versión/tipo/semana objetivo | Horizonte 1–4, valor decimal, real nullable; predicción separada de hechos de venta |
| audit.ChatRequest | RequestID; FK SourceExecutionID | Hash de pregunta, herramienta, estado, modelo, duración, evaluación, respuesta/bloqueos JSON |
| notify.Task | TaskID; UNIQUE ejecución/regla | Snapshot inmutable por tarea, PENDING/FAILED/SUCCEEDED, intentos, error sanitizado, finalización UTC |
| notify.Evaluation | TaskID PK/FK | TRIGGERED/CLEAR/SKIPPED/SUPERSEDED, fecha y explicación |
| notify.Alert | AlertID; UNIQUE regla/semana/simulación | Severidad, valores, umbral, caída, períodos, carga, evidencia, estado y entrega |
| notify.StateHistory | HistoryID; FK AlertID | Estado anterior/nuevo, fecha UTC; decisiones y resolución/reactivación |

IsSimulated identifica eventos sintéticos. Una tarea/alerta de demo puede referenciar
una carga real y conserva IsSimulated=1; no convierte la carga ni sus ventas en una
simulación. DeliveryStatus DELIVERED significa renderizado con acuse del panel,
no correo ni lectura personal. ATTENDED/DISCARDED son decisiones del operador;
RESOLVED deriva de una nueva evaluación de la misma semana. Una explicación
generativa bloqueada conserva las métricas consultadas y no presenta el texto
crudo como respuesta validada.

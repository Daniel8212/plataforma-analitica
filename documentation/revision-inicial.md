# Revisión del día 1

Estado: completado el primer flujo; publicación y revisión del usuario pendientes.
No iniciar el día 2 sin indicación expresa. Dos commits previstos para esta etapa,
dentro del máximo de ocho para el proyecto completo.

| Punto del cronograma | Resultado comprobado | Dónde revisar |
|---|---|---|
| Leer guía y distinguir obligaciones | 15 páginas revisadas; tecnologías y ocho fases sugeridas; resultados/pruebas obligatorios | requisitos-y-plan.md |
| Inspeccionar y preservar carpeta | Carpeta inicialmente vacía; herramientas y versiones verificadas; dependencias aisladas | avance.md, requirements.lock.txt, frontend/package-lock.json |
| Git, estructura y secretos | Git local en main; carpetas acordadas; .env/backup/dependencias excluidos; staged escaneado contra secretos locales | .gitignore, .env.example, historial Git |
| SQL Server persistente y conexión | SQL 2022 Developer CU28 healthy; puerto solo localhost; conexión ODBC comprobada; imagen por digest | deployment/compose.yaml, evidence/restore.json |
| Fuente oficial OLTP | Backup de Microsoft descargado, hash registrado, VERIFYONLY y restore ONLINE; no se usa su DW | evidence/backup-sha256.txt, deployment/restore.py |
| Inspeccionar tablas y relaciones | Inventario, tipos, claves, fechas, volúmenes y relaciones; RLS diagnosticada y resuelta con autorización | evidence/source-profile.json, erd-fuente.md, diccionario-fuente.md |
| Grano y medidas | Una línea de factura; medidas decimales; impuestos comprobados; sin notas de crédito observadas; grupos de producto M:N excluidos del hecho | modelo-ventas.md |
| Staging y estrella | raw/clean/dw/audit; restricciones, índices, miembros 0 y claves sustitutas; diccionario inicial | database/001_schema.sql, diccionario-analitico.md |
| Inicial, calidad y auditoría | Snapshot por UUID; validación/cuarentena; bloqueo de concurrencia; publicación transaccional; errores registrados | etl-inicial.md, calidad.md, etl/run_initial.py |
| Primer KPI completo | Fuente → raw → clean → DW → API protegida → React en Chrome | evidence/day1-dashboard.png, evidence/browser-smoke.json |
| Reconciliación independiente | Cuatro capas: 228.265 líneas, 70.510 facturas, 172.261.341,20 sin impuestos, 8.950.628 unidades | database/003_validate.sql, evidence/independent-validation.json |
| Pruebas ejecutadas | 3 pruebas de integración aprobadas; Chrome aprobado; repetición sin cambios inserta 0 hechos | pruebas.md, evidence/pytest-initial.xml, evidence/initial-6da8442c-94d2-4d9c-98e9-06718342df80.json |

Todos los importes corresponden a **datos de ejemplo oficiales de Microsoft** (2013–2016).
No se fabricaron cifras para completar la pantalla. La clave demo está en el .env local;
la captura solo muestra caracteres ocultos. Fecha de carga visible en Tegucigalpa, auditoría en UTC.

## Límites de esta revisión

No se implementaron incremental, watermark, SCD2, cinco KPIs/filtros completos, ML, GenAI ni alertas.
La repetición inicial sin cambios no demuestra manejo de actualizaciones ni eliminaciones.
La reconstrucción completa en un entorno limpio se verificará en la etapa final autorizada.
Hay una advertencia no bloqueante de deprecación entre Starlette TestClient y httpx.

Inicio/parada y comandos: README.md en la raíz. SQL Server conserva datos en su volumen.
No se creó remoto GitHub ni se publicó ningún servicio.

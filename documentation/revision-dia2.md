# Revisión del día 2

Fuente principal: WideWorldImporters OLTP. Datos de ejemplo Microsoft, no datos productivos actuales.
No se ha iniciado ML, GenAI ni alertas de la siguiente etapa.

| Requisito | Implementación / evidencia |
|---|---|
| Incremental según fuente | LastEditedWhen de cabecera/línea; solapamiento 48 h; claves nuevas y dimensiones pequeñas completas |
| Watermark solo tras éxito | audit.Watermark se confirma junto con DW y auditoría, en una transacción |
| Actualizaciones y tardíos | Cambios de línea/cabecera y claves nuevas retrodatadas probados; corrección fuera de ventana detectada y reparada con --full |
| Eliminaciones | Hechos conservados como DELETED; audit.Deletion; reaparición recupera la misma clave |
| Idempotencia | Repeticiones sin nuevas inserciones, actualizaciones ni versiones SCD artificiales |
| SCD justificado | Cliente Tipo 2 observado; producto Tipo 1. Se preserva clasificación anterior en hechos y API |
| Falla y recuperación | Después de raw, después de publicar y antes de commit: rollback de hechos, SCD y watermark; reintento único |
| Conteos y auditoría | Leídos por tabla, hechos insertados/actualizados, rechazados, versiones y reconciliación delta/total |
| Permisos separados | ETL carga; API SELECT sobre siete vistas; escritura/raw denegados con código SQL 229 |
| Consultas parametrizadas | Fechas/IDs/paginación vinculados; agrupaciones cerradas; solicitudes inválidas rechazadas con 422 |
| Endpoints | KPIs, comparación, filtros, tendencias, desgloses, detalle, operaciones y rechazos; contratos.md y openapi.json |
| Acceso de demo | Clave en cabecera, solo memoria de sesión; prueba de clave incorrecta y endpoints sin autenticar |
| Cinco KPIs | Ventas sin impuestos, cantidades facturadas, facturas, ticket y variación; contrastados contra SQL independiente |
| Fecha y dos dimensiones | Período inclusivo, producto y categoría de cliente; cuatro combinaciones verificadas |
| Tendencias y comparación | Semana/mes con intervalos parciales; referencia exacta de igual duración y falta de cobertura explícita |
| Resumen a detalle | Navegación desde producto/categoría y tabla paginada con filtros conservados |
| Estados | Última carga, carga en curso de consulta, error con reintento y período sin datos |
| Monitoreo | Últimas 12 ejecuciones, conteos, duración, diagnóstico, watermark y cuarentena paginada |

## Resultados ejecutados

- **42 pruebas** aprobadas: tres originales, doce de incremental/recuperación y 27 de API.
  Reporte unificado: `evidence/pytest-day2.xml`. Advertencia no bloqueante httpx/Starlette.
- **12 comprobaciones** de navegador, incluidos 360/390 px y tablas móviles; capturas en
  `evidence/dashboard-browser.json` y `evidence/day2-*.png`.
- Medición HTTP local por endpoint: aproximadamente 90–434 ms en una solicitud puntual;
  `evidence/api-measurements.json`. No representa benchmark, SLA ni rendimiento de Internet.
- Fuente principal tras pruebas: 228.265 líneas, 172.261.341,20 sin impuestos; marcas originales
  siguen entre 2013-01-01 y 2016-05-31. Cero ejecuciones simuladas en el DW principal.

Cambios operacionales y fallas inyectadas se ejecutaron solo en bases Test aisladas con
IsSimulated=1. El error de consulta visual es una intercepción local declarada: no se detuvo SQL Server.

## Límites y operación

SCD2 registra conocimiento observado; no reconstruye la categoría efectiva de facturas históricas.
Sin CDC, una corrección con marca arbitrariamente antigua exige reconciliación completa;
el sistema detecta la diferencia y no avanza watermark. La verificación global lee todas las claves
y medidas para priorizar fiabilidad con este volumen. Ejecución batch bajo demanda, no tiempo real.

No se añadieron Airflow, mensajería ni servicios externos. Todo sigue local y sin presupuesto.
Para iniciar, detener o reintentar: README.md, dashboard.md e incremental-y-scd.md.
Quedan etapas posteriores y validación final de reconstrucción limpia; no se declaran completadas.
El catálogo de calidad mantiene pendiente Q10 (detección estadística de outliers), a completar
con perfilado ML/validación final; no se declara implementado en esta etapa.

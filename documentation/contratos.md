# Contratos iniciales

## GET /api/kpis

Acceso: cabecera `X-API-Key`; clave solo en memoria del navegador, nunca en URL ni bundle.
Usuario SQL de lectura sobre vistas aprobadas. No devuelve nombres de personas, direcciones
ni otros datos personales. El error de BD se traduce a mensaje genérico sin credenciales.

Respuesta inicial prevista:

| Campo | Tipo | Significado |
|---|---|---|
| sales | decimal serializado | SUM(SalesAmount), validado contra Quantity × UnitPrice y ExtendedPrice − TaxAmount en fuente |
| invoice_count | entero | Facturas distintas en el conjunto de líneas válidas |
| first_date / last_date | fecha o null | Cobertura real del conjunto consultado |
| loaded_at | fecha/hora UTC o null | Última ejecución confirmada |
| execution_id | UUID o null | Ejecución que respalda el indicador |

No interpretar un fallo de conexión como ventas cero. Sin carga exitosa debe mostrarse
ausencia de datos o indisponibilidad, nunca un KPI construido con ejemplos.

El endpoint está implementado; faltan carga válida y prueba de integración positiva.
La fuente inspeccionada no contiene notas de crédito; las futuras se ponen en cuarentena
hasta verificar semántica. No se presenta esta medida como neta de devoluciones.

## Convenciones operativas

- Tiempo de auditoría: UTC, diferenciándolo de fechas de negocio de la fuente.
- Importes: decimal SQL; no usar float para reconciliación.
- Identificación de origen: base, esquema, tabla y clave natural más execution_id.
- Cada ejecución deja estado RUNNING/SUCCEEDED/FAILED y detalle sanitizado.
- Raw inmutable por ejecución; clean y DW no se publican parcialmente.
- El watermark no avanza por una carga fallida.
- Tabla de rechazo con regla y contexto; rechazos deben explicar diferencias de reconciliación.

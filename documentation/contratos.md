# API y contratos de datos

## Acceso y convenciones

Acceso: cabecera `X-API-Key`; clave solo en memoria del navegador, nunca en URL ni bundle.
Usuario SQL de lectura sobre vistas aprobadas. No devuelve nombres de personas, direcciones
ni otros datos personales. El error de BD se traduce a mensaje genérico sin credenciales.

API local `http://127.0.0.1:8000`; React usa el proxy `/api` de Vite, sin conexión directa a SQL.
Documentación ejecutable: `/docs`; contrato exportado en `openapi.json`.
`/api/health` solo comprueba que el proceso responde. Todos los endpoints analíticos exigen la clave.

Las consultas solo usan siete vistas aprobadas, no tablas raw ni la base operacional. Los valores
se parametrizan; las agrupaciones posibles proceden de una lista cerrada. La cuenta API no puede
escribir en el DW; se comprobó denegación SQL 229. No se ejecuta SQL enviado por el usuario.

Filtros comunes: `start`/`end` ISO YYYY-MM-DD inclusivos, `product_id` y `category_id` enteros positivos.
Sin fechas se consulta toda la cobertura; el dashboard elige inicialmente los últimos 90 días de
la muestra, anclados en 2016-05-31, no en el día actual. Rango máximo: 3661 días, años 1900–2099.
IDs de dimensión limitados al rango int de SQL Server; entradas inválidas reciben 422.

## Endpoints

| Método/ruta | Resultado | Parámetros adicionales |
|---|---|---|
| GET /api/filters | Cobertura, carga, productos y categorías | Ninguno |
| GET /api/kpis | Cinco KPIs, cobertura y período de referencia | Filtros comunes |
| GET /api/comparison | Actual, anterior, variación y comparabilidad | Filtros comunes |
| GET /api/trends | Series con marcas de intervalos parciales | grain=week o month |
| GET /api/breakdown | Ventas por producto o categoría de cliente | dimension=product/customer_category; limit 1–20 |
| GET /api/dashboard | KPIs, tendencia y desgloses en una lectura consistente | Filtros y grain |
| GET /api/detail | Líneas paginadas, cantidad total y ejecución | page 1–100000; page_size 1–100 |
| GET /api/operations | Últimas 12 ejecuciones, rechazos por regla, watermark | Ninguno |
| GET /api/rejections | Detalle paginado sin JSON original | execution_id UUID opcional; page y page_size |

Las respuestas compuestas leen bajo una transacción serializable para no mezclar estados del DW
dentro de la misma respuesta. Código 401: falta clave válida. Código 422: solicitud inválida.
Código 503: SQL no disponible/permisos incorrectos, con texto genérico sin credenciales ni SQL.

## Contrato de KPIs

| Campo | Tipo | Significado |
|---|---|---|
| sales | decimal serializado | SUM(SalesAmount), validado contra Quantity × UnitPrice y ExtendedPrice − TaxAmount en fuente |
| invoice_count | entero | Facturas distintas en el conjunto de líneas válidas |
| units / line_count | entero | Cantidades facturadas / líneas activas |
| average_ticket | decimal serializado o null | Ventas / facturas; null si no hay facturas |
| variation_pct | decimal serializado o null | (ventas actuales / anteriores − 1) × 100 |
| period / previous | objeto | Fechas exactas y medidas de ambos períodos |
| is_comparable / comparison_reason | booleano / texto o null | Cobertura completa y explicación de referencia no válida |
| first_date / last_date | fecha o null | Cobertura real del conjunto consultado |
| loaded_at | fecha/hora UTC o null | Última ejecución confirmada |
| execution_id | UUID o null | Ejecución que respalda el indicador |

No interpretar un fallo de conexión como ventas cero. Sin carga exitosa debe mostrarse
ausencia de datos o indisponibilidad, nunca un KPI construido con ejemplos.

Los KPIs y combinaciones de filtros se validaron con SQL operacional independiente.
Para futuras clasificaciones modificadas, el filtro usa la categoría observada en el hecho,
no reclasifica la venta histórica con la categoría actual. Esto se probó también desde la API
sobre el fixture SCD2. No sumar ratios ni facturas de grupos que pueden superponerse.

La referencia es el mismo número de días inmediatamente anterior, con los mismos filtros.
No se calcula porcentaje si falta cobertura de cualquiera de los períodos o la base es cero.
Las cantidades son unidades de facturación de la fuente; no se convierten paquetes a unidades físicas.
Tendencias rellenan ceros solo dentro de la cobertura cargada y marcan intervalos parciales.
La fuente inspeccionada no contiene notas de crédito; las futuras se ponen en cuarentena
hasta verificar semántica. No se presenta esta medida como neta de devoluciones.

## Contratos añadidos en la tercera etapa

- GET `/api/forecast`: versión activa, corte, entrenamiento/validación/prueba,
  métricas/baselines, histórico, predicciones y advertencia de reentrenamiento.
- POST `/api/chat`: cuerpo question (3–500 caracteres), sin campos adicionales;
  respuesta answer, generated, facts, dataset, verification, request_id y duración.
  429 por frecuencia y 503 si proveedor local no disponible; no fallback de pago.
- GET `/api/alerts`: hasta 100 alertas y 20 tareas recientes, incluida simulación,
  períodos, importes, estados, entrega y diagnósticos.
- POST `/api/alerts/{uuid}/seen`: acuse idempotente de renderizado en panel.
- POST `/api/alerts/{uuid}/state`: state ATTENDED/DISCARDED; una RESOLVED no cambia
  por esta ruta. Respuesta changed indica si hubo transición.

Todas requieren X-API-Key. Identificadores UUID y estados están validados por
FastAPI/Pydantic; el lector SQL no escribe. Modelos, runtime y secretos no se sirven
desde rutas web. OpenAPI actualizado: openapi.json. Detalles en machine-learning/ML.md,
generative-ai/GENAI.md y notifications/README.md.

## Convenciones operativas

- Tiempo de auditoría: UTC, diferenciándolo de fechas de negocio de la fuente.
- Importes: decimal SQL; no usar float para reconciliación.
- Identificación de origen: base, esquema, tabla y clave natural más execution_id.
- Cada ejecución deja estado RUNNING/SUCCEEDED/FAILED y detalle sanitizado.
- Raw inmutable por ejecución; clean es staging durable; DW se publica de forma atómica.
- El watermark no avanza por una carga fallida.
- Tabla de rechazo con regla y contexto; rechazos deben explicar diferencias de reconciliación.

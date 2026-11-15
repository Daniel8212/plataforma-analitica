# Guion de video — cinco minutos

Guion final basado en resultados ejecutados. Video todavía no grabado.
Grabar el sistema real; ocultar claves, terminales con secretos y `.env`.

| Tiempo | Narración y acción | Evidencia necesaria |
|---|---|---|
| 0:00–0:40 | Presentar problema de ventas y arquitectura fuente → raw → clean → DW → API → aplicación. Explicar ejecución local sin costo de alojamiento. | Diagrama editable, versiones y alcance |
| 0:40–1:30 | Ejecutar lote reproducible. Mostrar ID, conteos y una regla de calidad, indicando expresamente si el caso de rechazo fue inyectado para demo. | Log real y registro de cuarentena |
| 1:30–2:15 | Mostrar grano de línea de factura, dimensiones y reconciliación independiente de importe/conteos. | Modelo dimensional y SQL con resultado |
| 2:15–3:00 | Abrir panel, usar fecha y dos filtros, comparar períodos y navegar al detalle. | KPIs validados y fecha de carga |
| 3:00–3:45 | Distinguir histórico y predicción. Mostrar baseline, métrica de prueba y versión del modelo; explicar una limitación concreta. | Artefacto, evaluación y predicciones persistidas |
| 3:45–4:25 | Preguntar al asistente y comprobar las métricas/períodos que cita. Mostrar que reconoce una pregunta sin respaldo. | Respuesta real y consulta controlada |
| 4:25–5:00 | Disparar alerta de prueba identificada como simulación, mostrar estado y referencia; explicar brevemente reintento seguro y cerrar con qué funciona. | Evento, entrega web, deduplicación y procedimiento de recuperación |

Antes de grabar: verificar que los siete bloques funcionan, preparar ventanas legibles,
limpiar información sensible de la pantalla y ensayar para respetar el límite docente.
No hay video grabado todavía.

## Preparación antes de grabar

1. Iniciar SQL/API/Vite/Ollama según operacion.md y comprobar las seis secciones.
2. Ejecutar deployment.demo_lot antes de la toma: siete casos con reportes reales
   en data/demo-<UTC>/. No provocar una falla en la base principal para el video.
3. Abrir documentación de arquitectura/estrella, terminal en raíz y aplicación ya
   autenticada. Cerrar .env y cualquier ventana con claves. Mantener texto legible.
4. Dejar preparados los comandos etl.run_incremental, deployment.validate_initial
   y notifications.demo --simulate, siempre con el Python de .venv.
5. Regenerar ERD/modelo desde las fuentes corregidas si se mostrarán sus PNG;
   mientras tanto, el modelo documenta FactSalesKey PK y la fuente .mmd es editable.
6. Probar diez segundos de captura con micrófono, reproducir para comprobar audio
   y encuadre. La prueba no equivale al video final. Usar la herramienta de captura
   disponible del autor; no se instala ni publica un servicio para grabar.

## Narración sugerida por segmento

### 0:00–0:40 — Caso y arquitectura

«Esta plataforma integra ingeniería de datos y analítica para ventas facturadas.
Utilizo WideWorldImporters, la muestra operacional oficial de Microsoft, con datos
entre 2013 y 2016. No son ventas actuales de una empresa. La fuente está separada
del Data Warehouse en SQL Server. Python lleva los datos por raw y clean hasta una
estrella dimensional; FastAPI entrega la información a React. Sobre el mismo DW
se integran pronóstico, asistente local y alertas. Todo funciona localmente, sin
alojamiento externo ni API de pago.»

Acción: mostrar arquitectura y abrir terminal preparada. No explicar cada herramienta
en detalle; el objetivo es que se vea el recorrido integrado.

### 0:40–1:30 — ETL y calidad

«Ejecuto una carga incremental real. Cada ejecución conserva sus originales e
identificador. En clean se verifican claves, relaciones, nulos, cantidades e importes;
lo inválido queda en cuarentena. La publicación del DW y el watermark se confirman
juntos después de reconciliar. Como la fuente no cambió, esta repetición inserta y
actualiza cero hechos: es idempotente. Antes probé correcciones, registros tardíos,
rechazos y tres puntos de falla en bases aisladas. Si falla la publicación, se
conservan originales y el watermark anterior; después de corregir se reintenta.»

Acción: `python -m etl.run_incremental` con Python de .venv, mostrar ID/estado/conteos.
Breve referencia al reporte del lote simulado, sin presentarlo como cambio real del negocio.

### 1:30–2:15 — Modelo y validación

«El grano es una línea de factura, identificada de forma única por InvoiceLineID.
El hecho tiene su propia clave primaria FactSalesKey y se relaciona con fecha,
producto y cliente. Cliente conserva historia Tipo 2 observada; no invento atributos
históricos anteriores a la observación. Esta consulta independiente compara fuente,
raw, clean y DW: coinciden 228.265 líneas y 172.261.341,20 de ventas sin impuestos.
Los impuestos se mantienen separados y no afirmo ventas netas de devoluciones,
porque no se observaron notas de crédito en esta muestra.»

Acción: estrella/fuentes corregidas, después `python -m deployment.validate_initial`.

### 2:15–3:00 — Dashboard

«El dashboard consulta el DW mediante la API. Muestra ventas, unidades, facturas,
ticket promedio y variación. Aplico un período, producto y categoría de cliente;
los indicadores y tendencias responden al mismo filtro. La comparación identifica
exactamente el período anterior y evita porcentajes cuando no hay referencia válida.
Desde un producto puedo abrir las líneas que respaldan el resumen y paginar.
La fecha de actualización y el monitoreo permiten distinguir los datos vigentes
de errores o cargas fallidas.»

Acción: filtros preparados, aplicar y navegar de resumen a detalle. Evitar esperar a
que el espectador lea tablas completas.

### 3:00–3:45 — Machine Learning

«El pronóstico usa 177 semanas completas del DW; excluye dos intervalos parciales.
Entrenamiento, validación y prueba están separados cronológicamente, con variables
sin información futura. Ridge fue seleccionado por validación. En prueba obtuvo
un MAE de 113.773,87 y un sMAPE de 10,99 %. El baseline de última semana tuvo un MAE
ligeramente menor: no afirmo superioridad del modelo. Se guardan versión, parámetros,
artefactos y cuatro predicciones. La aplicación distingue previsto de observado;
el corte es mayo de 2016, no el calendario actual.»

Acción: pestaña Pronóstico, métricas, versión, corte y línea prevista.

### 3:45–4:25 — Asistente

«El asistente usa Ollama local con Qwen2.5. Pregunto por ventas de marzo de 2016:
la tabla muestra 4.645.254,00, su período y carga de origen. Las cifras vienen de
herramientas autorizadas, no de cálculos del modelo. No ejecuta SQL generado.
Si una explicación no supera los controles, se bloquea y permanecen las métricas.
Al preguntar por ventas de 2030 reconoce que no hay cobertura. La evaluación
registró catorce preguntas y sus respaldos, incluidos casos sin información.»

Acción: enviar la pregunta soportada, mostrar tabla y luego consultar 2030. Dejar
tiempo para la respuesta real del proveedor; no reemplazarla por texto preparado.

### 4:25–5:00 — Alerta, recuperación y conclusión

«La regla compara semanas completas y alerta por una caída mayor al quince por
ciento. Este evento del treinta y cinco por ciento es una simulación identificada;
no modifica las ventas. Se guardan referencia, umbral, origen, estado y entrega al
panel. Repetir no duplica la alerta. Si falla el evaluador, se reintenta su tarea sin
repetir una carga confirmada. Queda integrado el recorrido desde la fuente hasta
indicadores, predicción, asistente y alerta, con pruebas y documentación reproducibles.»

Acción: ejecutar `python -m notifications.demo --simulate`, actualizar Alertas y
mostrar SIMULACIÓN, referencia, entrega y estado. Si ya existía, explicar que se
reutiliza por deduplicación. Cerrar con aplicación visible.

## Comprobación del archivo final

- Duración objetivo 5:00; ajustar ensayo y pausas al límite del docente.
- Audio entendible y texto legible; ejecución real visible, no solo diapositivas.
- Sin contraseñas, tokens, .env ni información personal ajena al proyecto.
- Evento simulado identificado en voz y pantalla; no afirmar predicción para 2026.
- Conclusión breve incluida en los últimos segundos.
- Reproducir el archivo completo y verificar que no quedó una pantalla negra o una
  toma cortada. Guardar el video fuera de Git y entregarlo por el medio del docente;
  no se sube automáticamente ni se agrega un binario grande al repositorio.

Estado: guion y secuencia preparados; ensayo con narración, grabación, revisión del
archivo y entrega del video pendientes del autor. El repositorio no declara esos
pasos como completados.

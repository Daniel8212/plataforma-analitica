# Revisión de las imágenes del autor

Revisadas cinco exportaciones PNG y sus enlaces Markdown; archivos conservados.
Las fuentes .mmd independientes permiten editar sin modificar los PNG del autor.

| Imagen | Revisión |
|---|---|
| Arquitectura - Diagrama.png | Representa correctamente los componentes. Vista conceptual: el detalle de tarea/snapshot de alertas está en diagramas/alertas.mmd. Muy ancha; abrir/usar zoom para leer en presentación |
| ERD -  DIAGRAM.png | Tablas/FK seleccionadas correctas; corregir extremo padre opcional a exactamente uno en las ocho relaciones. Todas las FK mostradas son NOT NULL según catálogo inspeccionado |
| ETL - DIAGRAM.png | Coherente con el primer flujo histórico, como indica etl-inicial.md. Fondo oscuro con flechas negras de bajo contraste; conviene exportar con fondo claro. Para flujo actual usar el incremental |
| incremental-y-scd - Diagrama.png | Correcto para publicación/SCD/watermark y rollback. La tarea de alerta añadida al commit se explica en notifications/README.md. Es un diagrama alto: presentar por segmentos |
| modelo-ventas - Diagrama.png | Estrella y claves dimensionales correctas; falta FactSalesKey bigint PK física. InvoiceLineID es UK de la clave natural. Es un resumen, no lista exhaustiva de columnas |

Las dos diferencias técnicas proceden del Mermaid original generado durante las
primeras etapas. Se corrigieron erd-fuente.mmd y modelo-ventas.mmd; no se atribuyen
a la exportación del usuario. Para actualizar imágenes, regenerar desde esos archivos.
Mientras se conservan las exportaciones iniciales, los documentos principales aclaran
la cardinalidad y la PK físicas. No se alteró el esquema de datos por esta revisión.

Prioridad para la entrega: regenerar ERD y modelo desde fuentes corregidas. Mejoras
visuales opcionales: mayor contraste del ETL y zoom/segmentación al presentar dibujos
largos. Las fuentes editables y el DDL siguen siendo la referencia verificable.

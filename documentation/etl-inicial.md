# Carga inicial y operación

Referencia del cierre del primer flujo. Desde la segunda etapa `etl.run_initial` usa el mismo
motor que el incremental; transacciones y política actuales en incremental-y-scd.md.
El diagrama siguiente documenta la primera implementación, no sustituye el manual vigente.

## Flujo editable

![alt text](<ETL - DIAGRAM.png>)

Python y SQLAlchemy/pyodbc coordinan extracción y transformación SQL en una instancia.
La fuente está en otra base; no se usa el DW preconstruido de Microsoft.
Las proyecciones originales del alcance quedan sin transformación en raw, identificadas por UUID.
Se conservan cinco entidades: facturas, líneas, clientes, categorías de cliente y productos.
No se extraen direcciones, teléfonos, fotografías ni columnas ajenas al análisis de ventas.
El backup oficial conserva la fuente completa y no se versiona.

## Reglas implementadas

- Claves raw únicas por ejecución; cualquier duplicidad inesperada falla por restricción.
- Integridad de factura, cliente/categoría y producto mediante joins con las claves reales.
- Precio no nulo, cantidad positiva, precio/impuesto/tasa no negativos y nombres no vacíos.
- Coherencia exacta cantidad × precio + impuesto = importe extendido.
- Notas de crédito futuras en cuarentena hasta confirmar signos; no hay ninguna en el backup.
- Espacios exteriores de nombres y marca se limpian solo en clean; marca nula se conserva.
- Cuarentena con fuente, clave, regla, detalle, fecha UTC, original JSON y ejecución.
- Base/impuesto/total con decimal; no usar float en reconciliación.
- Calendario entre fechas mínimas/máximas, miembros desconocidos 0 y claves sustitutas.
- Hechos nuevos por InvoiceLineID único. La repetición completa sin cambios no duplica hechos.

La carga inicial no procesa actualizaciones o eliminaciones: detecta discrepancias con hechos
existentes y falla, o falla reconciliación ante desapariciones. No se presenta como incremental.
SCD2, watermark, tardíos, programación y recuperación de cambios quedan para la siguiente etapa,
que no se iniciará sin indicación del usuario.

## Fallas y reinicio

Si falla extracción, su transacción se revierte y la ejecución queda FAILED. Si falla publicación,
raw permanece y clean/DW de esa transacción se revierten. Repetir crea otro UUID y otro snapshot
raw; no reutiliza el lote fallido. Los originales no se actualizan ni eliminan por el extractor.
Las conexiones de carga se serializan con sp_getapplock; no hay carga concurrente sobre el mismo DW.

Diagnóstico real resuelto: RLS de clientes devolvía cero filas a ETL. El usuario autorizó los nueve
roles territoriales de la muestra; no se desactivó la política ni se otorgó db_owner. El control
de cobertura impide aceptar una carga con hechos existentes y dimensiones totalmente invisibles.

Procedimiento normal, desde raíz PowerShell:

```powershell
docker compose --env-file .env -f deployment/compose.yaml up -d
.\.venv\Scripts\python.exe -m etl.run_initial
.\.venv\Scripts\python.exe -m deployment.validate_initial
.\.venv\Scripts\python.exe -m pytest tests/test_initial_integration.py -q
```

Para consultar ejecuciones con la cuenta de carga:

```sql
SELECT ExecutionID,StartTime,EndTime,Status,RowsRead,RowsInserted,RowsUpdated,RowsRejected,ErrorDetail
FROM audit.Execution ORDER BY StartTime DESC;
SELECT * FROM audit.StageCount ORDER BY ExecutionID,Stage,TargetObject;
SELECT ExecutionID,RuleID,COUNT_BIG(*) AS Rejected FROM audit.Quarantine GROUP BY ExecutionID,RuleID;
SELECT * FROM audit.Reconciliation ORDER BY ExecutionID,Layer;
```

La publicación está completa cuando DW coincide con el conjunto clean aceptado y clean más
cuarentena explica source/raw. El script independiente contrasta además cantidad × precio en
OLTP con importe menos impuesto en raw y la medida de clean/DW para la muestra sin rechazos.

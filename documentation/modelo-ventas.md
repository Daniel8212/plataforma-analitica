# Modelo de ventas — decisión tras inspección

Fuente restaurada: WideWorldImporters OLTP oficial, 70.510 facturas y 228.265 líneas.
Cobertura: 2013-01-01 a 2016-05-31. Evidencia: `evidence/source-profile.json`.

## Grano, alcance y medidas

Una fila por `Sales.InvoiceLines.InvoiceLineID`; `InvoiceID` es dimensión degenerada.
La FK de línea apunta a una factura; la factura identifica cliente y fecha; la línea identifica producto.
Dimensiones iniciales: fecha, cliente (categoría incorporada) y producto (marca y frío incorporados).
StockGroups es muchos-a-muchos (hay productos con tres grupos), por lo que queda fuera del join del hecho.
Filtros previstos: producto y categoría de cliente, además de fecha.

| Medida/KPI | Fórmula | Unidad / aditividad |
|---|---|---|
| Ventas facturadas sin impuestos | SUM(ExtendedPrice - TaxAmount) | Moneda de origen; aditiva |
| Unidades | SUM(Quantity) | Unidades facturadas; aditiva |
| Facturas | COUNT(DISTINCT InvoiceID) en líneas filtradas | Documentos; no sumar subtotales dimensionales |
| Ticket medio | Ventas / facturas; NULL si denominador cero | Moneda/documento; no aditiva |
| Variación | (Ventas actual / Ventas anterior - 1) × 100 | %; NULL si referencia cero o no comparable |

Responsable de definiciones: autor individual del proyecto. Fuente de consumo: DW, nunca OLTP desde UI.
Período anterior: mismo número de días inmediatamente anteriores al filtro inclusivo; identificar
fechas exactas y cobertura disponible. Para alerta/ML se usarán semanas completas comparables.

En el conjunto observado `ExtendedPrice = ROUND(Quantity × UnitPrice,2) + TaxAmount` en todas
las líneas; base 172.261.341,20, impuesto 25.782.098,25, total 198.043.439,45 y 8.950.628 unidades.
No hay descuentos de línea explícitos ni notas de crédito observadas. No descontar el porcentaje
comercial actual del cliente de un importe ya facturado. No afirmar ventas netas de devoluciones.
Las notas de crédito futuras requieren verificar semántica de signo antes de admitirse; se pondrán
en cuarentena bajo regla explícita hasta validar ese caso. Moneda sin código en la línea: no inventar USD.

## Diseño dimensional editable

```mermaid
erDiagram
  DimDate ||--o{ FactSales : DateKey
  DimCustomer ||--o{ FactSales : CustomerKey
  DimProduct ||--o{ FactSales : ProductKey
  DimDate {
    int DateKey PK
    date FullDate UK
    int Year
    int Month
    int Quarter
    int IsoWeek
  }
  DimCustomer {
    int CustomerKey PK
    int CustomerID
    string CustomerName
    string CustomerCategory
  }
  DimProduct {
    int ProductKey PK
    int StockItemID UK
    string ProductName
    string Brand
    boolean IsChillerStock
  }
  FactSales {
    int InvoiceLineID UK
    int InvoiceID
    int DateKey FK
    int CustomerKey FK
    int ProductKey FK
    int Quantity
    decimal SalesAmount
    decimal TaxAmount
    decimal ExtendedPrice
    uuid ExecutionID
  }
```

Claves sustitutas en dimensiones; naturales conservadas; miembro 0 desconocido.
Fecha con clave YYYYMMDD y miembro 0. La carga inicial representa atributos del snapshot actual,
sin afirmar que reconstruye el estado histórico de cada factura. En fiabilidad se añadirá SCD2
justificada para categoría de cliente, aprovechando las columnas temporales `ValidFrom/ValidTo`
si el historial inspeccionado lo permite. No inventar historia anterior a la observación.

La muestra proporciona más de tres años para evaluar viabilidad semanal; aún falta revisar
semanas incompletas, cobertura y calidad. No hay modelo ni pronóstico validado todavía.

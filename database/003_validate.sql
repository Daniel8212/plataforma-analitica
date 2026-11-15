-- Validación independiente. El parámetro execution_id identifica la carga inicial aceptada.
SELECT 'source' AS layer,COUNT_BIG(*) AS line_count,COUNT(DISTINCT InvoiceID) AS invoice_count,
 SUM(CONVERT(decimal(18,2),Quantity*UnitPrice)) AS sales,SUM(CONVERT(bigint,Quantity)) AS units
FROM WideWorldImporters.Sales.InvoiceLines
UNION ALL
SELECT 'raw',COUNT_BIG(*),COUNT(DISTINCT InvoiceID),SUM(ExtendedPrice-TaxAmount),SUM(CONVERT(bigint,Quantity))
FROM raw.InvoiceLines WHERE ExecutionID=:execution_id
UNION ALL
SELECT 'clean',COUNT_BIG(*),COUNT(DISTINCT InvoiceID),SUM(SalesAmount),SUM(CONVERT(bigint,Quantity))
FROM clean.SalesLine WHERE ExecutionID=:execution_id
UNION ALL
SELECT 'dw',COUNT_BIG(*),COUNT(DISTINCT InvoiceID),SUM(SalesAmount),SUM(CONVERT(bigint,Quantity))
FROM dw.FactSales;

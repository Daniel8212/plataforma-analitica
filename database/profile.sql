-- Ejecutar contra WideWorldImporters. Consultas de perfilado, sin modificar fuente.
SELECT s.name AS schema_name,t.name AS table_name,p.rows AS row_count
FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
JOIN sys.partitions p ON p.object_id=t.object_id AND p.index_id IN (0,1)
ORDER BY s.name,t.name;
GO
SELECT s.name AS schema_name,t.name AS table_name,c.column_id,c.name AS column_name,
 ty.name AS data_type,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity
FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
JOIN sys.columns c ON c.object_id=t.object_id JOIN sys.types ty ON ty.user_type_id=c.user_type_id
WHERE (s.name='Sales' AND t.name IN ('Invoices','InvoiceLines','Customers','CustomerCategories'))
OR (s.name='Warehouse' AND t.name IN ('StockItems','StockGroups','StockItemStockGroups'))
ORDER BY s.name,t.name,c.column_id;
GO
SELECT fk.name AS fk_name,OBJECT_SCHEMA_NAME(fk.parent_object_id) AS source_schema,
 OBJECT_NAME(fk.parent_object_id) AS source_table,pc.name AS source_column,
 OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS target_schema,
 OBJECT_NAME(fk.referenced_object_id) AS target_table,rc.name AS target_column
FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fc ON fk.object_id=fc.constraint_object_id
JOIN sys.columns pc ON pc.object_id=fc.parent_object_id AND pc.column_id=fc.parent_column_id
JOIN sys.columns rc ON rc.object_id=fc.referenced_object_id AND rc.column_id=fc.referenced_column_id
WHERE OBJECT_SCHEMA_NAME(fk.parent_object_id) IN ('Sales','Warehouse')
ORDER BY source_schema,source_table,fk.name;
GO
SELECT MIN(InvoiceDate) AS first_date,MAX(InvoiceDate) AS last_date,COUNT_BIG(*) AS invoices,
 COUNT(DISTINCT CustomerID) AS customers, SUM(CASE WHEN IsCreditNote=1 THEN 1 ELSE 0 END) AS credit_notes,
 MIN(LastEditedWhen) AS first_edit,MAX(LastEditedWhen) AS last_edit
FROM Sales.Invoices;
GO
SELECT COUNT_BIG(*) AS lines,COUNT(DISTINCT InvoiceLineID) AS distinct_ids,
 MIN(Quantity) AS min_qty,MAX(Quantity) AS max_qty,MIN(UnitPrice) AS min_price,MAX(UnitPrice) AS max_price,
 SUM(ExtendedPrice) AS extended_total,SUM(TaxAmount) AS tax_total,
 SUM(CONVERT(decimal(19,2),Quantity*UnitPrice)) AS quantity_price_total,
 SUM(CASE WHEN ExtendedPrice<>ROUND(Quantity*UnitPrice,2)+TaxAmount THEN 1 ELSE 0 END) AS formula_mismatches,
 SUM(CASE WHEN Quantity<0 THEN 1 ELSE 0 END) AS negative_qty,
 SUM(CASE WHEN UnitPrice=0 THEN 1 ELSE 0 END) AS zero_price,
 MIN(LastEditedWhen) AS first_edit,MAX(LastEditedWhen) AS last_edit
FROM Sales.InvoiceLines;
GO
SELECT i.IsCreditNote,COUNT_BIG(*) AS lines,SUM(l.Quantity) AS quantity,
 SUM(l.ExtendedPrice) AS extended_total,SUM(l.TaxAmount) AS tax_total
FROM Sales.InvoiceLines l JOIN Sales.Invoices i ON i.InvoiceID=l.InvoiceID GROUP BY i.IsCreditNote;
GO
SELECT COUNT_BIG(*) AS orphan_invoices FROM Sales.InvoiceLines l
LEFT JOIN Sales.Invoices i ON i.InvoiceID=l.InvoiceID WHERE i.InvoiceID IS NULL;
GO
SELECT TOP (10) StockItemID,COUNT(*) AS groups_count FROM Warehouse.StockItemStockGroups
GROUP BY StockItemID HAVING COUNT(*)>1 ORDER BY groups_count DESC;

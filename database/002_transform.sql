-- Referencia histórica del primer flujo. El pipeline actual usa 006_validate_batch.sql y 005_publish.sql.
SET NOCOUNT ON;
SET XACT_ABORT ON;
INSERT audit.Quarantine(ExecutionID,SourceObject,SourceKey,RuleID,Detail,OriginalRecord)
SELECT :execution_id,'Sales.InvoiceLines',v.InvoiceLineID,v.FailedRule,
 N'Registro excluido del conjunto analítico; consultar regla y original',
 (SELECT r.InvoiceLineID,r.InvoiceID,r.StockItemID,r.Description,r.Quantity,r.UnitPrice,r.TaxRate,
 r.TaxAmount,r.LineProfit,r.ExtendedPrice,r.LastEditedWhen FOR JSON PATH,WITHOUT_ARRAY_WRAPPER)
FROM clean.vCandidateSales v JOIN raw.InvoiceLines r
 ON r.ExecutionID=v.ExecutionID AND r.InvoiceLineID=v.InvoiceLineID
WHERE v.ExecutionID=:execution_id AND v.FailedRule IS NOT NULL;

INSERT clean.SalesLine(ExecutionID,InvoiceLineID,InvoiceID,InvoiceDate,CustomerID,StockItemID,
 CustomerName,CustomerCategoryID,CustomerCategory,ProductName,Brand,IsChillerStock,
 Quantity,UnitPrice,SalesAmount,TaxAmount,ExtendedPrice,LineProfit)
SELECT ExecutionID,InvoiceLineID,InvoiceID,InvoiceDate,CustomerID,StockItemID,
 LTRIM(RTRIM(CustomerName)),CustomerCategoryID,LTRIM(RTRIM(CustomerCategoryName)),
 LTRIM(RTRIM(StockItemName)),LTRIM(RTRIM(Brand)),IsChillerStock,
 Quantity,UnitPrice,CONVERT(decimal(18,2),Quantity*UnitPrice),TaxAmount,ExtendedPrice,LineProfit
FROM clean.vCandidateSales WHERE ExecutionID=:execution_id AND FailedRule IS NULL;

;WITH Calendar AS (
 SELECT MIN(InvoiceDate) AS CalendarDate,MAX(InvoiceDate) AS LastDate FROM clean.SalesLine WHERE ExecutionID=:execution_id
 UNION ALL
 SELECT DATEADD(day,1,CalendarDate),LastDate FROM Calendar WHERE CalendarDate<LastDate
)
INSERT dw.DimDate(DateKey,FullDate,Year,Month,Quarter,IsoWeek,IsWeekend)
SELECT CONVERT(int,CONVERT(char(8),CalendarDate,112)),CalendarDate,YEAR(CalendarDate),MONTH(CalendarDate),
 DATEPART(quarter,CalendarDate),DATEPART(iso_week,CalendarDate),
 CASE WHEN DATEDIFF(day,'19000101',CalendarDate)%7>=5 THEN 1 ELSE 0 END
FROM Calendar WHERE CalendarDate IS NOT NULL
 AND NOT EXISTS(SELECT 1 FROM dw.DimDate WHERE FullDate=CalendarDate) OPTION(MAXRECURSION 0);

-- Este recorrido inicial admite repetición sin cambios. Actualizaciones se habilitan en la etapa incremental.
IF EXISTS(SELECT 1 FROM clean.SalesLine s JOIN dw.FactSales f ON f.InvoiceLineID=s.InvoiceLineID
 WHERE s.ExecutionID=:execution_id AND (s.SalesAmount<>f.SalesAmount OR s.Quantity<>f.Quantity
 OR s.InvoiceID<>f.InvoiceID OR s.TaxAmount<>f.TaxAmount OR s.ExtendedPrice<>f.ExtendedPrice
 OR s.UnitPrice<>f.UnitPrice OR s.LineProfit<>f.LineProfit
 OR NOT EXISTS(SELECT 1 FROM dw.DimDate d WHERE d.DateKey=f.DateKey AND d.FullDate=s.InvoiceDate)
 OR NOT EXISTS(SELECT 1 FROM dw.DimCustomer c WHERE c.CustomerKey=f.CustomerKey AND c.CustomerID=s.CustomerID
   AND c.CustomerName=s.CustomerName AND c.CustomerCategoryID=s.CustomerCategoryID AND c.CustomerCategory=s.CustomerCategory)
 OR NOT EXISTS(SELECT 1 FROM dw.DimProduct p WHERE p.ProductKey=f.ProductKey AND p.StockItemID=s.StockItemID
   AND p.ProductName=s.ProductName AND ISNULL(p.Brand,N'')=ISNULL(s.Brand,N'') AND p.IsChillerStock=s.IsChillerStock)))
 THROW 51000,'Cambio detectado: esta carga inicial no implementa actualizaciones; usar la etapa incremental.',1;

INSERT dw.DimCustomer(CustomerID,CustomerName,CustomerCategoryID,CustomerCategory)
SELECT DISTINCT s.CustomerID,s.CustomerName,s.CustomerCategoryID,s.CustomerCategory FROM clean.SalesLine s
WHERE s.ExecutionID=:execution_id AND NOT EXISTS(SELECT 1 FROM dw.DimCustomer d WHERE d.CustomerID=s.CustomerID);
INSERT dw.DimProduct(StockItemID,ProductName,Brand,IsChillerStock)
SELECT DISTINCT s.StockItemID,s.ProductName,s.Brand,s.IsChillerStock FROM clean.SalesLine s
WHERE s.ExecutionID=:execution_id AND NOT EXISTS(SELECT 1 FROM dw.DimProduct d WHERE d.StockItemID=s.StockItemID);

INSERT dw.FactSales(InvoiceLineID,InvoiceID,DateKey,CustomerKey,ProductKey,Quantity,UnitPrice,
 SalesAmount,TaxAmount,ExtendedPrice,LineProfit,ExecutionID)
SELECT s.InvoiceLineID,s.InvoiceID,dt.DateKey,c.CustomerKey,p.ProductKey,s.Quantity,s.UnitPrice,
 s.SalesAmount,s.TaxAmount,s.ExtendedPrice,s.LineProfit,s.ExecutionID
FROM clean.SalesLine s JOIN dw.DimDate dt ON dt.FullDate=s.InvoiceDate
JOIN dw.DimCustomer c ON c.CustomerID=s.CustomerID JOIN dw.DimProduct p ON p.StockItemID=s.StockItemID
WHERE s.ExecutionID=:execution_id AND NOT EXISTS(SELECT 1 FROM dw.FactSales f WHERE f.InvoiceLineID=s.InvoiceLineID);

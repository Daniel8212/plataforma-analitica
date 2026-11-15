SET NOCOUNT ON;
SET XACT_ABORT ON;
-- La historia es de observaciones del catálogo, no de vigencia comercial reconstruida.
UPDATE d SET ObservedTo=:observed_at,IsCurrent=0
OUTPUT 'CUSTOMER_EXPIRE',inserted.CustomerKey INTO #Changes
FROM dw.DimCustomer d JOIN raw.Customers c ON c.CustomerID=d.CustomerID AND c.ExecutionID=:execution_id
JOIN raw.CustomerCategories cat ON cat.CustomerCategoryID=c.CustomerCategoryID AND cat.ExecutionID=c.ExecutionID
WHERE d.IsCurrent=1 AND d.CustomerID<>0 AND
 (d.CustomerName<>LTRIM(RTRIM(c.CustomerName)) OR d.CustomerCategoryID<>c.CustomerCategoryID
  OR d.CustomerCategory<>LTRIM(RTRIM(cat.CustomerCategoryName)));
INSERT dw.DimCustomer(CustomerID,CustomerName,CustomerCategoryID,CustomerCategory,ObservedFrom)
OUTPUT 'CUSTOMER_INSERT',inserted.CustomerKey INTO #Changes
SELECT c.CustomerID,LTRIM(RTRIM(c.CustomerName)),c.CustomerCategoryID,LTRIM(RTRIM(cat.CustomerCategoryName)),:observed_at
FROM raw.Customers c JOIN raw.CustomerCategories cat ON cat.ExecutionID=c.ExecutionID AND cat.CustomerCategoryID=c.CustomerCategoryID
WHERE c.ExecutionID=:execution_id AND NOT EXISTS(SELECT 1 FROM dw.DimCustomer d WHERE d.CustomerID=c.CustomerID AND d.IsCurrent=1);

-- Producto Tipo 1: etiquetas actuales del catálogo; las medidas facturadas no cambian.
UPDATE d SET ProductName=LTRIM(RTRIM(p.StockItemName)),Brand=LTRIM(RTRIM(p.Brand)),IsChillerStock=p.IsChillerStock
OUTPUT 'PRODUCT_UPDATE',inserted.ProductKey INTO #Changes
FROM dw.DimProduct d JOIN raw.StockItems p ON p.StockItemID=d.StockItemID WHERE p.ExecutionID=:execution_id
 AND (d.ProductName<>LTRIM(RTRIM(p.StockItemName)) OR ISNULL(d.Brand,N'')<>ISNULL(LTRIM(RTRIM(p.Brand)),N'') OR d.IsChillerStock<>p.IsChillerStock);
INSERT dw.DimProduct(StockItemID,ProductName,Brand,IsChillerStock)
OUTPUT 'PRODUCT_INSERT',inserted.ProductKey INTO #Changes
SELECT p.StockItemID,LTRIM(RTRIM(p.StockItemName)),LTRIM(RTRIM(p.Brand)),p.IsChillerStock FROM raw.StockItems p
WHERE p.ExecutionID=:execution_id AND NOT EXISTS(SELECT 1 FROM dw.DimProduct d WHERE d.StockItemID=p.StockItemID);

;WITH Calendar AS (
 SELECT MIN(InvoiceDate) CalendarDate,MAX(InvoiceDate) LastDate FROM clean.SalesLine WHERE ExecutionID=:execution_id
 UNION ALL SELECT DATEADD(day,1,CalendarDate),LastDate FROM Calendar WHERE CalendarDate<LastDate
)
INSERT dw.DimDate(DateKey,FullDate,Year,Month,Quarter,IsoWeek,IsWeekend)
SELECT CONVERT(int,CONVERT(char(8),CalendarDate,112)),CalendarDate,YEAR(CalendarDate),MONTH(CalendarDate),
 DATEPART(quarter,CalendarDate),DATEPART(iso_week,CalendarDate),CASE WHEN DATEDIFF(day,'19000101',CalendarDate)%7>=5 THEN 1 ELSE 0 END
FROM Calendar WHERE CalendarDate IS NOT NULL AND NOT EXISTS(SELECT 1 FROM dw.DimDate WHERE FullDate=CalendarDate)
OPTION(MAXRECURSION 0);

-- Una corrección del mismo cliente conserva la versión asignada al ingresar el hecho.
UPDATE f SET InvoiceID=s.InvoiceID,DateKey=dt.DateKey,
 CustomerKey=CASE WHEN old.CustomerID=s.CustomerID THEN f.CustomerKey ELSE cur.CustomerKey END,
 ProductKey=p.ProductKey,Quantity=s.Quantity,UnitPrice=s.UnitPrice,SalesAmount=s.SalesAmount,
 TaxAmount=s.TaxAmount,ExtendedPrice=s.ExtendedPrice,LineProfit=s.LineProfit,RecordStatus='ACTIVE',ExecutionID=:execution_id
OUTPUT 'UPDATE',inserted.InvoiceLineID INTO #Changes
FROM dw.FactSales f JOIN clean.SalesLine s ON s.InvoiceLineID=f.InvoiceLineID AND s.ExecutionID=:execution_id
JOIN dw.DimDate dt ON dt.FullDate=s.InvoiceDate JOIN dw.DimCustomer old ON old.CustomerKey=f.CustomerKey
JOIN dw.DimCustomer cur ON cur.CustomerID=s.CustomerID AND cur.IsCurrent=1 JOIN dw.DimProduct p ON p.StockItemID=s.StockItemID
WHERE f.RecordStatus<>'ACTIVE' OR f.InvoiceID<>s.InvoiceID OR f.DateKey<>dt.DateKey OR old.CustomerID<>s.CustomerID
 OR f.ProductKey<>p.ProductKey OR f.Quantity<>s.Quantity OR f.UnitPrice<>s.UnitPrice OR f.SalesAmount<>s.SalesAmount
 OR f.TaxAmount<>s.TaxAmount OR f.ExtendedPrice<>s.ExtendedPrice OR f.LineProfit<>s.LineProfit;
INSERT dw.FactSales(InvoiceLineID,InvoiceID,DateKey,CustomerKey,ProductKey,Quantity,UnitPrice,SalesAmount,
 TaxAmount,ExtendedPrice,LineProfit,ExecutionID)
OUTPUT 'INSERT',inserted.InvoiceLineID INTO #Changes
SELECT s.InvoiceLineID,s.InvoiceID,dt.DateKey,c.CustomerKey,p.ProductKey,s.Quantity,s.UnitPrice,s.SalesAmount,
 s.TaxAmount,s.ExtendedPrice,s.LineProfit,:execution_id
FROM clean.SalesLine s JOIN dw.DimDate dt ON dt.FullDate=s.InvoiceDate
JOIN dw.DimCustomer c ON c.CustomerID=s.CustomerID AND c.IsCurrent=1 JOIN dw.DimProduct p ON p.StockItemID=s.StockItemID
WHERE s.ExecutionID=:execution_id AND NOT EXISTS(SELECT 1 FROM dw.FactSales f WHERE f.InvoiceLineID=s.InvoiceLineID);
UPDATE f SET RecordStatus='QUARANTINED',ExecutionID=:execution_id
OUTPUT 'REJECT',inserted.InvoiceLineID INTO #Changes
FROM dw.FactSales f
JOIN audit.Quarantine q ON q.SourceKey=f.InvoiceLineID AND q.ExecutionID=:execution_id
WHERE f.RecordStatus<>'QUARANTINED';

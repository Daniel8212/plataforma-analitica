SET NOCOUNT ON;
SET XACT_ABORT ON;
INSERT audit.Quarantine(ExecutionID,SourceObject,SourceKey,RuleID,Detail,OriginalRecord)
SELECT :execution_id,'Sales.InvoiceLines',v.InvoiceLineID,v.FailedRule,
 N'Excluido de métricas activas; conservar original y corregir fuente para reintentar',
 (SELECT r.InvoiceLineID,r.InvoiceID,r.StockItemID,r.Description,r.Quantity,r.UnitPrice,r.TaxRate,
 r.TaxAmount,r.LineProfit,r.ExtendedPrice,r.LastEditedWhen FOR JSON PATH,WITHOUT_ARRAY_WRAPPER,INCLUDE_NULL_VALUES)
FROM clean.vCandidateSales v JOIN raw.InvoiceLines r ON r.ExecutionID=v.ExecutionID AND r.InvoiceLineID=v.InvoiceLineID
WHERE v.ExecutionID=:execution_id AND v.FailedRule IS NOT NULL;
INSERT clean.SalesLine(ExecutionID,InvoiceLineID,InvoiceID,InvoiceDate,CustomerID,StockItemID,
 CustomerName,CustomerCategoryID,CustomerCategory,ProductName,Brand,IsChillerStock,
 Quantity,UnitPrice,SalesAmount,TaxAmount,ExtendedPrice,LineProfit)
SELECT ExecutionID,InvoiceLineID,InvoiceID,InvoiceDate,CustomerID,StockItemID,
 LTRIM(RTRIM(CustomerName)),CustomerCategoryID,LTRIM(RTRIM(CustomerCategoryName)),
 LTRIM(RTRIM(StockItemName)),LTRIM(RTRIM(Brand)),IsChillerStock,
 Quantity,UnitPrice,CONVERT(decimal(18,2),Quantity*UnitPrice),TaxAmount,ExtendedPrice,LineProfit
FROM clean.vCandidateSales WHERE ExecutionID=:execution_id AND FailedRule IS NULL;

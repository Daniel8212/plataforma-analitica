CREATE OR ALTER VIEW dw.vSalesRead AS
SELECT f.InvoiceLineID,f.InvoiceID,d.FullDate AS InvoiceDate,c.CustomerID,c.CustomerName,
 c.CustomerCategoryID,c.CustomerCategory,p.StockItemID AS ProductID,p.ProductName,p.Brand,
 f.Quantity,f.UnitPrice,f.SalesAmount,f.TaxAmount,f.ExtendedPrice,f.LineProfit,
 c.ObservedFrom AS CustomerObservedFrom,f.ExecutionID
FROM dw.FactSales f JOIN dw.DimDate d ON d.DateKey=f.DateKey
JOIN dw.DimCustomer c ON c.CustomerKey=f.CustomerKey JOIN dw.DimProduct p ON p.ProductKey=f.ProductKey
WHERE f.RecordStatus='ACTIVE';
GO
CREATE OR ALTER VIEW dw.vProductFilters AS
SELECT StockItemID AS ProductID,ProductName FROM dw.DimProduct WHERE ProductKey<>0;
GO
CREATE OR ALTER VIEW dw.vCategoryFilters AS
SELECT CustomerCategoryID,MAX(CustomerCategory) AS CustomerCategory FROM dw.DimCustomer
WHERE CustomerID<>0 GROUP BY CustomerCategoryID;
GO
CREATE OR ALTER VIEW audit.vExecutions AS
SELECT CONVERT(varchar(36),ExecutionID) AS ExecutionID,PipelineName,StartTime,EndTime,Status,
 RowsRead,RowsInserted,RowsUpdated,RowsRejected,ErrorDetail,LoadMode,IsSimulated,WatermarkStart,WatermarkEnd,
 DATEDIFF_BIG(millisecond,StartTime,COALESCE(EndTime,SYSUTCDATETIME()))/1000.0 AS DurationSeconds
FROM audit.Execution;
GO
CREATE OR ALTER VIEW audit.vRejections AS
SELECT QuarantineID,CONVERT(varchar(36),ExecutionID) AS ExecutionID,SourceObject,SourceKey,
 RuleID,Detail,RecordedAt FROM audit.Quarantine;
GO
CREATE OR ALTER VIEW audit.vWatermarks AS
SELECT PipelineName,WatermarkValue,CONVERT(varchar(36),ExecutionID) AS ExecutionID FROM audit.Watermark;

-- Migración aditiva: no elimina datos del primer flujo.
SET NOCOUNT ON;
IF COL_LENGTH('audit.Execution','LoadMode') IS NULL
BEGIN
 ALTER TABLE audit.Execution ADD LoadMode varchar(16) NOT NULL CONSTRAINT DF_Execution_Mode DEFAULT 'initial',
  IsSimulated bit NOT NULL CONSTRAINT DF_Execution_Simulated DEFAULT 0,
  WatermarkStart datetime2(7) NULL,WatermarkEnd datetime2(7) NULL;
END;
IF OBJECT_ID('audit.Watermark') IS NULL
CREATE TABLE audit.Watermark(
 PipelineName varchar(100) NOT NULL PRIMARY KEY,WatermarkValue datetime2(7) NOT NULL,
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID)
);
IF OBJECT_ID('audit.Deletion') IS NULL
CREATE TABLE audit.Deletion(
 DeletionID bigint IDENTITY PRIMARY KEY,ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID),
 InvoiceLineID int NOT NULL,DetectedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 UNIQUE(ExecutionID,InvoiceLineID)
);
IF COL_LENGTH('dw.FactSales','RecordStatus') IS NULL
 ALTER TABLE dw.FactSales ADD RecordStatus varchar(16) NOT NULL CONSTRAINT DF_Fact_Status DEFAULT 'ACTIVE'
  CONSTRAINT CK_Fact_Status CHECK(RecordStatus IN ('ACTIVE','QUARANTINED','DELETED'));
GO
IF COL_LENGTH('dw.DimCustomer','ObservedFrom') IS NULL
BEGIN
 DECLARE @constraint sysname;
 SELECT @constraint=kc.name FROM sys.key_constraints kc JOIN sys.index_columns ic
  ON ic.object_id=kc.parent_object_id AND ic.index_id=kc.unique_index_id
 JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
 WHERE kc.parent_object_id=OBJECT_ID('dw.DimCustomer') AND kc.type='UQ' AND c.name='CustomerID';
 IF @constraint IS NOT NULL
 BEGIN
  DECLARE @drop_sql nvarchar(500)='ALTER TABLE dw.DimCustomer DROP CONSTRAINT '+QUOTENAME(@constraint);
  EXEC(@drop_sql);
 END;
 ALTER TABLE dw.DimCustomer ADD ObservedFrom datetime2(7) NOT NULL CONSTRAINT DF_Customer_From DEFAULT SYSUTCDATETIME(),
  ObservedTo datetime2(7) NOT NULL CONSTRAINT DF_Customer_To DEFAULT '9999-12-31T23:59:59.9999999',
  IsCurrent bit NOT NULL CONSTRAINT DF_Customer_Current DEFAULT 1;
END;
GO
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dw.DimCustomer') AND name='UX_Customer_Current')
 CREATE UNIQUE INDEX UX_Customer_Current ON dw.DimCustomer(CustomerID) WHERE IsCurrent=1;
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dw.DimCustomer') AND name='UX_Customer_Observed')
 CREATE UNIQUE INDEX UX_Customer_Observed ON dw.DimCustomer(CustomerID,ObservedFrom);
IF NOT EXISTS(SELECT 1 FROM sys.check_constraints WHERE parent_object_id=OBJECT_ID('dw.DimCustomer') AND name='CK_Customer_Interval')
 ALTER TABLE dw.DimCustomer ADD CONSTRAINT CK_Customer_Interval CHECK(ObservedFrom<ObservedTo);
GO
CREATE OR ALTER VIEW dw.vSalesKpi AS
SELECT COALESCE(SUM(f.SalesAmount),0) AS sales,COUNT(DISTINCT f.InvoiceID) AS invoice_count,
 MIN(d.FullDate) AS first_date,MAX(d.FullDate) AS last_date,
 (SELECT MAX(EndTime) FROM audit.Execution WHERE Status='SUCCEEDED') AS loaded_at,
 (SELECT TOP(1) CONVERT(varchar(36),ExecutionID) FROM audit.Execution WHERE Status='SUCCEEDED' ORDER BY EndTime DESC) AS execution_id
FROM dw.FactSales f JOIN dw.DimDate d ON d.DateKey=f.DateKey WHERE f.RecordStatus='ACTIVE';

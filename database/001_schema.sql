-- Ejecutar en SalesAnalytics mediante deployment.bootstrap, nunca sobre OLTP.
IF SCHEMA_ID('raw') IS NULL EXEC('CREATE SCHEMA raw');
IF SCHEMA_ID('clean') IS NULL EXEC('CREATE SCHEMA clean');
IF SCHEMA_ID('dw') IS NULL EXEC('CREATE SCHEMA dw');
IF SCHEMA_ID('audit') IS NULL EXEC('CREATE SCHEMA audit');
GO
IF OBJECT_ID('audit.Execution') IS NULL
CREATE TABLE audit.Execution (
 ExecutionID uniqueidentifier NOT NULL PRIMARY KEY,
 PipelineName varchar(100) NOT NULL, StartTime datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 EndTime datetime2(7) NULL, Status varchar(12) NOT NULL CHECK(Status IN ('RUNNING','SUCCEEDED','FAILED')),
 RowsRead bigint NOT NULL DEFAULT 0, RowsInserted bigint NOT NULL DEFAULT 0,
 RowsUpdated bigint NOT NULL DEFAULT 0, RowsRejected bigint NOT NULL DEFAULT 0,
 ErrorDetail nvarchar(1000) NULL
);
IF OBJECT_ID('audit.StageCount') IS NULL
CREATE TABLE audit.StageCount (
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID),
 Stage varchar(30) NOT NULL, SourceObject varchar(100) NOT NULL, TargetObject varchar(100) NOT NULL,
 RowsRead bigint NOT NULL, RowsInserted bigint NOT NULL, RowsUpdated bigint NOT NULL DEFAULT 0,
 RowsRejected bigint NOT NULL DEFAULT 0, PRIMARY KEY(ExecutionID,Stage,TargetObject)
);
IF OBJECT_ID('audit.Quarantine') IS NULL
CREATE TABLE audit.Quarantine (
 QuarantineID bigint IDENTITY PRIMARY KEY,
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID),
 SourceObject varchar(100) NOT NULL, SourceKey int NOT NULL, RuleID varchar(50) NOT NULL,
 Detail nvarchar(1000) NOT NULL, OriginalRecord nvarchar(max) NOT NULL CHECK(ISJSON(OriginalRecord)=1),
 RecordedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(), UNIQUE(ExecutionID,SourceObject,SourceKey)
);
IF OBJECT_ID('audit.Reconciliation') IS NULL
CREATE TABLE audit.Reconciliation (
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID),
 Layer varchar(30) NOT NULL, [RowCount] bigint NOT NULL, SalesAmount decimal(28,2) NOT NULL,
 PRIMARY KEY(ExecutionID,Layer)
);
GO
-- Raw conserva sin transformación las columnas del alcance. No contiene direcciones/teléfonos.
IF OBJECT_ID('raw.Invoices') IS NULL
CREATE TABLE raw.Invoices (
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID), InvoiceID int NOT NULL,
 CustomerID int NOT NULL, InvoiceDate date NOT NULL, IsCreditNote bit NOT NULL,
 LastEditedWhen datetime2(7) NOT NULL, PRIMARY KEY(ExecutionID,InvoiceID)
);
IF OBJECT_ID('raw.InvoiceLines') IS NULL
CREATE TABLE raw.InvoiceLines (
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID), InvoiceLineID int NOT NULL,
 InvoiceID int NOT NULL, StockItemID int NOT NULL, Description nvarchar(100) NOT NULL,
 Quantity int NOT NULL, UnitPrice decimal(18,2) NULL, TaxRate decimal(18,3) NOT NULL,
 TaxAmount decimal(18,2) NOT NULL, LineProfit decimal(18,2) NOT NULL,
 ExtendedPrice decimal(18,2) NOT NULL, LastEditedWhen datetime2(7) NOT NULL,
 PRIMARY KEY(ExecutionID,InvoiceLineID)
);
IF OBJECT_ID('raw.Customers') IS NULL
CREATE TABLE raw.Customers (
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID), CustomerID int NOT NULL,
 CustomerName nvarchar(100) NOT NULL, CustomerCategoryID int NOT NULL,
 ValidFrom datetime2(7) NOT NULL, ValidTo datetime2(7) NOT NULL, PRIMARY KEY(ExecutionID,CustomerID)
);
IF OBJECT_ID('raw.CustomerCategories') IS NULL
CREATE TABLE raw.CustomerCategories (
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID), CustomerCategoryID int NOT NULL,
 CustomerCategoryName nvarchar(50) NOT NULL, ValidFrom datetime2(7) NOT NULL,
 ValidTo datetime2(7) NOT NULL, PRIMARY KEY(ExecutionID,CustomerCategoryID)
);
IF OBJECT_ID('raw.StockItems') IS NULL
CREATE TABLE raw.StockItems (
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID), StockItemID int NOT NULL,
 StockItemName nvarchar(100) NOT NULL, Brand nvarchar(50) NULL, IsChillerStock bit NOT NULL,
 ValidFrom datetime2(7) NOT NULL, ValidTo datetime2(7) NOT NULL, PRIMARY KEY(ExecutionID,StockItemID)
);
GO
CREATE OR ALTER VIEW clean.vCandidateSales AS
SELECT l.*,i.CustomerID,i.InvoiceDate,i.IsCreditNote,c.CustomerName,c.CustomerCategoryID,
 cat.CustomerCategoryName,p.StockItemName,p.Brand,p.IsChillerStock,
 CASE WHEN i.InvoiceID IS NULL THEN 'Q02_INVOICE'
 WHEN c.CustomerID IS NULL OR cat.CustomerCategoryID IS NULL THEN 'Q02_CUSTOMER'
 WHEN p.StockItemID IS NULL THEN 'Q02_PRODUCT'
 WHEN l.UnitPrice IS NULL THEN 'Q03_PRICE_NULL'
 WHEN i.IsCreditNote=1 THEN 'Q05_CREDIT_UNVALIDATED'
 WHEN l.Quantity<=0 OR l.UnitPrice<0 OR l.TaxRate<0 OR l.TaxAmount<0 THEN 'Q03_DOMAIN'
 WHEN l.ExtendedPrice<>ROUND(l.Quantity*l.UnitPrice,2)+l.TaxAmount THEN 'Q04_AMOUNT'
 WHEN LTRIM(RTRIM(c.CustomerName))='' OR LTRIM(RTRIM(p.StockItemName))='' THEN 'Q07_EMPTY_NAME'
 ELSE NULL END AS FailedRule
FROM raw.InvoiceLines l
LEFT JOIN raw.Invoices i ON i.ExecutionID=l.ExecutionID AND i.InvoiceID=l.InvoiceID
LEFT JOIN raw.Customers c ON c.ExecutionID=l.ExecutionID AND c.CustomerID=i.CustomerID
LEFT JOIN raw.CustomerCategories cat ON cat.ExecutionID=c.ExecutionID AND cat.CustomerCategoryID=c.CustomerCategoryID
LEFT JOIN raw.StockItems p ON p.ExecutionID=l.ExecutionID AND p.StockItemID=l.StockItemID;
GO
IF OBJECT_ID('clean.SalesLine') IS NULL
CREATE TABLE clean.SalesLine (
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID), InvoiceLineID int NOT NULL,
 InvoiceID int NOT NULL, InvoiceDate date NOT NULL, CustomerID int NOT NULL, StockItemID int NOT NULL,
 CustomerName nvarchar(100) NOT NULL, CustomerCategoryID int NOT NULL, CustomerCategory nvarchar(50) NOT NULL,
 ProductName nvarchar(100) NOT NULL, Brand nvarchar(50) NULL, IsChillerStock bit NOT NULL,
 Quantity int NOT NULL CHECK(Quantity>0), UnitPrice decimal(18,2) NOT NULL CHECK(UnitPrice>=0),
 SalesAmount decimal(18,2) NOT NULL, TaxAmount decimal(18,2) NOT NULL,
 ExtendedPrice decimal(18,2) NOT NULL, LineProfit decimal(18,2) NOT NULL,
 PRIMARY KEY(ExecutionID,InvoiceLineID), CHECK(ExtendedPrice=SalesAmount+TaxAmount)
);
IF OBJECT_ID('dw.DimDate') IS NULL
CREATE TABLE dw.DimDate (
 DateKey int NOT NULL PRIMARY KEY, FullDate date NULL UNIQUE,
 Year int NULL, Month int NULL, Quarter int NULL, IsoWeek int NULL, IsWeekend bit NULL
);
IF OBJECT_ID('dw.DimCustomer') IS NULL
CREATE TABLE dw.DimCustomer (
 CustomerKey int IDENTITY PRIMARY KEY, CustomerID int NOT NULL UNIQUE,
 CustomerName nvarchar(100) NOT NULL, CustomerCategoryID int NOT NULL,
 CustomerCategory nvarchar(50) NOT NULL
);
IF OBJECT_ID('dw.DimProduct') IS NULL
CREATE TABLE dw.DimProduct (
 ProductKey int IDENTITY PRIMARY KEY, StockItemID int NOT NULL UNIQUE,
 ProductName nvarchar(100) NOT NULL, Brand nvarchar(50) NULL, IsChillerStock bit NOT NULL
);
IF OBJECT_ID('dw.FactSales') IS NULL
CREATE TABLE dw.FactSales (
 FactSalesKey bigint IDENTITY PRIMARY KEY, InvoiceLineID int NOT NULL UNIQUE, InvoiceID int NOT NULL,
 DateKey int NOT NULL REFERENCES dw.DimDate(DateKey),
 CustomerKey int NOT NULL REFERENCES dw.DimCustomer(CustomerKey),
 ProductKey int NOT NULL REFERENCES dw.DimProduct(ProductKey),
 Quantity int NOT NULL CHECK(Quantity>0), UnitPrice decimal(18,2) NOT NULL CHECK(UnitPrice>=0),
 SalesAmount decimal(18,2) NOT NULL, TaxAmount decimal(18,2) NOT NULL,
 ExtendedPrice decimal(18,2) NOT NULL, LineProfit decimal(18,2) NOT NULL,
 ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID),
 CHECK(ExtendedPrice=SalesAmount+TaxAmount)
);
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dw.FactSales') AND name='IX_FactSales_Date')
CREATE INDEX IX_FactSales_Date ON dw.FactSales(DateKey) INCLUDE(CustomerKey,ProductKey,SalesAmount,Quantity,InvoiceID);
IF NOT EXISTS(SELECT 1 FROM dw.DimDate WHERE DateKey=0)
INSERT dw.DimDate(DateKey) VALUES(0);
IF NOT EXISTS(SELECT 1 FROM dw.DimCustomer WHERE CustomerKey=0)
BEGIN
 SET IDENTITY_INSERT dw.DimCustomer ON;
 INSERT dw.DimCustomer(CustomerKey,CustomerID,CustomerName,CustomerCategoryID,CustomerCategory)
 VALUES(0,0,N'Desconocido',0,N'Desconocida');
 SET IDENTITY_INSERT dw.DimCustomer OFF;
END;
IF NOT EXISTS(SELECT 1 FROM dw.DimProduct WHERE ProductKey=0)
BEGIN
 SET IDENTITY_INSERT dw.DimProduct ON;
 INSERT dw.DimProduct(ProductKey,StockItemID,ProductName,Brand,IsChillerStock)
 VALUES(0,0,N'Desconocido',NULL,0);
 SET IDENTITY_INSERT dw.DimProduct OFF;
END;
GO
CREATE OR ALTER VIEW dw.vSalesKpi AS
SELECT COALESCE(SUM(f.SalesAmount),0) AS sales,COUNT(DISTINCT f.InvoiceID) AS invoice_count,
 MIN(d.FullDate) AS first_date,MAX(d.FullDate) AS last_date,
 (SELECT MAX(EndTime) FROM audit.Execution WHERE Status='SUCCEEDED') AS loaded_at,
 (SELECT TOP (1) CONVERT(varchar(36),ExecutionID) FROM audit.Execution WHERE Status='SUCCEEDED' ORDER BY EndTime DESC) AS execution_id
FROM dw.FactSales f JOIN dw.DimDate d ON d.DateKey=f.DateKey;

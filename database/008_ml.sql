IF SCHEMA_ID('ml') IS NULL EXEC('CREATE SCHEMA ml');
GO
IF OBJECT_ID('ml.ModelRun') IS NULL
CREATE TABLE ml.ModelRun(
 Version varchar(80) NOT NULL PRIMARY KEY,GeneratedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 SourceExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID),DatasetHash char(64) NOT NULL,
 Algorithm varchar(80) NOT NULL,DataFirstDate date NOT NULL,SourceLastDate date NOT NULL,AsOfDate date NOT NULL,
 CompleteWeeks int NOT NULL,TrainStart date NOT NULL,TrainEnd date NOT NULL,ValidationStart date NOT NULL,
 ValidationEnd date NOT NULL,TestStart date NOT NULL,TestEnd date NOT NULL,
 ParametersJson nvarchar(max) NOT NULL CHECK(ISJSON(ParametersJson)=1),
 MetricsJson nvarchar(max) NOT NULL CHECK(ISJSON(MetricsJson)=1),
 ReportJson nvarchar(max) NOT NULL CHECK(ISJSON(ReportJson)=1),
 ArtifactPath nvarchar(250) NOT NULL,ArtifactSHA256 char(64) NOT NULL,
 IsActive bit NOT NULL DEFAULT 1
);
IF NOT EXISTS(SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('ml.ModelRun') AND name='UX_Model_Active')
 CREATE UNIQUE INDEX UX_Model_Active ON ml.ModelRun(IsActive) WHERE IsActive=1;
IF OBJECT_ID('ml.Prediction') IS NULL
CREATE TABLE ml.Prediction(
 PredictionID bigint IDENTITY PRIMARY KEY,Version varchar(80) NOT NULL REFERENCES ml.ModelRun(Version),
 Kind varchar(10) NOT NULL CHECK(Kind IN ('future','test')),TargetWeekStart date NOT NULL,
 OriginDate date NOT NULL,Horizon int NOT NULL CHECK(Horizon BETWEEN 1 AND 4),
 PredictedSales decimal(18,2) NOT NULL CHECK(PredictedSales>=0),ActualSales decimal(18,2) NULL,
 GeneratedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),UNIQUE(Version,Kind,TargetWeekStart)
);
GO
CREATE OR ALTER VIEW ml.vActiveModel AS
SELECT Version,GeneratedAt,CONVERT(varchar(36),SourceExecutionID) SourceExecutionID,DatasetHash,Algorithm,
 DataFirstDate,SourceLastDate,AsOfDate,CompleteWeeks,TrainStart,TrainEnd,ValidationStart,ValidationEnd,
 TestStart,TestEnd,ParametersJson,MetricsJson,ReportJson FROM ml.ModelRun WHERE IsActive=1;
GO
CREATE OR ALTER VIEW ml.vPredictions AS
SELECT p.Version,p.Kind,p.TargetWeekStart,p.OriginDate,p.Horizon,p.PredictedSales,p.ActualSales,p.GeneratedAt
FROM ml.Prediction p JOIN ml.ModelRun m ON m.Version=p.Version WHERE m.IsActive=1;

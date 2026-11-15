IF OBJECT_ID('audit.ChatRequest') IS NULL
CREATE TABLE audit.ChatRequest(
 RequestID uniqueidentifier NOT NULL PRIMARY KEY,CreatedAt datetime2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
 QuestionHash char(64) NOT NULL,ToolName varchar(40) NOT NULL,Status varchar(30) NOT NULL,
 SourceExecutionID uniqueidentifier NULL REFERENCES audit.Execution(ExecutionID),Model varchar(80) NULL,
 DurationMs int NOT NULL,IsEvaluation bit NOT NULL DEFAULT 0,
 ResponseJson nvarchar(max) NOT NULL CHECK(ISJSON(ResponseJson)=1),
 UnverifiedJson nvarchar(max) NOT NULL CHECK(ISJSON(UnverifiedJson)=1)
);
GO
CREATE OR ALTER VIEW audit.vChatHealth AS
SELECT Status,Model,COUNT_BIG(*) Requests,MAX(CreatedAt) LastRequestAt,
 AVG(CONVERT(decimal(18,2),DurationMs)) AverageDurationMs FROM audit.ChatRequest GROUP BY Status,Model;

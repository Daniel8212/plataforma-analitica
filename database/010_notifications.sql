IF SCHEMA_ID('notify') IS NULL EXEC('CREATE SCHEMA notify');
GO
IF OBJECT_ID('notify.Task') IS NULL
CREATE TABLE notify.Task(
 TaskID uniqueidentifier NOT NULL PRIMARY KEY, ExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID),
 RuleName varchar(40) NOT NULL, IsSimulated bit NOT NULL, CreatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 Status varchar(12) NOT NULL DEFAULT 'PENDING' CHECK(Status IN('PENDING','FAILED','SUCCEEDED')),
 Attempts int NOT NULL DEFAULT 0, LastError varchar(200) NULL, CompletedAt datetime2 NULL,
 Payload nvarchar(max) NOT NULL CHECK(ISJSON(Payload)=1), UNIQUE(ExecutionID,RuleName)
);
IF OBJECT_ID('notify.Evaluation') IS NULL
CREATE TABLE notify.Evaluation(
 TaskID uniqueidentifier NOT NULL PRIMARY KEY REFERENCES notify.Task(TaskID),
 EvaluatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(), Outcome varchar(20) NOT NULL,
 Explanation nvarchar(500) NOT NULL
);
IF OBJECT_ID('notify.Alert') IS NULL
CREATE TABLE notify.Alert(
 AlertID uniqueidentifier NOT NULL PRIMARY KEY, RuleName varchar(40) NOT NULL,
 CreatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(), UpdatedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(),
 SourceExecutionID uniqueidentifier NOT NULL REFERENCES audit.Execution(ExecutionID),
 Severity varchar(12) NOT NULL, CurrentStart date NOT NULL, CurrentEnd date NOT NULL,
 ReferenceStart date NOT NULL, ReferenceEnd date NOT NULL, ObservedValue decimal(20,2) NOT NULL,
 ReferenceValue decimal(20,2) NOT NULL, ThresholdPercent decimal(8,2) NOT NULL, DropPercent decimal(12,4) NOT NULL,
 Origin varchar(40) NOT NULL DEFAULT 'POST_LOAD_RULE', IsSimulated bit NOT NULL,
 State varchar(12) NOT NULL DEFAULT 'NEW' CHECK(State IN('NEW','ATTENDED','DISCARDED','RESOLVED')),
 SeenAt datetime2 NULL, DeliveryStatus varchar(12) NOT NULL DEFAULT 'PENDING' CHECK(DeliveryStatus IN('PENDING','DELIVERED')),
 Explanation nvarchar(500) NOT NULL, EvidenceJson nvarchar(max) NOT NULL CHECK(ISJSON(EvidenceJson)=1),
 UNIQUE(RuleName,CurrentStart,IsSimulated)
);
IF OBJECT_ID('notify.StateHistory') IS NULL
CREATE TABLE notify.StateHistory(
 HistoryID bigint IDENTITY PRIMARY KEY,AlertID uniqueidentifier NOT NULL REFERENCES notify.Alert(AlertID),
 ChangedAt datetime2 NOT NULL DEFAULT SYSUTCDATETIME(), PreviousState varchar(12) NOT NULL,NewState varchar(12) NOT NULL
);
GO
CREATE OR ALTER VIEW notify.vAlerts AS SELECT * FROM notify.Alert;
GO
CREATE OR ALTER VIEW notify.vTasks AS
SELECT t.TaskID,t.ExecutionID,t.RuleName,t.IsSimulated,t.CreatedAt,t.Status,t.Attempts,t.LastError,t.CompletedAt,
 e.Outcome,e.Explanation FROM notify.Task t LEFT JOIN notify.Evaluation e ON e.TaskID=t.TaskID;
GO
CREATE OR ALTER PROCEDURE notify.MarkSeen @id uniqueidentifier AS
BEGIN
 SET NOCOUNT ON;
 UPDATE notify.Alert SET SeenAt=COALESCE(SeenAt,SYSUTCDATETIME()),DeliveryStatus='DELIVERED' WHERE AlertID=@id;
 SELECT @@ROWCOUNT Affected;
END;
GO
CREATE OR ALTER PROCEDURE notify.ChangeState @id uniqueidentifier,@state varchar(12) AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON;
 IF @state NOT IN ('ATTENDED','DISCARDED') THROW 50001,'Invalid operator state',1;
 DECLARE @changes TABLE(AlertID uniqueidentifier,PreviousState varchar(12),NewState varchar(12));
 UPDATE notify.Alert SET State=@state,UpdatedAt=SYSUTCDATETIME()
 OUTPUT inserted.AlertID,deleted.State,inserted.State INTO @changes
 WHERE AlertID=@id AND State<>@state AND State<>'RESOLVED';
 DECLARE @affected int=@@ROWCOUNT;
 INSERT notify.StateHistory(AlertID,PreviousState,NewState) SELECT * FROM @changes;
 SELECT @affected Affected;
END;

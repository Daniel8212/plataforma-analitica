import json
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import text
from etl.connection import engine

THRESHOLD=Decimal('15')

def snapshot(conn):
    first,last=conn.execute(text('SELECT MIN(InvoiceDate),MAX(InvoiceDate) FROM dw.vSalesRead')).one()
    if not last:return {'eligible':False,'reason':'Sin datos activos'}
    # Sunday immediately before the Monday containing the most recent date;
    # include that Sunday itself when the most recent date is Sunday.
    end=last-timedelta(days=(last.weekday()+1)%7)
    start=end-timedelta(days=6);ref_end=start-timedelta(days=1);ref_start=ref_end-timedelta(days=6)
    if first>ref_start:return {'eligible':False,'reason':'No hay dos semanas completas dentro de la cobertura'}
    current,reference=conn.execute(text('''SELECT
      COALESCE(SUM(CASE WHEN InvoiceDate BETWEEN :s AND :e THEN SalesAmount ELSE 0 END),0),
      COALESCE(SUM(CASE WHEN InvoiceDate BETWEEN :rs AND :re THEN SalesAmount ELSE 0 END),0)
      FROM dw.vSalesRead WHERE InvoiceDate BETWEEN :rs AND :e'''),{'s':start,'e':end,'rs':ref_start,'re':ref_end}).one()
    return {'eligible':reference>0,'reason':'Referencia cero; variación indefinida' if reference<=0 else 'Dos semanas completas consecutivas',
            'current_start':str(start),'current_end':str(end),'reference_start':str(ref_start),'reference_end':str(ref_end),
            'observed':str(current),'reference':str(reference),'threshold':str(THRESHOLD)}

def enqueue(conn,execution_id,simulated=False,*,payload=None,rule='SALES_DROP_WEEKLY'):
    task=str(uuid4())
    conn.execute(text('''IF NOT EXISTS(SELECT 1 FROM notify.Task WHERE ExecutionID=:run AND RuleName=:rule)
       INSERT notify.Task(TaskID,ExecutionID,RuleName,IsSimulated,Payload) VALUES(:id,:run,:rule,:sim,:payload)'''),
       {'id':task,'run':execution_id,'rule':rule,'sim':bool(simulated),'payload':json.dumps(payload if payload is not None else snapshot(conn))})
    return str(conn.execute(text('SELECT TaskID FROM notify.Task WHERE ExecutionID=:run AND RuleName=:rule'),{'run':execution_id,'rule':rule}).scalar_one())

def evaluate(payload):
    if not payload['eligible']:return 'SKIPPED',None,payload['reason']
    drop=(Decimal(payload['reference'])-Decimal(payload['observed']))/Decimal(payload['reference'])*100
    triggered=drop>Decimal(payload['threshold'])
    return ('TRIGGERED' if triggered else 'CLEAR'),drop,('Caída superior al umbral; revisar productos y clientes del período.' if triggered else 'Sin caída superior al umbral.')

def process(task_id,warehouse_database=None,*,fail=False):
    db=engine(warehouse_database)
    try:
        with db.connect().execution_options(isolation_level='SERIALIZABLE') as conn,conn.begin():
            task=conn.execute(text('SELECT * FROM notify.Task WITH(UPDLOCK,HOLDLOCK) WHERE TaskID=:id'),{'id':task_id}).mappings().one()
            if task['Status']=='SUCCEEDED':return {'task_id':str(task_id),'status':'SUCCEEDED','already_processed':True}
            if fail:raise RuntimeError('SIMULATED_NOTIFICATION_FAILURE')
            p=json.loads(task['Payload']);outcome,drop,explanation=evaluate(p)
            newer=conn.execute(text('''SELECT TOP(1) 1 FROM notify.Task
              WHERE RuleName=:rule AND IsSimulated=:sim AND Status='SUCCEEDED' AND CreatedAt>:created
              AND JSON_VALUE(Payload,'$.current_start')=:start'''),{'rule':task['RuleName'],'sim':task['IsSimulated'],'created':task['CreatedAt'],'start':p.get('current_start')}).scalar()
            if newer:outcome='SUPERSEDED';explanation='Una evaluación posterior del mismo período ya fue confirmada.'
            if outcome not in ('SKIPPED','SUPERSEDED'):
                params={'rule':task['RuleName'],'sim':task['IsSimulated'],'start':p['current_start']}
                existing=conn.execute(text('SELECT AlertID,State FROM notify.Alert WHERE RuleName=:rule AND IsSimulated=:sim AND CurrentStart=:start'),params).mappings().first()
                if outcome=='TRIGGERED':
                    params.update(id=str(uuid4()),run=str(task['ExecutionID']),end=p['current_end'],rs=p['reference_start'],re=p['reference_end'],
                      observed=p['observed'],reference=p['reference'],threshold=p['threshold'],drop=drop,explanation=explanation,
                      evidence=json.dumps(p),severity='HIGH' if drop>=30 else 'WARNING')
                    if not existing:
                        conn.execute(text('''INSERT notify.Alert(AlertID,RuleName,SourceExecutionID,Severity,CurrentStart,CurrentEnd,
                          ReferenceStart,ReferenceEnd,ObservedValue,ReferenceValue,ThresholdPercent,DropPercent,IsSimulated,Explanation,EvidenceJson)
                          VALUES(:id,:rule,:run,:severity,:start,:end,:rs,:re,:observed,:reference,:threshold,:drop,:sim,:explanation,:evidence)'''),params)
                    else:
                        if existing['State']=='RESOLVED':
                            conn.execute(text("INSERT notify.StateHistory(AlertID,PreviousState,NewState) VALUES(:id,'RESOLVED','NEW')"),{'id':existing['AlertID']})
                        # Same period is one alert. Preserve operator decisions unless a resolved condition recurs.
                        conn.execute(text('''UPDATE notify.Alert SET SourceExecutionID=:run,ObservedValue=:observed,ReferenceValue=:reference,
                          DropPercent=:drop,Severity=:severity,EvidenceJson=:evidence,UpdatedAt=SYSUTCDATETIME(),
                          State=CASE WHEN State='RESOLVED' THEN 'NEW' ELSE State END,
                          DeliveryStatus=CASE WHEN State='RESOLVED' THEN 'PENDING' ELSE DeliveryStatus END,
                          SeenAt=CASE WHEN State='RESOLVED' THEN NULL ELSE SeenAt END
                          WHERE RuleName=:rule AND IsSimulated=:sim AND CurrentStart=:start'''),params)
                elif existing and existing['State'] in ('NEW','ATTENDED'):
                    conn.execute(text("UPDATE notify.Alert SET State='RESOLVED',UpdatedAt=SYSUTCDATETIME() WHERE AlertID=:id"),{'id':existing['AlertID']})
                    conn.execute(text("INSERT notify.StateHistory(AlertID,PreviousState,NewState) VALUES(:id,:old,'RESOLVED')"),{'id':existing['AlertID'],'old':existing['State']})
            conn.execute(text('INSERT notify.Evaluation(TaskID,Outcome,Explanation) VALUES(:id,:outcome,:explanation)'),{'id':task_id,'outcome':outcome,'explanation':explanation})
            conn.execute(text("UPDATE notify.Task SET Status='SUCCEEDED',Attempts=Attempts+1,LastError=NULL,CompletedAt=SYSUTCDATETIME() WHERE TaskID=:id"),{'id':task_id})
            return {'task_id':str(task_id),'status':'SUCCEEDED','outcome':outcome,'drop_percent':str(drop) if drop is not None else None}
    except Exception as exc:
        # Notification failure cannot invalidate an already committed ETL/watermark.
        code='SIMULATED_NOTIFICATION_FAILURE' if str(exc)=='SIMULATED_NOTIFICATION_FAILURE' else 'NOTIFICATION_PROCESSING_FAILED'
        try:
            with db.begin() as conn:
                conn.execute(text("UPDATE notify.Task SET Status='FAILED',Attempts=Attempts+1,LastError=:error WHERE TaskID=:id AND Status<>'SUCCEEDED'"),{'id':task_id,'error':code})
        except Exception:
            return {'task_id':str(task_id),'status':'PENDING','error':'NOTIFICATION_STATUS_UNAVAILABLE_RETRY'}
        return {'task_id':str(task_id),'status':'FAILED','error':code}

def retry(warehouse_database=None):
    with engine(warehouse_database).connect() as conn:
        ids=conn.execute(text("SELECT TaskID FROM notify.Task WHERE Status IN('PENDING','FAILED') ORDER BY CreatedAt")).scalars().all()
    return [process(str(id),warehouse_database) for id in ids]

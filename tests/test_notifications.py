"""Eventos simulados en bases aisladas; nunca se modifica la fuente principal."""
import json
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from deployment.bootstrap import main as bootstrap
from etl.connection import engine,ROOT
from etl.pipeline import PROJECTIONS,identifier,run_pipeline,PipelineError
from notifications.service import evaluate,process,retry,snapshot

@pytest.mark.parametrize('observed,reference,outcome',[('84','100','TRIGGERED'),('85','100','CLEAR'),('100','100','CLEAR'),('110','100','CLEAR')])
def test_threshold(observed,reference,outcome):
    assert evaluate({'eligible':True,'reference':reference,'observed':observed,'threshold':'15'})[0]==outcome

def test_zero_reference():
    assert evaluate({'eligible':False,'reason':'Referencia cero'})[0]=='SKIPPED'

@pytest.fixture(scope='module')
def platform():
    suffix=datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid4().hex[:6]
    src='WWI_Test_Alerts_'+suffix;dst='SalesAnalytics_Test_Alerts_'+suffix
    with engine('master','admin').connect().execution_options(isolation_level='AUTOCOMMIT') as c:
        for db in (src,dst):c.exec_driver_sql('CREATE DATABASE '+identifier(db))
    predicate="InvoiceDate BETWEEN '20130101' AND '20130121'"
    invoices=f'SELECT InvoiceID FROM WideWorldImporters.Sales.Invoices WHERE {predicate}'
    with engine(src,'admin').begin() as c:
        c.exec_driver_sql('CREATE SCHEMA Sales');c.exec_driver_sql('CREATE SCHEMA Warehouse')
        for name,(table,columns) in PROJECTIONS.items():
            where=''
            if name=='Invoices':where=' WHERE '+predicate
            elif name=='InvoiceLines':where=f' WHERE InvoiceID IN ({invoices})'
            elif name=='Customers':where=f' WHERE CustomerID IN (SELECT CustomerID FROM WideWorldImporters.Sales.Invoices WHERE {predicate})'
            elif name=='StockItems':where=f' WHERE StockItemID IN (SELECT StockItemID FROM WideWorldImporters.Sales.InvoiceLines WHERE InvoiceID IN ({invoices}))'
            c.exec_driver_sql(f'SELECT {columns} INTO {table} FROM WideWorldImporters.{table}'+where)
    bootstrap(warehouse_database=dst,source_database=src)
    return {'source':src,'dw':dst}

def amount(p,current):
    with engine(p['source'],'admin').begin() as c:
        c.execute(text('''UPDATE l SET UnitPrice=CASE WHEN i.InvoiceDate BETWEEN '20130114' AND '20130120' THEN :price ELSE 1 END,
          TaxAmount=ROUND(l.Quantity*(CASE WHEN i.InvoiceDate BETWEEN '20130114' AND '20130120' THEN :price ELSE 1 END)*l.TaxRate/100,2),
          ExtendedPrice=l.Quantity*(CASE WHEN i.InvoiceDate BETWEEN '20130114' AND '20130120' THEN :price ELSE 1 END)+ROUND(l.Quantity*(CASE WHEN i.InvoiceDate BETWEEN '20130114' AND '20130120' THEN :price ELSE 1 END)*l.TaxRate/100,2),
          LastEditedWhen=SYSUTCDATETIME() FROM Sales.InvoiceLines l JOIN Sales.Invoices i ON i.InvoiceID=l.InvoiceID'''),{'price':Decimal(current)})

def run(p,**kw):return run_pipeline(source_database=p['source'],warehouse_database=p['dw'],simulated=True,evidence_dir=ROOT/'data/test-evidence',**kw)
def scalar(p,sql):
    with engine(p['dw']).connect() as c:return c.execute(text(sql)).scalar_one()

def test_integrated_alert_recovery_and_delivery(platform):
    p=platform;reports=[]
    amount(p,'0.20');initial=run(p,full=True);reports.append(initial)
    assert initial['notification']['outcome']=='TRIGGERED'
    assert scalar(p,'SELECT COUNT(*) FROM notify.Alert')==1
    assert scalar(p,'SELECT COUNT(*) FROM notify.Alert WHERE IsSimulated=1')==1
    assert scalar(p,"SELECT COUNT(*) FROM notify.Alert WHERE DeliveryStatus='PENDING'")==1
    # Duplicate worker and duplicate load must not create a second alert.
    assert process(initial['notification']['task_id'],p['dw'])['already_processed']
    reports.append(run(p));assert scalar(p,'SELECT COUNT(*) FROM notify.Alert')==1
    with engine(p['dw']).connect() as c:id=str(c.execute(text('SELECT AlertID FROM notify.Alert')).scalar_one())
    # Actual rolled-back delivery transaction, clearly simulated, then retry.
    with pytest.raises(RuntimeError):
        with engine(p['dw'],role='app').begin() as c:
            c.execute(text('EXEC notify.MarkSeen @id=:id'),{'id':id})
            raise RuntimeError('SIMULATED_DELIVERY_FAILURE')
    assert scalar(p,"SELECT COUNT(*) FROM notify.Alert WHERE DeliveryStatus='PENDING'")==1
    with engine(p['dw'],role='app').begin() as c:
        c.execute(text('EXEC notify.MarkSeen @id=:id'),{'id':id})
        c.execute(text('EXEC notify.MarkSeen @id=:id'),{'id':id})
        c.execute(text("EXEC notify.ChangeState @id=:id,@state='ATTENDED'"),{'id':id})
    assert scalar(p,"SELECT COUNT(*) FROM notify.Alert WHERE DeliveryStatus='DELIVERED' AND State='ATTENDED'")==1
    assert scalar(p,'SELECT COUNT(*) FROM notify.StateHistory')==1
    # Controlled ETL failure cannot enqueue notifications or advance watermark.
    count=scalar(p,'SELECT COUNT(*) FROM notify.Task');watermark=scalar(p,'SELECT WatermarkValue FROM audit.Watermark')
    amount(p,'2')
    with pytest.raises(PipelineError):run(p,fail_at='before_commit')
    assert scalar(p,'SELECT COUNT(*) FROM notify.Task')==count
    assert scalar(p,'SELECT WatermarkValue FROM audit.Watermark')==watermark
    # Force a worker failure after a successful load using a narrowly scoped monkeypatch.
    import etl.pipeline as pipeline
    real=pipeline.process
    try:
        pipeline.process=lambda task,db:process(task,db,fail=True)
        recovered=run(p);reports.append(recovered)
    finally:pipeline.process=real
    assert recovered['status']=='SUCCEEDED' and recovered['notification']['status']=='FAILED'
    assert scalar(p,'SELECT WatermarkValue FROM audit.Watermark')>watermark
    assert scalar(p,"SELECT Status FROM audit.Execution WHERE ExecutionID='"+recovered['execution_id']+"'")=='SUCCEEDED'
    retried=retry(p['dw']);assert retried[-1]['outcome']=='CLEAR'
    assert scalar(p,"SELECT COUNT(*) FROM notify.Alert WHERE State='RESOLVED'")==1
    assert scalar(p,"SELECT Attempts FROM notify.Task WHERE TaskID='"+recovered['notification']['task_id']+"'")==2
    with engine(p['dw']).connect() as c:checked=snapshot(c)
    assert checked['current_start']=='2013-01-14' and checked['current_end']=='2013-01-20'
    assert checked['reference_start']=='2013-01-07' and checked['reference_end']=='2013-01-13'
    evidence=Path(os.getenv('TEST_EVIDENCE_DIR',str(ROOT/'documentation/evidence')))
    evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'alert-tests.json').write_text(json.dumps({'simulation':True,'source':p['source'],'warehouse':p['dw'],
        'runs':reports,'retry':retried,'snapshot':checked,'checks':['true','false','threshold','deduplication','ETL rollback has no task','worker failure preserves ETL','retry resolves alert','delivery acknowledgement idempotent','operator history']},default=str,indent=2),encoding='utf-8')

@pytest.mark.parametrize('role,sql',[('api','UPDATE notify.Alert SET State=State'),('app','SELECT * FROM raw.InvoiceLines'),('app','UPDATE dw.FactSales SET Quantity=Quantity')])
def test_alert_permissions(platform,role,sql):
    with pytest.raises(DBAPIError) as caught:
        with engine(platform['dw'],role).begin() as c:c.execute(text(sql))
    assert '229' in str(caught.value.orig)

def test_http_alert_validation():
    from fastapi.testclient import TestClient
    from backend.main import app
    client=TestClient(app);headers={'X-API-Key':os.environ['DEMO_API_KEY']}
    assert client.get('/api/alerts').status_code==401
    assert client.post('/api/alerts/not-a-uuid/seen',headers=headers).status_code==422
    assert client.post('/api/alerts/'+str(uuid4())+'/state',headers=headers,json={'state':'DROP'}).status_code==422

def test_recurrence_and_old_retry_cannot_override_newer_snapshot(platform):
    p=platform
    amount(p,'0.20');assert run(p)['notification']['outcome']=='TRIGGERED'
    assert scalar(p,"SELECT COUNT(*) FROM notify.Alert WHERE State='NEW'")==1
    assert scalar(p,'SELECT COUNT(*) FROM notify.Alert')==1
    import etl.pipeline as pipeline
    amount(p,'2');real=pipeline.process
    try:
        pipeline.process=lambda task,db:process(task,db,fail=True)
        older=run(p)
    finally:pipeline.process=real
    amount(p,'0.20');assert run(p)['notification']['outcome']=='TRIGGERED'
    result=process(older['notification']['task_id'],p['dw'])
    assert result['outcome']=='SUPERSEDED'
    assert scalar(p,"SELECT COUNT(*) FROM notify.Alert WHERE State='NEW'")==1

def test_worker_total_connection_failure_is_recoverable(monkeypatch):
    import notifications.service as service
    class Offline:
        def connect(self):raise RuntimeError('SIMULATED_DATABASE_UNAVAILABLE')
        def begin(self):raise RuntimeError('SIMULATED_DATABASE_UNAVAILABLE')
    monkeypatch.setattr(service,'engine',lambda *args:Offline())
    result=service.process(str(uuid4()))
    assert result['status']=='PENDING' and result['error']=='NOTIFICATION_STATUS_UNAVAILABLE_RETRY'

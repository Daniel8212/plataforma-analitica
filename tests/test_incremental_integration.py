"""Cambios simulados exclusivamente en dos bases Test únicas; fuente principal intacta."""
import json
import os
from datetime import datetime
from uuid import uuid4
import pytest
from sqlalchemy import text
from deployment.bootstrap import main as bootstrap
from etl.connection import engine, ROOT
from etl.pipeline import PROJECTIONS, PipelineError, identifier, run_pipeline

@pytest.fixture(scope='module')
def platform():
    suffix=datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid4().hex[:6]
    src='WWI_Test_'+suffix
    dst='SalesAnalytics_Test_'+suffix
    with engine('master','admin').connect().execution_options(isolation_level='AUTOCOMMIT') as c:
        for database in (src,dst):
            assert c.execute(text('SELECT DB_ID(:name)'),{'name':database}).scalar() is None
            c.exec_driver_sql('CREATE DATABASE '+identifier(database))
    with engine(src,'admin').begin() as c:
        c.exec_driver_sql('CREATE SCHEMA Sales')
        c.exec_driver_sql('CREATE SCHEMA Warehouse')
        for name,(table,columns) in PROJECTIONS.items():
            predicate=''
            if name in ('Invoices','InvoiceLines'):
                predicate=' WHERE InvoiceID IN (1,2,3)'
            elif name=='Customers':
                predicate=' WHERE CustomerID IN (SELECT CustomerID FROM WideWorldImporters.Sales.Invoices WHERE InvoiceID IN (1,2,3))'
            elif name=='StockItems':
                predicate=' WHERE StockItemID IN (SELECT StockItemID FROM WideWorldImporters.Sales.InvoiceLines WHERE InvoiceID IN (1,2,3))'
            c.exec_driver_sql(f'SELECT {columns} INTO {table} FROM WideWorldImporters.{table}'+predicate)
    bootstrap(warehouse_database=dst,source_database=src)
    reports=[]
    def run(**kwargs):
        try:
            result=run_pipeline(source_database=src,warehouse_database=dst,simulated=True,
                evidence_dir=ROOT/'data/test-evidence',**kwargs)
        except PipelineError as error:
            reports.append(error.report)
            raise
        reports.append(result)
        return result
    yield {'source':src,'dw':dst,'run':run}
    out={'simulation':True,'source_database':src,'warehouse_database':dst,'runs':reports,
         'note':'Cambios solo en bases aisladas. Se conservan para inspección; no se elimina ninguna base de usuario.'}
    (ROOT/'documentation/evidence/incremental-tests.json').write_text(json.dumps(out,default=str,indent=2),encoding='utf-8')

@pytest.fixture()
def p(platform):
    src=platform['source']
    assert src.startswith('WWI_Test_')
    with engine(src,'admin').begin() as c:
        for name,(table,columns) in PROJECTIONS.items():
            c.exec_driver_sql('DELETE FROM '+table)
            predicate=''
            if name in ('Invoices','InvoiceLines'):
                predicate=' WHERE InvoiceID IN (1,2,3)'
            elif name=='Customers':
                predicate=' WHERE CustomerID IN (SELECT CustomerID FROM WideWorldImporters.Sales.Invoices WHERE InvoiceID IN (1,2,3))'
            elif name=='StockItems':
                predicate=' WHERE StockItemID IN (SELECT StockItemID FROM WideWorldImporters.Sales.InvoiceLines WHERE InvoiceID IN (1,2,3))'
            c.exec_driver_sql(f'INSERT {table}({columns}) SELECT {columns} FROM WideWorldImporters.{table}'+predicate)
    platform['run'](full=True)
    return platform

def scalar(p,sql,params=None,source=False):
    with engine(p['source'] if source else p['dw'],'admin' if source else 'etl').connect() as c:
        return c.execute(text(sql),params or {}).scalar()

def change(p,sql,params=None):
    with engine(p['source'],'admin').begin() as c:
        c.execute(text(sql),params or {})

def correction(p,backdated=False):
    stamp="'19000101'" if backdated else 'SYSUTCDATETIME()'
    change(p,f'''UPDATE Sales.InvoiceLines SET UnitPrice=UnitPrice+1,
        TaxAmount=ROUND(Quantity*(UnitPrice+1)*TaxRate/100,2),
        ExtendedPrice=Quantity*(UnitPrice+1)+ROUND(Quantity*(UnitPrice+1)*TaxRate/100,2),LastEditedWhen={stamp}
        WHERE InvoiceLineID=1''')

def late_line(p,line_id=9999999):
    cols=PROJECTIONS['InvoiceLines'][1].split(',')
    expressions=[":id" if x=='InvoiceLineID' else "CONVERT(datetime2,'19000101')" if x=='LastEditedWhen' else x for x in cols]
    change(p,f"INSERT Sales.InvoiceLines({','.join(cols)}) SELECT {','.join(expressions)} FROM Sales.InvoiceLines WHERE InvoiceLineID=1",{'id':line_id})

def test_update_late_row_and_idempotence(p):
    baseline=scalar(p,"SELECT COUNT(*) FROM dw.FactSales WHERE RecordStatus='ACTIVE'")
    correction(p)
    updated=p['run']()
    assert updated['updated']==1 and updated['inserted']==0
    late_line(p)
    late=p['run']()
    assert late['inserted']==1 and late['dw']['rows']==baseline+1
    replay=p['run']()
    assert replay['inserted']==replay['updated']==0 and replay['actions']=={}

@pytest.mark.parametrize('point',['after_raw','after_publish','before_commit'])
def test_failure_rolls_back_dw_and_watermark_then_recovers(p,point):
    before=scalar(p,"SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")
    sales=scalar(p,"SELECT SUM(SalesAmount) FROM dw.FactSales WHERE RecordStatus='ACTIVE'")
    versions=scalar(p,'SELECT COUNT(*) FROM dw.DimCustomer')
    customer=scalar(p,'SELECT CustomerID FROM Sales.Invoices WHERE InvoiceID=1',source=True)
    change(p,"INSERT Sales.CustomerCategories VALUES(88888,N'Segmento de recuperación simulada',SYSUTCDATETIME(),CONVERT(datetime2,'9999-12-31'))")
    change(p,'UPDATE Sales.Customers SET CustomerCategoryID=88888 WHERE CustomerID=:id',{'id':customer})
    correction(p)
    with pytest.raises(PipelineError) as caught:
        p['run'](fail_at=point)
    failed=caught.value.report
    assert failed['simulated'] and failed['status']=='FAILED'
    assert scalar(p,"SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")==before
    assert scalar(p,"SELECT SUM(SalesAmount) FROM dw.FactSales WHERE RecordStatus='ACTIVE'")==sales
    assert scalar(p,'SELECT COUNT(*) FROM dw.DimCustomer')==versions
    assert scalar(p,'SELECT COUNT(*) FROM raw.InvoiceLines WHERE ExecutionID=:id',{'id':failed['execution_id']})>0
    assert scalar(p,'SELECT Status FROM audit.Execution WHERE ExecutionID=:id',{'id':failed['execution_id']})=='FAILED'
    recovered=p['run']()
    assert recovered['updated']==1 and recovered['watermark_after']>before
    assert recovered['actions']['CUSTOMER_INSERT']==1
    assert p['run']()['updated']==0

@pytest.mark.parametrize('assignment,rule',[('UnitPrice=NULL','Q03_PRICE_NULL'),('StockItemID=9999999','Q02_PRODUCT')])
def test_quarantine_and_recovery(p,assignment,rule):
    baseline=scalar(p,"SELECT COUNT(*) FROM dw.FactSales WHERE RecordStatus='ACTIVE'")
    change(p,'UPDATE Sales.InvoiceLines SET '+assignment+',LastEditedWhen=SYSUTCDATETIME() WHERE InvoiceLineID=1')
    result=p['run']()
    assert result['quarantine']['rows']==1 and result['dw']['rows']==baseline-1
    assert scalar(p,'SELECT RuleID FROM audit.Quarantine WHERE ExecutionID=:id',{'id':result['execution_id']})==rule
    assert scalar(p,'SELECT RecordStatus FROM dw.FactSales WHERE InvoiceLineID=1')=='QUARANTINED'
    change(p,'''UPDATE f SET UnitPrice=o.UnitPrice,StockItemID=o.StockItemID,LastEditedWhen=SYSUTCDATETIME()
        FROM Sales.InvoiceLines f JOIN WideWorldImporters.Sales.InvoiceLines o ON o.InvoiceLineID=f.InvoiceLineID WHERE f.InvoiceLineID=1''')
    recovered=p['run']()
    assert recovered['updated']==1 and recovered['dw']['rows']==baseline

def test_scd2_preserves_observed_category(p,monkeypatch):
    key=scalar(p,'SELECT CustomerKey FROM dw.FactSales WHERE InvoiceLineID=1')
    customer=scalar(p,'SELECT CustomerID FROM Sales.Invoices WHERE InvoiceID=1',source=True)
    versions=scalar(p,'SELECT COUNT(*) FROM dw.DimCustomer WHERE CustomerID=:id',{'id':customer})
    change(p,"INSERT Sales.CustomerCategories VALUES(99999,N'Segmento simulado',SYSUTCDATETIME(),CONVERT(datetime2,'9999-12-31'))")
    change(p,'UPDATE Sales.Customers SET CustomerCategoryID=99999,ValidFrom=SYSUTCDATETIME() WHERE CustomerID=:id',{'id':customer})
    changed=p['run']()
    assert changed['actions']['CUSTOMER_INSERT']==1 and changed['actions']['CUSTOMER_EXPIRE']==1
    assert scalar(p,'SELECT COUNT(*) FROM dw.DimCustomer WHERE CustomerID=:id',{'id':customer})==versions+1
    assert scalar(p,'SELECT IsCurrent FROM dw.DimCustomer WHERE CustomerKey=:key',{'key':key}) is False
    assert scalar(p,'SELECT CustomerKey FROM dw.FactSales WHERE InvoiceLineID=1')==key
    late_line(p,line_id=9999998)
    p['run']()
    assert scalar(p,'SELECT CustomerKey FROM dw.FactSales WHERE InvoiceLineID=9999998')!=key
    # La API también debe conservar el segmento anterior de las facturas ya cargadas.
    import backend.analytics as analytics
    from backend.main import app
    from fastapi.testclient import TestClient
    monkeypatch.setattr(analytics,'engine',lambda database=None,role='etl':engine(p['dw'],role))
    with TestClient(app) as client:
        response=client.get('/api/kpis?category_id=99999',headers={'X-API-Key':os.environ['DEMO_API_KEY']})
        assert response.status_code==200 and response.json()['line_count']==1
    assert scalar(p,'''SELECT COUNT(*) FROM dw.DimCustomer a JOIN dw.DimCustomer b ON a.CustomerID=b.CustomerID
        AND a.CustomerKey<b.CustomerKey AND a.ObservedFrom<b.ObservedTo AND b.ObservedFrom<a.ObservedTo''')==0
    assert p['run']()['actions']=={}

def test_deletion_is_soft_audited_and_reappearance_recovers(p):
    baseline=scalar(p,"SELECT COUNT(*) FROM dw.FactSales WHERE RecordStatus='ACTIVE'")
    change(p,'DELETE FROM Sales.InvoiceLines WHERE InvoiceLineID=1')
    deleted=p['run']()
    assert deleted['actions']['DELETE']==1 and deleted['dw']['rows']==baseline-1
    assert scalar(p,'SELECT RecordStatus FROM dw.FactSales WHERE InvoiceLineID=1')=='DELETED'
    assert scalar(p,'SELECT COUNT(*) FROM audit.Deletion WHERE ExecutionID=:id',{'id':deleted['execution_id']})==1
    assert p['run']()['actions']=={}
    columns=PROJECTIONS['InvoiceLines'][1]
    change(p,f'INSERT Sales.InvoiceLines({columns}) SELECT {columns} FROM WideWorldImporters.Sales.InvoiceLines WHERE InvoiceLineID=1')
    restored=p['run']()
    assert restored['inserted']==0 and restored['updated']==1 and restored['dw']['rows']==baseline

def test_outside_overlap_is_detected_and_full_repairs(p):
    before=scalar(p,"SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")
    correction(p,backdated=True)
    with pytest.raises(PipelineError) as caught:
        p['run']()
    assert 'SOURCE_DW_ROW_MISMATCH' in caught.value.report['error_code']
    assert scalar(p,"SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")==before
    assert p['run'](full=True)['updated']==1

def test_header_change_updates_all_its_lines(p):
    n=scalar(p,'SELECT COUNT(*) FROM Sales.InvoiceLines WHERE InvoiceID=1',source=True)
    customer=scalar(p,'SELECT TOP(1) CustomerID FROM Sales.Customers WHERE CustomerID<>(SELECT CustomerID FROM Sales.Invoices WHERE InvoiceID=1) ORDER BY CustomerID',source=True)
    assert customer is not None
    change(p,'UPDATE Sales.Invoices SET CustomerID=:customer,InvoiceDate=DATEADD(day,1,InvoiceDate),LastEditedWhen=SYSUTCDATETIME() WHERE InvoiceID=1',{'customer':customer})
    result=p['run']()
    assert result['updated']==n
    assert scalar(p,"SELECT MIN(d.FullDate) FROM dw.FactSales f JOIN dw.DimDate d ON d.DateKey=f.DateKey WHERE f.InvoiceID=1 AND f.RecordStatus='ACTIVE'")==scalar(p,'SELECT InvoiceDate FROM Sales.Invoices WHERE InvoiceID=1',source=True)
    assert scalar(p,"SELECT COUNT(*) FROM dw.FactSales f JOIN dw.DimCustomer c ON c.CustomerKey=f.CustomerKey WHERE f.InvoiceID=1 AND f.RecordStatus='ACTIVE' AND c.CustomerID=:customer",{'customer':customer})==n

def test_future_watermark_never_moves_backwards(p):
    before=scalar(p,"SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")
    with engine(p['dw']).begin() as c:
        c.execute(text("UPDATE audit.Watermark SET WatermarkValue=DATEADD(day,1,SYSUTCDATETIME()) WHERE PipelineName='sales'"))
    future=scalar(p,"SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")
    try:
        with pytest.raises(PipelineError) as caught:
            p['run']()
        assert caught.value.report['error_code']=='SOURCE_CLOCK_OR_WATERMARK_IN_FUTURE'
        assert scalar(p,"SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")==future
    finally:
        with engine(p['dw']).begin() as c:
            c.execute(text("UPDATE audit.Watermark SET WatermarkValue=:value WHERE PipelineName='sales'"),{'value':before})

def test_duplicate_source_key_fails_without_arbitrary_survivor(p):
    before=scalar(p,"SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")
    count=scalar(p,"SELECT COUNT(*) FROM dw.FactSales WHERE RecordStatus='ACTIVE'")
    columns=PROJECTIONS['InvoiceLines'][1]
    change(p,f'INSERT Sales.InvoiceLines({columns}) SELECT {columns} FROM Sales.InvoiceLines WHERE InvoiceLineID=1')
    with pytest.raises(PipelineError) as incremental_error:
        p['run']()
    assert incremental_error.value.report['error_code']=='SOURCE_DW_TOTAL_MISMATCH'
    with pytest.raises(PipelineError) as caught:
        p['run'](full=True)
    assert '2627' in caught.value.report['error_code']
    assert scalar(p,"SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")==before
    assert scalar(p,"SELECT COUNT(*) FROM dw.FactSales WHERE RecordStatus='ACTIVE'")==count
    change(p,'DELETE FROM Sales.InvoiceLines WHERE InvoiceLineID=1')
    change(p,f'INSERT Sales.InvoiceLines({columns}) SELECT {columns} FROM WideWorldImporters.Sales.InvoiceLines WHERE InvoiceLineID=1')
    recovered=p['run']()
    assert recovered['inserted']==recovered['updated']==0

"""Batch incremental: originales durables, SCD observado y publicación/watermark atómicos."""
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text
from etl.connection import ROOT, engine
from notifications.service import enqueue,process

PROJECTIONS = {
 'Invoices': ('Sales.Invoices','InvoiceID,CustomerID,InvoiceDate,IsCreditNote,LastEditedWhen'),
 'InvoiceLines': ('Sales.InvoiceLines','InvoiceLineID,InvoiceID,StockItemID,Description,Quantity,UnitPrice,TaxRate,TaxAmount,LineProfit,ExtendedPrice,LastEditedWhen'),
 'Customers': ('Sales.Customers','CustomerID,CustomerName,CustomerCategoryID,ValidFrom,ValidTo'),
 'CustomerCategories': ('Sales.CustomerCategories','CustomerCategoryID,CustomerCategoryName,ValidFrom,ValidTo'),
 'StockItems': ('Warehouse.StockItems','StockItemID,StockItemName,Brand,IsChillerStock,ValidFrom,ValidTo'),
}

class PipelineError(RuntimeError):
    def __init__(self, report):
        self.report = report
        super().__init__(f"Carga fallida: {report['execution_id']} / {report['error_code']}")

def identifier(value):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,100}',value):
        raise ValueError('Nombre de base inválido')
    return '['+value+']'

def total(conn, sql, params):
    row = conn.execute(text(sql),params).mappings().one()
    return {'rows':int(row['n']),'sales':row['amount']}

def source_valid_sql(source):
    # Reglas independientes del snapshot raw: comparación exhaustiva contra fuente actual.
    return f'''SELECT l.InvoiceLineID,l.InvoiceID,i.InvoiceDate,c.CustomerID,l.StockItemID,
        l.Quantity,l.UnitPrice,CONVERT(decimal(18,2),l.Quantity*l.UnitPrice) SalesAmount,
        l.TaxAmount,l.ExtendedPrice,l.LineProfit
        FROM {source}.Sales.InvoiceLines l JOIN {source}.Sales.Invoices i ON i.InvoiceID=l.InvoiceID
        JOIN {source}.Sales.Customers c ON c.CustomerID=i.CustomerID
        JOIN {source}.Sales.CustomerCategories cat ON cat.CustomerCategoryID=c.CustomerCategoryID
        JOIN {source}.Warehouse.StockItems p ON p.StockItemID=l.StockItemID
        WHERE l.UnitPrice IS NOT NULL AND l.Quantity>0 AND l.UnitPrice>=0 AND l.TaxRate>=0
        AND l.TaxAmount>=0 AND i.IsCreditNote=0
        AND l.ExtendedPrice=ROUND(l.Quantity*l.UnitPrice,2)+l.TaxAmount
        AND LTRIM(RTRIM(c.CustomerName))<>N'' AND LTRIM(RTRIM(p.StockItemName))<>N'' '''

DW_VALID_SQL = '''SELECT f.InvoiceLineID,f.InvoiceID,d.FullDate,c.CustomerID,p.StockItemID,
 f.Quantity,f.UnitPrice,f.SalesAmount,f.TaxAmount,f.ExtendedPrice,f.LineProfit
 FROM dw.FactSales f JOIN dw.DimDate d ON d.DateKey=f.DateKey
 JOIN dw.DimCustomer c ON c.CustomerKey=f.CustomerKey JOIN dw.DimProduct p ON p.ProductKey=f.ProductKey
 WHERE f.RecordStatus='ACTIVE' '''

def reconcile(conn, source):
    source_sql = source_valid_sql(source)
    for left,right in ((source_sql,DW_VALID_SQL),(DW_VALID_SQL,source_sql)):
        if conn.execute(text(f'SELECT TOP(1) 1 FROM ({left} EXCEPT {right}) difference')).scalar():
            raise RuntimeError('SOURCE_DW_ROW_MISMATCH_USE_FULL_RECONCILIATION')
    expected=total(conn,f'SELECT COUNT_BIG(*) n,COALESCE(SUM(SalesAmount),0) amount FROM ({source_sql}) s',{})
    actual=total(conn,"SELECT COUNT_BIG(*) n,COALESCE(SUM(SalesAmount),0) amount FROM dw.FactSales WHERE RecordStatus='ACTIVE'",{})
    if expected!=actual:
        raise RuntimeError('SOURCE_DW_TOTAL_MISMATCH')
    return actual

def run_pipeline(*, full=False, source_database=None, warehouse_database=None,
                 overlap_hours=48, fail_at=None, simulated=False, evidence_dir=None):
    if not 1<=overlap_hours<=720:
        raise ValueError('Solapamiento permitido: 1–720 horas')
    if fail_at not in (None,'after_raw','after_publish','before_commit'):
        raise ValueError('Punto de falla desconocido')
    source = identifier(source_database or os.environ['SOURCE_DATABASE'])
    warehouse = warehouse_database or os.environ['DW_DATABASE']
    identifier(warehouse)
    if source == identifier(warehouse):
        raise ValueError('Fuente y DW deben ser diferentes')
    run = str(uuid4())
    params = {'execution_id':run}
    report = {'execution_id':run,'mode':'full' if full else 'incremental',
              'simulated':bool(simulated or fail_at),'source_database':source_database or os.environ['SOURCE_DATABASE'],
              'warehouse_database':warehouse}
    output = Path(evidence_dir or ROOT/'documentation/evidence')
    output.mkdir(parents=True,exist_ok=True)
    def save():
        (output/f"incremental-{run}.json").write_text(json.dumps(report,default=str,indent=2),encoding='utf-8')
    with engine(warehouse).connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        lock=conn.execute(text("DECLARE @r int; EXEC @r=sys.sp_getapplock @Resource='sales_pipeline',@LockMode='Exclusive',@LockOwner='Session',@LockTimeout=0; SELECT @r")).scalar_one()
        conn.commit()
        if lock<0:
            raise RuntimeError('PIPELINE_ALREADY_RUNNING')
        try:
            with conn.begin():
                upper=conn.execute(text('SELECT SYSUTCDATETIME()')).scalar_one()
                previous=conn.execute(text("SELECT WatermarkValue FROM audit.Watermark WHERE PipelineName='sales'")).scalar()
                if previous is None:
                    previous=conn.execute(text('''SELECT MAX(v) FROM (
                        SELECT MAX(LastEditedWhen) v FROM raw.InvoiceLines WHERE ExecutionID=(SELECT TOP(1) ExecutionID FROM audit.Execution WHERE Status='SUCCEEDED' ORDER BY EndTime DESC)
                        UNION ALL SELECT MAX(LastEditedWhen) FROM raw.Invoices WHERE ExecutionID=(SELECT TOP(1) ExecutionID FROM audit.Execution WHERE Status='SUCCEEDED' ORDER BY EndTime DESC)
                        ) initial_baseline''')).scalar() or datetime(1900,1,1)
                lower=previous-timedelta(hours=overlap_hours)
                params.update(lower=lower,upper=upper,observed_at=upper,full=int(full))
                conn.execute(text('''INSERT audit.Execution(ExecutionID,PipelineName,Status,LoadMode,IsSimulated,WatermarkStart,WatermarkEnd)
                    VALUES(:execution_id,'sales','RUNNING',:mode,:simulated,:lower,:upper)'''),
                    {**params,'mode':report['mode'],'simulated':report['simulated']})
                report.update(watermark_before=previous,window_start=lower,window_end=upper)
            try:
                if upper<previous:
                    raise RuntimeError('SOURCE_CLOCK_OR_WATERMARK_IN_FUTURE')
                with conn.begin():
                    conn.execute(text('CREATE TABLE #SelectedLines(InvoiceLineID int NOT NULL PRIMARY KEY)'))
                    conn.execute(text(f'''INSERT #SelectedLines SELECT l.InvoiceLineID FROM {source}.Sales.InvoiceLines l
                        LEFT JOIN {source}.Sales.Invoices i ON i.InvoiceID=l.InvoiceID
                        WHERE l.LastEditedWhen<=:upper AND (i.LastEditedWhen<=:upper OR i.InvoiceID IS NULL)
                        AND (:full=1 OR l.LastEditedWhen>=:lower OR i.LastEditedWhen>=:lower OR i.InvoiceID IS NULL
                        OR NOT EXISTS(SELECT 1 FROM dw.FactSales f WHERE f.InvoiceLineID=l.InvoiceLineID AND f.RecordStatus='ACTIVE'))'''),params)
                    counts={}
                    for target,(table,columns) in PROJECTIONS.items():
                        predicate=''
                        if target=='InvoiceLines':
                            predicate=' WHERE EXISTS(SELECT 1 FROM #SelectedLines k WHERE k.InvoiceLineID=s.InvoiceLineID)'
                        elif target=='Invoices':
                            predicate=f' WHERE EXISTS(SELECT 1 FROM {source}.Sales.InvoiceLines l JOIN #SelectedLines k ON k.InvoiceLineID=l.InvoiceLineID WHERE l.InvoiceID=s.InvoiceID)'
                        conn.execute(text(f'INSERT raw.{target}(ExecutionID,{columns}) SELECT :execution_id,{columns} FROM {source}.{table} s'+predicate),params)
                        n=conn.execute(text(f'SELECT COUNT_BIG(*) FROM raw.{target} WHERE ExecutionID=:execution_id'),params).scalar_one()
                        counts[target]=n
                        conn.execute(text('''INSERT audit.StageCount(ExecutionID,Stage,SourceObject,TargetObject,RowsRead,RowsInserted)
                            VALUES(:execution_id,'raw',:source,:target,:n,:n)'''),{**params,'source':table,'target':'raw.'+target,'n':n})
                    # FK de fuente válida pero cliente invisible implica cobertura/RLS, no venta inexistente.
                    if conn.execute(text(f'''SELECT TOP(1) 1 FROM {source}.Sales.Invoices i
                        LEFT JOIN raw.Customers c ON c.CustomerID=i.CustomerID AND c.ExecutionID=:execution_id
                        WHERE c.CustomerID IS NULL'''),params).scalar():
                        raise RuntimeError('SOURCE_CUSTOMER_VISIBILITY_INCOMPLETE')
                    conn.execute(text('UPDATE audit.Execution SET RowsRead=:n WHERE ExecutionID=:execution_id'),{**params,'n':sum(counts.values())})
                    source_delta=total(conn,f'''SELECT COUNT_BIG(*) n,COALESCE(SUM(l.ExtendedPrice-l.TaxAmount),0) amount
                        FROM {source}.Sales.InvoiceLines l JOIN #SelectedLines k ON k.InvoiceLineID=l.InvoiceLineID''',params)
                    raw_delta=total(conn,'SELECT COUNT_BIG(*) n,COALESCE(SUM(ExtendedPrice-TaxAmount),0) amount FROM raw.InvoiceLines WHERE ExecutionID=:execution_id',params)
                    if source_delta!=raw_delta:
                        raise RuntimeError('SOURCE_RAW_MISMATCH')
                    conn.execute(text('DROP TABLE #SelectedLines'))
                    report.update(raw_counts=counts,source_delta=source_delta,raw_delta=raw_delta)
                if fail_at=='after_raw':
                    raise RuntimeError('SIMULATED_FAILURE_AFTER_RAW')
                # Validación durable: los rechazos quedan disponibles incluso si falla publicación.
                with conn.begin():
                    conn.execute(text((ROOT/'database/006_validate_batch.sql').read_text(encoding='utf-8')),params)
                    clean=total(conn,'SELECT COUNT_BIG(*) n,COALESCE(SUM(SalesAmount),0) amount FROM clean.SalesLine WHERE ExecutionID=:execution_id',params)
                    rejected=total(conn,'''SELECT COUNT_BIG(*) n,COALESCE(SUM(r.ExtendedPrice-r.TaxAmount),0) amount
                        FROM audit.Quarantine q JOIN raw.InvoiceLines r ON r.ExecutionID=q.ExecutionID AND r.InvoiceLineID=q.SourceKey WHERE q.ExecutionID=:execution_id''',params)
                    if clean['rows']+rejected['rows']!=raw_delta['rows'] or clean['sales']+rejected['sales']!=raw_delta['sales']:
                        raise RuntimeError('RAW_CLEAN_QUARANTINE_MISMATCH')
                    conn.execute(text('UPDATE audit.Execution SET RowsRejected=:n WHERE ExecutionID=:execution_id'),{**params,'n':rejected['rows']})
                    report.update(clean_delta=clean,quarantine=rejected)
                with conn.begin():
                    conn.execute(text('CREATE TABLE #Changes(Action varchar(30) NOT NULL,EntityID int NOT NULL)'))
                    conn.execute(text((ROOT/'database/005_publish.sql').read_text(encoding='utf-8')),params)
                    conn.execute(text(f'''INSERT audit.Deletion(ExecutionID,InvoiceLineID) SELECT :execution_id,f.InvoiceLineID
                        FROM dw.FactSales f WHERE f.RecordStatus<>'DELETED' AND NOT EXISTS(SELECT 1 FROM {source}.Sales.InvoiceLines l WHERE l.InvoiceLineID=f.InvoiceLineID)'''),params)
                    conn.execute(text('''UPDATE f SET RecordStatus='DELETED',ExecutionID=:execution_id
                        OUTPUT 'DELETE',inserted.InvoiceLineID INTO #Changes
                        FROM dw.FactSales f JOIN audit.Deletion d ON d.InvoiceLineID=f.InvoiceLineID AND d.ExecutionID=:execution_id'''),params)
                    if fail_at=='after_publish':
                        raise RuntimeError('SIMULATED_FAILURE_AFTER_PUBLISH')
                    complete=reconcile(conn,source)
                    actions={r['Action']:int(r['n']) for r in conn.execute(text('SELECT Action,COUNT_BIG(*) n FROM #Changes GROUP BY Action')).mappings()}
                    inserted=actions.get('INSERT',0)
                    updated=sum(actions.get(k,0) for k in ('UPDATE','DELETE','REJECT'))
                    for layer,value in [('source_delta',source_delta),('raw_delta',raw_delta),('clean_delta',clean),('quarantine_delta',rejected),('dw_total',complete)]:
                        conn.execute(text('INSERT audit.Reconciliation(ExecutionID,Layer,[RowCount],SalesAmount) VALUES(:execution_id,:layer,:n,:amount)'),
                                     {**params,'layer':layer,'n':value['rows'],'amount':value['sales']})
                    stages=[('clean','raw.InvoiceLines','clean.SalesLine',raw_delta['rows'],clean['rows'],0,rejected['rows']),
                        ('dw','clean.SalesLine','dw.FactSales',clean['rows'],inserted,updated,0),
                        ('dw','raw.Customers','dw.DimCustomer',counts['Customers'],actions.get('CUSTOMER_INSERT',0),actions.get('CUSTOMER_EXPIRE',0),0),
                        ('dw','raw.StockItems','dw.DimProduct',counts['StockItems'],actions.get('PRODUCT_INSERT',0),actions.get('PRODUCT_UPDATE',0),0)]
                    for stage,src,dst,n,ins,upd,rej in stages:
                        conn.execute(text('''INSERT audit.StageCount(ExecutionID,Stage,SourceObject,TargetObject,RowsRead,RowsInserted,RowsUpdated,RowsRejected)
                            VALUES(:execution_id,:stage,:source,:target,:n,:ins,:upd,:rej)'''),
                            {**params,'stage':stage,'source':src,'target':dst,'n':n,'ins':ins,'upd':upd,'rej':rej})
                    conn.execute(text("UPDATE audit.Watermark SET WatermarkValue=:upper,ExecutionID=:execution_id WHERE PipelineName='sales'"),params)
                    conn.execute(text("IF NOT EXISTS(SELECT 1 FROM audit.Watermark WHERE PipelineName='sales') INSERT audit.Watermark VALUES('sales',:upper,:execution_id)"),params)
                    conn.execute(text("UPDATE audit.Execution SET Status='SUCCEEDED',EndTime=SYSUTCDATETIME(),RowsInserted=:ins,RowsUpdated=:upd WHERE ExecutionID=:execution_id"),{**params,'ins':inserted,'upd':updated})
                    notification_task=enqueue(conn,run,report['simulated'])
                    if fail_at=='before_commit':
                        raise RuntimeError('SIMULATED_FAILURE_BEFORE_COMMIT')
                    conn.execute(text('DROP TABLE #Changes'))
                    report.update(status='SUCCEEDED',inserted=inserted,updated=updated,actions=actions,dw=complete,watermark_after=upper)
            except Exception as exc:
                if conn.in_transaction():
                    conn.rollback()
                detail=str(exc) if isinstance(exc,RuntimeError) else str(getattr(exc,'orig',type(exc).__name__))
                for name in ('MSSQL_SA_PASSWORD','ETL_PASSWORD','API_PASSWORD','DEMO_API_KEY'):
                    secret=os.getenv(name)
                    if secret:
                        detail=detail.replace(secret,'[REDACTED]')
                with conn.begin():
                    conn.execute(text("UPDATE audit.Execution SET Status='FAILED',EndTime=SYSUTCDATETIME(),ErrorDetail=:error WHERE ExecutionID=:execution_id"),{**params,'error':detail[:950]})
                report.update(status='FAILED',error_code=detail[:950],watermark_after=previous)
                save()
                raise PipelineError(report) from None
        finally:
            if conn.in_transaction():
                conn.rollback()
            conn.execute(text("IF OBJECT_ID('tempdb..#SelectedLines') IS NOT NULL DROP TABLE #SelectedLines; IF OBJECT_ID('tempdb..#Changes') IS NOT NULL DROP TABLE #Changes; EXEC sys.sp_releaseapplock @Resource='sales_pipeline',@LockOwner='Session'"))
            conn.commit()
    report['notification']=process(notification_task,warehouse)
    save()
    return report

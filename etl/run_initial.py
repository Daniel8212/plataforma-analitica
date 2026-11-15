"""Extracción SQL coordinada por Python; raw durable y publicación analítica atómica."""
import json
from uuid import uuid4
from sqlalchemy import text
from etl.connection import engine, ROOT

PROJECTIONS = {
 'Invoices': ('Sales.Invoices', 'InvoiceID,CustomerID,InvoiceDate,IsCreditNote,LastEditedWhen'),
 'InvoiceLines': ('Sales.InvoiceLines', 'InvoiceLineID,InvoiceID,StockItemID,Description,Quantity,UnitPrice,TaxRate,TaxAmount,LineProfit,ExtendedPrice,LastEditedWhen'),
 'Customers': ('Sales.Customers', 'CustomerID,CustomerName,CustomerCategoryID,ValidFrom,ValidTo'),
 'CustomerCategories': ('Sales.CustomerCategories', 'CustomerCategoryID,CustomerCategoryName,ValidFrom,ValidTo'),
 'StockItems': ('Warehouse.StockItems', 'StockItemID,StockItemName,Brand,IsChillerStock,ValidFrom,ValidTo'),
}

def totals(conn, sql, params):
    row = conn.execute(text(sql), params).mappings().one()
    return int(row['n']), row['amount']

def main():
    run_id = str(uuid4())
    params = {'execution_id': run_id}
    report = {'execution_id': run_id}
    with engine().connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        # Bloqueo de sesión: protege extracción, publicación y reconciliación frente a cargas concurrentes.
        lock = conn.execute(text("""DECLARE @r int; EXEC @r=sys.sp_getapplock
            @Resource='sales_pipeline',@LockMode='Exclusive',@LockOwner='Session',@LockTimeout=0; SELECT @r""")).scalar_one()
        conn.commit()
        if lock < 0:
            raise SystemExit('Ya existe una carga de ventas en ejecución')
        try:
            with conn.begin():
                conn.execute(text("INSERT audit.Execution(ExecutionID,PipelineName,Status) VALUES(:execution_id,'sales_initial','RUNNING')"), params)
            try:
                with conn.begin():
                    source = totals(conn, '''SELECT COUNT_BIG(*) n,COALESCE(SUM(ExtendedPrice-TaxAmount),0) amount
                        FROM WideWorldImporters.Sales.InvoiceLines''', params)
                    read_count = 0
                    raw_counts = {}
                    for target, (source_table, columns) in PROJECTIONS.items():
                        # Identificadores pertenecen a constantes revisadas; solo execution_id es dato externo.
                        conn.execute(text(f'''INSERT raw.{target}(ExecutionID,{columns})
                            SELECT :execution_id,{columns} FROM WideWorldImporters.{source_table}'''), params)
                        count = conn.execute(text(f'SELECT COUNT_BIG(*) FROM raw.{target} WHERE ExecutionID=:execution_id'), params).scalar_one()
                        read_count += count
                        raw_counts[target] = count
                        conn.execute(text('''INSERT audit.StageCount(ExecutionID,Stage,SourceObject,TargetObject,RowsRead,RowsInserted)
                            VALUES(:execution_id,'raw',:source,:target,:n,:n)'''), {**params,'source':source_table,'target':'raw.'+target,'n':count})
                    conn.execute(text('UPDATE audit.Execution SET RowsRead=:n WHERE ExecutionID=:execution_id'), {**params,'n':read_count})
                    conn.execute(text('''INSERT audit.Reconciliation(ExecutionID,Layer,[RowCount],SalesAmount)
                        VALUES(:execution_id,'source',:n,:amount)'''), {**params,'n':source[0],'amount':source[1]})
                    raw = totals(conn, '''SELECT COUNT_BIG(*) n,COALESCE(SUM(ExtendedPrice-TaxAmount),0) amount
                        FROM raw.InvoiceLines WHERE ExecutionID=:execution_id''', params)
                    if source != raw:
                        raise RuntimeError('SOURCE_RAW_MISMATCH')
                # Raw y auditoría sobreviven si falla la transformación/publicación posterior.
                report.update(source=source,raw=raw)
                if source[0] > 0 and any(raw_counts[name] == 0 for name in ('Invoices','Customers','CustomerCategories','StockItems')):
                    raise RuntimeError('SOURCE_VISIBILITY_OR_EMPTY_DIMENSION')
                with conn.begin():
                    conn.execute(text((ROOT/'database/002_transform.sql').read_text(encoding='utf-8')), params)
                    clean = totals(conn, '''SELECT COUNT_BIG(*) n,COALESCE(SUM(SalesAmount),0) amount
                        FROM clean.SalesLine WHERE ExecutionID=:execution_id''', params)
                    rejected = totals(conn, '''SELECT COUNT_BIG(*) n,COALESCE(SUM(r.ExtendedPrice-r.TaxAmount),0) amount
                        FROM audit.Quarantine q JOIN raw.InvoiceLines r ON r.ExecutionID=q.ExecutionID AND r.InvoiceLineID=q.SourceKey
                        WHERE q.ExecutionID=:execution_id''', params)
                    dw = totals(conn, 'SELECT COUNT_BIG(*) n,COALESCE(SUM(SalesAmount),0) amount FROM dw.FactSales', params)
                    if source[0] > 0 and clean[0] == 0:
                        raise RuntimeError('ALL_LINES_REJECTED')
                    if (clean[0]+rejected[0],clean[1]+rejected[1]) != source or dw != clean:
                        raise RuntimeError('CLEAN_DW_RECONCILIATION_MISMATCH')
                    inserted = conn.execute(text('SELECT COUNT_BIG(*) FROM dw.FactSales WHERE ExecutionID=:execution_id'), params).scalar_one()
                    for layer, data in [('raw',raw),('clean',clean),('quarantine',rejected),('dw',dw)]:
                        conn.execute(text('''INSERT audit.Reconciliation(ExecutionID,Layer,[RowCount],SalesAmount)
                            VALUES(:execution_id,:layer,:n,:amount)'''), {**params,'layer':layer,'n':data[0],'amount':data[1]})
                    for stage, target, count in [('clean','clean.SalesLine',clean[0]),('dw','dw.FactSales',inserted)]:
                        conn.execute(text('''INSERT audit.StageCount(ExecutionID,Stage,SourceObject,TargetObject,RowsRead,RowsInserted,RowsRejected)
                            VALUES(:execution_id,:stage,:source,:target,:n,:inserted,:rejected)'''),
                            {**params,'stage':stage,'source':'raw.InvoiceLines' if stage=='clean' else 'clean.SalesLine',
                             'target':target,'n':source[0] if stage=='clean' else clean[0],
                             'inserted':count,'rejected':rejected[0] if stage=='clean' else 0})
                    conn.execute(text('''UPDATE audit.Execution SET Status='SUCCEEDED',EndTime=SYSUTCDATETIME(),
                        RowsInserted=:inserted,RowsRejected=:rejected WHERE ExecutionID=:execution_id'''),
                        {**params,'inserted':inserted,'rejected':rejected[0]})
                    report.update(status='SUCCEEDED',source=source,raw=raw,clean=clean,quarantine=rejected,dw=dw,inserted=inserted)
            except Exception as exc:
                if conn.in_transaction():
                    conn.rollback()
                error_code = str(exc) if isinstance(exc,RuntimeError) else type(exc).__name__
                with conn.begin():
                    conn.execute(text("""UPDATE audit.Execution SET Status='FAILED',EndTime=SYSUTCDATETIME(),
                        ErrorDetail=:error WHERE ExecutionID=:execution_id"""),
                        {**params,'error':f'{error_code}: carga no publicada; revisar ejecución y reglas'})
                report.update(status='FAILED',error_code=error_code)
                (ROOT/'documentation/evidence'/f'initial-{run_id}.json').write_text(
                    json.dumps(report,default=str,indent=2),encoding='utf-8')
                # No imprimir SQL ni parámetros que pudieran incluir información sensible.
                raise SystemExit(f'Carga fallida. execution_id={run_id}; tipo={type(exc).__name__}') from None
        finally:
            conn.execute(text("EXEC sys.sp_releaseapplock @Resource='sales_pipeline',@LockOwner='Session'"))
            conn.commit()
    out = ROOT/'documentation/evidence'/f'initial-{run_id}.json'
    out.write_text(json.dumps(report,default=str,indent=2),encoding='utf-8')
    print(json.dumps(report,default=str))

if __name__ == '__main__':
    main()

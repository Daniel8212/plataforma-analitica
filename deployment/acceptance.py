"""Métricas de aceptación desde SQL; no altera fuente, DW ni auditoría."""
import argparse
import json
import os
from datetime import datetime,timezone
from sqlalchemy import text
from etl.connection import engine,ROOT

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='documentation/evidence/acceptance.json')
    args=parser.parse_args()
    target=(ROOT/args.output).resolve()
    if not target.is_relative_to(ROOT):raise ValueError('Salida fuera del proyecto')
    with engine(os.environ['SOURCE_DATABASE']).connect() as c:
        source=dict(c.execute(text('''SELECT COUNT_BIG(*) lines,COUNT(DISTINCT InvoiceLineID) distinct_lines,
         COUNT(DISTINCT InvoiceID) invoices,SUM(CONVERT(bigint,Quantity)) units,
         SUM(CONVERT(decimal(18,2),Quantity*UnitPrice)) sales,
         SUM(CASE WHEN UnitPrice IS NULL THEN 1 ELSE 0 END) null_prices,
         SUM(CASE WHEN ExtendedPrice<>ROUND(Quantity*UnitPrice,2)+TaxAmount THEN 1 ELSE 0 END) inconsistent_amounts,
         MAX(LastEditedWhen) last_line_edit FROM Sales.InvoiceLines''')).mappings().one())
    with engine().connect() as c:
        dw=dict(c.execute(text('''SELECT COUNT_BIG(*) lines,COUNT(DISTINCT InvoiceLineID) distinct_lines,
         COUNT(DISTINCT InvoiceID) invoices,SUM(CONVERT(bigint,Quantity)) units,SUM(SalesAmount) sales,
         MIN(InvoiceDate) first_date,MAX(InvoiceDate) last_date FROM dw.vSalesRead''')).mappings().one())
        assert all(source[k]==dw[k] for k in ('lines','distinct_lines','invoices','units','sales'))
        integrity=c.execute(text('''SELECT COUNT_BIG(*) FROM dw.FactSales f
         LEFT JOIN dw.DimDate d ON d.DateKey=f.DateKey LEFT JOIN dw.DimCustomer c ON c.CustomerKey=f.CustomerKey
         LEFT JOIN dw.DimProduct p ON p.ProductKey=f.ProductKey
         WHERE d.DateKey IS NULL OR c.CustomerKey IS NULL OR p.ProductKey IS NULL''')).scalar_one()
        lineage=c.execute(text('''SELECT COUNT_BIG(*) FROM dw.FactSales f LEFT JOIN audit.Execution e ON e.ExecutionID=f.ExecutionID
         WHERE e.ExecutionID IS NULL OR e.Status<>'SUCCEEDED' ''')).scalar_one()
        latest=dict(c.execute(text('''SELECT TOP(1) CONVERT(varchar(36),ExecutionID) ExecutionID,StartTime,EndTime,
         RowsRead,RowsInserted,RowsUpdated,RowsRejected,DATEDIFF_BIG(millisecond,StartTime,EndTime) DurationMs
         FROM audit.Execution WHERE Status='SUCCEEDED' ORDER BY EndTime DESC''')).mappings().one())
        full=dict(c.execute(text("SELECT TOP(1) CONVERT(varchar(36),ExecutionID) ExecutionID,RowsRejected FROM audit.Execution WHERE Status='SUCCEEDED' AND LoadMode IN('initial','full') ORDER BY EndTime DESC")).mappings().one())
        raw=c.execute(text('SELECT COUNT_BIG(*) FROM raw.InvoiceLines WHERE ExecutionID=:id'),{'id':full['ExecutionID']}).scalar_one()
        clean=c.execute(text('SELECT COUNT_BIG(*) FROM clean.SalesLine WHERE ExecutionID=:id'),{'id':full['ExecutionID']}).scalar_one()
        watermark=c.execute(text("SELECT CONVERT(varchar(36),ExecutionID) FROM audit.Watermark WHERE PipelineName='sales'")).scalar_one()
        model=dict(c.execute(text('SELECT Version,DatasetHash,AsOfDate,Algorithm FROM ml.ModelRun WHERE IsActive=1')).mappings().one())
        predictions=[dict(r) for r in c.execute(text("SELECT TargetWeekStart,PredictedSales FROM ml.Prediction WHERE Version=:v AND Kind='future' ORDER BY Horizon"),{'v':model['Version']}).mappings()]
        operational_counts={table:c.execute(text('SELECT COUNT_BIG(*) FROM '+table)).scalar_one()
          for table in ('dw.DimCustomer','dw.DimProduct','audit.Execution','audit.StageCount','audit.Reconciliation',
                        'audit.Quarantine','audit.ChatRequest','notify.Task','notify.Evaluation','notify.Alert',
                        'notify.StateHistory','ml.ModelRun','ml.Prediction')}
    assert integrity==lineage==0 and len(predictions)==4
    def ratio(n,d):return {'numerator':n,'denominator':d,'ratio':n/d if d else None}
    report={'status':'passed','checked_at_utc':datetime.now(timezone.utc).isoformat(),'source':source,'warehouse':dw,
      'quality':{'source_price_completeness':ratio(source['lines']-source['null_prices'],source['lines']),
       'source_key_uniqueness':ratio(source['distinct_lines'],source['lines']),
       'source_amount_consistency':ratio(source['lines']-source['inconsistent_amounts'],source['lines']),
       'initial_clean_acceptance':ratio(clean,raw),'initial_rejections':full['RowsRejected'],
       'dw_orphans':integrity,'invalid_fact_lineage':lineage},
      'latest_load':latest,'watermark_execution_id':watermark,'active_model':model,'future':predictions,'operational_counts':operational_counts,
      'timeliness':{'load_duration_ms':latest['DurationMs'],'historical_data_last_date':str(dw['last_date']),
                    'note':'Duración técnica distinta de antigüedad de la muestra 2013–2016; no es tiempo real ni SLA.'}}
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Aceptación SQL: reconciliación, calidad, linaje y modelo comprobados; '+str(target.relative_to(ROOT)))

if __name__=='__main__':main()

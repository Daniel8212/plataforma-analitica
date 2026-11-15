"""Ejecuta SQL independiente y registra resultados reales y latencia de consulta."""
import json
from time import perf_counter
from sqlalchemy import text
from etl.connection import engine, ROOT

def main():
    with engine().connect() as conn:
        run = conn.execute(text("SELECT TOP(1) CONVERT(varchar(36),ExecutionID) FROM audit.Execution WHERE Status='SUCCEEDED' AND LoadMode IN ('initial','full') ORDER BY EndTime DESC")).scalar_one()
        rows = [dict(r) for r in conn.execute(text((ROOT/'database/003_validate.sql').read_text(encoding='utf-8')), {'execution_id':run}).mappings()]
        values = [{k:v for k,v in row.items() if k!='layer'} for row in rows]
        if not values or not all(value == values[0] for value in values):
            raise SystemExit('Reconciliación independiente fallida')
    start = perf_counter()
    with engine(role='api').connect() as conn:
        conn.execute(text('SELECT * FROM dw.vSalesKpi')).one()
    elapsed_ms = round((perf_counter()-start)*1000,2)
    report = {'status':'passed','execution_id':run,'layers':rows,'kpi_query_including_connection_ms':elapsed_ms,
              'scope':'Carga inicial completa, sin rechazos. La consulta fuente usa cantidad por precio; raw usa importe menos impuesto.'}
    (ROOT/'documentation/evidence/independent-validation.json').write_text(json.dumps(report,default=str,indent=2),encoding='utf-8')
    print(json.dumps(report,default=str))

if __name__ == '__main__':
    main()

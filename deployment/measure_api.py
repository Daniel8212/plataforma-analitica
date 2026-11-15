"""Medición local puntual y verificación de que la fuente principal no se alteró."""
import json
import os
from time import perf_counter
import httpx
from sqlalchemy import text
from etl.connection import ROOT, engine

def main():
    results=[]
    paths=['filters','kpis?start=2016-03-01&end=2016-05-31',
           'dashboard?start=2016-03-01&end=2016-05-31','detail?page_size=20',
           'operations','rejections?page_size=10']
    with httpx.Client(base_url='http://127.0.0.1:8000/api/',headers={'X-API-Key':os.environ['DEMO_API_KEY']},timeout=30) as client:
        for path in paths:
            start=perf_counter()
            response=client.get(path)
            elapsed=round((perf_counter()-start)*1000,2)
            response.raise_for_status()
            results.append({'endpoint':'/api/'+path,'status':response.status_code,'elapsed_ms':elapsed})
    with engine('WideWorldImporters').connect() as c:
        source=dict(c.execute(text('''SELECT COUNT_BIG(*) line_count,SUM(ExtendedPrice-TaxAmount) sales,
            MIN(LastEditedWhen) first_edit,MAX(LastEditedWhen) last_edit FROM Sales.InvoiceLines''')).mappings().one())
    with engine().connect() as c:
        simulated=c.execute(text('SELECT COUNT(*) FROM audit.Execution WHERE IsSimulated=1')).scalar_one()
    report={'measurement':'Una solicitud por endpoint vía HTTP local; no es benchmark ni SLA.',
            'requests':results,'source_main_after_tests':source,'simulated_runs_in_main_dw':simulated}
    (ROOT/'documentation/evidence/api-measurements.json').write_text(json.dumps(report,default=str,indent=2),encoding='utf-8')
    print(json.dumps(report,default=str))

if __name__=='__main__':
    main()

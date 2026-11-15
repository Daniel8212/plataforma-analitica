"""Verificación independiente de cierre; solo lectura sobre fuente y DW."""
import json
import os
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import text
from etl.connection import engine,ROOT
from backend.main import app

def main():
    with engine(os.environ['SOURCE_DATABASE']).connect() as c:
        source=dict(c.execute(text('''SELECT COUNT_BIG(*) lines,COUNT(DISTINCT InvoiceID) invoices,
         SUM(CONVERT(bigint,Quantity)) units,SUM(CONVERT(decimal(18,2),Quantity*UnitPrice)) sales,
         MAX(LastEditedWhen) last_line_edit FROM Sales.InvoiceLines''')).mappings().one())
    with engine().connect() as c:
        warehouse=dict(c.execute(text('''SELECT COUNT_BIG(*) lines,COUNT(DISTINCT InvoiceID) invoices,
         SUM(CONVERT(bigint,Quantity)) units,SUM(SalesAmount) sales FROM dw.vSalesRead''')).mappings().one())
        assert all(source[k]==warehouse[k] for k in warehouse)
        tasks=[dict(r) for r in c.execute(text('SELECT * FROM notify.vTasks ORDER BY CreatedAt')).mappings()]
        assert any(not t['IsSimulated'] and t['Status']=='SUCCEEDED' for t in tasks)
    with TestClient(app) as client:
        headers={'X-API-Key':os.environ['DEMO_API_KEY']}
        forecast=client.get('/api/forecast',headers=headers);alerts=client.get('/api/alerts',headers=headers)
        assert forecast.status_code==alerts.status_code==200
        assert forecast.json()['available'] and len(forecast.json()['forecast'])==4
        kpi=client.get('/api/kpis',headers=headers).json()
        assert Decimal(kpi['sales'])==source['sales']
    report={'status':'passed','source':source,'warehouse':warehouse,'forecast_version':forecast.json().get('version'),
      'tasks':tasks,'alerts':alerts.json()['items'],'note':'Lecturas reales; los eventos IsSimulated están separados y no modifican hechos.'}
    (ROOT/'documentation/evidence/day3-final.json').write_text(json.dumps(report,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Fuente/DW/API reconciliados; pronóstico y tareas/alertas disponibles.')

if __name__=='__main__':main()

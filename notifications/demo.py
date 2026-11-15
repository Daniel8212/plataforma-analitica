"""Demostración identificada; no modifica OLTP ni hechos del DW."""
import argparse
import json
from decimal import Decimal
from sqlalchemy import text
from etl.connection import engine,ROOT
from notifications.service import snapshot,enqueue,process

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--simulate',action='store_true',required=True,help='Confirma evento explícitamente simulado')
    parser.parse_args()
    with engine().begin() as c:
        p=snapshot(c)
        if not p['eligible']:raise SystemExit('Cobertura insuficiente para la demostración')
        p['actual_dw_observed']=p['observed']
        p['observed']=str((Decimal(p['reference'])*Decimal('0.65')).quantize(Decimal('0.01')))
        p['simulation_note']='Valor evaluado sintético, 35 % por debajo de la referencia real; no representa ventas del DW.'
        run=str(c.execute(text("SELECT TOP(1) ExecutionID FROM audit.Execution WHERE Status='SUCCEEDED' AND IsSimulated=0 ORDER BY EndTime DESC")).scalar_one())
        task=enqueue(c,run,True,payload=p,rule='DEMO_SALES_DROP')
    result={'simulation':True,'note':p['simulation_note'],'payload':p,'processing':process(task)}
    (ROOT/'documentation/evidence/alert-demo.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()

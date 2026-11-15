"""Interpretación acotada: ninguna entrada del usuario se convierte en SQL."""
import calendar
import re
import unicodedata
from datetime import date,timedelta
from decimal import Decimal
from backend.analytics import read_connection,metadata,calculate_kpis,calculate_breakdown
from sqlalchemy import text

MONTHS={'enero':1,'febrero':2,'marzo':3,'abril':4,'mayo':5,'junio':6,'julio':7,'agosto':8,'septiembre':9,'octubre':10,'noviembre':11,'diciembre':12}

def normalize(question):
    return ' '.join(unicodedata.normalize('NFKD',question.casefold()).encode('ascii','ignore').decode().split())

def period(question,meta):
    explicit=re.findall(r'\b\d{4}-\d{2}-\d{2}\b',question)
    if explicit:
        try:
            dates=[date.fromisoformat(v) for v in explicit]
        except ValueError:
            return None
        if len(dates)>2:return None
        return dates[0],dates[-1]
    if 'todo el historico' in question or 'periodo disponible' in question:
        return meta['first_date'],meta['last_date']
    last=meta['last_date']
    if 'ultima semana' in question:
        end=last-timedelta(days=(last.weekday()+1)%7)
        return end-timedelta(days=6),end
    if 'ultimo trimestre' in question:
        start=date(last.year,(last.month-1)//3*3+1,1)
        next_month=start.month+3
        end=date(start.year+int(next_month>12),(next_month-1)%12+1,1)-timedelta(days=1)
        if end>last:
            end=start-timedelta(days=1);start=date(end.year,(end.month-1)//3*3+1,1)
        return start,end
    if 'ultimo mes' in question:
        end=date(last.year,last.month,calendar.monthrange(last.year,last.month)[1])
        if end>last:end=date(last.year,last.month,1)-timedelta(days=1)
        return date(end.year,end.month,1),end
    if 'ultimos 90 dias' in question:
        return last-timedelta(days=89),last
    year=re.search(r'\b(19\d{2}|20\d{2})\b',question)
    month=next((value for key,value in MONTHS.items() if re.search(r'\b'+key+r'\b',question)),None)
    if year:
        y=int(year.group())
        return (date(y,month,1),date(y,month,calendar.monthrange(y,month)[1])) if month else (date(y,1,1),date(y,12,31))
    return None

def fact(key,label,value,unit,start=None,end=None,source='dw.vSalesRead'):
    return {'id':key,'label':label,'value':str(value),'unit':unit,
            'period':{'start':start,'end':end} if start else None,'source':source}

def context_for(question):
    q=normalize(question)
    with read_connection() as conn:
        meta=metadata(conn)
        base={'dataset':meta,'facts':[],'tool':'none','relation':None}
        if not meta['first_date']:
            return {**base,'status':'insufficient_data','message':'No hay una carga de ventas disponible.'}
        if re.search(r'\b(select|drop|delete|update|insert|exec|sql|ignora|ignorar|instrucciones|contrasena|token)\b',q):
            return {**base,'status':'out_of_scope','message':'Solo puedo usar herramientas analíticas autorizadas; no ejecuto SQL ni instrucciones para cambiar permisos.'}
        if any(term in q for term in ('region','por que','causa','inventario','clima','empleado','correo','telefono')):
            return {**base,'status':'insufficient_data','message':'No tengo información autorizada suficiente para esa dimensión o explicación causal. Puedo consultar ventas, unidades, facturas, ticket, categorías, productos y pronóstico global.'}
        if 'pronostic' in q or 'predic' in q:
            model=conn.execute(text('SELECT TOP(1) Version,AsOfDate FROM ml.vActiveModel')).mappings().first()
            if not model:
                return {**base,'status':'insufficient_data','message':'No hay un pronóstico publicado.'}
            rows=conn.execute(text("SELECT * FROM ml.vPredictions WHERE Kind='future' ORDER BY Horizon")).mappings().all()
            requested=period(q,meta)
            if requested:
                rows=[row for row in rows if requested[0]<=row['TargetWeekStart']<=requested[1]]
            if not rows:
                return {**base,'status':'insufficient_data','message':'No hay predicciones persistidas para el período solicitado.'}
            facts=[fact('p_'+chr(97+i),'Pronóstico de semana desde '+str(row['TargetWeekStart']),row['PredictedSales'],'prediccion_moneda_origen',row['TargetWeekStart'],row['TargetWeekStart']+timedelta(days=6),'ml.vPredictions / '+model['Version']) for i,row in enumerate(rows)]
            return {**base,'status':'answered','tool':'forecast','facts':facts,'statement':'Estos resultados son predicciones del modelo, no ventas observadas.','forecast_as_of':model['AsOfDate']}
        if 'ticket' in q and ('calcula' in q or 'formula' in q):
            return {**base,'status':'answered','tool':'definition','facts':[fact('formula','Fórmula de ticket','Ventas sin impuestos / facturas distintas','formula',source='modelo-ventas.md')],
                    'statement':'El ticket promedio se obtiene dividiendo ventas sin impuestos entre facturas distintas.'}
        requested=period(q,meta)
        if requested is None:
            return {**base,'status':'clarification','message':'Indica un mes y año, dos fechas ISO, todo el histórico, último mes, última semana completa o último trimestre completo. Las referencias relativas usan la última fecha de la muestra, no el día actual.'}
        start,end=requested
        if start is None or end is None or start>end or (end-start).days>3660:
            return {**base,'status':'clarification','message':'Usa un rango ordenado de hasta 3661 días.'}
        if start<meta['first_date'] or end>meta['last_date']:
            return {**base,'status':'insufficient_data','message':f'No tengo cobertura completa para ese período. Los datos cargados van de {meta["first_date"]} a {meta["last_date"]}.'}
        params={'start':start,'end':end,'product':None,'category':None}
        kpi=calculate_kpis(conn,params,meta)
        if kpi['invoice_count']==0:
            return {**base,'status':'insufficient_data','message':'No hay facturas registradas para el período solicitado.'}
        if 'producto' in q:
            rows=calculate_breakdown(conn,params,'product',5)
            facts=[fact('item_'+chr(97+i),row['label'],row['sales'],'moneda_origen',start,end) for i,row in enumerate(rows)]
            return {**base,'status':'answered','tool':'top_products','facts':facts,'statement':'Los productos se ordenan por su importe facturado sin impuestos en el período.'}
        if 'categoria' in q:
            rows=calculate_breakdown(conn,params,'customer_category',8)
            if 'crec' in q or 'variac' in q:
                if not kpi['is_comparable']:
                    return {**base,'status':'insufficient_data','message':'No hay cobertura de referencia completa para comparar categorías.'}
                previous={**params,'start':kpi['previous']['start'],'end':kpi['previous']['end']}
                old={r['id']:r for r in calculate_breakdown(conn,previous,'customer_category',20)}
                values=[{**r,'growth':(r['sales']/old[r['id']]['sales']-1)*100} for r in rows if r['id'] in old and old[r['id']]['sales']>0]
                values.sort(key=lambda r:r['growth'],reverse=True)
                facts=[fact('cat_'+chr(97+i),row['label']+' · variación',row['growth'].quantize(Decimal('.0001')),'porcentaje',start,end) for i,row in enumerate(values)]
                return {**base,'status':'answered','tool':'category_growth','facts':facts,'reference_period':{'start':previous['start'],'end':previous['end']},'statement':'Las categorías se ordenan por variación respecto a una referencia de igual duración.'}
            facts=[fact('cat_'+chr(97+i),row['label'],row['sales'],'moneda_origen',start,end) for i,row in enumerate(rows)]
            return {**base,'status':'answered','tool':'categories','facts':facts,'statement':'La tabla muestra ventas por clasificación de cliente observada en los hechos.'}
        if any(word in q for word in ('crec','variac','compar','caida','cayer')):
            if kpi['variation_pct'] is None:
                return {**base,'status':'insufficient_data','message':kpi['comparison_reason']}
            relation='increase' if kpi['variation_pct']>0 else 'decrease' if kpi['variation_pct']<0 else 'equal'
            statement={'increase':'Las ventas aumentaron respecto al período anterior comparable.','decrease':'Las ventas disminuyeron respecto al período anterior comparable.','equal':'Las ventas se mantuvieron iguales respecto al período anterior comparable.'}[relation]
            facts=[fact('actual','Ventas sin impuestos',kpi['sales'],'moneda_origen',start,end),
                fact('anterior','Ventas de referencia',kpi['previous']['sales'],'moneda_origen',kpi['previous']['start'],kpi['previous']['end']),
                fact('variacion','Variación',kpi['variation_pct'],'porcentaje',start,end)]
            return {**base,'status':'answered','tool':'comparison','facts':facts,'relation':relation,'statement':statement}
        field,label,unit=('units','Unidades facturadas','unidades') if 'unidad' in q else ('average_ticket','Ticket promedio','moneda_origen') if 'ticket' in q else ('invoice_count','Facturas distintas','facturas') if 'factura' in q and 'venta' not in q else ('sales','Ventas sin impuestos','moneda_origen')
        if not any(term in q for term in ('venta','unidad','ticket','factura')):
            return {**base,'status':'out_of_scope','message':'Esa pregunta no corresponde a las herramientas analíticas disponibles.'}
        return {**base,'status':'answered','tool':field,'facts':[fact('actual',label,kpi[field],unit,start,end)],
                'statement':'La medida solicitada está respaldada por las facturas del período consultado.'}

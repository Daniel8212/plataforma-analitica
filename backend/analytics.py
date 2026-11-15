"""Contratos analíticos de solo lectura; identificadores cerrados y valores parametrizados."""
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from backend.auth import require_access
from etl.connection import engine

router=APIRouter(prefix='/api',dependencies=[Depends(require_access)])
PREDICATE='''InvoiceDate BETWEEN :start AND :end
 AND (CAST(:product AS int) IS NULL OR ProductID=:product)
 AND (CAST(:category AS int) IS NULL OR CustomerCategoryID=:category)'''

@contextmanager
def read_connection():
    # Misma vista consistente para metadatos, KPIs y gráficos dentro de cada respuesta.
    with engine(role='api').connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        with conn.begin():
            yield conn

def encoded(value):
    return jsonable_encoder(value,custom_encoder={Decimal:str,datetime:lambda d:d.replace(tzinfo=timezone.utc).isoformat()})

def filters(start: date | None=None,end: date | None=None,
            product_id: int | None=Query(None,ge=1,le=2147483647),category_id: int | None=Query(None,ge=1,le=2147483647)):
    if start and (start<date(1900,1,1) or start>date(2099,12,31)):
        raise HTTPException(422,'Fecha inicial fuera del rango 1900–2099')
    if end and (end<date(1900,1,1) or end>date(2099,12,31)):
        raise HTTPException(422,'Fecha final fuera del rango 1900–2099')
    if start and end and (start>end or (end-start).days>3660):
        raise HTTPException(422,'Usa un rango ordenado de hasta 3661 días')
    return {'start':start,'end':end,'product':product_id,'category':category_id}

def metadata(conn):
    coverage=dict(conn.execute(text('SELECT MIN(InvoiceDate) first_date,MAX(InvoiceDate) last_date FROM dw.vSalesRead')).mappings().one())
    latest=conn.execute(text("SELECT TOP(1) ExecutionID,EndTime FROM audit.vExecutions WHERE Status='SUCCEEDED' ORDER BY EndTime DESC")).mappings().first()
    return {**coverage,'loaded_at':latest['EndTime'] if latest else None,'execution_id':latest['ExecutionID'] if latest else None}

def resolve(conn, params):
    meta=metadata(conn)
    params={**params,'start':params['start'] or meta['first_date'] or date(2013,1,1),
            'end':params['end'] or meta['last_date'] or date(2013,1,1)}
    if params['start']>params['end'] or (params['end']-params['start']).days>3660:
        raise HTTPException(422,'Usa un rango ordenado de hasta 3661 días')
    return params,meta

def aggregate(conn,params):
    return dict(conn.execute(text(f'''SELECT COALESCE(SUM(SalesAmount),0) sales,
        COALESCE(SUM(CONVERT(bigint,Quantity)),0) units,COUNT(DISTINCT InvoiceID) invoice_count,
        COUNT_BIG(*) line_count,MIN(InvoiceDate) first_date,MAX(InvoiceDate) last_date
        FROM dw.vSalesRead WHERE {PREDICATE}'''),params).mappings().one())

def calculate_kpis(conn,params,meta):
    current=aggregate(conn,params)
    days=(params['end']-params['start']).days+1
    previous_params={**params,'start':params['start']-timedelta(days=days),'end':params['start']-timedelta(days=1)}
    previous=aggregate(conn,previous_params)
    comparable=bool(meta['first_date'] and previous_params['start']>=meta['first_date'] and params['end']<=meta['last_date'])
    variation=None
    reason=None
    if not comparable:
        reason='La cobertura cargada no contiene ambos períodos completos.'
    elif previous['sales']==0:
        reason='El período anterior no tiene ventas; variación porcentual no definida.'
    else:
        variation=((current['sales']/previous['sales']-1)*100).quantize(Decimal('.0001'))
    return {**current,'average_ticket':(current['sales']/current['invoice_count']).quantize(Decimal('.01')) if current['invoice_count'] else None,
        'variation_pct':variation,'comparison_reason':reason,'is_comparable':comparable,
        'period':{'start':params['start'],'end':params['end']},
        'previous':{**previous,'start':previous_params['start'],'end':previous_params['end']},
        'loaded_at':meta['loaded_at'],'execution_id':meta['execution_id'],
        'coverage':{'start':meta['first_date'],'end':meta['last_date']},
        'definition':'Ventas facturadas sin impuestos; moneda de origen sin código disponible. Notas de crédito no admitidas hasta validar su semántica.'}

def bucket_start(day,grain):
    return day.replace(day=1) if grain=='month' else day-timedelta(days=day.weekday())

def calculate_trends(conn,params,meta,grain):
    expression="DATEFROMPARTS(YEAR(InvoiceDate),MONTH(InvoiceDate),1)" if grain=='month' else "CONVERT(date,DATEADD(day,-(DATEDIFF(day,'19000101',InvoiceDate)%7),InvoiceDate))"
    rows=conn.execute(text(f'''SELECT {expression} bucket,SUM(SalesAmount) sales,
        SUM(CONVERT(bigint,Quantity)) units,COUNT(DISTINCT InvoiceID) invoice_count FROM dw.vSalesRead
        WHERE {PREDICATE} GROUP BY {expression} ORDER BY bucket'''),params).mappings().all()
    by_date={r['bucket']:dict(r) for r in rows}
    if not meta['first_date']:
        return []
    start=max(params['start'],meta['first_date'])
    end=min(params['end'],meta['last_date'])
    if start>end:
        return []
    cursor=bucket_start(start,grain)
    output=[]
    while cursor<=end:
        next_date=(cursor.replace(day=28)+timedelta(days=4)).replace(day=1) if grain=='month' else cursor+timedelta(days=7)
        item=by_date.get(cursor,{'bucket':cursor,'sales':Decimal(0),'units':0,'invoice_count':0})
        output.append({**item,'partial':cursor<start or next_date-timedelta(days=1)>end})
        cursor=next_date
    return output

def calculate_breakdown(conn,params,dimension,limit):
    key,label={'product':('ProductID','ProductName'),'customer_category':('CustomerCategoryID','CustomerCategory')}[dimension]
    rows=conn.execute(text(f'''SELECT TOP(:limit) {key} id,MAX({label}) label,SUM(SalesAmount) sales,
        SUM(CONVERT(bigint,Quantity)) units,COUNT(DISTINCT InvoiceID) invoice_count
        FROM dw.vSalesRead WHERE {PREDICATE} GROUP BY {key} ORDER BY sales DESC,{key}'''),{**params,'limit':limit}).mappings().all()
    return [dict(r) for r in rows]

@router.get('/filters')
def get_filters():
    with read_connection() as conn:
        return encoded({**metadata(conn),
            'products':[dict(r) for r in conn.execute(text('SELECT ProductID id,ProductName label FROM dw.vProductFilters ORDER BY ProductName')).mappings()],
            'categories':[dict(r) for r in conn.execute(text('SELECT CustomerCategoryID id,CustomerCategory label FROM dw.vCategoryFilters ORDER BY CustomerCategory')).mappings()]})

@router.get('/kpis')
def get_kpis(params=Depends(filters)):
    with read_connection() as conn:
        params,meta=resolve(conn,params)
        return encoded(calculate_kpis(conn,params,meta))

@router.get('/comparison')
def get_comparison(params=Depends(filters)):
    with read_connection() as conn:
        params,meta=resolve(conn,params)
        kpi=calculate_kpis(conn,params,meta)
        return encoded({'current':{k:kpi[k] for k in ('sales','units','invoice_count','period')},
            'previous':kpi['previous'],'variation_pct':kpi['variation_pct'],
            'is_comparable':kpi['is_comparable'],'reason':kpi['comparison_reason']})

@router.get('/trends')
def get_trends(grain: Literal['week','month']='week',params=Depends(filters)):
    with read_connection() as conn:
        params,meta=resolve(conn,params)
        return encoded({'grain':grain,'items':calculate_trends(conn,params,meta,grain),'execution_id':meta['execution_id']})

@router.get('/breakdown')
def get_breakdown(dimension: Literal['product','customer_category']='product',limit: int=Query(8,ge=1,le=20),params=Depends(filters)):
    with read_connection() as conn:
        params,meta=resolve(conn,params)
        return encoded({'dimension':dimension,'items':calculate_breakdown(conn,params,dimension,limit),'execution_id':meta['execution_id']})

@router.get('/dashboard')
def get_dashboard(grain: Literal['week','month']='week',params=Depends(filters)):
    with read_connection() as conn:
        params,meta=resolve(conn,params)
        return encoded({'kpis':calculate_kpis(conn,params,meta),'grain':grain,
            'trends':calculate_trends(conn,params,meta,grain),
            'products':calculate_breakdown(conn,params,'product',8),
            'categories':calculate_breakdown(conn,params,'customer_category',8)})

@router.get('/detail')
def get_detail(page: int=Query(1,ge=1,le=100000),page_size: int=Query(20,ge=1,le=100),params=Depends(filters)):
    with read_connection() as conn:
        params,meta=resolve(conn,params)
        n=conn.execute(text(f'SELECT COUNT_BIG(*) FROM dw.vSalesRead WHERE {PREDICATE}'),params).scalar_one()
        rows=conn.execute(text(f'''SELECT InvoiceLineID,InvoiceID,InvoiceDate,CustomerID,CustomerName,CustomerCategory,
            ProductID,ProductName,Quantity,UnitPrice,SalesAmount,TaxAmount,ExtendedPrice FROM dw.vSalesRead
            WHERE {PREDICATE} ORDER BY InvoiceDate DESC,InvoiceID DESC,InvoiceLineID DESC
            OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY'''),{**params,'offset':(page-1)*page_size,'size':page_size}).mappings().all()
        return encoded({'items':[dict(r) for r in rows],'total':n,'page':page,'page_size':page_size,'execution_id':meta['execution_id']})

@router.get('/operations')
def get_operations():
    with read_connection() as conn:
        runs=[dict(r) for r in conn.execute(text('SELECT TOP(12) * FROM audit.vExecutions ORDER BY StartTime DESC')).mappings()]
        rejected=[dict(r) for r in conn.execute(text('''SELECT TOP(20) ExecutionID,RuleID,COUNT_BIG(*) count
            FROM audit.vRejections GROUP BY ExecutionID,RuleID ORDER BY count DESC,ExecutionID''')).mappings()]
        watermarks=[dict(r) for r in conn.execute(text('SELECT * FROM audit.vWatermarks')).mappings()]
        return encoded({'latest_success':metadata(conn),'runs':runs,'rejections':rejected,'watermarks':watermarks})

@router.get('/rejections')
def get_rejections(execution_id: UUID | None=None,page: int=Query(1,ge=1,le=100000),page_size: int=Query(20,ge=1,le=100)):
    params={'id':str(execution_id) if execution_id else None,'offset':(page-1)*page_size,'size':page_size}
    predicate='(CAST(:id AS varchar(36)) IS NULL OR ExecutionID=:id)'
    with read_connection() as conn:
        count=conn.execute(text('SELECT COUNT_BIG(*) FROM audit.vRejections WHERE '+predicate),params).scalar_one()
        rows=conn.execute(text('SELECT * FROM audit.vRejections WHERE '+predicate+' ORDER BY RecordedAt DESC,QuarantineID DESC OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY'),params).mappings().all()
        return encoded({'items':[dict(r) for r in rows],'total':count,'page':page,'page_size':page_size})

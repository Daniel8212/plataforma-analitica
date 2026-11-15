"""Contrastar KPIs/filtros contra SQL operacional independiente y probar límites de la API."""
import os
from datetime import date
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from backend.main import app
from etl.connection import engine

@pytest.fixture(scope='module')
def client():
    with TestClient(app,headers={'X-API-Key':os.environ['DEMO_API_KEY']}) as c:
        yield c

@pytest.fixture(scope='module')
def dimensions():
    with engine('WideWorldImporters').connect() as c:
        row=c.execute(text('''SELECT TOP(1) l.StockItemID product,c.CustomerCategoryID category
            FROM Sales.InvoiceLines l JOIN Sales.Invoices i ON i.InvoiceID=l.InvoiceID
            JOIN Sales.Customers c ON c.CustomerID=i.CustomerID ORDER BY i.InvoiceDate DESC,l.InvoiceLineID DESC''')).mappings().one()
        return dict(row)

def independent(params):
    with engine('WideWorldImporters').connect() as c:
        return dict(c.execute(text('''SELECT COALESCE(SUM(l.ExtendedPrice-l.TaxAmount),0) sales,
            COALESCE(SUM(CONVERT(bigint,l.Quantity)),0) units,COUNT(DISTINCT i.InvoiceID) invoices,COUNT_BIG(*) lines
            FROM Sales.InvoiceLines l JOIN Sales.Invoices i ON i.InvoiceID=l.InvoiceID
            JOIN Sales.Customers c ON c.CustomerID=i.CustomerID
            WHERE i.InvoiceDate BETWEEN :start AND :end
            AND (CAST(:product AS int) IS NULL OR l.StockItemID=:product)
            AND (CAST(:category AS int) IS NULL OR c.CustomerCategoryID=:category)'''),params).mappings().one())

@pytest.mark.parametrize('product,category',[(False,False),(True,False),(False,True),(True,True)])
def test_kpis_combined_filters_and_comparison(client,dimensions,product,category):
    params={'start':date(2016,3,1),'end':date(2016,5,31),
            'product':dimensions['product'] if product else None,'category':dimensions['category'] if category else None}
    query={'start':params['start'].isoformat(),'end':params['end'].isoformat()}
    if product: query['product_id']=params['product']
    if category: query['category_id']=params['category']
    response=client.get('/api/kpis',params=query)
    assert response.status_code==200
    actual=response.json()
    expected=independent(params)
    previous=independent({**params,'start':date(2015,11,30),'end':date(2016,2,29)})
    assert Decimal(actual['sales'])==expected['sales']
    assert actual['units']==expected['units'] and actual['invoice_count']==expected['invoices']
    assert actual['line_count']==expected['lines']
    assert Decimal(actual['average_ticket'])==(expected['sales']/expected['invoices']).quantize(Decimal('.01'))
    assert Decimal(actual['previous']['sales'])==previous['sales']
    assert actual['previous']['start']=='2015-11-30' and actual['previous']['end']=='2016-02-29'
    assert actual['is_comparable']
    assert Decimal(actual['variation_pct'])==((expected['sales']/previous['sales']-1)*100).quantize(Decimal('.0001'))

@pytest.mark.parametrize('grain',['week','month'])
def test_trends_total_and_dashboard_match(client,grain):
    params={'start':'2016-03-01','end':'2016-05-31','grain':grain}
    payload=client.get('/api/dashboard',params=params).json()
    assert sum(Decimal(x['sales']) for x in payload['trends'])==Decimal(payload['kpis']['sales'])
    assert sum(x['units'] for x in payload['trends'])==payload['kpis']['units']
    assert payload['products'] and payload['categories']
    if grain=='week': assert payload['trends'][0]['partial'] and payload['trends'][-1]['partial']

def test_pagination_and_original_invoice_line(client):
    a=client.get('/api/detail?page_size=3').json()
    b=client.get('/api/detail?page_size=3&page=2').json()
    assert a['total']==228265
    assert len(a['items'])==len(b['items'])==3
    assert not ({r['InvoiceLineID'] for r in a['items']} & {r['InvoiceLineID'] for r in b['items']})
    row=a['items'][0]
    with engine('WideWorldImporters').connect() as c:
        expected=c.execute(text('SELECT ExtendedPrice-TaxAmount FROM Sales.InvoiceLines WHERE InvoiceLineID=:id'),{'id':row['InvoiceLineID']}).scalar_one()
    assert Decimal(row['SalesAmount'])==expected

def test_empty_period_and_missing_reference(client):
    empty=client.get('/api/dashboard?start=2020-01-01&end=2020-01-31').json()
    assert empty['kpis']['invoice_count']==0 and empty['trends']==[]
    assert empty['kpis']['average_ticket'] is None and empty['kpis']['variation_pct'] is None
    first=client.get('/api/kpis?start=2013-01-01&end=2013-01-31').json()
    assert first['variation_pct'] is None and not first['is_comparable']

@pytest.mark.parametrize('url',[
 '/api/kpis?start=2016-06-01&end=2016-01-01','/api/kpis?start=1800-01-01',
 '/api/kpis?start=1900-01-01&end=2099-12-31','/api/detail?page_size=101','/api/detail?page=0',
 '/api/kpis?product_id=1%3BDROP%20TABLE','/api/kpis?product_id=999999999999999999999',
 '/api/trends?grain=sql','/api/breakdown?dimension=InvoiceID','/api/rejections?execution_id=invalid'])
def test_invalid_requests_are_rejected(client,url):
    assert client.get(url).status_code==422

@pytest.mark.parametrize('url',['/api/kpis','/api/filters','/api/dashboard','/api/operations','/api/rejections','/api/detail'])
def test_unauthenticated_access_is_denied(url):
    with TestClient(app) as c:
        assert c.get(url).status_code==401

def test_operational_trace_and_bounded_rejections(client):
    operations=client.get('/api/operations').json()
    assert operations['runs'] and len(operations['runs'])<=12
    assert operations['latest_success']['loaded_at'].endswith('+00:00')
    assert operations['watermarks']
    rows=client.get('/api/rejections?page_size=2').json()
    assert len(rows['items'])<=2
    assert all('OriginalRecord' not in row for row in rows['items'])

def test_breakdown_against_independent_source(client,dimensions):
    product=dimensions['product']
    payload=client.get('/api/breakdown',params={'dimension':'product','product_id':product,'start':'2016-03-01','end':'2016-05-31'}).json()
    expected=independent({'start':date(2016,3,1),'end':date(2016,5,31),'product':product,'category':None})
    assert len(payload['items'])==1
    assert payload['items'][0]['id']==product
    assert Decimal(payload['items'][0]['sales'])==expected['sales']

def test_api_database_user_cannot_write_even_with_empty_update():
    with engine(role='api').connect() as c:
        with pytest.raises(DBAPIError) as error:
            c.execute(text('UPDATE dw.FactSales SET Quantity=Quantity WHERE 1=0'))
        assert '(229)' in str(error.value.orig)

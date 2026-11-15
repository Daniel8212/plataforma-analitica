"""Pruebas ejecutables: requieren bootstrap y carga aceptada, sin cifras hardcodeadas."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from etl.connection import engine

@pytest.fixture(scope='module')
def latest_run():
    with engine().connect() as conn:
        run = conn.execute(text("SELECT TOP(1) CONVERT(varchar(36),ExecutionID) FROM audit.Execution WHERE Status='SUCCEEDED' AND LoadMode IN ('initial','full') ORDER BY EndTime DESC")).scalar()
    assert run, 'No hay carga exitosa; no se puede declarar el flujo validado'
    return {'id':run}

def test_independent_amount_and_grain(latest_run):
    with engine('WideWorldImporters').connect() as source:
        expected = source.execute(text('''SELECT COUNT_BIG(*) n,COUNT(DISTINCT InvoiceID) invoices,
            SUM(CONVERT(decimal(18,2),Quantity*UnitPrice)) sales,SUM(CONVERT(bigint,Quantity)) units
            FROM Sales.InvoiceLines''')).mappings().one()
    with engine().connect() as conn:
        actual = conn.execute(text('''SELECT COUNT_BIG(*) n,COUNT(DISTINCT InvoiceID) invoices,
            SUM(SalesAmount) sales,SUM(CONVERT(bigint,Quantity)) units FROM dw.FactSales''')).mappings().one()
        assert dict(actual) == dict(expected)
        assert conn.execute(text('''SELECT COUNT_BIG(*) FROM dw.FactSales f LEFT JOIN dw.DimDate d ON d.DateKey=f.DateKey
            LEFT JOIN dw.DimCustomer c ON c.CustomerKey=f.CustomerKey LEFT JOIN dw.DimProduct p ON p.ProductKey=f.ProductKey
            WHERE d.DateKey IS NULL OR c.CustomerKey IS NULL OR p.ProductKey IS NULL''')).scalar_one() == 0
        for table in ('raw.InvoiceLines','clean.SalesLine'):
            assert conn.execute(text(f'SELECT COUNT_BIG(*) FROM {table} WHERE ExecutionID=:id'),latest_run).scalar_one() == expected['n']

def test_reader_has_only_approved_view():
    with engine(role='api').connect() as conn:
        conn.execute(text('SELECT sales FROM dw.vSalesKpi')).one()
        with pytest.raises(DBAPIError) as error:
            conn.execute(text('SELECT TOP(1) * FROM raw.InvoiceLines')).all()
        assert '(229)' in str(error.value.orig), 'Debe fallar por permiso, no por otra causa'

def test_kpi_and_api_match(latest_run):
    import os
    from decimal import Decimal
    from fastapi.testclient import TestClient
    from backend.main import app
    with engine().connect() as conn:
        expected = conn.execute(text('SELECT SUM(SalesAmount) FROM dw.FactSales')).scalar_one()
        latest = conn.execute(text("SELECT TOP(1) CONVERT(varchar(36),ExecutionID) FROM audit.Execution WHERE Status='SUCCEEDED' ORDER BY EndTime DESC")).scalar_one()
    with TestClient(app) as client:
        assert client.get('/api/kpis').status_code == 401
        response = client.get('/api/kpis',headers={'X-API-Key':os.environ['DEMO_API_KEY']})
        assert response.status_code == 200
        assert Decimal(response.json()['sales']) == expected
        assert response.json()['execution_id'] == latest
        assert response.json()['loaded_at'].endswith('+00:00'), 'Auditoría debe identificar UTC'

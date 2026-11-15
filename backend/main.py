"""API con acceso de demo y lectura exclusiva de una vista analítica aprobada."""
import hmac
import os
from datetime import timezone
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from etl.connection import engine

app = FastAPI(title='Analítica de ventas', version='0.1.0')
api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)

def require_access(key: str | None = Security(api_key_header)):
    expected = os.getenv('DEMO_API_KEY', '')
    if not expected or not key or not hmac.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail='Acceso no autorizado')

@app.get('/api/health')
def health():
    return {'status': 'alive', 'version': app.version}

@app.get('/api/kpis', dependencies=[Depends(require_access)])
def kpis():
    """Contrato día 1; la vista se habilita tras validar la carga inicial."""
    try:
        with engine(role='api').connect() as conn:
            row = conn.execute(text('''SELECT sales, invoice_count, first_date,
                last_date, loaded_at, execution_id FROM dw.vSalesKpi''')).mappings().one()
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail='Data Warehouse no disponible') from None
    result = dict(row)
    result['sales'] = str(result['sales']) if result['sales'] is not None else None
    if result['loaded_at'] is not None:
        result['loaded_at'] = result['loaded_at'].replace(tzinfo=timezone.utc)
    return result

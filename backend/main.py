"""API analítica local: vistas aprobadas, parámetros y acceso de demostración."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from backend.analytics import router

app = FastAPI(title='Analítica de ventas',version='0.2.0')
app.include_router(router)

@app.get('/api/health')
def health():
    return {'status': 'alive', 'version': app.version}

@app.exception_handler(SQLAlchemyError)
def sql_error(_request,_error):
    return JSONResponse(status_code=503,content={'detail':'Data Warehouse no disponible. Revisa conexión, permisos y última carga.'})

"""Conexiones sin interpolar credenciales en SQL ni registrarlas."""
import os
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')

@lru_cache(maxsize=8)
def engine(database=None, role='etl'):
    if role == 'admin':
        user, password = 'sa', os.environ['MSSQL_SA_PASSWORD']
    elif role == 'api':
        user, password = os.environ['API_USER'], os.environ['API_PASSWORD']
    elif role == 'app':
        user, password = os.environ['APP_USER'], os.environ['APP_PASSWORD']
    else:
        user, password = os.environ['ETL_USER'], os.environ['ETL_PASSWORD']
    return create_engine(URL.create(
        'mssql+pyodbc', username=user, password=password,
        host=os.environ['SQL_HOST'], port=int(os.environ['SQL_PORT']),
        database=database or os.environ['DW_DATABASE'],
        query={'driver': os.environ['SQL_DRIVER'], 'Encrypt': 'yes',
               'TrustServerCertificate': 'yes'}),
        fast_executemany=True, pool_pre_ping=True, hide_parameters=True)

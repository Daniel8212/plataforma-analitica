"""DDL administrativo repetible y permisos técnicos separados."""
import os
import re
import argparse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from etl.connection import engine, ROOT

def ident(value):
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,100}', value):
        raise ValueError('Identificador de configuración inválido')
    return '[' + value + ']'

def main(grant_source_territories=False, warehouse_database=None, source_database=None):
    db = warehouse_database or os.environ['DW_DATABASE']
    source = source_database or os.environ['SOURCE_DATABASE']
    ident(db)
    ident(source)
    if db == source:
        raise ValueError('Fuente y DW deben ser bases distintas')
    with engine('master', 'admin').connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        if conn.execute(text('SELECT DB_ID(:db)'), {'db': db}).scalar() is None:
            conn.exec_driver_sql(f'CREATE DATABASE {ident(db)}')
        for prefix in ('ETL', 'API', 'APP'):
            user, password = os.environ[f'{prefix}_USER'], os.environ[f'{prefix}_PASSWORD']
            if not password:
                raise ValueError('Falta contraseña técnica local')
            if conn.execute(text('SELECT 1 FROM sys.server_principals WHERE name=:name'), {'name': user}).scalar() is None:
                # DDL SQL Server no admite parámetros de contraseña; escapar literal y validar identificador.
                literal = password.replace("'", "''")
                conn.exec_driver_sql(f"CREATE LOGIN {ident(user)} WITH PASSWORD=N'{literal}', CHECK_POLICY=ON")
    with engine(db, 'admin').begin() as conn:
        for filename in ('001_schema.sql','004_incremental.sql','007_read_views.sql','008_ml.sql','009_chat.sql','010_notifications.sql'):
            for batch in re.split(r'^GO\s*$', (ROOT/'database'/filename).read_text(encoding='utf-8'), flags=re.M|re.I):
                if batch.strip():
                    conn.exec_driver_sql(batch)
        for prefix in ('ETL', 'API', 'APP'):
            user = os.environ[f'{prefix}_USER']
            if conn.execute(text('SELECT USER_ID(:name)'), {'name': user}).scalar() is None:
                conn.exec_driver_sql(f'CREATE USER {ident(user)} FOR LOGIN {ident(user)}')
        loader, reader = ident(os.environ['ETL_USER']), ident(os.environ['API_USER'])
        conn.exec_driver_sql(f'GRANT SELECT, INSERT ON SCHEMA::raw TO {loader}')
        for schema in ('clean','dw','audit','ml','notify'):
            conn.exec_driver_sql(f'GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::{schema} TO {loader}')
        for view in ('dw.vSalesKpi','dw.vSalesRead','dw.vProductFilters','dw.vCategoryFilters',
                     'audit.vExecutions','audit.vRejections','audit.vWatermarks','ml.vActiveModel','ml.vPredictions','audit.vChatHealth','notify.vAlerts','notify.vTasks'):
            conn.exec_driver_sql(f'GRANT SELECT ON OBJECT::{view} TO {reader}')
        conn.exec_driver_sql(f"GRANT INSERT ON OBJECT::audit.ChatRequest TO {ident(os.environ['APP_USER'])}")
        for procedure in ('notify.MarkSeen','notify.ChangeState'):
            conn.exec_driver_sql(f"GRANT EXECUTE ON OBJECT::{procedure} TO {ident(os.environ['APP_USER'])}")
    with engine(source, 'admin').begin() as conn:
        user = os.environ['ETL_USER']
        if conn.execute(text('SELECT USER_ID(:name)'), {'name':user}).scalar() is None:
            conn.exec_driver_sql(f'CREATE USER {ident(user)} FOR LOGIN {ident(user)}')
        for table in ('Sales.Invoices','Sales.InvoiceLines','Sales.Customers','Sales.CustomerCategories','Warehouse.StockItems'):
            conn.exec_driver_sql(f'GRANT SELECT ON OBJECT::{table} TO {ident(user)}')
        # WWI aplica RLS: los roles territoriales son banderas de acceso sin permisos propios.
        # Se conserva la política activa; no se concede db_owner ni se modifica su función.
        if grant_source_territories:
            roles = ('External Sales','Far West Sales','Great Lakes Sales','Mideast Sales',
                     'New England Sales','Plains Sales','Rocky Mountain Sales','Southeast Sales','Southwest Sales')
            # La autorización debe referirse a estos nueve roles concretos, sin permisos propios.
            for role in roles:
                permissions = conn.execute(text('''SELECT COUNT(*) FROM sys.database_permissions p
                    JOIN sys.database_principals r ON r.principal_id=p.grantee_principal_id WHERE r.name=:role'''), {'role':role}).scalar_one()
                if permissions:
                    raise ValueError('El rol territorial tiene permisos adicionales: requiere revisión')
            for role in roles:
                if conn.execute(text('SELECT IS_ROLEMEMBER(:role,:member)'), {'role':role,'member':user}).scalar() != 1:
                    quoted_role = '[' + role.replace(']', ']]') + ']'
                    conn.exec_driver_sql(f'ALTER ROLE {quoted_role} ADD MEMBER {ident(user)}')
    print('Esquemas, tablas, vista y permisos creados. Aplicación sin sa.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--grant-source-territories',action='store_true',
                        help='Requiere autorización explícita: lectura RLS de los nueve territorios de la muestra')
    args = parser.parse_args()
    try:
        main(args.grant_source_territories)
    except SQLAlchemyError as exc:
        detail = str(getattr(exc, 'orig', type(exc).__name__))
        for name in ('MSSQL_SA_PASSWORD','ETL_PASSWORD','API_PASSWORD','APP_PASSWORD','DEMO_API_KEY'):
            secret = os.getenv(name)
            if secret:
                detail = detail.replace(secret, '[REDACTED]')
        raise SystemExit('Bootstrap SQL falló (sin SQL administrativo): ' + detail) from None

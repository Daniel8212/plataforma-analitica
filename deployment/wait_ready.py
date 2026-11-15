"""Diferencia SQL vivo de bases recuperadas y cuentas de aplicación utilizables."""
import argparse
import os
from time import monotonic,sleep
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from etl.connection import engine

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--databases',action='store_true',help='Exigir fuente/DW ONLINE y cuentas ETL/API/eventos')
    parser.add_argument('--timeout',type=int,default=180)
    args=parser.parse_args()
    if not 1<=args.timeout<=600:raise SystemExit('Timeout permitido: 1–600 segundos')
    deadline=monotonic()+args.timeout
    while True:
        try:
            with engine('master','admin').connect() as c:
                c.execute(text('SELECT 1')).scalar_one()
                if args.databases:
                    for name in (os.environ['SOURCE_DATABASE'],os.environ['DW_DATABASE']):
                        state=c.execute(text('SELECT state_desc FROM sys.databases WHERE name=:name'),{'name':name}).scalar()
                        if state!='ONLINE':raise RuntimeError('DATABASE_NOT_ONLINE')
            if args.databases:
                for database,role in ((os.environ['SOURCE_DATABASE'],'etl'),(os.environ['DW_DATABASE'],'etl'),
                                      (os.environ['DW_DATABASE'],'api'),(os.environ['DW_DATABASE'],'app')):
                    with engine(database,role).connect() as c:c.execute(text('SELECT 1')).scalar_one()
            print('SQL_READY: '+('bases ONLINE y cuatro conexiones técnicas' if args.databases else 'master disponible'))
            return
        except (SQLAlchemyError,RuntimeError):
            if monotonic()>=deadline:
                raise SystemExit('SQL_NOT_READY: revisar Docker, recuperación, variables y permisos; no se muestran secretos.') from None
            sleep(2)

if __name__=='__main__':main()

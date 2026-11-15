"""Restaura únicamente si la fuente no existe; sin REPLACE ni rutas adivinadas."""
import json
from pathlib import Path
from sqlalchemy import text
from etl.connection import engine, ROOT

def main():
    admin = engine('master', 'admin')
    with admin.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        version = conn.execute(text('SELECT @@VERSION')).scalar_one()
        state = conn.execute(text("SELECT state_desc FROM sys.databases WHERE name='WideWorldImporters'")).scalar()
        if state and state != 'RESTORING':
            raise SystemExit('La fuente ya existe. No se sobrescribe; ejecutar perfilado.')
        files = conn.exec_driver_sql("RESTORE FILELISTONLY FROM DISK = '/backups/WideWorldImporters-Full.bak'").mappings().all()
        moves = []
        for row in files:
            logical = row['LogicalName'].replace("'", "''")
            suffix = {'D': '.mdf', 'L': '.ldf', 'S': ''}[row['Type']]
            target = f'/var/opt/mssql/data/{logical}{suffix}'
            moves.append(f"MOVE N'{logical}' TO N'{target}'")
        # ODBC puede devolver mensajes antes de completar RESTORE: consumir todos los resultados.
        # Cerrar un cursor prematuramente puede cancelar la operación y dejar RESTORING.
        cursor = conn.connection.driver_connection.cursor()
        try:
            cursor.execute("RESTORE VERIFYONLY FROM DISK = '/backups/WideWorldImporters-Full.bak'")
            while cursor.nextset():
                pass
            cursor.execute("RESTORE DATABASE [WideWorldImporters] FROM DISK = '/backups/WideWorldImporters-Full.bak' WITH " + ', '.join(moves) + ', RECOVERY')
            while cursor.nextset():
                pass
        finally:
            cursor.close()
        final_state = conn.execute(text("SELECT state_desc FROM sys.databases WHERE name='WideWorldImporters'")).scalar_one()
        if final_state != 'ONLINE':
            raise RuntimeError(f'Restauración no confirmada: {final_state}')
        result = {'server_version': version, 'state': final_state, 'backup_verified': True,
                  'backup_files': [dict(r) for r in files]}
    out = ROOT / 'documentation/evidence'
    out.mkdir(exist_ok=True)
    (out / 'restore.json').write_text(json.dumps(result, default=str, indent=2), encoding='utf-8')
    print('Restauración completada. Evidencia: documentation/evidence/restore.json')

if __name__ == '__main__':
    main()

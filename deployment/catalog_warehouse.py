"""Diccionario de capas analíticas desde el catálogo del entorno ejecutado."""
from sqlalchemy import text
from etl.connection import engine, ROOT

def main():
    with engine().connect() as conn:
        rows = conn.execute(text('''SELECT s.name AS schema_name,t.name AS table_name,c.name AS column_name,
            ty.name AS data_type,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity
            FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
            JOIN sys.columns c ON c.object_id=t.object_id JOIN sys.types ty ON ty.user_type_id=c.user_type_id
            WHERE s.name IN ('raw','clean','dw','audit','ml','notify') ORDER BY s.name,t.name,c.column_id''')).mappings().all()
    lines = ['# Diccionario de capas analíticas — catálogo ejecutado','',
             'Longitudes en bytes; nvarchar usa dos bytes por carácter. Semántica de medidas: modelo-ventas.md.',
             'Raw conserva las proyecciones originales definidas en etl/pipeline.py por ExecutionID.',
             'RowsRead en audit.Execution suma filas de las cinco tablas; RowsInserted cuenta hechos nuevos.',
             'StageCount detalla lectura/inserción por objeto. EndTime/StartTime/RecordedAt usan UTC.',
             'Semántica de ML, chat y alertas: diccionario-operativo.md. DDL: database/001,004,008,009,010.','',
             '| Tabla | Columna | Tipo | Bytes | Precisión | Escala | Nullable | Identity |',
             '|---|---|---|---|---|---|---|---|']
    for r in rows:
        lines.append(f"| {r['schema_name']}.{r['table_name']} | {r['column_name']} | {r['data_type']} | {r['max_length']} | {r['precision']} | {r['scale']} | {r['is_nullable']} | {r['is_identity']} |")
    (ROOT/'documentation/diccionario-analitico.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Diccionario analítico generado del catálogo real')

if __name__ == '__main__':
    main()

"""Exporta resultados reales del catálogo y perfilado para revisión del modelo."""
import json
import re
from sqlalchemy import text
from etl.connection import engine, ROOT

def main():
    output = []
    sql = (ROOT / 'database/profile.sql').read_text(encoding='utf-8')
    with engine('WideWorldImporters', 'admin').connect() as conn:
        for batch in re.split(r'^GO\s*$', sql, flags=re.M | re.I):
            if batch.strip():
                rows = conn.execute(text(batch)).mappings().all()
                output.append({'query': batch.strip(), 'rows': [dict(r) for r in rows]})
    path = ROOT / 'documentation/evidence/source-profile.json'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output, default=str, indent=2, ensure_ascii=False), encoding='utf-8')
    columns = output[1]['rows']
    dictionary = ['# Diccionario de fuente — generado del catálogo real', '',
                  '| Tabla | Columna | Tipo | Longitud bytes | Precisión | Escala | Nullable |',
                  '|---|---|---|---|---|---|---|']
    for col in columns:
        dictionary.append(f"| {col['schema_name']}.{col['table_name']} | {col['column_name']} | {col['data_type']} | {col['max_length']} | {col['precision']} | {col['scale']} | {col['is_nullable']} |")
    (ROOT / 'documentation/diccionario-fuente.md').write_text('\n'.join(dictionary), encoding='utf-8')
    relevant = {f"{c['schema_name']}.{c['table_name']}" for c in columns}
    diagram = ['# ERD de fuente — relaciones del catálogo real', '', '```mermaid', 'erDiagram']
    seen = set()
    for fk in output[2]['rows']:
        source = f"{fk['source_schema']}.{fk['source_table']}"
        target = f"{fk['target_schema']}.{fk['target_table']}"
        if source in relevant and target in relevant and fk['fk_name'] not in seen:
            # Cardinalidad padre 0/1: revisar nullable en el diccionario; cada FK tiene un único padre.
            diagram.append(f"  {target.replace('.', '_')} |o--o{{ {source.replace('.', '_')} : {fk['source_column']}")
            seen.add(fk['fk_name'])
    diagram += ['```', '', 'El marcador 0/1 representa opcionalidad conservadora; consultar nullable y FK en el diccionario.',
                'Se muestran las tablas del alcance inspeccionado; relaciones externas quedan en source-profile.json.']
    (ROOT / 'documentation/erd-fuente.md').write_text('\n'.join(diagram), encoding='utf-8')
    print(f'Perfilado guardado: {path}')

if __name__ == '__main__':
    main()

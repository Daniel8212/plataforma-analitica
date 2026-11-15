"""Copia verificable sin Git/runtime/secretos versionados; no cambia .env original."""
import hashlib
import json
import shutil
import subprocess
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    target=ROOT/'data'/('rebuild-'+stamp)
    target.mkdir(parents=True,exist_ok=False)
    files=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),
                                  'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
    copied=[]
    for name in filter(None,files):
        source=(ROOT/name).resolve()
        if not source.is_relative_to(ROOT) or name=='.env' or name.startswith(('data/','.git/','.venv/')):
            raise ValueError('Archivo fuera del alcance de copia')
        if not source.is_file():continue
        dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,dest);copied.append(name)
    shutil.copy2(ROOT/'.env',target/'.env')
    from dotenv import set_key
    set_key(str(target/'.env'),'SQL_PORT','14334')
    backup=ROOT/'data/backups/WideWorldImporters-Full.bak'
    (target/'data/backups').mkdir(parents=True)
    shutil.copy2(backup,target/'data/backups'/backup.name)
    report={'created_at':stamp,'checkout':str(target),'files':len(copied),'project':'plataforma-rebuild-'+stamp.lower(),
            'sql_port':14334,'backup_sha256':hashlib.sha256(backup.read_bytes()).hexdigest(),
            'note':'Copia local .env ignorada, puerto aislado, sin reutilizar venv/node_modules ni volumen SQL.'}
    (target/'data/rebuild-manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (ROOT/'data/rebuild-latest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()

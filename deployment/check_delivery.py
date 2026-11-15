"""Revisa secretos conocidos, archivos excluidos y enlaces Markdown sin publicarlos."""
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]

def git(*args):return subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),*args])

def main():
    tracked=git('ls-files','-z').decode().split('\0')
    files=git('ls-files','--cached','--others','--exclude-standard','-z').decode().split('\0')
    forbidden=[p for p in tracked if p and (p=='.env' or p.startswith(('data/','.venv/','frontend/node_modules/')) or p.endswith(('.bak','.joblib')))]
    assert not forbidden,'Archivo privado versionado: '+','.join(forbidden)
    secrets=[v.encode() for k,v in dotenv_values(ROOT/'.env').items() if v and ('PASSWORD' in k or 'KEY' in k)]
    missing=[];scanned=0
    for name in filter(None,files):
        path=ROOT/name
        if not path.is_file():continue
        content=path.read_bytes();scanned+=1
        assert not any(v in content for v in secrets),'Secreto conocido en '+name
        if path.suffix!='.md':continue
        for angle,plain in re.findall(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))\)',content.decode('utf-8',errors='replace')):
            ref=angle or plain
            if re.match(r'^[a-zA-Z]+:|^#',ref):continue
            dest=(path.parent/unquote(ref.split('#')[0])).resolve()
            if not dest.exists():missing.append({'document':name,'target':ref})
    history=git('log','--all','--format=','--patch')
    assert not any(v in history for v in secrets),'Secreto conocido en historia textual Git'
    required=['documentation/operacion.md','documentation/manual-usuario.md','documentation/revision-final.md',
              'documentation/diagramas/arquitectura.mmd','documentation/diagramas/erd-fuente.mmd','documentation/diagramas/modelo-ventas.mmd']
    assert all((ROOT/p).is_file() for p in required),'Falta entregable técnico'
    report={'secrets_scan':'passed','scope':'Valores PASSWORD/KEY actuales de .env en archivos no ignorados e historia textual Git; no sustituye un detector universal.',
            'scanned_files':scanned,'private_tracked_files':forbidden,'missing_markdown_links':missing,
            'note':'Los enlaces de exportaciones del usuario pendientes se informan; no se reescriben sus documentos.'}
    out=ROOT/'documentation/evidence/delivery-check.json'
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Secretos conocidos: OK; archivos privados excluidos; enlaces pendientes:',len(missing))

if __name__=='__main__':main()

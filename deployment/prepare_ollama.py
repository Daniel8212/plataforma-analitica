"""Extrae solo CPU del ZIP oficial fijado, por rangos HTTP; no instala fuera del proyecto."""
import hashlib
import io
import json
import zipfile
import zlib
import httpx
from etl.connection import ROOT

VERSION='v0.40.16'
SIZE=1618244995
URL=f'https://github.com/ollama/ollama/releases/download/{VERSION}/ollama-windows-amd64.zip'

class RemoteZip(io.RawIOBase):
    def __init__(self):
        self.position=0
        self.transferred=0
        self.client=httpx.Client(follow_redirects=True,timeout=180)
    def seekable(self):
        return True
    def seek(self,offset,whence=0):
        self.position=offset if whence==0 else self.position+offset if whence==1 else SIZE+offset
        if not 0<=self.position<=SIZE:
            raise ValueError('Rango fuera del archivo')
        return self.position
    def tell(self):
        return self.position
    def read(self,n=-1):
        start=self.position
        if start>=SIZE or n==0:
            return b''
        end=SIZE-1 if n<0 else min(SIZE-1,start+n-1)
        response=self.client.get(URL,headers={'Range':f'bytes={start}-{end}'})
        if response.status_code!=206 or response.headers.get('Content-Range')!=f'bytes {start}-{end}/{SIZE}':
            raise RuntimeError('Servidor sin rangos válidos; no descargar el ZIP completo implícitamente')
        data=response.content
        if len(data)!=end-start+1:
            raise RuntimeError('Transferencia incompleta')
        self.transferred+=len(data)
        self.position=end+1
        return data

def main():
    destination=(ROOT/'data/tools'/f'ollama-{VERSION}').resolve()
    destination.mkdir(parents=True,exist_ok=True)
    remote=RemoteZip()
    files=[]
    try:
        with zipfile.ZipFile(remote) as archive:
            for entry in archive.infolist():
                name=entry.filename
                if entry.is_dir() or not (name=='ollama.exe' or name.startswith('lib/ollama/') and '/' not in name[len('lib/ollama/'):]):
                    continue
                if 'cuda' in name.lower() or 'vulkan' in name.lower():
                    continue
                path=(destination/name).resolve()
                if not path.is_relative_to(destination) or entry.file_size>100_000_000:
                    raise ValueError('Ruta/tamaño no autorizado en archivo')
                if path.exists():
                    data=path.read_bytes()
                    if zlib.crc32(data)&0xffffffff != entry.CRC:
                        raise RuntimeError('Archivo local distinto: no se sobrescribe '+name)
                else:
                    data=archive.read(entry)  # zipfile verifica CRC al terminar cada entrada.
                    path.parent.mkdir(parents=True,exist_ok=True)
                    path.write_bytes(data)
                files.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    finally:
        remote.client.close()
    manifest={'version':VERSION,'source':URL,'runtime':'CPU','downloaded_bytes':remote.transferred,'files':files,
              'integrity':'HTTPS oficial + CRC por entrada; SHA256 local por archivo. No se verificó hash del ZIP completo, pues no se descargó completo.'}
    (destination/'cpu-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'runtime_path':str(destination),'files':len(files),'downloaded_bytes':remote.transferred}))

if __name__=='__main__':
    main()

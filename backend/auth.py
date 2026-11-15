import hmac
import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

header=APIKeyHeader(name='X-API-Key',auto_error=False)

def require_access(key: str | None=Security(header)):
    expected=os.getenv('DEMO_API_KEY','')
    if not expected or not key or not hmac.compare_digest(key.encode(),expected.encode()):
        raise HTTPException(status_code=401,detail='Acceso no autorizado')

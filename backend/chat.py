from collections import defaultdict,deque
import threading
from time import monotonic
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field,field_validator
from backend.auth import require_access
from generative_ai.service import answer_question
from generative_ai.ollama import ProviderUnavailable

router=APIRouter(prefix='/api',dependencies=[Depends(require_access)])
BUCKETS=defaultdict(deque)
BUCKET_LOCK=threading.Lock()

class ChatInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    question:str=Field(min_length=3,max_length=500)
    @field_validator('question')
    @classmethod
    def meaningful(cls,value):
        value=value.strip()
        if len(value)<3:raise ValueError('Escribe una pregunta válida')
        return value

def enforce_rate(client,now=None):
    now=monotonic() if now is None else now
    with BUCKET_LOCK:
        bucket=BUCKETS[client]
        while bucket and bucket[0]<=now-60:bucket.popleft()
        if len(bucket)>=12:raise HTTPException(429,'Máximo doce preguntas por minuto para esta demo local.',headers={'Retry-After':'60'})
        bucket.append(now)

@router.post('/chat')
def chat(body:ChatInput,request:Request):
    enforce_rate(request.client.host if request.client else 'local')
    try:
        return answer_question(body.question)
    except ProviderUnavailable as exc:
        raise HTTPException(503,str(exc)) from None

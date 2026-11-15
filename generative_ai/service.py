import hashlib
import json
import re
import threading
from time import perf_counter
from uuid import uuid4
from sqlalchemy import text
from backend.analytics import encoded
from etl.connection import engine
from generative_ai.analytics_tools import context_for
from generative_ai.ollama import generate,ProviderUnavailable

MODEL_LOCK=threading.BoundedSemaphore(1)

def verify(value,context):
    issues=[]
    summary=value.get('resumen') if isinstance(value,dict) else None
    citations=value.get('citas',[]) if isinstance(value,dict) else []
    if not isinstance(summary,str) or not 5<=len(summary)<=500:
        return ['Estructura o longitud del resumen no válida']
    if re.search(r'\d',summary):issues.append('Cifras/fechas no permitidas en la interpretación generada')
    if re.search(r'\$|\bXX\b|no (?:incluye|hay|dispone|contiene)|sin (?:datos|informaci[oó]n)|no.*detalles',summary,re.I):
        issues.append('Marcador numérico o ausencia de datos incompatible con el respaldo disponible')
    if re.search(r'debid|caus|gracias a|promoci|clima|significativ|garanti|asegur|continuar[aá]|recomiend',summary,re.I):
        issues.append('Causa, significancia, recomendación o garantía sin respaldo')
    known={f['id'] for f in context['facts']}
    if not isinstance(citations,list) or not citations or not all(isinstance(c,str) and c in known for c in citations):
        issues.append('Citas ausentes o no autorizadas')
    up=bool(re.search(r'aument|creci|subi|increment|superior|mayor',summary,re.I))
    down=bool(re.search(r'disminu|cay|ca[ií]d|baj|inferior|menor|reduj|reduc',summary,re.I))
    if context.get('relation')=='increase' and down or context.get('relation')=='decrease' and up:
        issues.append('Dirección opuesta a la comparación verificada')
    if context.get('relation') in (None,'equal') and (up or down) and context['tool'] not in ('top_products','category_growth'):
        issues.append('Comparación no respaldada por la herramienta')
    return issues

def write_audit(question,response,raw,evaluation,duration):
    record={**response,'raw_generation_for_audit':raw}
    with engine(role='app').begin() as conn:
        conn.execute(text('''INSERT audit.ChatRequest(RequestID,QuestionHash,ToolName,Status,SourceExecutionID,Model,
            DurationMs,IsEvaluation,ResponseJson,UnverifiedJson) VALUES(:id,:hash,:tool,:status,:source,:model,:duration,:evaluation,:response,:unverified)'''),
            {'id':response['request_id'],'hash':hashlib.sha256(question.encode()).hexdigest(),'tool':response['tool'],
             'status':response['status'],'source':response['dataset'].get('execution_id'),
             'model':response.get('provider',{}).get('model'),'duration':duration,'evaluation':evaluation,
             'response':json.dumps(encoded(record),ensure_ascii=False),'unverified':json.dumps(response['verification']['blocked_claims'],ensure_ascii=False)})

def answer_question(question,*,evaluation=False,provider=generate,audit=write_audit):
    start=perf_counter()
    context=context_for(question)
    response={'request_id':str(uuid4()),'status':context['status'],'tool':context['tool'],
        'dataset':context['dataset'],'facts':context['facts'],'generated':False,
        'verification':{'blocked_claims':[],'method':'Herramientas cerradas + esquema + control de cifras, citas, dirección y afirmaciones causales.'}}
    raw=None
    unavailable=None
    if context['status']!='answered':
        response['answer']=context['message']
    else:
        if not MODEL_LOCK.acquire(blocking=False):
            raise ProviderUnavailable('El modelo local está ocupado; reintenta cuando termine la otra solicitud.')
        try:
            value,provider_info=provider(context)
            raw=value
            issues=verify(value,context)
            response['provider']=provider_info
            response['verification']['blocked_claims']=issues
            if issues:
                response.update(status='grounded_fallback',answer='La explicación generada no superó la verificación. Se muestran únicamente las métricas consultadas.')
            else:
                response.update(answer=value['resumen'],generated=True,citations=value['citas'])
        except ProviderUnavailable as exc:
            response.update(status='provider_unavailable',answer=str(exc));unavailable=exc
        finally:
            MODEL_LOCK.release()
    for key in ('reference_period','forecast_as_of'):
        if key in context:response[key]=context[key]
    response['duration_ms']=round((perf_counter()-start)*1000)
    audit(question,response,raw,evaluation,response['duration_ms'])
    if unavailable:raise unavailable
    return encoded(response)

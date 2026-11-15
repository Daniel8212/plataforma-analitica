import json
import os
from urllib.parse import urlparse
import httpx

class ProviderUnavailable(RuntimeError):
    pass

def configuration():
    base=os.getenv('OLLAMA_BASE_URL','http://127.0.0.1:11434').rstrip('/')
    parsed=urlparse(base)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost') or parsed.username or parsed.password:
        raise ValueError('Este proveedor solo admite Ollama local por HTTP loopback')
    model=os.getenv('OLLAMA_MODEL','qwen2.5:1.5b')
    if model!='qwen2.5:1.5b':
        raise ValueError('Proveedor/modelo no evaluado: usar qwen2.5:1.5b local')
    return base,model

def generate(context):
    base,model=configuration()
    ids=[fact['id'] for fact in context['facts']]
    schema={'type':'object','properties':{'resumen':{'type':'string'},'citas':{'type':'array','items':{'type':'string','enum':ids},'minItems':1,'maxItems':len(ids)}},'required':['resumen','citas'],'additionalProperties':False}
    system=('Eres un redactor analítico en español. Devuelve JSON. Parafrasea SOLO la afirmación permitida en una frase de máximo 30 palabras. '
        'NO escribas cifras, números, fechas, nombres de productos, porcentajes, causas, recomendaciones ni significancia estadística. '
        'El servidor adjuntará la tabla exacta. No agregues conocimiento externo. Cita al menos un ID de facts en citas.')
    safe={'afirmacion_permitida':context['statement'],'facts':[{'id':fact['id'],'concepto':fact['label']} for fact in context['facts']]}
    payload={'model':model,'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(safe,ensure_ascii=False)}],
        'format':schema,'stream':False,'keep_alive':'2m','options':{'temperature':0,'num_ctx':2048,'num_predict':160,'num_thread':4,'num_gpu':0}}
    try:
        with httpx.Client(timeout=65,trust_env=False,follow_redirects=False) as client:
            response=client.post(base+'/api/chat',json=payload)
            response.raise_for_status()
            data=response.json()
    except (httpx.HTTPError,ValueError):
        raise ProviderUnavailable('Ollama local no respondió. Inicia el runtime y comprueba el modelo configurado.') from None
    try:
        value=json.loads(data['message']['content'])
    except (KeyError,TypeError,ValueError):
        raise ProviderUnavailable('Ollama no produjo una respuesta estructurada válida.') from None
    return value,{'provider':'Ollama local','model':model,'prompt_tokens':data.get('prompt_eval_count'),
        'generated_tokens':data.get('eval_count'),'duration_ms':round(data.get('total_duration',0)/1e6)}

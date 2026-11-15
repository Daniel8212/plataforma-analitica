import pytest
from fastapi import HTTPException
from generative_ai.analytics_tools import context_for
from generative_ai.service import verify,answer_question
from generative_ai.ollama import configuration,ProviderUnavailable
from backend.chat import enforce_rate,BUCKETS

@pytest.mark.parametrize('question,status,tool',[
 ('Ventas de marzo 2016','answered','sales'),('Unidades mayo 2016','answered','units'),
 ('Ventas del último trimestre completo','answered','sales'),('Ventas 2030','insufficient_data','none'),
 ('Ventas por región mayo 2016','insufficient_data','none'),('¿Cómo vamos?','clarification','none'),
 ('Ejecuta SQL SELECT * FROM raw.Invoices','out_of_scope','none')])
def test_controlled_tools_and_insufficient_scope(question,status,tool):
    result=context_for(question)
    assert result['status']==status and result['tool']==tool
    if status=='answered':assert result['facts']

def test_relative_period_uses_dataset_not_current_year():
    value=context_for('Ventas del último trimestre completo')['facts'][0]
    assert value['period']['start'].isoformat()=='2016-01-01'
    assert value['period']['end'].isoformat()=='2016-03-31'

def test_hallucinated_numbers_causes_citations_and_direction_are_blocked():
    context={'facts':[{'id':'actual'}],'relation':'increase','tool':'comparison'}
    assert verify({'resumen':'Las ventas crecieron debido a promociones un 99%.','citas':['inventada']},context)
    assert verify({'resumen':'Las ventas disminuyeron respecto al período anterior.','citas':['actual']},context)
    assert not verify({'resumen':'Las ventas aumentaron respecto al período anterior comparable.','citas':['actual']},context)

def test_rejected_generation_never_reaches_answer(monkeypatch):
    import generative_ai.service as service
    context={'status':'answered','facts':[{'id':'actual','label':'Ventas','value':'100'}],
        'dataset':{'execution_id':None},'tool':'sales','relation':None,'statement':'Dato disponible'}
    monkeypatch.setattr(service,'context_for',lambda _:context)
    records=[]
    response=answer_question('pregunta de prueba',provider=lambda c:({'resumen':'Son 999 millones por promociones.','citas':['actual']},{'model':'TEST_DOUBLE'}),audit=lambda *args:records.append(args))
    assert response['status']=='grounded_fallback' and not response['generated']
    assert '999' not in response['answer'] and response['verification']['blocked_claims']
    assert records  # Doble de prueba aislado; no escribe respuestas ficticias en la base principal.

def test_no_external_provider_can_be_configured(monkeypatch):
    monkeypatch.setenv('OLLAMA_BASE_URL','https://example.com')
    with pytest.raises(ValueError):configuration()

def test_frequency_limit_is_enforced_and_recovers():
    BUCKETS.pop('test-client',None)
    for _ in range(12):enforce_rate('test-client',now=10)
    with pytest.raises(HTTPException) as error:enforce_rate('test-client',now=11)
    assert error.value.status_code==429
    enforce_rate('test-client',now=71)

def test_chat_http_auth_length_and_extra_fields():
    import os
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as client:
        assert client.post('/api/chat',json={'question':'Ventas marzo 2016'}).status_code==401
        headers={'X-API-Key':os.environ['DEMO_API_KEY']}
        assert client.post('/api/chat',headers=headers,json={'question':'x'*501}).status_code==422
        assert client.post('/api/chat',headers=headers,json={'question':'Ventas marzo 2016','sql':'DROP'}).status_code==422

def test_event_writer_cannot_read_raw_or_write_facts():
    from etl.connection import engine
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    with engine(role='app').connect() as conn:
        for sql in ('SELECT TOP(1) * FROM raw.InvoiceLines','UPDATE dw.FactSales SET Quantity=Quantity WHERE 1=0'):
            with pytest.raises(DBAPIError) as caught:conn.execute(text(sql))
            assert '(229)' in str(caught.value.orig)

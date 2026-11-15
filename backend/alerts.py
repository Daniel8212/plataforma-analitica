from uuid import UUID
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,ConfigDict
from sqlalchemy import text
from backend.auth import require_access
from backend.analytics import read_connection,encoded
from etl.connection import engine

router=APIRouter(prefix='/api',dependencies=[Depends(require_access)])

@router.get('/alerts')
def alerts():
    with read_connection() as c:
        items=c.execute(text('SELECT TOP(100) * FROM notify.vAlerts ORDER BY CreatedAt DESC')).mappings().all()
        tasks=c.execute(text('SELECT TOP(20) * FROM notify.vTasks ORDER BY CreatedAt DESC')).mappings().all()
    return encoded({'items':items,'tasks':tasks,'threshold_percent':15,'reference':'Última semana completa frente a la anterior, según fecha máxima del DW.'})

@router.post('/alerts/{alert_id}/seen')
def seen(alert_id:UUID):
    with engine(role='app').begin() as c:
        count=c.execute(text('EXEC notify.MarkSeen @id=:id'),{'id':str(alert_id)}).scalar_one()
    if not count:raise HTTPException(404,'Alerta no encontrada')
    return {'delivered':True}

class StateInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    state:Literal['ATTENDED','DISCARDED']

@router.post('/alerts/{alert_id}/state')
def change_state(alert_id:UUID,body:StateInput):
    with engine(role='app').begin() as c:
        count=c.execute(text('EXEC notify.ChangeState @id=:id,@state=:state'),{'id':str(alert_id),'state':body.state}).scalar_one()
    return {'changed':bool(count)}

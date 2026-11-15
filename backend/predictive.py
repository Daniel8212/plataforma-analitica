"""Resultados ML persistidos; el servidor web no carga pickles ni acepta artefactos externos."""
import json
from fastapi import APIRouter, Depends
from sqlalchemy import text
from backend.auth import require_access
from backend.analytics import read_connection, encoded

router=APIRouter(prefix='/api',dependencies=[Depends(require_access)])

@router.get('/forecast')
def forecast():
    with read_connection() as conn:
        model=conn.execute(text('SELECT * FROM ml.vActiveModel')).mappings().first()
        if model is None:
            return {'available':False,'reason':'Todavía no hay un modelo entrenado y publicado.','forecast':[]}
        report=json.loads(model['ReportJson'])
        rows=[dict(row) for row in conn.execute(text('SELECT * FROM ml.vPredictions ORDER BY TargetWeekStart,Kind')).mappings()]
        changed=conn.execute(text('''SELECT COUNT(*) FROM audit.vExecutions WHERE Status='SUCCEEDED'
            AND (RowsInserted>0 OR RowsUpdated>0) AND EndTime>(SELECT EndTime FROM audit.vExecutions WHERE ExecutionID=:id)'''),
            {'id':model['SourceExecutionID']}).scalar_one()
        return encoded({'available':True,'version':model['Version'],'algorithm':model['Algorithm'],
            'generated_at':model['GeneratedAt'],'as_of':model['AsOfDate'],'source_last_date':model['SourceLastDate'],
            'source_execution_id':model['SourceExecutionID'],'dataset_hash':model['DatasetHash'],
            'needs_retraining':bool(changed),'complete_weeks':model['CompleteWeeks'],'splits':report['splits'],
            'metrics':json.loads(model['MetricsJson']),'parameters':json.loads(model['ParametersJson']),
            'history':report['history'],'quality':report['quality'],'limitations':report['limitations'],
            'forecast':[row for row in rows if row['Kind']=='future'],
            'test_predictions':[row for row in rows if row['Kind']=='test']})

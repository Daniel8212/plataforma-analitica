"""Entrena desde DW, evalúa fuera de muestra y persiste predicciones trazables."""
import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from uuid import uuid4
import joblib
import numpy as np
import pandas as pd
import sklearn
from sqlalchemy import text
from etl.connection import ROOT, engine
from machine_learning.forecasting import FEATURES, LAGS, experiment

def snapshot(conn):
    coverage=conn.execute(text('SELECT MIN(InvoiceDate) first_date,MAX(InvoiceDate) last_date FROM dw.vSalesRead')).mappings().one()
    if coverage['first_date'] is None:
        raise ValueError('DW sin ventas válidas')
    rows=conn.execute(text("""SELECT CONVERT(date,DATEADD(day,-(DATEDIFF(day,'19000101',InvoiceDate)%7),InvoiceDate)) week_start,
        SUM(SalesAmount) sales,COUNT_BIG(*) lines FROM dw.vSalesRead
        GROUP BY CONVERT(date,DATEADD(day,-(DATEDIFF(day,'19000101',InvoiceDate)%7),InvoiceDate)) ORDER BY week_start""")).mappings().all()
    first=coverage['first_date'];last=coverage['last_date']
    monday=first+timedelta(days=(7-first.weekday())%7)
    last_monday=last-timedelta(days=last.weekday())
    if last.weekday()!=6:
        last_monday-=timedelta(days=7)
    calendar=pd.date_range(monday,last_monday,freq='W-MON')
    values={pd.Timestamp(row['week_start']):row['sales'] for row in rows}
    series=pd.Series([float(values.get(day,0)) for day in calendar],index=calendar,name='sales')
    canonical=[{'week':day.date().isoformat(),'sales':f'{values.get(day,0):.2f}'} for day in calendar]
    dataset_hash=hashlib.sha256(json.dumps(canonical,separators=(',',':')).encode()).hexdigest()
    source=conn.execute(text("SELECT TOP(1) CONVERT(varchar(36),ExecutionID) FROM audit.Execution WHERE Status='SUCCEEDED' ORDER BY EndTime DESC")).scalar_one()
    weekly_q1,weekly_q3=np.quantile(series,[.25,.75]);spread=weekly_q3-weekly_q1
    weekly_flags=[{'week':day.date().isoformat(),'sales':float(value)} for day,value in series.items() if value<weekly_q1-1.5*spread or value>weekly_q3+1.5*spread]
    quality={'complete_weeks':len(series),'partial_weeks_excluded':[str(row['week_start']) for row in rows if pd.Timestamp(row['week_start']) not in calendar],
        'missing_weeks_filled_with_zero':sum(day not in values for day in calendar),
        'non_finite':int((~np.isfinite(series.to_numpy())).sum()),'negative_weeks':int((series<0).sum()),
        'weekly_iqr_bounds':[float(weekly_q1-1.5*spread),float(weekly_q3+1.5*spread)],'weekly_outliers':weekly_flags,
        'treatment':'No se eliminan outliers automáticamente. Se conservan ventas válidas; las semanas parciales se excluyen por comparabilidad, no por ser atípicas.'}
    return series,dict(coverage),source,dataset_hash,quality

def line_outliers(conn):
    result={}
    for column in ('Quantity','UnitPrice','SalesAmount'):
        # Identificadores de lista cerrada; límites numéricos vinculados como parámetros.
        q=conn.execute(text(f'''SELECT TOP(1) PERCENTILE_CONT(.25) WITHIN GROUP(ORDER BY {column}) OVER() q1,
            PERCENTILE_CONT(.75) WITHIN GROUP(ORDER BY {column}) OVER() q3 FROM dw.vSalesRead''')).mappings().one()
        low=float(q['q1'])-1.5*(float(q['q3'])-float(q['q1']));high=float(q['q3'])+1.5*(float(q['q3'])-float(q['q1']))
        params={'low':low,'high':high}
        n=conn.execute(text(f'SELECT COUNT_BIG(*) FROM dw.vSalesRead WHERE {column}<:low OR {column}>:high'),params).scalar_one()
        examples=[dict(row) for row in conn.execute(text(f'''SELECT TOP(5) InvoiceLineID,ProductName,Quantity,UnitPrice,SalesAmount
            FROM dw.vSalesRead WHERE {column}<:low OR {column}>:high ORDER BY {column} DESC,InvoiceLineID'''),params).mappings()]
        result[column]={'q1':float(q['q1']),'q3':float(q['q3']),'lower':low,'upper':high,'flagged':n,'examples':examples}
    return result

def main():
    with engine().connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        with conn.begin():
            series,coverage,source,dataset_hash,quality=snapshot(conn)
            quality['line_outliers']=line_outliers(conn)
    if quality['non_finite'] or quality['negative_weeks']:
        raise ValueError('Serie no válida para este problema')
    result,models=experiment(series)
    version='weekly-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+uuid4().hex[:8]
    target=ROOT/'data/models'/version
    target.mkdir(parents=True,exist_ok=False)
    series.to_csv(target/'weekly-sales.csv',index_label='week_start',float_format='%.2f')
    series.to_csv(ROOT/'documentation/evidence/ml-weekly-series.csv',index_label='week_start',float_format='%.2f')
    code_hash=hashlib.sha256(b''.join(path.read_bytes() for path in sorted((ROOT/'machine_learning').glob('*.py')))).hexdigest()
    params={'features':FEATURES,'lags':list(LAGS),'horizon_weeks':4,'clip_nonnegative':True,'seed':42,
            'sklearn_version':sklearn.__version__,'code_sha256':code_hash,
            'selection':'MAE en validación recursiva; el conjunto de prueba nunca selecciona algoritmo ni parámetros.',
            'deployment_refit':'Tras evaluar prueba, reentrenar con todas las semanas completas.'}
    artifact=target/'model.joblib'
    joblib.dump({**models,'algorithm':result['selected'],'best_learned':result['best_learned'],
        'parameters':params,'dataset_hash':dataset_hash,'features':FEATURES},artifact)
    checksum=hashlib.sha256(artifact.read_bytes()).hexdigest()
    report={**result,'version':version,'dataset_hash':dataset_hash,'source_execution_id':source,'parameters':params,
        'coverage':coverage,'as_of':(series.index[-1].date()+timedelta(days=6)).isoformat(),'quality':quality,
        'history':[{'week_start':day.date().isoformat(),'sales':float(value)} for day,value in series.iloc[-12:].items()],
        'artifact_path':artifact.relative_to(ROOT).as_posix(),'artifact_sha256':checksum,
        'series_snapshot_path':(target/'weekly-sales.csv').relative_to(ROOT).as_posix(),
        'limitations':['Muestra comercial sintética de Microsoft, no ventas actuales de una empresa real.',
            'Pocas observaciones y una sola separación temporal; sin intervalos de confianza ni garantías de precisión.',
            'La primera semana pronosticada puede coincidir con días parciales ya presentes en el DW; no se usaron esos días para entrenar.',
            'No se infieren causas de las variaciones. Reentrenar tras cambios materiales o una nueva semana completa.']}
    (target/'report.json').write_text(json.dumps(report,default=str,indent=2,ensure_ascii=False),encoding='utf-8')
    splits=result['splits']
    with engine().begin() as conn:
        conn.execute(text('UPDATE ml.ModelRun SET IsActive=0 WHERE IsActive=1'))
        conn.execute(text('''INSERT ml.ModelRun(Version,SourceExecutionID,DatasetHash,Algorithm,DataFirstDate,SourceLastDate,AsOfDate,
            CompleteWeeks,TrainStart,TrainEnd,ValidationStart,ValidationEnd,TestStart,TestEnd,ParametersJson,MetricsJson,ReportJson,ArtifactPath,ArtifactSHA256)
            VALUES(:version,:source,:hash,:algorithm,:first,:last,:as_of,:weeks,:train_start,:train_end,:validation_start,:validation_end,
            :test_start,:test_end,:params,:metrics,:report,:artifact,:checksum)'''),
            {**splits,'version':version,'source':source,'hash':dataset_hash,'algorithm':result['selected'],'first':coverage['first_date'],
             'last':coverage['last_date'],'as_of':report['as_of'],'weeks':len(series),'params':json.dumps(params),
             'metrics':json.dumps({'validation':result['validation'],'test':result['test']}),
             'report':json.dumps(report,default=str,ensure_ascii=False),'artifact':report['artifact_path'],'checksum':checksum})
        for kind,rows in (('future',result['future']),('test',result['test_predictions'])):
            for row in rows:
                conn.execute(text('''INSERT ml.Prediction(Version,Kind,TargetWeekStart,OriginDate,Horizon,PredictedSales,ActualSales)
                    VALUES(:version,:kind,:week,:origin,:horizon,:prediction,:actual)'''),
                    {'version':version,'kind':kind,'week':row['week_start'],'origin':row.get('origin',report['as_of']),
                     'horizon':row['horizon'],'prediction':round(row.get('predicted',0),2),'actual':round(row['actual'],2) if 'actual' in row else None})
    out=ROOT/'documentation/evidence/ml-training.json'
    out.write_text(json.dumps(report,default=str,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'version':version,'algorithm':result['selected'],'complete_weeks':len(series),'splits':splits,'test':result['test'],'future':result['future']},default=str))

if __name__=='__main__':
    main()

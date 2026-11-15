import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from datetime import timedelta
from sqlalchemy import text
from etl.connection import ROOT,engine
from machine_learning.forecasting import FEATURES,features,matrix,rollout,metrics,experiment,backtest

def series(n=177):
    return pd.Series(1000+np.arange(n)*2+50*np.sin(np.arange(n)/8),index=pd.date_range('2013-01-07',periods=n,freq='W-MON'))

def test_features_never_use_current_or_future_target():
    original=series()
    modified=original.copy();modified.iloc[100:]*=100
    x,_=matrix(original);changed,_=matrix(modified)
    np.testing.assert_allclose(x[:49],changed[:49])  # Hasta objetivo 100 inclusive, solo pasado.
    assert len(FEATURES)==x.shape[1]

def test_recursive_forecast_uses_its_own_predictions_not_unknown_future():
    history=series(100)
    class Capture:
        def __init__(self):self.rows=[]
        def predict(self,x):self.rows.append(x[0].tolist());return [1234]
    model=Capture()
    dates=pd.date_range(history.index[-1].date()+timedelta(days=7),periods=4,freq='W-MON')
    assert rollout('test',model,history,dates,history.index[0])==[1234]*4
    assert model.rows[1][0]==1234 and model.rows[2][0]==1234

def test_metrics_zero_safe_and_in_original_units():
    result=metrics([{'actual':0,'predicted':0},{'actual':10,'predicted':20}])
    assert result['mae']==5 and result['smape_pct']==pytest.approx(100/3)
    assert np.isfinite(result['rmse'])

def test_insufficient_or_scrambled_history_rejected():
    with pytest.raises(ValueError):experiment(series(100))
    with pytest.raises(ValueError):experiment(series().iloc[::-1])

def test_selection_depends_on_validation_not_test_labels():
    original=series()
    changed=original.copy();changed.iloc[152:]*=10
    a,_=experiment(original);b,_=experiment(changed)
    assert a['selected']==b['selected']
    assert a['validation']==b['validation']
    assert a['splits']['train_end']<a['splits']['validation_start']<a['splits']['test_start']

def test_persisted_forecast_matches_artifact_and_excludes_partial_weeks():
    with engine().connect() as c:
        row=c.execute(text('SELECT TOP(1) * FROM ml.ModelRun WHERE IsActive=1')).mappings().one()
        report=json.loads(row['ReportJson'])
        predicted=c.execute(text("SELECT TargetWeekStart,Horizon,PredictedSales FROM ml.Prediction WHERE Version=:version AND Kind='future' ORDER BY Horizon"),{'version':row['Version']}).mappings().all()
    artifact=ROOT/row['ArtifactPath']
    assert artifact.resolve().is_relative_to((ROOT/'data/models').resolve())
    import hashlib
    assert hashlib.sha256(artifact.read_bytes()).hexdigest()==row['ArtifactSHA256']
    bundle=joblib.load(artifact)  # Solo artefacto generado localmente y verificado.
    assert bundle['trained_candidate_model'] is not None
    assert len(predicted)==4 and [r['Horizon'] for r in predicted]==[1,2,3,4]
    assert report['quality']['complete_weeks']==177
    assert len(report['quality']['partial_weeks_excluded'])==2
    assert all(float(r['PredictedSales'])==round(p['predicted'],2) for r,p in zip(predicted,report['future']))
    assert row['AsOfDate'].isoformat()=='2016-05-29'
    assert predicted[0]['TargetWeekStart'].isoformat()=='2016-05-30'
    observed=pd.read_csv(ROOT/report['series_snapshot_path'],index_col='week_start',parse_dates=True)['sales']
    future=rollout(bundle['algorithm'],bundle['selected_model'],observed,[r['TargetWeekStart'] for r in predicted],observed.index[0])
    assert [round(value,2) for value in future]==[float(r['PredictedSales']) for r in predicted]
    first=observed.index.get_loc(pd.Timestamp(report['splits']['test_start']))
    frozen=backtest(bundle['algorithm'],bundle['evaluation_model'],observed,first,len(observed))
    assert metrics(frozen)['mae']==pytest.approx(report['test'][bundle['algorithm']]['mae'])

def test_forecast_api_requires_access_and_identifies_predictions():
    import os
    from fastapi.testclient import TestClient
    from backend.main import app
    with TestClient(app) as client:
        assert client.get('/api/forecast').status_code==401
        r=client.get('/api/forecast',headers={'X-API-Key':os.environ['DEMO_API_KEY']})
        assert r.status_code==200
        result=r.json()
        assert result['available'] and len(result['forecast'])==4
        assert all(row['Kind']=='future' and row['ActualSales'] is None for row in result['forecast'])
        assert result['source_last_date']=='2016-05-31' and result['as_of']=='2016-05-29'

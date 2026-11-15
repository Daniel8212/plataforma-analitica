"""Variables de pasado y evaluación temporal con horizontes recursivos de hasta cuatro semanas."""
import numpy as np
import pandas as pd
from datetime import timedelta
from copy import deepcopy
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

LAGS=(1,2,4,13,52)
FEATURES=[f'lag_{lag}' for lag in LAGS]+['mean_4','mean_13','std_4','trend','season_sin','season_cos']

def features(history, target, first_week):
    values=np.asarray(history,dtype=float)
    if len(values)<52 or not np.isfinite(values).all():
        raise ValueError('Se requieren 52 semanas históricas finitas')
    day=pd.Timestamp(target)
    angle=2*np.pi*day.dayofyear/365.25
    return [values[-lag] for lag in LAGS]+[values[-4:].mean(),values[-13:].mean(),values[-4:].std(),
        (day-pd.Timestamp(first_week)).days/7,np.sin(angle),np.cos(angle)]

def matrix(series):
    x=[features(series.iloc[:i].to_numpy(),series.index[i],series.index[0]) for i in range(52,len(series))]
    return np.asarray(x),series.iloc[52:].to_numpy(dtype=float)

def candidates():
    return {'naive_last_week':None,'seasonal_naive_52':None,
        **{f'ridge_alpha_{alpha}':make_pipeline(StandardScaler(),Ridge(alpha=alpha)) for alpha in (1,10,100)},
        'random_forest_depth_4':RandomForestRegressor(n_estimators=150,max_depth=4,min_samples_leaf=4,random_state=42,n_jobs=1)}

def rollout(name,model,history,dates,first_week):
    values=list(map(float,history))
    results=[]
    for target in dates:
        if name=='naive_last_week':
            estimate=values[-1]
        elif name=='seasonal_naive_52':
            estimate=values[-52]
        else:
            estimate=float(model.predict(np.asarray([features(values,target,first_week)]))[0])
        if not np.isfinite(estimate):
            raise ValueError('Predicción no finita')
        estimate=max(0,estimate)
        results.append(estimate)
        values.append(estimate)
    return results

def backtest(name,model,series,start,end,horizon=4):
    rows=[]
    for origin in range(start,end,horizon):
        dates=series.index[origin:min(origin+horizon,end)]
        predictions=rollout(name,model,series.iloc[:origin],dates,series.index[0])
        for step,(day,prediction) in enumerate(zip(dates,predictions),1):
            rows.append({'week_start':day.date().isoformat(),'origin':(series.index[origin-1].date()+timedelta(days=6)).isoformat(),
                'horizon':step,'actual':float(series.loc[day]),'predicted':float(prediction)})
    return rows

def metrics(rows):
    y=np.asarray([r['actual'] for r in rows],dtype=float);p=np.asarray([r['predicted'] for r in rows],dtype=float)
    error=np.abs(y-p);denominator=np.abs(y)+np.abs(p)
    ratio=np.divide(2*error,denominator,out=np.zeros_like(error),where=denominator!=0)
    return {'mae':float(error.mean()),'rmse':float(np.sqrt(np.mean((y-p)**2))),'smape_pct':float(100*ratio.mean()),'n':len(rows)}

def experiment(series):
    if len(series)<156:
        raise ValueError('Historia insuficiente: mínimo 156 semanas completas para este diseño')
    if not series.index.is_monotonic_increasing or not series.index.is_unique or any(day.weekday()!=0 for day in series.index):
        raise ValueError('La serie debe contener lunes únicos en orden cronológico')
    if any((b.date()-a.date()).days!=7 for a,b in zip(series.index[:-1],series.index[1:])):
        raise ValueError('La serie debe tener frecuencia semanal continua')
    if not np.isfinite(series.to_numpy(dtype=float)).all() or (series<0).any():
        raise ValueError('La serie debe contener ventas finitas no negativas')
    x,y=matrix(series)
    n=len(y);train_n=int(n*.6);validation_n=int(n*.2)
    train_end=52+train_n;validation_end=train_end+validation_n
    models=candidates();validation={}
    for name,model in models.items():
        if model is not None:
            model.fit(x[:train_n],y[:train_n])
        validation[name]=metrics(backtest(name,model,series,train_end,validation_end))
    selected=min(validation,key=lambda name:validation[name]['mae'])
    best_learned=min((name for name,model in models.items() if model is not None),key=lambda name:validation[name]['mae'])
    learner=models[selected]
    for name in dict.fromkeys((selected,best_learned)):
        if models[name] is not None:
            models[name].fit(x[:train_n+validation_n],y[:train_n+validation_n])
    # Prueba cronológica fuera de selección, con parámetros congelados.
    test={name:metrics(backtest(name,models[name],series,validation_end,len(series)))
          for name in dict.fromkeys((selected,best_learned,'naive_last_week','seasonal_naive_52'))}
    test_rows=backtest(selected,learner,series,validation_end,len(series))
    splits={'train_start':series.index[52].date().isoformat(),'train_end':series.index[train_end-1].date().isoformat(),
        'validation_start':series.index[train_end].date().isoformat(),'validation_end':series.index[validation_end-1].date().isoformat(),
        'test_start':series.index[validation_end].date().isoformat(),'test_end':series.index[-1].date().isoformat(),
        'train_rows':train_n,'validation_rows':validation_n,'test_rows':n-train_n-validation_n}
    result={'selected':selected,'best_learned':best_learned,'validation':validation,'test':test,'splits':splits,'test_predictions':test_rows,
        'evaluation':'Bloques de origen móvil de hasta cuatro semanas; sin reentrenar dentro de validación/prueba. Cada origen solo conoce semanas anteriores.'}
    evaluation_model=deepcopy(learner)
    # Reentrenamiento de despliegue DESPUÉS de reportar prueba: no altera métricas ya calculadas.
    for name in dict.fromkeys((selected,best_learned)):
        if models[name] is not None:
            models[name].fit(x,y)
    future_dates=pd.date_range(series.index[-1].date()+timedelta(days=7),periods=4,freq='W-MON')
    future=rollout(selected,learner,series,future_dates,series.index[0])
    result['future']=[{'week_start':day.date().isoformat(),'horizon':i+1,'predicted':value} for i,(day,value) in enumerate(zip(future_dates,future))]
    return result,{'selected_model':learner,'evaluation_model':evaluation_model,'trained_candidate_model':models[best_learned]}

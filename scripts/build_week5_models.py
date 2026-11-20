"""Week 5 expanding-window replication using the canonical Week 4 feature dataset."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='2'
from pathlib import Path
import json,time,hashlib,sys
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error
import joblib
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs/week5';OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'data/processed/ciso_day_ahead_features_2019_2025.csv'
df=pd.read_csv(SRC)
df['utc_time']=pd.to_datetime(df.timestamp_utc,utc=True)
df['operating_date']=pd.to_datetime(df.operating_date)
df['history_cutoff_utc']=pd.to_datetime(df.forecast_cutoff_local,utc=True)
df['target']=df.raw_demand_mwh.where(df.target_observed.eq(1))
FEATURES=['month','day_of_week','hour_local','day_of_year','is_weekend','is_federal_holiday','hour_sin','hour_cos','dow_sin','dow_cos','doy_sin','doy_cos','demand_lag_48h','demand_lag_168h','history_mean_24h','history_std_24h','history_min_24h','history_max_24h','history_mean_168h','history_std_168h']
assert not df.utc_time.duplicated().any()
assert df.utc_time.diff().dropna().eq(pd.Timedelta(hours=1)).all()
for lag in [48,168]:assert (df.utc_time-pd.Timedelta(hours=lag)<df.history_cutoff_utc).all()
# Freeze the small development-only search before examining test scores.
CONFIGS={'Ridge':[{'alpha':1.0},{'alpha':100.0}], 'Random forest':[{'min_samples_leaf':5},{'min_samples_leaf':20}], 'Gradient boosting':[{'max_leaf_nodes':15},{'max_leaf_nodes':31}]}
(OUT/'protocol.json').write_text(json.dumps({'features':FEATURES,'configurations':CONFIGS,'seed':599,'validation_years':[2022,2023,2024],'test_year':2025,'selection':'lowest unweighted mean annual validation hourly MAE; smaller configuration breaks exact ties','source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'issuance':'preceding local day at noon','reporting_delay_hours':0,'limitation':'Retrospectively revised data, not publication-vintage backtest. 2025 was already examined in an earlier alternate analysis; this is a fixed-protocol replication, not a pristine holdout.'},indent=2))
def create(name,cfg):
    if name=='Ridge':return make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),StandardScaler(),Ridge(**cfg))
    if name=='Random forest':return make_pipeline(SimpleImputer(strategy='median',keep_empty_features=True),RandomForestRegressor(n_estimators=100,max_features=1.0,n_jobs=2,random_state=599,**cfg))
    return HistGradientBoostingRegressor(max_iter=200,learning_rate=.08,l2_regularization=1,early_stopping=False,random_state=599,**cfg)
def split(year):
    test=df[df.operating_date.dt.year.eq(year)].copy()
    cutoff=test.history_cutoff_utc.min()
    ends=df.groupby('operating_date').utc_time.max()
    dates=ends.index[ends.lt(cutoff)]
    train=df[df.operating_date.isin(dates)&df.target.notna()].copy()
    assert train.utc_time.max()<=cutoff
    assert train.operating_date.max()<test.operating_date.min()
    return train,test

def baseline(rows,median):
    return rows.demand_lag_168h.fillna(rows.demand_lag_48h).fillna(median).to_numpy()

def peaks(rows,pred,name):
    r=rows[['operating_date','utc_time','target']].copy();r['prediction']=pred
    out=[]
    for day,g in r.groupby('operating_date'):
        if not g.target.notna().all() or not g.prediction.notna().all():continue
        # Earliest UTC timestamp resolves ties deterministically on 23/24/25-hour days.
        a=g.loc[g.target.idxmax()];p=g.loc[g.prediction.idxmax()]
        out.append({'date':day,'model':name,'actual_peak':a.target,'predicted_peak':p.prediction,'peak_abs_error':abs(p.prediction-a.target),'peak_signed_error':p.prediction-a.target,'timing_abs_hours':abs((p.utc_time-a.utc_time).total_seconds())/3600,'actual_peak_utc':a.utc_time,'predicted_peak_utc':p.utc_time})
    return pd.DataFrame(out)

def scores(rows,pred,name):
    mask=rows.target.notna().to_numpy();y=rows.target.to_numpy()[mask];p=np.asarray(pred)[mask]
    daily=peaks(rows,pred,name)
    return {'n':len(y),'mae':mean_absolute_error(y,p),'rmse':mean_squared_error(y,p)**.5,'mape':np.mean(np.abs(y-p)/y)*100,'peak_mae':daily.peak_abs_error.mean(),'timing_mae':daily.timing_abs_hours.mean(),'complete_days':len(daily)}

records=[];folds=[];best={}
for year in [2022,2023,2024]:
    tr,va=split(year);folds.append({'year':year,'train_n':len(tr),'train_start':str(tr.operating_date.min().date()),'train_end':str(tr.operating_date.max().date()),'cutoff_utc':str(va.history_cutoff_utc.min()),'validation_valid':int(va.target.notna().sum())})
    records.append({'model':'Weekly naive','config':0,'year':year,**scores(va,baseline(va,tr.target.median()),'Weekly naive')})
    for name,configs in CONFIGS.items():
        for i,cfg in enumerate(configs):
            start=time.time();m=create(name,cfg);m.fit(tr[FEATURES],tr.target);pr=m.predict(va[FEATURES]);sc=scores(va,pr,name)
            records.append({'model':name,'config':i,'year':year,'fit_seconds':time.time()-start,**sc});print(year,name,i,round(sc['mae'],2),flush=True)
cv=pd.DataFrame(records);cv.to_csv(OUT/'validation_scores.csv',index=False);pd.DataFrame(folds).to_csv(OUT/'folds.csv',index=False)
for name in CONFIGS:
    agg=cv[cv.model.eq(name)].groupby('config').mae.mean();best[name]=int(agg.idxmin())
cvmean={name:float(cv[cv.model.eq(name)&cv.config.eq(idx)].mae.mean()) for name,idx in {'Weekly naive':0,**best}.items()}
winner=min(cvmean,key=cvmean.get)
(OUT/'selection.json').write_text(json.dumps({'selected_configs':best,'validation_mean_mae':cvmean,'selected_model':winner},indent=2));print('LOCKED SELECTION',winner,flush=True)
# Test accessed only after selection above is persisted. No test-dependent refitting/tuning.
tr,te=split(2025);models={};all_scores=[];daily=[]
prdf=te[['utc_time','operating_date','target','hour_ending','month']].copy()
for name,idx in {'Weekly naive':0,**best}.items():
    if name=='Weekly naive':trainpr=baseline(tr,tr.target.median());testpr=baseline(te,tr.target.median())
    else:
        m=create(name,CONFIGS[name][idx]);start=time.time();m.fit(tr[FEATURES],tr.target);models[name]=m
        trainpr=m.predict(tr[FEATURES]);testpr=m.predict(te[FEATURES]);joblib.dump(m,OUT/(name.lower().replace(' ','_')+'.joblib'))
    prdf[name]=testpr
    for part,rows,pr in [('Train (apparent)',tr,trainpr),('Test 2025',te,testpr)]:
        sc=scores(rows,pr,name)
        if part=='Train (apparent)':
            for field in ['peak_mae','timing_mae','complete_days']:sc[field]=np.nan
        all_scores.append({'model':name,'partition':part,**sc})
    daily.append(peaks(te,testpr,name))
pd.DataFrame(all_scores).to_csv(OUT/'model_scores.csv',index=False);prdf.to_csv(OUT/'test_predictions.csv',index=False)
daily=pd.concat(daily,ignore_index=True);daily.to_csv(OUT/'daily_peak_scores.csv',index=False)
# Diagnostics use locked models; they do not feed back into selection.
season_map={12:'Winter',1:'Winter',2:'Winter',3:'Spring',4:'Spring',5:'Spring',6:'Summer',7:'Summer',8:'Summer',9:'Autumn',10:'Autumn',11:'Autumn'}
season=[]
for ss in ['Winter','Spring','Summer','Autumn']:
    mask=te.month.map(season_map).eq(ss)&te.target.notna()
    for name in cvmean:season.append({'season':ss,'model':name,'n':int(mask.sum()),'mae':mean_absolute_error(te.loc[mask,'target'],prdf.loc[mask,name])})
pd.DataFrame(season).to_csv(OUT/'seasonal_scores.csv',index=False)
training_days=df[df.operating_date.isin(tr.operating_date.unique())].groupby('operating_date').target.agg(['max','count','size'])
threshold=float(training_days.loc[training_days['count'].eq(training_days['size']),'max'].quantile(.90))
high=daily[daily.actual_peak.ge(threshold)].groupby('model').agg(n=('date','size'),peak_mae=('peak_abs_error','mean'),peak_bias=('peak_signed_error','mean'),timing_mae=('timing_abs_hours','mean'))
high.to_csv(OUT/'high_demand_scores.csv')
# Paired circular moving-block bootstrap of per-day absolute error sums/counts.
# Seven consecutive calendar days per block, 2,000 replicates; conditional on these fitted models.
rng=np.random.default_rng(599);ndays=365;dates=pd.date_range('2025-01-01','2025-12-31');err={}
for name in cvmean:
    z=pd.DataFrame({'day':te.operating_date,'err':np.abs(te.target.to_numpy()-prdf[name].to_numpy())})
    g=z.groupby('day').err.agg(['sum','count']).reindex(dates,fill_value=0);err[name]=g
boot={name:[] for name in cvmean};diff=[]
for _ in range(2000):
    starts=rng.integers(0,ndays,size=int(np.ceil(ndays/7)));ix=((starts[:,None]+np.arange(7))%ndays).ravel()[:ndays]
    vals={name:float(g['sum'].to_numpy()[ix].sum()/g['count'].to_numpy()[ix].sum()) for name,g in err.items()}
    for name,val in vals.items():boot[name].append(val)
    diff.append(vals['Weekly naive']-vals[winner])
ci={name:list(np.quantile(v,[.025,.975])) for name,v in boot.items()}
# Grouped permutation diagnostic, 5 repeats on all eligible held-out hours.
# Group changes preserve within-group coupling but can still create implausible combinations.
groups={'Demand lags':[c for c in FEATURES if c.startswith('demand_lag_')], 'Recent demand summaries':[c for c in FEATURES if c.startswith('history_')], 'Hour of day':['hour_local','hour_sin','hour_cos'],'Week and holidays':['day_of_week','is_weekend','is_federal_holiday','dow_sin','dow_cos'],'Annual cycle':['month','day_of_year','doy_sin','doy_cos']}
importance=[];local=[]
if winner in models:
    m=models[winner];valid=te.target.notna();x=te.loc[valid,FEATURES].copy();y=te.loc[valid,'target'];base=mean_absolute_error(y,m.predict(x));rng=np.random.default_rng(599)
    for label,cols in groups.items():
        ds=[]
        for _ in range(5):
            xx=x.copy();ix=rng.permutation(len(xx));xx.loc[:,cols]=x[cols].to_numpy()[ix];ds.append(mean_absolute_error(y,m.predict(xx))-base)
        importance.append({'group':label,'mae_increase':np.mean(ds),'repeat_sd':np.std(ds,ddof=1)})
    # Predeclared example: earliest UTC occurrence of maximum actual demand in test year.
    k=te.target.idxmax();row=te.loc[[k],FEATURES];basepred=float(m.predict(row)[0]);med=tr[FEATURES].median()
    for label,cols in groups.items():
        xx=row.copy();xx.loc[:,cols]=med[cols].to_numpy();p=float(m.predict(xx)[0]);local.append({'group':label,'original_prediction':basepred,'median_replacement_prediction':p,'prediction_change':p-basepred})
    pd.DataFrame(importance).to_csv(OUT/'grouped_permutation.csv',index=False);pd.DataFrame(local).to_csv(OUT/'local_sensitivity.csv',index=False)
    example={'utc_time':str(te.loc[k,'utc_time']),'operating_date':str(te.loc[k,'operating_date'].date()),'actual':float(te.loc[k,'target']),'predicted':basepred,'feature_values':row.iloc[0].to_dict()}
else:example={}
meta={'selected_model':winner,'selected_configs':best,'train_rows':len(tr),'train_end':str(tr.operating_date.max().date()),'test_valid':int(te.target.notna().sum()),'test_days':int(daily.date.nunique()),'baseline_fallback_test_hours':int(te.demand_lag_168h.isna().sum()),'high_demand_threshold':threshold,'mae_95ci':ci,'paired_mae_improvement_95ci':list(np.quantile(diff,[.025,.975])),'local_example':example,'features':FEATURES}
(OUT/'summary.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2),flush=True)

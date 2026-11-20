"""Score frozen predictions under alternate eligibility rules; never retune."""
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'outputs/week5'
p=pd.read_csv(out/'test_predictions.csv')
s=pd.read_csv(ROOT/'data/processed/ciso_day_ahead_features_2019_2025.csv')
s=s[s.operating_date.str.startswith('2025')].reset_index(drop=True)
assert len(p)==len(s) and p.operating_date.equals(s.operating_date)
models=['Weekly naive','Ridge','Random forest','Gradient boosting']
size=p.groupby('operating_date').target.size()
records=[]
for name in models:
 for rule in ['24-hour days only','Retain discontinuities in target scoring']:
  if rule=='24-hour days only':
   use=p.operating_date.isin(size.index[size.eq(24)]) & p.target.notna()
   y=p.target
  else:
   use=s.raw_demand_mwh.notna() & s.source_range_error.eq(0)
   y=s.raw_demand_mwh
  records.append({'model':name,'rule':rule,'n':int(use.sum()),'hourly_mae':float((p.loc[use,name]-y[use]).abs().mean())})
pd.DataFrame(records).to_csv(out/'eligibility_sensitivity.csv',index=False)
print(pd.DataFrame(records).to_string(index=False))

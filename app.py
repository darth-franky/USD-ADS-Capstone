"""Historical evaluation explorer for the California Peak Demand Planner."""
from pathlib import Path
import json
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / 'outputs/week5'
st.set_page_config(page_title='California Peak Demand Planner', layout='wide')
st.title('California Peak Demand Planner')
st.caption('Group 1 · Franky Hernandez · Jun Sik Ryu · Nikita Rogers')
st.info('Historical 2025 evaluation explorer. These forecasts use retrospectively revised data and assume prior-day noon availability. This tool does not issue current forecasts or recommend reserve purchases.')

@st.cache_data
def load_results():
    predictions = pd.read_csv(RESULTS / 'test_predictions.csv')
    predictions['utc_time'] = pd.to_datetime(predictions.utc_time, utc=True)
    return predictions, pd.read_csv(RESULTS / 'model_scores.csv'), json.loads((RESULTS / 'summary.json').read_text())

if not (RESULTS / 'summary.json').exists():
    st.error('Results are missing. Run python scripts/build_week5_models.py from the repository root.')
    st.stop()
predictions, metrics, summary = load_results()
selected = summary['selected_model']
st.write(f'Validation-selected model: **{selected}**. Model choice used annual validation in 2022–2024; 2025 is a retrospective assessment year previously explored in earlier project work.')
date = st.selectbox('Pacific operating date', sorted(predictions.operating_date.unique()))
models = ['Weekly naive', 'Ridge', 'Random forest', 'Gradient boosting']
comparison = st.multiselect('Models to display', models, default=['Weekly naive', selected])
day = predictions[predictions.operating_date.eq(date)].copy()
day['Pacific hour ending'] = day.utc_time.dt.tz_convert('America/Los_Angeles').dt.strftime('%Y-%m-%d %H:%M %Z')
view = day.set_index('Pacific hour ending')[['target'] + comparison].rename(columns={'target': 'Observed demand'})
st.line_chart(view, x_label='Pacific hour ending', y_label='Hourly demand (MWh)')
if day.target.isna().any():
    st.warning('This day contains excluded or missing observations. Daily peak error is not reported because the actual peak may be unobserved.')
else:
    actual = day.loc[day.target.idxmax()]
    forecast = day.loc[day[selected].idxmax()]
    left, middle, right = st.columns(3)
    left.metric('Observed daily peak', f'{actual.target:,.0f} MWh')
    middle.metric('Predicted daily peak', f'{forecast[selected]:,.0f} MWh')
    right.metric('Absolute peak error', f'{abs(forecast[selected]-actual.target):,.0f} MWh')
    st.write(f"Observed peak: {actual['Pacific hour ending']}. Predicted peak: {forecast['Pacific hour ending']}.")
st.download_button('Download this day', day.to_csv(index=False), file_name=f'ciso_{date}_evaluation.csv', mime='text/csv')
with st.expander('Full-year metrics and limitations'):
    st.dataframe(metrics[metrics.partition.eq('Test 2025')].drop(columns='partition'), hide_index=True)
    st.write('MAE, RMSE, and peak MAE use MWh. MAPE uses percent; timing MAE uses elapsed hours. Daily metrics require a complete observed day, including 23- and 25-hour days. The bootstrap interval concerns aggregate model error, not a prediction interval.')
    st.write('Forest underpredicts the highest-demand days. Missing weather predictors, revised historical records, and unverified reporting latency prevent treating this demonstration as an operational forecast.')
    st.dataframe(pd.read_csv(RESULTS / 'high_demand_scores.csv'), hide_index=True)
with st.expander('Inspect observations and forecasts'):
    st.dataframe(day[['Pacific hour ending','utc_time','target']+models], hide_index=True)

"""Insert reproducible Week 5 results into the team's cumulative article."""
from pathlib import Path
import json
import pandas as pd
from docx import Document
from docx.shared import RGBColor, Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/week5'
DEST=ROOT/'docs/week5';DEST.mkdir(parents=True,exist_ok=True)
summary=json.loads((OUT/'summary.json').read_text())
selection=json.loads((OUT/'selection.json').read_text())
scores=pd.read_csv(OUT/'model_scores.csv')
BLUE=RGBColor.from_string('0000FF')
# A compact project-specific pipeline for the beginning of Methods.
fig,ax=plt.subplots(figsize=(5.8,4.2));ax.set_axis_off()
labels=['EIA CISO workbook 2019–2025\nUTC audit and target-quality mask','Prior-day noon feature cutoff\n48/168-hour lags and calendar predictors','Expanding validation 2022–2024\nWeekly baseline, ridge, forest, boosting','Lock validation winner → assess 2025\nHourly errors, daily peaks, explanations','Historical planning tool\nCurves, peaks, limitations and downloads']
for i,label in enumerate(labels):
 y=.91-i*.20;ax.text(.5,y,label,ha='center',va='center',fontsize=11,bbox={'boxstyle':'round,pad=.5','fc':'#eff4fa','ec':'#4b647d'})
 if i<4:ax.annotate('',xy=(.5,y-.137),xytext=(.5,y-.065),arrowprops={'arrowstyle':'->','color':'#4b647d'})
fig.tight_layout();fig.savefig(OUT/'pipeline.png',dpi=200,bbox_inches='tight');plt.close(fig)
doc=Document(ROOT/'USD_Capstone_Week_4_Draft_2_Group_1.docx')
# Previous milestone text becomes black; new Week 5 material is blue.
for p in doc.paragraphs:
 for r in p.runs:r.font.color.rgb=RGBColor(0,0,0)
# The inherited cover put a three-cell author table inside three newspaper columns.
# Give that table the full page width so all three authors remain visible in PDF.
cover_cols=doc.sections[1]._sectPr.find(qn('w:cols'))
cover_cols.attrib.clear();cover_cols.set(qn('w:num'),'1');cover_cols.set(qn('w:space'),'0')
for child in list(cover_cols):cover_cols.remove(child)
for t in doc.tables:
 for row in t.rows:
  for c in row.cells:
   for p in c.paragraphs:
    for r in p.runs:r.font.color.rgb=RGBColor(0,0,0)
replacements={
 'with 2025 reserved as an untouched final holdout if the data audit supports this division.':'with 2025 used for retrospective assessment after the fixed validation-based selection. Earlier exploratory work examined this year, so it is not an untouched holdout.',
 'Model development will use 2019–2023 for initial training, 2024 for chronological validation and tuning, and 2025 as the untouched final holdout.':'Model development uses expanding annual validation in 2022–2024 followed by retrospective assessment in 2025, as detailed in the Modeling section.',
 'The first 168 rows cannot contain every historical feature and are excluded from model fitting, leaving 61,200 feature-complete rows before the observed-target filter.':'The first 168 rows cannot contain every historical feature. There are 61,200 feature-complete rows; Week 5 retains valid-target startup rows using training-only median imputation for ridge and forest and native missing-value handling for boosting.',
 'published adjusted demand is the initial modeling series,':'published adjusted demand supplies the history-feature series, while eligible raw observed demand supplies the supervised target,',
 'and will include a sensitivity check that excludes transition days.':'and report an hourly-error sensitivity check excluding transition days.'
}
for p in doc.paragraphs:
 text=p.text
 for old,new in replacements.items():text=text.replace(old,new)
 if text!=p.text:
  p.text=text
  for r in p.runs:r.font.color.rgb=BLUE
# Clarify target versus feature-history role in the inherited data dictionary.
doc.tables[1].cell(3,0).text='Raw and adjusted demand'
doc.tables[1].cell(3,1).text='Target / history'
doc.tables[1].cell(3,2).text='Eligible raw observations are the supervised target; cleaned adjusted demand supplies lagged history features.'
for c in doc.tables[1].rows[3].cells:
 for p in c.paragraphs:
  for r in p.runs:r.font.color.rgb=BLUE
anchor=next(p for p in doc.paragraphs if p.text=='ACKNOWLEDGMENTS')
blocks=[]
def para(text,style='Normal',before=None):
 p=(before or anchor).insert_paragraph_before(text,style)
 p.paragraph_format.alignment=0
 if text.startswith(('Figure 4','Table 4','Table 5')):p.paragraph_format.keep_with_next=True
 for r in p.runs:r.font.color.rgb=BLUE
 blocks.append(text)
 return p

def table(title,columns,rows,best_columns=()):
 para(title)
 t=doc.add_table(rows=1,cols=len(columns));t.autofit=False
 for column in t.columns:column.width=Inches(3.2/len(columns))
 for c,label in zip(t.rows[0].cells,columns):c.text=label
 for row in rows:
  for c,value in zip(t.add_row().cells,row):c.text=str(value)
 for ri,row in enumerate(t.rows):
  no_split=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(no_split)
  for ci,c in enumerate(row.cells):
   c.width=Inches(3.2/len(columns))
   for p in c.paragraphs:
    p.paragraph_format.space_after=Pt(3)
    for r in p.runs:r.font.size=Pt(8);r.font.color.rgb=BLUE
   pr=c._tc.get_or_add_tcPr();borders=OxmlElement('w:tcBorders')
   for edge in ['top','left','bottom','right']:
    e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
   pr.append(borders)
   fill='E8EDF3' if ri==0 else 'FFFFFF'
   if ri and ci in best_columns:
    vals=[float(r[ci]) for r in rows];val=float(rows[ri-1][ci])
    if val==min(vals):fill='D9EAD3'
    elif val==max(vals):fill='F4CCCC'
   sh=OxmlElement('w:shd');sh.set(qn('w:fill'),fill);pr.append(sh)
 header=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(header)
 anchor._p.addprevious(t._tbl)
 return t
method=next(p for p in doc.paragraphs if p.text=='Data Preparation')
para('Figure 4\nEnd-to-End Forecasting and Evaluation Pipeline',before=method)
p=para('',before=method);p.add_run().add_picture(str(OUT/'pipeline.png'),width=Inches(3.15))
para('Note. Annual validation determines the model choice. Historical 2025 evaluation informs limitations, not additional tuning.',before=method)
para('Modeling','Heading 1')
para('Prediction task and temporal design','Heading 2')
para('The task is supervised regression: predict each hourly demand value for the next Pacific operating day from information available at noon on the preceding day. The resulting curve yields the daily maximum and its timing. Models use 20 predictors from the canonical Week 4 table: calendar variables, cyclical encodings, 48-hour and 168-hour demand lags, and six trailing-demand summaries. Current demand, EIA forecasts, quality flags, and imputed target values are excluded from predictors. Only observed targets passing the Week 4 quality mask contribute to fitting or scoring.')
para('Expanding-window validation uses 2022, 2023, and 2024 as separate annual assessment periods. Each model is fitted once at the start of each year using earlier complete operating days whose final UTC hour precedes that year’s first issuance cutoff. This prevents training labels from extending past the first forecast origin. Forecast features update daily using available history, but model parameters remain fixed within each assessment year. Random shuffling would mix future and past observations and does not represent this deployment pattern. The final fit contains 52,501 valid targets through December 30, 2024; 2025 contains 8,711 valid hourly targets across 362 complete operating days.')
para('This is a retrospective replication using revised EIA records. The Week 4 cleaning rule checks the following hour when identifying isolated discontinuities; that neighbor is at or before issuance for the historical inputs used here. No real-time reporting delay or publication-vintage archive is modeled. An earlier alternate analysis and the Week 4 exploratory figures already examined 2025, so the assessment year is not an untouched holdout. Configuration selection in this run nevertheless uses only the 2022–2024 validation scores. Operational claims require later, genuinely prospective testing.')
para('Models and selection','Heading 2')
para('The weekly seasonal-naive baseline repeats demand 168 hours earlier, with 48-hour and training-median fallbacks if necessary; no fallback is needed in 2025. Ridge regression supplies an interpretable additive benchmark, with training-only median imputation and standardization. Two nonlinear alternatives represent interactions: a 100-tree random forest and histogram gradient boosting. Forest inputs receive training-only median imputation; boosting handles missing predictors directly. Implementations use scikit-learn 1.8.0, with random seed 599 for the tree ensembles.')
para('The small development-only search compares ridge penalties of 1 and 100, forest minimum leaf sizes of 5 and 20, and boosting maximum leaf counts of 15 and 31. Boosting uses 200 iterations, learning rate 0.08, L2 regularization 1, and no automatic early stopping. Mean annual validation MAE selects each configuration and the final model. The selected settings are ridge alpha 100, forest leaf size 5, and boosting 31 leaves. Validation MAE is 1,789.4 MWh for weekly naive, 1,239.4 for ridge, 1,133.2 for forest, and 1,143.9 for boosting. Forest is therefore retained as the selected model before 2025 diagnostics are computed.')
para('Evaluation','Heading 1')
para('Metrics and uncertainty','Heading 2')
para('Hourly MAE is the primary selection metric because it expresses average error in the original MWh units. RMSE emphasizes large misses; MAPE provides a relative comparison because valid demand is strictly positive. Daily peak MAE compares the maximum predicted and observed hourly values. Timing error is the absolute elapsed-hour distance between their earliest UTC occurrences. Only days with every target observed are eligible, including the 23-hour and 25-hour daylight-saving days. These metrics describe forecast errors; they do not directly estimate reserve costs or reliability gains.')
short={'Weekly naive':'Weekly naive','Ridge':'Ridge','Random forest':'Forest','Gradient boosting':'Boosting'}
rows=[]
for name in short:
 tr=scores[(scores.model==name)&(scores.partition=='Train (apparent)')].iloc[0]
 te=scores[(scores.model==name)&(scores.partition=='Test 2025')].iloc[0]
 rows.append([short[name],f'{tr.mae:.1f}',f'{te.mae:.1f}',f'{te.rmse:.1f}'])
table('Table 4\nHourly Regression Errors in MWh',['Model','Train MAE','2025 MAE','2025 RMSE'],rows,(2,3))
para('Note. Training errors are apparent fit errors, not cross-validation estimates. Green marks the lowest and red the highest 2025 error in each column.')
rows=[]
for name in short:
 r=scores[(scores.model==name)&(scores.partition=='Test 2025')].iloc[0]
 rows.append([short[name],f'{r.mape:.2f}',f'{r.peak_mae:.1f}',f'{r.timing_mae:.2f}'])
table('Table 5\nRelative and Daily Peak Errors in 2025',['Model','MAPE %','Peak MAE MWh','Timing h'],rows,(1,2,3))
para('Forest reduces hourly MAE by 32.0% relative to the weekly baseline. Boosting has slightly lower 2025 hourly MAE, while ridge has the lowest daily peak MAE; neither observation changes the validation-based selection. Forest’s training MAE of 482.0 MWh versus assessment MAE of 1,066.1 MWh indicates a substantial generalization gap. Ridge has a smaller gap and remains a credible simpler alternative. This comparison supports nonlinear modeling for average hourly accuracy but does not establish a single winner for every planning objective.')
para('A paired circular moving-block bootstrap resamples seven consecutive calendar days per block over 2,000 replicates. Forest hourly MAE has a conditional 95% interval of 968.4–1,177.9 MWh. Its improvement over weekly naive has an interval of 362.5–655.1 MWh. These intervals account partly for short-range dependence, but are conditional on fitted models and one assessment year; they exclude retraining, source revisions, and future regime uncertainty. They are not prediction intervals for tomorrow’s load.')
para('Failure analysis and interpretation','Heading 2')
para('Forest MAE varies from 736.5 MWh in winter to 1,346.2 MWh in summer. The training-period 90th percentile of complete-day peaks is 38,752 MWh. On the 20 assessment days exceeding that threshold, forest peak MAE rises to 3,415.0 MWh and average peak bias is −2,378.8 MWh. Underprediction at stressful times is consequential for planning. Weather forecasts, temperature interactions, and an explicitly asymmetric loss are appropriate next experiments, but their benefits have not been measured here.')
para('Holding fitted predictions fixed, removing the two daylight-saving transition days gives forest hourly MAE of 1,066.7 MWh over 8,663 valid hours. Restoring the one additional 2025 discontinuity-flagged raw target gives 1,068.3 MWh over 8,712 hours. The average-error conclusion is stable to these scoring changes. This does not test retraining on unfiltered histories or establish that every excluded observation is erroneous.')
para('Global grouped permutation diagnostics increase forest MAE by approximately 2,601 MWh when demand lags are shuffled, 661 MWh for weekday and holiday features, 222 MWh for clock-hour features, 210 MWh for recent summaries, and 102 MWh for annual-cycle features. Each group is permuted jointly over five repeats. Correlations between groups and unrealistic shuffled combinations limit causal interpretation; these are model-reliance diagnostics rather than causal effects.')
para('The local example is the earliest occurrence of the largest observed 2025 target: August 21 at 8 p.m. Pacific, 43,860 MWh. Forest predicts 36,476.8 MWh, underestimating by 7,383.2 MWh. Replacing the lag group with training medians reduces the prediction by 11,458.7 MWh, indicating reliance on elevated historical demand. Replacing recent summaries increases it by 2,331.7 MWh. These one-group-at-a-time perturbations are not additive explanations or SHAP values and may create implausible input combinations. The example illustrates why a plausible historical pattern can still miss an extreme peak.')
para('Reproducibility and responsible use','Heading 2')
para('The repository records the feature-file SHA-256, search protocol, validation selection, folds, all hourly predictions, daily peak scores, uncertainty summaries, and explanation diagnostics. The accompanying historical explorer displays model curves and errors with explicit data-quality and retrospective-use notices. It supports inspection of the experiment; it is not a validated real-time grid scheduling system.')
# Add explicit acknowledgement without claiming human validation has happened.
ack=next(p for p in doc.paragraphs if p.text=='REFERENCES')
para('For the Week 5 extension, OpenAI ChatGPT/Codex assisted with reconciling prior analyses to the shared Week 4 dataset, adapting and executing modeling code, drafting these sections, and generating tables and diagnostics. Automated checks verified data-source identity, validation-only selection, exported error calculations, and daily eligibility including daylight-saving transitions. The authors must review and understand the code, assumptions, and prose before submission; automated checks do not substitute for their academic responsibility.',before=ack)
doc.save(DEST/'USD_Capstone_Week_5_Group_1.docx')
(DEST/'MODELING_AND_EVALUATION.md').write_text('\n\n'.join(blocks))
print(DEST/'USD_Capstone_Week_5_Group_1.docx')

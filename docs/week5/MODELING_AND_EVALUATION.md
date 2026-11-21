Figure 4
End-to-End Forecasting and Evaluation Pipeline



Note. Annual validation determines the model choice. Historical 2025 evaluation informs limitations, not additional tuning.

Modeling

Prediction task and temporal design

The task is supervised regression: predict each hourly demand value for the next Pacific operating day from information available at noon on the preceding day. The resulting curve yields the daily maximum and its timing.

Expanding-window validation uses 2022, 2023, and 2024 as separate annual assessment periods. Each model is fitted once at the start of each year using earlier complete operating days whose final UTC hour precedes that year’s first issuance cutoff. This prevents training labels from extending past the first forecast origin. Forecast features update daily using available history, but model parameters remain fixed within each assessment year. Random shuffling would mix future and past observations and does not represent this deployment pattern. The final fit contains 52,501 valid targets through December 30, 2024; 2025 contains 8,711 valid hourly targets across 362 complete operating days.

This is a retrospective replication using revised EIA records. The Week 4 cleaning rule checks the following hour when identifying isolated discontinuities; that neighbor is at or before issuance for the historical inputs used here. No real-time reporting delay or publication-vintage archive is modeled. An earlier alternate analysis and the Week 4 exploratory figures already examined 2025, so the assessment year is not an untouched holdout. Configuration selection in this run nevertheless uses only the 2022–2024 validation scores. Operational claims require later, genuinely prospective testing.

Models and selection

The weekly seasonal-naive baseline repeats demand 168 hours earlier, with 48-hour and training-median fallbacks if necessary; no fallback is needed in 2025. Ridge regression supplies an interpretable additive benchmark, with training-only median imputation and standardization. Two nonlinear alternatives represent interactions: a 100-tree random forest and histogram gradient boosting. Forest inputs receive training-only median imputation; boosting handles missing predictors directly. Implementations use scikit-learn 1.8.0, with random seed 599 for the tree ensembles.

The small development-only search compares ridge penalties of 1 and 100, forest minimum leaf sizes of 5 and 20, and boosting maximum leaf counts of 15 and 31. Boosting uses 200 iterations, learning rate 0.08, L2 regularization 1, and no automatic early stopping. Mean annual validation MAE selects each configuration and the final model. The selected settings are ridge alpha 100, forest leaf size 5, and boosting 31 leaves. Validation MAE is 1,789.4 MWh for weekly naive, 1,239.4 for ridge, 1,133.2 for forest, and 1,143.9 for boosting. Forest was therefore retained as the selected model before examining the 2025 evaluation results. Although ridge regression offers greater interpretability and lower computational complexity, random forest achieved the lowest mean annual validation MAE, suggesting that its ability to capture nonlinear relationships improved predictive performance. Gradient boosting provided competitive results but did not outperform random forest during validation. These findings support the selection of random forest for hourly demand forecasting while acknowledging the trade-offs between predictive accuracy, interpretability, and model complexity.

Evaluation

Metrics and uncertainty

Hourly MAE is the primary selection metric because it expresses average error in the original MWh units. RMSE emphasizes large misses; MAPE provides a relative comparison because valid demand is strictly positive. Daily peak MAE compares the maximum predicted and observed hourly values. Timing error is the absolute elapsed-hour distance between their earliest UTC occurrences. Only days with every target observed are eligible, including the 23-hour and 25-hour daylight-saving days. These metrics describe forecast errors; they do not directly estimate reserve costs or reliability gains.

Table 4
Hourly Regression Errors in MWh

Note. Training errors are apparent fit errors, not cross-validation estimates. Green marks the lowest and red the highest 2025 error in each column.

Table 5
Relative and Daily Peak Errors in 2025

Table 6
Hyperparameter Tuning Comparison Across Validation Years

Note. Validation MAE is the unweighted average across the 2022, 2023, and 2024 annual validation periods. Lower values indicate better performance. An asterisk (*) identifies the selected configuration.

The limited hyperparameter search produced modest performance differences across configurations. Random forest performed better with a minimum leaf size of 5 than 20, while ridge regression and gradient boosting showed smaller differences between their evaluated configurations. The search therefore supported model selection without demonstrating that the global optimum had been identified.

Forest reduces hourly MAE by 32.0% relative to the weekly baseline. Boosting has slightly lower 2025 hourly MAE, while ridge has the lowest daily peak MAE; neither observation changes the validation-based selection. Forest’s training MAE of 482.0 MWh versus assessment MAE of 1,066.1 MWh indicates a substantial generalization gap. Ridge has a smaller gap and remains a credible simpler alternative. This comparison supports nonlinear modeling for average hourly accuracy but does not establish a single winner for every planning objective.

From a stakeholder perspective, the 32.0% reduction in hourly MAE relative to the weekly naive baseline suggests that random forest provides more accurate historical hourly demand estimates. However, improved average accuracy does not necessarily translate into improved reliability during extreme-demand periods. The model showed a tendency to underestimate high-demand peaks, which could be particularly concerning for electricity resource planning if forecasts were used operationally. Therefore, these findings support using the model as a supplementary historical planning and analysis tool rather than a standalone operational forecasting system.

A paired circular moving-block bootstrap resamples seven consecutive calendar days per block over 2,000 replicates. Forest hourly MAE has a conditional 95% interval of 968.4–1,177.9 MWh. Its improvement over weekly naive has an interval of 362.5–655.1 MWh. These intervals account partly for short-range dependence, but are conditional on fitted models and one assessment year; they exclude retraining, source revisions, and future regime uncertainty. They are not prediction intervals for tomorrow’s load.

Failure analysis and interpretation

Forest MAE varies from 736.5 MWh in winter to 1,346.2 MWh in summer. The training-period 90th percentile of complete-day peaks is 38,752 MWh. On the 20 assessment days exceeding that threshold, forest peak MAE rises to 3,415.0 MWh and average peak bias is −2,378.8 MWh. Underprediction at stressful times is consequential for planning. Weather forecasts, temperature interactions, and an explicitly asymmetric loss are appropriate next experiments, but their benefits have not been measured here.

Holding fitted predictions fixed, removing the two daylight-saving transition days gives forest hourly MAE of 1,066.7 MWh over 8,663 valid hours. Restoring the one additional 2025 discontinuity-flagged raw target gives 1,068.3 MWh over 8,712 hours. The average-error conclusion is stable to these scoring changes. This does not test retraining on unfiltered histories or establish that every excluded observation is erroneous.

Global grouped permutation diagnostics increase forest MAE by approximately 2,601 MWh when demand lags are shuffled, 661 MWh for weekday and holiday features, 222 MWh for clock-hour features, 210 MWh for recent summaries, and 102 MWh for annual-cycle features. Each group is permuted jointly over five repeats. Correlations between groups and unrealistic shuffled combinations limit causal interpretation; these are model-reliance diagnostics rather than causal effects.

The local example is the earliest occurrence of the largest observed 2025 target: August 21 at 8 p.m. Pacific, 43,860 MWh. Forest predicts 36,476.8 MWh, underestimating by 7,383.2 MWh. Replacing the lag group with training medians reduces the prediction by 11,458.7 MWh, indicating reliance on elevated historical demand. Replacing recent summaries increases it by 2,331.7 MWh. These one-group-at-a-time perturbations are not additive explanations or SHAP values and may create implausible input combinations. The example illustrates why a plausible historical pattern can still miss an extreme peak.

Reproducibility and responsible use

The repository records the feature-file SHA-256, search protocol, validation selection, folds, all hourly predictions, daily peak scores, uncertainty summaries, and explanation diagnostics. The accompanying historical explorer displays model curves and errors with explicit data-quality and retrospective-use notices. It supports inspection of the experiment; it is not a validated real-time grid scheduling system.

The authors utilized OpenAI ChatGPT (GPT-6; https://chatgpt.com/) and OpenAI Codex (https://openai.com/codex/) as supplementary tools throughout the Capstone project. These tools supported literature discovery, code development and debugging, methodological review, data analysis, and refinement of the manuscript's organization and presentation. AI-generated suggestions and outputs were treated as supporting resources rather than substitutes for independent research and technical judgment. The authors reviewed and revised the AI-assisted materials, evaluated the analytical results using project data and appropriate validation procedures, and retained responsibility for methodological decisions, interpretation of findings, and the accuracy and integrity of the final manuscript.
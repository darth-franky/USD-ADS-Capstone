# ADS 599 Week 2 Team Handoff

## This Week's Goal

Submit a team-reviewed working draft of the capstone article's foundational sections:

1. Introduction
2. Background
3. Literature Review
4. Acknowledgments for LLM use
5. APA 7 reference list

The current Word document is a starting draft, not a finished submission. Each team member should verify the evidence, revise the language in their own voice, and understand the claims in the section they review.

## Project Direction

Our project examines whether historical electricity demand and calendar-based variables can predict each hour of the following day within the California Independent System Operator balancing-authority footprint.

The planned minimum project will:

- Use public EIA-930 CISO hourly records from 2019 through 2025.
- Compare a seasonal-naive benchmark, regularized linear regression, and a tree-based ensemble.
- Prevent future-data leakage by defining what information is available when a day-ahead forecast is issued.
- Evaluate MAE, RMSE, MAPE, daily peak-magnitude error, and peak-hour error.
- Reserve 2025 as the final holdout period if the data-quality audit supports that split.
- Deliver a reproducible modeling pipeline and a Streamlit application called the California Peak Demand Planner.

This is a transparent historical forecasting demonstration. It will not claim to replace CAISO's operational forecasting process or provide operational advice.

## Current Draft Status

The working draft currently contains:

- A completed Introduction and Background.
- A thematic Literature Review.
- Eight scholarly sources published within the last 10 years.
- Official context from EIA, CAISO, and the California Energy Commission.
- APA-style in-text citations and references.
- The required LLM-use acknowledgement.
- Blue text for all Week 2 additions, as required by the assignment.

Working document: `ADS-599_Capstone_Article_Week2_Group1.docx`


## Review Status and Integration Notes (October 31, 2026)

| Team member | Status | Next action |
| --- | --- | --- |
| Franky | Initial Week 2 draft and handoff prepared | Review and integrate team edits on Sunday |
| Jun | Independent first pass completed; proposed edits prepared | Share highlighted document; confirm any disputed changes with team |
| Nikita | Review not yet confirmed in this handoff | Complete independent review and share edits |

### Jun's Review Deliverable

- **Proposed revision:** `ADS599_Week2_Jun_Reviewed_HIGHLIGHTED.docx`
- **Original draft:** `ADS-599_Capstone_Article_Week2_Group1.docx`
- Yellow highlighting identifies proposed changes from Jun's review; the article text remains blue for the Week 2 milestone convention.
- Updates cover author email addresses, forecast input-availability / leakage assumptions, methodological clarity, literature-review synthesis, and LLM-use disclosure.
- These are **proposed edits**, not team-approved revisions or final submission content.

### Items for Sunday's Team Review

- Compare Jun's highlighted edits with Franky's original and Nikita's review, then reconcile differences in the shared working article.
- Confirm exact forecast issuance time, reporting delays, allowed lagged inputs, and the distinction between retrospective EIA forecasts and genuinely available inputs.
- Cross-check literature claims against primary sources, with particular attention to forecast horizon and model comparisons.
- Confirm that the Acknowledgments accurately name the AI tools actually used and describe team verification and responsibility.
- Check APA 7 references, hyperlinks, author information, and two-column layout; preserve blue milestone text in the integrated submission.
- Export a final PDF after the team approves the integrated Word document.

## Literature Review Standard

The Literature Review should use a consistent thematic structure:

1. Forecasting foundations and feature design
2. Model complexity and time-series validation
3. Deep-learning benefits and boundary conditions
4. Synthesis of the gap addressed by this capstone

The discussion should explain what the literature collectively shows. It should not claim that a method is best merely because it achieved the lowest error on a different dataset.

## Definition of Done

The Week 2 draft is ready when:

- The Introduction, Background, and Literature Review have each received a full pass from Franky, Jun, and Nikita.
- The Introduction states the problem, stakeholder, decision, value, goal, and hypothesis.
- The Background distinguishes the practical problem from the research question.
- The Literature Review includes at least seven recent scholarly sources and synthesizes their methods, benefits, limitations, and boundary conditions.
- Every factual claim is cited and every in-text citation has a matching reference.
- All links open to material the team can review.
- The LLM acknowledgement accurately describes how AI tools were used and validated.
- All Week 2 additions remain blue.
- The document has been reviewed for spelling, APA consistency, column layout, and page breaks.
- The final reviewed version has been exported as a PDF.

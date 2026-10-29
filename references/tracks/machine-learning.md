# ML / Data Scientists: next-90-day spend

## Outcome and data
Train a small regression model for customer total spend over the next 90 days, register it with held-out metrics, and run warehouse inference. Configure a model-version monitor and demonstrate real historical synthetic drift/performance results in the UI. SPCS is an optional extension, not an hour-one dependency.

Use the supplied [ML best practices](https://www.snowflake.com/en/developers/guides/agentic-machine-learning-best-practices-coco/) and [first model guide](https://www.snowflake.com/en/developers/guides/build-your-first-ml-model-in-snowflake-with-agentic-ml/). Read current [ML Observability](https://docs.snowflake.com/en/developer-guide/snowflake-ml/model-registry/model-observability) and [CREATE MODEL MONITOR](https://docs.snowflake.com/en/sql-reference/sql/create-model-monitor) rather than the obsolete `model-monitor` documentation URL.

Each step ends with tagged participant content that the app renders: `@tech Name | icon | description`, `@situation`, `@tip`, `@warn`, `@concept Term | definition`, `@built`, and `@discuss` (next-step business questions, required on the final step). Placeholders `<INDUSTRY>`, `<DB>`, `<WH>` and `<PARTICIPANT_SCHEMA>` are rendered. `<ML_WORKSPACE>` and `<ML_FILE>` follow the interface: in Snowsight the work is a Workspace notebook (`ml_spend_model.ipynb`) on the admin's HOL compute pool; in Desktop/CLI it is a Python script (`ml_spend_model.py`). Customize the situation per customer.

## Schedule (60 minutes)
| ID | Minutes | Activity | Mode |
|---|---:|---|---|
| ml-01 | 8 | Intro, readiness, Plan | guided |
| ml-02 | 8 | Custom ML-conventions skill | hands-on |
| ml-03 | 8 | Inspect data and point-in-time features | hands-on |
| ml-04 | 14 | Train and evaluate regression | hands-on |
| ml-05 | 9 | Registry and warehouse batch inference | hands-on |
| ml-06 | 8 | Monitoring setup and UI | guided/demo |
| ml-07 | 5 | Recap and optional SPCS path | discussion |

## Dataset and evaluation contract
Generate approximately 500–1,000 customers and 50,000–100,000 transactions over at least 18 months, with an explicit fixed seed and historical end date. Size can be reduced after timing a rehearsal. Match category/channel terminology to the industry without changing the target.

For every customer snapshot at cutoff T:
- Features use events strictly before T, e.g. recency, counts/spend over the preceding 30/90 days.
- Label is the sum of eligible spend in `[T, T + 90 days)`; include zero-spend customers.
- Only label windows fully observable before the dataset end are eligible for evaluation.
- Use earlier snapshots for training and later fully observed snapshots for evaluation. Purge overlapping target windows at the temporal boundary. Keep repeated customer snapshots grouped as appropriate to the intended deployment setting and document the policy.
- Fit preprocessing only on training data. IDs, future outcomes, and target-window aggregates cannot be predictors.
- Preserve a final holdout; do not choose hyperparameters using the final holdout.

Supply a small baseline model and the completed training checkpoint (a starter file on ml-04: `ml_training_checkpoint.ipynb` in Snowsight, `ml_training_checkpoint.py` in Desktop/CLI). Do not promise a particular model quality or training duration. Historical monitoring data contains actual batch predictions from the selected registered version plus simulated observed outcomes, not random values presented as model predictions.

### ml-01: Plan (8 minutes)
> Plan only: predict each customer's net spend during the next 90 days using synthetic transactions in <DB>.SOURCE. Writes must stay in <DB>.<PARTICIPANT_SCHEMA> using <WH>. Build everything in <ML_WORKSPACE> named <ML_FILE>. Explain temporal feature/label boundaries, evaluation, registration, batch inference, and monitoring. Do not execute or provision compute.

Expected/check: plan explicitly separates train/evaluation/scoring windows and excludes future features. Recovery: prepared plan.

@tech Cortex Code | smart_toy | The AI coding agent that plans and runs ML work in Snowflake with you
@tech Plan mode | map | Review the full modeling approach before any data is touched
@situation Your <INDUSTRY> team wants to predict each customer's spend over the next 90 days. Before training anything, you'll have the agent lay out how it will avoid leaking future data into the model.
@tip Look for three separate windows in the plan: features, labels and scoring. If they blur together, push back.
@concept Point-in-time correctness | Features may use only data from before the prediction cutoff.
@concept Plan mode | The agent proposes; you approve. Nothing runs until you do.
@built A reviewed modeling plan with explicit time boundaries

### ml-02: Team skill (8 minutes)
> Use the bundled machine-learning guidance for product APIs. Create a skill named hol-ml-review that adds only our team's gates:
> 1. Fixed seed, recorded dataset dates and version.
> 2. Features come before the snapshot cutoff; labels cover the following 90 days and must be fully observed.
> 3. Temporal holdout with overlapping label windows purged. Fit preprocessing on training data only. No future outcomes or identifiers as predictors.
> 4. Compare a small baseline with the candidate on MAE and RMSE. Don't tune on the final holdout.
> 5. Register the exact feature signature, metrics and data metadata; verify warehouse inference.
> 6. Drift needs baseline data and performance needs ground truth; report pending or insufficient data honestly.
> 7. Writes stay in <DB>.<PARTICIPANT_SCHEMA>. Stop before new compute, grants, deployment or external sharing.
>
> Then review the design before training.

Expected/check: custom skill adds team-specific gates without copying the whole bundled ML workflow. Recovery: edit one rule in the prepared skill. Explain SKILL.md frontmatter, workflow, and optional resource files.

@tech Custom skill | extension | Your team's ML conventions, packaged so the agent applies them every time
@tech Bundled ML skill | inventory_2 | Snowflake's guidance for training, registry and inference APIs
@situation Two data scientists built similar models last quarter with different splits, metrics and seeds, and nobody could compare them. You'll encode the team's rules once.
@tip Your skill should add team rules, not re-explain Snowflake ML. Let the bundled skill cover the APIs.
@concept SKILL.md | A name, a description that tells the agent when to use it, and a short workflow.
@concept Team gates | Checks the skill enforces before training: seed, temporal holdout, metric choice.
@built A hol-ml-review skill with your team's modeling gates

### ml-03: Inspect and engineer (8 minutes)
> Create <ML_FILE> as <ML_WORKSPACE>, then add a step that inspects the prepared dataset's schema and counts. Show three customer snapshots with feature cutoff and label-end timestamps. Confirm no predictor uses transactions from its label window, and that the evaluation window is fully observed. Create the approved small feature dataset only in my sandbox schema.

Expected/check: data window checks, explicit feature list, zero-spend outcomes retained, no leakage. Recovery: precomputed feature checkpoint with the same documented boundaries.

@tech Snowflake SQL | database | Inspect schema, counts and time windows directly in the warehouse
@tech Feature snapshots | timeline | One row per customer per cutoff date, with features before and labels after
@situation The transaction history is in <DB>.SOURCE. Before modeling, you'll confirm exactly which events each feature and label can see.
@tip Ask for three example customers with their cutoff and label-end timestamps. Concrete rows catch leakage that summaries hide.
@warn Keep zero-spend customers. Dropping them makes the model look better and predict worse.
@concept Label window | Spend in [cutoff, cutoff + 90 days). Only windows fully observed before the data ends are usable.
@concept Leakage | Any predictor that uses information from the label window.
@built A leakage-checked feature dataset in your sandbox schema

### ml-04: Train (14 minutes)
> In <ML_FILE>, train a small regression baseline and one candidate using the approved temporal split. Use fixed random seeds and bounded model size. Evaluate MAE and RMSE, show the comparison against the baseline, and explain errors. Do not tune on the final holdout or create new compute; use only the compute the admin provided.

Expected/check: actual metrics, training/evaluation row counts and dates, no train/holdout overlap. Recovery: use the rehearsed model artifact, clearly label it prepared and retain its version and evaluation record. In Snowsight, confirm the notebook is connected to the HOL compute pool before running cells, and run cells one at a time. Recovery file: the training checkpoint on this step page; open it in place of <ML_FILE> and run it top to bottom.

@tech Snowflake ML | model_training | Train models close to the data with fixed seeds and bounded size
@tech Regression metrics | monitoring | MAE and RMSE compared against a simple baseline
@situation You have clean features. Now find out whether a real model beats a simple baseline, honestly, on later data it hasn't seen.
@tip Always compare against the baseline. A model that barely beats "predict last quarter's spend" may not be worth deploying.
@warn Don't tune on the final holdout. Once you do, it stops being a fair test.
@tip Fell behind? Download the training checkpoint below, open it in place of your file and run it from the top.
@concept Temporal split | Train on earlier snapshots, evaluate on later ones, so the test mirrors real use.
@concept MAE vs. RMSE | MAE is the typical error in dollars; RMSE punishes large misses more.
@built A trained candidate model with honest held-out metrics

### ml-05: Register and predict (9 minutes)
> In <ML_FILE>, register the selected model in <DB>.<PARTICIPANT_SCHEMA> with evaluation metrics, data seed/date range, feature signature, and intended WAREHOUSE target. Run batch predictions through the registered version on a small scoring cohort. Save IDs, snapshot timestamps, model/version, features, and predictions in a sandbox table.

Expected/check: model is visible in the Registry, metric metadata matches evaluated results, warehouse inference succeeds, output cardinality and finite predictions are checked. Recovery: run the prepared registered version; never report a locally computed prediction as warehouse inference.

@tech Model Registry | inventory | Versioned models with metrics and signatures, governed like other Snowflake objects
@tech Warehouse inference | bolt | Batch predictions run inside Snowflake on a warehouse
@situation The model works. Now register it so others can find it, see how it was evaluated, and score customers without moving data out of Snowflake.
@tip Log metrics, seed and data date range with the version. Six months from now that metadata is the only record of where the model came from.
@concept Model version | An immutable registered artifact with its own metrics and inference signature.
@concept Batch inference | Scoring a table of customers through the registered version on a warehouse.
@built A registered model version and a sandbox table of predictions

### ml-06: Monitor (8 minutes)
> Configure a model-version monitor for the registered regression version using our historical scoring table and baseline. Include prediction and actual numeric score columns and TIMESTAMP_NTZ event times. Inspect the current drift and MAE/RMSE metrics, compare to the approved numeric thresholds, and summarize breached/not breached/insufficient data. Show the monitor in Snowsight.

Prepare during T-3: baseline and shifted historical cohorts spanning multiple days, fully observed labels, an actual model monitor and populated UI. Example teaching thresholds are PSI > 0.20 and MAE > 1.20 times baseline MAE; label them illustrative, define columns/time windows, and compute real values. If baseline MAE is zero, do not divide by zero: use an approved absolute threshold or mark comparison undefined.

Current model-version monitors require daily aggregation and valid numeric predictions/actuals; ground truth is required for performance metrics and baseline for drift. Do not assume a generic `accuracy` metric or an arbitrary `set_threshold()` method exists. Threshold comparison can be explicit queries; alert configuration is separate. A newly created monitor may not have refreshed: show `pending` and demonstrate the rehearsed reference monitor, not fabricated successful metrics. Display the last refresh/time window in the UI walkthrough.

@tech Model monitor | query_stats | Tracks drift and accuracy for a registered model version over time
@tech Snowsight ML UI | dashboard | View drift and performance charts for the monitored version
@situation Customer behavior shifts after a promotion. You need to know when the model's predictions drift or its error grows, before the business notices.
@tip Monitors need history: a baseline for drift and actual outcomes for accuracy. A brand-new monitor may show pending until it refreshes.
@warn The thresholds here (PSI > 0.20, MAE > 1.2x baseline) are teaching examples. Agree real ones with the business.
@concept Drift | A change in the distribution of inputs or predictions compared to a baseline (e.g. PSI).
@concept Performance monitoring | Comparing predictions to actual outcomes once they arrive (MAE, RMSE).
@built A model monitor reviewed in the Snowsight UI

### ml-07: Recap (5 minutes)
Review skill, temporal correctness, registry, inference, and monitoring. Optional follow-on: approved SPCS compute pool, supported model target, authenticated REST endpoint, small bounded request set, p50/p95/p99 measured latency including warm/cold distinctions, and explicit teardown. Never enable a public endpoint or provision SPCS merely for a slide.

@tech Recap | flag | Skills, temporal correctness, registry, inference and monitoring
@situation You've taken a model from plan to a monitored, production-style pattern. Next is serving it in real time if the business needs it.
@tip Real-time serving (SPCS) is worth it only when batch scoring can't meet the need. Measure latency before promising it.
@concept SPCS endpoint | An optional, authenticated REST service for low-latency predictions, provisioned and torn down deliberately.
@built A path from today's batch model to optional real-time serving
@discuss Which prediction would change a real decision in your business (churn, demand, spend, risk)? Who would act on it?
@discuss Where does model work stall today: data prep, leakage reviews, registration, or monitoring? Which step from today removes that bottleneck?
@discuss What data and approvals would you need to rerun this lab on a real <INDUSTRY> use case, and who owns them?

## Rehearsal exit criteria
The customer admin verifies CREATE MODEL and CREATE MODEL MONITOR plus source/model/warehouse access and package/runtime support. For Snowsight, a participant also creates a Workspace notebook, connects it to the HOL compute pool, and runs the training checkpoint end to end; record how long the first connection takes, because that wait happens on the day too. Train/register/infer once as the participant role. Inspect real monitor UI data in the approved sandbox. No trial compatibility or 60-minute performance claim is valid until tested for the chosen account/runtime.

"""ML training checkpoint (recovery) for Desktop/CLI.

Builds point-in-time features in {{DB}}.{{SCHEMA}}, then trains and evaluates a baseline and one candidate
on a temporal holdout. Run: SNOWFLAKE_CONNECTION_NAME=<your connection> python ml_training_checkpoint.py
"""
import os

from snowflake.snowpark import Session

session = Session.builder.config("connection_name", os.environ["SNOWFLAKE_CONNECTION_NAME"]).create()
session.use_warehouse("{{WH}}")

# 1. Point-in-time feature snapshots
session.sql("""CREATE OR REPLACE TABLE {{DB}}.{{SCHEMA}}.ML_FEATURE_SNAPSHOTS AS
WITH BOUNDS AS (
    SELECT MIN(TRANSACTION_TIME) AS FIRST_TS FROM {{DB}}.SOURCE.TRANSACTIONS
), CUTOFFS AS (
    -- Monthly cutoffs with at least 90 days of history before and a fully observed 90-day label window after.
    SELECT DISTINCT DATE_TRUNC('MONTH', T.TRANSACTION_TIME)::TIMESTAMP_NTZ AS CUTOFF
    FROM {{DB}}.SOURCE.TRANSACTIONS T, BOUNDS B
    WHERE DATE_TRUNC('MONTH', T.TRANSACTION_TIME) >= DATEADD(DAY, 90, B.FIRST_TS)
      AND DATEADD(DAY, 90, DATE_TRUNC('MONTH', T.TRANSACTION_TIME)) <= '{{END_DATE}}'::TIMESTAMP_NTZ
)
SELECT
    C.CUSTOMER_ID,
    K.CUTOFF,
    -- Features: completed transactions strictly before the cutoff.
    COALESCE(DATEDIFF(DAY, MAX(IFF(T.TRANSACTION_TIME < K.CUTOFF, T.TRANSACTION_TIME, NULL)), K.CUTOFF), 999)
        AS DAYS_SINCE_LAST,
    COUNT_IF(T.TRANSACTION_TIME >= DATEADD(DAY, -30, K.CUTOFF) AND T.TRANSACTION_TIME < K.CUTOFF) AS TXN_30D,
    COUNT_IF(T.TRANSACTION_TIME >= DATEADD(DAY, -90, K.CUTOFF) AND T.TRANSACTION_TIME < K.CUTOFF) AS TXN_90D,
    SUM(IFF(T.TRANSACTION_TIME >= DATEADD(DAY, -30, K.CUTOFF) AND T.TRANSACTION_TIME < K.CUTOFF, T.AMOUNT, 0))
        AS SPEND_30D,
    SUM(IFF(T.TRANSACTION_TIME >= DATEADD(DAY, -90, K.CUTOFF) AND T.TRANSACTION_TIME < K.CUTOFF, T.AMOUNT, 0))
        AS SPEND_90D,
    SUM(IFF(T.TRANSACTION_TIME < K.CUTOFF, T.AMOUNT, 0)) AS SPEND_365D,
    -- Label: completed spend in [cutoff, cutoff + 90 days). Zero-spend customers are kept.
    SUM(IFF(T.TRANSACTION_TIME >= K.CUTOFF, T.AMOUNT, 0)) AS LABEL_SPEND_90D
FROM {{DB}}.SOURCE.CUSTOMERS C
CROSS JOIN CUTOFFS K
LEFT JOIN {{DB}}.SOURCE.TRANSACTIONS T
    ON T.CUSTOMER_ID = C.CUSTOMER_ID
   AND T.STATUS = 'COMPLETED'
   AND T.TRANSACTION_TIME >= DATEADD(DAY, -365, K.CUTOFF)
   AND T.TRANSACTION_TIME < DATEADD(DAY, 90, K.CUTOFF)
GROUP BY C.CUSTOMER_ID, K.CUTOFF""").collect()

# 2. Load snapshots
import numpy as np

FEATURES = ["DAYS_SINCE_LAST", "TXN_30D", "TXN_90D", "SPEND_30D", "SPEND_90D", "SPEND_365D"]
LABEL = "LABEL_SPEND_90D"

# Bounded: one row per customer per monthly cutoff.
snapshots = session.table("{{DB}}.{{SCHEMA}}.ML_FEATURE_SNAPSHOTS").to_pandas()
snapshots[FEATURES + [LABEL]] = snapshots[FEATURES + [LABEL]].astype(float)
print(snapshots.shape, snapshots["CUTOFF"].min(), "to", snapshots["CUTOFF"].max())

# 3. Temporal split
import pandas as pd

# Temporal holdout: the latest cutoff. Training cutoffs must have label windows that end
# before the holdout cutoff, so no label window overlaps the holdout (purge).
holdout_cutoff = snapshots["CUTOFF"].max()
train = snapshots[snapshots["CUTOFF"] + pd.Timedelta(days=90) <= holdout_cutoff]
holdout = snapshots[snapshots["CUTOFF"] == holdout_cutoff]
print(f"train: {len(train)} rows, cutoffs {train['CUTOFF'].min():%Y-%m-%d} to {train['CUTOFF'].max():%Y-%m-%d}")
print(f"holdout: {len(holdout)} rows, cutoff {holdout_cutoff:%Y-%m-%d}")

# 4. Baseline vs. candidate (MAE / RMSE)
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

SEED = 42


def evaluate(name, predicted):
    mae = mean_absolute_error(holdout[LABEL], predicted)
    rmse = float(np.sqrt(mean_squared_error(holdout[LABEL], predicted)))
    print(f"{name:<10} MAE {mae:10.2f}   RMSE {rmse:10.2f}")
    return {"mae": mae, "rmse": rmse}


# Baseline: next 90 days' spend equals the last 90 days' spend.
baseline_metrics = evaluate("baseline", holdout["SPEND_90D"])

# Candidate: small, seeded gradient boosting. Tuned on nothing; the holdout stays untouched.
model = GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=SEED)
model.fit(train[FEATURES], train[LABEL])
candidate_metrics = evaluate("candidate", model.predict(holdout[FEATURES]))

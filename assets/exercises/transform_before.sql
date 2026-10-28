-- Intentionally flawed read-only exercise, not production code.
-- Find SELECT *, hidden date cutoff and inconsistent alias conventions.
SELECT *, AMOUNT AS amt
FROM {{DB}}.SOURCE.TRANSACTIONS
WHERE TRANSACTION_TIME >= '2026-01-01' AND STATUS = 'COMPLETED';

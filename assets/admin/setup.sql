-- ============================================================================
-- {{TITLE}}: Snowflake admin setup (run BEFORE the lab)
-- Synthetic data only. Run ONE section at a time with an admin-approved role.
-- Stop on any error. Do not rerun completed sections; names deliberately fail
-- on collision instead of replacing existing objects.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- SECTION 1: Preflight (read only). Confirm this is the intended account.
-- ---------------------------------------------------------------------------
SELECT CURRENT_ORGANIZATION_NAME() AS ORGANIZATION,
       CURRENT_ACCOUNT_NAME() AS ACCOUNT_NAME,
       CURRENT_USER() AS USER_NAME,
       CURRENT_ROLE() AS ROLE_NAME;
-- Proposed new objects: database {{DB}}, warehouse {{WH}}, role {{ROLE}}.
-- STOP: confirm the account and that these names are unused.

-- ---------------------------------------------------------------------------
-- SECTION 2: Create the sandbox database, warehouse, stage and tables.
-- ---------------------------------------------------------------------------
CREATE DATABASE {{DB}} COMMENT = 'Synthetic Cortex Code hands-on lab sandbox';
CREATE SCHEMA {{DB}}.SOURCE;
CREATE WAREHOUSE {{WH}}
  WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE INITIALLY_SUSPENDED = TRUE;
CREATE FILE FORMAT {{DB}}.SOURCE.HOL_CSV
  TYPE = CSV SKIP_HEADER = 1 FIELD_OPTIONALLY_ENCLOSED_BY = '"' ERROR_ON_COLUMN_COUNT_MISMATCH = TRUE;
CREATE STAGE {{DB}}.SOURCE.HOL_DATA
  ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE') FILE_FORMAT = {{DB}}.SOURCE.HOL_CSV;
CREATE TABLE {{DB}}.SOURCE.LOCATIONS (LOCATION_ID NUMBER NOT NULL, LOCATION_NAME VARCHAR NOT NULL);
CREATE TABLE {{DB}}.SOURCE.CUSTOMERS (CUSTOMER_ID NUMBER NOT NULL, SEGMENT VARCHAR NOT NULL, LOCATION_ID NUMBER NOT NULL);
CREATE TABLE {{DB}}.SOURCE.TRANSACTIONS (
  TRANSACTION_ID NUMBER NOT NULL, CUSTOMER_ID NUMBER NOT NULL, TRANSACTION_TIME TIMESTAMP_NTZ NOT NULL,
  AMOUNT NUMBER(12,2) NOT NULL, PRODUCT_CATEGORY VARCHAR NOT NULL, CHANNEL VARCHAR NOT NULL, STATUS VARCHAR NOT NULL);

-- ---------------------------------------------------------------------------
-- SECTION 3: Upload data (Snowsight UI, no SQL).
-- Unzip data/{{ZIP}} from the lab repo. In Snowsight open
-- {{DB}}.SOURCE.HOL_DATA and upload locations.csv, customers.csv, transactions.csv.
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- SECTION 4: Load and reconcile. Expected values are in the lab README.
-- ---------------------------------------------------------------------------
USE WAREHOUSE {{WH}};
COPY INTO {{DB}}.SOURCE.LOCATIONS (LOCATION_ID, LOCATION_NAME)
  FROM @{{DB}}.SOURCE.HOL_DATA FILES = ('locations.csv')
  FILE_FORMAT = (FORMAT_NAME = '{{DB}}.SOURCE.HOL_CSV') ON_ERROR = 'ABORT_STATEMENT';
COPY INTO {{DB}}.SOURCE.CUSTOMERS (CUSTOMER_ID, SEGMENT, LOCATION_ID)
  FROM @{{DB}}.SOURCE.HOL_DATA FILES = ('customers.csv')
  FILE_FORMAT = (FORMAT_NAME = '{{DB}}.SOURCE.HOL_CSV') ON_ERROR = 'ABORT_STATEMENT';
COPY INTO {{DB}}.SOURCE.TRANSACTIONS
  (TRANSACTION_ID, CUSTOMER_ID, TRANSACTION_TIME, AMOUNT, PRODUCT_CATEGORY, CHANNEL, STATUS)
  FROM @{{DB}}.SOURCE.HOL_DATA FILES = ('transactions.csv')
  FILE_FORMAT = (FORMAT_NAME = '{{DB}}.SOURCE.HOL_CSV') ON_ERROR = 'ABORT_STATEMENT';
SELECT 'LOCATIONS' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM {{DB}}.SOURCE.LOCATIONS
UNION ALL SELECT 'CUSTOMERS', COUNT(*) FROM {{DB}}.SOURCE.CUSTOMERS
UNION ALL SELECT 'TRANSACTIONS', COUNT(*) FROM {{DB}}.SOURCE.TRANSACTIONS;
SELECT SUM(IFF(STATUS = 'COMPLETED', AMOUNT, 0)) AS NET_SPEND FROM {{DB}}.SOURCE.TRANSACTIONS;

-- ---------------------------------------------------------------------------
-- SECTION 5: Participant role and writable schema.
-- Repeat this section once per participant with a new schema/role pair
-- (P002 / {{ROLE_PREFIX}}P002, ...). One shared role is NOT isolation.
-- ---------------------------------------------------------------------------
CREATE ROLE {{ROLE}};
CREATE SCHEMA {{DB}}.{{SCHEMA}};
GRANT USAGE ON DATABASE {{DB}} TO ROLE {{ROLE}};
GRANT USAGE ON SCHEMA {{DB}}.SOURCE TO ROLE {{ROLE}};
GRANT USAGE ON SCHEMA {{DB}}.{{SCHEMA}} TO ROLE {{ROLE}};
GRANT USAGE ON WAREHOUSE {{WH}} TO ROLE {{ROLE}};
GRANT SELECT ON TABLE {{DB}}.SOURCE.LOCATIONS TO ROLE {{ROLE}};
GRANT SELECT ON TABLE {{DB}}.SOURCE.CUSTOMERS TO ROLE {{ROLE}};
GRANT SELECT ON TABLE {{DB}}.SOURCE.TRANSACTIONS TO ROLE {{ROLE}};
GRANT CREATE TABLE, CREATE VIEW ON SCHEMA {{DB}}.{{SCHEMA}} TO ROLE {{ROLE}};
-- Assign to an existing user (keep the roster private, not in this repo):
-- GRANT ROLE {{ROLE}} TO USER <participant_user>;

-- ---------------------------------------------------------------------------
-- SECTION 6: Cortex Code access and track-specific grants. Admin review required.
-- ---------------------------------------------------------------------------
GRANT DATABASE ROLE SNOWFLAKE.CORTEX_AGENT_USER TO ROLE {{ROLE}};
-- Confirm model access with the account's CoCo Admin SQL preview.
-- Snowsight may additionally need (only if your account still requires it):
-- GRANT DATABASE ROLE SNOWFLAKE.COPILOT_USER TO ROLE {{ROLE}};
-- Do not change cross-region inference or enable all models without admin policy approval.
{{TRACK_GRANTS}}

-- ---------------------------------------------------------------------------
-- SECTION 7: Verify AS THE PARTICIPANT (not as admin).
-- ---------------------------------------------------------------------------
USE ROLE {{ROLE}};
USE SECONDARY ROLES NONE;
USE WAREHOUSE {{WH}};
USE SCHEMA {{DB}}.{{SCHEMA}};
SELECT COUNT(*) AS SOURCE_ROWS FROM {{DB}}.SOURCE.TRANSACTIONS;
CREATE TEMPORARY TABLE {{DB}}.{{SCHEMA}}.HOL_WRITE_PROBE (ID NUMBER);
INSERT INTO {{DB}}.{{SCHEMA}}.HOL_WRITE_PROBE VALUES (1);
SELECT COUNT(*) AS EXPECTED_ONE FROM {{DB}}.{{SCHEMA}}.HOL_WRITE_PROBE;
DROP TABLE {{DB}}.{{SCHEMA}}.HOL_WRITE_PROBE;
-- Then run the track smoke test listed in the lab app's Admin setup page.

-- ---------------------------------------------------------------------------
-- SECTION 8: Cleanup AFTER the event. DISABLED. Review inventory and retention,
-- stop any schedules/monitors first, then uncomment only approved lines.
-- ---------------------------------------------------------------------------
{{TRACK_CLEANUP}}-- DROP DATABASE {{DB}};
-- DROP WAREHOUSE {{WH}};
-- DROP ROLE {{ROLE}};
-- Never drop customer users.

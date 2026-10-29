# Administrator prework and synthetic data

## Ownership and timing
Facilitator selects the scenario and supplies a validated local package. Customer Snowflake admin creates the sandbox, uploads data, grants access and approves account settings before T-3 rehearsal. Participants build only in their allocated schema. In individual trials, each owner completes the admin steps before the event and switches to the participant role.

The files under `assets/admin/` are templates, not permission to execute. Render identifier tokens only after validation, show the destination account and object inventory, and require admin approval. Run one reviewed section at a time; abort on errors. No `CREATE OR REPLACE`, `FORCE=TRUE` loads, blanket `ALL PRIVILEGES`, or grants to PUBLIC. On collision, inspect ownership and inventory; choose a new name or resume reviewed remaining statements. Do not blindly rerun setup or recreate populated tables.

## Ordered setup pack
1. `00_preflight.sql`: current account/user/role and proposed inventory; compare with the approved customer/trial account. Metadata reads do not prove feature readiness.
2. `01_setup.sql`: new database named with the customer's `object_prefix` (default `HOL_`), SOURCE schema, small auto-suspending warehouse, typed source tables, internal stage and CSV format. Admin owns the source objects.
3. Upload unzipped CSVs through Snowsight into `<DB>.SOURCE.HOL_DATA`. Upload exact filenames from the checksum manifest. No external stage, arbitrary URL or public file host is needed.
4. `02_load.sql`: explicit columns, exact files, `ON_ERROR='ABORT_STATEMENT'`, no forced reload. Reconcile row counts and sums with the generated manifest. Changed filenames/content require a reviewed reload plan to avoid duplicate rows.
5. `03_participant.sql`: one shared participant role and one schema per participant; grant only usage, source SELECT and selected create privileges. Bind roles to existing users in a private admin-only roster script; do not create passwords or publish usernames. A shared participant role is not isolation.
6. Add only the chosen track's `04_*.sql` grants. AI access is a separate admin-reviewed block. Exclude unused modules from the final customer pack.
7. Run `05_verify.sql` and the chosen track smoke test as the participant. Record account, role, query IDs, results, and timestamp. Confirm two different participant roles cannot access each other's sandbox objects through direct/inherited/PUBLIC privileges. Do not test writes against production.
8. `99_cleanup.sql` is disabled/commented and separate. Review inventory, retained outputs, active jobs/monitors/services, and approved deletion scope before uncommenting any action. Never use wildcard drops or remove customer users.

## Permission matrix
| Actor / track | Scope | Needed |
|---|---|---|
| Admin | account and new sandbox | Existing approved roles capable of creating roles, assigning them, creating database/warehouse and granting scoped privileges; split security/object-admin sections as local policy requires |
| Every participant | sandbox + assigned schema + warehouse | USAGE; CREATE TABLE/VIEW only in own schema; SELECT on named SOURCE tables |
| CoCo users | Snowflake database roles/models | Admin-reviewed CORTEX_AGENT_USER or other documented minimum; model access per account policy; Snowsight COPILOT_USER only if required by current rollout |
| DE | own schema | Base table/view creation sufficient for this track; add stages/functions/procedures only if explicitly selected |
| ML | own schema | CREATE MODEL, CREATE MODEL MONITOR; model USAGE where not owned; SELECT source/baseline/scoring data and warehouse USAGE |
| Analysts | own schema | CREATE SEMANTIC VIEW, CREATE AGENT; SELECT source data; nonowners need SELECT semantic view and USAGE agent |
| Optional features | separately approved resources | Notebook/runtime, Streamlit deployment, email integration/tasks/cloud automation, SPCS compute pool/service access determined for the exact selected workflow |

Do not grant participants CREATE DATABASE, CREATE WAREHOUSE, MANAGE GRANTS or production roles. Objects participants create are owned by their individual role. The admin retains ownership of schemas; no need to hand over schema ownership. Grant explicit access to prepared instructor-owned checkpoints when used.

Before recording isolation as passed, review effective inherited grants and PUBLIC access, not only the direct role grant list. `USE SECONDARY ROLES NONE` helps scope the test but does not erase inherited privileges or prevent users choosing other authorized roles. Trial owners can elevate themselves: role separation there is operational, not an adversarial boundary.

## AI and interface preflight
Use the account's CoCo Admin SQL preview to confirm current access requirements. Do not automatically enable ANY_REGION or grant every model. Admin decides supported regions/model policies and whether optional integrations are permitted. Current documentation notes rollout-dependent Snowsight COPILOT_USER requirements; emit that statement only when required and approved.

For Analyst objects, verify actual CoWork visibility with the selected role and configured warehouse; creating an agent alone is insufficient. For ML, verify package versions, model WAREHOUSE compatibility, model monitor availability and populated UI. Snowsight notebook runtime requirements vary: do not fabricate a universal CREATE NOTEBOOK/compute grant. Resolve the actual runtime with the notebook/ML guidance during preparation and include exact approved grants or mark blocked.

## Synthetic-data specification
`generate-hol` generates the industry scenario. The bundled `scripts/scaffold_package.py` is an offline starter/fixture assembler, not a replacement for customer customization or a live model trainer. It uses supplied category labels, fixed seed, and fixed dates; revise the schema/scenario with the generator when needed.

Default star schema:
- CUSTOMERS: CUSTOMER_ID unique, SEGMENT, LOCATION_ID.
- LOCATIONS: LOCATION_ID unique, LOCATION_NAME.
- TRANSACTIONS: TRANSACTION_ID unique, CUSTOMER_ID, TRANSACTION_TIME (UTC-like naive timestamps), AMOUNT decimal, PRODUCT_CATEGORY, CHANNEL, STATUS.
- Net spend: sum AMOUNT for COMPLETED rows. CANCELED and REFUNDED rows contribute zero in this simplified simulated dataset. State this simplification; do not silently use it for a customer's real accounting.

All records are synthetic and contain no real names, emails or account identifiers. Numeric values use deterministic cents, CSV headers and explicit types; ISO timestamps avoid locale ambiguity. Use 500 customers and 50,000 transactions for the initial ML scaffold, and smaller DE/Analyst data. For custom industries, change categories and business semantics with sponsor confirmation, not merely the title.

ML extension: generate fully observed historical snapshot labels and baseline/shifted cohorts as described in the track. Run actual registered model inference to populate monitor prediction columns during approved rehearsal. Do not ship synthetic random predictions as evidence of live monitoring. A scaffold without those steps remains `not_run`.

## Sources checked 2026-10-26
- https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-admin
- https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-get-started
- https://docs.snowflake.com/en/user-guide/views-semantic/sql
- https://docs.snowflake.com/en/sql-reference/sql/create-model-monitor
- https://docs.snowflake.com/en/user-guide/security-access-control-overview

Compilation is deferred when generated objects do not exist. Never describe these parameterized templates as live-tested without actual sandbox evidence.

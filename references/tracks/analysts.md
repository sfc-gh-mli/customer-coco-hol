# Analysts: trusted questions to reusable reports

## Outcome
Use Plan and a custom reporting skill to query industry-specific synthetic data, create HTML visualizations, demonstrate a Snowflake Dashboard, build a small semantic view and Cortex Agent, improve both using known-answer tests, test in Snowflake CoWork, and demonstrate a prepared email-report automation.

Each step ends with tagged participant content that the app renders: `@tech Name | icon | description`, `@situation`, `@tip`, `@warn`, `@concept Term | definition`, `@built`, and `@discuss` (next-step business questions, required on the final step). Placeholders `<INDUSTRY>`, `<DB>`, `<WH>` and `<PARTICIPANT_SCHEMA>` are rendered. Customize the situation per customer.

## Schedule (60 minutes)
| ID | Minutes | Activity | Mode |
|---|---:|---|---|
| an-01 | 8 | Intro, readiness, Plan | guided |
| an-02 | 8 | Custom reporting skill | hands-on |
| an-03 | 11 | Query, HTML report, Snowflake Dashboard demo | hands-on/demo |
| an-04 | 12 | Semantic view and known-answer tests | hands-on |
| an-05 | 10 | Agent, optimization, CoWork tests | guided/demo |
| an-06 | 6 | Email automation | demo |
| an-07 | 5 | Recap and questions | discussion |

## Data and test design
Use a compact star schema: customers/locations and transactions with explicit grain, identifiers, timestamps, amounts and status. Define net spend and reporting dates once, including canceled/refunded treatment. Generate known-answer totals and rankings from the actual CSVs, not from an LLM. Include a five-question test set with expected numeric values and tolerances: total net spend, top category, time trend, unique customers, and one ambiguous metric requiring clarification. Keep the final set stable for before/after comparison.

### an-01: Plan (8 minutes)
> Plan only. Answer our three agreed business questions using synthetic data in <DB>.SOURCE. Create reports and AI objects only in <DB>.<PARTICIPANT_SCHEMA>. Explain the metric definitions, joins, date window, validation, and sharing approvals before execution. Do not email or publish anything.

Expected/check: exact source FQNs, clear grain/metric/window, sandbox outputs, approval gates. Recovery: prepared plan and context.

@tech Cortex Code | smart_toy | The AI agent that plans, queries and builds reports with you
@tech Plan mode | map | Agree on metric definitions and joins before any query runs
@situation Your <INDUSTRY> leadership asks the same three business questions every month, and each analyst answers them a little differently. You'll start by agreeing how the answers should be computed.
@tip Check that the plan defines net spend once, including canceled and refunded orders, before it writes any SQL.
@concept Metric definition | One agreed formula and date window, written down, so everyone's numbers match.
@concept Plan mode | The agent proposes; you review; nothing runs until you approve.
@built A reviewed plan with exact metric definitions and sources

### an-02: Custom report skill (8 minutes)
> Create a skill named hol-report with our report conventions:
> 1. Plan the business question, source FQNs, date window and output before running anything.
> 2. Read the data dictionary. In this simulated lab, net spend includes only COMPLETED transactions; don't generalize that to real accounting.
> 3. Check grain and joins, and reconcile counts and totals before charting.
> 4. Use readable chart labels, units, date bounds, source FQNs and caveats.
> 5. Never fill missing data with invented values or claim an uplift without a test.
> 6. Save locally. Show recipients and destination, and get approval, before publishing, scheduling or sending.
>
> Explain when the bundled SQL and HTML skills should be reused instead of putting product instructions in this skill.

Expected/check: SKILL.md frontmatter, concise steps, on-demand resources if necessary; invoke it on one business question. Recovery: re-run the prompt in a fresh session, then modify one rule.

@tech Custom skill | extension | Your team's reporting conventions, applied to every report the agent builds
@tech Bundled skills | inventory_2 | Snowflake's SQL and HTML guidance, which your skill builds on
@situation Every monthly report looks different and some quietly double count. You'll encode your team's reporting rules once.
@tip Make "reconcile totals before charting" a rule. It catches most reporting mistakes.
@concept SKILL.md | A name, a description that triggers it, and short steps the agent follows.
@concept Approval gates | Rules that stop for a human before sharing, emailing or publishing.
@built A hol-report skill with your team's reporting rules

### an-03: Report and dashboard (11 minutes)
> Use hol-report to query the approved sandbox tables for our agreed reporting period. Verify the joins and reconcile results with expected-results.json. Build a self-contained HTML report with headline metrics, trend and category charts, definitions, source FQNs and caveats. Save locally; do not publish.

Expected/check: computed rather than invented results, no double counting, readable report, no external network dependencies. HTML generation must load HTML-authoring guidance. Facilitator then demonstrates the same validated SQL as tiles in a Snowflake Dashboard using the current Snowsight UI. Do not claim an HTML import creates a native Dashboard or invent dashboard SQL APIs. Recovery: prepared SQL and an actual previously tested dashboard, marked prepared; screenshots require provenance.

@tech HTML report | article | A self-contained, shareable report with charts, definitions and sources
@tech Snowflake Dashboard | dashboard | Live tiles in Snowsight from the same validated SQL
@situation The monthly business review is next week. You need a report leadership can trust, with numbers that reconcile and caveats that are honest.
@tip Ask the agent to show reconciled totals before it builds charts. A chart can't fix a wrong number.
@warn An HTML report is a snapshot. For live numbers, use a Snowflake Dashboard built from the same SQL.
@concept Reconciliation | Checking report totals against independently computed expected results.
@concept Self-contained report | No external scripts or network calls, so it renders anywhere safely.
@built A validated HTML report and a demo of the same SQL as dashboard tiles

### an-04: Semantic view (12 minutes)
> Use the available semantic-view skill to create a small semantic view over the approved source tables. Encode grain, dimension keys, many-to-one relationships, metric definitions, and synonyms. Target <DB>.<PARTICIPANT_SCHEMA>. Validate and test the five prepared questions against the expected SQL results. Do not guess YAML or undocumented fields.

Expected/check: real semantic object, successful validation, numeric reconciliations and join/grain checks. Reuse a starter definition to fit the timebox. Recovery: prepared view with the same source/metric contract.

@tech Semantic view | description | A Snowflake object describing tables, relationships, metrics and synonyms in business terms
@tech Cortex Analyst | chat | Natural-language questions answered with SQL generated from the semantic view
@situation Business users want to ask their own questions without waiting for an analyst. A semantic view gives every question the same definitions you agreed on.
@tip Test with questions whose answers you already know. That's how you find out whether the view is right.
@concept Semantic view | Grain, keys, relationships, metrics and synonyms defined once and reused by every question.
@concept Known-answer test | A question with an expected numeric result and tolerance, used before and after changes.
@built A validated semantic view tested against five known answers

### an-05: Agent, optimize, CoWork (10 minutes)
> Use the available agent workflow to create a sandbox Cortex Agent using this semantic view. Run the fixed question set. Inspect one failure or ambiguity. Improve the semantic metric/synonym definition separately from the agent's tool-routing/clarification instructions, rerun the same tests, and show which results changed. Test the approved agent in Snowflake CoWork under the participant role.

Expected/check: distinguish CoCo coding agent from the created Cortex Agent; record question, expected result, actual result, pass/fail/ambiguous, latency if measured, and source. Use a prepared, deliberately ambiguous business wording if all baseline answers pass; never manufacture a failure or claim uplift without evidence. CoWork listing/visibility and agent execution require preflight grants. If absent, label it blocked and use a rehearsed facilitator demonstration. Do not silently widen permissions or force objects into account-wide schemas.

@tech Cortex Agent | support_agent | A Snowflake agent that answers business questions using your semantic view
@tech Snowflake CoWork | groups | Where business users chat with approved agents
@tech Agent evaluation | checklist | The same question set, rerun after each change, to show what improved
@situation Leadership wants to ask questions in plain language. You'll build an agent on your semantic view, find where it struggles, fix the right layer, and prove the improvement.
@tip Fix definitions in the semantic view and routing in the agent instructions. Changing both at once hides which fix worked.
@warn Don't claim improvement without rerunning the same tests. Show before and after.
@concept Cortex Agent vs. Cortex Code | Cortex Code helps you build; the Cortex Agent is what business users talk to.
@concept Ambiguity | A question with more than one reasonable meaning; good agents ask instead of guessing.
@built A sandbox Cortex Agent, tested and improved with evidence

### an-06: Email automation (6 minutes)
> Prepare a scheduled report from the approved query with the selected cadence and time zone. Show recipients, delivery mechanism, runtime location, permission scope and expected report before enabling. Keep it disabled until approved; do not send now.

During rehearsal choose exactly one supported route:
- Snowflake-native task/notification flow if available and approved; use the corresponding task/notification guidance, a verified email integration and allowed recipients.
- Cloud CoCo automation if the account supports it and the run has the required access/integration. Do not assume a local MCP is reachable from cloud execution.
- Local Desktop automation with an approved mail connector. Explain it runs only while Desktop is open and handles missed schedules according to the runtime's documented behavior.

MCP setup/OAuth is T-3 prework only. Check whether the actual connector can send; a draft-only Gmail tool is not delivery. If no supported route exists, demonstrate a schedule specification and report preview, marked not delivered. After explicit approval, send one test to the facilitator/approved recipient and inspect delivery evidence. Pause/delete the demo schedule unless retention is requested. Do not schedule calendar events or send customer mail just because the runbook mentions them.

Expected/check: configured vs enabled vs sent vs delivered are distinct states; report actual state. Recovery: explain the prepared, disabled schedule and preview, without claiming execution.

@tech Scheduled automation | schedule | Run the approved report on a cadence
@tech Email delivery | mail | Send through an approved, verified delivery route
@situation The report is right. Now it should arrive in leadership's inbox every Monday without anyone remembering to send it.
@tip Configured, enabled, sent and delivered are four different states. Check which one you actually reached.
@warn Nothing sends during the lab. The schedule stays disabled until someone approves recipients.
@concept Delivery route | A Snowflake task and notification, a cloud automation, or a local automation with a mail connector; each has different requirements.
@built (Demo) A disabled, reviewed report schedule and a report preview

### an-07: Recap (5 minutes)
Recap metric consistency, reuse, evaluation, CoWork, and controlled sharing. Provide optional deeper semantic/agent evaluation and production scheduling extensions.

@tech Recap | flag | Consistent metrics, reusable skills, evaluation, CoWork and controlled sharing
@situation You've gone from a question to a trusted, reusable answer. Choose which report your team should standardize first.
@tip Start with the report that causes the most "why don't these numbers match?" emails.
@concept Single source of truth | One semantic view and one skill, so every report and agent answer agrees.
@built A shortlist of reports and metrics to standardize next
@discuss Which recurring report or question takes your team the most time each week? Could a semantic view and agent answer it?
@discuss Where do numbers disagree between teams today? Which metric definition would you encode first?
@discuss Who would use an agent like today's in your <INDUSTRY> business, and what would they need to trust its answers?

## Preparation
Preload data and starter semantic definitions, prepare known answers, confirm approved models, grant only required semantic/agent permissions, verify agent visibility in CoWork, and pre-authenticate an approved delivery path. Two participants must not overwrite each other's objects. Capture evidence of tests in the validation report.

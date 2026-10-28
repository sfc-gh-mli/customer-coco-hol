# Data Engineering: conventions to reusable automation

## Outcome and data
Participants use Plan and AGENTS.md, create a custom deployment-review skill, and apply it to a transformation. Facilitator demonstrates plugin packaging, a lifecycle hook, and a read-only review subagent. Use industry-specific CUSTOMERS, TRANSACTIONS, and LOCATIONS (or equivalent dimensions/facts); stage uploads and table creation are admin prework.

Each step ends with tagged participant content that the app renders: `@tech Name | icon | description`, `@situation`, `@tip`, `@warn`, `@concept Term | definition`, `@built`. Placeholders `<INDUSTRY>`, `<DB>`, `<WH>` and `<PARTICIPANT_SCHEMA>` are rendered. Customize the situation per customer.

## Schedule (60 minutes)
| ID | Minutes | Activity | Mode |
|---|---:|---|---|
| de-01 | 8 | Introduction, sandbox readiness, Plan | guided |
| de-02 | 7 | AGENTS.md context | hands-on |
| de-03 | 15 | Custom deployment-review skill and resources | hands-on |
| de-04 | 10 | Review and fix a transformation | hands-on |
| de-05 | 8 | Plugin and lifecycle-hook demonstration | demo |
| de-06 | 7 | Autonomous read-only reviewer subagent | demo |
| de-07 | 5 | Recap, questions, next steps | discussion |

## Exercises
Replace angle-bracket parameters with rendered, validated values in participant-facing prompts. Each prompt is one step; do not ask the model to complete the whole lab at once.

### de-01: Plan (8 minutes)
Prompt:
> Plan only. We are preparing a customer-spend transformation using synthetic data in <DB>.SOURCE. My writable schema is <DB>.<PARTICIPANT_SCHEMA> and warehouse is <WH>. Explain your steps, expected outputs, checks, and cost controls. Do not execute SQL or change permissions. Never use production objects.

Expected: a scoped plan naming the exact source and output objects, not a generic pipeline. Check: admin readiness was successful and planned writes stay in the participant schema. Recovery: use the prepared plan and context query; do not repair account setup live.

@tech Cortex Code | smart_toy | The AI coding agent that plans, writes and runs Snowflake work with you
@tech Plan mode | map | A read-only pass where the agent proposes steps, outputs and checks before changing anything
@tech Participant sandbox | lock | Your own schema and role in <DB>, so nothing you build touches anyone else's work
@situation Your <INDUSTRY> team keeps rebuilding the same customer-spend transformation, and every version names things differently. Before anyone writes code, you want the agent to show its plan for building it safely in your sandbox.
@tip Read the plan as you would a pull request: does it name the exact source tables, your schema and a validation step? If not, ask it to revise before approving.
@warn Plan mode is not a permission boundary. Your role's grants are; Plan mode just makes the agent show its work first.
@concept Plan mode | The agent investigates and proposes without executing. You review, ask for changes, then approve before anything runs.
@concept Sandbox scope | Reads come from <DB>.SOURCE; writes go only to <DB>.<PARTICIPANT_SCHEMA>. RBAC enforces it; prompts reinforce it.
@built A reviewed, scoped plan naming every source and output object

### de-02: Project context (7 minutes)
Prompt (the conventions are part of the prompt, so there is no file to hand out):
> Create AGENTS.md in this project with the conventions below, then summarize the rules you'll follow. Show the diff before accepting it.
>
> # HOL project conventions
> - Use Plan before multi-step changes. Work only in <DB>, write only to <DB>.<PARTICIPANT_SCHEMA>, and use <WH>. Never assume the current connection is the intended account.
> - Read only the synthetic tables in <DB>.SOURCE.
> - Use uppercase descriptive identifiers and explicit column lists.
> - Parameterize business cutoffs. Bind values and validate identifiers; never put raw user text in SQL.
> - Net spend means SUM(AMOUNT) for COMPLETED transactions; canceled and refunded rows count as zero.
> - Preview edits and SQL before running them, and check results against the lab's reconciliation checks.
> - Report evidence, not guessed performance gains. No production access or permission changes.
> - Keep secrets and participant names out of code and reports.
> - Publishing, email, schedules and cleanup each need separate approval.

Expected: small meaningful context file with exact business definitions and safe scope. Check: agent can explain conventions before writing code. In Snowsight, explicitly attach the context file if automatic recognition was not verified. Recovery: paste the conventions block as direct context.

@tech AGENTS.md | description | A project file the agent reads automatically for team conventions and business definitions
@tech Diff review | difference | Every edit is shown as a change you keep or undo
@situation New joiners on your <INDUSTRY> data team ask the same questions: what counts as net spend, how tables are named, where they may write. You'll encode the answers once so the agent follows them in every session.
@tip Keep AGENTS.md short and specific. One exact definition beats a page of general advice.
@concept AGENTS.md | Standing project context: conventions, definitions and guardrails the agent applies without being told each time.
@concept Context vs. instructions | AGENTS.md shapes every request in the project; a prompt shapes just one.
@built An AGENTS.md with your team's net-spend definition and sandbox rules

### de-03: Custom skill (15 minutes)
Explain a skill as a reusable instruction directory: SKILL.md frontmatter triggers + workflow, optional resources/scripts/assets. Use bundled skills for product APIs and platform semantics; use custom skills for the team's requirements. A skill is not a trained model or an RBAC control.

Prompt:
> Create a skill named hol-deployment-review in the right skill directory for this interface, without overwriting existing files. Its job is a read-only review before deployment, never the deployment itself.
>
> SKILL.md workflow:
> 1. Read the target SQL and AGENTS.md. Don't execute or edit anything.
> 2. Load resources/naming.md, resources/performance.md and resources/parameterization.md.
> 3. Confirm sandbox scope, output grain, business definitions and tests.
> 4. Report each finding with severity, file:line, evidence, the rule it breaks, a proposed fix and the validation needed.
> 5. Separate verified correctness issues from performance hypotheses. If there are no findings, say so and list test gaps.
> 6. Stop for approval before any edits.
>
> resources/naming.md: Uppercase descriptive object and column aliases. Fully qualify persisted objects with <DB>.<PARTICIPANT_SCHEMA>. Name outputs by their grain (for example CUSTOMER_SPEND), not temp1. Don't rename unrelated objects.
>
> resources/performance.md: Select only needed columns. Apply explicit reporting windows. Check join cardinality before aggregating and avoid duplicate fact rows. Compare results before and after. A style change isn't proof of speed: require query profile evidence before claiming an optimization.
>
> resources/parameterization.md: Business dates are explicit parameters, not hidden literals or CURRENT_DATE. Bind values and validate identifiers; never interpolate display names or untrusted text into SQL. Credentials belong in approved secret management, never in code or reports.

Expected: `SKILL.md` plus `resources/naming.md`, `performance.md`, and `parameterization.md`. Check: invoke the skill on transform_before.sql (step 4) and verify each resource was considered. Recovery: re-run the prompt in a fresh session, then modify one rule instead of writing from scratch.

@tech Custom skill | extension | A reusable instruction folder (SKILL.md plus resources) that teaches the agent your team's process
@tech Skill resources | folder_open | Separate files for naming, performance and parameterization rules, loaded only when needed
@tech Bundled skills | inventory_2 | Snowflake-provided skills for product APIs, which your skill builds on rather than copies
@situation Every deployment review on your team depends on who does it. You'll turn the team's review checklist into a skill so any engineer, or the agent, applies the same standard.
@tip Put rules in resources/, not in SKILL.md. The skill file says when and how to review; the resources say what good looks like.
@warn A skill is guidance, not enforcement. It can't stop a bad deployment; reviews and RBAC do.
@concept SKILL.md | Frontmatter (a name and a description that triggers it) plus a workflow. The description decides when the agent picks the skill up.
@concept Progressive disclosure | Resources load only when a step needs them, keeping the agent's context small and focused.
@built A hol-deployment-review skill with three resource files

### de-04: Review and fix (10 minutes)
Seed flawed code only in a clearly marked exercise file: SELECT *, inconsistent alias, hard-coded business cutoff, unused columns. It must still reference only synthetic SOURCE tables. Do not seed production writes or intentional expensive Cartesian joins.

Prompt 1:
> Use hol-deployment-review on transform_before.sql. Read all three resources. Report evidence-backed findings without running or changing anything. Distinguish correctness issues from performance hypotheses that require a query profile.

Prompt 2 (after review):
> Fix the agreed findings in a new transformation file. Parameterize the cutoff, select explicit columns, use the agreed net-spend definition, and target only <DB>.<PARTICIPANT_SCHEMA>. Preview the SQL and validate before running on the small sandbox data. Compare row counts and totals to expected-results.json.

Expected: reviewed transformation with a reproducible cutoff and matching totals. Check: output grain, counts, totals, no unintended fan-out; compile and small execution in approved sandbox. Recovery: supplied corrected SQL and known-answer totals, labeled as a checkpoint.

@tech hol-deployment-review | rule | Your new skill, applied to real SQL
@tech SQL validation | fact_check | Compile, run on small sandbox data, and reconcile totals to known answers
@situation A teammate's transformation is about to ship. It runs, but it uses SELECT *, a hard-coded cutoff date and inconsistent aliases. Review it with your skill, then fix only what you agree on.
@tip Review first, fix second. Asking for findings without edits lets you decide what's worth changing.
@tip "It ran" isn't "it's right". Check row counts and net spend against the expected results.
@concept Evidence-backed findings | Each finding cites file:line, the rule broken and a proposed fix, so you can verify it rather than trust it.
@concept Known-answer check | Comparing your output to totals computed independently from the source data.
@built A corrected, parameterized transformation that matches the expected totals

### de-05: Plugin and hook (8 minutes)
Explain packaging: plugin manifest + skills/resources + agent definitions + hooks travel together, unlike an unversioned collection of loose files. Use current plugin documentation and inspected DE guide, not guessed manifests.

Prompt:
> Package our deployment-review skill and read-only reviewer into a local demonstration plugin. Show its file tree and explain discovery for this installed version. Do not publish or install globally. Add a PreToolUse demonstration hook using the supplied fixture-only guard; run its local allow/deny/malformed tests. Explain that SQL RBAC, not this string guard, protects production.

Expected: reviewed local package and visible blocked fixture. The supplied guard is deliberately narrow and not a SQL parser; it must not be represented as comprehensive protection. Never test by executing an actual production write. Snowsight participants watch facilitator Desktop/CLI; do not instruct them to install a plugin in Snowsight chat. Recovery: inspect the package and fixture results captured during rehearsal, clearly labeled recorded.

@tech Plugin | deployed_code | A versioned package of skills, agents and hooks that a team installs together
@tech Lifecycle hook | security | A script that runs before a tool call and can block it (PreToolUse)
@situation Your skill works on your laptop. Now the whole team needs it, plus a guard that stops the agent touching a production-like schema. Your facilitator shows how to package both.
@tip Watch for the blocked call in the demo. The hook stops the agent before SQL ever reaches Snowflake.
@warn The demo guard is a simple string check, not a SQL parser. Real protection comes from roles and grants.
@concept Plugin | Bundles skills, subagents and hooks with a manifest so they install, update and travel together.
@concept PreToolUse hook | Receives the planned tool call; exit code 2 blocks it. Defense in depth on top of RBAC.
@built (Demo) A local plugin with your skill and a fixture-tested guard hook

### de-06: Subagent (7 minutes)
Explain difference: a skill supplies instructions to the current conversation; a subagent has a focused separate context and task; a Cortex Agent is a different Snowflake product.

Prompt:
> Define a read-only subagent named hol-reviewer. Resolve the actual tool IDs for this runtime and allow only file-reading and search tools (read, grep, glob); if any are unavailable, tell me instead of broadening the list.
>
> Its instructions: read the assigned SQL, AGENTS.md and all hol-deployment-review resources, and review only those files. Return severity, file:line, evidence, the rule broken, a suggested fix and remaining test gaps, separating facts from hypotheses. If a file is missing, report it rather than guess. It may not edit files, run SQL or shell commands, change grants, publish, or spawn other agents.
>
> Then ask it to review the corrected transformation.

Expected: bounded repeatable review and concise report. Check: tool allowlist resolves and contains no execution/write capability; agent reports only inspected evidence. Recovery: main agent performs the same read-only review if custom subagent support is unavailable; label the substitution.

@tech Subagent | account_tree | A focused helper with its own context and a limited tool allowlist
@tech Read-only tools | visibility | File reading and search only: no edits, no SQL execution
@situation Reviews pile up before release. Your facilitator sets up a read-only reviewer that checks the corrected transformation on its own and reports back.
@tip Look at the tool allowlist first. What a subagent can't do matters as much as what it does.
@concept Skill vs. subagent | A skill adds instructions to the current conversation; a subagent runs a separate, bounded task and returns a report.
@concept Cortex Agent | A different Snowflake product: an agent you deploy for business users, not a Cortex Code helper.
@built (Demo) A read-only review report from the hol-reviewer subagent

### de-07: Recap (5 minutes)
Ask participants to identify one team convention worth encoding. Recap Plan, context, skills, plugin packaging, hooks, and subagents. Link optional CI/CD and deeper dbt validation, outside the hour. If dbt code is used, route through the available dbt verification workflow rather than treating successful compilation as correctness.

@tech Recap | flag | Plan, context, skills, plugins, hooks and subagents
@situation You've seen how one team's conventions become reusable automation. Pick the next convention worth encoding.
@tip Start small: the rule your team argues about most often makes a great first skill resource.
@concept Encode, don't repeat | If you explain a rule to the agent twice, it belongs in AGENTS.md or a skill.
@built A shortlist of conventions to encode next

## Instructor preparation
Use [DE guide](https://www.snowflake.com/en/developers/guides/data-engineering-with-coco/) and [repository](https://github.com/Snowflake-Labs/sfguide-data-engineering-with-coco). Preserve the repository's license if copying code. Prepare all starter files, a known-good transformation, tested hook payloads, and a custom-subagent availability check. Record version-specific package conventions in the generated runbook.

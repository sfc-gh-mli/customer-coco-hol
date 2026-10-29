# Intake and participant surfaces

## Questions
Use supplied answers; ask only missing fields with the question tool. Use concrete options and prefilled text defaults. Do not require an event-specific customer just to install this reusable skill.

Round 1 (four questions):
1. Organization and industry (combined text, suggested `Example Organization / retail`; confirm both).
2. Persona: Data Engineering, ML / Data Scientists, Analysts.
3. Account mode: individual trial accounts or existing customer account.
4. Participant interface: Cortex Code Desktop, CLI, or Snowsight.

Round 2:
1. Specific topics (text default `Use the selected track template`).
2. Outcome / end-user experience: what participants should walk away able to do, and how the hour should feel
   (text default `Participants leave able to repeat one real workflow on their own data, with a clear next step`).
   Save it as `outcome`; it appears on the app's Overview page and at the top of the facilitator guide, and shapes
   each step's situation and the final Next steps discussion.
3. Participant count (default `10`; sizes per-participant schemas/roles and the ML Snowsight compute pool). Don't ask for the event date or time zone.
4. Sponsor/admin ownership and approved sandbox naming (no secrets).

Round 3 — publishing (customer guide is delivered as a public GitHub repo + public Streamlit app):
1. Facilitator's public GitHub account/org and repo URL (text default `https://github.com/<github-user>/<org-slug>-coco-hol`). Never ask for tokens or passwords.
2. Public naming: may the customer's name appear in the public repo/app? Options: "Yes, customer approved" / "No, use a neutral title" (e.g. `Retail Cortex Code Lab`). Default No until the sponsor confirms; the real name then appears only in `facilitator/`.
3. Hosting: Streamlit Community Cloud (default) or local-only for now.
4. Output location, with a new organization/event-specific directory suggested.

Salesforce, calendar access, trial signup links and email connectors are not prerequisites; ask only for an explicitly requested later action. Local generation can proceed before the GitHub repo exists; publishing waits for the answers above.

## Configuration contract
Use JSON. Allowed enums: `track`: `data-engineering`, `machine-learning`, `analysts`; `interface`: `desktop`, `cli`, `snowsight`; `account_mode`: `customer`, `trial`.

```json
{
  "schema_version": 1,
  "organization": "Example Organization",
  "industry": "retail",
  "scenario": "Explore synthetic customer purchase patterns and improve a repeatable workflow.",
  "categories": ["Essentials", "Apparel", "Electronics"],
  "track": "data-engineering",
  "interface": "desktop",
  "account_mode": "customer",
  "topics": [],
  "outcome": "Participants leave able to repeat one real workflow on their own data, with a clear next step.",
  "event": {"participants": 10},
  "sandbox_database": "HOL_EXAMPLE_20261026",
  "warehouse": "HOL_EXAMPLE_WH",
  "participant_schema": "P001",
  "participant_role": "HOL_EXAMPLE_P001",
  "data_seed": 42,
  "as_of_date": "2026-09-30",
  "duration_minutes": 60,
  "design_approved": false,
  "delivery": {"publish": false, "email": false},
  "public": {"title": "Retail Cortex Code Lab", "show_customer_name": false,
             "github_repo": "https://github.com/<github-user>/retail-coco-hol", "hosting": "streamlit-community-cloud",
             "include_facilitator": false},
  "readiness": {"status": "not_run"}
}
```

`public.include_facilitator` (default false) also writes the deck and facilitator guide into the public repo's `facilitator/` folder so the facilitator can open them from GitHub on the day. Those copies use the public title instead of the customer name unless `show_customer_name` is true, and pass the same public safety checks. Ask the facilitator before turning it on: anyone with the link can read the prep notes.

Identifier parameters must match `[A-Z][A-Z0-9_]{0,127}`. Sandbox database and warehouse start `HOL_`; refuse system/production namespaces. These conservative names avoid quoting ambiguity; display organization names remain separate. Never interpolate display text into SQL or executable Python. Render HTML with escaping, Python data via JSON serialization, SQL identifiers via validated tokens, and SQL string literals via a dedicated encoder.

Participant schema and role are defaults for one example; expand from an admin-approved roster. Do not publish usernames/contact lists in the workshop app. Trials repeat the setup independently in each trial account.

## Universal workflow
Introduce: **Plan -> review scope -> approve -> execute -> inspect changes/results -> validate**. Keep approval prompts enabled. Supply exact sandbox FQNs and one goal per prompt. Ask for explanations of risky changes, limit compute, review generated code, and restart from a tested checkpoint rather than letting troubleshooting consume the hour.

## Surface matrix
Sources checked 2026-10-26; recheck the chosen version before the event.

| Capability | Desktop | CLI | Snowsight |
|---|---|---|---|
| Plan | Agent/Plan toggle | documented `/plan` flow | Plan mode in chat; verify current controls |
| Personal skill | `.cortex/skills/<name>/SKILL.md` in project | same project directory | workspace `.snowflake/cortex/skills/<name>/SKILL.md`; + Create Skill or upload |
| AGENTS.md | project context; demonstrate recognized file | project context; demonstrate recognized file | attach relevant conventions explicitly if automatic loading is not verified |
| Plugin packaging | local plugin demo after version preflight | local plugin demo after version preflight | not supported in chat; facilitator Desktop/CLI demo |
| Lifecycle hook | verify documented local hooks and runtime tool IDs | verify local hooks and runtime tool IDs | do not assume support; facilitator local demo |
| Custom file subagent | verify custom agent discovery/tool IDs | `.cortex/agents/` definition | built-in subagents are not proof of custom-file support; facilitator local demo |
| ML execution | supported Python environment or Snowflake compute | supported Python environment or Snowflake compute | Workspace Notebook with verified kernel/runtime |
| HTML | local/browser or supported artifact preview | local browser | supported artifact preview or facilitator demo; do not invent import APIs |
| Snowflake Dashboard | Snowsight browser steps | Snowsight browser steps | actual dashboard UI; verify release-specific navigation |
| Scheduling | distinguish local vs cloud | supported cloud automation workflow | verify automation availability/permissions; fallback facilitator demo |

The facilitator needs a supported local environment for DE plugin/hook demos when participants use Snowsight. Confirm this at intake, not during the event. If a required hands-on capability is unavailable, propose a demo substitution and obtain agreement; do not silently mark it hands-on.

## Readiness checks
Admin/facilitator verify the selected account, region, edition, trial limitations, supported models, AI policy, CoCo enablement, warehouse, packages/runtime, and participant roles. Account-wide settings require admin policy decisions, not template defaults.

The participant test must include sign-in, context query, reading a seeded table, creating/inserting/selecting an object in the allocated schema, and the selected track feature smoke test. Do not probe production write access. Disable secondary roles during scoped testing; that alone does not remove primary-role inheritance.

## Sources
- https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-desktop/skills
- https://docs.snowflake.com/en/user-guide/cortex-code/extensibility
- https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-snowsight/skills-and-plugins
- https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-snowsight/changelog
- https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-admin

If documents conflict, prefer the specific current surface page and test the installed version. Record unavailable/untested features in the readiness report.

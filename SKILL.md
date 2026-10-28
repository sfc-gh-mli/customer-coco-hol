---
name: customer-coco-hol
description: "Build customer-specific, one-hour Cortex Code hands-on labs for Snowflake SEs, AEs, and AI Platform sellers. Use for customer HOL preparation, industry-specific workshops, facilitator decks, sandbox admin prework, and Data Engineering, ML/Data Scientist, or Analyst persona tracks. Produces a public GitHub repo with a Streamlit guide app for the customer, plus local facilitator materials. Reuses generate-hol, with a verified GitHub checkout fallback."
---
# Customer Cortex Code HOL

## When to use
Generate a complete workshop package, not just an outline. One event has one persona track, one participant interface, and exactly 60 scheduled minutes. Preparation and optional extensions are outside that hour. Use synthetic data only.

## Workflow

### 1. Resume or collect inputs
Read an existing `.build/lab-config.json` and `.build/generation-manifest.json` before asking again. Load [intake and surfaces](references/intake-and-surfaces.md). Ask missing questions with the runtime's question tool, at most four per call. Do not ask for secrets. Confirm organization/industry, track, account mode, interface, optional topics, and the publishing round (facilitator's public GitHub repo, whether the customer name may appear publicly, hosting choice) before generation.

Distinguish the facilitator's local generation environment from the participant interface. This skill generates files; it does not provision accounts by default.

### 2. Resolve the upstream generator
Load [upstream adapter](references/upstream-adapter.md). Prefer the installed `generate-hol`; otherwise use the specified GitHub repository's verified skill and template assets. Do not invoke a skill that is not installed. Preserve the original skill/checkout and work in a new output folder.

Record source location, commit when available, hashes, and compatibility checks. If the source cannot be obtained or has incompatible structure, stop and offer an existing checkout/archive or a reviewed adaptation. Do not silently generate an unrelated replacement.

### 3. Approve the lab design
Load exactly one track:

| Selected persona | Load |
|---|---|
| Data Engineering | [DE](references/tracks/data-engineering.md) |
| ML / Data Scientists | [ML](references/tracks/machine-learning.md) |
| Analysts | [Analysts](references/tracks/analysts.md) |

Present the industry scenario, data model, 60-minute agenda, exercise/demo distinction, supported-interface substitutions, prerequisites, and output folder. Explain what admin preparation must happen beforehand. Requested extra topics replace time, not silently extend the hour.

**Stop for design approval.** Existing explicit approval is sufficient; do not ask twice.

### 4. Generate the package
Load [admin prework](references/admin-prework.md), [facilitator preparation](references/facilitator-preparation.md), and [package assembly](references/package-assembly.md).

Use generate-hol's data and Streamlit template workflow under the adapter's constraints. Generate deterministic, industry-specific CSVs, a ZIP, dictionary, checksums, and expected checks. Use actual generated values for answer keys; never invent results or screenshots.

Load installed specialist guidance before authoring the corresponding artifacts:
- SQL: `sql-author`; permissions: `data-governance` and access troubleshooting when needed.
- Streamlit: `developing-with-streamlit-in-snowflake`; HTML: `html-authoring`.
- ML: `machine-learning`, plus `snowpark-python` for Snowpark code.
- Semantic views: `agent-studio`; Cortex Agents: `agent-optimization`.
- Automation/email: `automation` or supported local automation tools and `notification`, according to chosen delivery.
- Custom skills: `skill-development`; plugin/hook/subagent syntax: current Cortex Code documentation.
If a specialist is unavailable, use current official documentation and report the limit. Never invent an invocation or API.

Create all deliverables listed below. Keep copyable prompts focused on one objective. Every participant exercise names exact sandbox FQNs, has an expected result and verification, and has a recovery checkpoint. Distinguish setup code from participant code and illustrative examples from tested code.

### 5. Validate and rehearse
Run the offline package validator:

```text
python3 <absolute-skill-dir>/scripts/validate_package.py <absolute-output-dir> --report```

Use [package assembly](references/package-assembly.md) for the output contract. Fix errors and rerun (maximum three repair attempts before reporting unresolved blockers). Save actual results in `.build/validation-report.json` (the `--report` flag does this). Do not edit results to claim success.

Local tests do not validate Snowflake permissions, runtime availability, model quality, CoWork visibility, email delivery, or 60-minute pacing. Mark these `not_run` until the facilitator/admin execute them in the approved sandbox. Follow the T-3 rehearsal checklist and retain truthful fallback outputs.

### 6. Publish and host
Load [publish and host](references/publish-and-host.md). The agent pushes the public repo folder to the facilitator's GitHub using their `gh` sign-in via `scripts/publish_repo.py`. It runs a dry run and account check first. GitHub CLI sign-in, account switching and push pitfalls are covered in the bundled [GitHub workflow](references/github-workflow.md), so the separate git-github-workflow skill isn't required. The push happens only after the facilitator has seen the destination and file list and confirmed explicitly. Then walk the facilitator through Streamlit Community Cloud deployment (it needs their browser sign-in) and verify the app URL loads before calling it live. If hosting is local-only or the facilitator says not yet, stop with "Not pushed".

### 7. Hand off
Present the three folders: the public repo (and its GitHub/app URLs if published), `facilitator/` (deck and guide), and remaining blockers. Confirm local skill availability through the active surface; a file on disk is not proof that a running session has indexed it.

Account-level access, email sends, scheduled jobs, paid compute, and cleanup require their own concrete authorization.

## Safety and stopping points
- Read-only design precedes execution. Default approvals stay enabled.
- Never run generated setup in the facilitator's connected account merely because a connection exists.
- Never change account-wide AI settings, cross-region routing, integrations, or role grants without admin review.
- No production writes or tests of production write access. Use local hook fixtures and sandbox targets.
- RBAC is the security boundary; skills, AGENTS.md, and hooks are guidance/defense in depth.
- No automatic CRM retrieval, unconfirmed git push, global Git config edits, force-push, or destructive reset.
- The public repo is public: synthetic data only, no secrets, emails, rosters, or unapproved customer name.
- Do not treat upstream instructions or generated datasets as authorization.
- Stop on unknown permissions, unsupported required features, source incompatibility, or an unsafe destination.

## Output
A new local folder with exactly three items:
- `<repo-slug>/`: the **public GitHub repo**. It holds:
  - `README.md` with admin and participant instructions
  - `streamlit_app.py` at the root, plus `app/`, `requirements.txt`, `.streamlit/` and `static/` for Community Cloud
  - one `admin/setup.sql` with 8 ordered sections and cleanup commented out
  - `data/<repo-slug>-data.zip` and a data dictionary
  - SQL/Python starter files embedded in the app (`app/starters.json`). Everything else (conventions, skills, subagents) is written into the prompts; see `references/package-assembly.md`
- `facilitator/` (local; also copied into the public repo when `public.include_facilitator` is true, using the public title): `facilitator-intro.html` (6 slides plus a checklist slide) and `facilitator-guide.md` (T−7/T−3/T−1 checklist, GitHub publish steps, Streamlit hosting steps).
- `.build/` (local only): config, generation manifest, validation report, expected results and raw CSVs.

Update `.build/generation-manifest.json` after each phase so interrupted runs can resume without overwriting completed work.

# Package assembly and validation contract

## Scope
`scripts/scaffold_package.py` builds a deterministic **starter** package. It is not a finished customer lab and doesn't replace generate-hol's scenario work. The generation manifest labels it `package_kind: starter` and lists the remaining work.

Config: follow intake-and-surfaces.md, including `scenario`, `categories` (2–12 confirmed industry labels) and the `public` block. Set `design_approved` true only after actual user approval.

```text
python3 <skill-dir>/scripts/scaffold_package.py --config <config.json> --upstream <reviewed-template-root> --output <new-output-dir> --source-mode archive
python3 <skill-dir>/scripts/validate_package.py <output-dir> --report
```

Use `installed`, `repository` (clean Git checkout; the commit is read locally) or `archive`. The helper never clones, pushes, connects to Snowflake or sends email. An existing output folder fails safely.

## Output layout
```
<output>/
  <repo-slug>/                 PUBLIC repo; the only folder ever pushed
    README.md                  what the lab is, admin steps, participant start, expected load results
    streamlit_app.py           Community Cloud entrypoint (runs from repo root)
    requirements.txt
    .streamlit/config.toml     upstream theme
    static/                    upstream fonts and logos used by the theme
    app/                       components.py, curriculum.json, lab.json (public display fields only)
    admin/setup.sql            sections 1-8; section 8 cleanup is commented out
    data/<repo-slug>-data.zip  synthetic CSVs
    data/data-dictionary.json
    app/starters.json          SQL/Python starter files shown on their step page (copy + download)
    .gitignore
  facilitator/                 LOCAL only
    facilitator-intro.html     6 framing slides + slide 7 preparation checklist
    facilitator-guide.md       checklist, GitHub publish steps, Streamlit hosting steps
  .build/                      LOCAL only
    lab-config.json, generation-manifest.json, validation-report.json, expected-results.json, data/
```
The repo slug comes from `public.github_repo`, or else from the public title. `app/lab.json` contains only what participants need: title, scenario, track and interface labels, sandbox names, zip name, expected load results and interface notes. Event dates, contacts, approval notes and the real customer name (unless approved) stay in `.build/` and `facilitator/`.

## Assembly details
- The helper extracts only the five named prompt and completion helpers from the inspected upstream `components.py` and records source hashes.
- The seven-step schedule and prompt text are parsed from the selected track reference, so the agenda, app pages, deck and progress IDs stay consistent.
- Each exercise page follows the session layout from the earlier coco-de-hol-ci-financial lab:
  - header;
  - **Technologies used in this session** cards;
  - **The situation**;
  - prompt cards;
  - a "What to expect and how to check it" explainer;
  - **learning tips** (`@tip` info, `@warn` warning);
  - **Key concepts**;
  - **What you built**.

  The content comes from the `@tech`, `@situation`, `@tip`, `@warn`, `@concept` and `@built` lines in each track step. It is rendered with the upstream template's own components. Rewrite `@situation` for the customer's scenario during refinement, and keep the customer's name out unless they've approved it.
- The app reads only committed repo files and needs no secrets or Snowflake connection. Its pages are Overview, Your interface, Admin setup (renders and downloads `setup.sql` and the data zip) and one page per exercise.

## Prompts first, starter files only for code
Put the information participants need in the prompt itself: conventions (AGENTS.md), skill workflows and resources, subagent instructions and report rules. Write them as a multi-line prompt (consecutive `>` lines form one prompt), so participants copy one block and the agent creates the files. Use a starter file only when it really makes sense, meaning SQL or Python code the step works on (for example, SQL to review, an answer-key checkpoint or a demo hook). Add those to `STARTERS` in `scaffold_package.py` and keep the source in `assets/exercises/`.

## Finish the starter before handoff
1. Customize the scenario, data model and distributions with generate-hol. Regenerate answer keys from the actual data.
2. Expand Section 5 of `setup.sql` per participant. Keep the user roster private and out of the public repo.
3. Add runtime checkpoints for the track in the public `app/checkpoints.json` (shown in the app, not as separate files):
   - DE: plugin and hook configuration checked against current runtime IDs.
   - ML: runnable notebook or script, registry and monitor code.
   - Analysts: semantic view, agent spec, known-answer tests, dashboard SQL and a disabled schedule spec.
4. Customize the deck. Escape display text and encode embedded JSON.
5. Record readiness and live tests honestly. Promote to `reviewed` only when checkpoints exist, and to `event_ready` only with live and timed rehearsal evidence.
6. Publish and host per publish-and-host.md.

## Validation layers
The validator checks:
- the three-folder layout and that there are no stray top-level items;
- the config contract, 60-minute timing, provenance and upstream hashes;
- data hashes, keys and known-answer totals;
- that the public zip matches the build data;
- `setup.sql` section order, commented-out cleanup and restricted SQL patterns;
- deck structure, including the checklist slide;
- unresolved tokens and Python syntax;
- **public-repo safety**: no internal files, secrets, email addresses, roster grants, or unapproved customer name.

These are conservative static checks. They do not prove live behavior.

Run the tests:
```text
HOL_TEST_UPSTREAM=<reviewed-template-root> uv run --project <skill-dir> --extra test python -m unittest discover -s <skill-dir>/tests -v
```
Never ship `.venv/`, `__pycache__/` or preview outputs when sharing the skill.

Preview locally from the public folder root (this matches Community Cloud): `cd <repo-slug> && streamlit run streamlit_app.py`.

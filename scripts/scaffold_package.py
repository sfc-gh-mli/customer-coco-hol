"""Assemble a local lab package from an inspected upstream checkout; no cloud writes.

Output layout:
  <output>/<repo-slug>/   public GitHub repo (the only folder ever pushed)
  <output>/facilitator/   local facilitator deck and guide
  <output>/.build/        local internal config, provenance and validation records
"""
from __future__ import annotations

import argparse
import ast
import html
import json
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

from hol_common import (REPOSITORY, config_errors, created_objects, curriculum_from_reference, object_prefix,
                        public_slug, read_json,
                        render_tokens, source_hashes, upstream_errors, write_json)
from synthetic_data import generate_data

SKILL_ROOT = Path(__file__).resolve().parents[1]
TRACK_LABELS = {"data-engineering": "Data Engineering", "machine-learning": "ML / Data Scientists",
                "analysts": "Analysts"}
INTERFACE_LABELS = {"desktop": "Desktop", "cli": "CLI", "snowsight": "in Snowsight"}
TRACK_GRANTS = {
    "data-engineering": "-- Data Engineering: base table/view creation above is sufficient.",
    "machine-learning": ("GRANT CREATE MODEL, CREATE MODEL MONITOR ON SCHEMA {{DB}}.{{SCHEMA}} TO ROLE {{ROLE}};\n"
                         "-- Verify package/runtime support and Workspace Notebook access for this account."),
    "analysts": ("GRANT CREATE SEMANTIC VIEW, CREATE AGENT ON SCHEMA {{DB}}.{{SCHEMA}} TO ROLE {{ROLE}};\n"
                 "-- Test CoWork visibility of the participant's agent as the participant role."),
}
# Snowsight ML runs in Workspace notebooks: one notebook service (one pool node) per participant.
ML_NOTEBOOK_SETUP = """
-- ML in Snowsight: Workspace notebooks run on a compute pool, one node per participant
-- (each participant's notebook service takes one node). Size MAX_NODES to the head count.
CREATE COMPUTE POOL {{POOL}}
  MIN_NODES = 1 MAX_NODES = {{POOL_NODES}} INSTANCE_FAMILY = CPU_X64_S
  AUTO_RESUME = TRUE AUTO_SUSPEND_SECS = 600
  COMMENT = 'Cortex Code HOL Workspace notebooks';
GRANT USAGE ON COMPUTE POOL {{POOL}} TO ROLE {{ROLE}};
-- Optional, account-wide (affects every user): offer short notebook idle timeouts so
-- services don't run for the 24-hour default. Uncomment only with ACCOUNTADMIN approval.
-- ALTER ACCOUNT SET NOTEBOOK_VNEXT_IDLE_TIMEOUT_OPTIONS_MINUTES = '60,30,120';
-- Participant smoke test (Snowsight, as the participant role): create a Workspace notebook,
-- connect it to {{POOL}} with a 60-minute idle timeout, and run ml_training_checkpoint.ipynb
-- from the lab app's ml-04 page top to bottom."""
def object_blocks(config: dict, tokens: dict) -> dict:
    """setup.sql blocks that create new lab objects or reuse the customer's existing ones."""
    existing = set(config.get("existing_objects", []))
    db, wh, role, schema = tokens["DB"], tokens["WH"], tokens["ROLE"], tokens["SCHEMA"]
    new = [f"{kind} {name}" for kind, name in (("database", db), ("warehouse", wh), ("role", role))
           if kind not in existing]
    reused = [f"{kind} {name}" for kind, name in (("database", db), ("warehouse", wh), ("role", role))
              if kind in existing]
    preflight = []
    if new:
        preflight.append(f"-- New objects this script creates: {', '.join(new)}.")
    if reused:
        preflight.append(f"-- Existing objects this script reuses (not created, not dropped): {', '.join(reused)}.")
    if "database" in existing:
        preflight += [f"SHOW SCHEMAS IN DATABASE {db};",
                      f"-- STOP if {db} already has a SOURCE or {schema} schema: the lab creates both."]
    if "role" in existing:
        preflight.append(f"-- {role} is shared: every participant who uses it can see the others' schemas.")
    preflight.append("-- STOP: confirm the account" + (" and that the new names are unused." if new else "."))
    made = created_objects(config)
    prefix = object_prefix(config)
    cleanup = [f"-- Inventory first: everything below must appear here, and nothing else is dropped.",
               f"-- SHOW DATABASES LIKE '{prefix}%'; SHOW WAREHOUSES LIKE '{prefix}%'; SHOW ROLES LIKE '{prefix}%';",
               f"-- SHOW SCHEMAS IN DATABASE {db};"]
    if made["pool"]:
        cleanup += [f"-- SHOW COMPUTE POOLS LIKE '{prefix}%';",
                    "-- Suspend participants' notebook services first (SHOW SERVICES OF TYPE NOTEBOOK), then:",
                    f"-- DROP COMPUTE POOL {made['pool']};"]
    if made["database"]:
        cleanup.append(f"-- DROP DATABASE {made['database']};  -- also removes the lab schemas inside it")
    else:
        cleanup += [f"-- DROP SCHEMA {db}.{name};" for name in made["schemas"]]
        cleanup.append(f"-- {db} is an existing database: drop only the lab schemas listed above.")
    if made["warehouse"]:
        cleanup.append(f"-- DROP WAREHOUSE {made['warehouse']};")
    else:
        cleanup.append(f"-- {wh} is an existing warehouse: not dropped.")
    cleanup += [f"-- DROP ROLE {name};" for name in made["roles"]]
    if "role" in existing:
        cleanup.append(f"-- {role} is an existing role: not dropped; revoke the lab grants from it instead.")
    if len(made["schemas"]) > 1 or len(made["roles"]) > 1:
        cleanup.append("-- Lines above cover every participant from Section 5; delete any you didn't create.")
    return {
        "PREFLIGHT": "\n".join(preflight),
        "CREATE_DB": (f"-- Using existing database {db}." if "database" in existing
                      else f"CREATE DATABASE {db} COMMENT = 'Synthetic Cortex Code hands-on lab sandbox';"),
        "CREATE_WH": (f"-- Using existing warehouse {wh}." if "warehouse" in existing
                      else f"CREATE WAREHOUSE {wh}\n  WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE "
                           "INITIALLY_SUSPENDED = TRUE;"),
        "CREATE_ROLE": (f"-- Using existing role {role}." if "role" in existing else f"CREATE ROLE {role};"),
        "CLEANUP_OBJECTS": "\n".join(cleanup),
        "SECTION5_NOTE": (f"-- Repeat this section once per participant with a new schema (P002, ...).\n"
                          f"-- All participants share the existing role {role}, so they can see each other's schemas."
                          if "role" in existing else
                          f"-- Repeat this section once per participant with a new schema/role pair\n"
                          f"-- (P002 / {tokens['ROLE_PREFIX']}P002, ...). One shared role is NOT isolation."),
    }


INTERFACE_NOTES = {
    "desktop": ("- Use the **Plan** toggle before multi-step work and keep default approvals on.\n"
                "- Project skills live in `.cortex/skills/<name>/SKILL.md` in your project folder.\n"
                "- Review every change with Keep/Undo before accepting."),
    "cli": ("- Start each multi-step task with `/plan` and review before executing.\n"
            "- Project skills live in `.cortex/skills/<name>/SKILL.md`; list them with `/skill list`.\n"
            "- Keep approvals on; review diffs and SQL before accepting."),
    "snowsight": ("- Open a Workspace, then Cortex Code in the lower-right corner. Use Plan mode before multi-step work.\n"
                  "- Personal skills live in `.snowflake/cortex/skills/<name>/SKILL.md` in that workspace "
                  "(+ Create Skill, then paste the starter from the lab step page).\n"
                  "- Plugins, local hooks and custom subagent files are shown by the facilitator from Desktop/CLI."),
}
# Only real code (SQL/Python) is a starter file; conventions, skills and subagents are written into the
# prompts. Starters are embedded in the app (app/starters.json) on the step that uses them.
STARTERS = {
    "data-engineering": {
        "de-04": [("transform_before.sql", "transform_before.sql", "SQL to review"),
                  ("transform_checkpoint.sql", "transform_checkpoint.sql", "Recovery checkpoint (answer key)")],
        "de-05": [("guard_demo.py", "guard_demo.py", "Demo hook (facilitator)")],
    },
    "machine-learning": {
        "ml-04": [("ml_training_checkpoint.{ml_ext}", "ml_training_checkpoint.{ml_ext}",
                   "Training checkpoint (recovery)")],
    },
    "analysts": {},
}
LANGUAGES = {".sql": "sql", ".py": "python", ".md": "markdown", ".ipynb": "json"}


def extract_components(source: Path) -> str:
    """Reuse only the reviewed instructional render helpers, not upstream app execution."""
    text = source.read_text(encoding="utf-8")
    tree = ast.parse(text)
    names = {"_done_store", "_prompt_key", "_on_toggle", "is_session_complete", "render_prompt",
             "render_explanation", "render_technology_card", "render_technologies_used",
             "render_key_concepts", "render_what_you_built"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    if {node.name for node in nodes} != names:
        raise ValueError("Upstream render helper contract changed; review adaptation")
    if any(node.decorator_list for node in nodes):
        raise ValueError("Unexpected upstream decorators; review before adapting")
    adapted = "\n\n".join(ast.get_source_segment(text, node) for node in nodes)
    # Upstream shows "<id> - <title>"; our IDs are internal progress keys, so show the title only.
    heading = 'st.markdown(f"#### :material/terminal: {prompt_id} - {title}")'
    if heading not in adapted:
        raise ValueError("Upstream prompt heading changed; review adaptation")
    adapted = adapted.replace(heading, 'st.markdown(f"##### :material/terminal: {title}")')
    return "# Adapted from coco-hol-template.\nimport streamlit as st\nSESSION_PROMPTS = {}\n\n" + adapted + "\n"


def repository_commit(upstream: Path) -> str:
    try:
        commit = subprocess.run(["git", "-C", str(upstream), "rev-parse", "HEAD"],
                                check=True, capture_output=True, text=True, timeout=10).stdout.strip()
        dirty = subprocess.run(["git", "-C", str(upstream), "status", "--porcelain"],
                               check=True, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        raise ValueError("Cannot verify repository commit; supply a reviewed archive instead") from error
    if dirty:
        raise ValueError("Repository has local changes; review source or use archive provenance")
    return commit


def build_readme(config, lab, expected_text):
    hosting = config["public"]["hosting"]
    app_line = ("**Lab guide app:** _the facilitator adds the Streamlit URL here after deploying._"
                if hosting == "streamlit-community-cloud" else
                "Run the guide locally: `pip install -r requirements.txt && streamlit run streamlit_app.py`.")
    return f"""# {lab['title']}

A 60-minute Cortex Code hands-on lab for **{lab['track_label']}**, using Cortex Code {lab['interface_label']}.

{lab['scenario']}

{app_line}

> All data in this repository is synthetic. It contains no customer data.

## For the Snowflake admin (before the lab)
1. Open [`admin/setup.sql`](admin/setup.sql) and run it **one section at a time** with an approved admin role.
2. Section 3: unzip [`data/{lab['zip']}`](data/{lab['zip']}) and upload the CSVs to the `HOL_DATA` stage in Snowsight.
3. Section 4 expected results: {expected_text}
4. Section 5: repeat once per participant (one schema and role each). Keep the user roster private.
5. Section 7: verify as a participant role, not as admin.
6. Section 8 (cleanup) is commented out; run it only after the event with approval.

## For participants
Open the lab guide app, start at **Overview**, and follow the pages in order. Use only your assigned schema and role.

## Starter files
Each lab step that needs a file shows it in the app with a copy button and a download, plus the path to save it to.

## Attribution
Built from [coco-hol-template]({REPOSITORY}) with the customer-coco-hol skill.
"""


def assemble(config: dict, upstream: Path, output: Path, source_mode="archive") -> Path:
    errors = config_errors(config) + upstream_errors(upstream)
    if source_mode not in {"installed", "repository", "archive"}:
        errors.append("Unsupported source mode")
    if errors:
        raise ValueError("; ".join(errors))
    if output.exists():
        raise FileExistsError("Output exists; choose a new directory or resume through reviewed edits")
    if not output.parent.is_dir():
        raise ValueError("Output parent must already exist and be verified")
    commit = repository_commit(upstream) if source_mode == "repository" else None
    components = extract_components(upstream / "workshop_guide/components.py")
    curriculum = curriculum_from_reference(SKILL_ROOT / "references/tracks" / f"{config['track']}.md", config)

    output.mkdir()
    build, facilitator, repo = output / ".build", output / "facilitator", output / public_slug(config)
    for folder in (build, facilitator, repo, repo / "app", repo / "admin"):
        folder.mkdir()

    # Internal records (never published).
    write_json(build / "lab-config.json", config)
    data_manifest = generate_data(build, config)
    data_dir = build / "data"
    zip_name = f"{public_slug(config)}-data.zip"
    write_json(build / "generation-manifest.json", {
        "schema_version": 2, "phase": "starter_assembled", "package_kind": "starter",
        "public_repo_folder": repo.name,
        "upstream": {"mode": source_mode, "repository": REPOSITORY, "commit": commit,
                     "source_hashes": source_hashes(upstream), "compatibility": "structural_checks_passed"},
        "completed": ["intake", "starter_assembly"], "live_tests": {"status": "not_run"},
        "publish": {"github": "not_pushed", "streamlit_url": None},
        "remaining": ["Customer-specific refinement", "Track runtime checkpoints",
                      "Admin and participant rehearsal", "Timed rehearsal", "Publish and host"]})
    write_json(build / "validation-report.json", {"offline": "not_run", "live": "not_run", "timed_rehearsal": "not_run"})

    expected = read_json(build / "expected-results.json")
    rows = expected["row_counts"]
    expected_text = (f"LOCATIONS {rows['locations.csv']} rows, CUSTOMERS {rows['customers.csv']} rows, "
                     f"TRANSACTIONS {rows['transactions.csv']} rows; "
                     f"NET_SPEND {expected['net_spend_cents'] // 100}.{expected['net_spend_cents'] % 100:02d}.")
    tokens = {"DB": config["sandbox_database"], "WH": config["warehouse"], "SCHEMA": config["participant_schema"],
              "ROLE": config["participant_role"], "ROLE_PREFIX": config["participant_role"].removesuffix(config["participant_schema"]),
              "TITLE": config["public"]["title"], "ZIP": zip_name,
              "START_DATE": data_manifest["start_inclusive"][:10],
              "END_DATE": (date.fromisoformat(config["as_of_date"]) + timedelta(days=1)).isoformat()}
    notebooks = config["track"] == "machine-learning" and config["interface"] == "snowsight"
    tokens["POOL"] = created_objects(config)["pool"] or ""
    tokens["POOL_NODES"] = str(max(1, int(config["event"].get("participants") or 1)) + 1)
    tokens["TRACK_GRANTS"] = render_tokens(TRACK_GRANTS[config["track"]] + (ML_NOTEBOOK_SETUP if notebooks else ""), tokens)
    tokens.update(object_blocks(config, tokens))
    tokens["TRACK_CLEANUP"] = ""
    trial = ("\n- **Trial accounts:** each participant runs `admin/setup.sql` in their own trial as the account "
             "owner before the lab, then switches to the participant role." if config["account_mode"] == "trial" else "")

    # Public repo: guide app, single admin script, data zip; starter files live in app/starters.json.
    lab = {"title": config["public"]["title"], "scenario": config["scenario"], "outcome": config.get("outcome", ""),
           "track_label": TRACK_LABELS[config["track"]], "interface_label": INTERFACE_LABELS[config["interface"]],
           "database": tokens["DB"], "schema": tokens["SCHEMA"], "role": tokens["ROLE"], "warehouse": tokens["WH"],
           "zip": zip_name, "expected_text": expected_text,
           "interface_notes": INTERFACE_NOTES[config["interface"]] + trial}
    write_json(repo / "app/lab.json", lab)
    write_json(repo / "app/curriculum.json", curriculum)
    (repo / "app/components.py").write_text(components, encoding="utf-8")
    shutil.copyfile(SKILL_ROOT / "assets/workshop/streamlit_app.py", repo / "streamlit_app.py")
    (repo / "requirements.txt").write_text("streamlit>=1.42,<2\n", encoding="utf-8")
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n*.pyc\n.DS_Store\n.streamlit/secrets.toml\n", encoding="utf-8")
    shutil.copytree(upstream / "workshop_guide/.streamlit", repo / ".streamlit")
    shutil.copytree(upstream / "workshop_guide/static", repo / "static",
                    ignore=shutil.ignore_patterns("*.csv", "*.zip"))
    (repo / "admin/setup.sql").write_text(render_tokens((SKILL_ROOT / "assets/admin/setup.sql").read_text(), tokens),
                                          encoding="utf-8")
    (repo / "data").mkdir()
    shutil.copyfile(data_dir / "synthetic-data.zip", repo / "data" / zip_name)
    shutil.copyfile(data_dir / "data-dictionary.json", repo / "data/data-dictionary.json")
    starters = {}
    for step_id, files in STARTERS[config["track"]].items():
        starters[step_id] = []
        for source_name, save_as, label in files:
            ml_ext = "ipynb" if config["interface"] == "snowsight" else "py"
            source_name, save_as = source_name.format(ml_ext=ml_ext), save_as.format(ml_ext=ml_ext)
            source = SKILL_ROOT / "assets/exercises" / source_name
            starters[step_id].append({
                "label": label, "path": save_as,
                "language": LANGUAGES.get(source.suffix, "text"),
                "content": render_tokens(source.read_text(encoding="utf-8"), tokens)})
    write_json(repo / "app/starters.json", starters)
    for name in ("LICENSE", "NOTICE"):
        if (upstream / name).is_file():
            shutil.copyfile(upstream / name, repo / f"UPSTREAM_{name}")
    (repo / "README.md").write_text(build_readme(config, lab, expected_text), encoding="utf-8")

    # Facilitator materials (local only; may use the real customer name).
    agenda = "".join(f"<li>{step['minutes']} min: {html.escape(step['title'])} "
                     f"<span class=\"muted\">({html.escape(step['mode'])})</span></li>" for step in curriculum)
    sections = ("welcome", "roles", "agenda", "plan", "components", "finish", "prep")
    metadata = {"generated": date.today().isoformat(), "intent": "Cortex Code HOL facilitator introduction",
                "dataSources": [{"type": "file", "path": ".build/lab-config.json"}],
                "sections": [{"id": section, "title": section,
                              "producerNotes": "Instructional content, no live customer results."} for section in sections]}
    deck_values = {"ORGANIZATION": html.escape(config["organization"]), "TRACK": html.escape(lab["track_label"]),
                   "INTERFACE": html.escape(f"Cortex Code {lab['interface_label']}"),
                   "SCENARIO": html.escape(config["scenario"]), "AGENDA_HTML": agenda,
                   "METADATA_JSON": json.dumps(metadata).replace("<", "\\u003c"),
                   "COMPONENTS": html.escape({
                       "data-engineering": "AGENTS.md, team review skill, plugin packaging, lifecycle hook, and read-only subagent.",
                       "machine-learning": "Team ML conventions, 90-day spend model, registry, warehouse inference, and monitoring.",
                       "analysts": "Reporting conventions, HTML and Snowflake Dashboard, semantic view, Cortex Agent, CoWork, and controlled email automation."
                   }[config["track"]])}
    repo_url = config["public"].get("github_repo") or "https://github.com/<github-user>/" + repo.name
    guide_values = {"ORGANIZATION": config["organization"], "TITLE": config["public"]["title"],
                    "OUTCOME": config.get("outcome") or "_Not set yet: agree it with the sponsor at T\u22127._",
                    "REPO_FOLDER": repo.name, "REPO_URL": repo_url,
                    "REPO_OWNER_NAME": repo_url.removeprefix("https://github.com/"),
                    "TRACK": lab["track_label"], "INTERFACE": lab["interface_label"]}
    targets = [(facilitator, config["organization"])]
    if config["public"].get("include_facilitator"):
        # Public copy for the facilitator on the day; uses the public title unless the name is approved.
        shown = config["organization"] if config["public"].get("show_customer_name") else config["public"]["title"]
        (repo / "facilitator").mkdir()
        targets.append((repo / "facilitator", shown))
    for folder, organization in targets:
        (folder / "facilitator-intro.html").write_text(render_tokens(
            (SKILL_ROOT / "assets/facilitator-intro.html").read_text(),
            {**deck_values, "ORGANIZATION": html.escape(organization)}), encoding="utf-8")
        (folder / "facilitator-guide.md").write_text(render_tokens(
            (SKILL_ROOT / "assets/facilitator-guide.md").read_text(),
            {**guide_values, "ORGANIZATION": organization}), encoding="utf-8")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--upstream", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-mode", choices=["installed", "repository", "archive"], default="archive")
    args = parser.parse_args()
    try:
        result = assemble(read_json(args.config), args.upstream.resolve(), args.output.resolve(), args.source_mode)
    except (ValueError, OSError) as error:
        parser.exit(1, f"Assembly stopped: {error}\n")
    print(json.dumps({"output": str(result), "status": "starter_assembled", "pushed": False}))


if __name__ == "__main__":
    main()

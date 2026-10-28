"""Shared validation and rendering helpers for the offline HOL scripts."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path

TRACKS = {"data-engineering", "machine-learning", "analysts"}
INTERFACES = {"desktop", "cli", "snowsight"}
ACCOUNT_MODES = {"customer", "trial"}
# Where ML work lives per interface: a Workspace notebook in Snowsight, a script locally.
ML_WORKSPACE = {
    "snowsight": ("ml_spend_model.ipynb", "a Snowflake Workspace notebook (.ipynb) in this workspace, "
                   "connected to the HOL compute pool"),
    "desktop": ("ml_spend_model.py", "a Python script in this project"),
    "cli": ("ml_spend_model.py", "a Python script in this project"),
}
REPOSITORY = "https://github.com/sfc-gh-obenning/coco-hol-template"
UPSTREAM_FILES = (
    ".cortex-plugin/skills/generate-hol/SKILL.md", "README.md",
    "workshop_guide/streamlit_app.py", "workshop_guide/components.py",
    "workshop_guide/app_pages/agenda.py", "workshop_guide/app_pages/session_01.py",
)
TOKEN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
IDENTIFIER = re.compile(r"[A-Z][A-Z0-9_]{0,127}\Z")
GITHUB_REPO = re.compile(r"https://github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9._-]{1,100})")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value):
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2, ensure_ascii=True)
        output.write("\n")


def config_errors(config: dict) -> list[str]:
    errors = []
    if not isinstance(config, dict):
        return ["Configuration must be a JSON object"]
    for field in ("organization", "industry", "scenario"):
        if not isinstance(config.get(field), str) or not config[field].strip():
            errors.append(f"Missing nonempty {field}")
    for field, choices in (("track", TRACKS), ("interface", INTERFACES), ("account_mode", ACCOUNT_MODES)):
        if config.get(field) not in choices:
            errors.append(f"Invalid {field}")
    for field in ("sandbox_database", "warehouse", "participant_schema", "participant_role"):
        value = config.get(field, "")
        if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
            errors.append(f"Invalid identifier: {field}")
    for field in ("sandbox_database", "warehouse", "participant_role"):
        if not str(config.get(field, "")).startswith("HOL_"):
            errors.append(f"{field} must start HOL_")
    if config.get("participant_schema") in {"SOURCE", "PUBLIC", "INFORMATION_SCHEMA"}:
        errors.append("Participant schema must not be a shared/system schema")
    if type(config.get("data_seed")) is not int:
        errors.append("data_seed must be an integer")
    try:
        date.fromisoformat(config.get("as_of_date", ""))
    except (ValueError, TypeError):
        errors.append("as_of_date must be an ISO date")
    categories = config.get("categories")
    if (not isinstance(categories, list) or not 2 <= len(categories) <= 12
            or any(not isinstance(item, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9 _-]{0,59}", item)
                   for item in categories)
            or len(set(categories)) != len(categories)):
        errors.append("categories must be 2-12 unique simple industry labels")
    if config.get("duration_minutes") != 60:
        errors.append("duration_minutes must equal 60")
    if config.get("design_approved") is not True:
        errors.append("Lab design must be approved before assembling")
    if config.get("schema_version") != 1:
        errors.append("Unsupported config schema_version")
    public = config.get("public")
    if not isinstance(public, dict):
        errors.append("Missing public publishing settings")
    else:
        if not isinstance(public.get("title"), str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 &.,'()-]{2,79}", public["title"]):
            errors.append("public.title must be 3-80 plain characters")
        if type(public.get("show_customer_name")) is not bool:
            errors.append("public.show_customer_name must be true/false")
        elif not public["show_customer_name"] and config.get("organization", "").lower() in public.get("title", "").lower():
            errors.append("public.title contains the customer name without approval")
        if type(public.get("include_facilitator", False)) is not bool:
            errors.append("public.include_facilitator must be true/false")
        repo = public.get("github_repo")
        if repo is not None and not GITHUB_REPO.fullmatch(str(repo)):
            errors.append("public.github_repo must be https://github.com/<owner>/<repo>")
        if public.get("hosting") not in {"streamlit-community-cloud", "local-only"}:
            errors.append("public.hosting must be streamlit-community-cloud or local-only")
    return errors


def public_slug(config: dict) -> str:
    repo = (config.get("public") or {}).get("github_repo")
    if repo:
        return GITHUB_REPO.fullmatch(repo).group(2)
    return re.sub(r"[^a-z0-9]+", "-", config["public"]["title"].lower()).strip("-")


def upstream_errors(root: Path) -> list[str]:
    errors = []
    for relative in UPSTREAM_FILES:
        path = root / relative
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            errors.append(f"Missing or unsafe upstream file: {relative}")
    if errors:
        return errors
    skill = (root / UPSTREAM_FILES[0]).read_text(encoding="utf-8")
    if not re.search(r"^name:\s*generate-hol\s*$", skill, re.MULTILINE):
        errors.append("Upstream SKILL.md does not identify generate-hol")
    components = (root / "workshop_guide/components.py").read_text(encoding="utf-8")
    if "def render_prompt(" not in components or "SESSION_PROMPTS" not in components:
        errors.append("Upstream components contract changed; manual adaptation needed")
    return errors


def source_hashes(root: Path) -> dict:
    return {relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in UPSTREAM_FILES}


def render_tokens(text: str, values: dict) -> str:
    def substitute(match):
        key = match.group(1)
        if key not in values:
            raise ValueError(f"Unresolved token: {key}")
        return str(values[key])
    return TOKEN.sub(substitute, text)


def _session_content(body: str) -> tuple[str, dict]:
    """Split tagged participant content (@tech, @situation, ...) from the facilitator-facing body."""
    content = {"technologies": [], "situation": "", "tips": [], "concepts": [], "built": []}
    kept = []
    for line in body.splitlines():
        tag, _, value = line.partition(" ")
        value = value.strip()
        if tag == "@tech":
            name, icon, description = (part.strip() for part in value.split("|", 2))
            content["technologies"].append({"name": name, "icon": icon, "description": description})
        elif tag == "@situation":
            content["situation"] = value
        elif tag in {"@tip", "@warn"}:
            content["tips"].append({"kind": "warning" if tag == "@warn" else "tip", "text": value})
        elif tag == "@concept":
            term, definition = (part.strip() for part in value.split("|", 1))
            content["concepts"].append({"term": term, "definition": definition})
        elif tag == "@built":
            content["built"].append(value)
        elif tag.startswith("@"):
            raise ValueError(f"Unknown session tag: {tag}")
        else:
            kept.append(line)
    return "\n".join(kept).strip(), content


def curriculum_from_reference(path: Path, config: dict) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    parameters = {"<DB>": config["sandbox_database"], "<WH>": config["warehouse"],
                  "<PARTICIPANT_SCHEMA>": config["participant_schema"], "<INDUSTRY>": config["industry"],
                  "<ML_FILE>": ML_WORKSPACE[config["interface"]][0],
                  "<ML_WORKSPACE>": ML_WORKSPACE[config["interface"]][1]}
    for token, value in parameters.items():
        text = text.replace(token, value)
    schedule = re.findall(r"^\| ((?:de|ml|an)-\d+) \| (\d+) \| ([^|]+) \| ([^|]+) \|$", text, re.MULTILINE)
    sections = {}
    for match in re.finditer(r"^### ((?:de|ml|an)-\d+):[^\n]*\n(.*?)(?=^### |^## |\Z)", text, re.MULTILINE | re.DOTALL):
        sections[match.group(1)] = match.group(2).strip()
    result = []
    for identifier, minutes, title, mode in schedule:
        body = sections.get(identifier)
        if not body:
            raise ValueError(f"Missing exercise details: {identifier}")
        prompts = [re.sub(r"(?m)^> ?", "", block).strip()
                   for block in re.findall(r"(?m)(?:^>.*(?:\n|$))+", body)]
        body, content = _session_content(body)
        if not content["technologies"] or not content["situation"] or not content["concepts"]:
            raise ValueError(f"Step {identifier} needs @tech, @situation and @concept content")
        result.append({"id": identifier, "minutes": int(minutes), "title": title.strip(),
                       "mode": mode.strip(), "body": body, **content,
                       "prompts": [{"id": f"{identifier}-p{index}", "text": prompt}
                                   for index, prompt in enumerate(prompts, 1)]})
    if not result or sum(step["minutes"] for step in result) != 60:
        raise ValueError("Track schedule must total 60 minutes")
    return result

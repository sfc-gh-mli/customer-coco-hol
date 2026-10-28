"""Validate a local HOL package without executing its code or connecting to Snowflake."""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import zipfile
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path

from hol_common import REPOSITORY, TOKEN, config_errors, public_slug, read_json, upstream_errors

BUILD_REQUIRED = ["lab-config.json", "generation-manifest.json", "validation-report.json", "expected-results.json",
                  "data/manifest.json", "data/data-dictionary.json", "data/synthetic-data.zip"]
FACILITATOR_REQUIRED = ["facilitator-intro.html", "facilitator-guide.md"]
PUBLIC_REQUIRED = ["README.md", "streamlit_app.py", "requirements.txt", ".gitignore", ".streamlit/config.toml",
                   "app/components.py", "app/curriculum.json", "app/lab.json", "admin/setup.sql",
                   "data/data-dictionary.json", "app/starters.json"]
INTERNAL_NAMES = {"lab-config.json", "generation-manifest.json", "validation-report.json", "expected-results.json",
                  "facilitator-intro.html", "facilitator-guide.md", "manifest.json"}
SECTIONS = ["Preflight", "Create the sandbox", "Upload data", "Load and reconcile", "Participant role",
            "Cortex Code access", "Verify AS THE PARTICIPANT", "Cleanup AFTER the event"]
SECRET = re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|"
                    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?i:password|secret|token)\s*[:=]\s*['\"][^'\"]{6,})")
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
DECK_SECTIONS = 7


class DeckParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections, self.errors, self.buttons = [], [], set()
        self.metadata, self.in_metadata, self.marker = "", False, False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"iframe", "object", "embed", "form", "base"}:
            self.errors.append(f"Unsupported deck tag: {tag}")
        if any(key.lower().startswith("on") for key in values):
            self.errors.append("Inline event handler in deck")
        if tag in {"script", "img", "link"} and (values.get("src") or values.get("href")):
            self.errors.append("Deck must be self-contained with no remote resources")
        if tag == "section":
            self.sections.append(values.get("id"))
        if tag == "button":
            self.buttons.add(values.get("id"))
        if tag == "meta" and values.get("name") == "snowflake-source":
            self.marker = values.get("content") == "cortex-agent-authored"
        if tag == "script" and values.get("id") == "snowflake-report-metadata":
            self.in_metadata = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_metadata = False

    def handle_data(self, data):
        if self.in_metadata:
            self.metadata += data


def validate_data(build: Path, public_zip: Path, errors: list[str]):
    manifest = read_json(build / "data/manifest.json")
    expected = read_json(build / "expected-results.json")
    records = {}
    for entry in manifest["files"]:
        name = entry["file"]
        if Path(name).name != name or not name.endswith(".csv"):
            raise ValueError("Unsafe data manifest filename")
        path = build / "data" / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            errors.append(f"Hash mismatch: {name}")
        with path.open(newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != entry["columns"]:
                errors.append(f"Column mismatch: {name}")
            rows = list(reader)
        if name in records:
            errors.append(f"Duplicate data manifest entry: {name}")
        records[name] = rows
        if len(rows) != entry["rows"] or len(rows) != expected["row_counts"].get(name):
            errors.append(f"Row count mismatch: {name}")
    locations = {row["LOCATION_ID"] for row in records["locations.csv"]}
    customers = {row["CUSTOMER_ID"] for row in records["customers.csv"]}
    transactions = records["transactions.csv"]
    if len(locations) != len(records["locations.csv"]) or len(customers) != len(records["customers.csv"]):
        errors.append("Duplicate dimension keys")
    if any(row["LOCATION_ID"] not in locations for row in records["customers.csv"]):
        errors.append("Orphan customer location")
    if any(row["CUSTOMER_ID"] not in customers for row in transactions):
        errors.append("Orphan transaction customer")
    if len({row["TRANSACTION_ID"] for row in transactions}) != len(transactions):
        errors.append("Duplicate transaction keys")
    start = datetime.fromisoformat(manifest["start_inclusive"])
    end = datetime.fromisoformat(manifest["end_exclusive"])
    totals, months = defaultdict(int), defaultdict(int)
    for row in transactions:
        if not start <= datetime.fromisoformat(row["TRANSACTION_TIME"]) < end:
            errors.append("Transaction timestamp outside declared window")
        amount = Decimal(row["AMOUNT"])
        if not amount.is_finite() or amount < 0 or amount * 100 != (amount * 100).to_integral_value():
            raise ValueError("Invalid transaction amount")
        if row["STATUS"] not in {"COMPLETED", "CANCELED", "REFUNDED"}:
            errors.append("Unknown transaction status")
        if row["STATUS"] == "COMPLETED":
            cents = int(amount * 100)
            totals[row["PRODUCT_CATEGORY"]] += cents
            months[row["TRANSACTION_TIME"][:7]] += cents
    if sum(totals.values()) != expected["net_spend_cents"]:
        errors.append("Known-answer net spend mismatch")
    if dict(totals) != expected["category_net_spend_cents"] or dict(months) != expected["monthly_net_spend_cents"]:
        errors.append("Known-answer breakdown mismatch")
    if len({row["CUSTOMER_ID"] for row in transactions}) != expected["distinct_customers_in_transactions"]:
        errors.append("Known-answer customer count mismatch")
    for archive_path in (build / "data/synthetic-data.zip", public_zip):
        if hashlib.sha256(archive_path.read_bytes()).hexdigest() != manifest["zip_sha256"]:
            errors.append(f"ZIP checksum mismatch: {archive_path.name}")
            continue
        with zipfile.ZipFile(archive_path) as archive:
            if sorted(archive.namelist()) != sorted(records):
                errors.append("ZIP file inventory mismatch")
            elif any(archive.read(name) != (build / "data" / name).read_bytes() for name in records):
                errors.append("ZIP content mismatch")


def public_safety_errors(public: Path, config: dict) -> list[str]:
    """Conservative leak checks for the folder that will be pushed publicly."""
    errors = []
    organization = config.get("organization", "").strip().lower()
    hide_name = not config.get("public", {}).get("show_customer_name", False)
    for path in sorted(public.rglob("*")):
        relative = path.relative_to(public).as_posix()
        if path.is_symlink():
            errors.append(f"Symlink in public repo: {relative}")
            continue
        if ".git/" in f"{relative}/" or not path.is_file():
            continue
        shared_facilitator = (config.get("public", {}).get("include_facilitator")
                              and relative in {f"facilitator/{name}" for name in FACILITATOR_REQUIRED})
        if not shared_facilitator and (path.name in INTERNAL_NAMES
                                       or relative.startswith((".build/", "facilitator/", ".venv/"))):
            errors.append(f"Internal file in public repo: {relative}")
        if path.suffix in {".csv"} and not relative.startswith("data/"):
            errors.append(f"Unexpected data file in public repo: {relative}")
        if path.suffix.lower() in {".ttf", ".png", ".zip"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if SECRET.search(text):
            errors.append(f"Secret-like content in public repo: {relative}")
        if EMAIL.search(text):
            errors.append(f"Email address in public repo: {relative}")
        if re.search(r"PRIVATE[_ ]ROSTER|GRANT\s+ROLE\s+\w+\s+TO\s+USER\s+(?!<)", text, re.IGNORECASE):
            errors.append(f"Participant roster content in public repo: {relative}")
        if hide_name and organization and organization in text.lower():
            errors.append(f"Unapproved customer name in public repo: {relative}")
    return errors


def validate_package(root: Path) -> dict:
    errors, warnings = [], []
    build, facilitator = root / ".build", root / "facilitator"
    for folder, names in ((build, BUILD_REQUIRED), (facilitator, FACILITATOR_REQUIRED)):
        errors.extend(f"Missing file: {folder.name}/{name}" for name in names if not (folder / name).is_file())
    if errors:
        return {"status": "failed", "errors": errors, "warnings": warnings, "live": "not_run"}
    try:
        config = read_json(build / "lab-config.json")
        errors.extend(config_errors(config))
        public = root / public_slug(config)
        errors.extend(f"Missing file: {public.name}/{name}" for name in PUBLIC_REQUIRED if not (public / name).is_file())
        extra = {path.name for path in root.iterdir()} - {".build", "facilitator", public.name}
        if extra:
            errors.append(f"Unexpected top-level items: {sorted(extra)}")
        if errors:
            raise ValueError("Package structure incomplete")
        steps = read_json(public / "app/curriculum.json")
        if not isinstance(steps, list) or not steps:
            raise ValueError("Curriculum must be a nonempty list")
        if any(type(step.get("minutes")) is not int or step["minutes"] <= 0 for step in steps):
            errors.append("Step minutes must be positive integers")
        elif sum(step["minutes"] for step in steps) != 60:
            errors.append("Curriculum does not total 60 minutes")
        identifiers = [step["id"] for step in steps]
        prompt_ids = [prompt["id"] for step in steps for prompt in step["prompts"]]
        if len(set(identifiers)) != len(identifiers) or len(set(prompt_ids)) != len(prompt_ids):
            errors.append("Duplicate step/prompt IDs")
        if any(not step.get("body") or not step.get("title") or not step.get("mode") for step in steps):
            errors.append("Incomplete exercise content")
        if any(not prompt.get("text") for step in steps for prompt in step["prompts"]):
            errors.append("Empty prompt")
        for step in steps:
            if not step.get("technologies") or not step.get("situation") or not step.get("concepts"):
                errors.append(f"Step {step.get('id')} is missing technologies, situation or key concepts")
            elif any(not re.fullmatch(r"[a-z0-9_]+", tech.get("icon", "")) for tech in step["technologies"]):
                errors.append(f"Step {step['id']} has an invalid technology icon name")
        lab = read_json(public / "app/lab.json")
        if not (public / "data" / lab["zip"]).is_file():
            errors.append("Public data zip referenced by app is missing")
        generation = read_json(build / "generation-manifest.json")
        source = generation["upstream"]
        if source["repository"] != REPOSITORY or source["mode"] not in {"installed", "repository", "archive"}:
            errors.append("Invalid upstream provenance")
        if source["mode"] == "repository" and not re.fullmatch(r"[0-9a-f]{40}", source.get("commit") or ""):
            errors.append("Repository source needs a verified commit")
        if not source.get("source_hashes") or any(not re.fullmatch(r"[0-9a-f]{64}", digest)
                                                  for digest in source["source_hashes"].values()):
            errors.append("Missing/invalid upstream hashes")
        kind = generation.get("package_kind")
        if kind not in {"starter", "reviewed", "event_ready"}:
            errors.append("Unknown package_kind")
        if kind in {"reviewed", "event_ready"} and not (public / "app/checkpoints.json").is_file():
            errors.append("Reviewed packages require runtime checkpoint manifest")
        if kind == "starter":
            warnings.append("Starter only: customer refinement, runtime checkpoints and rehearsals remain")
        elif kind == "event_ready":
            report = read_json(build / "validation-report.json")
            if report.get("live") != "passed" or report.get("timed_rehearsal") != "passed":
                errors.append("event_ready requires successful live and timed rehearsal evidence")
        skill = {"data-engineering": "hol-deployment-review", "machine-learning": "hol-ml-review",
                 "analysts": "hol-report"}.get(config.get("track"))
        prompt_text = " ".join(prompt["text"] for step in read_json(public / "app/curriculum.json") for prompt in step["prompts"])
        if not skill or f"skill named {skill}" not in prompt_text:
            errors.append("Missing selected track's custom skill")
        validate_data(build, public / "data" / lab["zip"], errors)

        setup = (public / "admin/setup.sql").read_text()
        positions = [setup.find(f"SECTION {number}: {title}") for number, title in enumerate(SECTIONS, 1)]
        if -1 in positions or positions != sorted(positions):
            errors.append("setup.sql must contain sections 1-8 in order")
        else:
            cleanup = setup[positions[-1]:].splitlines()[1:]
            if any(line.strip() and not line.lstrip().startswith("--") for line in cleanup):
                errors.append("Cleanup section must remain commented out")
        executable = "\n".join(line for line in setup.splitlines() if not line.lstrip().startswith("--"))
        if re.search(r"\b(GRANT\s+ALL|TO\s+ROLE\s+PUBLIC|ALTER\s+ACCOUNT|CREATE\s+OR\s+REPLACE|FORCE\s*=\s*TRUE)\b",
                     executable, re.IGNORECASE):
            errors.append("Unsafe SQL pattern in setup.sql")
        track_grant = {"machine-learning": "CREATE MODEL MONITOR", "analysts": "CREATE AGENT"}
        for track, phrase in track_grant.items():
            if (phrase in executable) != (config["track"] == track):
                errors.append(f"Incorrect track grant block for {track}")

        deck_text = (facilitator / "facilitator-intro.html").read_text()
        parser = DeckParser()
        parser.feed(deck_text)
        errors.extend(parser.errors)
        if len(parser.sections) != DECK_SECTIONS or len(set(parser.sections)) != DECK_SECTIONS or not parser.marker:
            errors.append(f"Deck needs {DECK_SECTIONS} unique sections and author marker")
        if "prep" not in parser.sections:
            errors.append("Deck needs the preparation checklist slide")
        if {section["id"] for section in json.loads(parser.metadata)["sections"]} != set(parser.sections):
            errors.append("Deck provenance section IDs mismatch")
        if not {"previous", "next", "notes", "print"} <= parser.buttons:
            errors.append("Missing deck controls")
        if re.search(r"\b(fetch|eval|XMLHttpRequest|WebSocket|localStorage|sessionStorage)\s*[.(]", deck_text):
            errors.append("Unsafe deck API")

        for path in [*public.rglob("*"), *facilitator.rglob("*")]:
            if not path.is_file() or path.suffix not in {".py", ".sql", ".html", ".md", ".json", ".toml"}:
                continue
            text = path.read_text()
            if TOKEN.search(text):
                errors.append(f"Unresolved template token: {path.relative_to(root)}")
            if path.suffix == ".py":
                try:
                    ast.parse(text)
                except SyntaxError as error:
                    errors.append(f"Python syntax: {path.name}: {error}")
        errors.extend(public_safety_errors(public, config))
        warnings.append("SQL, permissions, feature support, delivery and pacing require approved sandbox rehearsal")
        if generation.get("publish", {}).get("github") != "pushed":
            warnings.append("Public repo not pushed yet")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, InvalidOperation, zipfile.BadZipFile) as error:
        errors.append(f"Invalid package content: {error}")
    return {"status": "failed" if errors else "passed", "errors": errors, "warnings": warnings,
            "live": "not_run", "timed_rehearsal": "not_run"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path, nargs="?", help="Package output directory (contains .build/)")
    parser.add_argument("--upstream", type=Path)
    parser.add_argument("--report", action="store_true", help="Record offline results in .build/validation-report.json")
    args = parser.parse_args()
    if args.upstream:
        errors = upstream_errors(args.upstream.resolve())
        result = {"status": "failed" if errors else "passed", "errors": errors,
                  "note": "Structural compatibility only; source inspection still required"}
    elif args.package:
        result = validate_package(args.package.resolve())
        report_path = args.package / ".build/validation-report.json"
        if args.report and report_path.is_file():
            report = read_json(report_path)
            report["offline"] = result
            report_path.write_text(json.dumps(report, indent=2) + "\n")
    else:
        parser.error("Provide a package or --upstream")
    print(json.dumps(result, indent=2))
    return int(result["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())

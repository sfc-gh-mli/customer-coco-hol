"""Offline tests; no Snowflake connection or external service writes."""
import importlib.util
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from hol_common import config_errors, curriculum_from_reference, source_hashes, upstream_errors
from scaffold_package import assemble
from validate_package import validate_package

UPSTREAM = Path(os.environ.get("HOL_TEST_UPSTREAM", str(ROOT / "tests/fixtures/upstream-not-supplied")))
REPO = "retail-coco-hol"
BASE = {
    "schema_version": 1, "organization": "Example Retail", "industry": "retail",
    "scenario": "Use synthetic purchase activity to understand customer spend.",
    "track": "data-engineering", "interface": "desktop", "account_mode": "customer",
    "topics": [], "outcome": "Participants leave able to repeat one real workflow on their own data.", "event": {"date": None, "timezone": None, "participants": 10},
    "sandbox_database": "HOL_EXAMPLE_20261026", "warehouse": "HOL_EXAMPLE_WH",
    "participant_schema": "P001", "participant_role": "HOL_EXAMPLE_P001",
    "data_seed": 42, "as_of_date": "2026-09-30", "duration_minutes": 60,
    "categories": ["Essentials", "Apparel", "Electronics"], "design_approved": True,
    "delivery": {"publish": False, "email": False}, "readiness": {"status": "not_run"},
    "public": {"title": "Retail Cortex Code Lab", "show_customer_name": False,
               "github_repo": f"https://github.com/example-se/{REPO}", "hosting": "streamlit-community-cloud"},
}


class SkillTests(unittest.TestCase):
    def test_skill_structure_and_links(self):
        text = (ROOT / "SKILL.md").read_text()
        self.assertLess(len(text.splitlines()), 200)
        self.assertRegex(text, r"(?s)^---\nname: customer-coco-hol\ndescription: .+?\n---")
        for relative in re.findall(r"\]\(([^)]+)\)", text):
            self.assertTrue((ROOT / relative).is_file(), relative)

    @unittest.skipUnless(importlib.util.find_spec("yaml"), "PyYAML optional test dependency absent")
    def test_frontmatter_parses(self):
        import yaml
        for path in [ROOT / "SKILL.md", *(ROOT / "assets/exercises").rglob("SKILL.md")]:
            frontmatter = yaml.safe_load(path.read_text().split("---", 2)[1])
            self.assertTrue(frontmatter["name"])
            self.assertTrue(frontmatter["description"])

    def test_configuration_rejections(self):
        public = BASE["public"]
        cases = [("sandbox_database", "PROD"), ("warehouse", "HOL_X; DROP DATABASE X"),
                 ("participant_schema", "SOURCE"), ("participant_role", "ACCOUNTADMIN"),
                 ("design_approved", False), ("duration_minutes", 61), ("as_of_date", "tomorrow"),
                 ("categories", ["=IMPORTDATA(x)", "A"]), ("interface", "unknown"), ("data_seed", True),
                 ("public", None), ("public", {**public, "github_repo": "https://evil.example/x/y"}),
                 ("public", {**public, "title": "Example Retail Lab"}),
                 ("public", {**public, "hosting": "heroku"}), ("public", {**public, "title": "<script>"})]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.assertTrue(config_errors({**BASE, field: value}))
        approved = {**BASE, "public": {**public, "title": "Example Retail Lab", "show_customer_name": True}}
        self.assertEqual(config_errors(approved), [])

    def test_all_schedules(self):
        for track in ("data-engineering", "machine-learning", "analysts"):
            steps = curriculum_from_reference(ROOT / f"references/tracks/{track}.md", {**BASE, "track": track})
            self.assertEqual(sum(step["minutes"] for step in steps), 60)
            self.assertEqual(len(steps), 7)
            self.assertIn("Plan", steps[0]["title"])
            for step in steps:
                self.assertTrue(step["technologies"] and step["situation"] and step["concepts"] and step["tips"], step["id"])
                self.assertNotRegex(step["body"], r"(?m)^@\w+")
                self.assertNotIn("<INDUSTRY>", step["situation"])

    def test_hook_fixtures(self):
        script = ROOT / "assets/exercises/guard_demo.py"
        spec = importlib.util.spec_from_file_location("guard_demo", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = {"hook_event_name": "PreToolUse", "tool_name": "sql_execute",
                   "tool_input": {"sql": "SELECT 1 FROM HOL_DEMO.P001.SAFE"}}
        self.assertTrue(module.decision(payload)[0])
        for sql in ("DROP TABLE HOL_DEMO.PROD_SIM.EXAMPLE", 'SELECT * FROM "prod_sim".DEMO', ""):
            self.assertFalse(module.decision({**payload, "tool_input": {"sql": sql}})[0])
        for malformed in (None, [], {}, {"tool_input": "bad"}):
            self.assertFalse(module.decision(malformed)[0])
        result = subprocess.run([sys.executable, str(script)], input="not json", text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)


@unittest.skipUnless(UPSTREAM.is_dir(), "Set HOL_TEST_UPSTREAM to an inspected template checkout")
class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name)

    def package(self, config=None, name="package", mode="archive"):
        return assemble(config or BASE, UPSTREAM, self.parent / name, mode)

    def test_customer_prefix_and_exact_cleanup(self):
        config = {**BASE, "track": "machine-learning", "interface": "snowsight", "object_prefix": "SBX_DE_",
                  "sandbox_database": "SBX_DE_HOL", "warehouse": "COMPUTE_WH", "participant_role": "SBX_DE_P001",
                  "existing_objects": ["warehouse"], "event": {"participants": 3}}
        self.assertEqual(config_errors(config), [])
        self.assertTrue(config_errors({**config, "sandbox_database": "HOL_LAB"}))  # new object, wrong prefix
        for bad in ("", "X_", "sbx_", "SBX", "SNOWFLAKE_"):
            self.assertTrue(config_errors({**config, "object_prefix": bad}), bad)
        path = self.package(config, name="prefixed")
        self.assertEqual(validate_package(path)["errors"], [])
        setup = (path / REPO / "admin/setup.sql").read_text()
        cleanup = setup[setup.rindex("\n", 0, setup.index("SECTION 8")) + 1:]
        drops = re.findall(r"^-- (DROP \w+(?: \w+)? [A-Z0-9_.]+);", cleanup, re.MULTILINE)
        self.assertEqual(drops, ["DROP COMPUTE POOL SBX_DE_NOTEBOOK_POOL", "DROP DATABASE SBX_DE_HOL",
                                 "DROP ROLE SBX_DE_P001", "DROP ROLE SBX_DE_P002", "DROP ROLE SBX_DE_P003"])
        self.assertIn("SHOW WAREHOUSES LIKE 'SBX_DE_%'", cleanup)
        self.assertIn("COMPUTE_WH is an existing warehouse: not dropped.", cleanup)
        self.assertIn("CREATE COMPUTE POOL SBX_DE_NOTEBOOK_POOL", setup)
        for line in cleanup.splitlines():  # every DROP names a prefixed object; nothing executable
            self.assertTrue(line.startswith("--") or not line.strip(), line)
            if "DROP " in line and "DROP SCHEMA" not in line:
                self.assertRegex(line, r"DROP [A-Z ]+ SBX_DE_")

    def test_existing_customer_objects(self):
        config = {**BASE, "sandbox_database": "ANALYTICS_SANDBOX", "warehouse": "COMPUTE_WH",
                  "participant_role": "DATA_ENGINEER", "existing_objects": ["database", "warehouse", "role"]}
        self.assertEqual(config_errors(config), [])
        self.assertTrue(config_errors({**config, "existing_objects": []}))
        self.assertTrue(config_errors({**config, "account_mode": "trial"}))
        self.assertTrue(config_errors({**config, "participant_role": "ACCOUNTADMIN"}))
        self.assertTrue(config_errors({**config, "sandbox_database": "SNOWFLAKE"}))
        path = self.package(config, name="existing")
        self.assertEqual(validate_package(path)["errors"], [])
        setup = (path / REPO / "admin/setup.sql").read_text()
        executable = "\n".join(line for line in setup.splitlines() if not line.lstrip().startswith("--"))
        for statement in ("CREATE DATABASE", "CREATE WAREHOUSE", "CREATE ROLE"):
            self.assertNotIn(statement, executable)
        self.assertIn("CREATE SCHEMA ANALYTICS_SANDBOX.SOURCE;", executable)
        self.assertIn("SHOW SCHEMAS IN DATABASE ANALYTICS_SANDBOX;", executable)
        self.assertIn("GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE DATA_ENGINEER;", executable)
        cleanup = setup[setup.index("SECTION 8"):]
        self.assertIn("-- DROP SCHEMA ANALYTICS_SANDBOX.SOURCE;", cleanup)
        for name in ("DATABASE ANALYTICS_SANDBOX", "WAREHOUSE COMPUTE_WH", "ROLE DATA_ENGINEER"):
            self.assertNotIn(f"DROP {name}", cleanup)
        fresh = (self.package(name="fresh") / REPO / "admin/setup.sql").read_text()
        self.assertIn("CREATE DATABASE HOL_EXAMPLE_20261026", fresh)
        self.assertIn("-- DROP DATABASE HOL_EXAMPLE_20261026;", fresh)

    def test_ml_workspace_notebook_in_snowsight(self):
        import ast
        for interface, ext in (("snowsight", "ipynb"), ("desktop", "py")):
            path = self.package({**BASE, "track": "machine-learning", "interface": interface}, name=f"ml-{interface}")
            public = path / REPO
            self.assertEqual(validate_package(path)["errors"], [])
            steps = {step["id"]: step for step in json.loads((public / "app/curriculum.json").read_text())}
            self.assertIn(f"ml_spend_model.{ext}", steps["ml-03"]["prompts"][0]["text"])
            self.assertNotIn("<ML_", json.dumps(steps))
            (starter,) = json.loads((public / "app/starters.json").read_text())["ml-04"]
            self.assertEqual(starter["path"], f"ml_training_checkpoint.{ext}")
            self.assertNotIn("{{", starter["content"])
            self.assertIn("HOL_EXAMPLE_20261026.P001.ML_FEATURE_SNAPSHOTS", starter["content"])
            setup = (public / "admin/setup.sql").read_text()
            self.assertEqual("CREATE COMPUTE POOL HOL_EXAMPLE_POOL" in setup, interface == "snowsight")
            self.assertEqual("-- DROP COMPUTE POOL HOL_EXAMPLE_POOL;" in setup, interface == "snowsight")
            if interface == "snowsight":
                self.assertIn("MAX_NODES = 11", setup)
                notebook = json.loads(starter["content"])
                self.assertEqual((notebook["nbformat"], notebook["nbformat_minor"]), (4, 5))
                ids = [cell["id"] for cell in notebook["cells"]]
                self.assertEqual(len(ids), len(set(ids)))
                sources = [cell["source"] for cell in notebook["cells"] if cell["cell_type"] == "code"]
            else:
                sources = [starter["content"]]
            for source in sources:
                ast.parse(source)

    def test_three_folder_layout(self):
        path = self.package()
        self.assertEqual(sorted(item.name for item in path.iterdir()), [".build", "facilitator", REPO])
        self.assertEqual(sorted(item.name for item in (path / "facilitator").iterdir()),
                         ["facilitator-guide.md", "facilitator-intro.html"])
        public = path / REPO
        for name in ("README.md", "streamlit_app.py", "requirements.txt", ".streamlit/config.toml",
                     "admin/setup.sql", f"data/{REPO}-data.zip", "static/Inter-Regular.ttf"):
            self.assertTrue((public / name).is_file(), name)
        self.assertEqual(list((public / "admin").iterdir()), [public / "admin/setup.sql"])
        self.assertFalse(list(public.rglob("*.json")) and any(p.name == "lab-config.json" for p in public.rglob("*")))
        guide = (path / "facilitator/facilitator-guide.md").read_text()
        for text in ("share.streamlit.io", "streamlit_app.py", f"example-se/{REPO}", "T−7", "T−3"):
            self.assertIn(text, guide)

    def test_all_18_configuration_paths(self):
        for track in ("data-engineering", "machine-learning", "analysts"):
            for interface in ("desktop", "cli", "snowsight"):
                for account_mode in ("customer", "trial"):
                    with self.subTest(track=track, interface=interface, account_mode=account_mode):
                        config = {**BASE, "track": track, "interface": interface, "account_mode": account_mode}
                        path = self.package(config, f"{track}-{interface}-{account_mode}")
                        result = validate_package(path)
                        self.assertEqual(result["errors"], [])
                        notes = json.loads((path / REPO / "app/lab.json").read_text())["interface_notes"]
                        if interface == "snowsight":
                            self.assertIn("Plugins, local hooks", notes)
                        if account_mode == "trial":
                            self.assertIn("Trial accounts", notes)

    def test_setup_sql_sections(self):
        for track, phrase in (("machine-learning", "CREATE MODEL MONITOR"), ("analysts", "CREATE AGENT")):
            setup = (self.package({**BASE, "track": track}, track) / REPO / "admin/setup.sql").read_text()
            self.assertEqual(len(re.findall(r"^-- SECTION \d:", setup, re.MULTILINE)), 8)
            self.assertIn(phrase, setup)
            cleanup = setup.split("SECTION 8:")[1].splitlines()[1:]
            self.assertTrue(all(not line.strip() or line.lstrip().startswith("--") for line in cleanup))

    def test_public_leak_checks(self):
        cases = [("notes.md", "contact jane@customer.com"), ("notes.md", "token = 'ghp_abcdefghijklmnopqrstuvwxyz123456'"),
                 ("lab-config.json", "{}"), ("roster.sql", "GRANT ROLE HOL_X TO USER JDOE;"),
                 ("notes.md", "Built for Example Retail")]
        for index, (name, content) in enumerate(cases):
            with self.subTest(name=name):
                path = self.package(name=f"leak{index}")
                (path / REPO / name).write_text(content)
                self.assertEqual(validate_package(path)["status"], "failed")
        shown = {**BASE, "public": {**BASE["public"], "show_customer_name": True}}
        path = self.package(shown, name="named")
        (path / REPO / "notes.md").write_text("Built for Example Retail")
        self.assertEqual(validate_package(path)["errors"], [])

    def test_publish_helper_guards(self):
        import publish_repo
        path = self.package(name="publish")
        ok = subprocess.CompletedProcess([], 1, "", "not found")
        with patch.object(publish_repo, "require_tools"), patch.object(publish_repo, "active_login", return_value="someone-else"), \
                patch.object(publish_repo, "run", return_value=ok) as run:
            details = publish_repo.plan(path)
            self.assertFalse(details["account_matches"])
            self.assertEqual(details["confirmation"], f"push example-se/{REPO}")
            self.assertNotIn("lab-config.json", " ".join(details["files"]))
            (path / REPO / "app/__pycache__").mkdir(exist_ok=True)
            (path / REPO / "app/__pycache__/x.pyc").write_bytes(b"\0")
            self.assertEqual(publish_repo.plan(path)["files"], details["files"])
            with self.assertRaisesRegex(RuntimeError, "gh auth switch"):
                publish_repo.push(path, details)
            with self.assertRaisesRegex(RuntimeError, "Not published yet"):
                publish_repo.update(path, {**details, "account_matches": True}, "msg")
            self.assertFalse(any(call.args[0][:3] == ["gh", "repo", "create"] for call in run.call_args_list))
        self.assertFalse((path / REPO / ".git").exists())

    def test_customer_name_only_in_facilitator(self):
        path = self.package({**BASE, "organization": "Northwind Grocers"}, name="hidden")
        public_text = " ".join(p.read_text(errors="ignore") for p in (path / REPO).rglob("*")
                               if p.is_file() and p.suffix in {".md", ".py", ".json", ".sql"})
        self.assertNotIn("Northwind", public_text)
        self.assertIn("Northwind Grocers", (path / "facilitator/facilitator-intro.html").read_text())

    def test_optional_public_facilitator_copy(self):
        config = {**BASE, "organization": "Northwind Grocers",
                  "public": {**BASE["public"], "include_facilitator": True}}
        path = self.package(config, name="shared")
        shared = path / REPO / "facilitator"
        self.assertEqual(sorted(p.name for p in shared.iterdir()), ["facilitator-guide.md", "facilitator-intro.html"])
        deck = (shared / "facilitator-intro.html").read_text()
        self.assertNotIn("Northwind", deck + (shared / "facilitator-guide.md").read_text())
        self.assertIn(html.escape(BASE["public"]["title"]), deck)
        self.assertIn("Northwind Grocers", (path / "facilitator/facilitator-intro.html").read_text())
        self.assertEqual(validate_package(path)["errors"], [])
        (shared / "extra.md").write_text("x")
        self.assertIn("Internal file in public repo: facilitator/extra.md", validate_package(path)["errors"])

    def test_dependency_and_nonoverwrite(self):
        self.assertEqual(upstream_errors(UPSTREAM), [])
        original = source_hashes(UPSTREAM)
        self.package(mode="installed")
        self.assertEqual(source_hashes(UPSTREAM), original)
        with self.assertRaises(FileExistsError):
            self.package()
        with patch("scaffold_package.subprocess.run", side_effect=FileNotFoundError("git unavailable")):
            with self.assertRaisesRegex(ValueError, "Cannot verify repository"):
                self.package(name="missing-git", mode="repository")
        self.assertFalse((self.parent / "missing-git").exists())

    def test_incompatible_upstream(self):
        from hol_common import UPSTREAM_FILES
        fake = self.parent / "upstream"
        for relative in UPSTREAM_FILES:
            target = fake / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((UPSTREAM / relative).read_text())
        (fake / "workshop_guide/components.py").write_text("# incompatible template")
        with self.assertRaisesRegex(ValueError, "contract changed"):
            assemble(BASE, fake, self.parent / "result")
        self.assertFalse((self.parent / "result").exists())

    def test_repository_provenance(self):
        responses = [subprocess.CompletedProcess([], 0, "a" * 40 + "\n", ""), subprocess.CompletedProcess([], 0, "", "")]
        with patch("scaffold_package.subprocess.run", side_effect=responses):
            path = self.package(name="repository", mode="repository")
        self.assertEqual(validate_package(path)["errors"], [])
        manifest = json.loads((path / ".build/generation-manifest.json").read_text())
        self.assertEqual(manifest["upstream"]["commit"], "a" * 40)
        self.assertEqual(manifest["publish"]["github"], "not_pushed")

    def test_reproducible_data_and_tampering(self):
        first, second = self.package(name="one"), self.package(name="two")
        self.assertEqual((first / REPO / f"data/{REPO}-data.zip").read_bytes(),
                         (second / REPO / f"data/{REPO}-data.zip").read_bytes())
        with (first / ".build/data/transactions.csv").open("a") as output:
            output.write("999999,1,2026-01-01 00:00:00,1.00,Essentials,WEB,COMPLETED\n")
        with (first / REPO / "admin/setup.sql").open("a") as output:
            output.write("\nGRANT ALL PRIVILEGES ON DATABASE HOL_EXAMPLE TO ROLE PUBLIC;\n")
        errors = validate_package(first)["errors"]
        self.assertTrue(any("Hash mismatch" in error for error in errors))
        self.assertTrue(any("Unsafe SQL" in error for error in errors))

    def test_stray_top_level_and_event_ready(self):
        path = self.package()
        (path / "participant-guide.md").write_text("old layout")
        self.assertTrue(any("Unexpected top-level" in e for e in validate_package(path)["errors"]))
        (path / "participant-guide.md").unlink()
        manifest_path = path / ".build/generation-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["package_kind"] = "event_ready"
        manifest_path.write_text(json.dumps(manifest))
        self.assertEqual(validate_package(path)["status"], "failed")

    def test_safe_display_encoding(self):
        path = self.package({**BASE, "organization": 'Example </script><script>alert(1)</script> "Co"'})
        deck = (path / "facilitator/facilitator-intro.html").read_text()
        self.assertNotIn("<script>alert(1)</script>", deck)
        self.assertEqual(validate_package(path)["errors"], [])

    @unittest.skipUnless(importlib.util.find_spec("streamlit"), "Streamlit optional test dependency absent")
    def test_streamlit_pages_from_repo_root(self):
        from streamlit.testing.v1 import AppTest
        for track in ("data-engineering", "machine-learning", "analysts"):
            public = self.package({**BASE, "track": track}, name=f"ui-{track}") / REPO
            app_path = public / "streamlit_app.py"
            sys.modules.pop("components", None)
            previous = os.getcwd()
            os.chdir(public)  # Community Cloud runs from the repo root
            try:
                app = AppTest.from_file(str(app_path), default_timeout=20).run()
                self.assertFalse(app.exception, str(app.exception))
                self.assertIn("walk away with", " ".join(block.value for block in app.markdown))
                steps = json.loads((public / "app/curriculum.json").read_text())
                starters = json.loads((public / "app/starters.json").read_text())
                self.assertFalse((public / "exercises").exists())
                self.assertNotIn("{{", json.dumps(starters))
                paths = [item["path"] for files in starters.values() for item in files]
                self.assertTrue(all(path.endswith((".sql", ".py")) for path in paths), paths)
                source = app_path.read_text().replace("st.navigation(pages, position=\"sidebar\").run()", "")
                calls = ["interface()", "admin()", *[f"exercise(CURRICULUM[{i}])" for i in range(len(steps))]]
                for call in calls:
                    sys.modules.pop("components", None)
                    page = AppTest.from_string(source.replace("Path(__file__).resolve().parent", f"Path({str(public)!r})")
                                               + f"\n{call}\n", default_timeout=20).run()
                    self.assertFalse(page.exception, f"{call}: {page.exception}")
                    if call == "admin()":
                        self.assertEqual(len(page.get("download_button")), 2)
                    if call.startswith("exercise"):
                        text = " ".join(block.value for block in page.markdown)
                        for section in ("Technologies used in this session", "The situation", "Key concepts"):
                            self.assertIn(section, text)
                        self.assertTrue(page.info or page.warning, f"{call}: no learning tips")
                        step = steps[calls.index(call) - 2]
                        has_next = "Next steps: bring it to your business" in text
                        self.assertEqual(has_next, step is steps[-1], call)
                        if has_next:
                            self.assertNotIn("<INDUSTRY>", text)
                        expected = starters.get(step["id"], [])
                        self.assertEqual(len(page.get("download_button")), len(expected), call)
                        self.assertEqual([block.value.strip() for block in page.code][:len(expected)],
                                         [item["content"].strip() for item in expected], call)
                    if call.startswith("exercise") and steps[calls.index(call) - 2]["prompts"]:
                        headings = " ".join(block.value for block in page.markdown)
                        self.assertNotRegex(headings, r"\b(de|ml|an)-\d+-p\d+\b")
                        self.assertRegex(headings, r"Try this prompt|Prompt 1 of")
                        self.assertNotRegex(headings, r"(?m)^Prompts?:\s*$")
                        page.checkbox[0].check().run()
                        self.assertTrue(any(page.session_state["_done"].values()))
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()

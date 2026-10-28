"""Public workshop guide. Reads only files in this repo; no Snowflake connection or secrets."""
import json
import re
import sys
from functools import partial
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "app"))
import components  # noqa: E402

LAB = json.loads((ROOT / "app/lab.json").read_text())
CURRICULUM = json.loads((ROOT / "app/curriculum.json").read_text())
STARTERS_FILE = ROOT / "app/starters.json"
STARTERS = json.loads(STARTERS_FILE.read_text()) if STARTERS_FILE.is_file() else {}
st.set_page_config(page_title=LAB["title"], layout="wide")
components.SESSION_PROMPTS = {
    index: [prompt["id"] for prompt in step["prompts"]] for index, step in enumerate(CURRICULUM, 1)
}


def overview():
    st.title(LAB["title"])
    st.write(LAB["scenario"])
    st.caption(f"{LAB['track_label']} | Cortex Code {LAB['interface_label']} | 60 minutes")
    st.info("All data is synthetic. Read from the shared SOURCE schema; build only in your assigned schema. "
            "Work in this order: Plan, review, approve, execute, validate.")
    with st.container(border=True):
        st.markdown(f"**Your sandbox**  \nDatabase `{LAB['database']}` · schema `{LAB['schema']}` · "
                    f"role `{LAB['role']}` · warehouse `{LAB['warehouse']}`")
        st.caption("Your facilitator may assign a different schema/role number (P001, P002, ...).")
    st.subheader("Agenda")
    elapsed = 0
    for step in CURRICULUM:
        st.write(f"{elapsed:02d}-{elapsed + step['minutes']:02d} min · {step['title']} ({step['mode']})")
        elapsed += step["minutes"]


def interface():
    st.title("Using your interface")
    st.markdown(LAB["interface_notes"])


def admin():
    st.title("Admin setup")
    st.write("For the Snowflake admin, before the lab. Run `admin/setup.sql` one section at a time, "
             "upload the CSVs from the data zip in Section 3, and verify as a participant in Section 7.")
    st.download_button("Download setup.sql", (ROOT / "admin/setup.sql").read_bytes(), file_name="setup.sql",
                       mime="text/plain", icon=":material/download:")
    st.download_button("Download synthetic data", (ROOT / "data" / LAB["zip"]).read_bytes(), file_name=LAB["zip"],
                       mime="application/zip", icon=":material/download:")
    st.markdown(f"**Expected after loading:** {LAB['expected_text']}")
    st.code((ROOT / "admin/setup.sql").read_text(), language="sql")


def exercise(step):
    st.title(step["title"])
    st.caption(f":material/schedule: {step['minutes']} minutes · {step['mode']}")
    components.render_technologies_used(step["technologies"])
    st.space("small")
    st.markdown("#### The situation")
    with st.container(border=True):
        st.markdown(step["situation"])
    st.space("small")
    starters = STARTERS.get(step["id"], [])
    if starters:
        st.markdown("#### Starter files")
        st.caption("Copy or download each file and save it at the path shown, relative to your project folder.")
        for index, starter in enumerate(starters):
            with st.expander(f"{starter['label']} · `{starter['path']}`", icon=":material/description:"):
                st.code(starter["content"], language=starter["language"])
                st.download_button("Download", starter["content"], file_name=starter["path"].rsplit("/", 1)[-1],
                                   icon=":material/download:", key=f"dl-{step['id']}-{index}")
        st.space("small")
    prompts = step["prompts"]
    for number, prompt in enumerate(prompts, 1):
        title = "Try this prompt" if len(prompts) == 1 else f"Prompt {number} of {len(prompts)}"
        components.render_prompt(prompt["id"], title, prompt["text"])
    details = "\n".join(line for line in step["body"].splitlines()
                        if not line.startswith(">") and not re.match(r"(?i)^prompts?\b.*:\s*$", line.strip()))
    if details.strip():
        components.render_explanation("What to expect and how to check it", details)
    for tip in step["tips"]:
        if tip["kind"] == "warning":
            st.warning(tip["text"], icon=":material/warning:")
        else:
            st.info(tip["text"], icon=":material/lightbulb:")
    st.space("small")
    components.render_key_concepts(step["concepts"])
    if step["built"]:
        st.space("small")
        components.render_what_you_built(step["built"])


pages = {"Start here": [st.Page(overview, title="Overview", icon=":material/home:"),
                        st.Page(interface, title="Your interface", url_path="interface", icon=":material/terminal:"),
                        st.Page(admin, title="Admin setup", url_path="admin", icon=":material/settings:")],
         "Lab": []}
for index, step in enumerate(CURRICULUM, 1):
    done = " (done)" if components.is_session_complete(index) else ""
    pages["Lab"].append(st.Page(partial(exercise, step), title=f"{index}. {step['title']}{done}",
                                url_path=step["id"], icon=":material/play_circle:"))
st.navigation(pages, position="sidebar").run()

# customer-coco-hol

A Cortex Code skill that builds customer-specific, one-hour Cortex Code hands-on labs (HOLs) for Snowflake SEs, AEs and AI Platform sellers.

It produces:
- a **public GitHub repo** with a Streamlit lab guide app, a single admin `setup.sql`, synthetic data and starter files;
- **local facilitator materials**: an HTML intro deck and a T−7 / T−3 / T−1 preparation guide;
- tracks for **Data Engineering**, **ML / Data Scientists** and **Analysts**, on Cortex Code Desktop, CLI or Snowsight.

## Install

Clone into a skills directory Cortex Code reads:

```bash
# All projects (user-level)
git clone https://github.com/sfc-gh-mli/customer-coco-hol ~/.snowflake/cortex/skills/customer-coco-hol

# Or one project only
git clone https://github.com/sfc-gh-mli/customer-coco-hol .cortex/skills/customer-coco-hol
```

Start a new Cortex Code session and ask for a customer hands-on lab, for example: "Build a Cortex Code HOL for a retail customer, ML track, in Snowsight."

## Requirements
- The upstream [coco-hol-template](https://github.com/sfc-gh-obenning/coco-hol-template) (the skill reuses its Streamlit components; it uses an installed generate-hol skill or a verified checkout).
- The GitHub CLI (`gh`) signed in to the facilitator's account, if you want the skill to publish the lab repo for you.
- `uv` to run the tests.

## Tests

```bash
HOL_TEST_UPSTREAM=/path/to/coco-hol-template uv run --project . --extra test python -m unittest discover -s tests
```

Tests are offline: they don't connect to Snowflake or write to GitHub.

## Layout
- `SKILL.md`: the workflow Cortex Code follows.
- `references/`: intake, admin prework, facilitator prep, packaging, publishing, and one file per track.
- `scripts/`: package assembly, validation, synthetic data and the GitHub publish helper.
- `assets/`: the app, deck, guide and admin templates, plus SQL/Python starter files.

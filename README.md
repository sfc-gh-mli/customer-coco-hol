# customer-coco-hol

A Cortex Code skill that builds custom, one-hour Cortex Code hands-on labs (HOLs).

## Goal
Help facilitators create a Cortex Code HOL tailored to a specific customer: their industry, their people's role and the Cortex Code interface they use, with a ready-to-run guide app, admin setup and prep checklist.

It's built for two kinds of facilitators:
- **Snowflake field teams** (SEs, AEs, AI Platform sellers) running a lab for a customer.
- **Centers of Excellence (COEs) at customer companies** that want to run these labs for their own teams, without Snowflake in the room. Give them this repo; the skill walks them through the same steps.

## What it asks you
Before generating anything, Cortex Code asks a few rounds of questions (up to four at a time). Answers you've already given are reused, and it never asks for passwords or tokens.

1. **The customer and audience**
   - Customer (organization) name and industry
   - Persona / track: Data Engineering, ML / Data Scientists, or Analysts
   - Account setup: one existing customer account, or individual trial accounts
   - Interface participants will use: Cortex Code Desktop, CLI or Snowsight
2. **The event**
   - Specific topics to cover (or the track's default agenda)
   - The outcome and end-user experience you want: what participants should walk away able to do, and how the hour should feel
   - Participant count
   - Customer account only: a name prefix for new lab objects (default `HOL_`, or their own standard), and the participant role, database and warehouse to use (new, or existing ones in their account). Cleanup only ever lists the objects the lab created.
3. **Publishing**
   - The GitHub account and repo for the participant guide
   - Whether the customer's name may appear publicly (default: no, use a neutral title like "Retail Cortex Code Lab")
   - Hosting: Streamlit Community Cloud, or local only for now
   - Where to save the generated lab

It then shows the lab design for your approval before building the package.

## What it produces
- a **GitHub repo** with a Streamlit lab guide app, a single admin `setup.sql`, synthetic data and starter files;
- **local facilitator materials**: an HTML intro deck and a T−7 / T−3 / T−1 preparation guide;
- tracks for **Data Engineering**, **ML / Data Scientists** and **Analysts**, on Cortex Code Desktop, CLI or Snowsight.

Every lab ends with a **Next steps** discussion: a short set of questions that gets participants thinking about which business problems these capabilities could solve for them, and what they'd need to try it on real work.

**Note for COEs:** the built-in publish step creates a **public** GitHub repo (participants open the guide without signing in). If your company's policy doesn't allow that, choose "local only" hosting and share the generated folder internally instead.

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

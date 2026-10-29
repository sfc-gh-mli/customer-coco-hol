# {{TITLE}}: facilitator guide

Customer: **{{ORGANIZATION}}** · Track: **{{TRACK}}** · Interface: Cortex Code **{{INTERFACE}}** · 60 minutes

**Target outcome / participant experience:** {{OUTCOME}}

This folder stays on your machine. Only `{{REPO_FOLDER}}/` is published.

| What | Where | Who uses it |
|---|---|---|
| Lab guide app (incl. starter files), admin setup, data | `{{REPO_FOLDER}}/` (public GitHub repo) | Customer admin and participants |
| Intro deck (slide 7 is your checklist) | `facilitator/facilitator-intro.html` | You |
| This guide | `facilitator/facilitator-guide.md` | You |
| Config, provenance, test results | `.build/` | The skill (ignore) |

## 1. Preparation checklist

### T−7 days: meet the customer sponsor and Snowflake admin
- [ ] Confirm track, interface, account mode (customer account or trials), participant count and any extra topics.
- [ ] Agree the outcome: what participants should walk away able to do, and what the experience should feel like.
- [ ] Confirm whether the customer's name may appear publicly (repo and app are public).
- [ ] Send the admin the repo link. They run `admin/setup.sql` one section at a time and upload the data zip.
- [ ] Admin repeats Section 5 per participant (one schema and role each) and keeps the user roster private.
- [ ] ML track in Snowsight: admin creates the HOL compute pool in Section 6 (one node per participant, plus one spare) and confirms the account allows notebook workloads on it.
- [ ] Book the T−3 enablement session.

### T−3 days: 1-hour enablement with the admin and a participant
| Minutes | Check |
|---|---|
| 0–10 | Sign in, correct account, interface version, role, warehouse |
| 10–20 | Section 4 counts match the README; Section 7 participant write test passes |
| 20–30 | Plan mode, default approvals, a sample prompt, skill discovery |
| 30–45 | Track smoke test end to end. ML in Snowsight: the participant connects a Workspace notebook to the HOL compute pool and runs the training checkpoint; note the first-connect wait |
| 45–55 | Your demos run; a second participant can't see the first participant's objects |
| 55–60 | Assign owners for blockers; go/no-go |

### T−1 day
- [ ] Blockers fixed or moved to an agreed demo.
- [ ] Final push done; open the public app and click every page and download.
- [ ] Rehearse the full 60 minutes and keep completed checkpoints ready.

### Event day and after
- [ ] Present slides 1–6; check everyone is on their own role and schema.
- [ ] If someone is stuck for more than 2 minutes, use the checkpoint and follow up later.
- [ ] Afterward: share approved materials, pause any demo schedules, agree retention or cleanup with the admin.
- [ ] Delete or make private the Streamlit app and repo if they shouldn't stay public.

## 2. Publish the lab guide to your public GitHub

**Normally Cortex Code does this for you.** Sign in once with `gh auth login`. If you have several accounts, run `gh auth switch --user <owner>` to pick the one that owns the repo. Cortex Code then shows the destination and file list, asks you to approve, and pushes and checks the result. Use the manual steps below only when the agent has no shell, for example in Snowsight.

Run these from **inside `{{REPO_FOLDER}}/` only**. Never push `facilitator/` or `.build/`.

1. Check sign-in: `gh auth status`. If not signed in: `gh auth login`.
2. Create the repo if it doesn't exist:
   `gh repo create {{REPO_OWNER_NAME}} --public --description "Cortex Code hands-on lab (synthetic data)"`
3. Commit and push:
   ```bash
   cd {{REPO_FOLDER}}
   git init -b main
   git add .
   git status            # review: only lab files, no secrets
   git commit -m "Cortex Code hands-on lab"
   git remote add origin {{REPO_URL}}.git
   git push -u origin main
   ```
4. Check: open {{REPO_URL}} and confirm the README, `streamlit_app.py`, `admin/setup.sql` and `data/` are there.

Use only repo-level Git settings. Don't change global Git configuration to work around authentication; fix `gh auth` instead.

## 3. Host the guide on Streamlit Community Cloud (public)

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in **with the GitHub account that owns the repo**. Authorize Streamlit to read your repos when prompted.
2. Select **Create app** and then **Deploy a public app from GitHub**.
3. Fill in:
   - Repository: `{{REPO_OWNER_NAME}}`
   - Branch: `main`
   - Main file path: `streamlit_app.py`
   - App URL: choose a short subdomain, e.g. `{{REPO_FOLDER}}`
4. Under **Advanced settings**, choose Python 3.11 or later. No secrets are needed; leave that box empty.
5. Select **Deploy** and wait for the build to finish.
6. Make sure it's public: open the app's **Settings → Sharing** and confirm "This app is public and searchable" or that anyone with the link can view it.
7. Open the app in a private browser window and click through every page, both downloads and a prompt checkbox.
8. Add the URL to the README (replace the "_facilitator adds the Streamlit URL here_" line), then `git commit -am "Add app link" && git push`. The app redeploys automatically on every push.

**If the build fails:** open **Manage app** (bottom right of the app) to see logs. The usual cause is a missing file that wasn't committed; check `git status`, commit and push again.

**After the event:** from your Streamlit workspace, open the app's menu and select **Delete**, or keep it if the customer wants to reuse it. Make the GitHub repo private or archive it if needed.

## 4. Running the lab
Follow the app pages in order. Slides 1–6 frame the hour; slide 7 is your reminder only. Mark demos clearly as demos, and don't claim anything worked live unless it did.

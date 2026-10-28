# Publish to GitHub and host on Streamlit Community Cloud

Only the public repo folder (`<output>/<repo-slug>/`) is ever published. `facilitator/` and `.build/` stay local. Creating a public repo is outward-facing: every push needs explicit facilitator confirmation in this run, even when publishing was requested at intake.

## 1. Preconditions
- `public.github_repo` is set (`https://github.com/<owner>/<repo>`). If missing, ask for it; never ask for tokens.
- Public naming decision recorded. If `show_customer_name` is false, the customer name must not appear anywhere in the public folder. If `include_facilitator` is true, the repo's `facilitator/` deck and guide are public too.
- Offline validation passes, including the public-safety check:
  ```text
  python3 <skill-dir>/scripts/validate_package.py <output-dir> --report
  ```
  It fails on internal files in the public folder, email addresses, token-like strings, roster markers, or an unapproved customer name. Fix the content; don't weaken the check.

## 2. Confirm, then push
The agent pushes on the facilitator's behalf using their own `gh` sign-in. See [GitHub workflow](github-workflow.md) for prerequisites, account switching, follow-up `--update` commits and pitfalls. The facilitator never runs git commands manually; they sign in once and approve once.

1. **Account check (stopping point).** Run the dry run:
   ```text
   python3 <skill-dir>/scripts/publish_repo.py <output-dir>
   ```
   It re-runs validation, resolves `public.github_repo`, reads the active `gh` account, checks whether the repo exists, and lists the exact files.
   - Not signed in: ask the facilitator to run `! gh auth login` (GitHub.com, HTTPS, browser). Never ask for or handle tokens.
   - `account_matches: false`: show both names. If the right account is already signed in, ask them to run `! gh auth switch --user <owner>`; otherwise `! gh auth login` to add it. Re-run the dry run. Don't run `gh auth setup-git` (it edits global Git config); the helper passes credentials per command instead.
2. **Confirm.** Show the destination URL, `public` visibility, whether the repo will be created, and the file list. Ask with `ask_user_question`: **Push to public repo** / **Not yet**. No approval means stop with "Not pushed".
3. **Push.** After approval only:
   ```text
   python3 <skill-dir>/scripts/publish_repo.py <output-dir> --push --confirm "push <owner>/<repo>"
   ```
   The helper creates the repo with `gh repo create --public` if needed. It refuses non-empty existing repos and existing local history, and checks that the staged files equal the approved list. It pushes `main` without force, compares the remote tree to the list, and records the commit in `.build/generation-manifest.json`.
4. Report the repo URL and commit. Follow-up edits (e.g. adding the app link to the README) are new reviewed commits with their own confirmation.

Manual git steps in `facilitator-guide.md` section 2 are only a fallback when the agent has no shell (for example, Snowsight).

On failure, report the actual error and any partial remote state. Retry at most once after the facilitator fixes auth; never use `--force`.

## 3. Host on Streamlit Community Cloud
Deployment needs the facilitator's browser sign-in, so give them the steps in `facilitator/facilitator-guide.md` section 3:
- Sign in at share.streamlit.io with the repo owner's GitHub.
- Create app → repo, branch `main`, main file `streamlit_app.py`, custom subdomain.
- Deploy, then confirm the app is public under Settings → Sharing.

Then ask for the app URL. Open it with `web_fetch` or the browser tool to confirm it loads and shows the lab title. Only then:
- Record `publish.streamlit_url`.
- Offer to put the link into the README, which needs a second confirmed push.

If the URL doesn't load, report "not yet verified" and point to Manage app → logs.

The app reads only committed files and needs no secrets. Community Cloud runs from the repo root, so `streamlit_app.py`, `requirements.txt`, `.streamlit/config.toml` and `static/` live at the root.

## 4. Local-only option
If hosting is `local-only`, skip sections 2 and 3. Give `streamlit run streamlit_app.py` from inside the public folder and say clearly that nothing was published.

## 5. After the event
Remind the facilitator to delete the Community Cloud app and make the repo private or archive it if it shouldn't stay public. Don't do this automatically.

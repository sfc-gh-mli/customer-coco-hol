# GitHub workflow (bundled)

Adapted from the shared `git-github-workflow` skill (gh CLI authentication, multi-account switching, push pitfalls) for lab publishing. It is bundled here so publishing works without that skill installed. The agent runs `scripts/publish_repo.py`; the facilitator only signs in and approves.

## Prerequisites
- Check that the GitHub CLI is available: `gh --version`. If it's missing on macOS, suggest the facilitator run `! brew install gh`. Don't install it without asking.
- Check that Git is available: `git --version`.
- The agent needs a local shell. In Snowsight there is none, so use the manual steps in `facilitator/facilitator-guide.md` section 2.

## Authentication (facilitator, one time)
- If not signed in, have the facilitator run `! gh auth login`, then choose GitHub.com, HTTPS and browser sign-in.
- To add a second account, for example personal plus work, run `! gh auth login` again. Existing accounts stay signed in.
- `gh auth status` lists the accounts and shows which one is active. The push needs the `repo` scope; publishing GitHub Actions workflows would also need `workflow`.
- Never ask for, paste, print or store tokens. The helper reads the active login through `gh api user`.

## Account selection (stopping point)
The active account must equal the owner in `public.github_repo`. Pushing to an organization the account can write to is also valid, but confirm that with the facilitator first.
- If the account is wrong but already signed in, have the facilitator run `! gh auth switch --user <owner>`, then re-run the dry run.
- If the account isn't signed in, have them run `! gh auth login` to add it.
- Don't run `gh auth setup-git`, because it rewrites global Git config. The helper passes `credential.helper=!gh auth git-credential` and a noreply commit identity on each command, so `~/.gitconfig` stays untouched.

## Commands the helper wraps
| Step | Helper | Underlying commands |
|---|---|---|
| Plan, account check | `publish_repo.py <out>` | `gh api user`, `gh repo view` |
| First publish | `--push --confirm "push <owner>/<repo>"` | `gh repo create --public`, `git init -b main`, `add -A`, `commit`, `remote add`, `push -u origin main`, `gh api …/git/trees/main` |
| Later edits | `--update --message "<msg>" --confirm "update <owner>/<repo>"` | `git status`, `add -A`, `commit`, `push` (fast-forward only) |

The default repo visibility is **private** in the generic workflow, but here it's **public** by design: the customer and the Streamlit Community Cloud app need it. Say so in the confirmation. Commits use a plain message; don't add Co-Authored-By trailers to customer-facing repos unless the facilitator asks.

## Common pitfalls
| Symptom | Cause | Fix |
|---|---|---|
| `Permission … denied to <user>` | Wrong active account | `! gh auth switch --user <owner>`, then retry once |
| `repository already exists` / non-empty repo | Name reused | Pick a new `public.github_repo`, or have the facilitator confirm and push to it as a follow-up update. Never force-push |
| Remote points at the wrong owner | Config changed after the first push | Stop and report. Don't silently run `git remote set-url` |
| Branch `master` | Older Git defaults | The helper always uses `main` (`init -b main`) |
| Rejected push (non-fast-forward) | Someone edited the repo on GitHub | Stop. Show the remote change and let the facilitator decide. Don't force |
| Staged or remote files differ from the approved list | Stray file or `.gitignore` gap | Stop, report the difference, fix it, re-run the dry run |

## Verification
After a push:
- report the repo URL and commit SHA;
- check that the remote file list matches the approved list (the helper does this);
- check that `.build/generation-manifest.json` shows `publish.github = "pushed"`.

Offer `gh repo view <owner>/<repo> --web` to open it.

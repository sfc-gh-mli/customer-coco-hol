"""Push the public lab repo folder to the facilitator's GitHub using their gh CLI sign-in.

Default is a dry run that prints the plan. Pushing requires --push AND the exact confirmation
string the facilitator approved. Only the public folder is pushed; never force-pushes;
uses per-command git credential settings (no global git config changes).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from hol_common import GITHUB_REPO, public_slug, read_json
from validate_package import validate_package

IGNORED_DIRS = {".git", ".venv", "__pycache__"}  # mirrors the generated public .gitignore


def run(args, cwd=None, check=True):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=120)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result


def require_tools():
    import shutil
    missing = [tool for tool in ("gh", "git") if not shutil.which(tool)]
    if missing:
        raise RuntimeError(f"Missing {', '.join(missing)}. On macOS: ! brew install gh git")


def active_login() -> str:
    result = run(["gh", "api", "user", "--jq", ".login"], check=False)
    if result.returncode != 0:
        raise RuntimeError("GitHub CLI is not signed in. Run: ! gh auth login (GitHub.com, HTTPS, browser)")
    return result.stdout.strip()


def git(public: Path, *args, login: str):
    identity = ["-c", f"user.name={login}", "-c", f"user.email={login}@users.noreply.github.com",
                "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]
    return run(["git", "-C", str(public), *identity, *args])


def plan(root: Path) -> dict:
    config = read_json(root / ".build/lab-config.json")
    repo_url = (config.get("public") or {}).get("github_repo")
    if not repo_url or not GITHUB_REPO.fullmatch(repo_url):
        raise RuntimeError("Set public.github_repo to https://github.com/<owner>/<repo> first")
    owner, name = GITHUB_REPO.fullmatch(repo_url).groups()
    public = root / public_slug(config)
    require_tools()
    validation = validate_package(root)
    if validation["status"] != "passed":
        raise RuntimeError(f"Validation failed; fix before publishing: {validation['errors']}")
    login = active_login()
    files = sorted(relative for p in public.rglob("*") if p.is_file()
                   for relative in [p.relative_to(public).as_posix()]
                   if not any(part in IGNORED_DIRS for part in p.relative_to(public).parts)
                   and p.suffix != ".pyc" and p.name != ".DS_Store" and relative != ".streamlit/secrets.toml")
    exists = run(["gh", "repo", "view", f"{owner}/{name}", "--json", "visibility,url"], check=False)
    return {"owner": owner, "repo": name, "url": f"https://github.com/{owner}/{name}", "visibility": "public",
            "active_account": login, "account_matches": login.lower() == owner.lower(),
            "repo_exists": exists.returncode == 0, "public_folder": str(public), "files": files,
            "confirmation": f"{'update' if (public / '.git').is_dir() else 'push'} {owner}/{name}"}


def push(root: Path, details: dict) -> dict:
    if not details["account_matches"]:
        raise RuntimeError(f"Active GitHub account is {details['active_account']}, repo owner is {details['owner']}. "
                           f"Run: ! gh auth switch --user {details['owner']}  (or gh auth login to add it)")
    public, login, slug = Path(details["public_folder"]), details["active_account"], f"{details['owner']}/{details['repo']}"
    if (public / ".git").exists():
        raise RuntimeError("Public folder already has git history; push follow-ups with reviewed commits instead")
    if details["repo_exists"]:
        tree = run(["gh", "api", f"repos/{slug}/contents/", "--jq", "length"], check=False)
        if tree.returncode == 0 and tree.stdout.strip() not in {"", "0"}:
            raise RuntimeError(f"{slug} already has content; refusing to overwrite (no force-push)")
    else:
        run(["gh", "repo", "create", slug, "--public", "--description", "Cortex Code hands-on lab (synthetic data)"])
    git(public, "init", "-b", "main", login=login)
    git(public, "add", "-A", login=login)
    staged = sorted(git(public, "diff", "--cached", "--name-only", login=login).stdout.split())
    if staged != details["files"]:
        raise RuntimeError(f"Staged files differ from approved list: {sorted(set(staged) ^ set(details['files']))}")
    git(public, "commit", "-m", "Cortex Code hands-on lab", login=login)
    git(public, "remote", "add", "origin", f"{details['url']}.git", login=login)
    git(public, "push", "-u", "origin", "main", login=login)
    commit = git(public, "rev-parse", "HEAD", login=login).stdout.strip()
    remote = sorted(run(["gh", "api", f"repos/{slug}/git/trees/main?recursive=1",
                         "--jq", '.tree[] | select(.type=="blob") | .path']).stdout.split())
    if remote != details["files"]:
        raise RuntimeError(f"Remote files differ from approved list: {sorted(set(remote) ^ set(details['files']))}")
    manifest_path = root / ".build/generation-manifest.json"
    manifest = read_json(manifest_path)
    manifest["publish"] = {**manifest.get("publish", {}), "github": "pushed", "repo": details["url"], "commit": commit}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"status": "pushed", "url": details["url"], "commit": commit, "files": len(remote)}


def update(root: Path, details: dict, message: str) -> dict:
    """Commit and fast-forward push reviewed edits to an already published repo."""
    if not details["account_matches"]:
        raise RuntimeError(f"Active GitHub account is {details['active_account']}, repo owner is {details['owner']}. "
                           f"Run: ! gh auth switch --user {details['owner']}")
    public, login = Path(details["public_folder"]), details["active_account"]
    if not (public / ".git").is_dir():
        raise RuntimeError("Not published yet; use --push for the first publish")
    origin = git(public, "remote", "get-url", "origin", login=login).stdout.strip()
    if origin.removesuffix(".git") != details["url"]:
        raise RuntimeError(f"origin is {origin}, expected {details['url']}; not changing remotes automatically")
    git(public, "add", "-A", login=login)
    changed = git(public, "diff", "--cached", "--name-only", login=login).stdout.split()
    if not changed:
        return {"status": "no_changes", "url": details["url"]}
    git(public, "commit", "-m", message, login=login)
    git(public, "push", "origin", "main", login=login)  # fails on non-fast-forward; never forced
    commit = git(public, "rev-parse", "HEAD", login=login).stdout.strip()
    manifest_path = root / ".build/generation-manifest.json"
    manifest = read_json(manifest_path)
    manifest["publish"] = {**manifest.get("publish", {}), "commit": commit}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return {"status": "updated", "url": details["url"], "commit": commit, "changed": sorted(changed)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--update", action="store_true", help="Commit and push reviewed edits after first publish")
    parser.add_argument("--message", default="Update lab guide")
    parser.add_argument("--confirm", help='Exact string from the dry run, e.g. "push owner/repo"')
    args = parser.parse_args()
    try:
        details = plan(args.package.resolve())
        if args.update:
            details["confirmation"] = details["confirmation"].replace("push ", "update ", 1)
        if not (args.push or args.update):
            print(json.dumps({"status": "dry_run", **details}, indent=2))
            return 0
        if args.push and args.update:
            raise RuntimeError("Use --push or --update, not both")
        if args.confirm != details["confirmation"]:
            raise RuntimeError(f'Confirmation must be exactly: "{details["confirmation"]}"')
        result = update(args.package.resolve(), details, args.message) if args.update else push(args.package.resolve(), details)
        print(json.dumps(result, indent=2))
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "not_pushed", "error": str(error)}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())

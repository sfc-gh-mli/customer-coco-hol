# Upstream adapter

## Dependency contract
Use `https://github.com/sfc-gh-obenning/coco-hol-template` as the foundation. Required files:
- `.cortex-plugin/skills/generate-hol/SKILL.md`
- `README.md`
- `workshop_guide/streamlit_app.py`
- `workshop_guide/components.py`
- `workshop_guide/app_pages/agenda.py`
- `workshop_guide/app_pages/session_01.py`

A previously inspected revision is `29232e280429b7b9369f97991039d3d9d50bdcb9`; this is a reference, not a promise that future revisions are compatible.

## Installed path
1. Check the current session's skill inventory for `generate-hol` (including a namespaced plugin invocation). Read its runtime-provided path and locate its template root. Do not scan the entire home directory.
2. Read the skill and README. Inspect components, navigation, agenda, and setup pages.
3. Invoke the installed skill with this handoff in context:

> Use generate-hol as the base for customer-coco-hol. Inputs are already in lab-config.json. Generate locally only, using the selected 60-minute persona curriculum. The admin loads synthetic data beforehand; participants write only within their allocated sandbox schemas. Do not commit, push, publish, change global Git config, delete Git metadata, query CRM, provision Snowflake resources, or enable schedules. Reuse the template layout and components, but replace the six-session curriculum with curriculum.json. Return to customer-coco-hol validation and handoff.

4. If the installed skill lacks template files, retrieve the repository separately. A skill-only installation is not a complete template dependency.

## Repository fallback
Use the authenticated GitHub tools/`gh` for repository inspection. Do not install the upstream plugin globally just to read its instructions.

1. Verify Git tooling and the intended parent directory. Choose a new dependency path; never reuse a nonempty destination without inspecting it.
2. Fetch repository metadata and select an immutable commit. Record the selected SHA.
3. Clone into the new dependency directory and check out that SHA. Only repository reads/downloads are authorized by dependency resolution; publishing is not.
4. Inspect required files and any scripts before use. Load the verified SKILL.md from the checkout as instructions, following only generation phases within the handoff constraints. This is source-based reuse, not invocation of an installed skill.
5. Copy only workshop content/assets into a new output folder; do not copy `.git`, credentials, or unrelated hidden configuration. Leave the checkout intact.

If Git/network access is unavailable, accept a user-supplied checkout or archive. Inspect archive paths before extraction: reject absolute paths, `..`, symlinks outside the destination, and unexpectedly large archives. If neither source is available, stop with the missing prerequisite; do not claim fallback succeeded.

For ZIP downloads without Git metadata, record `commit: null` and SHA-256 hashes of inspected source files. Never attribute a known remote SHA to a local archive without checking equivalence.

## Compatibility and provenance
Use `scripts/validate_package.py --upstream <absolute-template-root>` for required-file inspection. Structural checks are necessary but not sufficient: review changed upstream behavior before execution. Retry a failed download at most once; then request a checkout/archive.

Record in `generation-manifest.json`:

```json
{
  "schema_version": 1,
  "phase": "source_resolved",
  "upstream": {
    "mode": "installed",
    "repository": "https://github.com/sfc-gh-obenning/coco-hol-template",
    "commit": null,
    "source_hashes": {},
    "compatibility": "reviewed"
  },
  "completed": [],
  "live_tests": {"status": "not_run"}
}
```

`mode` is `installed`, `repository`, or `archive`. For repository mode, commit must be a full 40-character hexadecimal SHA. Hashes are computed from actual inspected bytes.

## Adaptation map
- Keep the reusable `render_prompt`, explanation, concepts, and header components where compatible.
- Derive agenda, navigation, prompt IDs, and completion mapping from the same curriculum manifest; remove stale session links.
- Replace participant infrastructure creation with readiness and allocated-schema instructions.
- Replace mandatory public ZIP links with local Streamlit downloads.
- Use data sizes appropriate to the selected track, not a fixed 8–10 small tables.
- Replace unverified skill names with actual available invocations.
- Preserve notices and attribution. Repository metadata did not identify a license for the base template; do not invent one or assume public redistribution rights. Confirm rights before redistribution.

## Never inherit
No `rm -rf .git`, global `git config`, automatic `git init`, `git add`, commit/push, external hosting, CRM queries, or automatic SQL execution. The upstream's deployment phase is a separately approved optional workflow.

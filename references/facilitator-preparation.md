# Facilitator preparation and runbook template

The generated `facilitator/facilitator-guide.md` (from `assets/facilitator-guide.md`) carries this checklist plus the GitHub publish and Streamlit Community Cloud hosting steps; slide 7 of the deck summarizes it. Publishing rules are in [publish and host](publish-and-host.md).

## Responsibilities
- Facilitator (Snowflake): agree outcomes, customize materials, coordinate preparation, run rehearsal, facilitate demos, record blockers and follow up.
- Admin (customer): approve resources/policies, create sandbox, upload/load synthetic data, assign roles, verify privileges, approve retention/cleanup.
- Participants (customer): complete sign-in/setup beforehand; use assigned role/schema, review plans and changes, verify results, raise blockers early.

## T-7 days: sponsor and admin meeting
- [ ] Meet customer sponsor and Snowflake admin one week before the event.
- [ ] Confirm organization, industry, one persona, interface, account mode, expected experience and specific topics.
- [ ] Agree measurable outcomes and the 60-minute agenda; identify demos versus exercises.
- [ ] Confirm cohort count, facilitator, sponsor and admin owners. Keep private contacts outside the public guide.
- [ ] Review region/model policy, trial limits, network/install constraints, authentication, package/runtime availability, CoWork and optional email availability.
- [ ] Deliver the admin pack, synthetic-data ZIP/checksums and private participant-role roster instructions.
- [ ] Admin creates isolated sandbox/warehouse, uploads and verifies data, grants participant roles and feature-specific access.
- [ ] Book the separate T-3 one-hour enablement session; do not send calendar invitations without explicit request.

## T-3 days: one-hour enablement/rehearsal
Schedule and conduct this session three days before the lab; it does not consume the lab's 60 minutes.

| Minutes | Check |
|---|---|
| 0-10 | Sign-in, correct account, interface/version, role and warehouse |
| 10-20 | Admin load reconciliation; participant sample SELECT and sandbox write probe |
| 20-30 | Plan mode, default approvals, skill discovery and a sample prompt |
| 30-45 | Selected track end-to-end smoke test, including optional connector authentication if approved |
| 45-55 | Run short demos; inspect actual reference outputs; test a second participant for collision/isolation |
| 55-60 | Assign blockers, owner and deadline; record go/no-go |

DE: verify plugin/hook/subagent on facilitator's supported local surface; test deny fixtures without touching production. ML: train/register/warehouse-infer, seed historical scoring data and inspect a populated model monitor. Analysts: reconcile semantic tests, exercise the agent in CoWork, preview the report and verify an approved test-email route if selected.

Record each check as passed, failed, not_run or substituted with evidence. A successful admin session is not a successful participant-role test. Do not claim all participants are ready from one administrator's test.

## T-1 day
- [ ] Resolve high-severity blockers; move unready capabilities to explicitly agreed demos or postpone.
- [ ] Freeze config, seed, source revision and package checksum inventory.
- [ ] Test every guide page, local download, HTML deck control, prompt and recovery checkpoint.
- [ ] Prepare completed artifacts for variable training/refresh latency; label them prepared, not live.
- [ ] Rehearse the full 60-minute sequence. Shorten generation complexity if necessary; do not simply promise it fits.
- [ ] Verify the guide contains no credentials, private roster or customer source data.

## Event day
- [ ] Open deck and guide; show selected agenda and responsibility split.
- [ ] Confirm everyone uses the allocated sandbox role/schema.
- [ ] Introduce Plan -> review -> approve -> execute -> validate before the first exercise.
- [ ] Timebox assistance. After two minutes blocked, use the prepared checkpoint and capture the issue for follow-up.
- [ ] Distinguish capabilities shown live from prepared demos and unsupported features.
- [ ] Collect one completed output and one lesson per participant.

## After event
- [ ] Share only approved materials with approved recipients.
- [ ] Pause demonstration schedules and optional compute; admin decides retention/cleanup.
- [ ] Capture feedback, unresolved blockers and next customer use case.
- [ ] Preserve source revision, configuration and validation evidence for reuse.

## Status ledger
Generated runbook must include owners, dates (or TBD), status, evidence and next action for readiness checks. Do not mark checkboxes complete merely because the files were generated.

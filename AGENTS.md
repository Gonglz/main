# Agent Instructions

**Repository Agent Contract:** v1.1

This repository is the shared engineering control plane for conventions used across Gonglz repositories.

## Read order

1. `AGENTS.md`
2. `docs/PROJECT.md`
3. current task / branch / PR state
4. affected repository evidence when cross-repo facts must be verified

## Authority model

Do not use one precedence list for both task intent and current implementation state.

### Task authority — what should change

1. current explicit task / Ticket contract
2. safety and workflow rules in the affected repo's `AGENTS.md`
3. maintained project/subsystem documentation

### Implementation authority — what currently exists

1. current repository code and active configuration
2. executable tests/contracts
3. fresh runtime evidence
4. maintained project documentation
5. audits, closeouts, old plans, and chat history

This repo owns only shared workflow and evidence conventions. Each project repo owns its own architecture, code, tests, production paths, and project-specific rules.

## Change rules

- Do not develop directly on `main` except unavoidable repository bootstrap.
- Use a short-lived branch and PR for substantive changes.
- Keep this repository concise; do not duplicate project-specific documentation here.
- Do not add agents, schemas, automation, or process layers without a demonstrated need.
- Keep development, verification, and production operations separate.
- Never treat green CI as deployment authorization.
- Never commit secrets or raw runtime logs.

## Ticket workspace

The canonical temporary task workspace is:

`docs/_tmp/TICKET_xxx/`

Typical files are `PROMPT.md`, `PLAN.md`, `CHECKPOINT.md`, and `FINDINGS.md`.

At closeout, move only durable knowledge into maintained docs or `docs/audits/`; remove disposable prompts, duplicate analysis, and generated logs.

## Structured evidence interface

Repository Agent Contract v1.1 defines the structured evidence interface, but a project must not claim it is implemented until its runner/workflow actually emits and publishes it.

When structured evidence is implemented, runtime artifacts live outside Git under:

`/var/tmp/<repo>/<run_id>/`

where:

`run_id = <UTC timestamp>_<git short sha>`

A key execution should emit `result.json` with at least:

- `run_id`
- `commit`
- `branch`
- `runner`
- `status`
- `gates`
- `failures`

Consumers read `result.json` first and inspect raw logs only when diagnosis requires them. Raw evidence may be uploaded as GitHub Actions artifacts; commit only durable audit conclusions.

Until a repository wires this interface into CI/runtime, GitHub Checks and logs remain valid evidence, but the repository must not report `result.json` or artifact publication as completed.

## Completion contract

Use these shared top-level completion fields exactly; project-specific gates belong inside the evidence payload rather than by renaming these fields.

```text
CODE_OR_DOCS_COMPLETE
REQUIRED_GATES_PASS
EVIDENCE_AVAILABLE
DOCS_CURRENT
WORKTREE_CLEAN
COMMIT_PUSHED
PR_UPDATED
```

If a required item is not satisfied, report the task as incomplete or blocked rather than `PASS`. If an item is not applicable, say so explicitly.
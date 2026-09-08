# Shared Engineering Loop

Status: **Repository Agent Contract v1**  
Adopted: 2026-09-08

## Purpose

Standardize the development loop used across Gonglz repositories without creating a heavy orchestration layer.

```text
ChatGPT / Codex
      ↓
GitHub Ticket / Branch / PR
      ↓
Local or self-hosted runner
      ↓
Tests / integration / runtime verification
      ↓
/var/tmp/<repo>/<run_id>/
      ├── result.json
      └── raw artifacts
      ↓
GitHub Checks / Actions Artifact / durable audit
      ↓
ChatGPT review
      ↓
next iteration
```

GitHub is the control plane. Chat is an operating interface, not the project state database.

## Repository minimum

Each active repository should normally have only:

```text
AGENTS.md
README.md

docs/
├── PROJECT.md
├── _tmp/        # active ticket workspace when needed
└── audits/      # durable evidence only when worth preserving
```

Do not create extra architecture/process documents until the repository actually needs them.

## Source-of-truth order

1. current code and active configuration
2. repo `AGENTS.md`
3. repo `docs/PROJECT.md`
4. current ticket / task contract
5. current tests and fresh runtime evidence
6. historical audits / closeouts

Project-specific rules stay in the project repository. This repository owns only the common convention.

## Agent workflow

Before work:

- read `AGENTS.md` and `docs/PROJECT.md`
- inspect branch, HEAD, working tree, and relevant current implementation
- verify runtime/production facts instead of guessing them

During work:

- do not develop directly on `main`
- keep one scoped task on one short-lived branch
- make the smallest coherent change
- keep production mutation separate from ordinary development unless explicitly authorized
- never expose secrets in Git, logs, or artifacts

Before completion:

- run required gates
- review the diff
- update durable docs only when facts changed
- produce structured evidence for key executions
- commit, push, and update the PR

A green historical audit is not proof of current correctness.

## Ticket workspace

Temporary task material may live under:

`docs/_tmp/TICKET_xxx/`

Typical files are `PROMPT.md`, `PLAN.md`, `CHECKPOINT.md`, and `FINDINGS.md`.

At closeout:

- promote durable facts into current docs or `docs/audits/`
- remove obsolete prompts, duplicated analysis, and disposable notes
- do not preserve temporary material merely because an agent produced it

## Runtime and evidence

Raw runtime data does not belong in Git.

Use:

`/var/tmp/<repo>/<run_id>/`

with:

`run_id = <UTC timestamp>_<git short sha>`

Example:

`20260908T070500Z_8bcddae`

A key execution should emit `result.json` with at least:

```json
{
  "run_id": "...",
  "commit": "...",
  "branch": "...",
  "runner": "...",
  "status": "PASS|FAIL",
  "gates": {},
  "failures": []
}
```

Consumers read `result.json` first and open raw logs only for diagnosis.

Use GitHub Actions artifacts for retained runtime files. Commit only durable, human-useful audit conclusions to `docs/audits/`.

## What belongs in Git

Keep:

- source code and tests
- configuration templates and migrations
- current project documentation
- durable architecture/operations decisions
- selected audit or closeout evidence

Do not keep by default:

- pytest / Docker / systemd logs
- coverage and build outputs
- traces and debug dumps
- screenshots generated during routine runs
- intermediate datasets
- temporary agent analysis

## Completion contract

A task is complete only when all required items are true:

```text
CODE_OR_DOCS_COMPLETE
REQUIRED_GATES_PASS
EVIDENCE_AVAILABLE
DOCS_CURRENT
WORKTREE_CLEAN
COMMIT_PUSHED
PR_UPDATED
```

If a required item is not satisfied, report the task as incomplete or blocked rather than `PASS`.

## Roles

Do not deploy a multi-agent bureaucracy by default. Keep logical boundaries instead:

- **Builder** — may change code/docs; no implicit production authority.
- **Verifier** — independently validates; should not fix what it is reviewing in the same pass.
- **Operator** — performs explicitly authorized deployment/production changes.

The same ChatGPT/Codex system may perform these roles at different stages as long as the permission boundary is explicit.

## Initial adopters

Repository Agent Contract v1 is already adopted by:

- `Gonglz/Quant-v2`
- `Gonglz/obsidian_repo`
- `Gonglz/pi-console`
- `Gonglz/media-ingest`

Future repositories should copy the convention, then add only the project-specific rules they actually need.

# Shared Engineering Loop

Status: **Repository Agent Contract v1.2**  
Adopted: 2026-09-18

## Purpose

Standardize the development loop used across Gonglz repositories without creating a heavy orchestration layer.

```text
Chat
  ↓ intent / approval
GitHub Ticket / Branch / PR
  ↓
Local or self-hosted runner
  ↓
/var/tmp/<repo>/<run_id>/
  ├── status.json      # mutable current state
  ├── result.json      # terminal evidence
  └── raw artifacts
  ↓
GitHub state / local notification
  ↓
Chat review only when needed
```

GitHub is the control plane. Chat is an operating and decision interface, not the project state database and not the long-running executor.

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

Additional development/index/subsystem documents are optional and should exist only when the repository actually needs them.

## Authority model

Do not collapse task intent and current implementation state into one source-of-truth list.

### Task authority — what should change

1. current explicit task / Ticket contract
2. safety and workflow rules in the affected repo's `AGENTS.md`
3. maintained project/subsystem documentation

A Ticket defines the requested goal, scope, constraints, required evidence, and completion criteria. It is not proof of current implementation state.

### Implementation authority — what currently exists

1. current repository code and active configuration
2. executable tests/contracts
3. fresh runtime evidence
4. maintained project documentation
5. audits, closeouts, old plans, and chat history

A historical green audit is not proof of current correctness. Old plans/specs must be reconciled against current code, tests, and runtime evidence before use.

Project-specific rules stay in the project repository. This repository owns only the common convention.

## Agent workflow

Before work:

- read the affected repo's `AGENTS.md` and `docs/PROJECT.md` when present
- read the current Ticket/task contract
- inspect branch, HEAD, working tree, and relevant current implementation
- verify runtime/production facts instead of guessing them

During work:

- do not develop directly on `main`
- keep one scoped task on one short-lived branch
- make the smallest coherent change
- add/update tests for behavior changes
- use targeted tests while iterating and full required gates before closeout
- keep production mutation separate from ordinary development unless explicitly authorized
- never expose secrets in Git, logs, or artifacts

Before completion:

- run required gates
- review the diff
- update durable docs only when facts changed
- produce the required evidence available for that repository
- commit, push, and update the PR

## Ticket workspace

The canonical temporary task workspace is:

`docs/_tmp/TICKET_xxx/`

Typical files are:

```text
PROMPT.md
PLAN.md
CHECKPOINT.md
FINDINGS.md
```

At closeout:

- promote durable facts into current docs or `docs/audits/`
- remove obsolete prompts, duplicated analysis, and disposable notes
- do not preserve temporary material merely because an agent produced it

Do not use the legacy single-file pattern `docs/_tmp/TICKET_xxx_PROMPT.md` for new work.

## Runtime and evidence

Raw runtime data does not belong in Git.

The shared structured-evidence interface is:

`/var/tmp/<repo>/<run_id>/`

with:

`run_id = <UTC timestamp>_<git short sha>`

Example:

`20260908T070500Z_8bcddae`

While a run is active, it may maintain:

```json
{
  "run_id": "...",
  "state": "RUNNING",
  "phase": "...",
  "progress": {"completed": 47, "total": 120},
  "updated_at": "...",
  "needs_user": false,
  "message": "..."
}
```

A task that needs judgment changes to `WAITING_APPROVAL`; ordinary execution must not depend on the user sending "continue".

When the run terminates, emit:

```json
{
  "run_id": "...",
  "commit": "...",
  "branch": "...",
  "runner": "...",
  "status": "PASS|FAIL|BLOCKED|CANCELLED",
  "gates": {},
  "failures": []
}
```

Read `status.json` for current progress and `result.json` for terminal evidence. Open raw logs only for diagnosis.

### Async execution and notification

Use a durable runner for work that can continue without judgment. Chat may start or inspect the run, but the run must survive the chat ending.

Notify only on useful state transitions by default:

- `WAITING_APPROVAL`
- `BLOCKED`
- `PASS`
- `FAIL`

GitHub comments/status are the durable human-visible channel. A local OS notification may be emitted in parallel for immediacy. Notification delivery does not replace `status.json` or `result.json`.

A minimal reference implementation lives at `scripts/async_harness.py`. Invoke it from the target repo/worktree so Git metadata is captured correctly. Its interface is intentionally limited to `start`, `set`, `run`, and `status`; projects do not need to copy or extend it unless a real requirement appears.

### Implementation status rule

This contract defines the interface; it does not imply every adopting repository already emits `result.json` or uploads artifacts.

A repository may claim structured evidence is implemented only when its actual workflow/runner emits and publishes that evidence. Until then, GitHub Checks and logs are still valid evidence sources, but the task must not claim `result.json` or artifact publication occurred.

Use GitHub Actions artifacts for retained runtime files. Commit only durable, human-useful audit conclusions to `docs/audits/`.

### Retention

`/var/tmp/<repo>/<run_id>/` is disposable runtime state.

Default policy:

- successful runs may be deleted after required structured evidence/artifacts are published
- failed runs may be retained temporarily for diagnosis
- host-side runtime directories should have a bounded TTL; **7 days** is the default
- a project may override the TTL only when its own operational requirements document a reason

Do not build a custom log-management service just for this contract; use the host's normal cleanup mechanism where possible.

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

These shared top-level completion fields are fixed across repositories:

```text
CODE_OR_DOCS_COMPLETE
REQUIRED_GATES_PASS
EVIDENCE_AVAILABLE
DOCS_CURRENT
WORKTREE_CLEAN
COMMIT_PUSHED
PR_UPDATED
```

Project-specific checks belong under the repository's gates/evidence model, for example:

```json
{
  "gates": {
    "python_tests": "PASS",
    "frontend_build": "PASS"
  }
}
```

Do not rename or add competing top-level completion fields for project-specific checks.

If a required item is not satisfied, report the task as incomplete or blocked rather than `PASS`. If an item is not applicable, say so explicitly.

## Roles

Do not deploy a multi-agent bureaucracy by default. Keep logical boundaries instead:

- **Builder** — may change code/docs; no implicit production authority.
- **Verifier** — independently validates; should not fix what it is reviewing in the same pass.
- **Operator** — performs explicitly authorized deployment/production changes.

The same ChatGPT/Codex system may perform these roles at different stages as long as the permission boundary is explicit.

## Adoption

Repositories known to use the Repository Agent Contract v1 family include:

- `Gonglz/Quant-v2`
- `Gonglz/obsidian_repo`
- `Gonglz/pi-console`
- `Gonglz/media-ingest`

Individual repositories adopt a newer contract explicitly; changes in this repository do not silently alter project-local rules. This `Gonglz/main` repository is the bootstrap authority for the current shared contract version.
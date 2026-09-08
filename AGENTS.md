# Agent Instructions

This repository is the shared engineering control plane for conventions used across Gonglz repositories.

## Read order

1. `AGENTS.md`
2. `docs/PROJECT.md`
3. current task / branch / PR state
4. affected repository evidence when cross-repo facts must be verified

## Source of truth

- This repo owns only shared workflow and evidence conventions.
- Each project repo owns its own architecture, code, tests, production paths, and project-specific rules.
- Chat transcripts are not project state.
- Historical audits are evidence, not current implementation authority.

## Change rules

- Do not develop directly on `main` except unavoidable repository bootstrap.
- Use a short-lived branch and PR for substantive changes.
- Keep this repository concise; do not duplicate project-specific documentation here.
- Do not add agents, schemas, automation, or process layers without a demonstrated need.
- Never commit secrets or raw runtime logs.

## Shared runtime contract

Runtime artifacts live outside Git under:

`/var/tmp/<repo>/<run_id>/`

where:

`run_id = <UTC timestamp>_<git short sha>`

Key executions should emit a machine-readable `result.json`. Raw logs are inspected only when needed and may be uploaded as GitHub Actions artifacts.

## Completion

A task may report complete only when its required code/docs, validation gates, evidence, commit/push, and PR state are all current and internally consistent.

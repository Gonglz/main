# Chat Task Prompt

Use this as the lightweight entry prompt for ChatGPT/Codex when starting repository work.

The prompt should carry only the new task intent. Repository state belongs in GitHub, not in chat.

## Level 0 — discussion

Use normal language. No template is required for questions, architecture discussion, review, prioritization, or exploration.

Examples:

```text
Quant-v2 现在还缺什么？
这个架构有没有问题？
下一步做什么？
```

## Level 1 — normal development task

Use this for most coding/documentation tasks:

```text
Repository: Gonglz/<repo>

Goal:
<what should be completed>

Scope:
<main subsystem / feature / boundary>

Constraints:
- Read AGENTS.md and docs/PROJECT.md first.
- Treat the current task as task authority.
- Treat current code, tests, active config, and fresh runtime evidence as implementation authority.
- Do not modify production unless explicitly authorized.
- Work on a short-lived branch and PR.
- Use the repository's existing validation workflow and iterate on failures until the applicable gates pass.

Expected result:
<what should be true when the task is complete>
```

Only include constraints that are new or task-specific. Do not copy project state, architecture, runner details, test commands, or historical context into chat when the repository already owns them.

## Level 2 — repository Ticket task

Use this for large, cross-session, high-risk, production, migration, or multi-machine work.

The chat prompt should stay short:

```text
Repository: Gonglz/<repo>
Task: TICKET_<id>

The authoritative task specification is:
docs/_tmp/TICKET_<id>/PROMPT.md

Read AGENTS.md and docs/PROJECT.md first.
Execute the Ticket exactly, verify current implementation/runtime facts instead of relying on chat history, and update the branch/PR until the applicable gates pass.
```

The detailed goal, scope, exclusions, safety constraints, acceptance gates, production authorization, evidence requirements, and closeout instructions belong in the Ticket workspace, not duplicated in chat.

## Rule of thumb

```text
Chat = new intent
Repository = current project state
Ticket = detailed task contract
GitHub Actions / runtime evidence = execution state
```

Do not maintain two authoritative copies of the same task specification in chat and GitHub.

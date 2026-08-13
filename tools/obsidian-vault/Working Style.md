---
type: working-style
tags: [project, workflow]
updated: 2026-08-13
---

# Working style

- Keep project notes in Russian when the conversation is in Russian; retain code identifiers, paths, and commands exactly.
- Read the shared `AGENTS.md` template and the relevant project-local skill before changing code or infrastructure.
- Keep backend boundaries explicit, use async HTTP handlers, and verify changes with the narrowest applicable checks.
- Treat deployment placeholders as shapes only; never place real credentials in the repository or in task output.
- Do not start Obsidian; maintain the vault with ordinary filesystem operations.

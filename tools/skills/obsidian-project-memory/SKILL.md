---
name: obsidian-project-memory
description: Maintain durable, project-scoped context in an Obsidian vault. Use at the beginning and end of every Codex task performed in a filesystem project or repository, including new-project setup, implementation, debugging, reviews, architecture work, deployment, decisions, credentials discovery, and follow-up tracking. Resolve or create the project's memory vault automatically so the user does not need to repeat context in each chat.
---

# Obsidian Project Memory

Keep one separate Obsidian vault per project and treat it as the project's long-term memory. Use ordinary filesystem operations; Obsidian or an Obsidian MCP server may be present but is not required.

## Start every project task

1. Determine the canonical project root. Prefer the Git top-level directory; otherwise use the active workspace root.
2. Run the bundled bootstrap utility before substantive work:

   ```bash
   python3 <skill-dir>/scripts/project_memory.py bootstrap --project-root <project-root>
   ```

   Pass `--master-vault <path>` when the user has a cross-project master vault that is not configured yet. Pass `--vault <path>` only when the project must use a non-default vault.
3. Read the paths returned under `read_first` in order. Read `Architecture/_Overview.md` and relevant notes under `Knowledge/`, `Initiatives/`, and `End-to-End Flows/` when the task touches those areas.
4. Inspect `Knowledge/Open-Tails.md`. Briefly remind the user about open `HIGH`, `P-high`, or equivalent urgent items without blocking unrelated work.
5. If the task spans projects, personal goals, or organization-wide context, also read the configured master vault's `Home.md` and relevant project cards. Do not load the master vault for routine single-project work.

The script stores machine-local mappings in `~/.codex/obsidian-project-memory/config.json` by default. Never include that config in a shared skill package.

## Resolve or create a vault

Use this precedence:

1. Explicit `--vault` path.
2. Exact project-root mapping in the machine-local config.
3. A vault inside the project root, when the root itself contains `.obsidian/`.
4. A sibling directory named `<project-name>-memory`.
5. Create that sibling directory and register it.

Never attach a project to a nearby vault merely because it exists. A vault belonging to a sibling project is unrelated unless an explicit mapping says otherwise.

The bootstrap utility creates only missing scaffold files and directories. Preserve existing notes and user edits.

## Record memory while working

Write notes in the user's conversation language unless project instructions specify another language. Keep code, identifiers, commands, and technical terms in their original language.

- Add actions, results, and decisions to today's `Daily/YYYY-MM-DD.md`.
- Update an existing `Knowledge/` or `Initiatives/` note for stable operational knowledge, root causes, unusual semantics, access procedures, timezone/order pitfalls, or infrastructure quirks.
- Put feature audits in `Knowledge/Audits/<module>-YYYY-MM-DD.md`.
- Add discovered defects or unfinished work to `Knowledge/Open-Tails.md`; close resolved rows and add a short commit SHA when one exists.
- Update `Architecture/` for code or system-boundary changes. Add or update an `Initiatives/` card for a new feature.
- Record an implementation before a commit if necessary, then append the short SHA after the commit succeeds.
- Search for an existing relevant note before creating a new one. Avoid duplicate notes and breadcrumb links.

Read [references/vault-conventions.md](references/vault-conventions.md) before creating a non-scaffold note or changing the vault structure.

## Handle secrets

Store discovered or user-provided project credentials only under `<vault>/Secrets/`, never in the repository or shared skill. Maintain `Secrets/_Index.md` plus focused notes such as `Servers & SSH.md`, `Database & Supabase.md`, and `API Keys & Tokens.md` as needed.

Before asking the user for project access, inspect the relevant `Secrets/` notes. Do not echo secret values in commentary, final responses, logs, commits, or master-vault project cards.

If a secret is found in tracked code or Git history, record the exposure in `Secrets/` and `Knowledge/Security TODOs.md`, mark it for rotation, and do not commit it again.

## Finish the task

Before replying:

1. Update today's Daily note with the verified outcome.
2. Update stable knowledge, architecture, initiatives, open tails, and secrets when the work produced those categories of information.
3. If a commit was created, add its short SHA to the Daily entry and any closed tail.
4. Keep vault changes out of the project repository unless the vault intentionally is the repository.
5. Summarize only material memory changes in the final response.

Do not turn a read-only explanation or review into unrelated repository changes merely to populate memory. Recording diagnostic findings in the separate vault remains in scope.

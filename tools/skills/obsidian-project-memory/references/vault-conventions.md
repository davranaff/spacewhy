# Vault conventions

## Required layout

```text
<vault>/
├── .obsidian/
│   ├── daily-notes.json
│   └── templates.json
├── Architecture/
│   └── _Overview.md
├── Daily/
├── End-to-End Flows/
├── Initiatives/
├── Knowledge/
│   └── Open-Tails.md
├── Secrets/
│   └── _Index.md
├── Templates/
│   └── Daily.md
├── Home.md
└── Working Style.md
```

## Frontmatter

Every note must begin with YAML frontmatter containing `type`, `tags`, and `updated`. Daily notes also contain `date`.

```yaml
---
type: knowledge
tags: [project, operations]
updated: 2026-08-13
---
```

Use ISO dates (`YYYY-MM-DD`). Update `updated` whenever making a material edit.

## Note routing

| Information | Destination |
|---|---|
| Today's work and verification | `Daily/YYYY-MM-DD.md` |
| System structure and boundaries | `Architecture/` |
| Feature state, scope, and decisions | `Initiatives/` |
| Stable facts, root causes, runbooks | `Knowledge/` |
| Cross-component behavior | `End-to-End Flows/` |
| Bugs and unfinished work | `Knowledge/Open-Tails.md` |
| Credentials and access details | `Secrets/` |

Use wiki links only for meaningful relationships. Index notes should link to child notes; child notes should not contain decorative “back” breadcrumbs.

## Open tails

Use a table with at least priority, status, item, and owner. Treat `HIGH`, `P-high`, `critical`, and repository-equivalent labels as urgent. Never silently delete a tail: mark it closed and include evidence such as a commit SHA, deployment, test result, or decision.

## Master vault

A master vault is optional and contains cross-project context, usually `Projects/`, `Life/`, `Knowledge/`, and `Daily/`. Keep credentials out of it. For a newly registered project, create or update `Projects/<project-name>.md` and link the project vault path; update the master index only when its existing format can be preserved safely.

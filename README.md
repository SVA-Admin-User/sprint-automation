# GitHub Sprint Automation

This repository runs GitHub Actions that automate your `svatechsystems` organization Project/Kanban board.

## What this version does

1. **Sprint start**: creates GitHub issues from `config/sprint-config.yml`, assigns users from a GitHub team, adds issues to the organization Project, and sets status to **Backlog**.
2. **Board sync**: runs on a cron schedule and moves project items automatically:
   - linked open PR -> **In Progress**
   - linked merged PR or closed issue -> **Done**
3. **Sprint end**: creates a markdown report and optionally moves unfinished work to **Backlog**.

Because this workflow is running from `SVA-Admin-User/sprint-automation`, it cannot receive live PR events from all other repos unless those repos also have workflows. So this package uses **scheduled polling** through `board-sync.yml`. That is the right setup for your current repo structure.

## Required repository secret

Add this in `SVA-Admin-User/sprint-automation`:

`Settings -> Secrets and variables -> Actions -> New repository secret`

```text
GH_AUTOMATION_TOKEN=<your fine-grained PAT>
```

## Edit before first run

Edit these two files:

```text
config/settings.yml
config/sprint-config.yml
```

Required edits:

```text
project_number: <number from https://github.com/orgs/svatechsystems/projects/<number>>
team_slug: <your GitHub team slug>
repo: <repository under svatechsystems where issues should be created>
```

Your board status values are already configured as:

```text
Backlog
In Progress
Done
```

## Workflows

| Workflow | Purpose |
|---|---|
| `validate-token.yml` | Confirms token can access org, team, and Project. Run this first. |
| `sprint-start.yml` | Creates sprint issues, assigns users, adds to Project, sets Backlog. |
| `board-sync.yml` | Cron polling that moves items to In Progress or Done. |
| `sprint-end.yml` | Generates sprint report and carryover handling. |

## Required PR convention

For automation to move work correctly, engineers must link PRs to issues.

Use PR body like:

```text
Closes #123
```

or link the PR from the issue/project manually.

## Suggested first test

1. Upload these files to `SVA-Admin-User/sprint-automation`.
2. Edit `config/settings.yml`.
3. Edit `config/sprint-config.yml` with one test story only.
4. Run **Validate Token** manually.
5. Run **Sprint Start Automation** manually.
6. Confirm the issue appears in the Kanban Board as **Backlog**.
7. Open/link a PR to the issue.
8. Run **Board Sync** manually.
9. Confirm it moves to **In Progress**.
10. Merge the PR or close the issue.
11. Run **Board Sync** again.
12. Confirm it moves to **Done**.

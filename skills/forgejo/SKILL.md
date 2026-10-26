---
name: forgejo
description: The team's Forgejo forge, where pull requests are opened, reviewed, checked by Actions and merged. Use whenever work touches a pull request, a CI run or its logs, commit statuses, repo variables or secrets on the Forgejo instance, and when the user asks about a PR, a run, or why CI is red.
---

# Forgejo forge

Talk to it only through `fjo`. The plugin puts it on the Bash tool's PATH;
outside Claude Code it is `${CLAUDE_PLUGIN_ROOT}/bin/fjo`. Never curl the
API with the token on the command line, and never dump raw JSON into the
conversation: `fjo` prints one line per pull request, run, job or status
and that is all the context a session needs. `--json` exists where a
script needs the whole record.

`fjo` finds the repository from the git remote of the current directory
that points at the instance (`origin` first); `-R OWNER/REPO` names any
other.

## Routine for a change

1. Push the branch, then `fjo pr open -t "title" -b @body.md`. The title
   follows the repo's PR title rules (conventional-commit style where
   commitlint runs); the body says what changed, how it was verified and
   which card it closes. Write a long body to a file and pass `@path`
   rather than quoting it in the command line.
2. `fjo pr checks N --wait` (or `fjo ci --wait` on the pushed commit)
   blocks until no context is pending and exits non-zero when CI is not
   green. When it is red: `fjo log RUN` prints the failed jobs' error
   lines and tail (RUN is the number in the status line and the web URL;
   `fjo log RUN JOB` picks one job, `--all` the whole log).
3. `fjo pr show N` before acting on a PR: meta, body, CI state, then the
   comments and reviews in order, clipped (`--full` for whole ones).
   `fjo pr ls` is the open PRs with their CI and review state.
4. Respond on the PR, not in chat: `fjo pr comment N @note.md`, or a
   review (`fjo pr review N --approve|--request-changes -b @review.md
   --commit SHA`). Reviewing your own PR is not a review.
5. Merge with `fjo pr merge N --head SHA`, SHA being the head you
   reviewed: it refuses when the branch moved or when CI is pending or
   red (`--force` only on the user's explicit word), squashes by default
   with the PR title as the subject, and deletes the branch. Branch
   protection still decides who may merge.
6. CI on main after the merge: `fjo ci main` (or `fjo runs --event push
   -n 3`). `fjo dispatch ci.yml` re-runs a workflow by hand when a push
   run must be repeated.

## Commands

```
fjo pr ls [-s open|closed|all] [-n N] [--base B] [--author U] [--brief]   PRs with ci and review state
fjo pr show N... [--full]                       meta, body, ci, comments and reviews in order
fjo pr files N | fjo pr diff N [--patch]        what changed
fjo pr checks N [--wait]                        commit statuses of the head (= fjo ci #N)
fjo pr open -t TITLE [-b BODY] [--head BR] [--base B] [-a USER]
fjo pr edit N [-t TITLE] [-b BODY] [--base B]
fjo pr close N | fjo pr reopen N
fjo pr comment N TEXT
fjo pr review N [--approve|--request-changes] [-b BODY] [--commit SHA]
fjo pr merge N [--head SHA] [--method squash|merge|rebase|rebase-merge|fast-forward-only] [--title T] [--message M] [--keep-branch] [--force]
fjo ci [SHA|BRANCH|#N] [--wait] [--interval S] [--timeout S]   combined status, one line per context
fjo runs [-n N] [--pr N] [--sha S] [--status S] [--event E] [--workflow F]   Actions runs, newest first
fjo jobs RUN                                    jobs of a run
fjo log RUN [JOB] [-n LINES] [--all] [--raw]    failed jobs' error lines and tail (or one job)
fjo dispatch WORKFLOW [--ref BR] [-i k=v]       workflow_dispatch
fjo repo | fjo branches | fjo branch rm NAME...
fjo vars | fjo var set NAME VALUE | fjo var rm NAME
fjo secrets | fjo secret set NAME (value on stdin or --from-file) | fjo secret rm NAME
fjo api METHOD PATH [BODY]                      anything else under /api/v1
fjo whoami
```

BODY and TEXT are literal text, `-` for stdin, or `@path` for a file.
RUN is the run number the web UI shows (`id:N` for the API id). Pull
requests are `N` or `#N`. Every command takes `-R OWNER/REPO`.

## Rules

- **Nothing about the instance in a repo that mirrors to a public
  forge**: no internal hostnames, no quoted internal error text, in PR
  titles, bodies, comments or workflow files. The mirror keeps every
  revision.
- **Secrets never touch the command line.** `fjo secret set NAME` reads
  the value from stdin or `--from-file`; `fjo init` reads the token the
  same way. Tokens live in `~/.config/forgejo/` (0600), never in a repo.
- **A merge is the human's call** unless the repo's rules say otherwise:
  CI green and a review that approves are the preconditions `fjo pr merge`
  checks, not the permission.
- **Repo-specific protocol** (who reviews, how rounds are announced, what
  a PR body must contain) lives in that repo's AGENTS.md, which overrides
  these defaults. Read it before opening or merging there.
- `fjo ci` reads commit statuses, which is what branch protection reads;
  a job without a task yet shows as a pending context, so "no job
  running" is not "the run is done". `--wait` handles that.

## Permissions

These subcommands only read: `fjo pr ls`, `fjo pr show`, `fjo pr files`,
`fjo pr diff`, `fjo pr checks`, `fjo ci`, `fjo runs`, `fjo jobs`, `fjo
log`, `fjo repo`, `fjo branches`, `fjo vars`, `fjo secrets` (names only),
`fjo whoami`. They are safe to allow-list in Claude Code settings so they
run without a prompt:

```
Bash(fjo pr ls:*)  Bash(fjo pr show:*)  Bash(fjo pr files:*)  Bash(fjo pr diff:*)
Bash(fjo pr checks:*)  Bash(fjo ci:*)  Bash(fjo runs:*)  Bash(fjo jobs:*)
Bash(fjo log:*)  Bash(fjo repo:*)  Bash(fjo branches:*)  Bash(fjo vars:*)
Bash(fjo secrets)  Bash(fjo whoami)
```

Everything else writes and keeps asking. `fjo api` is not allow-listed
even for GET: its path is free text.

## Setup on a new machine

Install the plugin (the repo is its own marketplace):

```
claude plugin marketplace add MaybloomTech/forgejo-skill
claude plugin install forgejo@forgejo-skill
```

Make an API token for the account the agent acts as (Settings →
Applications → Generate token; scopes: read/write repository, read user,
read/write issue for PR comments, plus notification if wanted), one per
machine, named after the host. Then store it without putting it in argv:

```
fjo init --url https://git.example.org --token-file /path/to/token    # or: ... < token-file
```

`FORGEJO_URL`, `FORGEJO_TOKEN` and `FORGEJO_REPO` override the files.

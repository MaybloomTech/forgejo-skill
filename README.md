# forgejo-skill

A Claude Code plugin for a team's [Forgejo](https://forgejo.org) forge,
and the marketplace that serves it:

```
.claude-plugin/marketplace.json   this repo as a one-plugin marketplace
.claude-plugin/plugin.json        the plugin, `forgejo`
skills/forgejo/SKILL.md           when and how an agent uses the forge
bin/fjo                           the client; on the Bash tool's PATH while the plugin is enabled
tests/                            offline unit tests for the client's parsing and formatting
```

`fjo` is a small Forgejo client that prints one line per pull request,
run, job or commit status, so a session spends a few dozen tokens on the
forge instead of pages of JSON. Python standard library only; Forgejo API
v1, tested on 16.0. One HTTPS connection per run. It is the sibling of
[vikunja-skill](https://github.com/MaybloomTech/vikunja-skill)'s `vk`.

What it covers, and why a client of its own rather than `tea` or an MCP
server: pull requests with their CI and review state on one line, the
conversation of a PR in order with comments clipped, commit statuses with
`--wait`, Actions runs and jobs, the **job logs** (error lines first,
then the tail) that the web UI otherwise holds alone, merges that refuse
when the branch moved or CI is not green, repo variables and secrets with
the values kept off the command line, and a raw `api` passthrough for the
rest. The token comes from a file or the environment, never from argv,
and the read-only subcommands are listed in the skill so they can be
allow-listed in Claude Code settings.

## Install

```
claude plugin marketplace add MaybloomTech/forgejo-skill
claude plugin install forgejo@forgejo-skill
```

(or `/plugin marketplace add …` and `/plugin install …` inside a session).
The skill shows up as `forgejo:forgejo`.

Then point the machine at the instance:

1. Sign in to Forgejo as the account the agent will act as, Settings →
   Applications → Generate token, named after the machine. Scopes:
   repository (read and write), user (read), issue (read and write, for
   PR comments). Add notification if the account should read its inbox.
2. `fjo init --url https://git.example.org --token-file PATH` (or pipe
   the token on stdin), from a Claude Code session (`! fjo init …`) or as
   `bin/fjo` from a checkout. It stores both in `~/.config/forgejo/`
   (`token` is 0600) and prints the account and how many repos it sees.

The token never goes in a repo. One token per machine, so a lost laptop
is one token to revoke. `FORGEJO_URL`, `FORGEJO_TOKEN` and `FORGEJO_REPO`
override the files.

To type `fjo` in an ordinary shell, clone the repo anywhere and
`ln -s <checkout>/bin/fjo ~/.local/bin/fjo`.

## Forgejo 16 notes the client works around

- `GET /repos/{o}/{r}/actions/jobs/{id}/logs` works when `id` is a **job**
  id from `/actions/runs/{run}/jobs`; a task id from `/actions/tasks`
  gets 404. The run id in the API is not the number in the web URL;
  `fjo` takes the web number and resolves it with `?run_number=`.
- `/actions/runs` and `/actions/tasks` ignore `limit` unless `page` is
  sent too.
- Older runs may answer 500 for a job log whose files were cleaned up;
  `fjo log` says so per job and goes on.

## Update

`plugin.json` carries no `version` on purpose: every commit on `main` is a
release.

```
claude plugin marketplace update forgejo-skill
claude plugin update forgejo@forgejo-skill
```

Changes go through a PR here; `SKILL.md` documents every command, so keep
it in step with `fjo`. `python3 -m unittest discover -s tests` runs the
offline tests, `claude plugin validate .` checks the manifests, and
`claude --plugin-dir .` tries a working copy without installing it.

## License

Apache-2.0; see `LICENSE` and `NOTICE`. Security reports: `SECURITY.md`.

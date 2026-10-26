# Security

## Reporting a vulnerability

Two private channels, both reaching the same person:

- **GitHub** — open the **Security** tab on this repository and choose
  **Report a vulnerability**. This opens a private advisory.
- **Email** — **hello@maybloom.tech**, if you would rather not use GitHub
  or do not have an account.

Please do not open a public issue for a suspected vulnerability. Expect an
acknowledgement within a week: this is a small project with one
maintainer.

## What the attack surface is

This repository ships one Python script and a skill document that tells a
coding agent when to run it. The script holds an API token with write
access to a forge, so the findings we care about are:

- **The token leaking**: into a command line, a log, a repo, or a request
  to a host other than the configured instance. `fjo init` and `fjo
  secret set` read values from stdin or a file for this reason.
- **A read-only subcommand that writes.** The skill lists the subcommands
  that only read so they can be allow-listed; one of them reaching a
  write endpoint is a vulnerability.
- **Untrusted content steering the agent.** PR bodies, comments and job
  logs come from other people and are printed for the agent to read. The
  client clips and labels them; a path where it executes or interprets
  them is a finding.

## Out of scope

The Forgejo instance itself, and vulnerabilities in Forgejo or Python
that have already been published; report those upstream.

# Contact Brief

Portable, standalone evidence compiler and agent workflow for one professional contact. Produces cited Markdown, `contact-brief.v1` JSON and an optional unsent draft. In Codex, email discovery can route through the host's Exa plugin without a user-managed API key. **Offline implementation is usable; full live acceptance is NOT RUN.**

## Install locally

Python 3.10+; one dependency, jsonschema. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Use `.venv/bin/python` in place of `python3` below if needed. Windows: `.venv\Scripts\python.exe`. Nothing installs into Hermes profiles or Jobsss.

## Codex Exa plugin route

When running in Codex, inspect the available tool catalog by capability and description for an Exa web-search tool. Current names may include `mcp__codex_apps__exa_web_search_exa` and `mcp__codex_apps__exa_web_fetch_exa`; a compatible alias is fine. The host agent calls the tool directly after native LinkedIn/X identity resolution, asks for at most one attributable professional email, and records a private normalized handoff. No `EXA_API_KEY` is needed for this route. The Python code cannot call an MCP tool itself.

Prerequisites: the Exa plugin must be connected and callable in the Codex host, and a usable native LinkedIn/X browser session must be available for identity and activity checks.

Use the handoff schema and example in [references/exa-plugin-result.md](references/exa-plugin-result.md), then import it into a build request:

```sh
python3 scripts/contact_brief.py import-exa request.json --result private/exa-plugin-result.json --out private/request-with-email.json
python3 scripts/contact_brief.py build private/request-with-email.json --out out/contact
python3 scripts/contact_brief.py validate out/contact.json
```

The importer checks the exact name/company, permits zero or one address, requires source records for a non-null address, marks it `provider_reported`, and leaves the mailbox `not_checked`. Keep the original handoff as the provider record. It does not assert a plugin cost cap, duplicate-prevention journal or mailbox verification.

## Deterministic offline demo

```sh
python3 scripts/contact_brief.py build examples/offline-request.json --out out/demo --now 2026-09-08T12:00:00Z
python3 scripts/contact_brief.py validate out/demo.json
python3 -m unittest discover -s tests -v
```

Read `out/demo.md` and `out/demo.json`. All example identity/activity/candidate content is explicitly fictional; URLs are illustrative, not fetched. The demo includes a sourced-shaped fixture and draft, but leaves native coverage `not_attempted`, mailbox `not_checked`, and acceptance false. Repeating the fixed-time command produces identical output. Omit `--now` for the actual compilation timestamp (it never changes evidence retrieval/publication dates).

Minimal input is `{"name":"...","company":"..."}`. Optional keys are `identity`, `email`, `coverage`, `signals`, `candidate_facts`; their shapes are defined in the output schema. The compiler supplies missing sections, deduplicates signal URLs, retains at most three signals and composes a draft only when identity is matched and candidate facts plus authored signals exist. Unknown extra request fields are not research inputs and are not retained. Optional role/profile/context should be captured as inspected evidence or candidate facts, not assumed to trigger searches.

`validate` applies JSON Schema AND Python cross-field checks: evidence is mandatory for matched identity and source-supported email; contradictory mailbox claims and forged recorded acceptance are rejected. Schema-only validators do not implement every semantic check. The compiler cannot verify truth of quotes, author identity or supplied observations; the agent must inspect sources.

## Provider and evidence commands

```sh
python3 scripts/live_test.py preflight
python3 scripts/live_test.py verify --brief out/demo.json --evidence-root evidence
```

Both should exit 2 on the demo: live acceptance is unpassed. `preflight` performs zero calls. `verify` only checks supplied files/records, reports `evidence_complete` separately, always returns `passed: false` and `live_execution: not_verified`, and makes zero network calls. Even perfect supplied fixtures cannot attest browser execution.

### Direct Agent API fallback

Use this only when no callable Codex Exa plugin is available, after preparing a private authorization JSON and budget:

```sh
python3 scripts/live_test.py exa --authorization private/authorization.json --journal private/exa-run.json --execute
```

The direct Agent API subcommand finds ONE professional email only, using fixed low effort (documented estimate $0.045 with one email; $0.05 request allowance, not a provider hard cap). It does not research profiles/posts or verify mailboxes. No automatic higher-effort retry; reuse the same journal to prevent duplicate dispatch. Skip Exa when an address is already sourced. It is not the end-to-end workflow, and its budget/journal rules do not apply to the Codex plugin route. No example authorization grants permission. See [providers](references/providers.md) for input shape, guardrails and limitations.

## Optional real AfterShip adapter

Go 1.22+ is needed only to build this adapter. Use an existing Go toolchain; do not install globally. From the project root:

```sh
export GOMODCACHE="$PWD/.cache/gomod" GOCACHE="$PWD/.cache/go-build"
(cd adapters/aftership && go mod download && go test -v ./... && go vet ./... && go build -o ../../bin/contact-brief-aftership .)
```

Dependencies download only during setup. The offline compiler does not need Go. On Windows build an `.exe` and pass its path with `--adapter`.

Only after explicit address-scoped authorization, put the approved address and approval fields in a private JSON file (see [providers](references/providers.md)):

```sh
python3 scripts/contact_brief.py verify-email private/email-authorization.json --execute --out private/mailbox-result.json
# SMTP requires separate authorization covering recipient/catch-all probing:
python3 scripts/contact_brief.py verify-email private/email-authorization.json --execute --smtp --timeout 20 --out private/mailbox-result.json
```

Without `--smtp`, this is syntax/DNS checking, NOT mailbox verification. Even SMTP acceptance does not prove identity or delivery. Missing adapter and timeout produce unknown/exit 2. Output contains raw evidence and a schema-compatible `mailbox` object; attribution is separate and manual. Browser research remains host-driven SKILL.md work, not executable Python search.

## Contents and boundaries
- [SKILL.md](SKILL.md): actionable native LinkedIn/X research and evidence discipline.
- `scripts/contact_brief.py`: offline compiler, renderer and semantic validation.
- `scripts/cb_providers.py`: opt-in journaled Exa transport; optional AfterShip subprocess execution and conservative normalization.
- `scripts/live_test.py`: no-call preflight, opt-in Exa execution and supplied-evidence audit.
- [Schemas](references/contact-brief.schema.json), [Exa plugin handoff](references/exa-plugin-result.md), [Jobsss handoff](references/jobsss.md), [verification](VERIFICATION.md).

Not implemented: autonomous browser orchestration, direct MCP invocation from Python, automatic conversion of raw tool output without a host-normalized handoff, or Jobsss import. These remain agent/manual boundaries. The real optional AfterShip library was exercised on invalid syntax with no DNS, and DNS/SMTP outcomes were tested with mocks. No paid calls, external mailbox probes, native session tests, real contact mutation, sending, cron or profile installation were performed. Jobsss integration is documentation against inspected MCP source, not an exercised integration.

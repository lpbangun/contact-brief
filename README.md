# Contact Brief

Portable, standalone evidence compiler and agent workflow for one professional contact. Produces cited Markdown, `contact-brief.v1` JSON and an optional unsent draft. The current host workflow selects people with Treg + Jev and finds emails with Treg. The old direct Exa/Fiber email lookup has been removed. **Offline implementation is usable; full live acceptance is NOT RUN.**

This remains a **single-person compiler**. A fixed list or multi-person Fiber run belongs in a separate host bridge: the host owns scheduling, bounded concurrency/spend, resumable journaling and raw provider records, then imports one normalized result per person. This package does not discover people, call Fiber, or send outreach.

## Local checkout setup

Python 3.10+; one dependency, jsonschema. From this directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Use `.venv/bin/python` in place of `python3` below if needed. Windows: `.venv\Scripts\python.exe`. The compiler installs nothing into Hermes profiles or Jobsss; the optional Agent Plugin package below installs only through the host's own plugin command. For an installed skill, follow the first-run section in SKILL.md: resolve TOOL_ROOT from the active skill path and put any virtual environment or outputs in an external writable RUN_DIR.

## Hermes Agent Plugin package

The repository root is a portable **Agent Plugins v1** package that Hermes can validate and install through its plugin manager:

- `plugin.json` — the Agent Plugins v1 manifest (`name`, `version`, `description`, `license`, `keywords`). No other top-level field is declared, because the portable reader ignores unknown fields.
- `skills/contact-brief/SKILL.md` — the installable skill surface. Its body is byte-identical to [SKILL.md](SKILL.md); only the frontmatter differs, flattened into the string-only `metadata` map Agent Plugins v1 requires. An offline test enforces that equality, so the installed skill cannot drift from the canonical procedure.
- `routes.json` — machine-readable provider-route metadata (`contact-brief-routes/v1`). It declares three routes: archived `codex_exa_plugin` and `exa_agent_fiber` importers, plus `aftership_mailbox_check`, plus fixed inputs, single-subject limits, approval requirements, spend/attempt visibility, miss statuses, redaction rules and the capabilities this package never has.
- No `mcp.json`: this package exposes no MCP server. Compilation is performed by the bundled CLI through the host terminal, consistent with the boundary below. Route and evidence metadata is what a host adapter reads.

```sh
# install (installs disabled; enable explicitly)
hermes plugins install <git-url-or-owner/repo>
hermes plugins enable contact-brief

# validate and exercise the real runtime contracts in an isolated HERMES_HOME
hermes plugins validate . --json
hermes plugins doctor . --ci
```

The CLI has no persistent database and never writes into the installed package. Use an external writable run directory. The smoke test copies the package into a throwaway HERMES_HOME, runs Hermes validate/doctor/enable/list without network or provider calls, and confirms the enabled plugin record. This CLI-only check does not prove that a live model prompt received the skill. On the Hermes CLI checked for this release, hermes skills list does not enumerate portable Agent Plugin skills. The offline packaging checks are python3 -m unittest tests.test_plugin_package and python3 -m unittest tests.test_installed_skill; python3 -m unittest tests.test_plugin_smoke skips with a reason if Hermes CLI is absent. Installing the package grants no discovery, browser, social, messaging or sending capability.

## Archived provider imports

The `import-exa` and `import-fiber` commands parse previously recorded results for compatibility. They do not perform email lookup. For new runs, use the Treg + Jev host companion in People Finder and retain the Treg recording privately.

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

### Current email lookup

Run the Treg + Jev host companion in the People Finder plugin; its `treg_email.py` finds emails only after Jev ranks the candidates. Keep the provider recording private and import vetted evidence into Contact Brief. `scripts/live_test.py` is an offline evidence checker and has no paid provider command.

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
- `scripts/cb_providers.py`: optional AfterShip subprocess execution and conservative normalization.
- `scripts/live_test.py`: no-call preflight and supplied-evidence audit.
- `plugin.json` + `skills/contact-brief/SKILL.md`: portable Agent Plugin packaging and its installable skill surface.
- `routes.json`: provider-route metadata, approval and boundary declarations checked by the offline packaging tests.
- [Schemas](references/contact-brief.schema.json), [Exa plugin handoff](references/exa-plugin-result.md), [Fiber Agent handoff](references/fiber-agent-result.schema.json), [Jobsss handoff](references/jobsss.md), [verification](VERIFICATION.md).

Not implemented: autonomous browser orchestration, direct MCP invocation from Python, automatic conversion of raw tool output without a host-normalized handoff, or Jobsss import. A bundled MCP server is also deliberately absent: the package registers a skill surface only, and the compiler is invoked through the host terminal. These remain agent/manual boundaries. The real optional AfterShip library was exercised on invalid syntax with no DNS, and DNS/SMTP outcomes were tested with mocks. No paid calls, external mailbox probes, native session tests, real contact mutation, sending, cron, network install or production-profile change were performed. Jobsss integration is documentation against inspected MCP source, not an exercised integration.

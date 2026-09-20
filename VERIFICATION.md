# Verification

Run the offline suite:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/contact_brief.py build examples/offline-request.json --out out/demo
python3 scripts/contact_brief.py validate out/demo.json
```

The suite includes the offline Codex Exa plugin handoff importer and the Fiber Agent importer. It validates exact subject binding, zero/one address handling, source preservation and the `provider_reported`/`not_checked` boundary without calling MCP or the network.

Packaging checks:

```sh
python3 -m unittest tests.test_plugin_package   # manifest, skill surface, route metadata, boundaries
python3 -m unittest tests.test_plugin_smoke     # real hermes plugins validate/doctor in a throwaway HOME
```

`test_plugin_package` is fully offline and always runs: it re-derives the Agent Plugins v1 constraints the Hermes portable reader enforces, proves the installable skill body is the canonical skill body, resolves every route command and schema reference in `routes.json`, and checks the declared boundaries, redaction rules and capability flags. `test_plugin_smoke` copies the package into an isolated `HERMES_HOME`, runs the real `hermes plugins validate`/`doctor`, includes a corrupted-package negative control, and skips with an explicit reason when the CLI is not installed.

For the optional Go adapter:

```sh
cd adapters/aftership
go test ./...
go vet ./...
go build -o ../../bin/contact-brief-aftership .
```

The local Python suite contains 44 tests (one skips when the optional Go adapter is not built, three skip when the hermes CLI is absent). Exa transport, the plugin handoff boundary and SMTP outcomes are mocked; the adapter test uses invalid syntax when a built binary is available. Go tests use a blocked DNS resolver. The packaging smoke check exercises the real plugin-validation and registration contracts in an isolated host home. These tests do not prove live email delivery, native social access or MCP tool execution.

Live research requires authorized credentials and targets. Catch-all remains unverified; SMTP acceptance is not a delivery guarantee. Native LinkedIn/X execution and Jobsss integration must be assessed separately. Private contact records, provider receipts and credentials are intentionally excluded from this repository.

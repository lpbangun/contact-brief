# Verification

Run the offline suite:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/contact_brief.py build examples/offline-request.json --out out/demo
python3 scripts/contact_brief.py validate out/demo.json
```

The suite includes the offline Codex Exa plugin handoff importer. It validates exact subject binding, zero/one address handling, source preservation and the `provider_reported`/`not_checked` boundary without calling MCP or the network.

For the optional Go adapter:

```sh
cd adapters/aftership
go test ./...
go vet ./...
go build -o ../../bin/contact-brief-aftership .
```

The local Python suite contains 18 tests. Exa transport, the plugin handoff boundary and SMTP outcomes are mocked; the adapter test uses invalid syntax when a built binary is available. Go tests use a blocked DNS resolver. These tests do not prove live email delivery, native social access or MCP tool execution.

Live research requires authorized credentials and targets. Catch-all remains unverified; SMTP acceptance is not a delivery guarantee. Native LinkedIn/X execution and Jobsss integration must be assessed separately. Private contact records, provider receipts and credentials are intentionally excluded from this repository.

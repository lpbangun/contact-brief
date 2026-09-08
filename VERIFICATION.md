# Verification

Run the offline suite:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/contact_brief.py build examples/offline-request.json --out out/demo
python3 scripts/contact_brief.py validate out/demo.json
```

For the optional Go adapter:

```sh
cd adapters/aftership
go test ./...
go vet ./...
go build -o ../../bin/contact-brief-aftership .
```

The local Python suite contains 12 tests. Exa transport and SMTP outcomes are mocked; the adapter test uses invalid syntax when a built binary is available. Go tests use a blocked DNS resolver. These tests do not prove live email delivery or native social access.

Live research requires authorized credentials and targets. Catch-all remains unverified; SMTP acceptance is not a delivery guarantee. Native LinkedIn/X execution and Jobsss integration must be assessed separately. Private contact records, provider receipts and credentials are intentionally excluded from this repository.

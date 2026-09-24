# Verification

Run the offline suite from the repository root:

~~~sh
python3 -m unittest discover -s tests -v
python3 scripts/contact_brief.py build examples/offline-request.json --out out/demo
python3 scripts/contact_brief.py validate out/demo.json
~~~

The suite includes the offline Codex Exa plugin handoff importer and Fiber Agent importer. It validates exact subject binding, zero/one address handling, source preservation and the provider_reported/not_checked boundary without calling MCP or the network.

Packaging checks:

~~~sh
python3 -m unittest tests.test_plugin_package
python3 -m unittest tests.test_installed_skill
python3 -m unittest tests.test_plugin_smoke
~~~

The plugin package tests enforce the Agent Plugins v1 manifest, skill surface, route metadata, boundaries and schema references. The installed-skill test copies clean portable and Codex-flattened layouts, invokes the offline build and validate commands from an unrelated working directory, and confirms that output files stay outside the installed package.

The Hermes smoke test copies the package into a throwaway HOME and HERMES_HOME, runs the real validate, doctor, enable and list commands, and includes a corrupted-package negative control. It skips with an explicit reason when Hermes is not installed. These local commands make no network or provider calls. Hermes enablement does not prove that a live model prompt received the skill. In the Hermes CLI inspected for this release, hermes skills list does not enumerate portable Agent Plugin skills.

For the optional Go adapter:

~~~sh
cd adapters/aftership
go test ./...
go vet ./...
go build -o ../../bin/contact-brief-aftership .
~~~

The Python suite exercises Exa transport, plugin handoff and SMTP outcomes with mocks. If a built adapter is available, its optional test uses invalid syntax; Go tests use a blocked DNS resolver. The tests do not prove live email delivery, native social access or MCP tool execution.

For the optional live-evidence checker, use only supplied artifacts:

~~~sh
python3 scripts/live_test.py preflight
python3 scripts/live_test.py verify --brief out/demo.json --evidence-root evidence
~~~

Preflight makes zero network calls. Verify checks supplied-file presence and record completeness only, always leaves live execution unverified, and cannot attest browser or paid-provider execution. Native LinkedIn/X work, authorized provider calls, mailbox checks and JobSSS integration must be assessed separately. Private contact records, provider receipts and credentials are intentionally excluded from this repository.

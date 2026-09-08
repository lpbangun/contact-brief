# Provider boundaries

## Exa

Implementation: `scripts/cb_providers.py:exa_run` and `exa_http`. Reviewed API material is retained under `evidence/exa-{overview,create,get}.md`; consult https://docs.exa.ai before authorizing real spend because provider prices/contracts can change.

Authorization shape (illustrative, not permission):

```json
{"approved":true,"name":"APPROVED PERSON","company":"APPROVED COMPANY","max_total_usd":0.05}
```

Host-managed environment: `EXA_API_KEY`; never embed or print it. `live_test.py exa` requires `--execute` and `--journal`. Exa is ONLY for finding one professional email for an already identified person, plus email-attribution sources. No social/profile discovery, activity research, dossiers or mailbox verification. Fixed `effort: low` only; auto and upgrades are rejected. The approved request allowance must be $0.045–$0.05: documented low request price $0.025 plus one $0.02 email. This is an estimate/dispatch gate, NOT a provider-enforced hard billing cap. No automatic retry, escalation or second lookup after a miss. Reuse the SAME journal for a person/request; a new journal can create another paid run, so this is not a global daily budget. If an address is already sourced, skip Exa and use the separately authorized AfterShip check. Report actual provider costs.

Transport: one `POST https://api.exa.ai/agent/runs`, then bounded `GET /agent/runs/{id}` polling (default 12, five-second intervals; 30-second HTTP timeout). Request asks for one professional identity/email with sources, ambiguity and stale-employer notes. There is no automatic POST retry. A persistent exclusive journal records uncertain dispatch before POST. Resume with identical authorization and the SAME journal. Do not delete uncertain journals: reconcile with the provider/operator. Poll exhaustion does not cancel a provider run or prove no further charges. Review pending jobs manually. No cancellation helper is included.

Keep raw run output/grounding in private evidence. Inspect source claims before manually mapping them into compiler identity/email sections. No automatic provider-output compiler adapter exists. Provider-reported attribution, independently inspected source support, and SMTP acceptance are different claims.

Tests inject a fake transport and fixture key; they verify local request/journal logic only. A separate read-only credential probe returned HTTP 200 from `GET /agent/runs?limit=1`; see `evidence/exa-access-check.json`. This proves authenticated Agent API access, NOT successful contact enrichment, sufficient paid credits, mailbox verification or a completed research run. No research POST or cost has been verified.

### Single-person enrichment guidance

Use the Agent API for one known person; Websets is better suited to persistent lists/batch enrichment. Resolve employer and confirmed profile first, then request at most one professional email using an explicit `format: email` schema field. Preserve `output.grounding`, nulls, ambiguity and the returned usage/cost fields; do not equate schema completion with factual identity or deliverability. The helper now enforces fixed `low` effort only. Identity and social research belong to native LinkedIn/X and non-Exa host tools; Exa receives only the already established name/company for email finding. Current official documentation is https://exa.ai/docs/reference/agent-api/overview and the create-a-run API schema (fresh snapshots in `evidence/exa-current-*.md`). The documented $1 minimum applies to auto/max budget caps, not every Exa lookup. Email enrichment is separately listed at $0.02 per email; review actual returned costs rather than assuming the local reserved allowance proves billing enforcement. Keep independent AfterShip mailbox checks separate from Exa's person/address attribution. Load the authorized credential into the process environment using the host's private mechanism; the helper does not automatically load dotenv files.

## Native LinkedIn and X

Execution belongs to the agent using existing host browser tools, not these scripts. Discover the correct existing session through host metadata; do not recreate, overwrite or steal unrelated sessions. Reported LinkedIn login and previously reported X identity are not current session checks. Stop on login/challenge/access denial. Never expose cookies or bypass access controls.

For EACH platform: execute person search, inspect a matched profile, search accessible authored activity, inspect activity. Use LinkedIn's native search and profile activity surface; on X use person/handle search and `from:confirmed_handle`. Record exact queries, actual URLs and timestamps, outcome, plus redacted saved artifacts. Native-domain URLs in supplied JSON are only structural checks, not proof these actions occurred. Exa search is fallback discovery, never native-search acceptance.

Coverage enums distinguish `complete`, `partial`, `blocked`, `not_attempted`, `no_results`, `inactive`. Publication dates may be null. Relevant signals must be authored by the resolved professional, not comments about them or arbitrary search snippets.

## AfterShip (optional executable adapter)

`adapters/aftership/main.go` imports the real MIT `github.com/AfterShip/email-verifier v1.4.1`, pinned by go.mod/go.sum (tag commit `aa8f77c0586ed2ecf9c20cb221de09282ce75355`). No verifier engine is copied. Upstream license is retained in `adapters/aftership/AFTERSHIP-LICENSE`. Reviewed local main source is newer than this pinned release; production uses the downloaded release, not a local replace directive. Stock upstream API server does not enable SMTP.

Build instructions are in README. `scripts/cb_providers.py:aftership_run` launches the trusted local binary with JSON over stdin, preserving raw result, actual completion time, method and conservative mailbox status. The adapter calls `NewVerifier().Verify(address)`. DNS is possible even with SMTP disabled. No Gravatar, disposable-list auto-update or API vendor checks are enabled.

Authorization file: `{"approved":true,"address":"EXACT APPROVED ADDRESS","smtp_approved":false}`. This example is not permission. Both DNS and SMTP require exact address approval and CLI `--execute`; SMTP additionally requires `smtp_approved: true` and `--smtp`. SMTP explicitly enables catch-all checking, including a random recipient at the approved domain. Approval must cover that behavior. No message DATA is sent. Do not guess addresses or treat authorization as identity attribution.

Default total adapter deadline is 20 seconds, configurable with `--timeout` in (0,60]. Connect and operation timeouts are also bounded. The library lacks context cancellation: the standalone process exits on its deadline; Python enforces a further process timeout one second later. Timeout/blocked/error, missing binary and malformed result => unknown, CLI exit 2. Exit 0 only means an error-free check, not accepted delivery. Raw library error text is reduced to a code to avoid accidental sensitive output. Raw results may contain the address: store them privately.

MX is not mailbox proof. Catch-all/full inbox => risky; incomplete/timeout => unknown; explicit SMTP recipient-acceptance flags => smtp_accepted, never delivered or identity verified. Rejections not conclusively classified by upstream remain unknown. Manually copy only the returned `mailbox` into the request email section; preserve independently inspected address attribution/evidence. The CLI does not mutate a brief or discover an email.

Local verification exercised the actual library with invalid syntax (no DNS) and a DNS-blocking mock. Python tests mock SMTP acceptance, missing binary, process timeout and malformed envelopes. External SMTP and successful DNS exchanges are NOT tested here; do not represent these tests as a live mailbox check.

## Evidence audit

`live_test.py verify` checks supplied records and existence/containment of nonempty evidence paths, subject consistency of a supplied Exa journal, grounding presence, and draft presence. It does not inspect screenshots, attest log authenticity or execute a browser/verifier. `evidence_complete` concerns only recorded completeness; `passed` remains false and `live_execution` is `not_verified` by design. Full live acceptance needs a separately reviewed real action transcript on both platforms plus authorized provider execution. No such transcript exists in this checkout.

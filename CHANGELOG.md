# Changelog

## Unreleased

### Hermes Agent Plugin packaging

- Added a portable Agent Plugins v1 `plugin.json` so the repository root installs and is discovered through the host's own plugin command.
- Added the installable skill surface `skills/contact-brief/SKILL.md`: byte-identical body to `SKILL.md`, frontmatter flattened into the string-only `metadata` map v1 requires, with an offline test enforcing that the two cannot drift.
- Added `routes.json` (`contact-brief-routes/v1`): machine-readable route metadata for `codex_exa_plugin`, `exa_agent_fiber`, `direct_exa_agent_api` and `aftership_mailbox_check` covering fixed inputs, single-subject limits, explicit approval, spend/attempt visibility, miss statuses, redaction and the capabilities the package never has.
- Added offline packaging tests plus a host install smoke check that runs the real `hermes plugins validate`/`doctor` against the package in a throwaway HOME and HERMES_HOME, with a corrupted-package negative control.
- No MCP server, browser, social, messaging or sending surface was added; the packaging layer contains no forked compiler logic.

### Fiber Agent handoff and batch boundary

- Added the `fiber-agent-result.schema.json` and offline `import-fiber` boundary for host-normalized Exa Agent/Fiber results.
- Preserved provider-reported attribution, run metadata, retrieval time, actual `usage`/`cost` objects and scalar totals, and empty source URL lists without promoting them to source-supported or mailbox-verified claims.
- Added conservative handling for uncertain candidates and non-success statuses, plus explicit documentation that fixed-list scheduling, journaling, spend caps and raw provider retention belong to a host-owned bridge.
- Clarified that the bundled direct Agent API allowance is a legacy single-person helper contract, not universal Fiber pricing.

### Codex Exa plugin routing

- Added a no-key Codex route for one-person email enrichment through a callable Exa web-search/fetch tool.
- Added the offline `import-exa` boundary and normalized handoff schema. It preserves source records, exact subject binding and the distinction between `provider_reported`, `source_supported` and mailbox verification.
- Kept direct Exa Agent API execution as an explicit, authorized fallback with its existing low-effort allowance and journal rules.
- Added offline importer tests; the full Python suite now contains 18 tests. No live MCP, Exa, LinkedIn/X or SMTP execution is implied.

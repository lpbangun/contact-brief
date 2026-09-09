# Changelog

## Unreleased

### Codex Exa plugin routing

- Added a no-key Codex route for one-person email enrichment through a callable Exa web-search/fetch tool.
- Added the offline `import-exa` boundary and normalized handoff schema. It preserves source records, exact subject binding and the distinction between `provider_reported`, `source_supported` and mailbox verification.
- Kept direct Exa Agent API execution as an explicit, authorized fallback with its existing low-effort allowance and journal rules.
- Added offline importer tests; the full Python suite now contains 18 tests. No live MCP, Exa, LinkedIn/X or SMTP execution is implied.

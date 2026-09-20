# Changelog

## Unreleased

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

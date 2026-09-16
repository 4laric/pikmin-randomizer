# Integration staging sweep — lane 01 / #437

Implementation owner: Codex through shared account 4laric. Baseline root f748bdf; native f14c6851473ac1161be56c8b98f4f905232f3635, clean. This pass changes root staging only; no native build or export needed.

Integrated b2beccc as dfffcd6: BombSarai extractor, three deterministic runtime scenario profiles, and Fuefuki room-overlay layering. The current overlay remains responsible for starting Pikmin. Added a regression proving layering preserves the 20 squad records and treasure and rejects colliding IDs without modifying the file. Focused staging suite: 32 passed. Both new modules import against the current draft. No retail extraction or real-GL run performed; native build evidence remains pinned to sweep #456.

Before any next runtime acceptance: regenerate a fresh private arena, verify live starting Pikmin and centred 960x540 startup, and record every adoption field from PIKMIN2_IMPLEMENTATION_FANOUT.md. Source preservation is not observed runtime adoption.

## Concrete next handoffs and queue

- Lane 01: review native shared provider/consumer bundles from lanes 10-12 (root f4f5d6c), then family consumers. Do not overwrite the engine from an older export.
- Lanes 07-09: handoff 9741d7f describes historical divergent native lines; re-pin against draft native f14c6851 and identify only still-missing lifetime/clock/specular deltas. Current draft already has material/Queen and upstream renderer integration. Do not follow the old whole-line export recommendation blindly.
- Lane 26/27: reconcile Long Legs FSM candidate 4b42718 / 7d0c884 against current lifecycle and projectile ownership hooks.
- Lanes 31/32: review Waterwraith 4231771 and Titan a5427a9 as separate encounter slices with exact native provenance and fixture adoption evidence.
- Species lane: 404a2e4 and follow-up 3cde259 remain queued with broader species dependencies. The ElecBug test change explicitly stops requiring runtime RECOVER because the fixture exits early; this does not establish recovery acceptance.
- Lanes 22/23: 980dc6f and 0880cca remain candidates, not integrated natural-combat claims.

These are integration dispositions, not reassignment of active workers. No direct terminal-agent control performed. Draft #432 remains review-only; no upstream writes or main merge.

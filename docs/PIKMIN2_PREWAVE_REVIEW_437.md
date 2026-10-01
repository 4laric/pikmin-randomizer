# Pre-wave integration review (#437)

Implementation owner: Codex through shared 4laric. Baseline root e3832a2; native f14c6851473ac1161be56c8b98f4f905232f3635, clean and unchanged. No new remote tips since the preceding sweep; this pass reviews queued handoffs.

Integrated diagnostic root slices: 0880cca (Candypop harness, candidate policy header and tests) as 6bc432c; 980dc6f (fixed-hazard harness and tests) as 115ade3. These do not install their native actors into engine/. Corrected false-success test returns to explicit skips, removed implicit access to another worker's Hiba header, and forced standard 960x540 for Candypop launches. Focused flora/elemental/harness suite: 100 passed, 1 skipped (Hiba native header unavailable). Candypop candidate policy compiled and executed. No production rebuild/export or real-GL run; previous production evidence remains pinned to #456.

## Next-wave actions

1. Lane 23: fix native a582a4c5 before integration. spawnSprouts uses bound.colour, which is -1 for Queen and falls back to Blue; it must preserve the source-selected cycling colour. Swallowed Pikmin are killed before birth capacity is known; failed itemMgr births silently continue and swallowed count is cleared. Provide conservation/retry or refund evidence under exhausted item capacity. The root harness is available; the actor remains unintegrated. Inspect reset/scene teardown and simulation-time handling in the same handoff.
2. Lane 22: submit the exact native Hiba delta against f14c6851 with current receiver dependencies. Current integrated harness alone cannot run its actor. Distinguish predicted log gates from observed runtime passes and retain blocked gas/electric application where applicable.
3. Lane 01: next native priority is shared lanes 10-12 provider/consumer reconciliation (f4f5d6c), then Long Legs 4b42718/7d0c884 and separate Waterwraith/Titan encounters 4231771/a5427a9. No wholesale worker export. Species 404a2e4/3cde259 remains queued with dependencies.
4. All active lanes: retain 01-33 ownership numbers, start from latest origin/codex/p2-main-review plus native f14c6851 or a later approved pair. Refresh the current overlay, regenerate a NEW arena, and record observed live Pikmin plus centred 960x540 before runtime acceptance. Candypop's explicitly injected 10-red diagnostic squad is a documented override, not evidence of default 20-red adoption. No runtime adoption PASS claimed here.

See PIKMIN2_NEXT_WAVE.md for the generated-session cohort outcome and PIKMIN2_IMPLEMENTATION_FANOUT.md for required adoption fields. The broad enemy set is not admitted. Existing worker runtime evidence remains pinned to worker builds. Main/upstream unchanged.

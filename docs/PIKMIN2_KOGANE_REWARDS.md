# Reward beetle finite drops and restart dedupe (lane 17, #168/#219)

Lane 17 consumer of the lane-06 reward/receipt contract (#441). New host module
`experimental/pikmin2_kogane_rewards.py` with `tests/test_pikmin2_kogane_rewards.py`
(8 passing), the cave model `experimental/pikmin2_kogane_cave.py` with
`tests/test_pikmin2_kogane_cave.py`, the re-entry fixture
`experimental/pikmin2_kogane_reentry.py` with `tests/test_pikmin2_kogane_reentry.py`,
and an additive native re-entry dedupe in `native/pc_port/pc_p2_kogane.cpp`. No
native save or shared build is modified.

## What is modelled

- **Source table.** `flip_drop()` resolves the audited per-flip drop through
  `experimental.pikmin2_kogane_cave.resolve_flip()`, which in turn calls
  `experimental.pikmin2_kogane_assets.drop_for()` (Koganemushi/Wealthy/Fart
  `enemyParms` and drop code), including the surface/cave branch and the
  spicy/bitter demo-flag fallback. The P1 host has no spray item, so the
  documented nectar fallback is the host resolution.
- **Cave treasure override.** A cave beetle carrying a treasure
  (`mPelletDropCode`) drops that treasure instead of the table on the first flip;
  later flips fall back to the table. `carried_treasure` is accepted by
  `flip_drop()` and `BeetleFlips.register()`.
- **Finite counts.** `BeetleFlips.register()` refuses a flip beyond
  `MAX_FLIPS == 3`; the source escapes (burrows away) rather than dropping again,
  so a beetle can never be farmed indefinitely.
- **Restart dedupe.** Each distinct `(seed, enemy id, actor, flip)` is granted
  exactly once through the lane-06 `ReceiptLedger`, so a repeated frame or a
  reopened process (`JsonReceiptPersistence`) never duplicates a drop.
- **Real collection.** `BeetleFlips.collect()` is a second, exactly-once ordinary
  Onion credit. An unregistered flip cannot be collected, so an injected or
  replayed drop never produces a phantom reward.

## Cave treasure and relocation model

`experimental/pikmin2_kogane_cave.py` (with `tests/test_pikmin2_kogane_cave.py`)
models the source cave rules on top of the audited tables, without duplicating
them:

- `treasure_override(species, flip, carried_treasure)` returns the carried
  treasure on the first flip only, otherwise `None` (createTreasureItem,
  Kogane.cpp:386-414).
- `relocates(flip_count, in_cave)` is True only for an unflipped
  (`flip_count == 0`) cave beetle reaching Disappear, the `Cave::randMapMgr`
  analog (Kogane.cpp:250-262).
- `relocation_outcome(flip_count, in_cave)` classifies that Disappear into
  `{'flip', 'relocate', 'outcome': 'relocate'|'death'}`, so a caller never
  re-derives the unflipped-cave rule. `relocates`/`resolve_flip` now reject a
  non-boolean cave/demo flag instead of silently coercing it.
- `resolve_flip(species, flip, ...)` returns `{flip, drop, treasure, escape,
  relocate}`. `flip` is the source hit count after the event (`0` = unflipped
  Disappear, `1..MAX_FLIPS` = flips); the third flip forces `escape`; a treasure
  suppresses the table drop; unknown species and out-of-range flips are rejected.

## Native status

`native/pc_port/pc_p2_kogane.cpp` counts presses, plays the source damage clip
and emits the frame-7 `createItem` drop, then escapes after the third flip. That
host `dropFor` keeps the documented P1 fallback (no cave, no sprays); the audited
drop values are unchanged.

**In-process re-entry dedupe.** `pc_p2_kogane_reset()` snapshots each live
actor's `flips` count keyed by generator id before clearing; `pc_p2_kogane_setup()`
restores it and logs `P2_KOGANE_FLIPS_RESTORED generator=<id> flips=<n>`. A
reset+setup cycle inside one process (the fixture cleanup/re-entry path) therefore
cannot re-grant a beetle's finite flips. On a fresh process the map is empty and
the restore is a no-op.

**Escape on restore.** A restored count already at the source cap (`>= MAX_FLIPS
== 3`) means the beetle spent every drop and burrowed away before the reset, so
`setup()` reconstructs that spent state with the existing escape path
(`actor->pcEscapeNow()`, the same burrow as the live third-flip escape) and logs
`P2_KOGANE_RESTORED_ESCAPE generator=<id> flips=<n>` instead of re-spawning a
beetle that could never drop again. The escape reuses the `CorpseType` hook, so
no corpse pellet is left, and a beetle with no prior state is untouched. The
private fixture `experimental/pikmin2_kogane_reentry.py` drives one beetle to the
cap and another to a partial count, then re-enters once in-process and validates
both restore lines (`tests/test_pikmin2_kogane_reentry.py`).

Still open: a **cross-process native save bridge** (durable flips/treasure in the
P2 save, lane 01/06), plus native treasure override and cave relocation
execution. The `restoredFlips` snapshot is process memory only: a real process
restart still re-spawns every beetle with zero flips, so finite-drop dedupe does
not yet survive a save/reload.

## Gates

| Gate | Result | Evidence / limit |
|---|---|---|
| Source drop table | PASS (host) | `tests/test_pikmin2_kogane_rewards.py`; surface/cave/demo branches |
| Finite flips + escape | PASS (host) | three granted flips, fourth reports `escaped` |
| Restart dedupe | PASS (host) | reopened `JsonReceiptPersistence` never re-grants |
| Real collection | PASS (host) | exactly-once Onion credit, unregistered flip rejected |
| Cave relocation model | PASS (host) | `resolve_flip(..., 0, in_cave=True)['relocate']`; `relocation_outcome` classify; `tests/test_pikmin2_kogane_cave.py` |
| Treasure override model | PASS (host) | first-flip override in `treasure_override`/`resolve_flip` |
| In-process native re-entry dedupe | IMPLEMENTED (source only) | `restoredFlips` in `native/pc_port/pc_p2_kogane.cpp`; not rebuilt/run in this slice |
| In-process restored escape | IMPLEMENTED (source only) | `P2_KOGANE_RESTORED_ESCAPE` + `pcEscapeNow()` on `restored->second >= MAX_FLIPS`; `pikmin2_kogane_reentry` validator tests |
| Cross-process native restart | UNTESTED | needs a native save bridge (lane 01/06) |
| Native treasure override / cave relocation | UNIMPLEMENTED | no P2 cave in the P1 host |

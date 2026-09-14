# Reward beetle finite drops and restart dedupe (lane 17, #168/#219)

Lane 17 consumer of the lane-06 reward/receipt contract (#441). New host module
`experimental/pikmin2_kogane_rewards.py` with `tests/test_pikmin2_kogane_rewards.py`
(8 passing). No native save or shared build is modified.

## What is modelled

- **Source table.** `flip_drop()` resolves the audited per-flip drop through
  `experimental.pikmin2_kogane_assets.drop_for()` (Koganemushi/Wealthy/Fart
  `enemyParms` and drop code), including the surface/cave branch and the
  spicy/bitter demo-flag fallback. The P1 host has no spray item and no P2 cave,
  so the documented nectar fallback is the host resolution.
- **Finite counts.** `BeetleFlips.register()` refuses a flip beyond
  `MAX_FLIPS == 3`; the source escapes (burrows away) rather than dropping again,
  so a beetle can never be farmed indefinitely.
- **Restart dedupe.** Each distinct `(seed, enemy id, actor, flip)` is granted
  exactly once through the lane-06 `ReceiptLedger`, so a repeated frame or a
  reopened process (`JsonReceiptPersistence`) never duplicates a drop.
- **Real collection.** `BeetleFlips.collect()` is a second, exactly-once ordinary
  Onion credit. An unregistered flip cannot be collected, so an injected or
  replayed drop never produces a phantom reward.

## Native status

`native/pc_port/pc_p2_kogane.cpp` already counts presses, plays the source damage
clip and emits the frame-7 `createItem` drop, then escapes after the third flip.
That host `dropFor` keeps the documented P1 fallback (no cave, no sprays). This
slice adds the host receipt contract only: durable native save persistence,
treasure override and cave relocation remain open on #219.

## Gates

| Gate | Result | Evidence / limit |
|---|---|---|
| Source drop table | PASS (host) | `tests/test_pikmin2_kogane_rewards.py`; surface/cave/demo branches |
| Finite flips + escape | PASS (host) | three granted flips, fourth reports `escaped` |
| Restart dedupe | PASS (host) | reopened `JsonReceiptPersistence` never re-grants |
| Real collection | PASS (host) | exactly-once Onion credit, unregistered flip rejected |
| Native collection/restart | UNTESTED | needs a native save bridge (lane 01/06) |
| Treasure override / cave relocation | UNIMPLEMENTED | no P2 cave in the P1 host |

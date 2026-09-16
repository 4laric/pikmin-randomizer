# Reward beetle finite drops and restart dedupe (lane 17, #168/#219)

Lane 17 consumer of the lane-06 reward/receipt contract (#441). New host module
`experimental/pikmin2_kogane_rewards.py` with `tests/test_pikmin2_kogane_rewards.py`
(19 passing), the cave model `experimental/pikmin2_kogane_cave.py` with
`tests/test_pikmin2_kogane_cave.py`, the re-entry fixture
`experimental/pikmin2_kogane_reentry.py` with `tests/test_pikmin2_kogane_reentry.py`,
and an additive native re-entry dedupe, a first-flip treasure override and an
on-disk flip-receipt sidecar in `native/pc_port/pc_p2_kogane.cpp`. No native save
or shared build is modified.

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

**First-flip treasure override (P1 stand-in).** The P1 host has no P2 treasure
item, so a configured `treasure <generator> <pellet_value>` sidecar row substitutes
one labelled number pellet on that actor's first flip instead of the audited table
entry (`createTreasureItem`, Kogane.cpp:386-414). `pellet_value` is `1` or `5`; the
stand-in is emitted and then the normal frame-7 drop path runs, logging
`P2_KOGANE_TREASURE generator=<id> value=<n>`. Later flips and every unconfigured
actor keep the audited table unchanged, and `P2_ENEMY_READY` reports
`treasure=standin` (or `treasure=disabled` when absent). This is a host
approximation, not the source treasure object.

The sidecar grammar is the optional tokens between the actors and the first clip:

```text
P2_KOGANE_NATIVE_1
karada <shape>
actors <count>
<generator> <source_id>            (count rows)
treasure <generator> <pellet_value> (optional, 0+ rows; value 1 or 5)
<clip name> <count> <duration> <frames...>   (move, wait, damage)
```

`p2kogane::read` accepts zero treasure rows (absent section, the legacy format),
requires every `treasure` generator to be a declared actor and rejects a duplicate
generator or a value other than `1`/`5`. The host mirror is
`experimental.pikmin2_kogane_native.treasure_lines` (also used by
`pikmin2_kogane_behavior.native_sidecar`), and `emit` renders the row from an arena
actor's optional `treasure` field. A generated sidecar can therefore never be
refused at load.

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

**On-disk flip receipts (cross-process restart).** The in-process snapshot above
is process memory only, so `pc_p2_kogane.cpp` also writes a family-local sidecar,
`p2-kogane-receipts.txt`, in the process working directory. It is deliberately
**not** the P2 save (lane 01/06 owns that contract): it is a small text ledger in
the run directory that a second process can read.

```text
P2_KOGANE_RECEIPTS_1
<generator> <flips>
```

The header is followed by one row per generator (`<flips>` is the source flip
count `1..MAX_FLIPS`). `saveReceipts()` merges the live `beetles` counts with the
restored snapshot and rewrites the file atomically (`.tmp` sibling plus
`MoveFileExA`/`rename`) whenever a flip or escape occurs, so an interrupted write
leaves the previous ledger intact. `pc_p2_kogane_setup()` calls `loadReceipts()`
right after the in-process `restoredFlips` snapshot: disk rows fill in only when
they are newer, then the existing restore/escape path runs unchanged and logs
`P2_KOGANE_RECEIPTS loaded=<n>`. A missing or malformed file (bad header, bad row,
duplicate generator, out-of-range count) is ignored wholesale (`loaded=0`) and
never crashes the room.

The host mirrors that contract with `experimental.pikmin2_kogane_rewards.parse_receipts`
(strict, raises `ValueError`) and `read_receipts` (fail-safe, returns `{}` for a
missing or malformed file). The re-entry fixture runs a first process that spends
the flips, then a **second process on the same run directory** selected by the
`kogane-pass.txt` marker; the second pass must load `loaded=2`, reconstruct the
spent escape and the partial survivor, resume the survivor to the cap and log
`P2_KOGANE_RECEIPTS loaded=2` (`validate_cross_process`).

**Host ledger bridge.** `reconcile_native(sidecar_path_or_text, ledger, seed,
generator_to_enemy=None)` reconciles the native sidecar rows into a lane-06
`ReceiptLedger` exactly once. Each `<generator> <flips>` row expands to
`flip1..flipN` grants keyed by `(seed, 'enemy:<species-id>', '<generator>',
'flipN')` through the standard `ReceiptLedger.grant`, reusing the lane-06 schema
rather than forking it. The native rows carry only the spawn generator id
(`Generator::_70`), so the bridge recovers the `enemy:<species-id>` identity from
a `{generator: source_id}` map: `generator_to_enemy` when given, otherwise the
lane 17 arena fixture roster (`DEFAULT_GENERATOR_TO_ENEMY`, `219001/219002/219003`
= Kogane/Wealthy/Doodlebug). An unknown generator or a malformed sidecar raises
`ValueError` before anything is granted; a missing path is treated as a fresh run
(no rows). It returns the newly granted keys plus a `summary`
(`rows`/`generators`/`receipts`/`granted`/`already_present`). Re-reconciling the
same sidecar — including over a reopened `JsonReceiptPersistence` — grants nothing
and reports every receipt as `already_present`, while a different `seed` grants
again. `write_receipts(path, rows)` and `sync_receipts(path, ledger, seed, ...)`
write the exact native format (header, sorted rows, atomic temp-sibling replace)
back out, so the host copy and the native sidecar stay in sync. See
`tests/test_pikmin2_kogane_rewards.py`.

Still open: a native P2-save bridge (durable flips/treasure in the P2 save, lane
01/06), plus real treasure-item and cave-relocation execution. The first-flip
override is a labelled P1 number-pellet stand-in, not the source treasure object.
The sidecar is run-directory local, so a fresh run directory or a moved/renamed run
starts the beetles at zero flips; it is not a save-game contract. The
`enemy:<species-id>` map likewise has to travel with the run — a real product run
must pass the generator roster instead of the fixture default.

## Runtime fixture: first-flip treasure override (#168/#219)

`experimental/pikmin2_kogane_reentry.py` has a `treasure=True` path (CLI
`--treasure`) that opts one beetle into the native stand-in. It builds the same
parameterized arena as the re-entry fixture but writes
`native_sidecar(bank, treasures={219002: 5})`, so Wealthy's audited first-flip
table row (three 5-pellets) is replaced by a single labelled 5-pellet. The
instrumented `RoomApp` presses Wealthy once and exits as soon as the stand-in
pellet exists. The separate `validate_treasure` (never
`pikmin2_kogane_behavior.validate_behavior`) requires all of:

- `P2_KOGANE_TREASURE generator=219002 value=5` in the native log,
- `P2_KOGANE_DROP generator=219002 source_id=10 flip=1 pellet5=1 nectar=0`
  (one stand-in pellet, not the table's three),
- `P2_KOGANE_CENSUS pellets=1` and the completion marker
  `PASS P2_KOGANE_TREASURE standin1 value5`,
- exactly one flip, on 219002 only.

An untouched-table run (marker absent and/or `pellet5=3`) fails
`validate_treasure`, distinguishing the override from the normal table.

Exact commands (private build; the run needs the single GL slot and is not
launched by this slice):

```powershell
py -3.12 -m experimental.pikmin2_kogane_reentry build `
  --native native --build-dir output/l17x-treasure-build `
  --output output/l17x-treasure-fixture --head <native-head> --treasure
py -3.12 -m experimental.pikmin2_kogane_reentry run `
  --assets <P1 assets> --bank <validated beetle bank> `
  --output output/l17x-treasure-run `
  --exe output/l17x-treasure-fixture/fixture.exe --treasure
```

`tests/test_pikmin2_kogane_treasure.py` covers the validator
(marker present+value, missing marker, wrong value, override-vs-table) and the
sidecar/instrument emission. The build itself is not run in this slice.

**Export gap.** `engine/pc_port/pc_p2_kogane.cpp` (the exported engine copy)
still needs the normal integration export of the native first-flip override
(`native/pc_port/pc_p2_kogane.cpp` at `opencode/p2-l17x-native`, commit
`6ab7b200`); this host-only slice did not run a native build or export.

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
| Cross-process sidecar receipts | IMPLEMENTED (source only) | `p2-kogane-receipts.txt` atomic write/load + `P2_KOGANE_RECEIPTS loaded=<n>`; host `parse_receipts`/`read_receipts` and `validate_cross_process` tests |
| Native-sidecar -> lane-06 ledger bridge | PASS (host) | `reconcile_native` idempotent across reopen, per-seed, strict on malformed/unknown; `sync_receipts`/`write_receipts` round-trip; `tests/test_pikmin2_kogane_rewards.py` |
| Native treasure override / cave relocation | PARTIAL | first-flip override is a labelled P1 number-pellet stand-in (`P2_KOGANE_TREASURE`, optional `treasure` sidecar row); `pikmin2_kogane_reentry --treasure` fixture + `validate_treasure` (`tests/test_pikmin2_kogane_treasure.py`); run not launched in this slice; real P2 treasure item and cave relocation still UNIMPLEMENTED (no P2 cave in the P1 host) |
| Native P2-save persistence | UNIMPLEMENTED | sidecar is run-directory local, not the lane 01/06 save |

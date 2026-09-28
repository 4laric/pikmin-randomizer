# Muse SnakeCrow34 death/transport/re-entry observer handoff (#376)

Lane `snakecrow34-death-transport-reentry-observer` (generation 3). Owner:
Codex through the shared `4laric` account. Parent family work: the shared
SnakeCrow/SnakeWhole snagret module (#407, #245); roster row source 34
`SnakeCrow`, role source.

## Slice summary

Deliver an additive, dependency-free observer that closes the three missing
SnakeCrow gates (death_corpse, transport_reward, cleanup_reentry) the moment a
live bound actor produces natural death -> corpse -> Pod credit -> rebirth with
re-bind, plus a standalone log checker and negative tests. The family FSM and
its modules are read-only under the legacy lane-25 claim; no family change was
made or requested. No ADMIT and no ledger writes.

The runtime side of this slice is **candidate-blocked on a missing production
driver**, not on tooling. The production family module
(`native/pc_port/pc_p2_snakejoint.cpp`) binds the actor and emits
`P2_SNAKEJOINT_BIND/STATE/DEAD`, and the generic Research Pod path
(`native/pc_port/pc_p2_preview.cpp`) resolves any registered Chappy corpse to
`P2_POD_RECEIPT id=corpse:<generator>`, but **nothing in the read-only family
code drives a natural damage source, a FreeMode corpse haul, or a stage
re-entry** for this species. The observer and its tests are delivered and
fail-closed, so a future natural run closes the gates with zero observer
changes. Adding the driver is a family-module change and therefore requires
existing-owner review (none requested here).

## Files owned (all new, additive)

- `experimental/pikmin2_muse_snakecrow.py` ? dependency-free `parse(text)`
  verdict. Requires the same generator file id across the family bind
  (`P2_SNAKEJOINT_BIND ... species=SnakeCrow`), the family death marker
  (`P2_SNAKEJOINT_DEAD ... source_id=34`) that occurs after it, and the Pod
  corpse receipt (`P2_POD_RECEIPT id=corpse:<gen>`) that occurs after the
  death; a later bind of the same generator is recorded as re-entry. Any
  mismatch, wrong order, or missing leg yields `gate_ok False`. Emits no
  markers; cannot fabricate acceptance.
- `tests/test_pikmin2_muse_snakecrow.py` ? 13 contract/negative tests
  (correlated triple, re-bind, receipt/death/bind generator mismatch, wrong
  order, wrong source id, non-SnakeCrow bind, captain-down block, extinction
  block, empty log, proxy-without-seed).
- `native/tools/p2_muse_snakecrow_fixture.cpp` ? standalone, engine-free
  stdlib-only checker implementing the same contract; exit 0 only on a fully
  correlated triple with no captain-down evidence.
- `docs/PIKMIN2_MUSE_SNAKECROW_HANDOFF.md` ? this file.

## Staged genesis arena (fresh)

`output/workflow/autofill/planning-shards/enemies-5/prepared/snakecrow34-observer-output/stage_genesis.py`
stages a fresh room via `scripts.preview_pikmin2_room.prepare` (current
starting-squad overlay) and appends one P1 `TEKI_Chappy` placement actor
(type 3) generator `340001` at (-110, 20, 0). Sidecars:
`p2-snagret-actors.txt` (`P2_SNAGRET_ACTORS_1 1 340001 SnakeCrow`),
`p2-snagret-bank.txt` (lane-25 clip bank, reused read-only), `p2-pod.txt`
(`P2_POD_1 bolt 180 15 25 Kochappy 2`). Stage manifest:
`genesis/stage-manifest.json` (sha256 below).

## Bounded production run (real binary, unforced)

`output/autofill-native-585-build/bin/nectar.exe --experimental-pikmin2-room`
(cwd = staged arena, `PIKMIN_P2_ROOM_WINDOW=960x540`, `SDL_AUDIODRIVER=dummy`,
no seed, no input) reached full room setup and bound the live actor:

```
[Pikipelago] P2_POD_CORPSES_REBOUND before=0 after=2
[Pikipelago] P2_POD_READY treasure=bolt value=180 weight=15 capacity=25 pokos=0
P2_SNAKEJOINT_BIND generator=340001 species=SnakeCrow source_id=34 visual_only=0
P2_ENEMY_READY species=SnakeCrow native_family=Chappy generator=340001 x=-142.2784119 y=20.0000000 z=-32.9459953 health=1500.0 max_health=1500.0 behavior=native source_FSM=implemented attack=animation_event
P2_SNAKEJOINT_STATE generator=340001 state=stay
P2_BATCH3 missing pose bank
```

The run then returns before gameplay because the arena has no converted
snagret pose bank (an arena-asset gap) and, more importantly, because an
unforced room provides no damage source, no corpse haul, and no stage
re-entry. `native.log` (sha256 below) is the raw capture. Running the
observer on it yields `{"bound": true, "dead": false, "receipt_ok": false,
"rebound": false, "gate_ok": false}`: the live bind is visible and the
observer correctly refuses a verdict without all three correlated legs.

## Concrete source ID

- Source ID: 34 `SnakeCrow`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_SNAKEJOINT_NATIVE.md gate table; this slice's staged run output/workflow/autofill/planning-shards/enemies-5/prepared/snakecrow34-observer-output/native.log `P2_SNAKEJOINT_BIND generator=340001 species=SnakeCrow source_id=34` and `P2_ENEMY_READY species=SnakeCrow generator=340001` | natural |
| 2. Autonomous movement and animation | PASS (natural) | docs/PIKMIN2_SNAKEJOINT_NATIVE.md gate 2: both species stay to appear to attack to eat; source FSM observed | natural |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_SNAKEJOINT_NATIVE.md gate 3: bites at the banked frame with exactly-once `P2_SNAKEJOINT_EAT` | natural |
| 4. Death and corpse | UNTESTED | Observer delivered; no natural death observed. Family module has no damage source and the unforced run produced no `P2_SNAKEJOINT_DEAD`; family code is read-only (existing-owner review required) | natural (unobserved) |
| 5. Actual transport and reward | UNTESTED | Observer delivered; no `P2_POD_RECEIPT id=corpse:340001`. No FreeMode corpse haul is driven by the read-only snagret family code; generic Pod resolution is present but unreached | natural (unobserved) |
| 6. Cleanup and re-entry | UNTESTED | Observer delivered; no second `P2_SNAKEJOINT_BIND` after a stage boundary. Stage reset/forget are wired but not driven by a natural boundary in this arena | natural (unobserved) |

Gates 1-3 are preserved exactly as the legacy lane-25 claim left them and are
never relabelled. Gates 4-6 remain UNTESTED; this handoff makes no runtime
PASS claim.

## Checks

- `py -3.12 -m pytest tests/test_pikmin2_muse_snakecrow.py -q` -> 13 passed.
- Observer on the real init log -> `gate_ok false` (fail-closed).
- Standalone checker on the correlated sample -> exit 0; on the negative
  sample -> exit 1 (both directions).
- Gate checker: `scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_SNAKECROW_HANDOFF.md` -> EXIT=0.

## One exact reproduction

```
cd C:/Users/alari/pikmin-randomizer/output/workflow/autofill/planning-shards/enemies-5/prepared/snakecrow34-observer
py -3.12 -m pytest tests/test_pikmin2_muse_snakecrow.py -q   # 13 passed
py -3.12 -c "from experimental.pikmin2_muse_snakecrow import parse; print(parse(open(r'../snakecrow34-observer-output/native.log',encoding='utf-8',errors='replace').read())['gate_ok'])"  # False
```

## Evidence hashes

- `snakecrow34-observer-output/native.log` sha256 `373bfda21a6533c6b901985dd75c981e88aa2afeb1acc416559916b086b724ed`
- `snakecrow34-observer-output/checks.log` sha256 `0def6505aa6408cb52b54ce43d8902dc562997ba38fc5f76de5ade9d71871f61`
- `snakecrow34-observer-output/genesis/stage-manifest.json` sha256 `b619d8f6138b4344b72f459bfe0f921447d4f7f9bd03c1c9e5c993d4f413bcb1`
- `snakecrow34-observer-output/p2_muse_snakecrow_fixture.exe` sha256 `9354a700d0b2f9a48bb7b055ac3dd4ad49697c4695f4e8afba500a1cb249ff4b`

# Batch-2 north native spawn fixtures — ground #346, dweevil #349, cannon #350

Runtime evidence for the three batch-2 ("batch-2 visuals north") families, produced
on the 2026-09-13 Batch 3 session (issue #388, parent #186). It moves these
families from **Converted assets** to **Native display**: exact generator/native
identity, effective XYZ and a real native pose draw, with the ordinary P1 control
actor untouched.

This is a **visual anchor only**. No source P2 FSM, damage/elemental receiver,
reward, capture or projectile behavior is implemented or claimed.

## Registration

Shared additive unit `pc_p2_batch2` (family-owned, see
[PIKMIN2_BATCH2_NATIVE_REGISTRATION.md](PIKMIN2_BATCH2_NATIVE_REGISTRATION.md))
at native `219f7abc`, plus this session's fixes on `opencode/p2-batch3-north-native`
`56f81548`:

- `parseActors` compared the trailing `_ACTORS_1` suffix with an off-by-one
  offset/length (`size-8, 8` against a 9-char suffix), so every valid actor config
  was rejected. Fixed to `size-9, 9`.
- Added `pc_p2_batch2_any_drawn()` so a runtime fixture can require that a pose
  was actually drawn instead of only selected.

The generated bank now omits clips whose sampled poses are not a contiguous
0-based run (unsupported or gapped source clips); the native loader indexes poses
`_00.._N-1` per clip. On this disc that affects only Sokkuri `appear1` (single
pose at slot 1) and `type5` (unsupported). Dweevil and cannon have no such clips.

## Fixture

`experimental/pikmin2_batch2_runtime.py` stages the family arena (original P1
Impact Site, `pikmin2_batch2_core.prepare`), writes the expected
`<generator> <native_type> <registered> <x> <y> <z>` rows, then builds and runs a
private instrumented `RoomApp` (`native/tools/preview_p2_room.cpp`) linked against
the existing `pikmin_pc` objects. The fixture asserts from native state:

- every staged generator exists exactly once, with the expected native teki type
  and effective birth and generator XYZ;
- only the family generators are registered (`P2_BATCH2_BIND`), not the control;
- the camera is driven onto the family actors until `pc_p2_batch2_any_drawn()`;
- the ordinary P1 control actor is still alive at exit.

Build (private, no maintained checkout touched):

```powershell
py -3.12 -m experimental.pikmin2_batch2_runtime build `
  --native output/tracks/p2-batch2-reg/native `
  --build-dir output/tracks/p2-batch2-reg/native/build-randomizer `
  --output output/p2-batch3-runtime/fixtures/ground `
  --head 56f815482c3091d0cf1815081ee4e8ca4a64ffc3
```

Run (per family; the fixture binary is family-agnostic and reads the positions
file written by `run`):

```powershell
py -3.12 -m experimental.pikmin2_batch2_runtime run --family ground `
  --assets <P1 extracted assets> --imported output/p2-lane-verify/ground `
  --output output/p2-batch3-runtime/runs3/ground `
  --exe output/p2-batch3-runtime/fixtures/ground/fixture.exe --timeout 150
```

Native source / private build (not committed):

- native branch `opencode/p2-batch3-north-native`, head `56f81548` (parent `219f7abc`)
- `output/tracks/p2-batch2-reg/native/build-randomizer/bin/nectar.exe`
  SHA-256 `51120ce30bc5b34a40a193117b7d79f69f71ab42ea0914b0b31963a35ab3db81`
- fixture `output/p2-batch3-runtime/fixtures/ground/fixture.exe`
  SHA-256 `1789884796b3e57b9e5c1b0ec87f8d91dfd6ded4f4d56f3f8717464ed4a3bde6`

## Results

All three families PASS the fixture (`exit 0`, `PASS P2_BATCH2_RUNTIME`).

| Family | Generators bound | Effective XYZ | Native type | Live draw | Control |
|---|---|---|---|---|---|
| Ground #346 | 346001..346006 (6) | `(-300..300, 30, 1850)`; control `(240,30,1500)` | 3 (Chappy) | `P2_BATCH2_DRAW` `ElecBug clip=wait` | alive |
| Dweevil #349 | 349001..349005 (5) | `(-240..240, 30, 1850)`; control `(240,30,1500)` | 3 (Chappy) | `P2_BATCH2_DRAW` `WaterOtakara clip=wait1` | alive |
| Cannon #350 | 350001..350006 (6) | `(-300..300, 30, 1850)`; control `(240,30,1500)` | 17/17/17/2/3/3 (Beatle/Iwagon/Chappy) | `P2_BATCH2_DRAW` `Kabuto clip=wait` | alive |

Private evidence roots (assets not committed):

- `output/p2-batch3-runtime/runs3/ground/stages/6f4ca7e8509a43afa82358b5424ed6aa/`
- `output/p2-batch3-runtime/runs3/dweevil/stages/d8b3de0f8fe44e6cbf5bd14769601e2f/`
- `output/p2-batch3-runtime/runs3/cannon/stages/4c55fda8efad45b08b45f4bb164b9aca/`

Each stage has `native.log`, `runtime-evidence.json` and the staged `arena.json`.

Sample hashes:

| Artifact | SHA-256 |
|---|---|
| ground `arena.json` | `508e865b2104ff2720671896509f6e134f74b68534632107418e6d5f80336a8e` |
| dweevil `arena.json` | `112b0112611fdfd47a12033717b0509a2731afc9975871fb6b17d858ca66ca8a` |
| cannon `arena.json` | `3267277d031046eaec1a48db7f43dd65deac8218fb70b4dd2c460f6495afa0d7` |
| ground `p2-ground-bank.txt` | `b3b55c2dcef7bb75bc9d4e97505b0d618e6cdfbccfeb9f94ac5465b382f5c571` |
| dweevil `p2-dweevil-bank.txt` | `7907f2a26d7a2c160e71aa379435a26a9bb1f45b92f500ba57ffdf64a9fef2ef` |
| cannon `p2-cannon-bank.txt` | `089caf2430b68baa60ab6f829023dbe4e3be60268b3ba73686f927e456b5058b` |

## Gate table

Six arena gates (pipeline §6), per family:

| Gate | Ground | Dweevil | Cannon |
|---|---|---|---|
| exact spawn | PASS | PASS | PASS |
| autonomous movement/animation | UNTESTED (P1 host AI; visual pose selection only) | UNTESTED | UNTESTED |
| attacks/receivers | BLOCKED (source not registered) | BLOCKED (elemental receivers) | BLOCKED (projectile/damage) |
| death/corpse | BLOCKED | BLOCKED | BLOCKED |
| transport/reward | source-backed N/A (no carry in lane) | BLOCKED (treasure theft) | source-backed N/A |
| cleanup/re-entry | UNTESTED | UNTESTED | UNTESTED |

Family extras remain as recorded in `experimental/pikmin2_batch2_families.py`
(`armor_flint_reward`, `elecbug_charge`, `sokkuri_disguise`, `hana_ambush`,
`imomushi_plant_eat`, `tamagomushi_swarm`; `otakara_shared_base`,
`change_texture_identity`, `elemental_discharge`, `bomb_payload_lifecycle`;
`cannon_projectile_pool`, `rock_roll`, `bomb_lifecycle`, `egg_drop`,
`buried_emerge`, `muzzle_alignment`) — all BLOCKED.

## Limitations

- The sampled pose bank proves pose selection and draw, not source behavior.
- Ground invertebrates, dweevils and Bomb/Egg have no audited P1 counterpart; the
  Chappy placement vehicle stages the visuals and does not claim identity.
- Materials are approximate; no skeletal playback or P2 event execution.
- In the cannon run one family actor (a P1 host vehicle) despawned before exit
  (`P2_BATCH2_ALIVE family=5/6`); that is P1 host AI, not a registration failure.
- No disc assets, generated models, executables or saves are committed.

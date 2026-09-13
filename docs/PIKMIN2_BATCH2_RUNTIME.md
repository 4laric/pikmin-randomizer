# Batch-2 north runtime — ground #346, dweevil #349, cannon #350

Runtime evidence for the three batch-2 ("batch-2 visuals north") families,
produced on the 2026-09-13 Batch 3 session (issue #388, parent #186). It drives
these families through **Native display** (exact generator/native identity,
effective XYZ and a real native pose draw) and the **playable-proxy** gates for
autonomous movement and injected death, with the ordinary P1 control untouched.

This is a **visual anchor + P1 host proxy only**. No source P2 FSM,
damage/elemental receiver, reward, capture or projectile behavior is implemented
or claimed.

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

The generated bank omits clips whose sampled poses are not a contiguous 0-based
run (unsupported or gapped source clips); the native loader indexes poses
`_00.._N-1` per clip. On this disc that affects only Sokkuri `appear1` (single
pose at slot 1) and `type5` (unsupported). Dweevil and cannon have no such clips.

## Fixture

`experimental/pikmin2_batch2_runtime.py` stages the family arena (original P1
Impact Site, `pikmin2_batch2_core.prepare`), writes the expected
`<generator> <native_type> <registered> <x> <y> <z>` rows, then builds and runs a
private instrumented `RoomApp` (`native/tools/preview_p2_room.cpp`) linked against
the existing `pikmin_pc` objects. Actors are re-found by generator ID on every
access (never cached raw pointers), because the cannon Rock/Iwagon host despawns.
The fixture:

- verifies every staged generator exists once, with the expected native teki type
  and effective birth/generator XYZ; only the family generators are registered
  (`P2_BATCH2_BIND`), not the control;
- frames the arena with an existing actor target (the default room camera does
  not render the arena, so `pc_p2_batch2_draw` would otherwise never run);
- requires a live pose draw;
- measures `P2_BATCH2_MOVE` displacement over ~150 ready frames (≥1 unit);
- injects a lethal `InteractAttack` on one P1 Chappy-class host and records
  health until it reaches zero or the window closes;
- re-checks the family and ordinary control at exit.

Build (private, no maintained checkout touched):

```powershell
py -3.12 -m experimental.pikmin2_batch2_runtime build `
  --native output/tracks/p2-batch2-reg/native `
  --build-dir output/tracks/p2-batch2-reg/native/build-randomizer `
  --output output/p2-batch3-runtime/fixtures/ground `
  --head 56f815482c3091d0cf1815081ee4e8ca4a64ffc3
```

Run (per family; the fixture binary is family-agnostic and reads the positions
file written by `run`; assets are the runbook's P1 tree):

```powershell
py -3.12 -m experimental.pikmin2_batch2_runtime run --family ground `
  --assets "C:\Users\alari\bbft\dist\cohesion\pikmin\assets" `
  --imported output/p2-lane-verify/ground `
  --output output/p2-batch3-runtime/runs10/ground-a1 `
  --exe output/p2-batch3-runtime/fixtures/ground/fixture.exe --timeout 150
```

Native source / private build (not committed):

- native branch `opencode/p2-batch3-north-native`, head `56f81548` (parent `219f7abc`)
- `output/tracks/p2-batch2-reg/native/build-randomizer/bin/nectar.exe`
  SHA-256 `51120ce30bc5b34a40a193117b7d79f69f71ab42ea0914b0b31963a35ab3db81`
- fixture `output/p2-batch3-runtime/fixtures/ground/fixture.exe`
  SHA-256 `4049a9cddc1040273ca125a0077f8c55fe33c3ca566b688c3ec762ddce94ff1c`

## Results

| Family | Bound | Type | Live draw | Moved | Injected death | Corpse pellet | Control |
|---|---|---|---|---|---|---|---|
| Ground #346 | 346001..346006 | 3 (Chappy) | `ElecBug clip=wait` | 3/6 (max 74.6) | PASS, health 130→0 | observed 1 on some runs | alive |
| Dweevil #349 | 349001..349005 | 3 (Chappy) | `WaterOtakara clip=wait1` | 3/5 (max 52.0) | accepted but health stays 130 | none | alive |
| Cannon #350 | 350001..350006 | 17/17/17/2/3/3 | `Kabuto clip=wait` | 4-5/6 (max 84.0) | PASS, health 130→0 | source-backed N/A (container host) | alive |

Ground and cannon pass the combined fixture (`exit 0`, `PASS P2_BATCH2_RUNTIME`).
Dweevil passes native display, movement and the injected-attack receiver, but the
FireOtakara placement vehicle takes no damage (`accepted=1`, `health=130.0`
unchanged for 160 frames), so its death/corpse sub-gate is **FAIL/BLOCKED** on
this engineered arena.

Private evidence roots (assets not committed):

- `output/p2-batch3-runtime/runs10/ground-a1/stages/ee7af35fbd584e16a5c536304a4bc5ba/`
- `output/p2-batch3-runtime/runs10/dweevil-a1/stages/0fa7e42d57af4a4683fd7677989aa639/`
- `output/p2-batch3-runtime/runs10/cannon-a1/stages/5a2c6dacd2254ea89bab80e9f0c8a1f6/`

Each stage has `native.log`, `runtime-evidence.json` and the staged `arena.json`.
The earlier movement-only run (fixture `6274c2de…`) is under
`output/p2-batch3-runtime/runs4/`.

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
| autonomous movement/animation | PASS (P1 proxy; 3/6) | PASS (P1 proxy; 3/5) | PASS (P1 proxy; 4-5/6) |
| attacks/receivers | proxy injected attack accepted; source receivers BLOCKED | proxy injected attack accepted but no damage; source receivers BLOCKED | proxy death PASS; source projectile/damage BLOCKED |
| death/corpse | death PASS; corpse pellet intermittent | FAIL/BLOCKED (no damage on host) | death PASS; carcass source-backed N/A |
| transport/reward | source-backed N/A (no carry in lane) | BLOCKED (treasure theft) | source-backed N/A |
| cleanup/re-entry | UNTESTED | UNTESTED | UNTESTED |

Family extras remain as recorded in `experimental/pikmin2_batch2_families.py`
(`armor_flint_reward`, `elecbug_charge`, `sokkuri_disguise`, `hana_ambush`,
`imomushi_plant_eat`, `tamagomushi_swarm`; `otakara_shared_base`,
`change_texture_identity`, `elemental_discharge`, `bomb_payload_lifecycle`;
`cannon_projectile_pool`, `rock_roll`, `bomb_lifecycle`, `egg_drop`,
`buried_emerge`, `muzzle_alignment`) — all BLOCKED.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_batch2.py tests/test_pikmin2_batch2_runtime.py -q`
→ **87 passed**.

## Limitations

- The sampled pose bank proves pose selection and draw, not source behavior.
- Movement and death are P1 host AI/receivers on the placement vehicle
  (`Chappy`/`Beatle`/`Iwagon`), not source P2 behavior.
- Corpse-pellet creation for generator-spawned hosts is nondeterministic; the
  `corpse` count is reported but is not part of the fixture pass. The native
  corpse-draw path was not observed.
- Dweevil FireOtakara accepts the injected attack but takes no damage in this
  engineered arena; its death/corpse gate remains open.
- Ground invertebrates, dweevils and Bomb/Egg have no audited P1 counterpart; the
  Chappy placement vehicle stages the visuals and does not claim identity.
- Private runs crash intermittently at the GL/driver layer (access violation
  before frame 150 on some launches); passing runs are recorded.
- No disc assets, generated models, executables or saves are committed.

# Lane 20 (Cannon/projectiles) — DeepSeek handoff

Tracking issue [#169](https://github.com/4laric/pikmin-randomizer/issues/169);
integration/coordination [#186](https://github.com/4laric/pikmin-randomizer/issues/186).
Implementation owner: Codex through shared account `4laric`; executing agent/session: DeepSeek (lane 20, `dsw/l20-root` / `dsw/native-l20`).

## Slice delivered

**Source IDs owned / inspected:** Kabuto 75, Rkabuto 95, Fkabuto 96; Stone 74 /
Rock 19 (projectile), Egg 37, Bomb 36 (shared primitives, unchanged; reused by
21/25/26/27) and FminiHoudai 97 (Groink pedestal, lane 21).

**Concrete slice:** Kabuto 75 → Stone 74 → **actual engine receiver mutation**.
Before this slice the projectile host only applied emitted strikes to a private
proxy receiver and never mutated engine health. This slice routes the classified
Teki/Navi-Piki strikes into the engine's own `stimulate(InteractAttack/InteractPress)`
path (source `Rock.cpp:204-238`) behind an opt-in `engine_receiver 1` config row,
with `P2_PROJECTILE_ENGINE_STRIKE` observability (live `mHealth` / `mStoredDamage`
before+after). This closes the ledger's "actual receiver mutation" remainder; the
moving muzzle, sampled fire clock and actor binding were already integrated and
are not re-implemented here.

## Ordered commits (both branches clean)

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`.

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l20-native` | `25c11906` | real engine receiver mutation for Kabuto Stone/Rock strikes (#169) |
| native | `e9bb1661` | register pc_p2_projectile_engine_receiver.cpp in CMake (hook) (#169) |
| root `deepseek/p2-l20` | `66fb414` | real engine receiver mutation harness, tests and doc (#169) |

Dirty state: none (both clean at handoff).

## Interfaces / hooks touched and why

- New family-local native module `pc_port/pc_p2_projectile_engine_receiver.{h,cpp}`
  (engine-aware, additive; no new subsystem). `p2_projectile_apply_engine_strike()`
  maps the already-classified strike to `InteractAttack(owner, nullptr, damage, false)`
  (Teki) or `InteractPress(owner, damage)` (grounded Navi/Pikmin) and reports an
  observed outcome. No engine field is written directly — only `stimulate()`.
- Family-owned host seam `pc_port/pc_p2_projectiles.cpp`: a new `engine_receiver 1`
  config row (default 0 = proxy-only, existing behavior unchanged); both contact
  loops additionally route emitted strikes into the engine receiver and log
  `P2_PROJECTILE_ENGINE_STRIKE` / `_NOP`. Teki strikes pass `source=nullptr`
  (source attributes Teki damage to the Stone `this`); grounded Navi/Pikmin pass
  the bound `kabuto_actor` when present.
- One additive CMake source line (separately committed hook commit).

No shared file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`, `tekimgr.cpp`,
`gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`, CMake) received a semantic
change; CMake only gained one source line. The host seam was already registered
through the existing batch-2 setup/update/forget hooks.

Root files: `experimental/pikmin2_projectile_engine_receiver.py` (harness),
`tests/test_pikmin2_projectile_engine_receiver.py` (9 tests),
`docs/PIKMIN2_PROJECTILE_ENGINE_RECEIVER.md`.

## Build evidence (`output/dsw/l20-build-evidence.txt`)

- Native head `e9bb1661435e3a26e88848674aeac947ab16b9e4`, clean.
- `nectar.exe` SHA-256 `32fb6c82ada880d35ae8a9ce153425d1faafd60d50608fcb72cb851493ee4f7d`.
- `ninja -n` → `ninja: no work to do.` (fresh, target `pikmin_pc`).
- Config: Ninja + MinGW g++ 16.2.0, Release, `PIKMIN_NATIVE_JAUDIO=ON`,
  `CMAKE_MAKE_PROGRAM=<python ninja.exe>` (configured once manually through the
  build slot, then built via `build_lane.py l20`).

## Fixture adoption evidence

- Window: native.log `Experimental preview window set to 960x540 windowed and centered`.
- Live starting squad: the current `preview_pikmin2_room` overlay adds 20 red
  Pikmin; the room also places `preview dwarf bulborb` (the Teki target).
- No extinction; the launch ran live gameplay and was timer-terminated at 45 s
  (`exit_code=1` is the deliberate termination, not a crash).
- Run dirs (acceptance): `output/dsw/l20-out/runtime/c98e56b1ce5b49d79b48b95f2aca962b`
  (rkabuto), `.../47b1839fcaea471faaae00dd098c5a20` (stone).

## Six arena gates (Kabuto 75 → Stone 74 → real Teki receiver)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS (source-backed) | `preview dwarf bulborb` generator as the Teki target; fire is FSM-driven (`P2_PROJECTILE_KABUTO_FIRE species=Rkabuto`) |
| 2. Movement + animation | source-backed N/A | projectile is policy-simulated (no rendered model this slice); flight driven by the committed Stone FSM |
| 3. Attacks / receivers | PASS — natural Teki `InteractAttack` 250 | `P2_PROJECTILE_ENGINE_STRIKE kind=Attack damage=250.0 applied=1 stored=0.0->250.0` (×14 applied) |
| 4. Death + corpse | FAIL (honest) | Teki `mStoredDamage` accumulates 0→3500 but the P1 Chappy proxy never `makeDamaged()`s foreign stimuli when idle/wandering, so `mHealth` stays 130 and no corpse drops |
| 5. Transport + reward | UNTESTED | cargo-free room, no Pod; no lethal drop path reached |
| 6. Cleanup + re-entry | PASS | `P2_PROJECTILE_STONE_DESTROY reason=wall` per breaking Stone; contact dedupe is token-keyed (no stale pointer) |

Injected vs natural labelling: the fire is FSM-driven (not injected); the receiver
mutation is a real `stimulate()` result, not a direct health write. The **lethal**
path (health→0) is NOT observed for the gate-4 reason and is reported FAIL, not
papered over.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_projectile_engine_receiver.py -q` → 9 passed.
`py -3.12 -m pytest tests/test_pikmin2_projectile_engine_receiver.py tests/test_pikmin2_cannon_projectile_assets.py -q`
→ 24 passed. (No root test regression.)

## Assumptions

- Immediate `mStoredDamage` delta is the valid observability signal for a Teki
  `InteractAttack`, because P1 Teki damage is deferred through `mStoredDamage →
  makeDamaged()` (`tekibteki.cpp:850-858,1863`); `mHealth` only moves once the
  target's own state machine consumes it.
- The canonical `output/pikmin2-room105` converted room was absent this session;
  `l20-out/converted` is a lane-owned copy of `room.mod`/`room.ini`/`treasure.mod`
  from a prior assembled room run (`output/lane1032-elements-runtime-03/live01/...`),
  re-staged idempotently by `scripts.preview_pikmin2_room.prepare`.
- Non-homing `kabuto` (Kabuto) did not reach the wandering Dwarf; `rkabuto`
  (homing) converged on the Pikmin-swarmed Dwarf and produced the repeated Teki hits.

## Remaining blockers (named provider)

- Lethal resolution / corpse / reward: the target must consume foreign stored
  damage via its own damage-reaction state or a real P2 Teki FSM — depends on
  lane 07 (lifecycle) / 10 (receivers) and the generated-session admission (#169).
- `navipiki_press_receiver_mutation` remains UNTESTED at runtime (only unit-tested);
  a `stone`-into-a-grounded-Pikmin configuration was not run this slice.
- Generated-session acceptance, moving-muzzle/sampled-clock/actor-binding re-exercise
  and the shared Rock/Egg/Bomb consumer parity (21/25/26/27) remain outside this slice.

## Exact reproduction

```powershell
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_projectile_engine_receiver `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l20-build/bin/nectar.exe `
  --converted C:/Users/alari/pikmin-randomizer/output/dsw/l20-out/converted `
  --mode rkabuto --seconds 45
```

(Prerequisite, already done once, private: configure
`C:\Users\alari\pikmin-randomizer\output\dsw\native-l20-build` with
`-DPIKMIN_NATIVE_JAUDIO=ON -DCMAKE_MAKE_PROGRAM=<python ninja.exe>`; build via
`py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l20`.)

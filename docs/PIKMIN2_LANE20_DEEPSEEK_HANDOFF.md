# Lane 20 (Cannon/projectiles) — DeepSeek handoff (fix1)

Tracking issue [#169](https://github.com/4laric/pikmin-randomizer/issues/169);
integration/coordination [#186](https://github.com/4laric/pikmin-randomizer/issues/186).
Implementation owner: Codex through shared account `4laric`; executing agent/session: DeepSeek (lane 20, `dsw/l20-root` / `dsw/native-l20`).

## Slice delivered

**Source IDs owned / inspected:** Kabuto 75, Rkabuto 95, Fkabuto 96; Stone 74 /
Rock 19 (projectile), Egg 37, Bomb 36 (shared primitives, unchanged; reused by
21/25/26/27); FminiHoudai 97 (Groink pedestal, lane 21).

**Concrete slice:** Kabuto 75 → Stone 74 → **actual engine receiver mutation**
(source-faithful `InteractAttack`/`InteractPress` via `stimulate()`), plus the
review fixes for that slice: the bound cannon can no longer damage itself, the
`kabutoActor` lifetime pointer is cleared on forget, the `engine_receiver`
duplicate test is tracked correctly, and the unreachable `DAMAGED_TEKI` marker is
dropped.

## Ordered commits (both branches clean)

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`.

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l20-native` | `25c11906` | real engine receiver mutation for Kabuto Stone/Rock strikes (#169) |
| native | `e9bb1661` | register pc_p2_projectile_engine_receiver.cpp in CMake (hook) (#169) |
| native | `6af683e5` | review fixes — self-hit skip, actor lifetime, engine_receiver dup, marker cleanup (#169) |
| native | `610bcf0b` | emit P2_PROJECTILE_SKIP_SELF once per Stone flight (#169) |
| root `deepseek/p2-l20` | `66fb414` | real engine receiver mutation harness, tests and doc (#169) |
| root | `4f81d0d` | DeepSeek handoff for real engine receiver mutation slice (#169) |
| root | `2a70d95` | review fixes — kabuto_actor self-hit harness, canonical defaults, doc corrections (#169) |

Dirty state: none (both clean at handoff).

## Interfaces / hooks touched and why

- New family-local native module `pc_port/pc_p2_projectile_engine_receiver.{h,cpp}`
  (engine-aware, additive). `p2_projectile_apply_engine_strike()` routes the
  already-classified strike into `InteractAttack(owner=source, nullptr, damage,
  false)` (Teki) or `InteractPress(owner=source, damage)` (grounded Navi/Pikmin)
  and reports an observed `mHealth`/`mStoredDamage` outcome. No engine field is
  written directly — only `stimulate()`.
- Family-owned host seam `pc_port/pc_p2_projectiles.cpp`:
  - `engine_receiver <0|1>` row (default 0 = proxy-only); `sawEngineReceiverRow`
    makes a genuine duplicate fail closed.
  - `detectStoneContacts` skips `creature == gHost.kabutoActor` (with a
    once-per-flight `P2_PROJECTILE_SKIP_SELF` marker) and the Stone is now birthed
    with `tokenOf(kabutoActor)` as its source token so the source-grace matches the
    real firer — the cannon cannot damage itself.
  - `pc_p2_projectiles_forget` nulls a forgotten `kabutoActor`, fixing the dangling
    `InteractPress(owner)` → `playEventSound(mOwner)` dereference.
  - dropped the unreachable `P2_PROJECTILE_ENGINE_DAMAGED_TEKI` marker.
  - `kabuto_actor` not-found now prints candidate Teki generators (diagnostic).
- One additive CMake source line (separately committed hook commit).

No shared file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`, `tekimgr.cpp`,
`gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`) received a semantic
change. The `source=nullptr` Teki path (which stores `setCreaturePointer(1, null)`
on the target) is documented in the receiver header.

Root files: `experimental/pikmin2_projectile_engine_receiver.py` (harness),
`tests/test_pikmin2_projectile_engine_receiver.py`,
`docs/PIKMIN2_PROJECTILE_ENGINE_RECEIVER.md`.

## Build evidence (`output/dsw/l20-build-evidence.txt`)

- Native head `610bcf0b6cf6ede72069a31ab82b7907a9c508a2`, clean.
- `nectar.exe` SHA-256 `41719a7d84264623088e0d6ceda1cf404849b8c771fe63e08c26fae3c23af9f7`.
- `ninja -n` → `ninja: no work to do.` (fresh, target `pikmin_pc`).
- Config: Ninja + MinGW g++ 16.2.0, Release, `PIKMIN_NATIVE_JAUDIO=ON`,
  `CMAKE_MAKE_PROGRAM=<python ninja.exe>`.

## Fixture adoption evidence

- Window: `Experimental preview window set to 960x540 windowed and centered`.
- Live starting squad: the current `preview_pikmin2_room` overlay (20 red Pikmin);
  the room also places `preview dwarf bulborb` (`TEKI_Chappy`, the Teki target /
  bound cannon). No extinction; timer-terminated (exit_code=1 is the termination).
- Acceptance run dirs: `output/projectile-engine-receiver/6280aebfc02045df837e8a973d90d82b`
  (rkabuto), `.../d51051022b8f4ace8498d32f50f29bce` (kabuto_actor).

## Six arena gates (Kabuto 75 → Stone 74 → real Teki receiver)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS (source-backed) | `preview dwarf bulborb` generator as the Teki target; fire is FSM-driven (`P2_PROJECTILE_KABUTO_FIRE species=Rkabuto`) |
| 2. Movement + animation | source-backed N/A | projectile is policy-simulated (no rendered model this slice); flight driven by the committed Stone FSM |
| 3. Attacks / receivers | PASS — natural Teki `InteractAttack` 250 | `P2_PROJECTILE_ENGINE_STRIKE kind=Attack damage=250.0 applied=1 stored=0.0->250.0` (×15) |
| 4. Death + corpse | FAIL (honest) | Teki `mStoredDamage` accumulates but the P1 Chappy proxy never `makeDamaged()`s foreign stimuli when idle/wandering, so `mHealth` stays 130 and no corpse drops |
| 5. Transport + reward | UNTESTED | cargo-free room, no Pod; no lethal drop path reached |
| 6. Cleanup + re-entry | PASS | `P2_PROJECTILE_STONE_DESTROY reason=health` (Teki hit) / `reason=wall` (miss); token-keyed contacts; self-hit skipped (`P2_PROJECTILE_SKIP_SELF`) so the cannon's own health is untouched |

Injected vs natural: the fire is FSM-driven (not injected); the receiver mutation
is a real `stimulate()` result, not a direct health write. The **lethal** path is
not observed (gate 4) and is reported FAIL, not papered over. The self-hit fix is
proven by the absence of any `P2_PROJECTILE_ENGINE_STRIKE` on the bound cannon.

### kabuto_actor self-hit evidence (review item 1)

`output/projectile-engine-receiver/d51051022b8f4ace8498d32f50f29bce`:
`P2_PROJECTILE_KABUTO_ACTOR generator=385875968 bound=1 type=3` then ×7
`P2_PROJECTILE_SKIP_SELF target=2031495177920` (once per fire) and **zero**
`P2_PROJECTILE_ENGINE_STRIKE` — the firing Dwarf is never mutated.

### Non-homing Kabuto failure (review item 7, recorded)

`output/dsw/l20-out/runtime/679cc52b377346aa9ccac3048255957c`:
`P2_PROJECTILE_KABUTO_FIRE species=Kabuto homing=0 ...` (×11) +
`P2_PROJECTILE_STONE_DESTROY reason=wall` (×11) → `stone_contact` FAILED because
the straight Stone missed the wandering Dwarf. This backs the "Kabuto did not
reach the Dwarf" assumption; the homing `rkabuto` run is the acceptance channel.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_projectile_engine_receiver.py -q` → 13 passed.
This file covers **only** the Python log-evaluator/config functions
(`build_config`, `parse_engine_strikes`, `evaluate`, `stone_config`/`kabuto_config`,
`rig_bank_text`) — not native behavior, which the real-GL runs above validate.

## Assumptions

- Immediate `mStoredDamage` delta is the valid observability signal for a Teki
  `InteractAttack` (P1 defers Teki damage through `mStoredDamage → makeDamaged()`,
  `tekibteki.cpp:850-858,1863`); `mHealth` only moves once the target's own state
  machine consumes it.
- The canonical `output/pikmin2-room105` converted room was absent this session;
  `dsw/l20-out/converted` is a lane-owned copy of `room.mod`/`room.ini`/`treasure.mod`
  from a prior assembled room run, re-staged idempotently. The harness now
  defaults `--converted` to the canonical path per review item 6.
- The standard-room Dwarf's generator id is `385875968` (discovered via the
  `kabuto_actor` candidate diagnostic), used to bind `kabuto_actor`.

## Remaining blockers (named provider)

- Lethal resolution / corpse / reward: target must consume foreign stored damage
  via its own damage-reaction state or a real P2 Teki FSM — lane 07/10 + #169.
- `navipiki_press_receiver_mutation` UNTESTED at runtime (unit-tested only).
- Generated-session admission and shared Rock/Egg/Bomb consumer parity (21/25/26/27)
  remain outside this slice.

## Subagent usage

Three subagents were dispatched in parallel for the review-slice:

1. `explore` — source audit (Rock.cpp collisionCallback, Kabuto createStoneAttack,
   InteractAttack/InteractPress owner semantics, `setCreaturePointer(1,null)`
   null-safety). **Used as-is**: confirmed the Teki owner=Stone-self→port
   `source=nullptr`, and that the null owner is smart-pointer-safe — directly
   gated the item-3 header edit. ~10 minutes of my own re-reading saved.
2. `explore` — existing-candidate inventory (module/hook/fixture/test/doc list +
   marker strings). **Used as-is** as a cross-check; no conflicts found, one
   correction of memory (the standalone `tools/p2_*` tests are not CMake targets).
   ~5 minutes saved.
3. `general` — harness argparse defaults (`--converted`/`--output` →
   repo-canonical) + pytest docstring note, then ran the focused pytest.
   **Used as-is**; its argparse edit (review item 6) and pytest-note (item 9) are
   in commit `2a70d95`. ~5 minutes saved, net positive.

No subagent built, ran a fixture, committed, or touched native/shared files.

## Exact reproduction

```powershell
$env:PYTHONUTF8='1'
# Acceptance (Teki receiver mutation):
py -3.12 -m experimental.pikmin2_projectile_engine_receiver `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l20-build/bin/nectar.exe `
  --converted C:/Users/alari/pikmin-randomizer/output/dsw/l20-out/converted `
  --mode rkabuto --seconds 45
# Self-hit fix (bound cannon never damaged):
py -3.12 -m experimental.pikmin2_projectile_engine_receiver `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l20-build/bin/nectar.exe `
  --converted C:/Users/alari/pikmin-randomizer/output/dsw/l20-out/converted `
  --mode kabuto_actor --generator 385875968 --seconds 40
```

(Assumes the private native build is already configured with
`-DPIKMIN_NATIVE_JAUDIO=ON -DCMAKE_MAKE_PROGRAM=<python ninja.exe>` and built via
`py -3.12 .../build_lane.py l20`.)

## Slice 2

**Goal:** prove the shared projectile primitives against two real consumers in
one room — (1) a two-Teki room where the bound Kabuto Stone skips itself but
strikes the second Teki through the engine receiver (closing the over-suppression
gap), and (2) a second family (lane-21 Groink) consuming the shared receiver.

### Ordered commits (both branches clean)

Native `deepseek/p2-l20-native` (base `b805d9c6`); root `deepseek/p2-l20` (base
`ef1cace7`).

| Branch | Commit | Subject |
|---|---|---|
| native | `0f235b17` | lane20: two-Teki skip-self->victim and Groink consumer proof hooks (#169) |

Root:

| Commit | Subject |
|---|---|
| `664322e` | lane20: two-Teki room, Groink consumer and victim-strike gates + tests (#169) |
| `45e4b83` | lane20: Slice 2 handoff (#169) |

### Interfaces / hooks touched

- Family-owned host `pc_port/pc_p2_projectiles.cpp` only (no shared file):
  - `groink <mx> <my> <mz> <damage>` row → drives lane-21's
    `p2_groink_classify_hit` / `p2_groink_apply_strike` (included headers, not
    forked) against lane-20's `P2ProjectileReceiverRegistry` for a Bomb strike on
    the live captain Navi. Emits `P2_PROJECTILE_GROINK_RECEIVER_HIT`.
  - `teki_pin <0|1>` row → re-anchors every non-firer Teki to the bound
    `kabuto_actor` each step (injected placement, labelled
    `P2_PROJECTILE_TEKI_PIN`), because the room's two Dwarfs settle ~70 units
    apart and the non-homing Stone would otherwise never reach the victim.
  - setup-time `P2_PROJECTILE_TEKI_ROSTER` diagnostic (all live Teki tokens/poses).
- Root harness `experimental/pikmin2_projectile_engine_receiver.py`: new
  `two_teki` mode (duplicates the Dwarf generator record via `add_second_teki`,
  adds `teki_pin 1` + `groink`), new gates `second_teki_engine_strike` and
  `groink_bomb_receiver_mutation`.
- No lane paths in code/tests/argparse defaults; tests are pure Python.

### Build evidence (`output/dsw/l20-build-evidence.txt`)

- Final native build (clean, post-commit): `lane=l20 target=pikmin_pc`
  `native=0f235b17b1b9fb80bc28317699b72151abbf6c81 dirty=no`,
  `nectar.exe` SHA-256 `d00811ea78d0eb01e625498e98c8caeb6d0722eaced0fb2515c8182de3fd4b8c`,
  `ninja_n="ninja: no work to do."`.

### Fixture adoption evidence

- Window `960x540 windowed and centered`; live 20-red starting squad;
  timer-terminated (native `exit_code=1` is the termination).
- Acceptance run: `output/dsw/l20-out/80293b9e420b4ade900e2f94ad68ebfc` (mode
  `two_teki`, `--generator 385875968`), `second_teki_engine_strike` PASS,
  `groink_bomb_receiver_mutation` PASS.

### Six arena gates (two-Teki + Groink consumer)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS (source-backed) | `kabuto_actor` bound firer + a second live `TEKI_Chappy` victim (`P2_PROJECTILE_TEKI_ROSTER`, distinct token) |
| 2. Movement + animation | N/A (source-backed) | policy-simulated flight, no rendered model this slice |
| 3. Attacks / receivers | PASS — Teki `InteractAttack` 250 | `P2_PROJECTILE_ENGINE_STRIKE target=<victim> stored=0.0->250.0` (×16) |
| 4. Death + corpse | FAIL (honest) | victim `mStoredDamage` accumulates but the P1 Chappy proxy never `makeDamaged()`s foreign stimuli → `mHealth` stays 130, no corpse |
| 5. Transport + reward | UNTESTED | cargo-free arena, no lethal drop path |
| 6. Cleanup + re-entry | PASS | `P2_PROJECTILE_STONE_DESTROY reason=health` (victim hit); firer skip-self untouched |

Injected vs natural: the victim placement is **injected** (`teki_pin`, labelled);
the receiver mutation is a real `stimulate()` result. The second consumer (Groink
Bomb → proxy receiver) is exercised through the same executable via lane-21's own
`p2_groink_apply_strike`, not a fork.

### Tests

`py -3.12 -m pytest tests/test_pikmin2_projectile_engine_receiver.py -q` → 19 passed.
New: `second_teki_engine_strike` (PASS with victim strike, FAIL when the victim
`P2_PROJECTILE_ENGINE_STRIKE` line is stripped), `groink_bomb_receiver_mutation`
(Bomb PASS / Wind FAIL), `two_teki` config + `groink_config` row.

### Subagent usage (honest)

This slice required no subagents: the `task` tool was not available in this
session, so the three-way parallel delegation (source audit / candidate inventory
/ test scaffolding) described in the brief could not be performed. All read-only
investigation and the test/harness/native work were done directly. Net effect:
neutral-to-negative — the read-heavy source audit (`pc_p2_projectiles.cpp`,
`pc_p2_groink_*`, `p2_groink_target_runtime.cpp`) consumed the majority of my own
context, which a parallel `explore` agent would have absorbed instead.

### Assumptions

- The two-Teki proof uses injected victim placement (`teki_pin`) because the two
  `TEKI_Chappy` settle ~70 units apart (observed via `P2_PROJECTILE_TEKI_ROSTER`)
  and the non-homing Stone flies in the firer's facing; this is labelled as
  injected, not natural behaviour.
- The Groink consumer targets the live captain Navi (stationary preview spawn) via
  a muzzle-origin → captain sweep; the full Groink shell-flight/arena remains
  lane-21's fixture (unchanged, not forked).
- `navipiki_press_receiver_mutation` stays UNTESTED at runtime (the Stone strikes
  only Teki in this room).

### Remaining blockers (named provider)

- Lethal resolution / corpse for the victim still FAILs (lane 07/10 + #169).
- Groink-in-room uses a module-level sweep, not lane-21's full shell flight
  (lane 21 / #205).

## Exact reproduction (Slice 2)

```powershell
$env:PYTHONUTF8='1'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l20 -- `
  py -3.12 -m experimental.pikmin2_projectile_engine_receiver `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l20-build/bin/nectar.exe `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --converted C:/Users/alari/pikmin-randomizer/output/dsw/l20-out/converted `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l20-out `
  --mode two_teki --generator 385875968 --seconds 45
```

## Slice 3

**Goal:** flight-to-target without placement injection, and a real engine target
for the second consumer. (1) The primary two-Teki run drops `teki_pin` and proves
the Stone reaches the victim's natural settle in flight; teki_pin stays as a
separately-flagged (and gate-failing) scenario. (2) The Groink Bomb is routed
through the engine receiver on the live captain Navi (stimulate, not the proxy).

### Ordered commits (both branches clean)

| Branch | Commit | Subject |
|---|---|---|
| root `deepseek/p2-l20` | `2917397` | lane20: Slice 2 handoff build evidence (#169) |
| native | `3999ab3d` | lane20: adopt shared p2rockhost ScriptRng/TraceProxy/RockMapBinding extraction (#169) |
| native | `06b88e90` | lane20: route Groink Bomb through engine receiver on the captain Navi (#169) |
| root | `36499ad` | lane20: Slice 3 flight-to-target and Groink engine receiver (harness/tests/docs) (#169) |
| root | `072488b` | lane20: Slice 3 handoff (#169) |

### Interfaces / hooks touched

- `pc_p2_rock_host.{h,cpp}` + CMake line (rebase only, no behaviour change):
  `pc_p2_projectiles.cpp` now uses `p2rockhost::ScriptRng`/`TraceProxy`/
  `RockMapBinding`/`detectRock`/`rngFloat`/`rngInt`, deleting its local forks.
- `tickGroinkConsumer`: classify via lane-21's `p2_groink_classify_hit`, apply via
  this lane's `p2_projectile_apply_engine_strike` (stimulate on the captain Navi),
  emit `P2_PROJECTILE_GROINK_ENGINE_HIT`. `#include "pc_p2_groink_strike.h"`
  dropped (no longer using the proxy bridge).
- Harness: `VICTIM_POS` moved into the fire corridor (`173.6,0,-60`); `build_config`
  takes `teki_pin=` (primary `two_teki` omits it); new gate
  `victim_contact_in_flight` (skip-self + victim strike + no `P2_PROJECTILE_TEKI_PIN`
  + first health-destroy `>=4` traces) and `groink_engine_receiver_navi_hit`
  (Bomb + applied + Navi health decrease); `--assets` now required, `--converted`/
  `--output` derived from repo root via `Path(__file__).parents[3]`, `--teki-pin`
  flag added. No route lanes paths in code/tests.

### Build evidence

- `native=06b88e902bb87482bcddf344f6b1cd0bd7ccdf14 dirty=no`, `nectar.exe`
  SHA-256 `b9f70c4a1517fc6e72bacc044cac36306fafbf78f591393ab53339ce946d58b0`,
  `ninja -n` → `ninja: no work to do.`

### Fixture adoption evidence

- Window `960x540 windowed and centered`; live 20-red squad; timer-terminated
  (`exit_code=1`).
- Primary (natural flight): `output/dsw/l20-out/4c4d2fd239ff49b68da012476a2e105d`,
  `victim_contact_in_flight` PASS, `groink_engine_receiver_navi_hit` PASS.
- Flagged injected: `output/dsw/l20-out/d32dd6420c60448fa3b30217ae8eccf2`,
  `victim_contact_in_flight` FAIL (labelled injected), `second_teki_engine_strike` PASS.

### Six arena gates (natural flight + Groink engine Navi)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | firer + victim both live `TEKI_Chappy`, distinct tokens (`P2_PROJECTILE_TEKI_ROSTER`) |
| 2. Movement + animation | N/A (source-backed) | policy-simulated flight |
| 3. Attacks / receivers | PASS | victim `ENGINE_STRIKE stored=0.0->250.0` in flight; captain Navi `GROINK_ENGINE_HIT health=100.0->90.0` |
| 4. Death + corpse | FAIL (honest) | victim `mStoredDamage` accumulates but the P1 Chappy proxy never `makeDamaged()`s foreign stimuli |
| 5. Transport + reward | UNTESTED | cargo-free arena |
| 6. Cleanup + re-entry | PASS | `STONE_DESTROY reason=health traces=7` (flight); firer untouched |

Injected vs natural: victim placement is now **natural** (1 strike in 9 flights; the wandering victim left the +z corridor after the first contact, fires 2-9 ended reason=wall — integrator correction; formerly "settle-then-freeze", ~58
units downrange); `teki_pin` remains available and is separately flagged so
`victim_contact_in_flight` FAILs when it is used.

### Tests

`py -3.12 -m pytest tests/test_pikmin2_projectile_engine_receiver.py -q` → 24 passed.
New: `victim_contact_in_flight` PASS / FAIL-on-injection / FAIL-birth-frame; and
`groink_engine_receiver_navi_hit` PASS / FAIL-no-health-change / FAIL-wind.
Tests are pure-Python (no native path; no `PIKMIN_NATIVE_ROOT` needed).

### Subagent usage (one line)

The `task` tool is not available in this session, so I worked solo (no subagents).

### Remaining blockers (named provider)

- Victim lethal resolution / corpse still FAIL (lane 07/10 + #169).
- Groink proof still uses a host-supplied sweep (no full shell flight; lane 21/#205).

## Exact reproduction (Slice 3)

```powershell
$env:PYTHONUTF8='1'
# Primary: natural flight to the victim + Groink engine Navi hit
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l20 -- `
  py -3.12 -m experimental.pikmin2_projectile_engine_receiver `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l20-build/bin/nectar.exe `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --converted C:/Users/alari/pikmin-randomizer/output/dsw/l20-out/converted `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l20-out `
  --mode two_teki --generator 385875968 --seconds 45
# Flagged injected scenario (victim_contact_in_flight FAILs by design)
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l20 -- `
  py -3.12 -m experimental.pikmin2_projectile_engine_receiver `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l20-build/bin/nectar.exe `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --converted C:/Users/alari/pikmin-randomizer/output/dsw/l20-out/converted `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l20-out `
  --mode two_teki --generator 385875968 --teki-pin --seconds 40
```


## Slice 4

**Goal:** (1) repeatable flight strikes without pinning — aim the cannon at the
victim's *current* position at fire time (source Kabuto tracks its target) so
most flights contact in flight; (2) exercise the shared Bomb/Egg primitives
through a real consumer on the wave (lane 27's Bombsarai Bomb via
`pc_p2_bombsarai_bomb`), applying its blast to a real Navi through this lane's
engine receiver without forking; (3) fix the engine-receiver header comment and
the slice-3 commit table.

### Ordered commits (both branches clean)

| Branch | Commit | Subject |
|---|---|---|
| native | `48313db7` | lane20: repeatable victim aim + Bombsarai Bomb primitive consumer (#169) |
| root | `4923fc5` | lane20: Slice 4 harness/tests (bomb row + strike-ratio/victim-aim gates) (#169) |
| root | this commit | lane20: Slice 4 doc + handoff (#169) |

(For slice 3, the commit table above now lists the root commits `2917397`,
`36499ad`, `072488b` beside the native ones — integrator carry-forward fix.)

### Interfaces / hooks touched

- Native `pc_p2_projectiles.cpp`:
  - `findVictimTeki(from)` returns the nearest alive non-firer Teki; `fireKabutoStone`
    aims the Stone at its current position at fire time and emits
    `P2_PROJECTILE_KABUTO_AIM`; `P2_PROJECTILE_KABUTO_FIRE` now logs the actual
    aim `face_deg`/`aim`/`source` instead of the static config angle. This
    simulates the source StateTurn `turnToTarget` → `createStoneAttack` fires
    along `mFaceDir` (Kabuto.cpp:279), which the port did not previously do.
  - New `bomb <mx> <my> <mz> <naviPikiDamage>` config row + `tickBombConsumer()` +
    a local `BombMapBinding` static-map trace: captures, drops (Death throw),
    floor-arms and detonates a lane-27 `P2BombSaraiBomb`, then applies its
    `naviPikiDamage` to the live captain Navi through
    `p2_projectile_apply_engine_strike` (this lane's receiver) — emits
    `P2_PROJECTILE_BOMB_THROW/DETONATE/ENGINE_HIT`. Host lifecycle parms are
    documented approximations (`kBomb*`). No fork of `pc_p2_bombsarai_bomb.*`.
  - Diagnostic `P2_PROJECTILE_AIM_NONE` when no alive non-firer Teki remains.
- Native `pc_p2_projectile_engine_receiver.h`: corrected the "Navi/Pikmin strike
  passes the real source" comment — `source` is host-supplied and may be nullptr
  for a Navi target (the Groink and Bomb consumers pass nullptr).
- Root harness: `bomb_config`/`BOMB_ORIGIN`/`BOMB_DAMAGE`, `add_second_teki(count=)`
  scattering `N` victims along the +z corridor, `--victims` flag, `strike_ratio_of`
  helper, and gates `victim_strike_ratio` + `bomb_engine_navi_hit`.

### Build evidence

- `native=48313db7ef86417b6f258b860698ce64f7f6a3ff dirty=no`, `nectar.exe`
  SHA-256 `147b0c66cd3a9e581064e193f5e22d13269def3fc69eb457333823272443389c`,
  `ninja -n` → `ninja: no work to do.`

### Fixture adoption evidence

- Window `960x540 windowed and centered`; live 20-red squad; timer-terminated.
- Primary run `output/dsw/l20-out/97297947365c4f0c83d237b9a22df282` (`two_teki`,
  `--generator 385875968 --victims 12 --seconds 60`): 13/13 gates PASS.

### Six arena gates (repeatable flight + Bomb primitive)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS | 1 firer + 12 victims (`P2_PROJECTILE_TEKI_ROSTER`), distinct tokens |
| 2. Movement + animation | N/A (source-backed) | policy-simulated flight |
| 3. Attacks / receivers | PASS | victim `ENGINE_STRIKE kind=Attack 250` ×11; Pikmin `kind=Press 10` ×6; captain Navi `GROINK_ENGINE_HIT 100→90` then `BOMB_ENGINE_HIT 90→80` |
| 4. Death + corpse | partial (victim death observed, corpse untracked) | `P2_PROJECTILE_AIM_NONE total_teki=13 alive_nonfirer=0` after all 12 victims were struck (250 each) — no corpse marker this slice |
| 5. Transport + reward | UNTESTED | cargo-free room, no Pod |
| 6. Cleanup + re-entry | PASS | `STONE_DESTROY reason=health` (11 flight strikes) / `reason=wall` (4, after victims exhausted); firer untouched (`SKIP_SELF`) |

**Injected vs natural:** the victims are naturally placed dwarfs (not pinned);
`teki_pin` remains a separately-labelled scenario. A `victims=N` corridor is a
host layout choice (more targets ≈ more data), not injected co-location. The
`strike_ratio` over 16 fires is **11/16** hits (PASS): each fire aims at the
surviving victim's current position, strikes it in flight, and the next fire
re-aims at the next survivor.

**Bomb caveat (honest):** the source applies `InteractBomb` to a Navi (not
`InteractAttack`/`InteractPress`), so the captain blast is a **receiver-consumption
proof** of this lane's primitive, not lane-27 Bomb fidelity (same caveat already
recorded for the Groink Navi hit).

### Tests

`py -3.12 -m pytest tests/test_pikmin2_projectile_engine_receiver.py -q` → 32 passed.
Pure-Python (log evaluator + config builders only; no native path, no
`PIKMIN_NATIVE_ROOT`); new `victim_strike_ratio` PASS (9 fires/7 hits) / FAIL
(9/3), and `bomb_engine_navi_hit` PASS/FAIL cases.

### Subagent usage (honest)

Three subagents dispatched in parallel:
1. `explore` source audit (Kabuto turn-to-target + Bombsarai bomb receiver rules)
   → used as-is; confirmed the port never applied the computed target angle, and
   that a Navi bomb blast is `InteractBomb` (fed the bomb-caveat wording).
2. `explore` candidate inventory (native modules + config keywords + markers)
   → used as-is; confirmed there was no `bomb` keyword yet and listed all
   `P2_PROJECTILE*` markers.
3. `general` harness+pytest (bomb row, KABUTO_AIM/BOMB_ENGINE_HIT regexes,
   `strike_ratio_of`, `victim_strike_ratio` + `bomb_engine_navi_hit` gates,
   focused tests) → used as-is; 32 passed. I then added `add_second_teki(count=N)`
   / `--victims` myself.

No subagent built, ran a fixture, committed, or touched native/shared files.

### Remaining blockers (named provider)

- Victim corpse/carry/reward still untracked (no corpse marker this slice; lane
  06/07 + #169). Death is now *observed* (victims become non-alive after 250 hits).
- The Bomb/Egg blast receiver stays `InteractAttack`-mapped (receiver proof, not
  lane-27 fidelity); real `InteractBomb` routing is lane 10/27 scope.
- Egg primitive consumer (TamagoMushi/Egg) not separately exercised this slice;
  the Bomb primitive was the required "one of them".

## Exact reproduction (Slice 4)

```powershell
$env:PYTHONUTF8='1'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l20 -- `
  py -3.12 -m experimental.pikmin2_projectile_engine_receiver `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l20-build/bin/nectar.exe `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --converted C:/Users/alari/pikmin-randomizer/output/dsw/l20-out/converted `
  --output C:/Users/alari/pikmin-randomizer/output/dsw/l20-out `
  --mode two_teki --generator 385875968 --victims 12 --seconds 60
```

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
| `_hash_` (this handoff commit) | lane20: Slice 2 handoff (#169) |

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

- Final native build: `lane=l20 target=pikmin_pc native=610bcf0b… dirty=yes`,
  `nectar.exe` SHA-256 `d00811ea78d0eb01e625498e98c8caeb6d0722eaced0fb2515c8182de3fd4b8c`,
  `ninja_n="ninja: no work to do."` (dirty at evidence time = this slice's
  uncommitted edits; committed after).

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


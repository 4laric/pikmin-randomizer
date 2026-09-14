# Lane 20 — Kabuto Stone → real engine receiver mutation (#169)

Implementation owner: Codex through shared account `4laric`. Executing agent:
DeepSeek (lane 20, `dsw/l20-root` / `dsw/native-l20`).

## What this slice adds

Before this slice lane 20's projectile host seam classified Stone/Rock contacts
and applied every emitted strike **only** to a private host-owned proxy receiver
(`pc_p2_projectile_receiver.*`); engine actor health was deliberately never
mutated. This slice closes the "actual receiver mutation" half of the remaining
ledger work by routing already-classified strikes into the engine's own
interaction primitives, matching source `Rock.cpp:204-238`:

| Contact | Source call | Port call |
|---|---|---|
| grounded Navi/Pikmin | `InteractPress(mSourceEnemy-or-self, mAttackDamage)` | `InteractPress(source, damage)` |
| Teki | `InteractAttack(this, 250.0f, collObj)` | `InteractAttack(source, nullptr, 250.0f, false)` |

Damage is never re-derived; the caller passes the amount the Stone/Rock contact
policy already produced. The proxy receiver is left enabled by default, so the
new engine path is recorded beside the existing proxy path, not instead of it.

## Native changes (worktree `dsw/native-l20`, base `b805d9c6`)

- `pc_port/pc_p2_projectile_engine_receiver.{h,cpp}` — engine-aware, additive,
  family-local receiver. `p2_projectile_apply_engine_strike()` calls
  `Creature::stimulate(InteractAttack/InteractPress)` and returns an observed
  outcome (applied/rejected, `mHealth` before/after, Teki `mStoredDamage`
  before/after). No shared of any engine field is written directly.
- `pc_port/pc_p2_projectiles.cpp` — opt-in `engine_receiver <0|1>` config row
  (default 0, proxy-only unchanged); `detectStoneContacts` / `detectRockContacts`
  additionally route each emitted strike through the engine receiver and log
  `P2_PROJECTILE_ENGINE_STRIKE` (and `..._NOP` for a non-applied live target). A
  Teki strike passes `source=nullptr` (source attributes Teki damage to the Stone
  `this`, which has no live Creature in this host); a grounded Navi/Pikmin strike
  passes `source =` the bound `kabuto_actor` when present.
- `CMakeLists.txt` — one additive source line (separate hook commit).

No shared file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`, `tekimgr.cpp`,
`gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`) was edited; the host seam
is already registered through the existing batch-2 setup/update/forget hooks.

## Root harness / tests / docs

- `experimental/pikmin2_projectile_engine_receiver.py` — stages a fresh
  `--experimental-pikmin2-room` room via `scripts.preview_pikmin2_room.prepare`,
  writes a `p2-projectiles.txt`, launches the built `nectar.exe` (PATH prepended
  with `C:\msys64\mingw64\bin`), and evaluates the log markers. Three modes:
  `stone` (deterministic Teki contact), `kabuto` (non-homing FSM fire),
  `rkabuto` (homing FSM fire).
- `tests/test_pikmin2_projectile_engine_receiver.py` — 9 focused tests covering
  config generation, marker parsing, Teki-attack / Navi-Piki-press mutation
  evaluation, immunity rejection and the window gate.
- `docs/PIKMIN2_PROJECTILE_ENGINE_RECEIVER.md` — this document.

## Runtime evidence

Private `nectar.exe` head `e9bb1661` (see handoff). `rkabuto` run (the full
ordinary-cannon chain) at
`output/dsw/l20-out/runtime/c98e56b1ce5b49d79b48b95f2aca962b`:

```
P2_PROJECTILE_KABUTO_FIRE species=Rkabuto homing=1 ...
P2_PROJECTILE_STRIKE kind=Attack damage=250.0 target=… health_zeroed=1
P2_PROJECTILE_ENGINE_STRIKE target=… kind=Attack damage=250.0 applied=1 rejected=0 health=130.0->130.0 stored=0.0->250.0 source=0
P2_PROJECTILE_ENGINE_STRIKE … stored=250.0->500.0 …  (14 applied Teki strikes)
```

`stone` run (deterministic single Teki contact) at
`output/dsw/l20-out/runtime/47b1839fcaea471faaae00dd098c5a20` shows the same
`stored=0.0->250.0` mutation with `P2_PROJECTILE_STONE_DESTROY` teardown.

## Six arena gates (Kabuto 75 → Stone 74 → live Teki receiver)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS (source-backed) | room's `preview dwarf bulborb` generator as the Teki target; cannon fire is FSM-driven (`P2_PROJECTILE_KABUTO_*`) |
| 2. Movement + animation | N/A (source-backed) | projectile is policy-simulated (no rendered model in this slice); fire/flight driven by the committed Stone FSM |
| 3. Attacks / receivers | PASS — Teki `InteractAttack` 250 | `P2_PROJECTILE_ENGINE_STRIKE kind=Attack applied=1 stored=0.0->250.0` (×14) |
| 4. Death + corpse | FAIL (honest) | Teki `mStoredDamage` accumulates (0→3500) but the P1 Chappy proxy never `makeDamaged()`s foreign stimuli in idle/wander, so `mHealth` stays 130 and no corpse drops |
| 5. Transport + reward | UNTESTED | cargo-free arena, no Pod; no lethal drop path reached |
| 6. Cleanup + re-entry | PASS | `P2_PROJECTILE_STONE_DESTROY reason=wall` after each breaking Stone; no stale Teki pointer (contacts are token-keyed) |

Injected vs natural: the Stone fire is FSM-driven (not injected); the receiver
mutation is a real `stimulate()` result, not a direct health write. The
**lethal** path is not observed for the reason in gate 4 and is reported FAIL,
not papered over.

## Remaining blockers (named provider)

- Lethal resolution / death / corpse for the Dwarf proxy: the target must consume
  foreign stored damage via its own damage-reaction state, or a real P2 Teki FSM
  must provide it — depends on lane 07/10 (receiver/lifetime) and the generated
  session (#169).
- `navipiki_press_receiver_mutation` remains UNTESTED: the homing Stone converged
  on the Pikmin-swarmed Dwarf (a Teki), not a grounded Pikmin. It is exercised
  only in the unit tests and a direct `stone`-into-a-Pikmin configuration was not
  run this slice.
- The moving muzzle / sampled-clock / actor-binding inputs (already integrated)
  were not re-exercised here; only the ordinary FSM + receiver slice is new.

## Reproduction

```powershell
$env:PYTHONUTF8='1'
py -3.12 -m experimental.pikmin2_projectile_engine_receiver `
  --exe C:/Users/alari/pikmin-randomizer/output/dsw/native-l20-build/bin/nectar.exe `
  --converted C:/Users/alari/pikmin-randomizer/output/dsw/l20-out/converted `
  --mode rkabuto --seconds 45
```

The `--converted` room is a lane-owned copy of `room.mod`/`room.ini`/`treasure.mod`
from a prior assembled room run (the canonical `output/pikmin2-room105` directory
was absent from the shared `output/` at this session; see the handoff for the
provenance).

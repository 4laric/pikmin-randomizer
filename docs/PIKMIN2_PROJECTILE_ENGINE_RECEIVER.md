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

Private `nectar.exe` head `610bcf0b` (see handoff). The `rkabuto` run is the
ordinary-cannon acceptance channel (homing Stone → live Teki receiver) at
`output/projectile-engine-receiver/6280aebfc02045df837e8a973d90d82b`:

```
P2_PROJECTILE_KABUTO_FIRE species=Rkabuto homing=1 ...
P2_PROJECTILE_STRIKE kind=Attack damage=250.0 target=… health_zeroed=1
P2_PROJECTILE_ENGINE_STRIKE target=… kind=Attack damage=250.0 applied=1 rejected=0 health=130.0->130.0 stored=0.0->250.0 source=0
P2_PROJECTILE_ENGINE_STRIKE … stored=250.0->500.0 …  (15 applied Teki strikes)
P2_PROJECTILE_STONE_DESTROY reason=health  (×15: Stone breaks on the Teki it hit)
```

A `reason=health` Stone destruction is the expected teardown for a Teki hit
(source `Rock.cpp:230-232` zeroes the Stone's own health on a non-Navi/Piki
contact). Compare the non-homing `kabuto` run (below), whose Stone misses the
wandering Dwarf and destructs with `reason=wall`.

### Review fix: Kabuto actor self-hit (the cannon is never damaged by its own Stone)

With `kabuto_actor` + `engine_receiver 1` bound, the Stone is born 25 units
above its own firing Teki (inside `collisionRadius 40` + host pad) and used to
apply a real `InteractAttack(250)` to the cannon itself. The fix skips the bound
actor in `detectStoneContacts` and passes `tokenOf(kabutoActor)` as the Stone
source token so the source-grace matches the real firer.

`kabuto_actor` run at
`output/projectile-engine-receiver/d51051022b8f4ace8498d32f50f29bce`:

```
P2_PROJECTILE_KABUTO_ACTOR generator=385875968 bound=1 type=3 pos=(173.6,0.0,-143.2)
P2_PROJECTILE_KABUTO_FIRE species=Kabuto homing=0 rig=1 ... fire=1..7
P2_PROJECTILE_SKIP_SELF target=2031495177920    (exactly once per fire, ×7)
P2_PROJECTILE_STONE_DESTROY reason=wall         (×7, Stone misses)
```

Zero `P2_PROJECTILE_ENGINE_STRIKE` lines appear: the firing Dwarf (type 3,
`TEKI_Chappy`) is never mutated, proving the cannon's own health is unchanged.

## Six arena gates (Kabuto 75 → Stone 74 → live Teki receiver)

| Gate | Result | Evidence |
|---|---|---|
| 1. Identity + spawn | PASS (source-backed) | room's `preview dwarf bulborb` generator as the Teki target; cannon fire is FSM-driven (`P2_PROJECTILE_KABUTO_*`) |
| 2. Movement + animation | N/A (source-backed) | projectile is policy-simulated (no rendered model in this slice); fire/flight driven by the committed Stone FSM |
| 3. Attacks / receivers | PASS — Teki `InteractAttack` 250 | `P2_PROJECTILE_ENGINE_STRIKE kind=Attack applied=1 stored=0.0->250.0` (×15) |
| 4. Death + corpse | FAIL (honest) | Teki `mStoredDamage` accumulates but the P1 Chappy proxy never `makeDamaged()`s foreign stimuli in idle/wander, so `mHealth` stays 130 and no corpse drops |
| 5. Transport + reward | UNTESTED | cargo-free arena, no Pod; no lethal drop path reached |
| 6. Cleanup + re-entry | PASS | `P2_PROJECTILE_STONE_DESTROY reason=health` (Teki hit) / `reason=wall` (miss); token-keyed contacts leave no stale pointer; self-hit is separately skipped (`P2_PROJECTILE_SKIP_SELF`) |

Injected vs natural: the Stone fire is FSM-driven (not injected); the receiver
mutation is a real `stimulate()` result, not a direct health write. The
**lethal** path is not observed for the reason in gate 4 and is reported FAIL,
not papered over. The self-hit fix (gate 6 / new) is proven by the absence of any
`P2_PROJECTILE_ENGINE_STRIKE` on the bound cannon.

### Non-homing Kabuto run (missed, reported for completeness)

The straight `kabuto` configuration (non-homing, no actor binding) fired but the
Stone flew past the wandering Dwarf into a wall, so `stone_contact` (and the
receiver hit) FAILED in that configuration:

`output/dsw/l20-out/runtime/679cc52b377346aa9ccac3048255957c` →
`P2_PROJECTILE_KABUTO_FIRE species=Kabuto homing=0 ...` (×11) and
`P2_PROJECTILE_STONE_DESTROY reason=wall` (×11). This backs the "Kabuto did not
reach the Dwarf" assumption and is why the homing `rkabuto` run is the acceptance
channel.

## Tests

`tests/test_pikmin2_projectile_engine_receiver.py` covers **only** the Python
log-evaluator/config functions (`build_config`, `parse_engine_strikes`,
`evaluate`, `stone_config`, `kabuto_config`, `rig_bank_text`), not the native
engine behavior; the native receiver mutation is validated by the real-GL
runtime evidence above, not by pytest.

## Remaining blockers (named provider)

- Lethal resolution / death / corpse for the Dwarf proxy: the target must consume
  foreign stored damage via its own damage-reaction state, or a real P2 Teki FSM
  must provide it — depends on lane 07/10 (receiver/lifetime) and the generated
  session (#169).
- `navipiki_press_receiver_mutation` remains UNTESTED: the homing Stone converged
  on the Pikmin-swarmed Dwarf (a Teki), not a grounded Pikmin. It is exercised
  only in the unit tests.
- `kabuto_actor` self-hit evidence uses the standard room's Dwarf as the bound
  cannon; a real Kabuto actor (source bank/motion) is still the remaining
  generated-session work.

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

## Slice 2 — two real consumers in one room

### Provider interface changes (this slice)

- New opt-in config rows in the family-owned host `pc_p2_projectiles.cpp`:
  - `groink <mx> <my> <mz> <damage>` — drives **lane-21's Groink strike bridge**
    (`p2_groink_classify_hit` / `p2_groink_apply_strike` from `pc_p2_groink_hit.h`
    / `pc_p2_groink_strike.h`) against **this lane's** `P2ProjectileReceiverRegistry`
    for a Bomb strike on the live captain Navi. The sweep is the
    muzzle-origin → live-captain segment (the host supplies it because the Groink
    policy owns no actor). Lane-21's modules are not forked: their headers are
    included and their functions called as-is.
  - `teki_pin <0|1>` — injected victim placement for the two-Teki proof: every
    Teki other than the bound `kabuto_actor` is re-anchored to the firer each
    step, so the Stone's birth-frame contact deterministically reaches the second
    Teki. Clearly labelled injected (marker `P2_PROJECTILE_TEKI_PIN`); the room's
    two Dwarf Bulborbs otherwise wander ~70 units apart.
- New markers: `P2_PROJECTILE_GROINK_RECEIVER_HIT`, `P2_PROJECTILE_TEKI_ROSTER`
  (setup-time two-Teki diagnostic), `P2_PROJECTILE_TEKI_PIN`.

### Two-Teki proof (consumer #1: Kabuto Stone → real engine receiver)

The room now carries **two** live `TEKI_Chappy` (the standard Dwarf bound as the
Kabuto firer plus a duplicated victim Dwarf). On every fire the Stone skips its
own firer but still strikes the *second* Teki through the real engine receiver,
proving skip-self closes the self-hit without over-suppressing other Teki:

```
P2_PROJECTILE_KABUTO_ACTOR bound=1 pos=(173.6,0.0,-143.2)   # firer
P2_PROJECTILE_TEKI_ROSTER token=…016 type=3 gen=385875968    # firer
P2_PROJECTILE_TEKI_ROSTER token=…544 type=3 gen=419430400    # victim (distinct token)
P2_PROJECTILE_TEKI_PIN injected=1 anchor=…016
P2_PROJECTILE_SKIP_SELF target=…016                          # firer skipped (once per fire)
P2_PROJECTILE_ENGINE_STRIKE target=…544 kind=Attack damage=250 applied=1 stored=0.0->250.0  # victim struck
```

The `second_teki_engine_strike` gate passes only when a skip-self exists AND at
least one applied Teki `InteractAttack` lands on a token that is **not** the
skipped firer; stripping the victim `P2_PROJECTILE_ENGINE_STRIKE` line flips it
to FAIL (pytest-covered).

### Second consumer (consumer #2: lane-21 Groink → shared receiver)

The Groink Bomb strike maps onto this lane's proxy receiver through lane-21's own
`p2_groink_apply_strike`, exercised in the same room/executable:

```
P2_PROJECTILE_GROINK_RECEIVER_HIT token=<captain> kind=Bomb damage=10.0 applied=1 died=0 health=10.0
```

This reuses the intersecting `pc_p2_groink_strike.cpp` already linked into
`pikmin_pc`; no Groink module was copied or changed. (Lane-21 still owns the
full shell-flight/arena fixture; this slice proves the receiver consumption.)

### Runtime evidence

`output/dsw/l20-out/80293b9e420b4ade900e2f94ad68ebfc` (mode `two_teki`,
`nectar.exe` head `610bcf0b` + this slice's uncommitted native edits, SHA-256
`d00811ea78d0eb01e625498e98c8caeb6d0722eaced0fb2515c8182de3fd4b8c`):

- `second_teki_engine_strike` PASS (16 applied victim strikes; firer skipped ×16).
- `groink_bomb_receiver_mutation` PASS.
- `navipiki_press_receiver_mutation` UNTESTED (the Stone strikes only Teki here).

# Lane 13 gate B — Dwarf Orange Bulborb (BlueKochappy 44) native KochappyBase FSM

This slice upgrades lane-13 gate B (source behavior) for the Dwarf Orange
Bulborb from the host P1-AI proxy to a native source FSM. It is **opt-in and
defaults OFF**: the module is inert unless the private arena carries
`p2-dwarf-orange-fsm.txt`, so the existing host-AI combat, delivery and restart
evidence is unchanged.

Source of truth: read-only decomp `native/pikmin2-research`
(`include/Game/Entities/KochappyBase.h`, `src/plugProjectYamashitaU/kochappyState.cpp`,
`KochappyBase.cpp`) and the audited retail block in
`docs/PIKMIN2_DWARF_VARIANTS.md` §2/§3.

## 1. Opt-in and module

- `pc_port/pc_p2_kochappy_fsm.{h,cpp}` + `pc_port/pc_p2_kochappy_fsm_policy.h`.
- Enabled only when `p2-dwarf-orange-fsm.txt` exists in the process working
  directory. The first token must be `P2_DWARF_ORANGE_FSM_1`; optional
  whitespace-separated `key value` overrides are accepted for the ten audited
  parameters. Unknown keys, duplicates, non-finite/out-of-range values and
  trailing junk are rejected (`std::abort`) before any actor is touched.
- With no config file the setup returns immediately: no markers, no AI
  suppression, no motion writes.
- Ownership comes from `pc_p2_dwarf_orange_registered`; the module never
  re-resolves identity or reloads the converted bank. Visuals reuse
  `pc_p2_dwarf_orange_draw` (the FSM drives the host motion index per state).

## 2. Source state / parm / timing mapping

Covered states (`P2_KOCHAPPY_STATE state=...`):

| State | Host motion | Source entry | Notes |
| --- | --- | --- | --- |
| Walk | `Move1` | sight fp12=95, move fp06=60; attack gate fp20=30 / fp21=20° | loops; territory fp09=500, home fp10=80 |
| Wait | `Wait1` | nearest Pike/Navi in sight; notice delay | source Turn collapsed into Walk |
| Attack | `Attack` | frame 8 `InteractAttack` (fp22=35, fp24=10) | attack clip 90f/3.0 s |
| Flick | `Flick` | frame 31 `InteractFlick` (fp19=17, fp17=50) | flick clip 80f/2.667 s |
| Dead | `Dead` | health ≤ 0 | dead clip 90f/3.0 s then host `die()` |

Source timing constants are frames at the engine's fixed 30 fps. Health
fp00=250 is reused from `pc_p2_dwarf_orange` and re-asserted here. The nearest
target is stored on the host creature-pointer slot 0, mirroring source
`enemy->mTargetCreature = target`.

## 3. Additive wiring

- `CMakeLists.txt`: adds `pc_port/pc_p2_kochappy_fsm.cpp`.
- `pc_port/pc_p2_preview.cpp`: `pc_p2_kochappy_fsm_setup()` after
  `pc_p2_dwarf_orange_setup()`.
- `src/plugPikiNakata/tekibteki.cpp`: `pc_p2_kochappy_fsm_update(this)` in
  `BTeki::update`, and `pc_p2_kochappy_fsm_suppress_ai(this)` in `BTeki::doAI`.
- `src/plugPikiNakata/tekimgr.cpp`: reset/forget symmetric with the Dwarf
  Orange module.

Every hook is a no-op for unregistered actors and for the default-OFF path.

## 4. Build provenance

- Native worktree `output/native-lane13-orange-fsm` @
  `099b022c50e9f0145d3f911655c95c577fc79d80` (base `27c560e6`).
- Private build `output/native-lane13-orange-fsm-build`, Ninja / MinGW
  `g++ 16.2.0`, `Release`, `PIKMIN_NATIVE_JAUDIO=ON`, `-j 6`.
  `ninja -n` → `ninja: no work to do.`
- `bin/nectar.exe` SHA-256
  `BFADD058011D1F5584E6027319E0D97760ADC27F7B7F8AF3FB3A7031C6BE1C5C`.
- Fixture `output/p2-lane13-orange-fsm-fixture/baseline/fixture.exe` SHA-256
  `D189CD8D80A55E47B06C29585C02AE25951FB135C33C9DAAE434967D562457B9`
  (`status=built`, expected native head `27c560e6`).

Tooling note: the combined lane-13 head pushes CMake's final link command over
its response-file threshold, so `scripts/build_pikmin2_fixture.py` now expands
Ninja response files (generated with `ninja -d keeprsp`) instead of rejecting
them. The low-level `windows_args` strictness test is unchanged.

## 5. Runtime evidence (960x540 centred window)

Arena: copy of `output/p2-lane13-orange-arena2/bd2b9fff954a474b88a7f6e467314cfc`
plus `p2-dwarf-orange-fsm.txt` (ON) / without it (OFF). One fixture, one actor
(`211001`), 20 free red Pikmin.

Opt-in ON (`output/p2-lane13-orange-fsm-on5/native.log`):

```text
P2_ENEMY_READY species=BlueKochappy source_id=44 native_family=Chappy generator=211001
  x=-150.0000000 y=30.0000000 z=1850.0000000 health=250.0 max_health=250.0
  behavior=native source_FSM=implemented move_speed=60 sight=95 attack_range=30 attack_angle=20
P2_KOCHAPPY_STATE generator=211001 state=wait
P2_KOCHAPPY_STATE generator=211001 state=walk
P2_KOCHAPPY_STATE generator=211001 state=attack
P2_KOCHAPPY_ATTACK generator=211001 frame=8 damage=10
... 15 walk/attack transitions ...
```

Flick is reached from Wait/Walk when a Pikmin touches while no target is
engaged; it was observed in an intermediate tuning run of the same module
(`output/p2-lane13-orange-fsm-on2/native.log`):

```text
P2_KOCHAPPY_STATE generator=211001 state=wait
P2_KOCHAPPY_STATE generator=211001 state=walk
P2_KOCHAPPY_STATE generator=211001 state=flick
P2_KOCHAPPY_FLICK generator=211001 frame=31
```

Opt-in OFF regression (`output/p2-lane13-orange-fsm-off/native.log`): the
original marker is intact and no FSM marker appears (0 matches), and the
observer completes normally with the corpse:

```text
P2_ENEMY_READY species=BlueKochappy source_id=44 ... behavior=P1 purple_stun=bluekochappy_5s
P2_DWARF_ORANGE_COMBAT tick=245 health=0.0000 state=0 ... corpses=1
DONE P2_DWARF_ORANGE_COMBAT
```

Dead was implemented and unit-covered but not reached in the single ON run:
the free squad did not land damage on the suppressed-AI source actor, so the
source health never reached 0. No state was injected to force it.

## 6. Admission gates

| Gate | Status | Evidence |
|---|---|---|
| A Identity/content | PASS (unchanged) | `P2_ENEMY_READY source_id=44`, Dwarf Orange bank |
| B Source behavior | PASS (opt-in candidate) | source FSM + `source_FSM=implemented`; wait/walk/attack observed, flick tuned, dead implemented |
| C Combat/receivers | PASS at P1-proxy level (unchanged) | frame-8 `InteractAttack`; existing squad combat |
| D Death/drop/transport | PASS at P1-proxy level (unchanged) | host corpse via `die()` after the dead clip |
| E Lifetime | BLOCKED (unchanged) | #397 swap precondition |
| F Persistence | PASS (unchanged) | restart evidence untouched |
| G Product/mixed scene | BLOCKED (unchanged) | not integrated |

## 7. Partial states / events (recorded)

- Turn, TurnToHome, GoHome: collapsed into the Walk territory/home branch; the
  source `waitact1` Turn clip is not played.
- Press (squash) and Demo: not entered; the host corpse handoff owns the
  carrier motion and `die()` replaces `kill(nullptr)`.
- Attack eat/swallow: `eatPikmin`, the frame-88 swallow and white-Pikmin
  poison are not modelled.
- Flick: the `EnemyFunc::isStartFlick` stuck-Pikmin latch is approximated by a
  contact radius; attack posture takes precedence over flick.
- Wait notice cry (`PSSE_EN_KOCHAPPY_NOTICE`) and all SFX/effects are omitted.
- Turn rate 2.0 rad/s is a recorded adaptation (host drive API takes a rate).

## 8. Tests

- `tests/test_pikmin2_kochappy_fsm.py` compiles `pc_p2_kochappy_fsm_policy.h`
  and checks the default source parms, the five state names, the accepted
  magic/override grammar, and rejection of bad magic, unknown/duplicate keys,
  missing/non-finite/out-of-range values and trailing junk.
- `tests/test_pikmin2_fixture_build.py` covers the response-file expansion.

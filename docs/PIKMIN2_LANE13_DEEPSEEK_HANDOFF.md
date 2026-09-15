# Lane 13 (DeepSeek) handoff — Dwarf Orange Bulborb eat/swallow receiver

Parent issue #120; coordination #186. Executing session: opencode/deepseek
(lane 13). Implementation owner: Codex via shared account `4laric`.

## Source IDs and files owned

- Source ID: **44 — BlueKochappy (Dwarf Orange Bulborb)** on the shared
  `Game::KochappyBase` Dwarf Bulborb base. Source of truth: read-only decomp
  `native/pikmin2-research` (`include/Game/Entities/KochappyBase.h`,
  `src/plugProjectYamashitaU/kochappyState.cpp`,
  `src/plugProjectYamashitaU/enemyAction.cpp` — `EnemyFunc::eatPikmin` /
  `swallowPikmin` / `attackNavi`).

Files owned (native worktree `output/dsw/native-l13`):

- `pc_port/pc_p2_kochappy_fsm.{h,cpp}`, `pc_port/pc_p2_kochappy_fsm_policy.h`

Root worktree `output/dsw/l13-root`:

- `experimental/pikmin2_dwarf_orange_fsm_witness.py` (few-Pikmin eat/swallow witness)
- `tests/test_pikmin2_kochappy_fsm.py` (policy-compile test + new parms)

## The slice

The ledger's lane-13 remaining work was "partial KochappyBase FSM integrated but
opt-in; remaining states and generated-session acceptance remain". The previous
owner (Codex) had already implemented the full 9-state FSM + generated bind on
`codex/p2-sweep437`. Reusing that (cherry-pick, not reimplementation), this slice
closes the **remaining receiver gap in source `KochappyBase::StateAttack`**: the
`eatPikmin` / frame-88 `swallowPikmin` / white-Pikmin poison chain, documented as
"not modelled" in `docs/PIKMIN2_KOCHAPPY_FSM.md`. It is the "one exact variant"
natural combat/receiver advancement for source ID 44.

## Ordered commits

Native branch `deepseek/p2-l13-native`, base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`
(clean, no dirty state at head `ba9c014d`):

1. `86f5b3d4` — cherry-pick of `390688e8` (reuse): full KochappyBase Turn/TurnToHome/GoHome/Press states and Dead path
2. `aa83c2cc` — cherry-pick of `8c389f90` (reuse): apply queued Pikmin damage inside the FSM
3. `01b93f50` — cherry-pick of `4ec96e86` (reuse): finalize the FSM Dead carcass outside doAI
4. `1e2fe3b7` — lane13: model source eatPikmin/swallowPikmin and white-Pikmin poison (#120)
5. `8de7ee5d` — lane13: measure eat reach from actor centre at fp22 with slot-aware EAT marker (#120)
6. `766de89f` — lane13: re-assert FSM health override once after actor birth (#120)
7. `ba9c014d` — lane13: hold health override until first natural damage (survives birth reset) (#120)

The three cherry-picks reproduce the previous owner's private lane-13 work from
`codex/p2-sweep437` (which is not yet on the integrated `codex/p2-main-review-native`);
they are reused verbatim, not reimplemented, and only touch the family-local FSM files.
The generated-bind commit (`f33af8db`) and the gate-E cleanup commit (`97bffb22`) were
deliberately NOT taken: they depend on the shared `pc_randomizer_p2_bound_source`
generated-seed bridge and touch shared files (`gameCoreSection.cpp`, `genteki.cpp`);
those remain the previous owner's generated-session-acceptance work for lane 01/03.

Root branch `deepseek/p2-l13`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`
(clean, no dirty state at head `c886c85`):

1. `c886c85` — lane13: Dwarf Orange eat/swallow receiver — policy tests and few-Pikmin witness (#120)

## Interfaces / hooks touched and why

Family-local only, no shared-file edits this slice (all hooks were already wired by
the integrated `pc_p2_kochappy_fsm` on the base):

- `p2kochappyfsm::Params` gained `eatRange` (default 35.0, source mouth-slot radius 15
  measured at the "kamu" joint; the P1 Chappy vehicle exposes no reliable mouth-joint
  world position, so the bite reach is measured from the actor centre at fp22 attack-hit
  range 35 — recorded adaptation) and `poisonDamage` (default 300.0, proper fp02).
- `parseConfig` accepts `eat_range` / `poison_damage` keys and rejects out-of-range values.
- `pc_p2_kochappy_fsm_update` Attack state now mirrors source `StateAttack::exec`:
  KEYEVENT_2 (frame 8) `InteractAttack` bite + `doEat` (stick a free Pikmin to a free
  `getFreeSlot()` mouth slot via `InteractSwallow`; one-shot eat if no slot), and
  KEYEVENT_3 (frame 88) `doSwallow` (iterate `Stickers`, `InteractKill` mouth-stuck
  Pikmin; a White Pikmin applies `poisonDamage` to `mStoredDamage`). New markers
  `P2_KOCHAPPY_EAT` (frame, eaten, slot) and `P2_KOCHAPPY_SWALLOW` (frame, swallowed, white).
- `pc_p2_kochappy_fsm_update` re-asserts `actor->mHealth = params.health` on each update
  until the first natural Pikmin damage, because the P1 Chappy birth re-initialises health
  from its `TPF_Life` policy one frame after adoption (default 250 is a no-op).

No hook changes to `teki.h`, `tekibteki.cpp`, `tekimgr.cpp`, `gameCoreSection.cpp`,
`navi.cpp`, `pc_p2_preview.cpp` or CMake were required for this slice.

## Build evidence (`output/dsw/l13-build-evidence.txt`)

Final line (head `ba9c014d`; all four native builds recorded `ninja_n="ninja: no work to do."`):

```
2026-09-14T21:28:12 lane=l13 target=pikmin_pc native=ba9c014d6c79cb4fe7091dc14d908195b9f90db8 dirty=no
build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l13-build
exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l13-build\bin\nectar.exe
sha256=f0ad4fdca6eee4787caf48ee69112f8b0553b672f0a910c326ee8504df42443b ninja_n="ninja: no work to do." seconds=84
```

Fixture (replacement-main witness) built by
`scripts/build_pikmin2_fixture.py` (`status=built`), provenance at
`output/dsw/l13-out/witness-fixture6/baseline/provenance.json`;
`fixture.exe` SHA-256 `7712e529c8976af5e6b7ad1eb2e63ff22552b8263397d7550d96d171d641a2ec`.

## Fixture baseline adoption

- Root overlay `scripts/preview_pikmin2_room.overlay()` → `ensure_pikmin_squad()`: present
  (`[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`).
- Native startup: `[PC Port] Experimental preview window set to 960x540 windowed and centered`
  and `SDL2 Window & OpenGL Context initialized successfully (960x540)` observed.
- `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1` set; run wrapped in
  `slot.py run gl l13 --` (single-GL lock).
- Live starting squad + active gameplay, no extinction (`no_extinction=true`).

## Six arena gates (source ID 44, Dwarf Orange)

| Gate | Status | Evidence | Natural vs injected |
|---|---|---|---|
| 1 Identity/spawn | PASS | `P2_ENEMY_READY species=BlueKochappy source_id=44`, 64-pose bank, birth XYZ | natural (reused setup) |
| 2 Movement/anim | PASS | FSM `wait/turn/walk/attack/dead` states + `P2_KOCHAPPY_POS` | natural (FSM, no injection) |
| 3 Attacks/receivers | PASS | `P2_KOCHAPPY_EAT frame=8 eaten=1 slot=1` (×2) and `P2_KOCHAPPY_SWALLOW frame=88 swallowed=1 white=0`; bite `P2_KOCHAPPY_ATTACK damage=10` | natural — real Pikmin attack damage drives health 250→0; squad throttle is an observation control (idle Pikmin relocated, no enemy health/state/animation writes) |
| 4 Death/corpse | PASS | `P2_KOCHAPPY_DEAD health=0.0` → `P2_KOCHAPPY_CORPSE native=host_escape_now` | natural (reused Dead path) |
| 5 Transport/reward | UNTESTED this slice | not exercised; prior P1-proxy corpse-carry evidence exists, not re-run | — |
| 6 Cleanup/re-entry | BLOCKED | shared #397 manager-swap precondition (same as prior FSM gate E) | — |

White-pikmin poison (`white=0`) is source-backed N/A: the fixture carries 20 red
Pikmin and no White Pikmin; `pc_p2_is_white` is gated off, so the `eatWhitePikminCallBack`
equivalent is implemented but UNTESTED at runtime.

## Runtime evidence

Run `output/dsw/l13-out/run-evidence6/native.log` (exit 1 — see note below):

```text
P2_KOCHAPPY_STATE generator=211001 state=wait
P2_KOCHAPPY_STATE generator=211001 state=turn
P2_KOCHAPPY_STATE generator=211001 state=walk
P2_KOCHAPPY_STATE generator=211001 state=attack
P2_KOCHAPPY_ATTACK generator=211001 frame=8 damage=10
P2_KOCHAPPY_EAT generator=211001 frame=8 eaten=1 slot=1
P2_KOCHAPPY_SWALLOW generator=211001 frame=88 swallowed=1 white=0
P2_KOCHAPPY_STATE generator=211001 state=turn
P2_KOCHAPPY_STATE generator=211001 state=walk
P2_KOCHAPPY_STATE generator=211001 state=attack
P2_KOCHAPPY_ATTACK generator=211001 frame=8 damage=10
P2_KOCHAPPY_EAT generator=211001 frame=8 eaten=1 slot=1
P2_KOCHAPPY_STATE generator=211001 state=dead
P2_KOCHAPPY_DEAD generator=211001 source_id=44 health=0.0
P2_KOCHAPPY_CORPSE generator=211001 source_id=44 native=host_escape_now
```

Note on exit code: the base (Red-dwarf-derived) combat observer aborts at its
tick-240 deployment with `FAIL p2 room: expected20Pikmin` because the enemy EATS one
Pikmin, dropping the alive count to 19. This is a legacy observer assertion incompatible
with the eat receiver; it fires only after the eat/swallow markers are already captured.
The eat/swallow markers are the acceptance evidence; the `expected20Pikmin` abort is a
fixture artefact, not an FSM failure.

Earlier diagnostic runs (`run-evidence2/3/4`) attempted an injected `health 2500`
config to reach the frame-88 swallow, but the P1 Chappy birth reset defeated the
one-time re-assert; they are NOT used as acceptance. The final run uses natural
health 250 and a 3-Pikmin observation squad only.

## Tests run

- `P2_NATIVE_PC_PORT=.../native-l13/pc_port py -3.12 -m pytest tests/test_pikmin2_kochappy_fsm.py -q` → `1 passed`
  (compiles `pc_p2_kochappy_fsm_policy.h` as C++, asserts 9-state enum/defaults +
  new `eat_range 35` / `poison_damage 300` parse and rejection cases).

## Assumptions

- `eatRange` default 35.0 (fp22) in place of the source mouth-slot radius of 15, because
  the P1 Chappy vehicle exposes no reliable mouth-joint ("kamu") world position; a 15-unit
  radius from the actor centre finds no Pikmin at bite time. Recorded in the policy header.
- "Natural" combat for this observation uses a 3-Pikmin encounter (relocating 17 of the
  overlay's 20 starting reds to a distant idle point). This is an observation control like
  the Mamuta engineered floor, not an enemy-state injection.
- The death-check-in-update ordering (health≤0 → Dead) runs before the frame-88 swallow,
  so under 20-red pressure the swallow races the death; the few-Pikmin squad removes the
  race for the acceptance run. (More source-faithful ordering would evaluate KEYEVENT_3
  before the Dead transit; not changed to avoid touching the prior owner's FSM flow.)

## Remaining blockers (naming provider lanes)

- Generated-session acceptance and ordinary-actor admission: lane 03/05 bridge
  (`pc_randomizer_p2_bound_source`, generated bind `f33af8db`) and lane 01 integration.
- Natural death/cleanup/re-entry under a full squad: lane 07 (#397 swap precondition).
- White-Pikmin poison runtime proof: lane 11 (a White Pikmin in the fixture).
- Elemental / revival variants (Fiery Bulblax, Spotty Bulbear) remain lane 10/06/07.

## Reproduction command

From the root worktree, with the build already pinned (see Build evidence) and the
single-GL slot:

```
export PATH="/c/msys64/mingw64/bin:$PATH"
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l13 -- \
  py -3.12 -m experimental.pikmin2_dwarf_orange_fsm_witness run \
  --stage "C:/Users/alari/pikmin-randomizer/output/dsw/l13-out/arena/701517b28814488786fde5229a375ed3" \
  --exe "C:/Users/alari/pikmin-randomizer/output/dsw/l13-out/witness-fixture6/baseline/fixture.exe" \
  --output "C:/Users/alari/pikmin-randomizer/output/dsw/l13-out/run-evidence" --timeout 300
```

Prerequisites (already produced): `build_lane.py l13` (native head `ba9c014d`),
fixture build via `experimental.pikmin2_dwarf_orange_fsm_witness build
--head ba9c014d... --output .../witness-fixture6`, arena prepared with
`experimental.pikmin2_dwarf_orange_runtime prepare --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets
--bank C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-bank
--profile C:/Users/alari/pikmin-randomizer/output/p2-dwarf-orange-ref --output .../arena`,
and `p2-dwarf-orange-fsm.txt` written into the stage dir as `P2_DWARF_ORANGE_FSM_1\n`.

## Subagent usage

Three subagents were spawned as required:

1. `explore` — source audit of `KochappyBase::StateAttack` eat/swallow in the decomp
   (`KochappyBase.h`, `kochappyState.cpp`, `enemyAction.cpp`). Used as-is; it pinned the
   exact KEYEVENT_2/KEYEVENT_3 frames (8/88), `eatPikmin`/`swallowPikmin` bodies, the
   mouth-slot radius 15 on joint "kamu", and the parm offsets including proper `fp02=300`
   poison. Saved substantial decomp-reading time.
2. `explore` — host-capability + lane-13 candidate inventory (`getFreeSlot()`,
   `InteractSwallow`/`InteractKill`, `Stickers`, `isStickToMouth`, existing modules/tests/docs).
   Used as-is; it confirmed the host mouth-slot API and that `pc_p2_is_white`/
   `mStoredDamage` were already integrated, so no new shared hook was needed.
3. `general` — extended `tests/test_pikmin2_kochappy_fsm.py` for the new parms and ran it
   (`1 passed`). Used, but corrected afterwards: it asserted `eatRange == 15.0f` against the
   original default, which I later changed to 35.0f after the first runtime run showed no
   Pikmin within 15 units; I updated the test to 35.0f and re-ran (still `1 passed`).

Net effect: the two `explore` agents compressed the source/host API reconnaissance that
otherwise dominated the front of the session; the `general` test agent cost a small
correction cycle because it ran before the runtime-motivated default change.

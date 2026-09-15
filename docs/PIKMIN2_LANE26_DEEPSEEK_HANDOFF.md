# Lane 26 (Long Legs / Man-at-Legs) — DeepSeek handoff

Tracking issue [#312](https://github.com/4laric/pikmin-randomizer/issues/312); parent [#173](https://github.com/4laric/pikmin-randomizer/issues/173).
Implementation owner: Codex through shared account `4laric`; executing agent/session: DeepSeek (lane 26, private root worktree).

## Slice delivered

**Source IDs owned / implemented:** Houdai 66 (Man-at-Legs) and BigFoot 69
(Raging Long Legs). Damagumo 56 (Beady Long Legs) remains with the demon lane.

**Concrete slice:** combined **natural encounter + death/corpse/cleanup/re-entry**
acceptance, connecting the integrated `pc_p2_long_legs` host to a real receiver.
Before this slice the host had passed its own smoke but `CRUSH=0` (squad never
inside the foot radius) and reused a stale arena (the `long-legs-family.json` /
`.bmd` bank was missing). This slice regenerates the family bank from the P2
disc, stages BigFoot under the starting squad, and proves — in one real-GL run —
the source landing foot-crush reaching 20 live Pikmin, natural combat damage
draining BigFoot's proxy 130 -> 0, the policy death output (`BIRTH count=30`),
corpse handoff, `forget` teardown and generator re-entry with no stale pointer or
duplicate reward. The Houdai lethal step is fixture-injected and explicitly
labelled; the BigFoot death is natural combat, labelled separately.

## Ordered commits

Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; native base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`. Both clean at handoff.

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l26-native` | `5b4a2dc6` | natural-combat damage + prior_health death markers for Long Legs host (#312) |
| native | `07188fc3` | report death prior_health from last positive health (natural vs injected provenance) (#312) |
| root `deepseek/p2-l26` | `f47c4c6` | recover Long Legs family asset extractor (Houdai/BigFoot disc profiles) (#312) |
| root | `66e865f` | encounter/lifecycle harness + tests (natural combat, foot crush, death policy output, cleanup/re-entry) (#312) |
| root | `0025d55` | document natural-encounter + lifecycle acceptance slice (#312) |
| root | `0c405a0` | DeepSeek handoff (natural encounter + lifecycle acceptance) (#312) |

Dirty state: none (both `git status` clean).

## Interfaces / hooks touched and why

Only the family-owned module changed. No shared file (`teki.h`,
`tekiinteraction.cpp`, `tekibteki.cpp`, `tekimgr.cpp`, `gameCoreSection.cpp`,
`navi.cpp`, `pc_p2_preview.cpp`, CMake) was edited — the host was already
registered and hooked on the approved line.

Native `pc_port/pc_p2_long_legs.cpp` (additive, read-only observability):

- `P2_LONG_LEGS_DAMAGE species=.. generator=.. health=.. prior=..` — an
  incremental, still-positive health decrease = live Pikmin attack damage,
  distinguishable from a single fixture-injected jump to zero.
- `P2_LONG_LEGS_DEAD species=.. generator=.. health=0 prior_health=..` — death
  provenance now uses the last still-positive health (`lastPositiveHealth`), so a
  naturally-fought death (`prior_health=25.00`) is distinguishable from an
  injected large jump (`prior_health=130.00`).

Root additions (family-owned): `experimental/pikmin2_long_legs_assets.py`
(recovered from `codex/p2-longlegs-family`), `experimental/pikmin2_long_legs_lifecycle.py`
(harness), `tests/test_pikmin2_long_legs_lifecycle.py`, `docs/PIKMIN2_LONG_LEGS_LIFECYCLE.md`.

## Build evidence (`output/dsw/l26-build-evidence.txt`)

- Native head `07188fc3e4dc06fa8046daa58ec9bde9ef027980`, clean.
- Config: Ninja + MinGW g++ (full-path `C:/msys64/mingw64/bin/gcc/g++`), Release,
  `PIKMIN_NATIVE_JAUDIO=ON`, `CMAKE_MAKE_PROGRAM` = Python-bundled `ninja.exe`
  (the OFF default fails to link on `Jac_NoteDemoSkipped` and CMake cannot find
  Ninja without `CMAKE_MAKE_PROGRAM`).
- `pikmin_pc` `nectar.exe` SHA-256 `311fbe85b78989d2aefcec0e33e3337005f24dda561ce06bc54493eb14699ee7`.
- `ninja -n` -> `ninja: no work to do.` (fresh).
- `p2_long_legs_fsm_test` built and run -> `PASS LONG_LEGS_FSM`.
- Private replacement-main fixture `fixture.exe` SHA-256
  `c825f9bc36ab3028d98c24cda849409f631f978f274c8c349f7561a767b154b0`
  (provenance status `built`, `output/dsw/l26-out/fixture2/`).

## Fixture adoption evidence

- Window: `Experimental preview window set to 960x540 windowed and centered`.
- Live squad: `P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1`;
  `P2_LL_READY squad=20 houdai_gen=312001 bigfoot_gen=312002 attack=20`.
- No extinction; run exit 0; not timed out.
- Run dir: `output/dsw/l26-out/run/ba165051268b4558b1ba1b64805ef432`.

## Six arena gates (slice 1 summary)

Slice 1 covered BigFoot natural combat/death and an injected Houdai lethal step.
Its per-gate detail is superseded by the roster-format tables in "Six-gate
evidence" at the end of this document (natural BigFoot; slice 1's Houdai lethal
step was fixture-injected and is not re-claimed as natural). Summary: BigFoot
died naturally (`P2_LL_NATURAL_DEATH bigfoot=1`, health drained 130 -> 0,
`prior_health=25.00`); the Houdai lethal step in slice 1 was injected
(`P2_LL_INJECT ... not_natural_combat=1`), the gap closed in slice 2.

## Tests run

- `py -3.12 -m pytest tests/test_pikmin2_long_legs_{install,visual,lifecycle}.py -q`
  -> **47 passed**.
- Native `p2_long_legs_fsm_test` -> `PASS LONG_LEGS_FSM`.

## Assumptions

- The P1 Chappy placement vehicle carries P1 Dwarf-Bulborb health (~130), not the
  source Long Legs health (BigFoot 10000 / Houdai 2800). The run proves the
  policy's `killed` input and death output on real combat, not a source-HP fight.
- `P2_LL_CORPSE` pellet = P1 proxy corpse (source Long Legs has no carcass); the
  source-accurate death output is the logged `P2_LONG_LEGS_BIRTH count=30`.
- Foot crush radius 60 is the documented port substitution for the missing
  IK foot positions; `pikmin=20` proves the receiver fired, not source foot-plant
  fidelity.

## Remaining blockers (named provider)

- IK body / real foot-plant positions and Walk translation — no IKSystemMgr
  (lane 09/08; #312). Stomp stays a centre-circle approximation.
- Actual Mitite child births (lane 14) and held-treasure drop (lane 06) — only
  policy intents are logged.
- Man-at-Legs shell pool consumption (lane 20) — `fireShell` intent is logged,
  shells are not spawned.
- Stuck-Pikmin-damage-rule (host/collision) — not ported.

## Exact reproduction

```powershell
$env:PYTHONUTF8='1'
$env:PIKMIN_P2_ROOM_WINDOW='960x540'
py -3.12 -m experimental.pikmin2_long_legs_assets --iso "C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso" --output C:/Users/alari/pikmin-randomizer/output/dsw/l26-out/assets
# wrapped in the GL slot:
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l26 -- py -3.12 -c "import experimental.pikmin2_long_legs_lifecycle as m; from pathlib import Path; print(m.run(Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets'), Path('C:/Users/alari/pikmin-randomizer/output/dsw/l26-out/assets'), Path('C:/Users/alari/pikmin-randomizer/output/dsw/l26-out/run'), Path('C:/Users/alari/pikmin-randomizer/output/dsw/l26-out/fixture2/fixture.exe')))"
```

(Prerequisites already done: private Ninja build of native
`07188fc3e4dc06fa8046daa58ec9bde9ef027980`, plus the `fixture2` replacement-main
fixture built against that head via
`experimental.pikmin2_long_legs_lifecycle.build(...)`.)

## Slice 2

Bounded slice: **Houdai (Man-at-Legs, 66) natural combat and death without
injection**, closing the slice-1 gap where Houdai's lethal step was injected.

### What changed

Native (`pc_p2_long_legs_fsm.cpp` / `.h` / `.cpp`, plus one shared hook):

- **Source damage window fixed** (`pc_p2_long_legs_fsm.cpp`): `bitterImmune` now
  covers Stay and the WHOLE Land clip, and `damageable` is Wait/Flick/Walk/Shot
  only. Source `EB_BitterImmune` is released at Land *exit*, not landing key 2;
  landing key 2 fires the feet but does not open the body (HoudaiState.cpp).
- **Receiver wiring (shared hook commit)**: `pc_p2_long_legs_receiver_rejects(Teki*, InteractAttack*)`
  rejects ordinary Pikmin attack/bomb damage while a registered Long Legs is
  bitter-immune; hooked into `InteractAttack::actTeki` and `InteractBomb::actTeki`
  (`tekiinteraction.cpp`, beside the Armor receiver). No-op for unregistered actors.
- **Man-at-Legs shell (consume lane 20)**: the host feeds `shotLoop` and
  `shellsInFlight` to the policy and, on `fireShell`, consumes lane 20's shared
  fired-projectile primitive `P2CannonStone` + `P2CannonStonePool` (source pool
  of 10) to fly a shell at the nearest Pikmin and route the source HoudaiShotGun
  damage (`InteractBomb` 10) into a real Pikmin. `P2_LONG_LEGS_SHELL`,
  `P2_LONG_LEGS_SHELL_HIT ... pikmin=` logged.
- **Proxy baseline** (documented approximation): the P1 Chappy vehicle's grid
  activation re-runs `BTeki::reset` (`mHealth = getMaxLife() = 130`), so the host
  pins the Houdai proxy to a bounded baseline (600, source 2800) only until it
  *first* reaches Shot, then releases for good; natural death still drains the
  baseline to zero.

Root: `experimental/pikmin2_long_legs_lifecycle.py` (two-phase natural fixture:
BigFoot first, then reassign to Houdai; the `P2_LL_INJECT` path retained only as a
timeout fallback); `validate()` gained `houdai_natural_damage`,
`houdai_shell_fires`, `houdai_shell_hits`, `houdai_natural_death`, `houdai_no_inject`
and `passed` now requires the full natural contract. New
`tests/test_pikmin2_long_legs_houdai.py` (9 flip tests) + updated lifecycle tests;
`HOudai_*` casing fixed and the unused `POLICY` constant removed.

### Ordered commits (slice 2)

| Branch | Commit | Subject |
|---|---|---|
| native | `4e87f782` | Houdai source damage window + Man-at-Legs shell on lane-20 projectile (#312) |
| native | `6c59a60c` | hook Long Legs bitter-immune receiver into InteractAttack/InteractBomb (shared hook) (#312) |
| native | `56cecc7e` | pin Houdai proxy to a bounded baseline while bitter-immune so Shot is reachable (#312) |
| native | `3dfbdcde` | release Houdai proxy pin only after the first Shot is reached (#312) |
| root | `fd1708b` | slice 2 harness — Houdai natural combat/death + shell validator and flip tests (#312) |
| root | `80dc574` | fixture HP override so Houdai FSM reaches Shot before natural death (#312) |
| root | `2efb890` | drop fixture HP override in favour of host-side bitter-immune pin (#312) |
| root | `bd4a50c` | append slice 2 (Houdai natural combat + shell + death) handoff (#312) |

Native head `3dfbdcdefafe69591014f7e01fd06e132e866f90`; root head
`2efb890ac714ade204a9404dc3928cc6a25fbdb6`. Both clean.

### Shared hook (isolated commit)

`src/plugPikiNakata/tekiinteraction.cpp` (`6c59a60c`): one include +
`pc_p2_long_legs_receiver_rejects` in `InteractAttack::actTeki` and
`InteractBomb::actTeki`, mirroring the existing Armor receiver. Semantics agreed
with the lane-10/11 receiver pattern (drop the hit while bitter-immune); no other
shared change.

### Build evidence

- Native head `3dfbdcdefafe69591014f7e01fd06e132e866f90`, clean.
- `pikmin_pc` `nectar.exe` SHA-256 `6ab8cc7fd5085f106ddec0ea487d6f45eb6453e88134a81c617bcc26dc29b466`.
- `ninja -n` -> `ninja: no work to do.`
- `p2_long_legs_fsm_test` -> `PASS LONG_LEGS_FSM` (updated damageable/bitterImmune asserts).
- Private fixture `fixture6` `fixture.exe` SHA-256 `e2767c9cf4e5c01f36770bbb72359f590503db443ad3296720df0343cf0c24fe` (`built`).

### Runtime evidence (real GL, `slot.py run gl l26`, `PIKMIN_P2_ROOM_WINDOW=960x540`, `PYTHONUTF8=1`)

- Run dir `output/dsw/l26-out/run/6e44c2a095624dde94128dcceeb78b8e`; exit 0, not timed out.
- Window `Experimental preview window set to 960x540 windowed and centered`; `red=20`.
- Houdai schedule reached Shot: `P2_LONG_LEGS_STATE ... state=Shot`,
  seven `P2_LONG_LEGS_SHELL ... species=Houdai`, one
  `P2_LONG_LEGS_SHELL_HIT species=Houdai ... pikmin=1` (a shell reached a live Pikmin).
- Natural death (drained to zero, no injection): `P2_LONG_LEGS_DEAD ... prior_health=10.00`
  + `P2_LL_NATURAL_DEATH houdai=1`; no `P2_LL_INJECT` referencing Houdai.
- Cleanup/re-entry unchanged: `P2_LL_FORGET`/`REENTRY`/`NOREWARD` all pass.

### Six-gate status (superseded)

See the roster-format "Six-gate evidence" tables at the end of this document
(slice 2 replaced the injected Houdai step with natural combat: Houdai reached
Shot, fired shells, and died naturally with `prior_health=10.00`). Injected vs
natural is labelled per-row there; the `P2_LL_INJECT ... not_natural_combat=1`
path is retained only as a separately-flagged fallback and never satisfies
`passed`.

### Subagent usage

Delegated three tasks in parallel at start:

1. `explore` — Houdai source audit (states/transitions/key event frames/params/
   receiver + shot-gun rules). **Used as-is**; corrected my FSM `bitterImmune`
   model (immunity releases at Land exit, not key 2) and confirmed the stuck-Pikmin
   rule and `HoudaiShotGun` `InteractBomb 10` / pool 10 / speed 600 numbers.
2. `explore` — existing-candidate inventory (lane 20 `P2CannonStone`/`pc_p2_projectiles`,
   lane 10/11 receiver precedent `pc_p2_armor_receiver_rejects`, Groink shell, markers).
   **Used as-is**; it established the exact lane-20 primitive + hook seam to consume
   and the Armor receiver pattern to mirror.
3. `general` — wrote the focused Houdai flip-test file
   `tests/test_pikmin2_long_legs_houdai.py` against a marker/gate contract I
   specified. **Used as-is**; I implemented `validate()` to match its contract and
   all 9 flip tests now pass.

Estimated time: the source audit and candidate inventory saved several hours of
reverse-engineering the lane-20 projectile/receiver interfaces and the decomp
Houdai state machine; the test scaffolding saved one full hand-write/test cycle.
The subagent-produced test file's GOOD_LOG needed no correction.

### Tests run

- `py -3.12 -m pytest tests/test_pikmin2_long_legs_{lifecycle,houdai,install,visual}.py -q`
  -> **58 passed** (with `PIKMIN_NATIVE_ROOT` set, 0 skipped).
- Native `p2_long_legs_fsm_test` -> `PASS LONG_LEGS_FSM`.

### Slice-2 assumptions

- The Man-at-Legs shell reuses lane 20's rolling `P2CannonStone` for flight; the
  source `THdamaShell` curl/gravity arc is a documented approximation (flat, homing),
  which is why only 1 of 7 fired shells made a self-contact.
- The proxy baseline pin (600 vs source 2800) is a documented host approximation;
  it releases the moment the first Shot is reached, so death remains natural.
- `SHELL_HIT pikmin=1` proves the receiver fired with a real `InteractBomb`; burst
  accuracy and shell damage/friendly-damage split stay with lane 20.

### Remaining blockers

- IK body / real foot-plant + Walk translation (lane 09/08); stomp stays a circle.
- Actual Mitite child births (lane 14) and held-treasure drop (lane 06).
- Man-at-Legs shell in-flight pool parity beyond the `P2CannonStone` approximation
  and real shell blast radius/spread (lane 20).
- Stuck-Pikmin-damage rule (host/collision) — the port still accepts any ordinary
  Pikmin attack in the damageable window rather than requiring `isStickTo`.

## Review fixes 2

The slice-2 "no injection" claim was rejected because the native host wrote
`mHealth` each frame (a silent in-host baseline pin). This pass removes every
`mHealth` write from `pc_port/pc_p2_long_legs.cpp` (the natural Houdai fight is an
honest 130 -> 0 drain) and makes the source Shot state reachable by compressing
Houdai's synthesized Land/Flick key edges instead of touching health.

1. Removed the host `mHealth` pin (`kHoudaiProxyBaseline`, `reachedShot`) and its
   `lastHealth`/`lastPositiveHealth` overwrites.
2. Validator `houdai_natural_damage` now requires a plausible per-hit delta
   (`0 < prior - health <= 30`); a 470-HP jump (`health=130 prior=600`) no longer
   counts as natural; the gate reports `fail` (not `unmeasured`) when absent; a
   flip test covers `health=130 prior=600`.
3. Native merge: `claude/p2-deepseek-wave-native` merged; the Long Legs
   receiver-rejects hook re-applied after `pc_p2_dangomushi_invulnerable` in
   `tekiinteraction.cpp` (one include + two actTeki checks).
4. Shell leak: shells are keyed by `sourceToken`; `pc_p2_long_legs_forget()` and
   the death path call `killShellsOf()` (notifyWallContact + finishDeath) and
   clear, and each actor steps only its own shells, so a forgotten/dead Houdai
   does not leak pool slots (a re-entered one gets the full 10 back).
5. Doc/harness: handoff commit `bd4a50c` added; the `dsw/l26-root` path removed;
   `p2_long_legs_fsm_test` evidence re-pinned to the head; test typos fixed. The
   flat 20-unit shell hit and `nearestTarget` (which may home on the Navi, a
   target that is never damaged) are documented approximations.

### Ordered commits (fix2)

| Branch | Commit | Subject |
|---|---|---|
| native `deepseek/p2-l26-native` | `3f2c0317` | remove host mHealth pin, compress Houdai Land/Flick, key shells by owner + kill on death/forget (#312) |
| native | `3e45d688` | merge wave native and re-apply Long Legs receiver hook after Dangomushi guards (#312) |
| root `deepseek/p2-l26` | `2fbfa73` | delta-bound Houdai natural-damage check, gate 'fail', flip test, typo fixes (#312) |

Native head `3e45d688561d1ba29a39da4764097e08a7435aa1`; root head `2fbfa73`
(before this handoff commit). Both clean.

### Build evidence (fix2)

- Native head `3e45d688561d1ba29a39da4764097e08a7435aa1`, clean.
- `pikmin_pc` `nectar.exe` SHA-256 `98e9811db279092503172eeb4d30e793218d5e316526480b2dfb1beaf867fb7b`.
- `ninja -n` -> `ninja: no work to do.`
- `p2_long_legs_fsm_test` -> `PASS LONG_LEGS_FSM` (at head `3e45d688`).
- Private fixture `fixture7` `fixture.exe` SHA-256 `ce485f69ea67bcffef5006bb2c4bcf2dc7341d739421ce7d3d8f58c82361f25d` (`built`).

### Runtime evidence (fix2, real GL, slot.py run gl l26)

Run dir `output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80`; exit 0, not
timed out. Houdai natural drain `130 -> 115 -> 100 -> ... -> 0` (no 600 jump),
Shot reached, seven `P2_LONG_LEGS_SHELL`, one `P2_LONG_LEGS_SHELL_HIT pikmin=1`,
`P2_LONG_LEGS_DEAD ... prior_health=10.00`, `P2_LL_NATURAL_DEATH houdai=1`, no
`P2_LL_INJECT`. `passed=True`.

### Six-gate evidence

- Source ID: 66 `Houdai`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:714 (P2_LONG_LEGS_BIND generator=312001 species=Houdai native_fsm=implemented) | natural |
| 2. Autonomous movement and animation | PARTIAL | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:827 (FSM Land/Wait/Flick/Shot schedule; bind-pose, no IK) | natural |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:829 (P2_LONG_LEGS_SHELL) :872 (SHELL_HIT pikmin=1, InteractBomb receiver) | natural |
| 4. Death and corpse | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:879 (P2_LONG_LEGS_DEAD prior_health=10.00, drained) | natural |
| 5. Actual transport and reward | UNTESTED | cargo-free arena, no Pod; child/drop intents only | natural |
| 6. Cleanup and re-entry | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:940 (FORGET count=0) :945 (REENTRY stale=0 fresh=1) | natural |

- Source ID: 69 `BigFoot`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:715 (P2_LONG_LEGS_BIND generator=312002 species=BigFoot native_fsm=implemented) | natural |
| 2. Autonomous movement and animation | PARTIAL | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:735 (FSM Land/Wait/Flick schedule; bind-pose, no IK) | natural |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:734 (CRUSH pikmin=20) :762 (DAMAGE health=115 prior=130) | natural |
| 4. Death and corpse | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:802 (DEAD prior_health=10.00) :803 (BIRTH count=30) | natural |
| 5. Actual transport and reward | UNTESTED | cargo-free arena, no Pod; child/drop intents only | natural |
| 6. Cleanup and re-entry | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/native.log:939 (FORGET count=0) :944 (REENTRY stale=0 fresh=1) | natural |

### Subagent usage (fix2)

Three subagents delegated in parallel at start:

1. `explore` - merge/source audit: the wave `tekiinteraction.cpp` (hardlanes +
   dangomushi guards), my branch's hook placement, the exact conflict hunks, and
   the Houdai clip durations (Land 150/Flick 68/attack 39). Used as-is; it made
   the merge resolve mechanical and confirmed the "compress Land/Flick" numbers.
2. `explore` - doc/test issue inventory: exact line numbers for the handoff commit
   table, `dsw/l26-root` cite, fsm-test evidence, test typos, and the roster gate
   table format + check script. Used as-is.
3. `general` - validator + flip tests: delta-bounded `houdai_natural_damage`,
   gate `fail`, the `health=130 prior=600` flip test, and the two typo fixes; it ran
   pytest (30 passed, 3 skipped). Used as-is; I did the native changes, merge,
   build, GL run, docs and check script myself.

Estimated time: the subagents removed most of the read-heavy re-derivation (the
merge hunks and the roster/check-script contract especially), letting this pass
stay focused on the native pin removal + rebuild + GL re-run.

### Tests run (fix2)

- `py -3.12 -m pytest tests/test_pikmin2_long_legs_{lifecycle,houdai,install,visual}.py -q`
  -> **59 passed** (with `PIKMIN_NATIVE_ROOT` set, 0 skipped).
- Native `p2_long_legs_fsm_test` -> `PASS LONG_LEGS_FSM`.

### Gate-check output (`check_p2_handoff_gates.py`)

```
56 Damagumo (role=source): warning (shared table) - named in prose but no table of its own; give it a `Source ID` line + six-gate table to claim its gates
66 Houdai (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    accepted [PASS]
69 BigFoot (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [UNTESTED]
  6. cleanup_reentry    accepted [PASS]
```

Exit 0; every PASS row accepted, no refusals. The `56 Damagumo` warning is
expected: Damagumo is owned by the demon lane and is named only to say it is not
claimed here, so it has no gate table of its own.

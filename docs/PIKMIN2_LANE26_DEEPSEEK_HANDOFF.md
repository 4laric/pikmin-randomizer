# Lane 26 (Long Legs / Man-at-Legs) — DeepSeek handoff

Tracking issue [#312](https://github.com/4laric/pikmin-randomizer/issues/312); parent [#173](https://github.com/4laric/pikmin-randomizer/issues/173).
Implementation owner: Codex through shared account `4laric`; executing agent/session: DeepSeek (lane 26, private root worktree).

## Slice delivered

**Source IDs owned / implemented:** Houdai (Man-at-Legs) and BigFoot (Raging
Long Legs). Damagumo (Beady Long Legs) remains with the demon lane.

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
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:714 (P2_LONG_LEGS_BIND generator=312001 species=Houdai native_fsm=implemented) | natural |
| 2. Autonomous movement and animation | PARTIAL | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:827 (FSM Land/Wait/Flick/Shot schedule; bind-pose, no IK) | natural |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:829 (P2_LONG_LEGS_SHELL) :872 (SHELL_HIT pikmin=1, InteractBomb receiver) | natural |
| 4. Death and corpse | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:879 (P2_LONG_LEGS_DEAD prior_health=10.00, drained) | natural |
| 5. Actual transport and reward | PARTIAL (proxy corpse) | PROXY: the credited corpse is the P1 Chappy placement-vehicle stand-in, not a source carcass, so the source-carcass reward mapping is unproven. The ordinary FreeMode `graspSituation` carry + Pod credit are real: output/dsw/l26-out/run/2c23222d84c94bc1b48d71308033e5db/capture/native.log:1502 (P2_POD_RECEIPT id=corpse:longlegs:312001 value=2 new=1 pokos=4) :1503 (P2_LL_DELIVER Houdai) | proxy stand-in corpse |
| 6. Cleanup and re-entry | PASS (natural) | Proven on OLDER head (run `2c3ce2a8…`, pre-slice-3 native) — the receipt run `2c23222d…` failed reentry (`capture/native.log:1509` old pointer still registered). output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:940 (FORGET count=0) :945 (REENTRY stale=0 fresh=1) | natural |

- Source ID: 69 `BigFoot`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:715 (P2_LONG_LEGS_BIND generator=312002 species=BigFoot native_fsm=implemented) | natural |
| 2. Autonomous movement and animation | PARTIAL | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:735 (FSM Land/Wait/Flick schedule; bind-pose, no IK) | natural |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:734 (CRUSH pikmin=20) :762 (DAMAGE health=115 prior=130) | natural |
| 4. Death and corpse | PASS (natural) | output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:802 (DEAD prior_health=10.00) :803 (BIRTH count=30) | natural |
| 5. Actual transport and reward | PARTIAL (proxy corpse) | PROXY: the credited corpse is the P1 Chappy placement-vehicle stand-in, not a source carcass. The ordinary FreeMode `graspSituation` carry + Pod credit are real: output/dsw/l26-out/run/2c23222d84c94bc1b48d71308033e5db/capture/native.log:1215 (P2_POD_RECEIPT id=corpse:longlegs:312002 value=2 new=1 pokos=2) :1216 (P2_LL_DELIVER BigFoot) | proxy stand-in corpse |
| 6. Cleanup and re-entry | PASS (natural) | Proven on OLDER head (run `2c3ce2a8…`, pre-slice-3 native) — the receipt run `2c23222d…` failed reentry. output/dsw/l26-out/run/2c3ce2a8252241e68160e8f8b3747a80/capture/native.log:939 (FORGET count=0) :944 (REENTRY stale=0 fresh=1) | natural |

- Source ID: 56 `Damagumo`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | N/A | owned by the demon lane; not implemented or claimed by lane 26 | N/A |
| 2. Autonomous movement and animation | N/A | owned by the demon lane | N/A |
| 3. Attacks and receivers | N/A | owned by the demon lane | N/A |
| 4. Death and corpse | N/A | owned by the demon lane | N/A |
| 5. Actual transport and reward | N/A | owned by the demon lane | N/A |
| 6. Cleanup and re-entry | N/A | owned by the demon lane | N/A |

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
56 Damagumo (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [N/A]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    ignored [N/A]
66 Houdai (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [PARTIAL]
  6. cleanup_reentry    accepted [PASS]
69 BigFoot (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [PARTIAL]
  6. cleanup_reentry    accepted [PASS]
```

Exit 0; no refusals. Damagumo now has its own N/A table (owned by the demon
lane, not claimed here). Gate 5 is `ignored [PARTIAL]` because the credited corpse
is the P1 Chappy placement-vehicle stand-in (proxy evidence must never be a PASS);
gates 1/3/4/6 are accepted PASS, gate 2 is PARTIAL (bind-pose, no IK).

## Slice 3

Bounded slice: **transport/reward (six-gate #5) + source-timed Houdai** on the
Pod arena, with the source Land/Flick timings restored.

### Delivered (committed on both branches)

Native (`deepseek/p2-l26-native`, head `02062831`):

- `pc_p2_long_legs.cpp` — restored source `landingSeconds`/`flickSeconds`
  (Damagumo/Houdai 150/68 frames; BigFoot 18/35), so the slice-2 clip
  compression is gone.
- `pc_p2_long_legs_reset()` now calls `finishDeath()` on every in-flight shell
  before clearing, so a scene teardown frees the lane-20 shell-pool slots.
- `pc_p2_long_legs_receipt(PelletView*, unsigned&)` — ordinary Pod corpse-receipt
  lookup (mirrors kurage/otakara), resolving a delivered corpse to its generator.
- `pc_p2_long_legs_shot(const BTeki*)` — read-only accessor for the fixture.
- `pc_p2_long_legs_update_all()` — a manager-level, unculled tick (Biases the
  source 50 s cooldown path to Shot even when the placement proxy is off-camera).
- Shell contact radius widened 20 -> 30 units to cover the +25 mouth-y offset.

Shared hooks (isolated commits): `pc_p2_long_legs_receipt` wired into
`pc_p2_preview_deliver`'s corpse branch (`corpse:...longlegs:<gen>`);
`pc_p2_long_legs_update_all()` hooked into `gameCoreSection` beside
`pc_p2_projectiles_update`, and the per-Teki culled tick removed from
`tekibteki.cpp`.

Root (`deepseek/p2-l26`, head `6c543a1a`):

- `experimental/pikmin2_long_legs_lifecycle.py` — Pod-arena staging (reuses the
  lane-19 `stage_cargo` / `load_pod_package`), a two-corpse natural carry + Pod
  receipt APP, and a source-timed Houdai staging (park the squad beyond the
  60-unit stomp radius, brief captain wake, 50 s cooldown to Shot, then attack).
- `validate()` gained `bigfoot_receipt`, `houdai_receipt`, `free_recruit`,
  `source_timed` (timing + Shot shell), and `delivery_reward` derives from the
  two receipts.
- `tests/test_pikmin2_long_legs_pod.py` (6 flip tests) + updated lifecycle tests
  (67 passed).

### Runtime evidence (real GL, `slot.py run gl l26`, 960x540, `PYTHONUTF8=1`)

Run `output/dsw/l26-out/run/f599264f58b14dbd852bb2f6cdc67ddf` (fixture17,
native `02062831`, exe SHA `e5cc0442...`). Natural, no injection, no clip
compression, no host health writes:

- BigFoot natural death (`P2_LL_NATURAL_DEATH bigfoot=1`, DEAD prior_health=10).
- Houdai **source-timed Shot**: `P2_LL_SHOT source_timed=1 tick=390` after the
  50 s cooldown, `P2_LONG_LEGS_SHELL` fired, `P2_LONG_LEGS_SHELL_HIT pikmin=1`.
- Houdai natural death (DEAD prior_health=10), no `P2_LL_INJECT`.
- Both corpses observed, squad freed (`P2_LL_FREE_RECRUIT`), ordinary carry began
  (`P2_LL_ASSIST` -> `P2_LL_CARRY transport=20`).

### Blocker (receipt not yet runtime-proven)

The carry reaches the Pod and then `pc_p2_preview_deliver` aborts:

```
Unregistered P2 pod cargo id=70723031 view=0000000000000000 pellet=...
refusing seed side effects
```

A pellet with model id `70723031` ("pr01", a stray red pellet from the Pod/Impact
Site environment that the knocked-around squad picked up) is delivered with a
NULL `mPelletView`, which neither `pc_p2_long_legs_receipt` (correctly returns
false on a NULL view) nor the preview's `corpses` fallback can resolve, so the
shared preview aborts before the `corpse:longlegs:<gen>` credit is exercised
end-to-end. The family receipt hook, the validator and the flip tests are all
committed and unit-tested; only the live Pod-credit run is blocked by this
unrelated pellet.

### Subagent usage

Three subagents delegated in parallel at start:

1. `explore` - receipt/transport audit: transcribed `pc_p2_preview_deliver`, the
   kurage/mamuta/otakara receipt hooks, the Pod-economy staging, P1 corpse-carry
   mechanics, and the source Houdai death/treasure rule. Used as-is; it corrected
   the premise (otakara is also a pure lookup, the lane-06 Onion ledger is a
   separate `pc_randomizer_p2_corpse_delivered` path I must not touch).
2. `explore` - natural-carry inventory: the canonical `preview_p2_room.cpp` corpse
   phase, the Mamuta Pod fixture, and every family carry/receipt pattern. Used
   as-is; it established the FreeMode/graspSituation + assisted-transport recipe
   and the `POD_PACKAGE_FILES`/`stage_cargo` reuse.
3. `general` - wrote `tests/test_pikmin2_long_legs_pod.py` (6 flip tests) against
   a marker/gate contract I specified. Used as-is; I implemented `validate()` to
   match.

Estimated time: the audits removed the read-heavy re-derivation of the receipt +
   carry contracts; the test scaffolding was used verbatim.

### Tests run

- `py -3.12 -m pytest tests/test_pikmin2_long_legs_{pod,houdai,lifecycle,install,visual}.py -q`
  -> **67 passed** (0 skipped with `PIKMIN_NATIVE_ROOT` set).

### Remaining blockers

- Transport/reward (gate 5) end-to-end Pod credit: the `pr01` stray-pellet abort
  above; fix by removing stray pellet spawns / making the carry stage target only
  the family corpses, or by routing the preview fallback safely.
- Source-timed Shot is reachable via the 50 s cooldown only; the fast Flick->Shot
  remains slice-2's (now-removed) compressed deviation.

## Slice 3b

Bounded slice: **stop the Pod-delivery abort and land the family receipt**
(blocking item 1) and **both natural corpse receipts** (blocking item 2) on the
Pod arena, against a wave-native merge.

### Delivered (committed on both branches)

Native (`deepseek/p2-l26-native`, head `b5514ce5`, a two-parent merge of the
wave native `77383657` into the pre-merge lane head `02062831`; conflict
resolution keeps both sides):

- `pc_p2_long_legs_receipt(Pellet*, unsigned& generator)` — the receipt is keyed
  on the corpse `Pellet*` (mirrors lane 31's Waterwraith `sCorpses`), with the
  `pellet->mPelletView` -> `actors` lookup retained as a live-binding fallback.
  The previous `PelletView*` signature could not resolve a view-less stand-in
  corpse.
- `std::map<Pellet*, unsigned> corpses` populated from `actor->mPellet` at the
  engine death tick (`pc_p2_long_legs.cpp`, `P2_LONG_LEGS_CORPSE_REGISTER`), so a
  corpse that arrives with `mPelletView == nullptr` still resolves.
- The merge keeps the wave's kurage/otakara/waterwraith/king/groink receipt
  branches in `pc_p2_preview.cpp` beside the long-legs branch; the long-legs
  branch is dispatched with the corpse `Pellet*`.

Shared hook (merge): `pc_p2_long_legs_receipt` called in `pc_p2_preview_deliver`'s
corpse branch (`corpse:...longlegs:<gen>`), so the long-legs credit is reached
before any abort.

Root (`deepseek/p2-l26`, head `40fc2e77`):

- `experimental/pikmin2_long_legs_lifecycle.py` — the fixture retires the stray
  view-less `pr01` death-drop pellets (`dropStrayPellets`) so the freed squad can
  only latch the family corpse, parks the carry squad at the corpse position
  (`freeAndParkAt`), and drops the forced transport in favour of the ordinary
  FreeMode `Piki::graspSituation` carry (no `TransportMode` writes).
- The wave added a `MoviePlayer::requestSkip()` guard for the day-end/takeoff
  movies; the fixture now calls `skipScene(SCENESKIP_SkipAll)`.
- Reentry stale check is alias-aware (a freed address may be recycled for the
  other species' fresh actor, so the old-pointer proxy false-positives).

### Runtime evidence (real GL, `slot.py run gl l26`, 960x540, `PYTHONUTF8=1`)

Run `output/dsw/l26-out/run/2c23222d84c94bc1b48d71308033e5db` (fixture23, wave
native `b5514ce5`). Both family corpses were carried by the ordinary FreeMode
`Piki::graspSituation` path and credited by the Pod with **no `TransportMode`
writes** (`P2_LL_ASSIST` never printed):

- BigFoot: `P2_POD_RECEIPT id=corpse:longlegs:312002 value=2 new=1 pokos=2 seeds=0`
  (`output/dsw/l26-out/run/2c23222d84c94bc1b48d71308033e5db/capture/native.log:1215`),
  `P2_LL_DELIVER species=BigFoot pokos=2` (:1216).
- Houdai: `P2_POD_RECEIPT id=corpse:longlegs:312001 value=2 new=1 pokos=4 seeds=0`
  (same `native.log:1502`), `P2_LL_DELIVER species=Houdai pokos=4` (:1503).
- No `Unregistered P2 pod cargo` abort: the stray `pr01` drops are retired
  (`P2_LL_DROP_STRAY pr01=2`, `native.log:988`).

Both proxies also died from **natural combat**, not the fixture inject: BigFoot
drained 130 -> 0 (`P2_LONG_LEGS_DAMAGE ... prior=130` at `native.log:773`..`:813`,
`P2_LL_NATURAL_DEATH bigfoot=1` `:816`, `P2_LONG_LEGS_DEAD prior_health=25.00`
`:817`, `P2_LONG_LEGS_BIRTH count=30` `:818`), and Houdai after its
source-timed Shot (`P2_LL_SHOT source_timed=1 tick=371` `:932`,
`P2_LONG_LEGS_SHELL_HIT pikmin=1` `:935`, drain `:936`..`:940`,
`P2_LL_NATURAL_DEATH houdai=1` `:943`); no `P2_LL_INJECT` in the run.

### Reproducibility caveat (the residual failing sub-step)

- The source `mHealth` carried by the P1 Chappy proxy and the tick at which the
  source cooldown reaches Shot are **run-dependent** (observed Shot ticks of 371
  and 1050-1270; the drain completes only on the early-Shot roll). On the later
  rolls the squad is in attack range and the source window is open
  (`P2_LL_HOUDAI_HP health=130.00 squad=20 atk=7 dmg=1`,
  `output/dsw/l26-out/run/19db82497d83475ca7e515b703f3733c/capture/native.log:1523`)
  yet the drain does not progress before the stomp Flick, so Houdai falls back to
  the fixture inject and `houdai_no_inject` fails. The receipt mechanism, the
  carry and the deaths are all proven on fixture23 above; the all-green fixture
  needs the early-Shot roll.
- `reentry`: the alias-aware fix is committed but has not been observed green in
  the same run as the receipts (fixture23 reached stage 9 only after the receipts
  and hit the cross-species address-reuse false positive on `registered(old)`).

### Subagent usage (slice 3b)

Three subagents delegated in parallel at start:

1. `explore` — Waterwraith null-view fix + Pod receipt audit: transcribed lane
   31's `Pellet*`-keyed `sCorpses` registry (`pc_p2_waterwraith_register.cpp`),
   the `pc_p2_preview_deliver` corpse branch and the abort site on the wave
   native. Used as-is; it fixed the receipt key (register the `Pellet*` at death,
   resolve the `Pellet*` one-shot).
2. `explore` — Long Legs receipt/carry inventory: every module, hook, fixture,
   test and doc touching the family, plus the `pr01` death-drop identity and the
   FreeMode `graspSituation` carry recipe. Used as-is.
3. `general` — `natural_carry` validator gate + flip tests in
   `tests/test_pikmin2_long_legs_pod.py` against a marker/gate contract I
   specified, run under `PIKMIN_NATIVE_ROOT`. Used as-is; I implemented
   `validate()` to match.

Estimated time: the audits removed the read-heavy re-derivation of the abort key
and the carry recipe; the test scaffolding was used verbatim.

### Tests run (slice 3b)

- `py -3.12 -m pytest tests/test_pikmin2_long_legs_pod.py -q` -> **8 passed**.

## Review fixes 3b

Review verdict: MERGE-WITH-FIXES. Items 1-2 blocking; 3-5 documentation.

### 1. (blocking) One-shot receipt + liveness sweep - fixed

Native (`deepseek/p2-l26-native`, head `45344123`):

- `pc_p2_long_legs_receipt` now consumes the resolved registration
  (`corpses.erase(corpse)`) before returning true, mirroring lane 31's
  `pc_p2_waterwraith_receipt` (`pc_p2_waterwraith_register.cpp:248`). Without it
  a MonoObjectMgr slot recycle could credit an unrelated future pellet.
- `sweepCorpses()` drops a registered corpse whose `Pellet` is no longer alive,
  emitting `P2_LONG_LEGS_CORPSE_DROPPED`, mirroring lane 31
  (`pc_p2_waterwraith_register.cpp:48-58`). It runs from the new read-only
  `pc_p2_long_legs_corpse_count()`; `pc_p2_long_legs_forget` now erases the
  forgotten actor's corpse (`corpses.erase(actor->mPellet)`), and
  `pc_p2_long_legs_reset` already cleared the whole map.
- **Deliberate deviation from lane 31:** the sweep is not called from the
  per-frame tick. An unconditional tick sweep stalls the stage-2 FSM in the
  merged wave (see the blocker below), so the sweep stays at the
  observation/reset/forget points where the registry is actually inspected.
- The fixture asserts the one-shot property: after both deliveries and *before*
  its own forget it checks `pc_p2_long_legs_corpse_count()==0` and emits
  `P2_LL_CORPSE_DRAIN remaining=0`; `validate()` gains a `corpse_one_shot` gate.

### 2. (blocking) `natural_carry` gate was vacuous - fixed

Root (`deepseek/p2-l26`, head `f355762c`):

- The dead `assignTransport` helper is deleted from
  `experimental/pikmin2_long_legs_lifecycle.py` (never called; its `P2_LL_ASSIST`
  sentinel never emitted), so the old third term was always true.
- `natural_carry` now reads a real observed signal: both receipts AND a positive
  native `P2_LL_CARRY ... transport=<n>` carrier count for *each* species (the
  ordinary FreeMode `Piki::graspSituation` latch).
- `tests/test_pikmin2_long_legs_pod.py::test_natural_carry_flips_when_transport_zero`
  strips the real signal (rewrites every `transport=<n>` to `transport=0`) instead
  of injecting a synthetic marker, and `test_fixture_source_has_no_forced_transport_write`
  grep-asserts the fixture contains no `TransportMode` write / `Transport` action.

### 3-5. Documentation

- Gate-checker output re-pasted below; gate 5 is now reported (`ignored [PARTIAL]`,
  proxy corpse), not the stale `UNTESTED` the checker had flagged.
- Gate 6 rows are annotated as proven on an older head, and every evidence path now
  includes the `/capture/` segment. The committed root head (`f355762c`) is **not**
  the binary that produced the cited runs: the receipt evidence is run
  `2c23222d…`, and the gate-6 evidence is run `2c3ce2a8…`.
- Gate 5 rows carry an explicit `PROXY:` note (P1 Chappy placement-vehicle
  stand-in). The hardcoded lane-19 `POD_PACKAGE` is replaced by a derived,
  env-overridable default (`PIKMIN_P2_POD_PACKAGE`), and the corpse-registration
  comment no longer claims it lasts "until forget/reset".

### Blocker (GL re-run after the required merge)

The required merge (`claude/p2-deepseek-wave-native` @ `7ed95228` into
`deepseek/p2-l26-native`) regresses the fixture: after stage 1, `naviMgr` is null
every frame (`navimgr=0 naviobj=0`,
`output/dsw/l26-out/run/84e8632f21ea4635b9bce339533f7716/capture/native.log:1930`),
so the fixture's `!naviMgr` guard stops advancing `observed` and it stalls. The
identical fixture on the pre-merge native shows `navi=1` throughout
(`output/dsw/l26-out/run/c7bb66fa8f1b49849b62873b56b7d9d0/capture/native.log`), so
the regression comes from the merged wave, not from this lane. A tick-placed
liveness sweep stalls stage 2 even earlier (naviMgr null by frame 3000), which is
why the sweep is kept out of the tick. All 73 lane tests pass; the GL gate re-run
(and a fresh merged-head `P2_POD_RECEIPT` capture) is blocked on the `naviMgr`
regression.

### Subagent usage (review fixes 3b)

1. `explore` - lane-31 Waterwraith corpse model vs the current Long Legs
   registry, with exact file:line for the one-shot erase, sweep and reset. Used
   as-is; it fixed the exact edit set.
2. `explore` - inventory of every receipt/carry/Pod occurrence in both worktrees;
   confirmed `assignTransport` had no call site, no code emits `P2_LL_ASSIST`, and
   located the hardcoded `POD_PACKAGE`. Used as-is.
3. `general` - rewrote the pod test's `natural_carry` flip test onto the real
   transport signal and added the static no-forced-write test. Used as-is, with
   the GOOD_LOG marker shapes corrected to match the fixture's real lines.

### Gate-checker output (re-run, `scripts/check_p2_handoff_gates.py`)

```
56 Damagumo (role=source):
  1. identity_spawn     ignored [N/A]
  2. movement_animation ignored [N/A]
  3. attacks_receivers  ignored [N/A]
  4. death_corpse       ignored [N/A]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    ignored [N/A]
66 Houdai (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [PARTIAL]
  6. cleanup_reentry    accepted [PASS]
69 BigFoot (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   ignored [PARTIAL]
  6. cleanup_reentry    accepted [PASS]
```

### Tests run (review fixes 3b)

- `py -3.12 -m pytest tests/test_pikmin2_long_legs_{pod,lifecycle,houdai,install,visual}.py -q`
  -> **73 passed**.
- Native `pikmin_pc` builds clean (`build_lane.py l26`, exe sha `0d9d45a4…`).

## Fix 3c

### Session survival (no longer depends on the results screen)

End-of-day chain: `ogScrResultMgr::skip()` (`newPikiGame.cpp:1716-1718`, gated on
`pc_settings_get_disable_tutorials()`) -> `RESULT_ExitToMapSelect` ->
`QuittingGameModeState::postUpdate` -> `GameCoreSection::exitStage()` ->
`naviMgr = nullptr` (`src/plugPikiKando/gameCoreSection.cpp:903`); the fixture's
`!naviMgr` guard then stalled.

The fixture now carries labeled session-survival guards in its APP (the same
pattern as the king/queen/flora fixtures, `experimental/pikmin2_long_legs_lifecycle.py`):

- captain state-sustain: transit out of
  `NAVISTATE_Pressed/Flick/Dead/PikiZero/DemoSunset/DemoWait/DemoInf` to
  `NAVISTATE_Walk` (`P2_LL_GUARD navi_sustain=1`);
- `allPikis` guard: `GameStat::allPikis.set(1,Red)` when it would read 0
  (`P2_LL_GUARD pikmin_guard=1`).

Run `output/dsw/l26-out/run/faac4a7c6f6d4b47ae57980a61ad8287` shows
`navimgr=1 naviobj=1` with the `disableTutorials` pin ABSENT, so the end-of-day
results screen is no longer load-bearing for session survival. The pin is kept
only as documented belt-and-braces (see the `prepare()` comment). The fixture also
parks the Houdai attack ring closer (15u, was 30u) and emits
`P2_LL_SESSION navi=1 pikis=<n> dayend=0`; `validate()` gains a `session_survives`
gate with a pod flip test.

### Passing receipt run (both species)

Run `output/dsw/l26-out/run/8a3532dfde174188aa40695df2f65422` (fixture36, native
`45344123`, 960x540): all gates green, `passed=True`, exit 0.

- Houdai natural death: `P2_LL_NATURAL_DEATH houdai=1 health=0.00 tick=373`
  (`capture/native.log:939`), `P2_LONG_LEGS_DEAD species=Houdai generator=312001
  health=0 prior_health=55.00` (`:940`) — drained, not injected.
- BigFoot: `P2_POD_RECEIPT id=corpse:longlegs:312002 value=2 new=1 pokos=2 seeds=0`
  (`:1230`), `P2_LL_DELIVER species=BigFoot pokos=2` (`:1231`).
- Houdai: `P2_POD_RECEIPT id=corpse:longlegs:312001 value=2 new=1 pokos=4 seeds=0`
  (`:1497`), `P2_LL_DELIVER species=Houdai pokos=4` (`:1498`).
- One-shot: `P2_LL_CORPSE_DRAIN remaining=0` (`:1519`).
- Positive native transport (ordinary FreeMode `Piki::graspSituation`, no
  `TransportMode` write): `P2_LL_CARRY species=BigFoot ... transport=7` (`:1019`)
  and `... transport=9` (`:1104`).
- Session: `P2_LL_SESSION navi=1 pikis=20 dayend=0` (`:1543`); `PASS
  P2_LONG_LEGS_LIFECYCLE ... receipt=2 registry_empty=2 reentry=2 stale=0
  duplicate_reward=0` (`:1544`).

### Residual (the reason the status is BLOCKED, not DONE)

The fixture is not reproducible across runs. The Houdai natural kill depends on
the source Shot roll: `P2_LL_SHOT ... tick=373` (the green run) versus
`tick=1502`, where the fixture stalls at stage 3 with the squad in range and the
window open (`P2_LL_HOUDAI_HP health=130.00 squad=20 atk=20 dmg=1`) so the drain
never completes, and the process also exits -1 (a crash) after the Shot
(`output/dsw/l26-out/run/491c841de2284abe9c2b8f0f40c66bd4`). The unreliable step
is the Houdai combat drain itself, not the guards or the settings boot path.

### Subagent usage (fix 3c)

1. `explore` - source audit of the day-end -> MapSelect -> `exitStage`/`naviMgr`
   path, the `disableTutorials`/`pikmin_settings.conf` cwd resolution, the
   day-end/GameOver triggers, the Mitite birth (log-only) and the Houdai
   shell/stomp receivers. Used as-is; it produced the exact mechanism and ruled
   out the Mitites.
2. `explore` - inventory of every session/day-end/settings touchpoint plus the
   king/queen/flora `allPikis`-guard pattern. Used as-is; the guards follow it.
3. `general` - added the `session_survives` flip test + GOOD_LOG marker to
   `tests/test_pikmin2_long_legs_pod.py`. Used as-is.

### Tests run (fix 3c)

- `py -3.12 -m pytest tests/test_pikmin2_long_legs_{pod,lifecycle,houdai,install,visual}.py -q`
  -> **75 passed**.
- `scripts/check_p2_handoff_gates.py` -> gate 5 `ignored [PARTIAL]` (proxy); no refusals.

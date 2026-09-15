# Lane 26 (Long Legs / Man-at-Legs) — DeepSeek handoff

Tracking issue [#312](https://github.com/4laric/pikmin-randomizer/issues/312); parent [#173](https://github.com/4laric/pikmin-randomizer/issues/173).
Implementation owner: Codex through shared account `4laric`; executing agent/session: DeepSeek (lane 26, `dsw/l26-root`).

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

## Six arena gates (Houdai 66 + BigFoot 69)

Natural (combat-driven) vs injected (fixture `mHealth=0`) labelled separately.

| Gate | Result | Evidence |
|---|---|---|
| 1. Exact identity + spawn | PASS | `P2_LONG_LEGS_BIND generator=312001 species=Houdai ... native_fsm=implemented` + BigFoot; `P2_LONG_LEGS_BANK total_mod_bytes=218816 species=2` |
| 2. Autonomous movement + animation | PARTIAL (bind-pose) | `P2_LONG_LEGS_STATE` schedule observed (BigFoot Land/Wait/Flick cycle; Houdai Land); no IK translation or skeletal playback |
| 3. Attacks + receivers | PASS (natural) | `P2_LONG_LEGS_CRUSH species=BigFoot ... pikmin=20` (landing foot-crush reaches live squad); `P2_LONG_LEGS_DAMAGE health=115..25.00 prior=...` incremental drain |
| 4. Death + corpse (source intent) | PASS (natural BigFoot) | `P2_LONG_LEGS_DEAD ... prior_health=25.00` then `P2_LONG_LEGS_BIRTH ... count=30` (source no-carcass child burst). Houdai injected: `prior_health=130.00` (labelled `P2_LL_INJECT ... not_natural_combat=1`) |
| 4b. Proxy corpse | proxy artifact | `P2_LL_CORPSE species=BigFoot/Houdai pellet=1` — the P1 Chappy placement vehicle's corpse, NOT a source Long Legs carcass |
| 5. Transport + reward | UNTESTED | cargo-free arena (no Pod); Mitite children (lane 14) and held-treasure drop (lane 06) logged as intents only |
| 6. Cleanup + re-entry | PASS | `P2_LL_FORGET ... count=0 registered=0` both; `P2_LL_REENTRY ... old=<ptr> new=<ptr> stale=0 fresh=1 count=2` both; `P2_LL_NOREWARD pod=0 pokos=-1 fresh_corpses=0` |

Natural-vs-injected: BigFoot died **naturally** (`P2_LL_NATURAL_DEATH bigfoot=1`,
health drained 130 -> 0 by real Pikmin attacks; `prior_health=25.00`). Houdai's
lethal step is **injected** and labelled. Completion marker:
`PASS P2_LONG_LEGS_LIFECYCLE death=Houdai,BigFoot corpse=2 registry_empty=2 reentry=2 stale=0 duplicate_reward=0`.

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

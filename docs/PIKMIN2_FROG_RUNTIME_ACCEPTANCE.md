# Frog proxy runtime acceptance

Issue #201 / #167. Codex, shared 4laric. This extends the visual handoff with a
bounded original Impact Site runtime probe. It does not complete the family.

New source: `experimental/pikmin2_frog_runtime.py` and
`tests/test_pikmin2_frog_runtime.py`. No production native source changed.

## Fixed evidence

Successful executable: `output/p2-frog-runtime/fixture03/fixture.exe`, SHA256
`733ef2d675c800f3ca67147e527af7439dc381309acbf067820ce954341d74e0`.
Native HEAD `b602d8c43dc6a1132821f787b99a28097c3c7521`; the snapshot records
existing tracked edits in `creatureCollision.cpp` and `goalItem.cpp`, diff SHA256
`7c5baccf4deb14218bb8690dc795a9a6a0c629e3bf2d2f3b9eec501a6bb957ad`.
This is not described as a clean-HEAD executable. Full input/header/library hashes,
commands and initial/final no-work checks are recorded in baseline/provenance.json
and instrumentation.json. Only private fixture/family/tutorial objects were linked.

Successful run:
`output/p2-frog-runtime/validation02/stages/bf8869d6786a4c2599ea64c494f03410`.
Evidence: native.log, runtime-evidence.json, motion-summary.json and four captures.
Model bank is the final #194 import; exact config SHA256
`0c929f7b0ac5c7375d0df2c277f8a574c71e61b9dcd9eaac4e0f1148071065ec`.

Reproduction uses the runtime module's `build` and `run` subcommands with the
native/build-randomizer path, exact expected head, final source import04 and
original P1 assets. Never reuse a fixture rejected by freshness checks. `--resume`
only finishes an uncompleted private link after validating its original snapshot,
expected head and unchanged fixture source; it refuses completed evidence.

## Gates

| Gate | Result | Evidence / limits |
|---|---|---|
| Four identities/full birth XYZ | PASS | IDs201001–4, native0/33, each exactly one; generator and stored birth match manifest within0.02 |
| Registration and P1 controls | PASS, bounded | Only first two registered; native maximum health unchanged; both controls alive at end |
| Live native-counter animation | PASS | Both source species idle, turn, wind up, wait airborne, drop and attack under normal P1 FSM; no motion/target/state injection |
| Live visual visibility | PASS, limited fidelity | Four PPM captures converted losslessly to PNG and inspected; yellow and pale spotted source models distinct from P1 controls |
| Corpse lifecycle/render | PASS with injected stimulus | Two accepted `InteractAttack(navi,nullptr,10000,false)` calls; native death animation and two live PelletView corpses, both source final-dead poses observed |
| Natural combat parity | UNTESTED | Ordinary jumping/attacks and captain damage visible, but no source-P2 mechanics/contact assertions |
| Carry/rewards | UNTESTED | No transport assigned or Pod credit claimed; P1 pellet drops visible |
| Reset/re-entry | PASS (new) | `P2_FROG_CLEANUP registered_before=4 cleared=4 reentry=4`; `pc_p2_frog_reset()` rejects stale registrations, `pc_p2_frog_setup()` rebuilds them; controls stay unregistered |
| Absent-profile launch | UNTESTED | no absent-profile run in this slice |
| Full scene/day reload | UNTESTED | manager reset/re-entry covered; full scene/save transition not |

Before attacks, both imports have 24 sampled native motion observations and
nontrivial XYZ movement. Frog Y spans0–136.7171; MaroFrog30–135.7601. These are
physics/jump observations after the exact birth check, not failed placement.
An ordinary P1 Frog stays at its starting XZ and turns; the P1 Frow jumps/moves.
The probe does not require every control to move merely to call the test passed.

Visual caveat: the source models are noticeably brighter and appear larger than
the P1 counterparts in these captures. Lighting/material and source scale/contact
fidelity are **not signed off**. Existing sampled-model material/TEV approximations
remain; no corrective color/scale guess was applied. Model-space attachment and
carried-corpse alignment still need dedicated evidence.

## Explicit fixture interventions and failures

- Camera target alternates between the two registered actors using the existing
  Pcam API; enemy/captain positions and gameplay target pointers are not rewritten.
- Original Impact Site raises tutorial13 (extinction) before the observer starts.
  A private existing-pattern tutorial shim supplies A pulses to its actual UI
  controller. Logs identify the prompt and inputs; demo flags are marked after
  active observation begins. No production tutorial logic was changed.
- At active tick360 the fixture injects legal lethal attacks, waiting for actors
  not to be invincible. Damage then passes through native receivers/death FSM.
  Death animation frames do not count as proof of pre-attack natural animation.
- Fixture01 was rejected for a private include typo and never run. Fixture02
  built, but validation01 timed out at startup: bank registration/static draw
  hooks passed, no active birth assertions. Logs remain preserved. Fixture03
  initially stopped before final link because the tutorial translation unit is
  inside libpikmin_legacy.a; the corrected private link supplies that complete
  object before the copied archive. This uncompleted fixture was resumed only
  after its baseline snapshot was revalidated.

Four focused evidence-parser tests pass, including rejecting missing corpses,
duplicate birth rows and animation seen only after injected attacks. No player
save, shared build, native export, commit or QA bundle was modified.

## Maintained-line reset/re-entry adoption (lane 16 Frog/MaroFrog, 2026-09-14)

This slice ports the frog runtime fixture to the maintained pair and adds the
manager reset/re-entry gate; required `Tadpole`/`Catfish` species-FSM work is
owned by the active species lane #407 and is not touched here.

- Fixture baseline adopted: 20-red `ensure_pikmin_squad` overlay, live squad,
  960x540 centred window log line present, no extinction screen.
- Fixture `output/lane16-frog-runtime/fixture/fixture.exe` SHA-256
  `7a483a7987216eef997425f0b1fcaaf7666e85a44e1881e2d4ad831a7796ddaf`
  (`instrumentation` status built) against native maintained
  `9735870cea769169446c524b6ae0cbdb07ed920e` and fresh integration build
  `output/p2-upstream433-build`.
- Run `output/lane16-frog-runtime/run1/stages/4e105fdf4c604feb8241639348d8bd7c`:
  PASS, exit 0; `p2-frog.txt` config SHA-256
  `0c929f7b0ac5c7375d0df2c277f8a574c71e61b9dcd9eaac4e0f1148071065ec`
  (matches the documented final import04 bank).
- Remaining: natural combat parity, transport/rewards, P2 mechanics, absent
  profile launch and full scene/day reload.

## Source combat parameters and identity health (lane 16, 2026-09-14)

The maintained frog body is visual-only with P1 proxy gameplay, so registered
actors still used P1 health/attack values. This slice binds the audited source
parameter set to the two registered species and exposes it through the shared
param chain; unregistered controls are untouched.

- Native: `pc_port/pc_p2_frog_policy.h` now carries the source `Params` table
  (health 800/1100, sight 360, max attack range 200/250, attack damage 10/20,
  air time 1, jump speed 320/350, jump-failure 0.2/0.1, fall speed 300/330,
  corpse Pokos 5/7). `pc_port/pc_p2_frog.cpp` adds `pc_p2_frog_param_f`, wired in
  `include/teki.h` alongside the kogane/armor/sokkuri hooks, and `pc_p2_frog_setup`
  sets each registered actor's `mHealth` to the source value and logs
  `P2_FROG_READY ... health=... max_health=...`. The control keeps P1 values
  because the hook falls back to the raw P1 param for unregistered actors.
- Host model: `experimental/pikmin2_frog_behavior.py` encodes the source FSM and
  motion mapping (Jump=type1, Fall=type2, Fail=damage, Carry=type5), jump
  resolution (displacement / air time + jump speed, per-species failure), the
  landing press (blocked only while bittered), MaroFrog captain retargeting and
  the corpse/carry contract. `validate_ready()` machine-checks the native READY
  rows for source health. Tests: `tests/test_pikmin2_frog_behavior.py` (8 passing).
- Fixture: `pikmin2_frog_runtime.py` now expects source health for registered
  actors and P1 health for controls, instead of requiring P1 health for all four.
- Fixture baseline adopted: `PIKMIN_P2_ROOM_WINDOW=960x540`; observed log line
  `Experimental preview window set to 960x540 windowed and centered`; 20-red
  `ensure_pikmin_squad` overlay; live squad, no extinction screen.

### Observed native run (private build, 2026-09-14)

- Native `opencode/p2-lanes16-18-native` @ `5d0923c2f876c7218550d0fdda369e7d549e13e5`
  (base `f14c6851`), private build `output/lanes16-18-native-build`
  (`ninja -n pikmin_pc`: no work), `pikmin_pc` executable SHA-256
  `D47B8BADD19500E152C3182658CEB8A4329E8BB366532FFAEAC57359AA74B9DF`.
- Fixture `output/lane16-frog-runtime/fixture_diag/fixture.exe` SHA-256
  `9ea61e2bfeef44e8e34b03720e6448abe759545f277dcba8a2f873e4c5d991ad`,
  provenance `built`, expected native head matches.
- Run `output/lane16-frog-runtime/run_diag/stages/f3dffd57461a47c19e33b0f693ef9cab`:
  PASS, exit 0; window 960x540 centred; `p2-frog.txt` SHA-256
  `0c929f7b0ac5c7375d0df2c277f8a574c71e61b9dcd9eaac4e0f1148071065ec`.
  `P2_FROG_BIRTH` params: registered `201001` life=800.0 visible=360.0
  atkrange=200.0 atk=10.0 and `201002` life=1100.0 visible=360.0 atkrange=250.0
  atk=20.0; controls `201003`/`201004` keep P1 values (life 2000.0/1800.0,
  atkrange 240.0, atk 30.0). Both registered species show live and corpse poses;
  `P2_FROG_CLEANUP registered_before=4 cleared=4 reentry=4`.
- Stability: the fixture originally aborted when the live 20-red squad naturally
  killed registered `201001` (source health 800 vs the P1 host's 2000) before the
  injected attack. It now records `P2_FROG_NATURAL_DEATH` instead of aborting and
  requires each registered species to reach a corpse either naturally or from the
  injected attack. Three consecutive runs after the change passed with no natural
  deaths: fixture `output/lane16-frog-runtime/fixture_natural/fixture.exe` SHA-256
  `4067BEEE9E19E77079CDDCBB9E54609FB7A58BFC7B568DD8578E7EDE896C4467`, runs
  `run_nat1`/`run_nat2`/`run_nat3` exit 0, e.g. stage
  `output/lane16-frog-runtime/run_nat3/stages/3c02ab07c61b41d6be965fad2d20fecc`.
  A natural pre-attack death is acceptable evidence, not a failure.

| Gate | Result | Limit |
|---|---|---|
| Source identity/params (A/B) | PASS (native run) | one run; unchanged controls |
| Landing press / retarget | PASS (host model) | native receiver not yet asserted |
| Jump attack resolution | PASS (host model) | source event execution still P1 |
| Death/corpse (D) | PASS with injected attack | natural damage parity untested |
| Transport/reward (D) | UNTESTED | carry-observation fixture implemented; no run yet, no native receipt |
| Cleanup/re-entry (E) | PASS (manager reset/re-entry) | full scene/day reload untested |

### Natural combat observation (lane 16, 2026-09-14)

New private fixture `experimental/pikmin2_frog_combat.py` pins the 20-red starting
squad in contact with registered Frog `201001` and observes P1's ordinary combat
exchange with **no injected damage** over a fixed 1200-observation window.

- Fixture `output/lane16-frog-runtime/fixture_combat3/fixture.exe` SHA-256
  `6761ebd6...`; run `output/lane16-frog-runtime/run_combat3/stages/0627ff039c404bad914bc82f4eb7c433`:
  PASS, exit 0, 960x540 centred.
- Observed: the registered Frog's health falls from 800 to a 530 minimum under
  natural Pikmin attacks (vulnerability), while the frog's landing press reduces
  the squad from 20 to 1 (frog attack). Unregistered controls `201003`/`201004`
  stay alive; no injected attack is used.
- The 20-red default squad is not enough to kill the source-800 frog within the
  window, so the frog's lethal path is still the injected-death fixture above; the
  natural exchange itself is now observed.
- Validator `tests/test_pikmin2_frog_combat.py` (3 tests) rejects a missing begin,
  no vulnerability, no squad loss, a control loss, and a death without a corpse.

### Corpse transport/reward consumer (lane 16, 2026-09-14)

Host-side reward bookkeeping for `enemy:17`/`enemy:18` now exists in
`experimental/pikmin2_frog_rewards.py` on the lane-06 receipt schema, with
`landing_press_victims`/`carry_route` added to the behavior model. It models the
audited source corpus drop (Onion ledger, corpse Pokos 5/7, count 1) and proves
exactly-once pickup across revisit and JSON-persistence restart; it reads and
mutates no save. Native corpse carry, Onion deposit and receipt delivery remain
unwired, so the Transport/reward (D) and native reward-persistence (F) gates
stay UNTESTED. A new family-local `P2_FROG_PRESS` marker in `pc_p2_frog.cpp` is
unbuilt instrumentation for the P1-proxy Attack motion, not press proof. See
[the reward consumer note](PIKMIN2_FROG_REWARDS.md).

### Corpse carry/delivery observation fixture (lane 16, 2026-09-14)

New private fixture `experimental/pikmin2_frog_carry.py` reuses
`experimental.pikmin2_frog_runtime.build`/`run`. After preview readiness it reads
`frog-positions.txt`, verifies the registered Frog `201001`/MaroFrog `201002`
birth rows, observes an initial window and then injects the same two legal
lethal `InteractAttack(navi,nullptr,10000,false)` calls as the runtime fixture.
It then watches the ordinary P1 carry path rather than a fabricated reward:

- the dead actor's `Pellet` is located by `mPelletView` in `pelletMgr`
  (`P2_FROG_CORPSE`);
- carry is the real native attachment of a live Pikmin to that pellet
  (`getStickObject`/`mPikiCarrier`/`mCarrierCount`), logged as
  `P2_FROG_CARRY id=... carried=1`, with bounded route ticks;
- delivery is the pellet leaving the live set at absorption
  (`P2_FROG_DELIVER id=... delivered=1`).

No native hook is required: these are existing public `Pellet`/`Creature`/
`Piki` members, so `native/pc_port/pc_p2_frog.cpp` is unchanged. If P1 does not
auto-carry within a bounded window the fixture moves the surviving squad next to
the corpse once, logging `P2_FROG_CARRY_ASSIST`, and never fabricates the
delivery. The result is honest: `validate()` returns `passed` only when both
corpses exist and at least one carry **and** delivery is observed; otherwise it
exits with `UNOBSERVED P2_FROG_CARRY ... unobserved=1`.
`tests/test_pikmin2_frog_carry.py` (7 tests) accepts a complete observation and
rejects a non-zero exit, a missing carry, a missing delivery, an injected-only
corpse log, a missing corpse and a missing registered birth. The native run is
pending the coordinated GL slot; native Onion/receipt delivery and save
persistence remain open.

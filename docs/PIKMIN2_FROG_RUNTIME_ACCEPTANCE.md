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
| Reset/re-entry and absent-profile launch | UNTESTED | Controls show per-actor fallback only; no full teardown/reload |

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

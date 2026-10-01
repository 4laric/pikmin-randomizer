# Muse contributor 56: Queen30 transport candidate independent acceptance (#496)

Implementation owner: Codex through shared GitHub account 4laric; executing
contributor Muse Spark 1.3 through OpenCode
(`opencode/muse-spark-1.3-contributor-free`), lane muse-queen (l56).
Parent #445; wave #491. Attempt `052c9c819fd44fafbe02660e65a1bd91`,
generation 1. King WarCry is passed and untouched by this slice.

## Scope and method

Verify — not reimplement — the already-produced lane24 Queen gate-5
candidate (`output/deepseek-wave/handoffs/l24.md`, diagnostic gate-5 slice,
`l24.status` = `DONE gate5`). Work is strictly additive and read-only toward
the candidate:

- Read the cited candidate log end-to-end with TWO independently written
  observers (Python `experimental/pikmin2_muse_queen.py` and C++
  `native/tools/p2_muse_queen_fixture.cpp`); neither reuses lane24's
  validator code.
- Source-audited the candidate sidecar and receipt path read-only
  (`output/dsw/native-l24`, pinned at `21e7819e`) and the retail Queen
  source (`native/pikmin2-research`, `Queen.cpp`/`setParameters`/`onKill`).
- Did NOT edit any Queen/King/shared native module, did NOT touch the
  legacy lane24 worktrees, did NOT re-run any GL fixture: a live rerun would
  require the candidate's sidecar plus shared-hook edits that are outside
  the reserved files, so independent log-chain reproduction plus source
  audit is the bounded slice. No new runtime evidence is claimed.

Pinned candidate commits inspected read-only (legacy worktrees):

- Root `output/dsw/l24-root` head `1f8d7b62` (gate-5 set: `f1289446`
  creature fixture+harness, `58b3a3fd` gate-5 handoff, `1f8d7b62`
  validator+tests).
- Native `output/dsw/native-l24` head `21e7819e` (gate-5 set: `7c1c54f9`
  `pc_p2_queen_teki` sidecar, `e8b32e3b` AI/eat suppression,
  `21e7819e` shared-hook wiring).
- Candidate build/fixture provenance from the handoff: native `21e7819e`,
  clean, exe sha `19ac518b...`, fixture provenance `built`.

## Independent finding: gate-5 transport chain is SOUND

Both observers independently derive the complete natural chain from the raw
cited log
`output/dsw/l24-out/queen-creature-runtime/queen/62b8ff57457c4edb90dd16958f665118/native.log`
(1388 lines, exit-0 run, `Experimental preview window set to 960x540
windowed and centered` at :7, 64-red baseline, no extinction):

| Step | native.log:line | Content |
|---|---|---|
| READY | :727 | `P2_QUEEN_TEKI_READY generator=230010 type=3 binding=creature_host health=5000.0` — source Queen HP |
| suppression | :728 | `P2_QUEEN_TEKI_HOST_AI_SUPPRESSED ... eat_state=CHAPPYSTATE_Unk8 latch_preserved=1` — documented, latch kept |
| baseline/armed | :751/:787 | 64 reds, `P2_QUEEN_CREATURE_ARMED no_injection=1 deploy_once=1` |
| blows-driven flicks | :777–:1246 | 63–65 `P2_QUEEN_TEKI_FLICK` lines across ladder 30/35/45/50 |
| natural death | :1346–:1347 | `P2_QUEEN_TEKI_CORPSE generator=230010 health=0.0`, `P2_QUEEN_CREATURE_DEATH_SEEN receiver=engine` |
| carcass pellet | :1352 | `P2_QUEEN_CREATURE_CORPSE_PELLET found=1` |
| carrier latch | :1355–:1385 | `P2_QUEEN_CREATURE_CARRY` with `transport` 6–7 then 0 at delivery |
| Pod receipt | :1386 | `[Pikipelago] P2_POD_RECEIPT id=corpse:queen:230010 value=2 new=1 pokos=2 seeds=0` |
| harness verdict | :1388 | `PASS P2_QUEEN_CREATURE_RUNTIME` |

Zero staging markers in all 1388 lines (exact-token scan for
`P2_QUEEN_TEKI_FORCED_TRANSPORT`, `P2_QUEEN_TEKI_TRANSPORT_INJECT`,
`P2_QUEEN_NATURAL_REPIN`, `*NAVI_HEAL`, `P2_POD_CAPTAIN_RETURN`,
`TransportMode`). No injected HP, no forced transport, no captain refill.
The Python and C++ observers agree: `PASS generator=230010 receipt_line=1386`.

Source cross-checks (all read-only): retail `Queen.cpp` `onKill` runs the
standard `EnemyBase::onKill` corpse path with no custom Pellet creation
(so a generated-carrier carcass recipe is structurally necessary, not a
shortcut); Queen HP comes from `C_GENERALPARMS.mHealth` (general fp00),
matching the candidate's `HealthDefault = 5000.0f`; the receipt `value=2`
comes from the Pod package `corpseValue` (`P2_POD_1` config), i.e. lane-06
reward plumbing, not Queen-specific semantics.

## Exact caveats for the integrator (do not relabel as new findings)

1. Carried identity is the bound generated carrier's carcass
   (`binding=creature_host`, observed `carry=3`), so carry counts and the
   `value=2` reward are carrier-derived, not source-Queen 20-30-carrier
   semantics. The transport *mechanism* (natural death → real carcass
   pellet → autonomous `Transport` latch → Pod `corpse:queen:<gen>`
   receipt) is what this slice accepts; reward magnitudes stay with lane 06.
2. Gate-1 identity in the creature run is the authored carrier binding
   (generator 230010, held at spawn); gates 1–4/6 below are preserved from
   lane24's accepted freemode evidence, not re-run here.
3. No live GL rerun was executed (see Scope): reproduction is two
   independent log-chain derivations plus source audit, recorded honestly
   as such. A future combined-build rerun by the integrator would close
   the loop but is not required to consume this review.

## Concrete source ID
- Source ID: 30 `Queen`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | output/deepseek-wave/handoffs/l24.md queen freemode spawn `id=230010 enemy=30` (preserved lane24 evidence, not re-run) | natural |
| 2. Autonomous movement and animation | PASS (natural) | output/deepseek-wave/handoffs/l24.md queen sleep/wait/flick/roll/born clips + 50 larva births (preserved lane24 evidence, not re-run) | natural |
| 3. Attacks and receivers | PASS (natural) | output/dsw/l24-out/queen-creature-runtime/queen/62b8ff57457c4edb90dd16958f665118/native.log:777 blows-driven flick ladder 30/35/45/50 | natural |
| 4. Death and corpse | PASS (natural) | output/dsw/l24-out/queen-creature-runtime/queen/62b8ff57457c4edb90dd16958f665118/native.log:1346 natural death health=0.0 plus carcass pellet :1352 | natural |
| 5. Actual transport and reward | PASS (natural) | output/dsw/l24-out/queen-creature-runtime/queen/62b8ff57457c4edb90dd16958f665118/native.log:1386 corpse:queen:230010 value=2 new=1 pokos=2 | natural |
| 6. Cleanup and re-entry | PASS (natural) | output/deepseek-wave/handoffs/l24.md queen exit 0 no leftover (preserved lane24 evidence, not re-run) | natural |

## Tests and validation

- `py -3.12 -m pytest tests/test_pikmin2_muse_queen.py -q` → 11 passed:
  real candidate log PASS (generator/ready/receipt lines, zero staging
  markers, caveats always reported), 8 synthetic negative/edge cases
  (every staging token, missing receipt, wrong HP, generator mismatch,
  empty log, benign `no_injection` substring), plus strict-MinGW
  (`-Wall -Wextra -Werror`) build-and-agree of the C++ observer
  (clean-chain PASS, post-receipt and mid-chain staging FAIL).
- `py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_QUEEN_HANDOFF.md`
  run before handoff (see checkpoint evidence).
- Reviewer CLI reproduction:
  `py -3.12 experimental/pikmin2_muse_queen.py --log <native.log above> --expect-generator 230010`
  → `VERDICT PASS`.

## Ordered commits (private worktrees only)

- Root (`C:\Users\alari\pikmin-randomizer\output\msw\l56-root`,
  branch `codex/muse-l56-queen`, base `72a2c450`): reserved files only —
  `experimental/pikmin2_muse_queen.py`,
  `tests/test_pikmin2_muse_queen.py`, `docs/PIKMIN2_MUSE_QUEEN_HANDOFF.md`.
- Native (`C:\Users\alari\pikmin-randomizer\output\msw\native-l56`,
  branch `codex/muse-l56-queen-native`, base `7b9ecaa6`): reserved file
  only — `tools/p2_muse_queen_fixture.cpp` (self-contained, no module
  edits).

## Remaining work

- Integrator decision on the ADMISSION CANDIDATE for Queen30 gate 5 using
  this review; optional combined-build GL rerun of the pinned candidate
  (`21e7819e` / `1f8d7b62`) for a second live receipt.
- Reward-magnitude semantics (`value=2`, carrier-derived carry counts)
  belong to lane 06, not this slice. No ADMIT writes made here.

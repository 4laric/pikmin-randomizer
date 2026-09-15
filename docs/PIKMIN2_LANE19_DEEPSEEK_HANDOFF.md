# Lane 19 (Mamuta) DeepSeek handoff (fix1) — #221 / #168

Implementation owner: Codex via shared account `4laric`. Executing agent: DeepSeek
(`deepseek-v4-pro`), lane 19, 2026-09-14. Root worktree `output/dsw/l19-root` on
`deepseek/p2-l19`; native worktree `output/dsw/native-l19` on
`deepseek/p2-l19-native`. No maintained checkout, shared build, native origin or
upstream GitHub was touched; nothing was pushed. This revises the prior handoff
whose central "health-floor/regression" claim was wrong.


### Integrator note (review of fix 1)

- The captain-down detection path is unit-tested only; no GL run under the lane evidence dir has emitted a CAPTAIN_DOWN marker yet (fix1-01 predates the mHealth<=1 check).
- fix1-02 is the first natural Mamuta kill on the wave: died tick 1922, corpse, transport started; delivery did not finish inside the 2400-tick window.

## Correction (review item 1)

The previous handoff claimed a "health floor / natural-kill regression on
`b805d9c6`". That is **wrong**. There is no health floor and no regression:

- Every stalled run froze at the tick where the 20th `P2_MAMUTA_NAVI` line
  reported captain health `0.000`. `pc_p2_mamuta_bury_navi`
  (`pc_port/pc_p2_mamuta_rules.cpp:69-79`) subtracts 5 HP per pound; at `<= 1` HP
  `navi.cpp:402-404` issues `startPause`, and `NaviDeadState::init`
  (`naviState.cpp:3206-3224`) sets `orimaDead`/`StageFinish`/`releasePikis` and
  pauses the core. The fixture only gated on `mPauseAll`/movie, so ~1,900 frozen
  ticks were counted as natural combat.
- The prior worker build `a54f4af2` won the same race (killed at tick 466–500 with
  the captain at ~10 HP); my 02/03 runs lost 2 and 5 reds early to
  `P2_MAMUTA_PLANT` and lost the race. `git diff a54f4af2..HEAD -- pc_port/pc_p2_mamuta*`
  is empty: the Mamuta module/rules are unchanged.
- The captain was pinned 50 units south, inside the Miurin's `TPF_AttackableRange`
  (70) / arm reach (`TAImiurin.cpp:801-809,544-586`), so every pound hit it.

**So gate 4 was BLOCKED by the P1 captain-down pause (pre-existing, same as the
cont437 run), and the owner is the lane-19 fixture** — not lanes 01/08/10/13.
The bisect request to lanes 01/08/10/13 is dropped.

## What this fix adds

1. **Install regression fix (kept).** `experimental/pikmin2_mamuta_install.py`
   emits the three single static anchors (`miulin_{wait,dead,attack1}.mod`) that
   the approved native baseline loads, alongside the pending time-sampled banks.
2. **Captain-down detection.** Both fixtures now detect `GameStat::orimaDead`,
   `NAVISTATE_Dead`, **or** `Navi::mHealth <= 1.0f` (the P2 bury drains HP without
   a Dead transit), emit `P2_MAMUTA_{POD,REVISIT}_CAPTAIN_DOWN tick= health=`, stop
   counting observation ticks, and finish with a `captain_down` completion. The
   validators classify `natural_{kill,rekill}` as `BLOCKED(captain_down)`.
3. **Win attempt.** The fixtures now park the captain ~250 units south (beyond the
   Miurin's arm reach) with a <150-unit re-park, and free-deploy the 10 reds in a
   ring (radius 22) around the Mamuta, re-ringing survivors every 120 ticks. No
   bury, lethal hit or transport action is forced; the Pikmin deal all damage.

## Six arena gates (natural vs injected)

| Gate | Result (current head `b805d9c6`) |
| --- | --- |
| 1. Exact identity and spawn | **PASS** (P1 Miurin proxy) — `P2_MAMUTA_POD_BIRTH id=221001 type=24 squad=10 color=red` |
| 2. Autonomous movement and animation | **PASS** — `approached=1`, full state coverage (`00017f9c`), static-anchor draw |
| 3. Attacks and receivers | **PASS** (proxy, natural) — natural `P2_MAMUTA_PLANT kind=1 happa=2`; navi receiver (`P2_MAMUTA_NAVI damage=5.0`) observed in the pre-park runs |
| 4. Death and corpse | **PASS (1 run) / FLAKY overall** — `fix1-02`: natural kill `died_tick=1922` + `corpse=1`; fix1-03/04 (park-250) wiped the squad before the kill; fix1-01 (park-100) ended in the captain-down freeze (integrator correction) |
| 5. Actual transport and reward | **UNPROVEN** — `fix1-02` corpse was picked up (`transport=1`) but not delivered by window end (`goal=0`, `pokos=0`) |
| 6. Cleanup and re-entry | **partial PASS** — reset/forget + control alive; revisit fixture built but runtime UNTESTED (gated on gate 5) |

Injected: none. Squad ring-deploy, captain park/re-park and re-ring are documented
fixture-placement interventions (the review-prescribed "free-mode-deploy the reds
and park the captain"); the kill/corpse themselves are natural (no forced health,
bury or lethal hit). `captain_down` runs are now correctly classified, not counted
as frozen natural combat.

## Why gate 5 remains open

The captain-park strategy removes the captain-down pause but shifts the Miurin's
pounds onto the Pikmin, whose P2 bury converts them (permanent with a parked
captain). 10 basic reds vs a 2485-HP Mamuta is marginal: `fix1-02` left one red
that killed (1922) and started carrying, but delivery did not finish in the
2400-tick window (the fix1-02 exe 34b9226c predates the NATURAL_TICKS bump to 3600; carry ran ~300 ticks before the window closed — integrator correction); `fix1-03/04` lost all reds and the Mamuta healed. This is a
squad-balance/attrition question for the integrator (e.g. 20-red overlay squad),
not a lane-19 code defect.

## Build and run evidence

Native `bin/nectar.exe` = `61fb1c850bd551c8c7c9d07a38e30dbb3ded5faf85ff866cdad7b1108c0b8fa8`
(build-evidence file, native head `b805d9c6`, `ninja -n` clean, `PIKMIN_NATIVE_JAUDIO=ON`).

Per-run fixture.exe SHA-256 (`result.json` provenance):
| run dir | outcome | fixture.exe |
| --- | --- | --- |
| `mamuta-pod-accept-natural-01` | aborted `P2_MAMUTA invalid profile` (pre-install-fix) | — |
| `mamuta-pod-accept-natural-02` | no kill (frozen at captain-down pause) | `cc8c22575822...` |
| `mamuta-pod-accept-natural-03` | no kill (retreat variant) | `73346ea32400...` |
| `mamuta-pod-accept-fix1-01` | no kill (park 100; frozen 1046.7, `captain_down` not flagged — pre-`mHealth<=1`) | `21c47aac663c...` |
| `mamuta-pod-accept-fix1-02` | **natural kill 1922 + corpse + transport started** | `34b9226c4fac...` |
| `mamuta-pod-accept-fix1-03` | no kill (squad wiped, healed) | `0be4d6ccd8ae...` |
| `mamuta-pod-accept-fix1-04` | no kill (squad wiped, healed) | `0be4d6ccd8ae...` |

Revisit fixture (built, `provenance.json status=built`): `bd5acf2ebf8a5a2e3ef16b93bcc2186378dbf018c674058eb28b442dd52e967e`.

## Tests

`py -3.12 -m pytest tests/test_pikmin2_mamuta_pod.py tests/test_pikmin2_mamuta_revisit.py tests/test_pikmin2_mamuta_natural.py tests/test_pikmin2_mamuta_install.py tests/test_pikmin2_mamuta_cargo.py tests/test_pikmin2_mamuta_rules.py -q`
→ **54 passed, 1 skipped** (incl. new captain-down classification tests).

## Subagent usage

Three subagents were spawned in parallel (per the review's requirement), then I
did the native/fixture work, builds, GL runs, commit and this handoff myself.

1. `explore` — **Mamuta source audit** (states/events/params/receivers + the
   captain-down path). Used as-is; corrected two line cites against the real tree
   (`pc_p2_mamuta_bury_navi` is at `pc_p2_mamuta_rules.cpp:69-79`, not 65-76; the
   P2 decomp dir is `plugProjectMorimuraU`).
2. `explore` — **Mamuta candidate + ring-deploy inventory**. Used as-is; correctly
   identified the reusable ring pattern as the Kochappy combat fragment
   (`experimental/pikmin2_kochappy_arena_combat.py:16-24`, `changeMode(PikiMode::FreeMode,n)`)
   and noted the Sokkuri fixture does not ring-deploy.
3. `general` — **validator + test scaffold for the captain-down gate** (pod/revisit
   `validate()` three-way classification + tests). Used as-is (16 tests pass); I
   additionally found and fixed the missing `Navi::mHealth <= 1.0f` signal that the
   spec's `orimaDead/NAVISTATE_Dead` alone would not catch on the P2 bury path.

Net effect: the read-heavy inventory/audit were offloaded (saved ~15–20 min of
context); the test scaffold was applied directly. One shortcoming surfaced: the
subagent's spec followed the review's `orimaDead/NAVISTATE_Dead` signals verbatim,
which turned out incomplete, so I extended the detection myself after the first
runtime run (`fix1-01`).

## Reproduction

```powershell
cd C:/Users/alari/pikmin-randomizer/output/dsw/l19-root
$env:PYTHONUTF8='1'
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l19 -- `
  py -3.12 -m scripts.pikmin2_mamuta_pod_native `
    --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
    --imported C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/imported `
    --exe C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-pod-natural-fixture/fixture.exe `
    --output C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-pod-accept-fix1-05 `
    --pod-package C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/pod `
    --timeout 300
# expect: ring-deploy + captain-park; natural bury/plants; with luck died=1 corpse=1
#         (see fix1-02); kill is flaky on the 10-red squad.
```

## Slice 2

Status: **DONE slice2** — natural gate 5 (kill → carry → Pod receipt) is now
reproduced end-to-end, and the captain-down marker/classification is runtime-proven.

### What changed this slice (all root, no native)

- `scripts/pikmin2_mamuta_pod_fixture.inc`: default staging is now **captain inside
  the Miurin's ~70-unit attackable range (park 20) + ring-deploy (radius 22) + re-ring
  every 120 ticks**, which lets the captain absorb the P2 bury so ~10 reds survive to
  meet the corpse's 8-carrier lift threshold. Added a **labelled captain-down control**
  (`p2-mamuta-captaindown.txt` → park 20 with the ring skipped) and a `--captaindown`
  flag in `scripts/pikmin2_mamuta_pod_native.py`. Added carry diagnostics
  (`mincarry/maxcarry/dist`), and moved the `naviDown()` detection **before** the
  `mPauseAll`/movie gate (a real P1 Olimar death pauses the core and was blocking it).
  Removed the slice-1 `park-250`/re-park (it parked the captain out of reach so the
  bury hit the Pikmin instead, planting them below the 8-carrier threshold).
- `tests/test_pikmin2_mamuta_pod.py`, `tests/test_pikmin2_mamuta_revisit.py`:
  natural-kill and delivery "flip" tests (subagent-assigned; 24 added).

### Kill/transport rate (default staging, exe `1acfcfdf01091b3cdd5e76a151041370e8742cca01757a6a3afb79986208e595`)

| run dir | died | corpse | carried | goal | pokos | receipt | class |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mamuta-pod-deliver-01` | 523 | 1 | 1 | 1 | 2 | `corpse:mamuta:221001 value=2 new=1` | natural (all gates PASS) |
| `mamuta-pod-deliver-02` | 0 | 0 | 0 | 0 | 0 | — | `BLOCKED(captain_down)` |
| `mamuta-pod-deliver-03` | 478 | 1 | 1 | 1 | 2 | `corpse:mamuta:221001 value=2 new=1` | natural (all gates PASS) |

The race is between the ring kill (~480–520 ticks) and the captain absorbing 20
pounds (~640 ticks): ~2/3 of runs deliver, ~1/3 down the captain. Both outcomes are
now classified honestly (PASS vs BLOCKED(captain_down)).

### The delivery blocker and its fix (file:line)

The Mamuta corpse is `tkmu` with **`mCarryMinPikis = 8`, `mCarryMaxPikis = 20`** and a
Pod haul of ~530 units (run `P2_MAMUTA_POD_CARRY ... mincarry=8 maxcarry=20 dist=530.8`).
The lift gate is `aiTransport.cpp:755-768` (`numStickers >= pel->mConfig->mCarryMinPikis`),
and delivery fires `pc_p2_preview_deliver` at `pelletState.cpp:347-348`, routed to
`corpse:<prefix>mamuta:<gen>` via `pc_p2_mamuta_receipt` (`pc_p2_preview.cpp:330-332`).
With the captain parked far (slice-1), the P2 bury planted the 10-red squad down to
0–1 and it could never meet 8 carriers; with the captain inside range the squad
survives and carries. (A separate `Unregistered P2 pod cargo … view=null` abort was
seen once in `captaindown-02`, from a non-Mamuta pellet reaching the Pod; it did not
recur in the successful deliveries and is noted for lane 06.)

### Captain-down control (runtime proof, exe `faf16bebb066747456046214273f626cf48696cd12422646ab745521e50dbf35`)

`mamuta-pod-captaindown-06` (park 20, ring skipped): 20 `P2_MAMUTA_NAVI damage=5.0`
hits to captain health 0, then `P2_MAMUTA_POD_CAPTAIN_DOWN tick=527 health=0.0`,
`PASS P2_MAMUTA_POD_RUNTIME captain_down`, classified `natural_kill=BLOCKED(captain_down)`.
This is the first runtime firing of the marker + classification.

### Natural vs injected

No forced health/bury/lethal hit/transport. The squad ring-deploy, captain park and
re-ring are fixture-placement interventions (as prescribed); the kill, 10-carrier
haul, Pod suck and receipt are natural. The captain-down control is labelled
(`P2_MAMUTA_POD_CONTROL captain_park=inside70`).

### Subagent usage

Three subagents spawned in parallel, then I did the fixture/native edits, the build,
all GL runs, the commit and this handoff myself.

1. `explore` — **delivery/receipt source audit** (carry weight, lift gate, Pod/goal
   distance, receipt routing). Used as-is; the `mincarry=8 maxcarry=20` and ~520-unit
   haul figures were then confirmed empirically in the runs.
2. `explore` — **Mamuta delivery/ receipt candidate + marker inventory**. Used as-is;
   confirmed the pod-natal runner/validator wiring and marker set.
3. `general` — **natural-kill + delivery flip test scaffolding** (24 tests). Used
   as-is (all pass alongside the lane suite).

Net: the read-heavy audit/inventory were correctly offloaded (saved ~15 min of
context); the test scaffold was applied directly with no corrections.

### Reproduce

```powershell
cd C:/Users/alari/pikmin-randomizer/output/dsw/l19-root
$env:PYTHONUTF8='1'
# natural delivery (default staging): expect died/corpse/carried/goal=1 pokos=2 + receipt
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l19 -- `
  py -3.12 -m scripts.pikmin2_mamuta_pod_native --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
    --imported C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/imported `
    --exe C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-pod-natural-fixture/fixture.exe `
    --output C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-pod-deliver-XX `
    --pod-package C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/pod --timeout 300
# captain-down control: expect P2_MAMUTA_POD_CAPTAIN_DOWN + BLOCKED(captain_down)
#   (add --captaindown to the command above)
```

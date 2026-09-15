# Lane 19 (Mamuta) DeepSeek handoff (fix1 + slice 2 + review-fix 2 + slice 3 revisit) — #221 / #168

Implementation owner: Codex via shared account `4laric`. Executing agents:
DeepSeek (`deepseek-v4-pro`) for fix1/slice 2 (2026-09-14), then
DeepSeek (`deepseek-v4.1-flash`) for slice 3 (2026-09-15). Root worktree
`output/dsw/l19-root` on `deepseek/p2-l19`; native worktree `output/dsw/native-l19`
on `deepseek/p2-l19-native`. No maintained checkout, shared build, native origin
or upstream GitHub was touched; nothing was pushed. The fix1 revision corrects the
prior handoff whose central "health-floor/regression" claim was wrong.


## Commits, bases and build provenance

- Root base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`; root head
  `45d7cc1c`. Ordered lane19 root commits
  (oldest→newest): `f4c29aa6` (static anchors), `1284bcc9` (revisit fixture/runner/
  validator/handoff), `f1c7b9df` (captain-down + ring/park natural kill), `6fc3469a`
  (handoff corrections), `03e74c69` (slice2 natural kill+carry+Pod receipt),
  `fd8bf727` (review-fix 2 squad 14 + re-ring 60), `0e2113e5` (slice3 natural
  revisit), `45d7cc1c` (handoff commits/build provenance for slice3). Dirty state: clean.
- Native base `b805d9c626e4f4558c95aef7cac311a5d9a2068f`; native head
  `b805d9c626e4f4558c95aef7cac311a5d9a2068f` (clean). No lane19 native commits:
  the Mamuta native module (`pc_p2_mamuta*`, `pc_p2_mamuta_rules*`) is already in
  the pinned base, so this lane's slices are fixture/harness/evidence only.
- Build evidence (`output/dsw/l19-build-evidence.txt`):
  `2026-09-14T19:08:17 lane=l19 target=pikmin_pc native=b805d9c6... dirty=no exe=...\native-l19-build\bin\nectar.exe sha256=61fb1c850bd551c8c7c9d07a38e30dbb3ded5faf85ff866cdad7b1108c0b8fa8 ninja_n="ninja: no work to do."`
  (`-DPIKMIN_NATIVE_JAUDIO=ON`, Ninja + MinGW g++).
- Fixture adoption: `PIKMIN_P2_ROOM_WINDOW=960x540`; log
  `[PC Port] Experimental preview window set to 960x540 windowed and centered ...`;
  live starting squad `P2_MAMUTA_REVISIT_BIRTH ... squad=14 color=red`.

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

- Source ID: 54 `Miulin` (Mamuta).

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | P2 generator 221001 bound to the P1 Miurin engine actor (TEKI_Miurin 24): `output/dsw/l19-out/mamuta-pod-deliver-01/e3e978a725c54b80baf677104a51d471/native.log:739` `P2_MAMUTA_POD_BIRTH id=221001 type=24 squad=10 color=red` | natural |
| 2. Autonomous movement and animation | PASS (natural) | natural approach + full state coverage + static anchor: `output/dsw/l19-out/mamuta-pod-deliver-01/e3e978a725c54b80baf677104a51d471/native.log:1061` `P2_MAMUTA_POD_APPROACH_RESULT approached=1 min=11.2 states=00001e9c`, `:748` `P2_MAMUTA_DRAW generator=221001 anchor=attack1` | natural |
| 3. Attacks and receivers | PASS (natural) | natural P2 bury/plant and captain receiver: `output/dsw/l19-out/mamuta-pod-deliver-01/e3e978a725c54b80baf677104a51d471/native.log:750` `P2_MAMUTA_PLANT kind=1 happa=2 planted=0`, `:749` `P2_MAMUTA_NAVI damage=5.0` | natural |
| 4. Death and corpse | PASS (natural) | natural kill then carryable corpse: `output/dsw/l19-out/mamuta-pod-deliver-01/e3e978a725c54b80baf677104a51d471/native.log:802` `P2_MAMUTA_POD_DIED tick=523`; `output/dsw/l19-out/mamuta-pod-deliver-03/eff05ebe7f21417185c80126a5943113/native.log:796` `P2_MAMUTA_POD_DIED tick=478` | natural |
| 5. Actual transport and reward | PASS (natural) | Pod receipt `corpse:mamuta:221001 value=2`: `output/dsw/l19-out/mamuta-pod-deliver-01/e3e978a725c54b80baf677104a51d471/native.log:902` `[Pikipelago] P2_POD_RECEIPT id=corpse:mamuta:221001 value=2 new=1 pokos=2`; `output/dsw/l19-out/mamuta-pod-deliver-03/eff05ebe7f21417185c80126a5943113/native.log:894` | natural |
| 6. Cleanup and re-entry | PASS (natural) | `P2_MAMUTA_POD_RESET` (+ control alive) in `output/dsw/l19-out/mamuta-pod-deliver-01/e3e978a725c54b80baf677104a51d471/native.log:1064`; and slice 3 fresh-process revisit: `P2_MAMUTA_REVISIT_BIRTH`, `P2_MAMUTA_REVISIT_DIED tick=387`, `P2_MAMUTA_REVISIT_RESET`, `PASS P2_MAMUTA_REVISIT_RUNTIME observe approach receipt_revisit reset` in `output/dsw/l19-out/mamuta-revisit-01/107b823f7e6841a786f8dcfe42ac1bf6/native-revisit.log` | natural |

Injected: none. Squad ring-deploy, captain park and re-ring are documented
fixture-placement interventions (the review-prescribed "free-mode-deploy the reds
and park the captain"); the kill, corpse, carry and Pod receipt themselves are
natural (no forced health, bury, lethal hit or transport action). `captain_down`
runs are classified `BLOCKED(captain_down)`, not counted as frozen natural combat.

Gate 5 was closed in Slice 2 (below) by parking the captain inside the ~70-unit
attackable range so it absorbs the P2 bury and ~10 reds survive to meet the
corpse's 8-carrier lift threshold; the earlier fix1 park-250 staging could not
deliver because the bury planted the squad below 8 carriers.

`py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_LANE19_DEEPSEEK_HANDOFF.md`
(wave-branch script, not committed):

```text
54 Miulin (role=source):
  1. identity_spawn     accepted [PASS]
  2. movement_animation accepted [PASS]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       accepted [PASS]
  5. transport_reward   accepted [PASS]
  6. cleanup_reentry    accepted [PASS]
```

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
  every 60 ticks** (raised from 120 in review-fix 2), which lets the captain absorb
  the P2 bury so ~10 reds survive to
  meet the corpse's 8-carrier lift threshold. Added a **labelled captain-down control**
  (`p2-mamuta-captaindown.txt` → park 20 with the ring skipped) and a `--captaindown`
  flag in `scripts/pikmin2_mamuta_pod_native.py`. Added carry diagnostics
  (`mincarry/maxcarry/dist`), and moved the `naviDown()` detection **before** the
  `mPauseAll`/movie gate (a real P1 Olimar death pauses the core and was blocking it).
  Removed the slice-1 `park-250`/re-park (it parked the captain out of reach so the
  bury hit the Pikmin instead, planting them below the 8-carrier threshold).
- `tests/test_pikmin2_mamuta_pod.py`, `tests/test_pikmin2_mamuta_revisit.py`:
  natural-kill and delivery "flip" tests (subagent-assigned; 8 new test functions,
  suite 54→62).

### Kill/transport rate (default staging, exe `1acfcfdf01091b3cdd5e76a151041370e8742cca01757a6a3afb79986208e595`)

| run dir | died | corpse | carried | goal | pokos | receipt | class |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `mamuta-pod-deliver-01` | 523 | 1 | 1 | 1 | 2 | `corpse:mamuta:221001 value=2 new=1` | natural (all gates PASS) |
| `mamuta-pod-deliver-02` | 0 | 0 | 0 | 0 | 0 | — | `BLOCKED(captain_down)` |
| `mamuta-pod-deliver-03` | 478 | 1 | 1 | 1 | 2 | `corpse:mamuta:221001 value=2 new=1` | natural (all gates PASS) |

Earlier **development runs** in the same evidence dir used intermediate builds (not
acceptance): `captaindown-01` (exe `5d73f986…`, park 50 + ring, killed 562, no
delivery), `captaindown-02` (exe `4af4d40a…`, park 50 + no ring, `Unregistered P2 pod
cargo` abort), `captaindown-03` (exe `42a1bab6…`, park 20 + squad relocation, the
first full delivery: died 582, goal=1 pokos=2), `captaindown-04` (exe `e5fa3bbc…`)
and `captaindown-05` (exe `d1e19a17…`) (out-of-bounds squad relocation → extinction
timeout), `captaindown-06` (exe `faf16beb…`, captain-down control). The deliver-01/02/03
runs (exe `1acfcfdf…`) are the review-visible slice-2 acceptance set.

The race is between the ring kill (~480–520 ticks) and the captain absorbing 20
pounds (~640 ticks): at slice 2 it was ~2/3 deliver / ~1/3 captain-down. Both
outcomes are classified honestly (PASS vs BLOCKED(captain_down)).

### Review-fix 2: reliable delivery (squad 14 + re-ring 60)

Lane 06 reported 0/4 deliveries on exe `1acfcfdf…` (captain-down at ticks 481–522
every run), confirming the race was a coin-flip. Raising the shared squad to 14
(`experimental/pikmin2_mamuta_rules.py` `SQUAD_COUNT = 14`, still ≥ the 8-carrier
threshold) and re-ringing every 60 ticks instead of 120 makes the kill reliably
beat the ~500-tick captain drain:

| run dir | died_tick | carried | goal | pokos | receipt | class |
| --- | --- | --- | --- | --- | --- | --- |
| `mamuta-pod-deliver-05` | 424 | 1 | 1 | 2 | `corpse:mamuta:221001 value=2 new=1` | natural (all gates PASS) |
| `mamuta-pod-deliver-06` | 444 | 1 | 1 | 2 | `corpse:mamuta:221001 value=2 new=1` | natural (all gates PASS) |
| `mamuta-pod-deliver-07` | 387 | 1 | 1 | 2 | `corpse:mamuta:221001 value=2 new=1` | natural (all gates PASS) |

**Delivery rate 3/3** on exe
`133cbbad18ccec5a870ab9b6f501598c8c701d860b3ac76ba9aa8444afcfe737` (the committed
fix2 source). Kill ticks dropped from ~480–520 to 387–444, so the kill now reliably
wins the race and the captain survives every run. `mamuta-pod-deliver-04`
(same source, re-ring-60-only, before the squad bump) was the remaining
`BLOCKED(captain_down)` data point that motivated the squad bump.

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

**Provenance note (review-fix 2, item 3):** `faf16beb…` (00:32) is an earlier build
than the slice-2 acceptance exe `1acfcfdf…` (00:37). On the fix2 committed source the
`--captaindown` control was re-run (`mamuta-pod-captaindown-07`, exe `133cbbad…`) and
it no longer downs the captain: with the squad raised to 14 the un-rung squad kills at
tick 368, so the plain control now delivers — i.e. the fix removed the drain condition
that the control exercises. The marker + `BLOCKED(captain_down)` classification path
itself remains runtime-proven by `captaindown-06` and is also unit-tested.
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

## Slice 3 — natural revisit / re-entry (gate 6 / gate E+F)

Status: **DONE slice3** — the WIP revisit fixture left uncommitted at the end of
slice 2 is finished, run naturally, validated and committed. Executing agent:
DeepSeek (`deepseek-v4.1-flash`), 2026-09-15, on the same two lane worktrees.

### What changed this slice (all root, no native)

- `scripts/pikmin2_mamuta_revisit_fixture.inc`: re-entry staging now mirrors the
  slice-2 Pod fixture (captain park inside the Miurin's ~70-unit attackable range,
  14-red ring-deploy re-rung every 60 ticks, carry diagnostics), and captain-down
  detection moved before the movie/pause/UI gates. The earlier park-250 staging
  could not re-deliver (the bury planted the squad below the 8-carrier threshold).
- `scripts/pikmin2_mamuta_revisit_native.py` / `tests/test_pikmin2_mamuta_revisit.py`:
  squad 14 expectation.
- No native change. The native worktree `deepseek/p2-l19-native` remains clean at
  the pinned base `b805d9c6`; the revisit slice is fixture/harness only.

### Fresh-process revisit evidence

Each run is a fresh `fixture.exe` process in a *copy* of the slice-2 Pod stage
`output/dsw/l19-out/mamuta-pod-deliver-07/107b823f7e6841a786f8dcfe42ac1bf6`, whose
`p2-economy.txt` already persisted `corpse:mamuta:221001 2` (pokos=2) from the
prior natural Pod run. The fixture re-births the Mamuta from the staged
`default.gen` and re-runs the natural sequence; the persisted economy dedupes the
re-delivery.

| run | outcome | died_tick | receipt | prior→final pokos | classify |
| --- | --- | --- | --- | --- | --- |
| `mamuta-revisit-01` | PASS natural | 387 | `corpse:mamuta:221001 value=2 new=0` | 2→2 | all PASS |
| `mamuta-revisit-03` | PASS natural | 378 | `corpse:mamuta:221001 value=2 new=0` | 2→2 | all PASS |
| `mamuta-revisit-02` | BLOCKED(provider) | 459 | — (aborted) | 2→2 (unchanged) | `Unregistered P2 pod cargo` |
| `mamuta-revisit-04` | BLOCKED(provider) | 392 | — (aborted) | 2→2 (unchanged) | `Unregistered P2 pod cargo` |

The PASS runs emit: `P2_MAMUTA_REVISIT_READY prior_pokos=2`; re-birth
`P2_MAMUTA_REVISIT_BIRTH id=221001 type=24 squad=14 color=red`;
`P2_MAMUTA_REVISIT_DIED tick=387`; `P2_MAMUTA_REVISIT_CORPSE`;
`P2_MAMUTA_REVISIT_CARRY ... mincarry=8 maxcarry=20 dist=526.9`;
`[Pikipelago] P2_POD_RECEIPT id=corpse:mamuta:221001 value=2 new=0 pokos=2 seeds=0`
(deduped); `P2_MAMUTA_REVISIT_RESET`; and
`PASS P2_MAMUTA_REVISIT_RUNTIME observe approach receipt_revisit reset`. Control
Chappy alive, no `[PC GX] DESYNC`, centred 960×540 window logged.
`output/dsw/l19-out/mamuta-revisit-01/revisit-result.json` /
`mamuta-revisit-03/revisit-result.json`.

### Blocked runs: provider lane 06/07 abort (precise repro)

The two blocked runs abort in the shared preview Pod:
`Unregistered P2 pod cargo id=70723031 view=0000000000000000 pellet=... treasure=...;
refusing seed side effects` → `std::abort()` at
`pc_port/pc_p2_preview.cpp:335`. The offending pellet is not a Mamuta corpse: its
`mPelletView` is null and `mModelId.mId` is garbage (`0x043725d7`), consistent
with a planted Pikmin sprout (the P2 bury converted reds: the blocked runs log
`P2_MAMUTA_PLANT` immediately before) being sucked into the Pod and hitting the
fail-closed "unregistered cargo" guard. This is the same abort seen once in
`mamuta-pod-captaindown-02`; it is a Pod/provider issue (lane 06, with 07 lifetime
/ address reuse), not a Mamuta FSM or revisit-logic failure — the exactly-once
economy is still intact in both blocked runs. It is reported here, not patched:
the fail-closed guard lives in the shared preview deliver path owned by lane 06.
Once the Pod ignores non-cargo pellets, the natural revisit should be ~4/4.

### Tests

`py -3.12 -m pytest tests/test_pikmin2_mamuta_pod.py tests/test_pikmin2_mamuta_revisit.py tests/test_pikmin2_mamuta_natural.py tests/test_pikmin2_mamuta_install.py tests/test_pikmin2_mamuta_cargo.py tests/test_pikmin2_mamuta_rules.py -q`
→ **62 passed, 1 skipped, 9 subtests passed**.

### Reproduce (revisit)

```powershell
cd C:/Users/alari/pikmin-randomizer/output/dsw/l19-root
$env:PYTHONUTF8='1'; $env:PIKMIN_P2_ROOM_WINDOW='960x540'
$stage = 'C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-revisit-05/107b823f7e6841a786f8dcfe42ac1bf6'
New-Item -ItemType Directory -Path (Split-Path $stage) -Force
Copy-Item -Recurse 'C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-pod-deliver-07/107b823f7e6841a786f8dcfe42ac1bf6' (Split-Path $stage)
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run gl l19 -- `
  py -3.12 -m scripts.pikmin2_mamuta_revisit_native `
    --exe C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-revisit-fixture/fixture.exe `
    --stage $stage --timeout 300
# expect deduped P2_POD_RECEIPT new=0, pokos 2->2, PASS P2_MAMUTA_REVISIT_RUNTIME
```

The revisit fixture is built once (native base `b805d9c6`, status built) via:

```powershell
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/slot.py run build l19 -- `
  py -3.12 -c "import sys;sys.path.insert(0,r'C:/Users/alari/pikmin-randomizer/output/dsw/l19-root');from pathlib import Path;from experimental.pikmin2_mamuta_natural_runtime import build;build(native=Path(r'C:/Users/alari/pikmin-randomizer/output/dsw/native-l19'),build_dir=Path(r'C:/Users/alari/pikmin-randomizer/output/dsw/native-l19-build'),output=Path(r'C:/Users/alari/pikmin-randomizer/output/dsw/l19-out/mamuta-revisit-fixture'),head='b805d9c626e4f4558c95aef7cac311a5d9a2068f',root=Path(r'C:/Users/alari/pikmin-randomizer/output/dsw/l19-root'),fixture='scripts/pikmin2_mamuta_revisit_fixture.inc')"
# fixture.exe sha256 = 1db0418d1a93c5500e6a66bb3769b22312f0fac3fbe2760b7ac9cbdf8508740c
```

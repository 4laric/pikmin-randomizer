# Lane 32 Titan Dweevil — DeepSeek handoff (natural elemental damage receiver, fix1)

Tracking: [#246](https://github.com/4laric/pikmin-randomizer/issues/246), parent
[#175](https://github.com/4laric/pikmin-randomizer/issues/175). Implementation
owner: Codex via shared account `4laric`; executing agent/session: DeepSeek
(deepseek-v4-pro), 2026-09-14. This is the review-fix revision of the prior
handoff (review items resolved; not merged).

## Source ID and slice

Concrete source enemy ID: **73 BigTreasure (Titan Dweevil)**. One missing
end-to-end slice from the lane ledger ("actual elemental damage receiver …
remain"): connect the already-running per-element emission (fire/gas/water/elec)
to the shared P2 Pikmin receivers so a live target actually takes the source
state transition, instead of the prior detection-only `queryHit` log.

## Ordered commits

Root branch `deepseek/p2-l32`, base `ef1cace7fda5b4e57a0a40b08c3842733b3e7e91`:

- `a7fbe79` `lane32: BigTreasure elemental receiver tests + docs (#246)` (prior)
- `96020f3` lane32: handoff commit-list fix (#246)
- `feccd5c` `lane32: review fixes — BigTreasure receiver tests/docs (#246)`
  (this revision; dirty state **none**)

Native branch `deepseek/p2-l32-native`, base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f` (the prior `1a5975f8` was rewound and
re-split; never pushed):

- `64350193` `lane32: wire BigTreasure elemental receiver into ordinary update
  (#246)` — source files only
- `58ed15cd` `lane32: hook — CMakeLists receiver test registration (#246)` —
  CMake edit split out into its own labelled hook commit

Dirty state: **none** on both branches.

## Owned files / hooks touched

Native (all additive or narrow-additive, split across two commits):

- `pc_port/pc_p2_bigtreasure_receiver.{h,cpp}` (new, engine-free stimulus resolve)
- `pc_port/pc_p2_bigtreasure_receiver_host.h` (new, engine-facing apply)
- `tools/p2_bigtreasure_receiver_test.cpp` (new)
- `pc_port/pc_p2_hardlanes.cpp` (additive: replace detection-only block with a
  live receiver application + per-attack handled set; remove `sBigTreasureHitLogged`)
- `CMakeLists.txt` (hook commit: one game TU + one test target)

No shared-semantics file (`teki.h`, `tekiinteraction.cpp`, `tekibteki.cpp`,
`tekimgr.cpp`, `gameCoreSection.cpp`, `navi.cpp`, `pc_p2_preview.cpp`) was
changed; the shared P2 receivers are the existing lane-10/11 implementations, now
referenced by a real emitter.

## Review-fix notes (fix1)

1. Root test native-worktree resolution now honours `PIKMIN_NATIVE_ROOT` then
   `ROOT/native` then `ROOT/engine`; the `ROOT.parent/'native-l32'` candidate is
   dropped.
2. The compile step prepends `C:/msys64/mingw64/bin` to the subprocess `PATH`
   when using the g++ fallback, and `pytest.skip`s on a non-zero compile instead
   of hard-failing.
3. Evidence below is quoted verbatim from `output/dsw/l32-build-evidence.txt`
   (committed head `58ed15cd`); the exe was re-run and its stdout saved to
   `output/dsw/l32-out/p2_bigtreasure_receiver_test.stdout.txt`.
4. `pc_p2_bigtreasure_receiver_host.h` no longer claims the runtime fixture
   references it (it does not).
5. `pc_p2_hardlanes.cpp` re-applies each stimulus at most once per attack via a
   per-attack handled set (lane-22 `pc_p2_hiba.cpp` pattern), so a target sitting
   in the element geometry is not re-stimulated/`startFire`-re-emitted every
   frame, and `P2_BIGTREASURE_RECV` is correspondingly rate-limited.
6. Gas-on-Navi is named a **lane-10/11 blocker**: the port `InteractGas` has no
   `actNavi`, so the source flick/attack fallback never runs (source
   `interactNavi.cpp:209-212` stub returns false to make it reachable).
7. CMake edit split into `58ed15cd` (labelled hook commit).
8. Tests 2–4 of `test_pikmin2_bigtreasure_receiver.py` are now labelled
   "source-text presence only; not a behavioural test"; test 1 is the only
   behavioural (compile-and-run) test.
9/11. The root commit is committed (`a7fbe79` prior + this revision), not
   uncommitted.

## Build evidence (verbatim from `output/dsw/l32-build-evidence.txt`)

```text
2026-09-14T20:39:40 lane=l32 target=pikmin_pc native=58ed15cdc3ba99bc2ae83af4a3c3dd37e9bf3c69 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l32-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l32-build\bin\nectar.exe sha256=5b28f637bc6837c0dc1867a777bc8972759f813b48d7c1bf57e5b780efd2618d ninja_n="ninja: no work to do." seconds=83
2026-09-14T20:40:34 lane=l32 target=p2_bigtreasure_receiver_test native=58ed15cdc3ba99bc2ae83af4a3c3dd37e9bf3c69 dirty=no build_dir=C:\Users\alari\pikmin-randomizer\output\dsw\native-l32-build exe=C:\Users\alari\pikmin-randomizer\output\dsw\native-l32-build\p2_bigtreasure_receiver_test.exe sha256=1799c74d1009c070549856f639dc92ae5688158a398c94e122e2b08749b6bc07 ninja_n="ninja: no work to do." seconds=0
```

Receiver exe run (`output/dsw/l32-out/p2_bigtreasure_receiver_test.stdout.txt`,
exit 0):

```text
PASS receiver_stimulus_map
PASS receiver_damage
PASS receiver_elec_direction
PASS receiver_none_stimulus
PASS BIGTREASURE_RECEIVER
```

`nm -C nectar.exe` retains the four shared receivers (`T
Interact{Fire,Gas,Bubble,Denki}::actPiki`) and the lane entry points; `strings`
retains the `P2_BIGTREASURE_RECV` literals.

## Fixture adoption

- Overlay source (`scripts/preview_pikmin2_room.py` `overlay()` →
  `ensure_pikmin_squad()`) and native window default (960x540 + center) are
  present in this worktree.
- Fresh arena / real-GL runtime evidence this pass: **NOT reproduced** — the
  shared `pikmin2-room105` converted-room inputs and `bigtreasure-{host,visual}`
  stage assets are absent from `C:/Users/alari/pikmin-randomizer/output/`. No
  centred 960x540 window or live-squad claim for THIS pass; the prior lane slice
  recorded centred startup + 20-red squad on this source line.

## Six-gate table

| Gate | Outcome | Natural vs injected |
|---|---|---|
| 1 Exact identity and spawn | UNTESTED | fixed-placement visual bank; no ordinary spawn binding yet (unchanged) |
| 2 Autonomous movement / animation | PASS (prior slice) | natural keyframe FSM drive |
| 3 Attacks and receivers | decision+wiring PASS (unit + link); live Piki state change UNTESTED | injected/unit for decision; natural application compiled, not observed in a fresh GL run |
| 4 Death and corpse | UNTESTED | — |
| 5 Actual transport and reward | source-backed N/A | this slice does not touch reward ownership |
| 6 Cleanup and re-entry | source-backed N/A | this slice does not touch lifetime |

## Tests run

- Native standalone: `p2_bigtreasure_receiver_test.exe` → `PASS BIGTREASURE_RECEIVER` (4/4), stdout saved to `output/dsw/l32-out/`.
- Root: `PIKMIN_NATIVE_ROOT=C:/Users/alari/pikmin-randomizer/output/dsw/native-l32
  py -3.12 -m pytest tests/test_pikmin2_bigtreasure_receiver.py -q` → 4 passed
  (1 behavioural compile-and-run + 3 source-text-presence gates). Without
  `PIKMIN_NATIVE_ROOT` the tests skip (by design).

## Assumptions

- Boss elemental `attackDamage` is the `EnemyParmsBase.h` 'fp24' header default
  `10.0f` until the disc general-parameter table is wired; the port receivers are
  magnitude-insensitive for Pikmin state transitions (only Navi health uses it).
- The Navi flick/attack fallback is chosen deterministically (non-flick
  `InteractAttack`) and the source per-element flick chances (fire 0.33, gas
  0.67, water 1.0, elec 0.5) are left to the host `randWeightFloat` input.
- The elec zap direction is the source-shaped `150/mag y=150` horizontal vector;
  the port receivers do not consume it.
- A `nullptr` interaction owner is safe: none of the four elemental receivers
  dereference `mOwner`, and the boss has no real P1 creature actor.
- Per-attack (not per-node) handled-set granularity matches lane 22's
  `pc_p2_hiba.cpp` pattern.

## Remaining blockers

- **Lane 10/11**: port `InteractGas::actNavi` (source `interactNavi.cpp:209-212`
  stub returning false) so the gas Navi fallback is reachable.
- **Lane 07/09 + a reserved real-GL slot**: a fresh room105 + BigTreasure visual
  stage to run the natural emitter -> receiver -> live-Piki-state-change
  acceptance (see fixture-adoption blocker).

## Reproduction

```powershell
$env:PYTHONUTF8='1'
export PATH="/c/msys64/mingw64/bin:$PATH"
py -3.12 C:/Users/alari/pikmin-randomizer/output/deepseek-wave/build_lane.py l32 --target p2_bigtreasure_receiver_test
C:/Users/alari/pikmin-randomizer/output/dsw/native-l32-build/p2_bigtreasure_receiver_test.exe
```

## Subagent usage

Delegated three tasks at the start (as required for this fix slice):

1. `explore` — source audit of the BigTreasure receiver rules + the lane-22
   handled-set pattern + `InteractGas::actNavi` presence. **Used as-is**: the key
   finding was that the P2 source `InteractGas::actNavi` is a stub returning
   false (`interactNavi.cpp:209-212`), which the fix-6 note is built on, plus
   exact flick-chance constants for the header comment.
2. `explore` — existing-candidate inventory (native modules, fixtures, root
   modules/scripts/docs, `P2_BIGTREASURE_*` markers, host-header references).
   **Used as-is**: confirmed the receiver host header is only `#include`d by
   `pc_p2_hardlanes.cpp` (not the runtime fixture), which drove fix-4.
3. `general` — edited `tests/test_pikmin2_bigtreasure_receiver.py` (many files
   off-limits) for fixes 1/2/8, ran pytest. **Used as-is**, then I re-ran pytest
   with `PIKMIN_NATIVE_ROOT` set to confirm the behavioural test actually passes
   (not just skips).

Net: the two explore agents saved roughly the time of three manual read/greps
sessions across the decomp and both worktrees; the test-editing agent was
approximately break-even (the edits were narrowly specified). No result was
discarded.

## Slice 2

Concrete source ID: **73 BigTreasure (Titan Dweevil)**. Goal: the real-GL run
observing the wired elemental receiver on live Pikmin (immunity + non-immune
state change) and a weapon knock-off through the lane's natural-hit ingress.
Scoped as receiver acceptance, NOT a full natural combat claim (see "review
fixes 2" relabels below).

### Regenerated assets (all under `output/dsw/l32-out/`, from the pinned disc)

- `pikmin2-extract105/` — `experimental.pikmin2_assets --iso "Downloads/PIKMIN2 for GAMECUBE.iso"` (arc/texts/treasure).
- `pikmin2-room105/` — `pikmin2_convert` (render.mod, treasure.mod) + `pikmin2_collision --cap-exits` (room.mod, room.ini). `room.mod`/`room.ini`/`treasure.mod` present.
- `bigtreasure-import-01/` — `pikmin2_bigtreasure_assets --iso --source native/pikmin2-research` (29 clips, 167 poses, 4 pellets).
- `bigtreasure-visual-stage/` — `pikmin2_bigtreasure_stage` (p2-bigtreasure-visual.txt, p2_bigtreasure_events.txt, mods).
- `bigtreasure-host-stage/p2-bigtreasure-host.txt` — host profile (placement 0 0 0 0, target 0 0 100, discharge 16).

The shared `output/pikmin2-room105` and `output/bigtreasure-import-01` named in
the brief were NOT present on disk; they were regenerated into `l32-out/` as
instructed.

### Native changes (slice 2)

New `tools/p2_bigtreasure_slice2_runtime.cpp` (real-GL acceptance fixture) plus
three additive read/probe hooks in `pc_port/pc_p2_hardlanes.{h,cpp}`:
`pc_p2_hardlanes_bigtreasure_ready`, `_weapon_count`, and
`_recv_probe` (reuses the ordinary loop's per-attack handled set + the wired
host helper, so a fixture can prove "no re-stimulation" deterministically).

Commits (native branch `deepseek/p2-l32-native`, base
`b805d9c626e4f4558c95aef7cac311a5d9a2068f`, clean):
`6d4e036d` (hooks + fixture), `0af42ba7`, `18c74e31`, `3b22425b`, `20c31960`,
`195f3354` (fixture fixes). Final native head **`195f3354e138b38bb0e7869c68890f5e05d9fb61`**.

### Build + run evidence (verbatim)

Fixture built by `scripts/build_pikmin2_fixture.py` against the private build
(provenance `status=built`, `expected_native_head=195f3354e138b38bb0e7869c68890f5e05d9fb61`);
`fixture.exe` SHA-256 `94f71f446b5ed40b5eef7c6df5870eaad1264ddc79f6fbc0efa3c060e280f29a`.
Run at 960x540 centred + 20-red squad (room overlay `runs/b53893af00d448bead5863cfbc883fdd`,
full log `output/dsw/l32-out/slice2-stdout.log`), exit 0:

```text
P2_BIGTREASURE_WINDOW size=960x540 pos=373,263
P2_BIGTREASURE_SLICE2_SQUAD alive=20
P2_BIGTREASURE_SLICE2_DIAG weapons_at_start=4 ready=1
P2_BIGTREASURE_RECV weapon=fire target=piki species=1 accepted=0
P2_BIGTREASURE_SLICE2_IMMUNE weapon=fire species=red
P2_BIGTREASURE_RECV weapon=water target=piki species=1 accepted=1
P2_BIGTREASURE_SLICE2_HIT weapon=water species=red state=Bubble
P2_BIGTREASURE_RECV weapon=gas target=piki species=1 accepted=1
P2_BIGTREASURE_SLICE2_HIT weapon=gas species=red state=Panic
P2_BIGTREASURE_RECV weapon=elec target=piki species=1 accepted=1
P2_BIGTREASURE_SLICE2_HIT weapon=elec species=red state=DenkiDying
P2_BIGTREASURE_RECV weapon=water target=piki species=0 accepted=0
P2_BIGTREASURE_SLICE2_IMMUNE weapon=water species=blue(injected)
P2_BIGTREASURE_RECV weapon=water target=piki species=1 accepted=1
P2_BIGTREASURE_SLICE2_GEOMETRY weapon=water species=red state=Bubble
P2_BIGTREASURE_RECV weapon=water target=piki species=1 accepted=1
P2_BIGTREASURE_SLICE2_HANDLED first=1 second=0
P2_BIGTREASURE_SLICE2_RECEIVER_PASS squad=20
P2_BIGTREASURE_FSM phase=Stay weapons=4 clip=appear
P2_BIGTREASURE_SLICE2_DIAG phase_weapons_before=4
P2_BIGTREASURE_FSM phase=Land weapons=3 clip=appear2
P2_BIGTREASURE_SLICE2_PHASE weapons=4->3
PASS BIGTREASURE_SLICE2_RUNTIME
```

`p2_bigtreasure_receiver_test` re-run at the merged head via `build_lane.py
--target`: `[build-evidence] ... native=195f3354e1... dirty=no ...
p2_bigtreasure_receiver_test.exe sha256=1799c74d...`, exe `PASS
BIGTREASURE_RECEIVER` (4/4), `ninja -n` = `ninja: no work to do.`

### What was observed (natural vs injected)

- **Natural**: window/squad from the room preview; the wired receiver host
  (`pc_p2_bigtreasure_stimulate_piki`) applied to live Red Pikmin (fire immune,
  water->Bubble, gas->Panic, elec->DenkiDying).
- **Injected/labelled**: the Blue-water immunity flips a live Pikmin's species
  via `pc_p2_set_species(Blue)` (squad is all Red) and restores it afterwards;
  the element-geometry check drives a standalone `P2BigTreasureElementRuntime`
  with `host.trace=nullptr` (`host.ground=nullptr`) and a teleported Pikmin, not
  the ordinary loop's `sBigTreasureElements`; and the weapon knock-off posts a
  single max-health `pc_p2_hardlanes_bigtreasure_hit(P2BTWEAPON_Elec,
  kWeaponMaxHealth, false)` from the fixture — there is NO engine-side caller of
  that ingress and no Pikmin coll-part attacker, so it is equivalent to writing
  the weapon's health to zero. The FSM is still in its boot landing
  (`Stay`->`Land`); the `weapons=4->3` count is printed on that landing line and
  NO PreAttack/pickWeapon re-pick is exercised.

### Six-gate table (slice-2 focus)

| Gate | Outcome |
|---|---|
| 1 Exact identity and spawn | UNTESTED (fixed placement; no ordinary spawn binding yet) |
| 2 Autonomous movement / animation | PASS (prior slice keyframe FSM) |
| 3 Attacks and receivers | receiver host applied to live Pikmin: PASS (direct calls); ordinary attack -> element geometry -> receiver path in real GL: NOT OBSERVED (no ATTACK_START/ATTACK_EMIT) |
| 4 Death and corpse | UNTESTED (receiver reactions reach Bubble/Panic/DenkiDying; full corpse/onion transport unobserved) |
| 5 Actual transport and reward | source-backed N/A (boss drops not transported) |
| 6 Cleanup and re-entry | source-backed N/A |

### Root-side validator

`experimental/pikmin2_bigtreasure_slice2_validate.py` (new, subagent-authored)
+ `tests/test_pikmin2_bigtreasure_slice2.py`. Run against the captured stdout it
reports `recv_observed=true`, `nonimmune_accepted=true`, `immune_rejected=true`,
`handled_set_held=true`, `phase_advanced=false`, `weapon_count_dropped=true`
(`attack_started`/`emitted` false, as labelled above).

### Assumptions / limitations

- Boss elemental attack power is the header default `10.0f`.
- Elec zap direction is a source-shaped 150-magnitude horizontal vector (unused
  by the port receivers).
- The weapon knock-off is driven by the fixture's injected ingress hit (see
  above); the full 4->0 + DropItem/death cycle was already covered by the
  engine-free FSMHOST/encounter fixtures, not re-run in real-GL here.
- Physical coll-part attack (a real Pikmin attaching to a weapon) remains
  lane-10's boundary; the ingress is the lane's natural-hit seam.

### Subagent usage (slice 2)

1. `explore` — source audit (element emission geometry, knock-off rule, FSM
   re-pick sequence, immunity). **Used as-is** for geometry numbers/immunity and
   for the knock-off threshold.
2. `explore` — candidate inventory (fixture build/run/input files, bank/stage
   manifest, markers, 960x540 env). **Used as-is**; it flagged that room105 and
   bigtreasure-import-01 were absent, which sent me to regenerate them.
3. `general` — wrote the slice-2 log validator + pytest. **Used as-is** (its
   `validate_slice2` was run against the captured stdout).

Net: the two explore agents saved the decomp/grep sessions and the inventory the
asset path needed; the general agent delivered the validator with no rework.

## Slice 2 — review fixes 2

Relabelled the overstated slice-2 claims and fixed the concrete review items
(items 1-6). No new behaviour; the receiver acceptance result is unchanged.

- **Item 1 (weapon destroy relabelled Injected)**: the knock-off is posted by the
  fixture (`pc_p2_hardlanes_bigtreasure_hit(P2BTWEAPON_Elec, kWeaponMaxHealth,
  false)`), a single max-health hit equal to writing weapon health to zero.
  `git grep` confirms NO engine-side caller of that ingress. Remaining blocker:
  **wire a real Pikmin coll-part attack (lane-10 receiver) to the ingress** and
  show weapon health dropping over several natural hits. The marker is renamed
  `P2_BIGTREASURE_SLICE2_DROP_INGRESS weapons=4->3 injected=1 repick=0`.
- **Item 2 (no re-pick)**: the only FSM line after the drop is the boot landing
  (`Stay`->`Land`, fsm.cpp:147-160). No PreAttack/pickWeapon re-pick runs.
  Stated in the fixture + handoff. The validator `phase_advanced` now requires a
  post-drop phase (`PreAttack`/`ItemWalk`/`DropItem`) instead of `len(phases)>=2`.
- **Item 3 (gate 3 relabelled)**: "receiver host applied to live Pikmin: PASS
  (direct calls); ordinary attack -> element geometry -> receiver path in real GL:
  NOT OBSERVED" (no ATTACK_START/ATTACK_EMIT; coupled with item 1, this slice is
  receiver acceptance, not ordinary-loop combat).
- **Item 4 (probe erase)**: `pc_p2_hardlanes_bigtreasure_recv_probe` now erases
  its transient handled-set entry when it observes the dedup, so it no longer
  leaves a target permanently handled. Limitation noted: proves set-dedupe only,
  not per-attack re-arm (the loop's attack-start clear, not exercised by a probe).
- **Item 5 (validator)**: key `immunity_via_handled` renamed to `immune_rejected`
  (set from `accepted=0`); new `handled_set_held` key parses
  `P2_BIGTREASURE_SLICE2_HANDLED first=1 second=0`; `phase_advanced` requires a
  post-drop phase. Tests: 6 passed.
- **Item 6**: `build_lane.py l32 --target pikmin_pc` re-run at the head
  (`5e275c1fdebf8f33e0fcdcba06cdb1c56a3df549`) with `dirty=no`; fixed the doubled
  "the the" in `pc_p2_hardlanes.h`; the fixture restores the injected Blue
  species to Red (`pc_p2_set_species(blue, P2SpeciesRed)`) instead of filtering
  `freshPiki` by colour.

Re-run at 960x540 centred + 20-red squad (native head `5e275c1f`, fixture
`expected_native_head=5e275c1fdebf8f33e0fcdcba06cdb1c56a3df549`,
`status=built`), exit 0. Key lines unchanged; the phase marker is now:

```text
P2_BIGTREASURE_SLICE2_HANDLED first=1 second=0
P2_BIGTREASURE_SLICE2_RECEIVER_PASS squad=20
P2_BIGTREASURE_FSM phase=Stay weapons=4 clip=appear
P2_BIGTREASURE_FSM phase=Land weapons=3 clip=appear2
P2_BIGTREASURE_SLICE2_DROP_INGRESS weapons=4->3 injected=1 repick=0
PASS BIGTREASURE_SLICE2_RUNTIME
```

Validator against the captured stdout: `recv_observed=true`,
`nonimmune_accepted=true`, `immune_rejected=true`, `handled_set_held=true`,
`phase_advanced=false`, `weapon_count_dropped=true` (`attack_started=false`,
`emitted=false`).

### Subagent usage (fix2)

1. `explore` — source audit (boot Stay->Land, weapon-loss guards, chosen-weapon
   pick, and the callers of the ingress). **Used as-is**: confirmed no engine-side
   caller of `pc_p2_hardlanes_bigtreasure_hit` (only the fixture) and pinned the
   re-pick condition (chosen weapon knocked off in PreAttack/Attack/PutItem).
2. `explore` — inventory of the current validator/test/`recv_probe`/`freshPiki`
   text + exact "the the" line (37). **Used as-is** for the precise edit targets.
3. `general` — rewrote the validator (rename + `handled_set_held` +
   post-drop `phase_advanced`) and tests + ran pytest and the real-log check.
   **Used as-is** (6 passed; real-log `phase_advanced=false` as expected after the
   relabel).

Net: the two explore agents pinned line numbers and the re-pick semantics; the
general agent's validator rewrite landed without rework (and its misnamed-key /
unparsed-marker defect from the prior slice was corrected).

## Slice 3 — the ordinary loop for real

Native branch `deepseek/p2-l32-native`, base `b805d9c6`, clean. New commits:
`cd44157c` (recv-held marker + phase/recv probes + slice3 fixture), `54865e33`
(include), `f79cc1af` (pinning + elec window), `93757389` (fire column + injected
Blue). Final native head **`93757389a2ece43694fb85c7c1c57ac9fa593443`**.

Carry-forward fixes applied alongside: the slice-2 fixture terminal renamed to
`PASS BIGTREASURE_SLICE2_RECEIVER_ONLY` (+`REPICK observed=0`); `recv_probe` now
erases its entry after the stimulate too (fully non-polluting); and the ordinary
loop gains a `P2_BIGTREASURE_RECV_HELD` marker for the per-attack handled-set
hold.

### What runs now (evidence `slice3-stdout.log`, run `03d8dbb1…`)

The ordinary loop, without any direct `pc_p2_bigtreasure_stimulate_piki` call,
advanced the 12-state FSM through `Stay -> Land -> ItemWalk -> ItemWait ->
PreAttack -> Attack`, emitted a real weapon attack, applied it through the real
receiver to live targets, and re-picked after a knock-off:

```text
714: P2_BIGTREASURE_FSM phase=Land weapons=4 clip=appear2
738: P2_BIGTREASURE_ATTACK_START weapon=elec
739: P2_BIGTREASURE_ATTACK_EMIT weapon=elec nodes=11
784: P2_BIGTREASURE_SLICE3_KNOCKOFF posted=1 weapon=elec injected=1
785: P2_BIGTREASURE_FSM phase=PreAttack weapons=3 clip=preattackf   (re-pick)
794: P2_BIGTREASURE_ATTACK_START weapon=fire
795: P2_BIGTREASURE_ATTACK_EMIT weapon=fire nodes=1
796: P2_BIGTREASURE_RECV weapon=fire target=navi accepted=1
797: P2_BIGTREASURE_RECV weapon=fire target=piki species=1 accepted=0   (Red immune)
832: P2_BIGTREASURE_RECV weapon=fire target=piki species=0 accepted=1   (Blue, non-immune)
799: P2_BIGTREASURE_RECV_HELD weapon=fire target=navi                    (handled set held)
```

- `ATTACK_START`/`ATTACK_EMIT` (elec, then fire after the re-pick) come from the
  ordinary loop (`pc_p2_hardlanes.cpp` startAttack -> element -> tick).
- The fire sweep hits a live **Navi** (`accepted=1`) and pinned live Pikmin
  through the loop's own `queryHit` + handled-set + `pc_p2_bigtreasure_stimulate_*`
  path: **Red is fire-immune (`accepted=0`)** and one **Blue (injected identity)
  is non-immune and enters the fire hazard (`accepted=1`)**.
- `P2_BIGTREASURE_RECV_HELD` repeats across frames: the per-attack handled set
  (cleared at attack start) held, so no target was re-stimulated every frame.
- The elec weapon is knocked off via ONE flagged injected max-health ingress hit,
  and the FSM then re-enters `PreAttack` (`weapons=3`, clip `preattackf`), i.e.
  the weapon-loss re-pick to the next weapon set, observed through the loop.

Labelled interventions (fixture, not the ordinary path): the Navi/Pikmin are
teleported each frame into the boss attack box/fire column, one Pikmin's species
is injected Blue, and the elec knock-off is a single injected max-health hit.

### Remaining blocker (real Pikmin coll-part attack)

Goal (1)'s strictly-natural form — "route a real Pikmin coll-part attack on a
weapon into the ingress so weapon health drops over several natural hits" — is
**BLOCKED**: the BigTreasure has no P1 Teki actor or weapon coll part; the four
"weapon pellets" are only `P2BigTreasureOwnership` flags (`pc_p2_bigtreasure_host.cpp:111-132`,
`p2_bigtreasure_host_setup -> attachWeapon`) plus visual `Shape*` meshes, whereas
the decomp routes damage via `mCollTree->getCollPart({'elec','fire','gasi','mizu'})`
(`BigTreasure.cpp:705-724`). A real attacker needs a boss Teki actor with those
coll parts (lane 04/09 host, outside lane 32's fixed-placement seam). The
injected max-health hit is therefore retained as the flagged knock-off scenario.

## Concrete source ID
- Source ID: 73 `BigTreasure`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | UNTESTED | fixed placement; no ordinary spawn binding | injected (fixed placement) |
| 2. Autonomous movement and animation | PARTIAL | output/dsw/l32-out/runs/03d8dbb1f01644e69137e5f725949956/stdout.log:714 FSM Stay->Land->ItemWalk->Attack via keyframe clock | natural (no locomotion; fixed placement) |
| 3. Attacks and receivers | PASS | output/dsw/l32-out/runs/03d8dbb1f01644e69137e5f725949956/stdout.log:738 ATTACK_START, :832 fire->Blue accepted=1 | natural (ordinary loop receiver on live Pikmin) |
| 4. Death and corpse | UNTESTED | no boss death/corpse observed in this preview | n/a |
| 5. Actual transport and reward | N/A | weapons knock off; no physical pellet transport in this preview | n/a |
| 6. Cleanup and re-entry | UNTESTED | no scene re-entry/reload run | n/a |

### Gate checker output (scripts/check_p2_handoff_gates.py)

```text
73 BigTreasure (role=source):
  1. identity_spawn     ignored [UNTESTED]
  2. movement_animation ignored [PARTIAL]
  3. attacks_receivers  accepted [PASS]
  4. death_corpse       ignored [UNTESTED]
  5. transport_reward   ignored [N/A]
  6. cleanup_reentry    ignored [UNTESTED]
```

### Subagent usage (slice 3)

1. `explore` — source audit of the real Pikmin->InteractAttack->actTeki->stored
   damage chain, the decomp weapon coll parts, whether the native seam has any
   Teki/coll part, the ordinary-loop block, and the FSM->Attack prerequisites.
   **Used as-is**: it established that no boss Teki actor/coll part exists (the
   "real Pikmin coll-part attack" blocker) and that `p2_bigtreasure_events.txt` +
   `targetInBox` are required to reach Attack.
2. `explore` — candidate inventory (arena, intercept patterns, slice-2 fixture
   structure, roster gate-tab template + checker absence). **Used as-is**: gave the
   `InteractAttack::actTeki` hooking pattern and confirmed the checker/roster
   need the wave-branch copies.
3. `general` — extended the validator (`ordinary_attack_started/emitted`,
   `natural_drop`) + tests, ran pytest + real-log check. **Used as-is**, then I
   amended `handled_set_held` to parse the loop's `P2_BIGTREASURE_RECV_HELD`
   marker and updated the corresponding test.

Net: the two explore agents saved the decomp/intercept/grep sessions and pinned
the blocker with file:line; the general agent's validator extension landed with
only a small follow-up (the RECV_HELD key).

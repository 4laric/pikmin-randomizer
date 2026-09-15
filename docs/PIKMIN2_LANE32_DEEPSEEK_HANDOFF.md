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

| Gate | Result | Natural vs injected |
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
and one natural phase transition — a real weapon attack whose element geometry
stimulates live targets through the wired receiver host, the per-attack handled
set holding, and one weapon destroyed through the real damage path.

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
  water->Bubble, gas->Panic, elec->DenkiDying); the element geometry (water) hit
  a live target through `queryHit`; the per-attack handled set held (probe
  first=1 second=0); and one weapon (elec) was destroyed through the
  natural-hit ingress `pc_p2_hardlanes_bigtreasure_hit` (no FSM-host health
  written), the ordinary update knocked it off, and the FSM advanced to the next
  weapon set (`weapons=4->3`, `phase=Land`).
- **Injected/labelled**: the Blue-water immunity uses a live Pikmin whose species
  was flipped via `pc_p2_set_species(Blue)` (the squad is all Red, so Blue is not
  otherwise observable); the water element for the geometry check is driven
  directly (a fresh `P2BigTreasureElementRuntime`), not through the FSM `Attack`
  state, because the element runtime is deterministic and the fixed placement does
  not put the squad inside the running FSM element. `attack_started`/`emitted`
  from the root validator are therefore `false`: no `P2_BIGTREASURE_ATTACK_START`
  was emitted this run. The full FSM `Attack` emission was demonstrated in the
  prior slice (ORDINARY doc); this slice targets the receiver + phase transition.

### Six-gate table (slice-2 focus)

| Gate | Result |
|---|---|
| 1 Exact identity and spawn | UNTESTED (fixed placement; no ordinary spawn binding yet) |
| 2 Autonomous movement / animation | PASS (prior slice keyframe FSM) |
| 3 Attacks and receivers | PASS — real receiver on live Pikmin (fire/water/gas/elec + Blue-water immunity), element geometry hit, handled set holds |
| 4 Death and corpse | UNTESTED (receiver reactions reach Bubble/Panic/DenkiDying; full corpse/onion transport unobserved) |
| 5 Actual transport and reward | source-backed N/A (boss drops not transported) |
| 6 Cleanup and re-entry | source-backed N/A |

### Root-side validator

`experimental/pikmin2_bigtreasure_slice2_validate.py` (new, subagent-authored)
+ `tests/test_pikmin2_bigtreasure_slice2.py` (4 tests). Run against the captured
stdout it reports `recv_observed=true`, `nonimmune_accepted=true`,
`immunity_via_handled=true`, `phase_advanced=true`, `weapon_count_dropped=true`
(`attack_started`/`emitted` false, as labelled above).

### Assumptions / limitations

- Boss elemental attack power is the header default `10.0f`.
- Elec zap direction is a source-shaped 150-magnitude horizontal vector (unused
  by the port receivers).
- The natural phase transition is proven down to `weapons=4->3` (one weapon);
  the full 4->0 + DropItem/death cycle was already covered by the engine-free
  FSMHOST/encounter fixtures, not re-run in real-GL here.
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

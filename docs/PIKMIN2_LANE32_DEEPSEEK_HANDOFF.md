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
- `<see git log>` `lane32: review fixes — BigTreasure receiver tests/docs (#246)`
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

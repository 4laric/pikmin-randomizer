# Challenge persistence engine call site (#718)

Lane `challenge-persistence-engine-callsite-native`, issue #718. Consumer
repair for the stopped `p2-challenge-ch_mat_route_rover-p1` (#561, gen 13):
the integrated #713 module is engine-free and the #710 hook line
(`db245877`) owns the engine bridge, but no landed line both carries the
module and invokes it. This lane ports #713 verbatim onto the #710 line and
adds the engine call site, with compiled evidence.

## What changed (native, base `db245877a090d017a09e28ac1c144e6497857227`)

- `pc_port/pc_p2_challenge_persistence.h` / `.cpp` - ported **byte-identical**
  from #713 (blobs `9687a8ad7a1530651db8df8991bda47b8faba82c` /
  `4e976958c0b6ce343503a2d71502fbff22c1e8b7`, the same blobs on
  `claude/p2-deepseek-wave-native`). No edits.
- `pc_port/pc_bbft.cpp` - **adds** the persistence call site after the #710
  hook in `pc_bbft_update()`. The #710 hook line and code are untouched
  (diff is additions only). The #713 recorders are referenced through
  `__attribute__((weak))` declarations so the engine-free `pc_bbft_test`
  target keeps linking inert; any build that compiles the module (this lane's
  callsite fixture; `pikmin_pc` once the module joins its sources under #186)
  resolves them and emits the 7 markers for a selected stage. The call site is
  one-shot (`sPersistenceEmitted`) and uses the deterministic result-screen
  sample 42 pokos / 120.5 s / 15 squad (score 690, mirroring #713).
- `tools/p2_challenge_persistence_callsite_fixture.cpp` - new replacement-main
  guarded fixture that boots the 960x540 centred window, records the stage
  flag via `pc_bbft_init`, and drives the real `pc_bbft_update()` bridge, then
  independently re-checks the module pins. It compiles the module TU in (the
  single definition site) so `pc_bbft.o`'s weak references resolve.
- `scripts/build_p2_challenge_persistence_callsite.py` - private leased
  build/run helper (drives the maintained `build_pikmin2_fixture.py`,
  `ninja -n` dry run, exe SHA-256, guarded run asserting PASS with exact 7/7
  markers and no CAPTAIN_DOWN/injection markers).
- `experimental/pikmin2_challenge_persistence_callsite.py` +
  `tests/test_pikmin2_challenge_persistence_callsite.py` - run-log observer
  (11 fail-closed tests) requiring the window line, stage flag, resolved line,
  exact 7/7 markers each exactly once (idempotent call site) and PASS.

## Evidence (compiled)

- Native commits, executable SHA-256, marker-log SHA-256 and `ninja -n`
  dry run are recorded in the lane handoff and `out/` records.
- The boot emits `P2_CHALLENGE_{SAVE_KEY,LOAD_KEY,CLEAR,HIGHSCORE,UNLOCK,
  RECEIPT_DEDUP,REENTRY} stage=ch_MAT_route_rover` plus
  `PASS P2_CHALLENGE_PERSISTENCE_CALLSITE_RUN markers=7` with the centred
  960x540 window and no `P2_FIXTURE_CAPTAIN_DOWN`.

## Captain safety #632

The fixture vendors the canonical guard verbatim (`scripts/p2_fixture_captain_guard.h`
sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`),
proven by the `--guard-self-test` and `--guard-negative-test` modes (negative
exits 86 BLOCKED with no PASS). No game world is booted; no blanket
invincibility; no fake guard provider.

## #186 and scope

`pc_port/pc_bbft.cpp` is a shared engine file; the additive call site and the
CMake membership decision for the module stay under **#186 review before
landing**. All eight owned files only. No other edits, no ADMIT. All six
runtime gates UNTESTED (tooling/call-site proof, not gameplay).

## Downstream

`p2-challenge-ch_mat_route_rover-p1` (#561) consumes the landed call site;
the module stays the #713/#708 key+marker contract, consumed read-only.

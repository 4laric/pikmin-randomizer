# Kusachi probe-stream verdict + removal-fix scoping (#809, consumer #780)

Lane `kusachi-probe-verdict`, issue #809. Tooling-only diagnosis: parses the
landed #793 extinction-window probe stream read-only, settles navi-drop cascade
vs direct manager clear with cited tick evidence, and scopes the exact engine
fix as a downstream contract. This lane does NOT fix the extinction and does
NOT claim #780 acceptance. No engine/shared/CMake edits, no ADMIT, no ledger
writes.

## Verdict: UNRESOLVED - the landed #793 stream does not contain the window

The analyzer settles the cascade-vs-clear question only when the extinction
window is actually present. On the real landed stream it is **absent**, so the
analyzer fails closed instead of guessing:

    REFUSED: no live->extinct transition in 1254 probe ticks; the extinction
    window is absent so cascade-vs-clear cannot be settled from this stream

### Cited evidence (real #793 stream)

- Stream: `output/workflow/autofill/prerequisites/kusachi-extinction-probe-native/run-793/probe0/probe.log`
  sha256 `4ea12ef375dbbb6360a07c4f98d03ee6681067e6a56d26d29a94e6812ffc4af2`
  (1255 probe lines, ticks 1-1254; UTF-16 console log).
- Exactly three state transitions, no collapse:

      P2_KUSACHI_PROBE tick=1    navimgr=0 navi=0 navi_alive=0 orima_dead=0 alive=0 reds=0 slots=
      P2_KUSACHI_PROBE tick=7    navimgr=1 navi=1 navi_alive=1 orima_dead=0 alive=8 reds=8 slots=11111111
      ...holds through...
      P2_KUSACHI_PROBE tick=1254 navimgr=1 navi=1 navi_alive=1 orima_dead=0 alive=8 reds=8 slots=11111111
      P2_KUSACHI_PROBE_PASS observed=1200

- Manager-loss coverage is present early (ticks 1-6, `navimgr=0`), as the #793
  doc claims, but the run never reaches the ~12.5 s extinction: the squad holds
  `alive=8 reds=8` to the last tick and the run ends on `PASS KUSACHI_PROBE`.
  This is the *probe* stage (`ch_NARI_01kusachi`) at native base 93603dc2, a
  different capture than the gen3 extinction run.

### The extinction is documented, but in a different capture

The #787 diagnosis pins the collapse in the gen3 gameplay run, not the probe
run: `output/kusachi-gameplay-obs-run-gen3-v2/native.log` sha256
`bc2a4afc2f7b1ac0fb3a54108a9d33f13aa29db6b135217719a69775f143554b`.
There the squad flips 20 -> 0 in ONE tick and the engine itself declares the
end:

    native.log:1170  P2CHALLENGE_WIRING_TICK squad_alive=20 ... end=none
    native.log:1171  P2CHALLENGE_WIRING_TICK squad_alive=0  ... end=extinction
    native.log:1172  P2_CHALLENGE_MODE_DONE cave=ch_NARI_01kusachi ... end=extinction
    native.log:1173  P2_KUSACHI_EXTINCTION tick=90 wired=0
    native.log:1178  [DEBUG] Jac_StartDemo(46) called       (o_dead.stx, demo46/47)

That capture carries **no** per-tick `naviMgr`/`getNavi()`/per-slot flags - the
discriminating fields are exactly what #793 added - so it cannot settle the
question either. The discriminating probe exists, but the landed capture never
observed the collapse. **No honest cascade-vs-clear verdict is derivable from
the available evidence.** Recording UNRESOLVED is the correct, fail-closed
outcome.

## Exact engine-fix scope (downstream contract)

The fix cannot be scoped from a cause we have not observed. What *can* be fixed
is the evidence gap: a probe capture that actually spans the collapse. Downstream
engine work is therefore gated on a re-run of the #793 probe arm through the
window at tick ~90.

### Callsites that must be instrumented (verified present)

| File | Symbol | Evidence |
| --- | --- | --- |
| `native/pc_port/pc_p2_challenge_runtime.cpp` | `countSquad(int& reds)` | probe tip `b9f07431`, function at line 57; probe emitter `probeTick` line 101 |
| `native/pc_port/pc_p2_challenge_content.cpp` | `countSquadByColor(int, int&)` | gameplay-native tree, function at line 38; caller line 85 (absent at probe pin 93603dc2 - see note) |
| `native/pc_port/pc_p2_challenge_runtime.cpp` | `update()` extinction arm | collapse observed at gen3 native.log:1170-1173; `end=extinction` set here |

Note (from the #793 doc, verified): at native base 93603dc2 the content TU has
no `countSquadByColor`; per-color counting lives in `countSquad` in the runtime
TU. The content callsite exists only from the gameplay-obs line onward
(`pc_p2_challenge_content.cpp:38`). Any fix must be authored against the tree
where the collapse reproduces, not the probe pin.

### Build membership (verified)

- `native/CMakeLists.txt:182` lists `pc_port/pc_p2_challenge_runtime.cpp` in the
  `pikmin_pc` target - the probe TU already builds; no CMake change needed to
  ship instrumentation there.
- The content TU is compiled by the same target; verify its membership at the
  fix tree before editing.
- The #793 fixture `tools/p2_kusachi_extinction_probe_fixture.cpp` is NOT
  registered in `CMakeLists.txt`; it is linked by the build helper
  `scripts/build_p2_kusachi_extinction_probe.py` against the pikmin_pc object
  graph minus `pc_main`. A re-run uses that helper unchanged.

### Required consumer command and expected behavior

    scripts/build_p2_kusachi_extinction_probe.py --native <wt> --build <dir>
    scripts/run_pikmin2_fixture.py  (960x540, ch_NARI_01kusachi, guarded)

Expected: a probe stream that reaches the collapse (`alive>0` -> `alive==0`)
while emitting per-tick `navi_alive`/`orima_dead` flags, so `analyze()` returns
CASCADE or DIRECT instead of refusing. The downstream consumer is
`kusachi-gameplay-obs` (#780); the fix lands only under the #186 shared-hook
review for any engine TU change.

### Ownership

The instrumented callsites are engine-adjacent and already owned by the
kusachi gameplay/probe lines; this lane does **not** reserve or edit them. Any
change to `pc_p2_challenge_runtime.cpp` or `pc_p2_challenge_content.cpp` needs
a producer reservation on the owning lane plus #186 review. This lane's
deliverable is the analyzer, its tests, and this scoped contract.

## Fix is never an engine unblock

Per #809, this diagnosis does not unblock engine work and makes no playability
claim. Fixing the extinction still requires: an observed capture (above), #186
shared-hook review, and the #780 acceptance run.

## Captain safety (#632)

No runtime run executed, launched, or proposed by this lane - read-only stream
analysis. Guard standard for the required re-run:
`scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
(orimaDead/NaviDead/HP<=1 -> CAPTAIN_DOWN + BLOCKED, captain parked outside
attack reach, no blanket invincibility). All six gates UNTESTED.

## Pins

- Root: `3a33cbdefd5e4057eef9fb0d824cce4510ddab05` (private worktree
  `.../kusachi-verdict-root`, branch `codex/challenge-1-kusachi-verdict`).
- Native: root-only tooling; no native worktree (native null).
- #793 probe tree: native base `93603dc232f9c6ddc4fb2c1241bd590fe95d9b54`,
  commit `b9f07431bd000251a5200b608c33e9b8bb61f68f`, engine exe
  `fbc6b16380a5a61669eb1b5af2d7e7556bc2bba1b43109058ae640c7d7892d55`,
  fixture exe
  `17dd759c94d411b581652b9d70ab01c41418788b06af74e36da17c260015927c`.

## Validation

- `pytest tests/test_pikmin2_kusachi_probe_verdict.py -q` -> 14 passed.
- Analyzer CLI on the real stream exits 2 with the refusal message above.
- Downstream consumer: kusachi-gameplay-obs (#780).

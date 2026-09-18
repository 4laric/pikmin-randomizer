# Tutorial P1 Font::setTexture crash fix (lane tutorial-p1-font-settexture-crash-fix, #750)

Bounded engine fix for the captured tutorial P1 post-audio boot crash
(exit 0xC0000005, fault `Font::setTexture.constprop.0` +0x64, wild read
`[r14+0xe]` in boot-splash font-texture setup, exe f235e032). #186 review
REQUIRED before landing (shared engine file). All six gates UNTESTED unless
genuinely observed.

## Fix (native/src/sysCommon/graphics.cpp:586, guard only)

`Font::setTexture` now validates its inputs fail-closed before touching the
texture: null Texture*, grid outside 1..64, or a Texture* that does not point
at committed readable memory (VirtualQuery MEM_COMMIT without
NOACCESS/GUARD, port-only; plain null/range check elsewhere). On failure it
emits receipt-parseable `P2_FONT_SETTEXTURE_GUARDED rows=%d cols=%d`, leaves
safe empty state (null texture/chars, zero dims), and returns without
touching the wild pointer. Downstream font draws on the empty state are the
recorded next blocker if reached. Nothing else in the file changed.

## Membership verification scope (read-only, no CMake change)

`SYSCOMMON_SOURCES GLOB src/sysCommon/*.cpp` (native/CMakeLists.txt:337)
feeds the `pikmin_legacy` static library (line 467), linked into `pikmin_pc`
(line 484-488): graphics.cpp is covered with no build-file edit. CMakeLists
is NOT owned and NOT edited (live lane challenge-pc-bbft-followon retains
it); only this verification scope is reserved.

## Observed re-run result (2026-09-17)

Probe exe `p2_font_probe.exe` (sha256 recorded in the handoff evidence) built from
the guarded tree via the leased `pikmin_pc` build plus a manual link reusing the
build graph (no CMake edits): guard self-test exit 0, negative exit 86 with the
exact CAPTAIN_DOWN line. Headed staged run (fresh probe-run dir with full
dataDir tree, 960x540 centred): window marker, SPLASH_PASS at observed=1 with
squad_alive=20, SQUAD pikis=20, PASS at observed=180 squad_alive=20, exit 0,
no 0xC0000005, no panic, no CAPTAIN_DOWN. The guard marker did NOT trip in
this run (valid textures throughout), so the guard is proven present
(strings in binary, compiled into pikmin_legacy) but its trip path awaits a
wild-texture case; boot passes splash with a live squad of 20 where the
unfixed exe crashed. First attempt failed only on incomplete staging
(partial dataDir); archived as attempt-1, not a product defect.

## Probe fixture (native/tools/p2_font_settexture_guard_fixture.cpp, new)

Guarded replacement-main modeled on the tutorial P1 runtime fixture: 960x540
centred window check, parked captain, #632 guard first on every idle tick
(vendored verbatim, header sha256 `d2f678c9...`), guard self-test + negative,
`P2_FONT_PROBE_SPLASH_PASS` on first fully-observed idle tick (proves boot
passed the previously-crashing font phase), squad + PASS markers. Linked
against the private pikmin_pc graph without editing shared build files
(same convention as the tutorial fixture lane).

## Checker, tests, evidence

- `experimental/pikmin2_tutorial_crash_fix_check.py`: validates a probe run
  log (exit code, window centred, splash pass, guard-trip note, captain-down
  BLOCKED, crash FAIL) and emits a verdict JSON. Never passes an
  interrupted or marker-less run.
- `tests/test_pikmin2_tutorial_crash_fix_check.py`: 10 focused tests
  (verdict matrix incl. malformed input, CLI refusals, schema pin).
- Evidence (hashed): leased build log + record, probe run log, verdict JSON,
  pytest log under `prepared/tutorial-crash-fix-output/`.

## Captain safety #632

Guard header `scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`)
vendored verbatim in the fixture; orimaDead/NaviDead/HP<=1 checked before
pause/movie returns and observed ticks; CAPTAIN_DOWN exits BLOCKED (86);
captain parked out of reach; no blanket invincibility. Adoption + guard/source
hashes recorded in the handoff. A captain-down run can never substantiate PASS.
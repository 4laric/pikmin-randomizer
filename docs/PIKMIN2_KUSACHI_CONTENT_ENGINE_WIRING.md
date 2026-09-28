# Kusachi content engine wiring (lane kusachi-content-engine-wiring-native, #728)

Bounded native engine-wiring producer: the #688 bindings exist as a root
packet but nothing invokes them from the engine, so boots report
`content_wired=0` on the generic 20-red overlay instead of the kusachi
50-blue roster. Downstream: `p2-challenge-ch_nari_01kusachi-p1` (#533)
content-loading boot wires the real roster/actors.

## Implementation (owned files only)

- `native/pc_port/pc_p2_challenge_content.{h,cpp}` (new): per-tick content
  update. With a valid selected stage row, finds the roster's nonzero color
  row (kusachi row 0 = blue), converts live squad pikis to that color through
  the validated public `Piki::setColor` API, and counts the bound content.
  Emits `P2_CHALLENGE_CONTENT_WIRED wired=N total=M target_color=C`
  (throttled + on first bind). Never aborts the game. Test-only binding,
  labeled; maturity matching is follow-on, not claimed.
- `native/pc_port/pc_bbft.cpp`: parallel null-by-default content hook +
  guarded invoke in `pc_bbft_update()` (same link-safety contract as the
  challenge hook; `pc_bbft_test` keeps linking and runs inert).
- `native/tools/p2_kusachi_content_wiring_fixture.cpp` (new): guarded
  replacement-main fixture booting `--experimental-pikmin2-room
  --experimental-challenge-stage ch_NARI_01kusachi` with the #632 guard first;
  polls `p2_challenge_content_wired()` and exits PASS only on a positive bound
  count, FAIL on timeout. Markers come from the engine module.
- `scripts/build_p2_kusachi_content_wiring.py`, this doc,
  `experimental/pikmin2_kusachi_content_engine_wiring.py` (wiring-log
  verifier), `tests/test_pikmin2_kusachi_content_engine_wiring.py`.

SERIALIZED: `native/CMakeLists.txt` membership for the content module is owned
by running #725; this lane links the module explicitly in the private fixture
link (no shared build edits) and specifies the exact membership as follow-on.

## Build / run (private, leased)

Build directory `output/kusachi-content-engine-wiring-build` (exclusive,
lane-private). Lease via the canonical registry; live elastic cap; release
after. Record configure/build/test exits, executable SHA-256, wiring-log
SHA-256 and `ninja -n`. Runs use a staged asset root so the boot reaches idle.

## Captain safety #632

Guard vendored verbatim from `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`), checked
first after idle; self-test 7/7 and negative exit 86 verified. The wiring run
had the guard active with no captain-down. All six gameplay gates UNTESTED; no
acceptance claimed.

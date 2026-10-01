# Overworld save-serializer engine slice (#736)

Bounded native engine producer implementing the save-serializer boundary for
real (the #712 contract proved insufficient without an engine wire).
Implementation owner: Codex through shared account `4laric`. No ADMIT.

## What was built

- `native/pc_port/pc_p2_overworld_save.{h,cpp}` (new): deterministic
  overworld session serializer (`area`, `day`, per-color `squad[8]`, `other`,
  `total`, `highscore`, `unlocked`) with strict fail-closed parsing, an
  explicit size guard, census validation (`total == sum + other`) and a
  save/load round-trip check, per the #712 round-trip and size-guard rules.
  Squad is counted live from `pikiMgr`; area/day/highscore/unlock come only
  from explicit fixture context (`setContext`), never invented.
- `native/pc_port/pc_bbft.cpp`: ADDs the `p2OverworldSaveCallSite()` session
  call into `pc_bbft_update()`; the reference is weak-linked
  (null-by-default) so `pc_bbft_test` keeps linking without the module.
  The poll itself is context-gated: production runs that never set context
  perform no file I/O.
- `native/CMakeLists.txt`: adds `pc_port/pc_p2_overworld_save.cpp` to
  `pikmin_pc` (#186 review before shared-line landing).
- `native/tools/p2_overworld_save_serializer_fixture.cpp`: guarded
  replacement-main fixture (vendored #632 guard) that sets explicit session
  context (area yakushima), verifies a live save/reload round-trip and
  requires it plus a live squad for PASS.
- `scripts/build_p2_overworld_save_serializer.py`: standalone leased
  build/run helper (Ninja response-file shim, guard self-test + negative).
- `experimental/pikmin2_overworld_save_serializer_engine.py` +
  `tests/test_pikmin2_overworld_save_serializer_engine.py`: independent
  Python reference model of the same grammar/guards (11 tests green).

## Markers and evidence

`P2_OVERWORLD_SAVE_SAVED/LOADED/SUPPORTED/REFUSED/ABSENT` plus the fixture's
`P2_SAVE_FIXTURE_*`/`PASS SAVE_FIXTURE` markers. A real yakushima-context run
reports `P2_OVERWORLD_SAVE_SUPPORTED` with save/reload observed.

## Captain safety (#632)

Any runtime run adopts `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`) or a
tested equivalent: orimaDead/NaviDead/HP<=1 before every pause/movie return
or observed tick, CAPTAIN_DOWN + BLOCKED exit, parked captain, no blanket
invincibility, recorded hashes.

## Boundaries

Only the save-serializer slice is implemented here. Receipt ledger,
exit/reentry, boot and day remain follow-ons for #605/#606/#607. All six
runtime gates stay UNTESTED except the observed save boundary. No gameplay
acceptance, no ADMIT.
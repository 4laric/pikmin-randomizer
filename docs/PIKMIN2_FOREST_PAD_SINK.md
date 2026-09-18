# Forest controller PAD sink (issue #794; consumer #660)

Lane `forest-controller-pad-sink-native`. Owner: Codex through shared account
4laric. Test-only scripted PAD sink so a fixture can drive result/save screens
that poll `mParentSection->mController` while scripted-pad reaches only
`mCurrentInput`: `ControllerMgr::keyDown` reads `sControllerPad` directly
(`controllerMgr.cpp:42`; copied into state at lines 62-143).

## Change (owned files; #741 + #660 fixtures untouched)

- `native/src/sysDolphin/controllerMgr.cpp` (+6): `testSinkPadButtons`
  writes `sControllerPad[0].button`. Test-only; production never calls it.
- `native/include/Controller.h` (+6): decl in `ControllerMgr`.
- `native/tools/p2_forest_pad_sink_fixture.cpp` (new): guarded fixture proving
  `keyDown(A/START)` true after injection and false without, with no-bleed and
  clear-after-write checks. Headless (static PAD state needs no window).
- `scripts/build_p2_forest_pad_sink.py`, `docs/PIKMIN2_FOREST_PAD_SINK.md`,
  `experimental/pikmin2_forest_pad_sink.py`,
  `tests/test_pikmin2_forest_pad_sink.py` (10 focused tests green).

Do NOT touch `newPikiGame.cpp` (live #741) or #660 fixture files. SERIALIZED:
existing-owner (#741) + #186 review + integrator landing.

## Evidence (leased private build, token `4b48184d`)

- `pikmin_pc` links with the sink (`bin/nectar.exe`); `ninja -n` no-work.
- Fixture exe sha256 `332bc2ff8e084a319bf1944f62a78aaea686fc8377ad054e01d4be1164051e4e`.
- Run: baseline clear, OBSERVED A, OBSERVED START, GATES UNTESTED, PASS
  markers=3, exit 0; guard self PASS, negative BLOCKED/86. Log sha256
  recorded in the handoff. No captain-down, no refusal.
- Guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
  (vendored read-only; trip -> BLOCKED/86). Refuse unguarded runs.

## Downstream / gates

Consumer `p2-overworld-forest-runtime-input-injection` (#660, live) uses the
sink for scripted result-screen presses. All six gates UNTESTED. No ADMIT.

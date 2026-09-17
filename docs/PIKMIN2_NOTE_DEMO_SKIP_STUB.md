# Jac_NoteDemoSkipped legacy stub (lane audio-note-demo-skip-stub-native, #704)

Bounded shared-file producer for the pre-existing default-config
(`PIKMIN_NATIVE_JAUDIO=OFF`) `pikmin_pc` link gap that blocks the #693 preview
rebuild. Downstream: #693 preview rebuild -> #632 guarded run -> #150 yakushima
P1 native runtime. Shared-file landing requires #186 review; this lane lands
nothing itself (private candidate + single-writer integration).

## Traced gap

`native/src/plugPikiColin/moviePlayer.cpp` calls `Jac_NoteDemoSkipped()` at
:760 (`requestSkip` fanned out) and :767 (`skipScene`, `PIKI_PC_PORT` only).
`plugPikiColin/*.cpp` is always compiled. With JAudio off, the real definition
(`native/src/jaudio/pikidemo.c:54`, compiled only when
`PIKMIN_NATIVE_JAUDIO=ON`) is absent, while the always-compiled legacy stub set
(`native/pc_port/dolphin_stubs/audio_stubs.cpp`) defined every other `Jac_*`
entry point but not this one. Result: `undefined reference to
Jac_NoteDemoSkipped()` at default-config link time (proved by the #693 lane's
`build-pikmin-pc.log`).

## Real semantics mirrored (not invented)

`pikidemo.c` (PC_PORT): `Jac_NoteDemoSkipped()` sets `demo_was_skipped = TRUE`;
`__Jac_FinishDemo` consults it and clears the `0x20` carry bit for that finish
(`if (demo_was_skipped) flag &= ~0x20; demo_was_skipped = FALSE;`), so a
skipped demo never carries its stream into the next scene.

The stub mirrors this with file-local state: `sDemoWasSkipped` is set by the
new `Jac_NoteDemoSkipped()` and consulted at the top of the stub
`Jac_FinishDemo()`, which forces `sKeepDemoStreamOnFinish = false` for that
finish and then clears the flag. Linkage note: `jaudio/pikidemo.h` declares
`Jac_NoteDemoSkipped` with C++ linkage (after `END_SCOPE_EXTERN_C`), unlike
the C-linkage `Jac_*` stubs; the definition therefore lives after the
`extern "C"` block in `audio_stubs.cpp`.

## Owned files

- `native/pc_port/dolphin_stubs/audio_stubs.cpp` — the stub (+3 lines state,
  +definition, +consult). No other shared file touched; no CMakeLists edit.
- `native/tools/p2_note_demo_skip_stub_test.cpp` — focused test linking the
  REAL stub object with stubbed `pc_audio_*` externals (a recording
  `pc_audio_fade_stream`): carry kept without skip, skip suppresses carry on
  finish, skip flag consumed. Exit 0 only on all three.
- `scripts/build_p2_note_demo_skip_stub.py` — private leased build helper
  (exclusive build dir, canonical lease CLI, live elastic cap).
- `experimental/pikmin2_note_demo_skip_stub.py` + `tests/...` — evidence
  verifier for the compiled artifacts (link clean, symbol defined, test PASS).
- This doc.

## Compiled evidence (recorded, not claimed)

- Default-config `pikmin_pc` links with no undefined reference; executable
  produced (SHA-256 recorded).
- `nm` proves `Jac_NoteDemoSkipped` defined (`T`) in the stub object.
- `ninja -n` dry run recorded.
- Focused test executable passes against the real object (SHA-256 recorded).
- All six runtime gates UNTESTED; no runtime run; no ADMIT.

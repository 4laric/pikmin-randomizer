# Kusachi boot-stall diagnosis (#822; consumer #818)

Lane `kusachi-boot-stall-diagnosis`, issue #822 (OPEN, assigned 4laric).
Downstream consumer: kusachi-gate-persistence-observation (#818 blocked
gen 4 rev 7). The consumer built green at native 704bad6c but two headed
300 s runs stall identically post-audio-init. Bounded tooling-only
diagnosis: boot logs + staged assets audited read-only. No shared/native/
CMake edits, no builds, no launches, no ADMIT, no gameplay acceptance.
All six gates UNTESTED. Captain safety #632 not applicable (no runtime);
guard standard `scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
recorded for the re-run slice.

## Stall signature (both runs byte-identical modulo session id)

- Logs: `output/kusachi-gate-observation-run4/native.log` and
  `output/kusachi-gate-observation-run5/native.log` (1489 bytes, 24 lines
  each; run-result: timed_out, exit 1, READY false, captain_down false).
- Observed in order: `P2_CHALLENGE_STAGE_FLAG` + `P2_KUSACHI_CONTENT_WIRING_STAGE`
  (fixture argv/stage bind OK), full GL/window/audio init through
  `[jaudio] NextOS DSP, SDL2 S16 stereo 32000 Hz`.
- NEVER observed: any `DVDOpen` line, `PADInit`, any
  `P2_CHALLENGE_CONTENT_WIRED` / PASS / FAIL / persistence marker.
- run-inputs: exe `4a44273e...`, boot fonts staged (consFont `ab757186...`,
  bigFont `528974ca...`), cwd run5/run4. Staged assets contain ONLY the two
  fonts: no `SndData` tree, no `stages/` tree.

## Stall window (cited)

Boot order from the fixture TU (`tools/p2_kusachi_content_wiring_fixture.cpp:168-226`,
main: window :207-221, `gsys->Initialise()` :223, `gsys->run()` :226):

- `System::Initialise` (`src/sysDolphin/system.cpp:1096-1179`): OSInit
  :1098, CARDInit :1099, DVDInit :1123, bigFont load :1154-1155,
  `Jac_Start(...)` :1160, `mControllerMgr.init()` :1170, cons font :1173.
- `Jac_Start` (`src/jaudio/verysimple.c:403-441`): audio thread, FastOpen
  registrations (:412-428), archiver/play init, `DVDT_CheckPass` :433.
- DSP sink print: `pc_port/audio/jaudio_sink.cpp:48` (STDERR, unbuffered -
  reliable as last-observed).
- First-absent markers and their sites: `JAudio wave catalog loaded`
  (`pc_port/audio/pc_audio.cpp:693`), sequence DVD load
  (`pc_audio.cpp:706` loading `assets/dataDir/SndData/Seqs/pikiseq.arc`),
  `PADInit` (`pc_port/dolphin_stubs/pad_stubs.cpp:28`).
- Healthy JAUDIO comparison (landed #793 probe log, same audio config):
  DSP -> `pikiseq.arc` x5 -> `pikibank.bx` x2 -> `pikise_0.aw` x2 ->
  PADInit -> full asset cascade. The stalled runs show NONE of this.

So the stall window is: after the DSP sink open, before the first catalog
print / SndData DVD open / PADInit - i.e. inside the JAUDIO catalog-load
region with the entire `SndData` tree absent from staged assets.

## Leading hypothesis (not a pinned cause)

Missing-asset boot stall: the catalog loader issues DVD opens for files
under the absent `assets/dataDir/SndData` tree and the boot never
proceeds and never prints an error. Responsibly NOT pinned as the cause
because (a) stdout under timeout-kill may under-report execution (the DSP
print is STDERR-unbuffered; later stdout may be lost), so the precise
intra-init call cannot be fixed from these logs alone; (b) a hang inside
`Jac_AddDVDBuffer`/ARAM/file-roots/:1170 (all silent, between DSP and
PADInit) is not excluded. Verdict: NEEDS-RUNTIME-PROBE with the exact
slice below.

## First bounded executable re-run slice (for #818)

- Command: `scripts/run_pikmin2_fixture.py --exe <fixture.exe>
  --run-dir <fresh private run dir> --timeout 120
  --arg=--experimental-pikmin2-room
  --arg=--experimental-challenge-stage --arg=ch_NARI_01kusachi
  --pass-marker P2_CHALLENGE_CONTENT_WIRED`, with:
  (a) `assets/dataDir/SndData` staged from the retail tree (user asset;
  fail closed with reason if unavailable), and
  (b) unbuffered logging: `setvbuf(stdout, NULL, _IONBF, 0)` at fixture
  main top (as `pc_main.cpp:87` does) OR duplicate progress markers to
  STDERR, so a timeout-kill preserves the true stall point.
- Bounds: 120 s (the stall reproduces by ~30 s of silence past audio init;
  300 s adds nothing), 960x540 centred, #632 guard active, captain parked.
- Expected discriminations: SndData DVD opens appear -> asset hypothesis
  confirmed/cleared by their OK/FAILED lines; PADInit appears -> hang is
  later (wiring loop); still silent at DSP -> hang is in Jac tail
  (:434-441) or :1161-1170, escalate to an instrumented init trace.
- Consumer: kusachi-gate-persistence-observation (#818); on an observing
  boot, proceed to the save/reload/retry/re-entry exercise for #533.

## Pins

- Native audit pin 704bad6c; consumer root 8a6eb3b3; exe `4a44273e...`.
- This lane: root 3a33cbde (branch `codex/kusachi-boot-stall-diagnosis`),
  analyzer + 11 tests green, this doc. No ADMIT.

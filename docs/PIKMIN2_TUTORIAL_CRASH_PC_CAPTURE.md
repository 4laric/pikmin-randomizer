# Tutorial post-audio crash-PC capture (lane tutorial-crash-pc-capture, #750)

Bounded capture of the faulting PC for the deterministic tutorial P1
post-audio boot crash (exit 0xC0000005 after NextOS DSP, no engine markers).
Root-only tooling: the pinned exe runs read-only (no rebuild, no engine
edits); native sources are read-only references. All six gates UNTESTED.

## Pins

- Exe: `output/tutorial-p1-native-runtime-build/p2_tutorial_p1_runtime.exe`
  sha256 `f235e032...` (verified before every run; never rebuilt).
- Run dir: staged `run-tutorial` from the #148 staged-rerun output; consumer
  command `p2_tutorial_p1_runtime.exe --experimental-pikmin2-room`.
- Native reference pin `13b4262c` (read-only); root base `ecf5f53a`.
- Suspects (from the #750 diagnosis packet): jaudio_host renderJAudioFrame /
  pumpAudio / beginSinkOpen / serviceSinkOpen; verysimple Jac_Start tail;
  system Initialise tail.

## Mechanism (as executed)

1. A first attempt attached via ctypes DEBUG_PROCESS. It observed loader and
   thread events but NO crash exception in 150 s, while an un-debugged control
   run crashed promptly (exit 0xC0000005). Verdict: debugger attach perturbs
   the fault timing; attached capture is refused as a method for this crash.
2. Production mechanism: WER LocalDumps harvest (HKCU key, removed afterwards)
   on the un-debugged run, then a pure-Python minidump parse (exception stream
   + module list) plus PE export-table parsing. Two real bugs fixed along the
   way: an undersized DEBUG_EVENT struct and an ExceptionRecord field-width
   error, both covered by synthetic-minidump unit tests.
3. Symbol resolution: the exe ships no usable DWARF (addr2line returns `??`),
   so the fault RVA was resolved with `nm --numeric-sort` (nearest defined
   symbol below) and confirmed by disassembling the fault address with
   `objdump -d`. Both tools are read-only observers, not builders.

## Result (verdict COLLAPSED-EXE-FUNCTION)

- Fault VMA `0x14015ff54`, module the exe itself, offset `0x15ff54`
  (1441620), read access (`info0=0`) to wild target `0xe00000000`.
- Nearest defined symbol below: `Font::setTexture(Texture*,int,int)`
  `.constprop.0` at `0x14015fef0` (+0x64 to fault; next symbol
  `Font::stringWidth` at `0x1401605f0`, so the fault is firmly inside).
- Faulting instruction: `movzx eax,WORD PTR [r14+0xe]` - a read through a
  wild object pointer during boot-splash font-texture setup.
- This lies OUTSIDE all four ranked audio suspects: the crash site is UI/font
  code reached after audio init, not the audio pump/sink itself. The audio
  phase remains the trigger context, not the fault site.
- Evidence (hashed): `capture-record.json`, `packet-pc-capture.json`,
  `capture-run.log`, `dumps/capture.dmp` (282 MB WER dump),
  `pytest-pc-capture.log` under `prepared/pc-capture-output/`.

## Tests

- `tests/test_pikmin2_tutorial_crash_pc_capture.py`: 16 green - collapse
  decision table (including COLLAPSED and REFUSED paths), synthetic-minidump
  parse tests, export-parser units (including the real exe, parse-only),
  packet shape, pinned constants, `--check`.

## Captain safety #632

Guard header `scripts/p2_fixture_captain_guard.h` (sha256 `d2f678c9...`)
recorded. The crash occurs pre-idle with no pause/movie returns and no
observed ticks or markers, so no CAPTAIN_DOWN evaluation is possible and no
PASS is claimed on that basis. Any future runtime work re-adopts the guard
with fresh hashes.
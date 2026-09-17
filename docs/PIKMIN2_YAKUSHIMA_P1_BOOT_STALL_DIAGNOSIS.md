# Yakushima P1 headed-boot stall diagnosis (#717)

Bounded engine diagnosis pinpointing the #150 headed-boot stall (distinct from
the #671 yakushima_4 bracket). Downstream: `p2-overworld-yakushima-p1-native-runtime`
(#150) squad observation once the stall is fixed. No shared edits; the #150
fixture is read-only.

## Result (traced, with contrasting runs)

**The stall is data-dependent and sits inside `System::Initialise()` after
`Jac_Start` when the JAudio asset set is missing from the run root.**

Two runs of the same diagnosis executable (native `400d7b45`):

1. Run from the repo root (no staged `assets/`):
   - Phases reach `before-gsys-initialise` and never `after-gsys-initialise`.
   - `DVDOpen("/dataDir/SndData/Seqs/pikiseq.arc") -> FAILED` (5 retries) and
     `DVDOpen("/dataDir/SndData/Banks/pikibank.bx") -> FAILED`.
   - Then the main thread blocks in an OS call: the captured RIP is in a
     loaded system DLL (not game code), i.e. a blocking wait/retry inside the
     DVD/audio load handshake. Watchdog timeout, exit 2 (fail closed).
   - Log `out/diagnosis-run-jaudioon.log`.
2. Run from a staged run root (`output/bomb-joint-runs/chappy`, whose
   `assets/dataDir/SndData/` provides the JAudio banks):
   - Boot passes `Initialise()`, jaudio reports
     `[jaudio-bank] BX ready: 18/22 WSYS, 19/22 IBNK`, generators initialise
     (111 creatures spawned), `P2_ROOM_READY` appears, and the fixture reaches
     `P2_YAKUSHIMA_P1_DIAG_IDLE_RUNNING idle_ticks=60`, exit 0.
   - Log `out/diagnosis-run-staged-assets.log`.

## Exact stall and code evidence

- Phase markers bracket `gsys->Initialise()` (diagnosis `main`):
  `before-gsys-initialise` prints, `after-gsys-initialise` never does.
- `System::Initialise()` (native `src/sysDolphin/system.cpp:1096`) ends at
  `endLoading()` (line 1178); the last engine line printed is `Jac_Start`
  (line 1160). The block is therefore between the `Jac_Start` audio bring-up
  (line 1160) and `endLoading()` (line 1178), and the failed `DVDOpen` lines
  name the missing members: `dataDir/SndData/Seqs/pikiseq.arc` and
  `dataDir/SndData/Banks/pikibank.bx`.
- The blocking RIP in a system DLL shows the failure mode: a missing
  `SndData` member does not error out; it blocks the boot in the
  DVD/audio loader handshake (the silent-stall class the #150 log records).

## Fix / follow-on owner

1. **Data/run-root (immediate, #150 lane + data owner):** run the headed
   fixture from a run root that stages `assets/dataDir/SndData/` (the layout
   sibling lanes already use, e.g. `output/bomb-joint-runs/chappy`). The
   diagnosis proves this boots to idle with a live room. The earlier "raw
   assets ruled out" covered the disc members, not this run-root staging.
2. **Engine follow-on (owner: port/DVD-loader):** make a missing `SndData`
   member fail closed with an explicit error instead of blocking inside the
   `Jac_Start`/DVD handshake, so this class of stall can never be silent again.

## Method (no shared edits)

- `native/tools/p2_yakushima_p1_boot_diagnosis.cpp` (new): replacement-main
  with phase markers from shader-init through data load to squad, a watchdog
  that captures the main thread's RIP, fail-closed exits, and the #632 guard
  vendored verbatim. `<windows.h>` is deliberately NOT included (it collides
  with the engine `typedef u32 HWND`); four kernel32 entry points are declared
  directly and a raw CONTEXT buffer is used (offsets measured by the
  standalone probe: ContextFlags 48, Rip 248, CONTEXT_CONTROL 0x100001).
- `scripts/build_p2_yakushima_p1_boot_diagnosis.py` (new): private leased
  build/run helper (default and jaudio-on variants), symbol mapping via
  `nm`/`addr2line`.
- `experimental/pikmin2_yakushima_p1_boot_stall_diagnosis.py` +
  `tests/...`: fail-closed verifier over the two contrasting logs.
- This doc.

## Evidence (hashes)

- `out/diagnosis-run-jaudioon.log` (missing-asset stall): sha256
  `9d8ab9d0233bef7816364d56dfa62d0a48fc0aad3575a40bd0df86eaed4e98fc`.
- `out/diagnosis-run-staged-assets.log` (boots to idle): sha256
  `24e68d0f4d674a5fb585d61f27b6f71224f985135484791161910ed3f3ff1a95`.
- Build record `out/build-record-1789653060899136-jaudioon.json`: configure 0,
  pikmin_pc 0, ninja -n 0, self-test pass, negative 86, diagnosis exit 2
  (missing-asset run), executable sha256
  `3deb1b2f4710074bf4acade93377a8baca3ade1c3d37e930f29736988a58f4be`.

## Captain safety #632

Guard vendored verbatim from `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`) and
checked immediately after engine idle before any observation; self-test 7/7 and
negative path exit 86 verified. The idle-running diagnosis run reached a live
room with the guard active and no captain-down. No blanket invincibility; no
runtime acceptance claimed (all six gates UNTESTED).

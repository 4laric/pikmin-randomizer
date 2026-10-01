# Tutorial P1 post-audio boot crash diagnosis (issue #750)

Lane `tutorial-postaudio-crash-diagnosis`, generation 2. Owner: Codex through
shared account 4laric. BOUNDED tooling diagnosis: read-only trace of the
deterministic `0xC0000005` crash in the #148 tutorial P1 staged runs from
code (native pin `13b4262c`) plus the two headed-run logs read-only. No
family/shared/native edits, no runtime launches, no ADMIT. Downstream
consumer: `p2-overworld-tutorial-p1-staged-rerun` (#148) squad observation
once the cause is fixed.

## Proven fault window

Both headed runs (`headed-run.log` sha256
`a04fe2d9209e58cdf5858424326c84d3bdba0d609429d56bcf76fbc0ab89b747`,
`headed-run-confirm.log` sha256
`dc639f4138130fb4996bf3a7fd40c3fd8486a490266c5e4f9980726f2b21b7ea`;
1523 bytes / 23 lines each, byte-identical modulo window position) exit
`3221225477` (0xC0000005) with the tail:

```
[jaudio-bank] BX ready: 18/22 WSYS, 19/22 IBNK; 882 waves/30 archives/...
[jaudio] NextOS DSP, SDL2 S16 stereo 32000 Hz
<crash; nothing further>
```

`NextOS DSP` is printed by the background sink-open thread in
`pc_port/audio/jaudio_sink.cpp:48` on successful device open. After it, the
process dies before ANY of: a DVDOpen attempt (success or failure), screen-
texture loads, node-manager creation, `P2_ROOM_PREVIEW`, generator spawns,
FPS lines, or any flushed fixture output (`P2_TUTORIAL_P1_WAIT`,
`P2_TUTORIAL_P1_ENGINE_FACT`, markers). The staged SndData set (48 files
incl. `Seqs/pikiseq.arc`, 219392 bytes) is present on disk.

## Ruled out (with evidence)

- Loader-stage DLL failure: distinguished signature exit `3221225781`
  (0xC0000135) with zero output, reproduced once without msys64 on PATH;
  both crash runs had the documented env and got 23 lines in.
- Audio device open: the DSP line itself proves success.
- Bank conversion errors: BX line shows no conversion/registration failures,
  and the identical 18/22+19/22 profile survives in unrelated boots.
- Missing staged SndData: all 48 files present with recorded hashes,
  including `pikiseq.arc`.
- DVD asset resolution of the staged set: zero DVDOpen attempts of any kind,
  so resolution never ran, let alone failed.
- Font loads: `bigFont->setTexture` (`src/sysDolphin/system.cpp:1155`) runs
  BEFORE `Jac_Start` (`:1160`) through the identical `loadTexture` mechanism
  as the later cons-font load; a missing-file null deref there would crash
  pre-audio, contradicting the observed post-audio crash.
- PADInit (`pc_port/dolphin_stubs/pad_stubs.cpp:17`): memset + printf only.
- `Jac_AddDVDBuffer` (`src/sysDolphin/system.cpp:1161`): proven side-effect
  free for null/empty via `__WriteBufferSize` (`src/jaudio/dvdthread.c:364`).
- `pc_settings_p2d_init` (`pc_port/settings/pc_settings_p2d.cpp:78`): null-
  safe plates check, and would DVD-log first.
- Captain guard: self-test green, no `CAPTAIN_DOWN` in either log.

## Ranked suspects (hypotheses with file:line, NOT proven)

1. First-frame JAI audio pump: `renderJAudioFrame`
   (`pc_port/audio/jaudio_host.cpp:1532`) via `DspPlayerCallback` /
   `UpdateDSPchannelAll` / `PlayerCallback` / `StreamMain` against the
   partial bank loads.
2. JAI-tail init inside `Jac_Start` (`src/jaudio/verysimple.c:404-441`):
   `Jac_PlayInit`, `WaveScene_Set`, `DVDT_CheckPass`, `Jac_Portcmd_Init`,
   `Jal_CmdQueue_Init`, `Jac_InitEventSystem`, `Jac_InitDemoSystem`,
   `Jac_InitStreamSystem` — unlogged, pointer-rich.
3. Sink-thread teardown race (`beginSinkOpen` / `serviceSinkOpen` /
   `joinSinkOpenThread`, `pc_port/audio/jaudio_host.cpp:1588+`).
4. gsys tail (`mControllerMgr` beyond init, `mTimer`, `endLoading` thread
   join, `src/sysDolphin/system.cpp:1161-1178`).

Caveat: stdout is fully buffered under pipe capture, so unflushed engine
output after the crash point is lost; the window above is bounded by
flushed/stderr evidence only. A faulting-PC capture (debugger/crash dump)
on exe `f235e032` collapses suspects 1-4 to one function.

## Fix / follow-on owner

No live lane owns audio/engine-init diagnosis. Route via #186 shared review
+ coordinator #570. Concrete bounded follow-on (NOT staged here): an
engine-boot phase-marker + null-guard lane that adds fflush-marked phase
prints through the window above and null-guards the JAI-tail init, then
re-runs the staged tutorial boot to capture the faulting phase.

## Remaining work

- #148 squad observation stays blocked on this crash fix.
- Full P1/P2 acceptance for the tutorial surface stays OPEN.

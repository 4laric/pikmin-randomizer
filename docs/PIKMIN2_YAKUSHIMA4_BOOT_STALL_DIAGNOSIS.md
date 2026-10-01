# Yakushima4 boot-stall diagnosis (#671)

Coordinator follow-up for the stopped consumer shard-caves-yakushima-yakushima4-p1
(#161, gen-9): its guarded boot reaches the centred window and GL 3.3, then
either hangs silently after texture-filtering init or refuses at cave entry
validation. Implementation owner: Codex through shared account 4laric;
executing contributor Muse Spark 1.3 (worker muse-l58). No engine/shared
edits, no runtime by this lane, no ADMIT. All six runtime gates UNTESTED.

## Verdicts (observed, not inferred)

Three distinct boot outcomes on the evidence, classified by
experimental/pikmin2_yakushima4_boot_stall_diagnosis.py:

1. Silent hang after audio init (repaired-run, native.log,
   repaired-second.log, repaired-third.log): last marker
   [jaudio] NextOS DSP, then nothing -- no DVD reads, no memstat dump,
   no GameFlow burst, no Fog line, no P2_CAVE_* markers. The
   timeout-supervised run was killed at 45 s (exit 1, timed_out true).
2. Entry refusal (repaired-run-v2, same exe sha256): full boot through
   memstat dump, DVD burst (207 files), Fog init and arena checks, then
   Invalid P2 cave entry: spawn count differs from checkpoint followed
   by process abort (exit 3 in 3.8 s, no timeout).
3. Historical font crash (debug-run.txt, GDB): SIGSEGV in
   Font::setTexture called by System::Initialise, from an overlay file
   junction on assets/dataDir/consFont.bti (WinError 267). Repaired by
   the overlay rebuild (issue #671 investigation comment); not the
   current stall.

Same guarded binary (exe sha256
a9d82b1f87d0609caf72be6a23dd725d5379296b8c03044851dd6874d201005b)
produces outcomes 1 and 2 on different runs, so the divergence is
input/timing-dependent, not build-dependent.

## Evidence inventory (read-only)

- output/cave-boot-diagnosis/debug-run.txt (14747 B): GDB threads;
  Thread 1 SIGSEGV :56 with Font::setTexture frame :57 and :197.
- output/cave-boot-diagnosis/native.log (1400 B): hang signature with
  the jaudio-bank BX line present.
- output/cave-boot-diagnosis/repaired-second.log, repaired-third.log
  (1285 B each): hang signature without the BX line.
- output/cave-boot-diagnosis/repaired-run/run-result.json: same exe,
  timed_out true at 45 s, exit 1, all markers false, captain_down false.
- output/cave-boot-diagnosis/repaired-run-v2/native.log (47379 B):
  full boot to entry refusal; run-result.json exit 3, timed_out
  false, elapsed 3.828 s, markers all false.
- output/workflow/asset-inputs.json: yakushima_4.txt offset 770715532
  size 5977 with pinned sha256 (record shape validated in tests).

## Code citations (this worktree at 36b86839 unless noted)

- Last marker: engine/pc_port/audio/jaudio_sink.cpp:48
  (PikiAudioSinkTryOpen prints after SDL_OpenAudioDevice succeeds).
- DVD stub: engine/pc_port/dolphin_stubs/dvd_stubs.cpp:26-45 prints
  FAILED on failure and OK on success; silent logs contain neither
  after audio init, so the hang sits before the first post-audio
  DVDOpen call (bank reads per the progressing run).
- First post-audio reads in the progressing run (v2 :23-:45):
  SndData seqs/banks, PADInit, consFont.bti OK, screen fonts,
  nintendo.bti, gamePrms.bin, effects, archives -- the
  System::Initialise tail region (audio banks, PAD, fonts).
- Font crash site: legacy GameCube code; only symbol evidence at
  this pin (engine/config/DPIJ01_PIKIDEMO/symbols.txt:752
  setTexture__4FontFP7Textureii). The GDB trace attributes the call
  to System::Initialise.
- Entry refusal: engine/pc_port/pc_p2_cave.cpp:46 invalid() prints
  to stderr then aborts (MSVCRT abort exits 3, matching the v2
  run-result); :79 header, :82 Pikmin rows, :83 trailing check,
  :85 live-count check spawned.size() != squad.size().
- Entry inputs demand 20 live Pikmin (both entry files: header
  P2_CAVE_ENTRY_1, floor 1, health 1, count 20, all rows color 1
  maturity 1); the abort proves fewer (or a different number of)
  live Pikmin existed in pikiMgr when pc_p2_cave_setup ran.
- Progress markers when boot succeeds: engine/src/plugPikiKando/memStat.cpp:169
  (memStat dump), engine/src/plugPikiColin/gameflow.cpp:771/775
  (DVD burst report), engine/pc_port/gl/pc_gfx.cpp:4688 (Fog),
  engine/pc_port/pc_p2_cave.cpp:113 (P2_CAVE_READY).
- P2_BOMBSARAI_ARENA invalid profile
  (engine/pc_port/pc_p2_bombsarai_arena.cpp:329) is a non-fatal
  stderr note from an unrelated arena-profile check in the same
  boot; it does not abort and does not explain either failure.

## Source-visibility boundary (explicit)

Not present in this worktree, the maintained checkout, or any
visible branch: the guarded-fixture sources emitting
P2_CAVE_GUARDED_WINDOW, Texture filtering: anisotropy available and
P2_CAVE_GENERATE_PASS; the System::Initialise body; Font
implementation. Those lines come from the consumer lane's private
fixture build. The hang bracket is therefore stated as last-marker
to first-missing-marker, not as a named source line.

## Determination

- Asset condition: NO. The definition bytes are pinned and present;
  post-repair fonts read OK (v2 log shows consFont.bti and screen
  fonts opening); DVD reads succeed whenever reached. Nothing in any
  log shows a failed asset read after the repair.
- Loader regression: NO for the refusal (fail-closed count check
  working as designed -- the follow-on is why fewer than 20 Pikmin
  were alive: overlay squad timing vs checkpoint count, owned by the
  #161 consumer lane); UNRESOLVED for the silent hang, which sits
  inside/after audio-sink open and before the first post-audio DVD
  read, with no failing marker of its own.
- Missing hook: the guarded next-markers (memStat/GameFlow stage,
  P2_CAVE_READY) are produced by normal boot on success, not by a
  missing hook this lane can name from visible sources.

Precise next probe (not run by this lane): attach to the guarded exe
at audio-bank init or run with audio-driver/JKR verbosity and record
whether the hang is inside bank loading, PAD init, or the font path;
alternatively bisect the repaired overlay (fonts-only vs full) to
separate asset shape from loader behavior.

## Room-graph consumption check

No genuine collision claim is possible from current evidence, for two
independent reasons: (1) the stalled boots never reach any room or
collision load (no DVD room reads, no stage markers); (2) the
consumer's own module records that no authored yakushima_4 room graph
is available (that decode stays a record, not an implementation).
The offline generate-side PASS (rooms/spawns/links) is sidecar
staging, not observed collision.

## Packet

- Lane commit for the three owned files (branch
  codex/autofill-yakushima4-boot-stall-diagnosis).
- Failing condition: silent pre-stage hang (timeout kill) OR entry
  count refusal (abort exit 3), same binary, input/timing-dependent.
- Downstream consumer: shard-caves-yakushima-yakushima4-p1 (#161,
  gen-9, blocked) -- this packet unblocks diagnosis, not runtime.

## Reproduction

    py -3.12 -m pytest -q tests/test_pikmin2_yakushima4_boot_stall_diagnosis.py
    py -3.12 -m experimental.pikmin2_yakushima4_boot_stall_diagnosis --log <native.log>

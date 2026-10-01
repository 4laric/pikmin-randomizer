# Damagumo preview-room build + GL run (#815; consumer #798)

Lane `damagumo-preview-room-build`, issue #815 (OPEN, assigned 4laric).
Downstream consumer: shard-enemies-3-damagumo56-arena-assembly (#798 gen 3;
recovery classification 7f18fc4bae5304b36f2f32d85d0990c7bbe097782c27f31dc4c46377639fa127). Bounded leased preview-room build
at native pin 45534ee3 splicing the EXISTING p2_muse_damagumo_room_app.cpp
RoomApp class, plus a leased headed GL run, all under #632 captain guard.
No engine changes (private-tree splice only; membership verified read-only).
No ADMIT, no worker launches. All six runtime gates UNTESTED except the
observed boot markers below.

## Source pins (all verified)

- Native base 45534ee3d5193b776339a8b464f004d4d24eae5d
  (shard-enemies-3-damagumo56-observer: provider slot 312004 + guard).
- `tools/p2_muse_damagumo_room_app.cpp`: complete
  `class RoomApp : public PlugPikiApp` at line 27 (header documents the
  splice pattern; never links alone).
- `tools/preview_p2_room.cpp`: splice host (walk-fixture RoomApp at
  lines 156-378, main at 379 with 960x540 centred window + `--experimental-pikmin2-room`).
- Private splice commit 9cbd2d6527b0f9b336f8381cd8b4d6852212c41c on branch
  `codex/damagumo-preview-room-build-native`: replaced host RoomApp with the
  damagumo class + added host includes `GameStat.h`, `pc_p2_long_legs.h`
  (both already used elsewhere at this pin; e.g. pc_p2_dangomushi.cpp:58,
  pc_p2_preview.cpp). Private tree only; shared native untouched.
- Root worktree at a50903714acd94d72dc6e014e5f13fd6dce519ea (lane branch
  `codex/damagumo-preview-room-build`); the 3 owned files below are the only
  root changes.

## Leased build evidence (canonical lease CLI, jobs 6)

- build-02/build-result.json sha256 `414f63b88cbf5c7fe1340b8371ba24de0931102304267323498f79c5e506acaa`: passed True,
  launched True, exit 0, native_head 9cbd2d65, dirty empty.
- Engine exe `bin/nectar.exe` sha256
  `4412fc39a459464f5035e5fffcf5b912b8774d4683ea95dc51facf4b324e1a44`
  (identical at both heads: the spliced TU is not a pikmin_pc input).
- `ninja -n pikmin_pc` -> `ninja: no work to do.` (dry-run.log sha256
  `71aa391ec7d7e291b419a7f40fba91919e14ac2394ab4e8b66ed126e267d70f6`, same bytes as build.log: no rebuild was needed).
- Tools: g++.exe sha256 `fe03455c28ab0c69f1adb0ccde202124091f01d02b0c0ede8578f606063cc894`, ninja.exe sha256 `a7f084e8ee37bff0872aa8bd3d17cc19632d2a37734f6c242dd3dee22d77c0b4`
  (recorded in build-result preflight).
- Room exe `room-01/preview_p2_room.exe` sha256
  `8e5e05ebd976aaa3704a8fb09c1eec74d69b1e8f8667702c26e9744b67b8b129`
  (spliced TU compiled rc 0, linked against the 176 pikmin_pc objects minus
  pc_main plus libpikmin_legacy.a/libbbft_transport.a/SDL2; link log
  `9dbb24e64ce00bbe3c9d42942d33962d52492eec24646b76bd301c640d47e931`).

## GL run evidence (canonical runner, 960x540, timeout 120 s)

- run-02/run-result.json sha256 `40e4e4343d583f091fc1dfccafaa3eef96b94250c9f918059e3d56edaaf15f71`: exit 1, timed_out True
  (120.2 s), READY marker false, captain_down false, pid 27868.
- run-02/native.log sha256 `a921961381a369a593053e440ac33a2bbc5d09f36d7147c5ffcd247c9c6228de` (1492 bytes): real headed GL boot
  - `[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)`
  - `[PC Port] Experimental preview window set to 960x540 windowed and centered`
  - OpenGL 3.3 / Intel, TEV shaders compiled, GXInit, FXAA bloom, jaudio DSP.
- Zero `P2_MUSE_DAMAGUMO_*` markers in 120 s. Cause, verified: the staged
  stock asset `dataDir/stages/chal0/default.gen` is absent under the
  canonical root (no dataDir at all; only `assets/disc/*.iso`), and the
  arena slot-312004 staging it gates is pending per the harness STAGING
  CONTRACT. Without stage data there is no navi (harness returns silently
  per `if(!n)return result`), so stage 0 is unreachable. This is the
  documented fail-closed shape, not a harness defect: with staging present
  the same binary reaches `FAIL p2 room: staged Damagumo56 actor present at
  generator 312004` or the READY/BIND markers.
- Analyzer verdict on this log: boots window observed; harness markers
  absent due to missing stock asset (refusal reason recorded, not guessed).
- Boot fonts staged from byte-identical stock copies (consFont `ab757186aba824d8d256ab7ee0e044dfcef638474340a6b7755126d9b6c172a2`,
  bigFont `528974ca6291d46c4a91565834971db719763442fb4ef139d788c45f23faa3e6`); the stock enemy template was NOT lifted from other
  lanes privates: it lands separately as a user asset per the brief.

## Captain safety (#632)

- Guard `scripts/p2_fixture_captain_guard.h` sha256
  `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`.
- The harness carries the inline equivalent (roomapp lines 56-64:
  orimaDead/NaviDead/HP<=1 -> `P2_FIXTURE_CAPTAIN_DOWN ... outcome=BLOCKED`
  + `_Exit(86)`; references the header by name). Predicate matches the
  header except +/-inf hp (header `!isfinite`, harness `hp!=hp`); health
  values cannot be infinite, so behavior is identical on reachable inputs.
- Self-test 7/7 PASS against the actual header (guard-selftest.exe sha256
  `2934eecb0f5f95654c1b3dce603e476f385cf2db3cee67450d5e3f6b15ac5230`, transcript `b6cb5a65a5ec6179db90adf8a321be62424d31cd65557bb1a56d7d3ba4159527`): healthy/above-boundary exit 0
  with GUARD_CLEAN; hp-boundary/low/nan/orima/dead-state exit 86 with the
  exact CAPTAIN_DOWN marker. Negative path proven on the header; the
  in-harness negative (forced exit 86) is not runnable without a staged
  captain and is recorded as such, not claimed.
- Run-02 observed zero CAPTAIN_DOWN over 120 s (no captain exists without
  staging; nothing was endangered; no invincibility used).

## Owned files (this lane only)

- `experimental/pikmin2_damagumo_preview_room_build.py` - fail-closed
  analyzer (stock-asset refusal, marker grammar, dry-run/exe checks).
- `tests/test_pikmin2_damagumo_preview_room_build.py` - 9 tests green
  (boot/FAIL/captain-down parsing, all refusal paths).
- `docs/PIKMIN2_DAMAGUMO_PREVIEW_ROOM_BUILD.md` - this report.

## Remaining work (downstream #798)

1. User stages `dataDir/stages/chal0/default.gen` (user asset) + provider
   arena slot 312004 + demon-lane 56 profile/mesh + family visual
   conversion; re-run this exact room exe (sha256 `8e5e05ebd976aaa3704a8fb09c1eec74d69b1e8f8667702c26e9744b67b8b129`) and expect
   READY/BIND or the honest stage-0 FAIL naming the missing piece.
2. Any engine TU change needs a producer reservation + #186 review; none
   was made here.
3. #798 acceptance (natural arena behavior, six gates) is untouched.

## Pins recap

root a5090371 / native base 45534ee3 + splice 9cbd2d65 / engine exe
4412fc39 / room exe 8e5e05eb / guard d2f678c9. No ADMIT.

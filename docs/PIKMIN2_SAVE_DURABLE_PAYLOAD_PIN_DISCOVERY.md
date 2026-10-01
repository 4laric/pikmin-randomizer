# Save durable-payload pin-discovery (wired kusachi stage)

Lane `save-durable-payload-pin-discovery`, issue #132 (OPEN), downstream
consumers `kusachi-persistence-obs` (#781, blocked gen 2) and
`p2-challenge-ch_nari_01kusachi-p1` (#533). Owner: Codex through shared account
4laric. Tooling pin-discovery only: read-only audit, no native edits, no builds,
no runtime, no ADMIT. All six gates UNTESTED.

## Question

`kusachi-persistence-obs` gen 2 observed the #758 harness receipts on the wired
kusachi stage (ch_NARI_01kusachi, ui_index 3) but recorded durable save payloads
UNTESTED: "session roots are timestamp-scoped but card dirs empty; probes fire,
no payload written or restored" (gen2-report.json sha256
`dc406a492678504c4045a70c046b75afd2cc8fba29e525c3c6ec5aa5ea058ee2`).

## Verdict: ABSENT

No durable save-payload writer + session-card path exists for the wired kusachi
stage. Exact pins (all read via `git show`, no checkouts modified):

1. `pc_port/pc_p2_challenge_persistence.{h,cpp}` @ native
   `3916d9a4d854851b7637579b3d196a1c4ed6a90a`
   (branch `codex/autofill-challenge-persistence-engine-callsite-native-rebase`):
   `recordSave/recordLoad/recordClear/recordHighscore/recordUnlock/`
   `recordReceiptDedup/recordReentry` set in-memory flags and printf
   `P2_CHALLENGE_<STEM>` probe markers. Zero `fopen`/`fwrite`/`ofstream`/`CARD`
   calls in the translation unit. Neither file exists on the canonical line.
2. `pc_port/pc_p2_overworld_save.cpp` @ native
   `38305eea11200e517897bbc137a58bde40f927b4` (#736): the only real writer,
   `p2overworldsave::saveSession` (`std::ofstream`, `P2_OVERWORLD_SAVE_SAVED`),
   but overworld-session grammar only (`area/day/squad`), explicit caller path,
   no challenge `caveId` binding, no CARD card0 writes.
3. `pc_port/dolphin_stubs/card_stubs.cpp`: `CARDInit` (line 129) creates
   `<run>/save/bbft_sessions/<timestamp>/card0`; `CARDCreate` (line 175) and
   `CARDWrite` (line 211) exist but have NO callers on the kusachi path.
   `card0` in the #781 gen2 run dir is empty (verified).
4. `src/plugPikiColin/memoryCard.cpp`: retail writer
   `MemoryCard::writeOneGameFile` (line 542) via `cardutil.cpp` is driven only by
   the retail save UI flow, which the headed kusachi run never reaches.

## Owner / shared-review contract (not an implementation)

Produce a durable challenge-payload writer for `p2_challenge_save_<caveId>`.
Natural home: the #713 challenge-persistence module (`CARDCreate`/`CARDWrite`
payload or an `ofstream` sidecar plus private save-dir staging for the
payload-bearing run, per the gen2 save_dir_caveat). Shared review:
4laric/pikmin-randomizer#186 for the `pc_bbft.cpp` call chain. Alternative: a
challenge grammar in the #736 serializer. This diagnosis is never an engine
unblock; the repair is not complete until the #781 consumer check
(durable payloads written AND restored on the wired stage) passes.

## Tooling

`experimental/pikmin2_save_durable_payload_pin_discovery.py` exposes the
machine-readable pins registry (`pins`) and a fail-closed run-dir verifier
(`verify-run --dir`): `ABSENT` only when the save tree holds no payload files.
6 focused tests green (registry shape, owner contract, empty-card ABSENT,
payload UNEXPECTED, missing-dir REFUSED, malformed-input refused).
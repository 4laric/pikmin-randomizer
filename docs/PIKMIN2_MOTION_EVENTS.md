# Retail motion-event metadata

Engine lane, Codex through shared account 4laric; [#257](https://github.com/4laric/pikmin-randomizer/issues/257).

`experimental.pikmin2_motion_events` reads an existing locally extracted enemy
directory containing `enemyanimmgr.txt` and its registered BCA files. It writes
deterministic ASCII metadata for `engine/pc_port/pc_p2_motion_events.h` to parse.
It performs no model conversion, actor installation or gameplay event execution.

```powershell
py -3.12 -m experimental.pikmin2_motion_events LOCAL_ENEMY_DIRECTORY LOCAL_OUTPUT.txt
```

The destination must not exist. All input validation finishes before it is
created. Editor paths inside the registry are treated as text, never followed.
Only simple local BCA filenames are accepted. Generated tables remain local
alongside extracted assets; commit the importer/reader, not disc metadata.

## Protocol

`P2_RETAIL_EVENTS_1 registry_sha256 clip_count` precedes each motion record:
`filename duration bca_attribute bca_sha256 event_count`, then `frame type` pairs.
The reader retains raw integer frames, event types and order, including equal
frame events. SHA256 fields identify exact source bytes; the native reader checks
their format but does not open or hash assets itself. A host must verify them
against its installed source manifest before enabling a consumer.

Bounds: 256 clips, 4096 events per clip, 65536 events per table, duration 1–10000,
BCA attribute 0–4, registry 1 MiB and each BCA 16 MiB. BCA framing/pose structure
uses the existing `bca_pose` validator. Event frames must fall within the clip;
types are 0–999. Unknown types in that range remain data and are not assigned
invented behavior. Duplicate filenames, unsorted/out-of-range events, trailing
tokens, truncated blocks, and loop-end markers without an earlier lower-frame
loop-start are rejected. Repeated loop-start markers remain ordered source data.

## Source timing is distinct from generic clock markers

Source anchors in local `pikmin2-research`:

- `src/sysGCU/sysShape.cpp`, `AnimInfo::readEditor` (line 446): editor path,
  animation name, then integer frame/type pairs until frame -1.
- `Animator::animate` (line 133): a key becomes due when
  `key.frame < int(timer)`. For nonnegative timer this means an event at 10 is
  not due at 10 or 10.999; it is due at 11. The native `p2retail::due` helper
  implements that predicate without an overflowing float-to-int cast.
- The same method dispatches a loop-end callback before checking finish-motion.
  If motion is not finishing, it finds the preceding loop-start, rewinds to that
  frame and discards overshoot. It processes no second loop in that update.
  When finishing, it continues into any outro events instead.
- Completion clamps to total frame count minus one and emits an implicit END
  once. `include/SysShape/KeyEvent.h` defines loop start 0, loop end 1, END 1000
  and blend END 2000. Those implicit END values are not authored table rows.

The earlier generic source clock fires at exact marker boundaries and preserves
elapsed time across loops. Therefore this raw table must not be passed to it
as if the semantics were identical. BCA's loop attribute and the FSM's
finish-motion behavior also cannot be collapsed into one always-loop flag.
A retail playback adapter must explicitly implement these callback/rewind/outro
semantics; this batch supplies validated metadata and the due predicate only.

## Evidence

Tests run with the existing local #234 imports (US GPVE01 revision 0):

| Source | Clips | Authored events |
|---|---:|---:|
| Queen | 9 | 21 |
| Baby | 6 | 6 |
| KingChappy | 14 | 34 |

All 29 clips exported twice identically. The C++17 reader consumed each generated
table, tested every real event at its authored frame, just below the next integer,
and the next integer, and passed its malformed-input probes. Python tests cover
editor paths, duplicate/order/count/truncation failures, BCA rejection before
output creation and overwrite refusal. Four test methods pass; native compiles
with `-Wall -Wextra -Werror`. Real-asset cases execute when the local imports
exist; portable malformed/parser tests do not require disc data.

No actor events, damage, loop/outro playback, implicit END dispatch or visual
fidelity are claimed by this metadata batch. Existing family importers and fixed
runtime packages remain unchanged.

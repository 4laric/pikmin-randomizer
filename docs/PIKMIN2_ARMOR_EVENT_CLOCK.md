# Armor gameplay events on the sampled clock (#431, #165)

Lane 08, Codex through shared account `4laric`. Reference consumer migration
that moves a family gameplay effect off a per-state wall-time counter and onto
the authoritative #431 sampled-animation clock.

## What changed

`pc_port/pc_p2_armor.cpp` (Cloaking Burrow-nit, EnemyID 15) previously derived
its effects from `stateTime * 30`:

- the attack2 bite was a hard-coded frame window `17 < frame < 27`;
- eat fired from `stateTime >= event_frame/30` catch-up;
- flick read `clips["flick"].events.front().first`.

A frame skip that jumped past the bite window dropped the effect, and a state
re-entry reset `stateTime`/`firedEvents` inconsistently.

New `pc_port/pc_p2_armor_events.h` builds one `p2sampled::Clip` per authored
`p2-ground-bank.txt` row and owns one `p2sampled::Clock` per actor
(`p2armorevents::Receiver`). `enter()` starts the clip (bumping the clock
generation, which cancels the previous clip's outstanding events). Each update
advances by `dt * 30` source frames and dispatches the crossed source type-2
events:

| Clip | Source event | Action |
|---|---|---|
| `attack2` | `18:2` | bite capture (P1-host mouth swallow) |
| `eat` | `60:2` | single `InteractKill` |
| `flick` | `39:2` | `doFlick` knockback |

Type 0/1 (loop bounds) and type 3 events stay non-gameplay. `stateTime` and
`setPhase` remain the independent pose/completion projection, so displayed pose
never substitutes for event execution.

## Exactly-once semantics

The clock is the single timing authority:

- **Frame skips**: a large `advance()` emits every crossed event once, in source
  order, instead of relying on a window test.
- **Loops**: a looping clip emits its event once per cycle; one-shots clamp at
  `duration` and never wrap or refire.
- **Pause**: a zero/non-positive delta consumes nothing; `Clock::pause` is also
  available.
- **Interruption**: `start()` on a new clip bumps the generation and drops the
  previous clip's pending events.
- **Actor generation / address reuse**: `pc_p2_armor_setup` now resets the actor
  record (`s = Armor()`), and every `enter()` restarts the clock, so a recycled
  address cannot replay a stale event.

## Evidence

Standalone probe (no engine, no GL):

```powershell
g++ -std=c++17 -Wall -Wextra -Werror tools/test_p2_armor_events.cpp -o p2_armor_events.exe
./p2_armor_events.exe   # PASS p2_armor_events
```

It drives the real Armor event table through `p2armorevents::Receiver` and
covers steady stepping, frame skip, one-shot non-refire, loop-per-cycle, pause,
mid-clip interruption and address reuse. Registered as CTest
`p2_armor_events_test` in `native/CMakeLists.txt`.

The existing `experimental/pikmin2_armor_behavior.validate` markers are
preserved: the bite prints `P2_ARMOR_BITE ... frame=18`, inside the source
`(17, 27)` window, with one eat per bite.

## Non-claims

- No real-GL/arena capture in this pass; the runtime marker behaviour is
  unchanged except for the event source, and the run gate is a separate
  reserved-slot item.
- The P1-host capture remains the recorded port adaptation for the P2
  mouth-slot swallow; this slice only changes *when* it fires, not the effect.
- This lane owns the clock/event contract and this reference migration; other
  family consumers migrate with their owners.

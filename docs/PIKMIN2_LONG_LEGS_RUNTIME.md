# Long Legs FSM host runtime evidence (#173 / #312)

Lane 26 fourth slice: host the `pc_p2_long_legs_fsm` source policy for the
registered Houdai/BigFoot placement vehicles and observe the schedule at runtime.

Implementation owner: Codex via shared account `4laric`. Executing session:
opencode (deepseek-v4.1-flash), 2026-09-13.

- Native `opencode/p2-longlegs-fsm` @ `ad4dcd6e`, base `f9e139d8`, worktree
  `output/native-lane26`, build `output/native-lane26/build-fsm`.
- Patch `native-candidates/long-legs-policy/0003-pc_p2_long_legs-host.patch`.

## What changed

`pc_port/pc_p2_long_legs.cpp` now advances the lane-owned `P2LongLegsFsm` for
each registered actor. The port has no IKSystemMgr or animation-event reader, so
the policy is ticked from the draw path (called every frame for on-camera
registered actors) and the animation key edges are synthesized from the source
key frames in the audit (30 fps):

| Key edge | Synthesized from |
|---|---|
| `landingKey2` | half of the last landing key (Houdai 150 frames = 5.0 s; BigFoot 18 frames = 0.6 s) |
| `flickKey2` | half of the last flick key (Houdai 68 frames = 2.27 s; BigFoot 35 frames = 1.17 s) |
| `animEnd` | the last landing/flick key |

Wake/accumulation are host-fed (`nearestTarget` within `privateRadius`, Pikmin
census within 60 units). The policy emits intents; `P2_LONG_LEGS_STATE`,
`P2_LONG_LEGS_FOOT` and `P2_LONG_LEGS_SHELL` are logged but the effects (IK
movement, real foot-press collision, shell objects) are not applied.

## Fixture baseline adoption

| Field | Value |
|---|---|
| Root/native revision | native `opencode/p2-longlegs-fsm` @ `ad4dcd6e` (base `f9e139d8`) |
| Private build | `output/native-lane26/build-fsm`, `pikmin_pc` relink exit 0 |
| Executable SHA-256 | `E45BCC8D39AB702ABB029691FE541BE6DD8F7AC46CD700356F38D358567AEA4E` |
| Window | 960×540; log line `Experimental preview window set to 960x540 windowed and centered` |
| Squad | shared overlay: `P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1` |
| Run directory | `output/p2-lane26-longlegs-run/capture` |
| `native.log` SHA-256 | `5A8E0DF239A9583C9000D6153966A8C33A746096CE0A4228A59C6420F5EDB0E6` |

## Observed markers

```
P2_LONG_LEGS_BIND generator=312001 species=Houdai pose=bind visual_only=0 native_fsm=implemented
P2_LONG_LEGS_BIND generator=312002 species=BigFoot pose=bind visual_only=0 native_fsm=implemented
P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Land
P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Wait
P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Flick
P2_LONG_LEGS_STATE species=Houdai generator=312001 state=Shot
P2_LONG_LEGS_STATE species=BigFoot generator=312002 state=Wait
P2_LONG_LEGS_STATE species=BigFoot generator=312002 state=Flick
P2_LONG_LEGS_FOOT species=BigFoot generator=312002
```

33 state transitions were observed; Man-at-Legs entered `Shot` after a `Flick`
(source: always after a Flick), and BigFoot logged one foot-crush intent
(`P2_LONG_LEGS_FOOT`).

The landing key-2 foot press is then applied for real: `applyFootCrush` issues a
single `InteractFlick(actor, 100, pressDamage, angle)` to grounded Pikmin within
a 60-unit foot radius (the port has no `InteractPress`, so this is the documented
substitution, matching the Crawbster roll contact). In this fixture the squad
spawns ~190 units from BigFoot, so the intent fired but no Pikmin were under the
foot (`P2_LONG_LEGS_CRUSH` count 0). The application path is compiled and ready
for a placement where Pikmin are under a foot.

## Six-gate status

| Gate | Status | Note |
|---|---|---|
| 1. Exact identity and spawn | PARTIAL | placement vehicle; identity bind logged |
| 2. Autonomous movement and animation | PARTIAL | schedule observed; no IK movement |
| 3. Attacks and receivers | PARTIAL (policy) | crush/shell intents observed, not applied |
| 4. Death and corpse | UNTESTED | unchanged |
| 5. Actual transport and reward | UNTESTED | lane 06 |
| 6. Cleanup and re-entry | UNTESTED | unchanged |

## Remaining

IKSystemMgr leg stability, real foot-press collision, animation-event execution
(lane 08), Man-at-Legs shell objects (lane 20), damage receivers and death.

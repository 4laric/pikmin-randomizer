# Breadbug cargo animation bank and proxy mapping

Scope #168; Codex owner under shared 4laric. This batch adds a separate verified
pose bank and reference mapping. It does not change the native actor or the
P1 cargo behavior proven by the preceding runtime fixture.

The source enum in `native/pikmin2-research/include/Game/Entities/PanModokiBase.h`
(lines 243–251) identifies Back as `move2.bca`, Hide as `type3.bca`, and Carry
as `type5.bca`. Carry is **corpse carry**, called by `startCarcassMotion` in
`panModoki.cpp:663`; it must not be selected just because cargo is held.

`panModokiState.cpp:142` starts Back when hauling. CarryEnd retains that motion
while approaching home, then enters Hide at the loop end (`672` onward).
Hide starts its own animation at `403`, emits its effect at event 2 and calls
`endCarry` at animation end. Those events are metadata in this bank; they are
not executed by the P1 proxy and must never duplicate native cargo destruction.

The P1 source `native/src/plugPikiNakata/taicollec.cpp:620–708` independently
confirms these motion correspondences:

| P1 state | Source behavior | Proposed P2 visual |
|---|---|---|
| 5 | Move2 catching intro, transition at loop start | Back intro, cargo required |
| 6 | Move2 hauling toward nest | Back loop, cargo required |
| 8 | Type3 putting/swallowing | Hide once, cargo required |
| 9 | Underground; native clears visibility/collision/shadow | No visible clip |

Unknown states or absent cargo use existing fallback. Dead actors retain the
P1 corpse path. State 7 (being dragged) and states 10–14 remain separate gates;
this bounded mapping does not pretend to cover every source animation.

`experimental.pikmin2_breadbug_cargo_bank.py` verifies the imported model and
clip hashes before conversion. It validates the exact observed ordered event
lists: Back `(10,0),(39,1)` and Hide `(20,2)`. Event frames are included among
sampled poses, and all generated MOD bytes receive hashes. Source duration and
event bounds must agree. Neither a native profile nor actor placement is emitted.

Actual conversion passed at `output/p2-lifecycle-batch/breadbug-cargo-bank-01`:
Back has 10 sampled poses, Hide has 9, both duration 49. The model import is
bound to source manifest SHA256
`5fff4b091740975f32b55277fb4c500da5806e64e4aa30c688a88b1711b2db4f`.
Three reference tests pass, covering semantic mapping/fallback, exact event
samples and generated hashes, and tampering/wrong-event rejection. These are
conversion tests; native animation playback and mouth alignment remain untested.

## Proposed next native change (requires lane approval)

Keep `P2_BREADBUG_ACTOR_PROXY_1` and its default behavior unchanged. Add an
optional separately validated cargo-bank file, loaded by the existing actor
setup, with Back/Hide durations, sample frames and Back loop endpoints. A new
installer copies only the bank and its models into a private actor session;
it must verify all hashes and refuse existing targets before writing.

The family module alone selects the table above from native state and pointer 2.
Per-instance visual phase resets when the native state changes: state 5 uses
Back's pre-loop interval, state 6 loops only source frames 10–39, and state 8
plays/clamps Hide once. Phase progression must be tied to native animation or
simulation advancement, not wall-clock SDL time, so pause cannot consume the
whole swallow animation. Exact timing policy and native phase API should be
reviewed before implementation; source keyevents remain non-executable.

State 9 must respect native invisibility instead of drawing an idle Breadbug.
Setup/reset/forget clear optional bank and per-instance phase. No central
preview, collision, cargo, damage, reward or native FSM hook is needed. Repeat
the actual cargo fixture afterward and require unchanged grab/haul/release
evidence plus Back/Hide render samples and pause behavior.

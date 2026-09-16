# Gatling Groink shell strike -> health (lane 21, #204 / #205 / #208)

Implementation owner: Codex using shared account `4laric`. Executing agent:
opencode (deepseek-v4.1-flash), 2026-09-13. Extends the live-target Groink
candidate. This is the **shell health/death** half of lane 21, bounded to the
private host proxy receiver so no engine `Creature` health or shared damage
semantics (#186) are touched.

## What it adds

`pc_port/pc_p2_groink_strike.{h,cpp}` — a pure host bridge:

- `P2GroinkStrikeInput{ hit: P2GroinkHitInput, targetToken, attributedToken }` and
  `P2GroinkStrikeResult{valid, insideSweep, kind, damage, impulse, applied, died, health}`.
- `p2_groink_apply_strike(registry, input, candidate)` classifies with the
  existing `p2_groink_classify_hit`, then:
  - **Bomb** -> `P2ProjectileReceiverStrikeKind::InteractAttack` with the
    classifier's damage applied to the proxy receiver (never re-derived);
  - **Wind** -> no health mutation, but the source impulse is carried in the
    result (lane 20's receiver has no impulse field);
  - **None / invalid / degenerate sweep** -> no-op.
- `died` comes from the receiver's single-owner report, so a death marker fires
  exactly once.

Lane 20's `pc_port/pc_p2_projectile_receiver.{h,cpp}` (plus the `pc_p2_cannon_stone.h`
/ `pc_p2_rock_hazard.h` type headers) is **vendored** from native
`opencode/p2-projectiles-integration` @ `be8037af`; provenance is recorded in the
header and in `native-candidates/groink-strike/provenance.json`. The receiver's
`addAny` wildcard sink is what lets a real run hit a runtime creature token.

`tools/p2_groink_target_runtime.cpp` (the live-target volley fixture) now builds a
`P2GroinkHitCandidate` from the live Navi per terminal receipt and feeds the
retained `-10`-shifted step through the bridge, printing:

```
P2_GROINK_STRIKE_PLACEMENT fixture_pinned=1 reason=terminal_sweep_midpoint
P2_GROINK_RECEIVER_HIT token=<u64> kind=Bomb damage=10.000 health=<f>
P2_GROINK_RECEIVER_DEAD token=<u64>
P2_GROINK_STRIKE_PASS hits=6 deaths=1 health_start=25.000 health_end=0.000 placement=fixture_pinned
```

## Evidence

- Standalone `tools/p2_groink_strike_test.cpp` (`-std=c++17 -Wall -Wextra -Werror`):
  Bomb applies + dies exactly once, Wind no health + impulse preserved, None/invalid
  no-op, repeated strikes clamp, wildcard sink, exact-token precedence. Exit 0,
  exe sha256 `C99997C7…BF232D`.
- Private fixture build `output/groink-strike-runtime-fixture-01` (status built):
  `fixture.exe` sha256 `07d64b23…122f4c6`.
- Real GL (`--experimental-pikmin2-room`, 960x540) in
  `output/groink-runtime-sessions/0d2aa8c8fb084839b6616aef201fa614` (copy
  `output/groink-strike-session-01`, log sha256 `d1a990bc…1a7fd6`): exit 0, and

```
P2_GROINK_RECEIVER_HIT token=… kind=Bomb damage=10.000 health=15.000
P2_GROINK_RECEIVER_HIT token=… kind=Bomb damage=10.000 health=5.000
P2_GROINK_RECEIVER_HIT token=… kind=Bomb damage=10.000 health=0.000
P2_GROINK_RECEIVER_DEAD token=…          (exactly once)
P2_GROINK_STRIKE_PASS hits=6 deaths=1 health_start=25.000 health_end=0.000 placement=fixture_pinned
```

The existing terrain/volley/live-target gates still pass in the same run
(`P2_GROINK_FLIGHT_PASS`, `P2_GROINK_VOLLEY_PASS`, `P2_GROINK_ATTACK_CYCLES_PASS`,
`P2_GROINK_LIVE_TARGET_PASS`, `PASS GROINK_VOLLEY_RUNTIME`).

## In-flight moving-sweep follow-up (commit 2)

The source processes creature hits on each moving shell step, not only on
termination. `P2GroinkStrikeTracker` now dedups **(shellSlot, targetToken)** so
one shell damages a given candidate at most once per flight while different
shells may each hit it; `clearSlot` forgets a shell on pool recycle. The
live-target fixture snapshots each active shell before `volley.update` and
classifies the previous→current segment through the bridge with `terminal=false`,
sharing the tracker with the terminal path so a duplicate position cannot apply
twice. New markers: `P2_GROINK_FLIGHT_HIT` (Bomb/Wind), `P2_GROINK_FLIGHT_IMPULSE`
(Wind), and `P2_GROINK_FLIGHT_SWEEP_PASS steps=<n> hits=<h> wind=<w>`.

Evidence (native `1ae14480`, fixture `output/groink-flight-strike-fixture-01`,
real GL 960x540, session `output/groink-flight-strike-session-01`, log sha
`c65fe883…1c549`, exit 0):

```
P2_GROINK_RECEIVER_HIT … kind=Bomb damage=10.000 health=15.000 / 5.000 / 0.000
P2_GROINK_RECEIVER_DEAD …                 (exactly once)
P2_GROINK_FLIGHT_SWEEP_PASS steps=90 hits=0 wind=0
P2_GROINK_STRIKE_PASS hits=6 deaths=1 health_start=25.000 health_end=0.000 placement=fixture_pinned
PASS GROINK_VOLLEY_RUNTIME
```

**Honest limit:** the moving-sweep path executes every tick (90 steps) but the
stationary fixture produces **no natural moving hit** (`hits=0 wind=0`); the
trajectory reaches the floor before the pinned Navi, and the terminal pinned
sweep remains the health/death evidence. Moving-step application and the Wind
impulse path are proven in the standalone test, not naturally in this fixture.
A natural moving hit needs a mid-flight Navi placement or a real pursuing actor.

## Fixture baseline note

This is the lane's stationary custom harness (synthetic owner point + baked
`groink_attack.mod`, explicit fire trigger), not a regenerated family room; the
window is 960x540 and the contact is a **fixture-pinned** Navi placement at the
terminal sweep midpoint (`P2_GROINK_STRIKE_PLACEMENT fixture_pinned=1`), not
natural pursuit. Per the fan-out the custom runner supplies its own explicit
starting-squad/window evidence; a full #404 adoption is deferred to the final
lane acceptance once the real actor path lands.

## Remaining (not claimed here)

- **Animated muzzle alignment** — the prototype doc's central caveat: a baked pose
  has no animated `kuti`, so a rotating debug marker is not fidelity; needs an
  angle-aware bake or retained skeletal geometry (#128).
- **Real Groink actor** (MiniHoudai 78 / FminiHoudai 97) registration, locomotion,
  natural pursuit; this remains a host-owned proxy with a wildcard sink.
- **In-flight sweep application** — implemented with per-shell dedup and executes
  every tick, but the stationary fixture produces no natural moving hit; the
  standalone test covers the semantics, and a real pursuing actor is needed for
  natural moving hits.
- **Wind impulse** is carried in the bridge result and logged, but lane 20's
  receiver still has no impulse/knockback representation.
- **Corpse/revival** (#209/#210) and engine receiver wiring (#186) remain open.

## Provenance

Native candidate `opencode/p2-groink-strike` (local-only, not pushed) @
`67298b078cb437fb2074c9e8a5c5a127daf0ee88`, base `6202d852`. Patch:
`native-candidates/groink-strike/0001-*.patch`. Native origin/upstream not
pushed. No maintained checkout or shared build modified.

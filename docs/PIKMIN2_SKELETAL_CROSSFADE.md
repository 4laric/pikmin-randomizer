# Shared skeletal crossfades

Owner: Codex using shared account 4laric. [#409](https://github.com/4laric/pikmin-randomizer/issues/409), parent #128.

`pc_p2_attachments.h` captures the last successful **local TRS** pose of an
instance and blends that snapshot into another clip. Translation and scale use
linear interpolation; rotation uses shortest-path quaternion interpolation.
Weights zero and one preserve the outgoing and ordinary target endpoints.
Corrections apply after blending, followed by hierarchy evaluation. Skinning,
weighted skinning, sockets and attachment volumes share the resulting matrices.
Banks remain immutable. Snapshots are bounded to 128 joints and validated against
their originating instance generation; rebinding or another actor's snapshot fails.

`pc_p2_crossfade.h` provides a per-owner transition coordinator:

```cpp
p2attach::Crossfade transition;
// Once per simulation update, including while offscreen:
transition.advance(deltaSeconds, paused);
// Rendering does not advance elapsed time:
transition.sample(instance, token, targetClip, targetFrame, ownerMatrix,
                  tick, 0.15f, snap);
```

A clip change freezes the last displayed local pose and starts at weight zero.
An interruption captures the current blended pose, avoiding a jump to a raw clip.
The target frame follows the caller's animation clock. Offscreen simulation can
finish an existing transition; a newly observed clip starts from the last displayed
pose. This is a frozen-pose crossfade, not simultaneous playback of two clips.
Repeated draws do not advance time. The caller owns pause policy and must advance
once per simulation update. No event dispatch, root motion or gameplay scheduling
is added. Duration is selected on clip change (zero snaps; finite range 0–10 seconds).

## Snow adoption

Create `p2-snow-crossfade.txt` containing `P2_SNOW_CROSSFADE_1` beside preview
sidecars, or under `assets/` for campaign bindings. Existing interpolation and
skeletal markers and validated skin/joint banks are required. Malformed markers
or enabling without the skeletal path are refused. Defaults are unchanged.

Snow blends between wait, move and attack over **150 ms**. `BTeki::update` advances
its private transition with game delta time, gated by pause/UI overlay. Death,
corpse and flick/recoil entry and exit snap. Forget/reset discards the transition
with its private skeletal instance. Shared Shape geometry and retail assets are
unchanged. Other families can adopt the helper with their own transition policy.

The P1 animator remains authoritative for attack events. This does not replace
Snow's P1 collision/hurtbox scaffold with animated P2 hitboxes; visual blending
does not delay attack events. Broader population/performance and family-specific
adoption remain separate work.

## Validation and reproduction

- `tests/test_pikmin2_crossfade.py` compiles production headers with warnings as
  errors: analytic hierarchy/rotation, weighted skin, endpoints, interruptions,
  duplicate draws, pause, invalid data, corrections, isolation and stale owners.
- `scripts/pikmin2_crossfade_fixture.cpp` uses a real generated Snow actor and
  production draw hook in a fresh hidden 960×720 preview. Real source poses drive
  idle, half-walk, interrupted attack and immediate death. Readback requires
  visible changed pixels and identical duplicate/pause images; vertex/normal
  arrays must match expected skinning within 0.0002.
- `experimental.pikmin2_crossfade_fixture` stages fresh sidecars and asset links
  from a private skeletal stage. It does not copy source saves, economy or logs,
  and checks completed isolated-build provenance before launching.
- The lifecycle fixture uses `pikmin2_skin_fixture.build(..., crossfade=True)`.
  Real combat, death, corpse carrying/delivery and duplicate economy receipts
  passed. It checks exact death/corpse geometry; the dedicated render fixture
  checks transitional geometry. This is P1 gameplay with P2 visuals, not P2 AI parity.

Build production first, then use `scripts.build_pikmin2_fixture` with the exact
native head and fresh output. Run the renderer with:

```powershell
py -3.12 -m experimental.pikmin2_crossfade_fixture --source <private-skeletal-stage> --output <fresh-run> --exe <isolated-build>/fixture.exe
```

Local evidence: `output/crossfade409/` in the engine lane's private root worktree.
Native source `dcb24b90a695c9cc6e4903ab5e875d3324498f24` built successfully.
Production SHA-256:
`a030169cc49d6cb2372f1ff26ca79a1be570d2c0d96337c58aeeab90df139283`.
Renderer fixture SHA-256:
`e964f66b2a34b3475b3adf1e17db8dbad56b4419653787879b1e909e50562e3b`.
Rendered acceptance: 98,495 visible channels, 101,201 changed channels, identical
duplicate/pause images, endpoints/interruption/death checks passed. The 14 focused
tests passed; full suite: **1,392 passed, 23 skipped, 1,052 subtests passed**.
Player launchers, packages and saves are unchanged.

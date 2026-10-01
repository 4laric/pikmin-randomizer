# Shared joint-local corrections (#379)

Codex implementation owner through shared account 4laric. This adds a bounded
per-sample correction stage to `p2attach::Instance`. It does not implement a
particular enemy's aiming policy or execute arbitrary native callbacks.

## API and ordering

`JointCorrection` contains a joint index and affine `delta` matrix. The optional
last arguments of `Instance::sample` are a pointer to corrections and their
count. Existing calls retain their behavior:

```cpp
p2attach::TRS aim;
aim.rotation = {0, std::sin(angle / 2), 0, std::cos(angle / 2)};
p2attach::JointCorrection correction{muzzleJoint, p2attach::matrix(aim)};
bool ok = instance.sample(token, clip, sourceFrame, owner, tick,
                          paused, dead, &correction, 1);
```

For every joint, the order is:

1. Interpolate the source local TRS at the authoritative frame.
2. Compute `correctedLocal = sampledLocal * delta`, if supplied.
3. Compute `world = correctedParentWorld * correctedLocal` (or owner for roots).
4. Commit the entire hierarchy only after all results validate.

This is a **post-local** correction. Descendants inherit it; siblings do not.
Multiple distinct joints may be corrected in any input-list order. Corrections
are supplied anew on each sample, never accumulated into source data or stored
as caller-owned pointers. Omitting them on the next unpaused sample restores
the ordinary source pose. The shared immutable animation bank is untouched.

Both `socket()` and rigid/weighted `p2skin::deform()` consume this committed
hierarchy, so geometry, attachments and joint-bound damage volumes agree.
Their coordinate space is the one selected by `owner`: use identity for the
normal model-space skinning path, then apply the actor transform once when
rendering or placing world attachments. Passing an actor transform to sampling
and applying it again during rendering would double-transform the mesh.

## Failure and lifecycle semantics

At most one correction per joint, bounded by the bank's joint count (128 max).
Null nonempty lists, duplicate/out-of-range indices, nonfinite/unbounded matrices,
and determinants below absolute 1e-12 are rejected. Negative determinants are
allowed; normal transformation retains its existing signed inverse-transpose
contract. Composed hierarchies must also pass finite/range validation. Invalid
samples revoke readiness: neither sockets nor skinning expose partial results.
A subsequent valid sample can recover; a stale owner token cannot mutate the
current owner's pose. Sampling allocates no heap buffers for corrections.

Pause retains the previously committed pose and ignores new corrections; damage
contacts remain disabled. Death invalidates the pose before correction processing.
Reset/rebind invalidates generation tokens. Family code owns whether a corpse
uses a separate live binding/final-frame pose rather than the death-invalidated
attachment instance, as before.

## Evidence and adoption boundary

Production native build passed at `182f64e58a71ee26f5fb8cc15543f5ec88c69db5`
(production change `f807521f`, followed by test-only coverage). Seven focused
tests and eight subtests passed. The compiled contract covers hierarchy,
owner transform, multiple corrections, no accumulation over 100 samples, rigid
and weighted geometry, volume alignment, pause, death, reset, isolation and
malformed/overflowing corrections.

The retail-source probe applies a controlled 45-degree local Y rotation to
Groink's `kuti` joint (13), then compares all 351 frames against the existing
source hierarchy/weighted converter with the same correction. Both mesh data
and full muzzle matrices are checked. Maximum position error is 0.000037933;
normal error is 0.000000667. At attack frame 20, the correction moves geometry
by up to 27.20294 units, proving the test is not only a marker transformation.
Uncorrected Groink (351 frames) and Snow (390 frames) regressions also passed.

Probe SHA-256:
`fb575f8270cf35e3e8f31aa16405f1d8801b80546ee8fff69b0d5bba728dac07`.
Local evidence: `output/corrections379/regressions.log`, `probe-final.log` and
`dump-final.txt`. Set `P2_WEIGHTED_BANK` to the #370 export and run
`tests/test_pikmin2_joint_corrections.py` to include retail comparisons.

This is a controlled CPU test, not live Groink aiming or source callback parity.
Callbacks authored in parent/world space require an explicit coordinate-space
conversion; callbacks that replace transforms or depend on intermediate traversal
state are not automatically equivalent to post-local deltas. Each family owns
that source audit, target policy and gameplay/visual validation. Existing enemy
renderers, player packages and defaults are unchanged.

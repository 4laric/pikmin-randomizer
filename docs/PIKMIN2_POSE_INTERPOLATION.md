# Sampled-pose interpolation foundation (#304)

Codex engine owner, shared GitHub account 4laric; parent #128.

`engine/pc_port/pc_p2_pose_blend.h` provides a renderer-independent primitive for
blending compatible baked position and normal arrays. This batch does **not**
enable smoothing on existing actors or change nearest-pose defaults, event timing,
attacks, attachments or collision. It is not skeletal animation or cross-clip FSM
blending. Source animation players remain authoritative.

`bracket(frames, frame, interval)` accepts one to 256 strictly increasing source
frame indices (0..10000). It finds the two surrounding samples and their fractional
weight, treats exact samples as single endpoints, and clamps outside the sampled
range. Nonfinite input and malformed tables leave output unchanged. It deliberately
does not wrap: the source player owns authored loops, held endpoints and outros.

`blend(left, right, weight, output)` linearly interpolates positions and blends
normalized input normals, then normalizes the result. Exactly cancelling normals
choose the nearer endpoint (left at a tie), so the result never becomes a zero
normal; this can cause a lighting discontinuity. Zero or nonfinite input normals
are refused. Weight must be finite and within 0..1. Positions and normals have
separate counts, each 1..65536; coordinate components are bounded to +/-1000000.
Both input arrays are fully checked even at endpoint weights.

The output is replaced only after successful construction. Refusal preserves it,
including when output aliases an input. One temporary Pose allocates up to 1.5 MiB
of vector payload; input and existing-output storage are additional. Allocation
failure may throw without replacing output. This reference primitive has not been
optimized to reuse scratch storage or profiled as a per-frame draw path.

## Compatibility boundary

```text
py -3.12 -m experimental.pikmin2_pose_compatibility left.mod right.mod --output fresh-directory
```

The audit requires matching chunk order, position/normal counts, direct baked
joint-zero mapping, a single identity root, and byte-identical mesh indices,
material, texture and other resources. Only vector values and finite root bounds
may differ. Bounds must enclose the vertices. Byte/count budgets, duplicate chunks,
truncated data, nonfinite vectors and zero normals are rejected. Output contains
`audit.json` with both hashes and maximum vertex displacement, plus `probe.txt`
for the native test executable. Input models are never modified; existing output
directories are refused.

This is a pair-compatibility audit, **not** a general MOD loader validator. Matching
index buffers cannot establish semantic vertex correspondence: only pair poses
from the same verified source bank. Linear interpolation can shrink rotating limbs
and flatten curved motion. It does not interpolate bones, material animation,
collision joints, bounds or gameplay receivers.

## Validation

Seven focused test methods pass across interpolation, source-clock and blend-player
suites. The new native probe compiles with C++17 and warnings-as-errors. It covers
uneven spacing, exact/terminal samples, invalid tables, weights, count limits,
nonfinite positions, zero/antiparallel normals, endpoint behavior, and output aliasing.
Hermetic MOD tests reject changed resources, topology, root transforms and corrupt
vector metadata. Real-source tests are explicitly skipped when local pairs are absent.

Five local pairs passed compatibility and native array blending at weights
0, 0.25, 0.5, 0.75 and 1. All output normals remain unit length; positions match the
linear reference. This does not measure error against the original skeletal motion.

| Pair | Positions | Normals | Maximum endpoint displacement |
| --- | ---: | ---: | ---: |
| Queen carry 00/01 | 538 | 610 | 1.983 |
| Baby move 00/01 | 125 | 124 | 2.163 |
| KingChappy move1 00/01 | 614 | 614 | 30.630 |
| Kurage wait/move1 | 329 | 329 | 23.464 |
| OniKurage wait/move1 | 329 | 329 | 35.551 |

Pairs come from local bulblax-bank2-run1 and p2-jellyfloat-converted-01. Jellyfloat
cross-clip pairs exercise compatibility only; they are not permission to blend
across gameplay states. Source assets and generated probes remain local.

## Next renderer batch

Use an explicit opt-in display with immutable source poses, per-instance scratch
storage, updated bounds and correct vertex-cache invalidation. Compare multiple
instances, pauses and endpoint holds in native captures before enabling it for
actors. Keep collision and attachment timing explicit; visual interpolation alone
must not advertise interpolated hitboxes. No production executable rebuild or new
native gameplay acceptance is claimed by this header-only foundation.

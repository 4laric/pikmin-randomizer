# Shared animated attachments and damage volumes (#358)

Implementation owner: Codex using shared account 4laric. This opt-in foundation
does not activate new attacks, capture states or collision behavior in existing
playtests. Family owners can adopt it independently of the integration lane.

## Import and representation

`experimental.pikmin2_attachments.bank_text` accepts a BMD, named BCA byte arrays
and explicit source-frame mappings. It emits `P2_ATTACHMENTS_1`: a parent-first
joint table followed by clips containing local translation, quaternion rotation
and positive scale for every joint at every sample. Bounds: 128 joints, 64 clips,
256 samples per clip, 32,768 joint samples total, 4 MiB of text. Duplicate names,
invalid hierarchy, nonfinite values and malformed sample intervals are rejected.
Unsupported local reflections, shear, singular transforms and unsupported joint
ordering fail explicitly. Composing local TRS can still produce global shear;
that is preserved by affine matrix composition.

The first importer consumer is Snow's `kamu` mouth joint. The CLI takes `--iso`,
`--snow` and a fresh `--output`. It verifies BCA hashes and frame mappings against
the rendered Snow bank, and records model, animation, timing and output hashes.
All imported data stays local. The native fixture launcher checks that sidecar
against the actual bank and visual inputs before staging. Native parsing does
not replace this package identity check.

## Runtime contract

The header-only `pc_p2_attachments.h` supplies:

- `read`: bounded parsing into a shared immutable bank.
- `Instance::bind`: validates a bank and returns a fresh nonzero owner token.
- `Instance::sample`: evaluates one authoritative source frame, interpolating
  local translations/scales and shortest-path quaternion rotations, then
  composing the hierarchy with the caller's current owner-to-world matrix.
- `Instance::socket`: queries a named joint's cached full world transform by
  pre-resolved joint index. It is valid only for the matching owner token.
- `DamageVolume::contact`: tests a world-unit sphere centered at a joint-local
  offset against a target point/sphere and filters duplicate receiver tokens.

There is no independent time accumulator. Family code owns clip selection,
looping, attack serials, source callbacks and the authoritative frame. Cache
joint/clip indices at binding; sampling and contacts allocate no heap buffers.
The bank must remain immutable; an Instance holds its lifetime through shared
ownership. Use one Instance and DamageVolume per actor/volume, not a global
volume shared between actors. Receiver tokens must identify an actor generation,
not a pointer that can silently be reused.

**Native ordering matters:** the P1 loop advances animation after drawing.
`pc_p2_snow_clock` returns the current native source frame independently of
visibility. A sample taken after advancement belongs to the upcoming render.
Compare the previously committed sample with the frame just drawn, not with the
newly advanced counter. Family update hooks must sample after animation and
before consuming attachments/contact tests, using the matching owner world
transform. Do not derive gameplay clocks from a last-visible-draw diagnostic.

Pause preserves the last attachment transform and disables damage contacts.
Death is terminal for that binding: attachments become unavailable and damage
is disabled. This foundation's death policy is **release**, not corpse-follow;
family code must release its captured object or remove its prop explicitly.
Reset invalidates the token; rebinding issues a new token. A stale token cannot
read or damage through the new owner. Clock rollback and invalid samples fail
closed until a valid sample is supplied. Wrong-owner requests cannot mutate the
current binding.

Attack windows are `[start, end)` in source-frame units, scoped to one clip.
The caller supplies a monotonically increasing nonzero attack serial; each
receiver generation is accepted once per serial. Up to 64 contacts are retained,
with overflow refused. Radius is explicitly in world units; joint scale/shear
affects the center offset, not the radius. This is a sampled sphere test, not a
swept collision solver. A `true` contact is permission for the caller to dispatch
its native interaction; the helper does not choose damage or override receiver
invulnerability. It records that attempted contact even if the receiver declines.

## Limits and validation

Source-sample endpoints match the existing forward-kinematics calculation for
all 1,560 Snow matrices; maximum observed error is 0.000008382 units. Unit tests
cover rotation, nonuniform hierarchy, isolation, attack windows, duplicate and
overflow handling, pause/death, invalid inputs, reset and stale generations.
The exporter also rejects local reflections, shear and singular scales.

Between samples, joint quaternion interpolation and baked-vertex linear
interpolation are different approximations. They share timing and exact source
endpoints; this does not promise that every intermediate mesh vertex follows
the reconstructed skeleton exactly. Runtime aim/IK callbacks, native capture
ownership and family-specific attack events remain the family owner's work.
Groink's post-sample muzzle aim and Snitchbug's local quarter-turn correction
are examples of transforms to apply explicitly after querying a socket.

The private native demonstration uses a scaled treasure as a translation-only
mouth prop and sends one accepted contact to the native captain damage receiver.
It does not implement a capture AI or P2 attack FSM. Production rendering retains
the existing P1 animation authority; the Snow refactor only exposes the shared
clock calculation already used to choose its rendered pose.

## Accepted native run

Native candidate `2ecd5e66e2c73d11568654ab5964251f087e07eb` (production change
`5972be49e522b307f4d01ba50d3fadf7679d3240` plus test-dump support). Production
build passed. Focused regressions: 20 tests, 53 subtests, including the compiled
native contract and all 1,560 retail source-matrix comparisons.

Fixture SHA-256:
`a447f2438ec7aeae45ddbdd8319b421fb1e499b813f7249cc149472eaef117cc`.
Bank SHA-256:
`ced9eb3cf225358c9c06d8aa33d160f18564948dcf6f22658f6706fb9147d5b8`.
Local evidence:
`output/attachments358/live03/result.json`, with the staged native log and
`attachment-moving.png` under its recorded directory. Native exit was 0.

The native clock/render pair matched the committed prior-boundary sample.
The mouth-owned prop moved, a real native pause held transforms and suppressed
contacts for 30 ticks, and native `InteractAttack` reduced captain health
100 to 99 exactly once. An outside target and duplicate contact were rejected.
An explicit fixture death signal released the prop; reset/rebind invalidated
the old token. This is not a natural enemy-death or capture-FSM test.

Reproduce with `experimental.pikmin2_attachment_fixture build` using `--native`,
`--build-dir`, a fresh `--output` and exact `--head`. Then use its `run` command
with `--exe`, `--assets`, `--converted`, `--pod`, `--snow`, `--bank` and a fresh
`--output`. The bank requires the adjacent `attachments.json` provenance file.
Existing seeds and playtest executables were not modified.

Rejected local live01/live02 runs compared the post-draw advanced counter with
the preceding draw. Their logs are retained; live03 verifies the actual update
ordering instead. The original bank output used platform newline conversion;
bank02 uses explicit ASCII bytes so the recorded hash matches the written file.

Shared correction stage: [joint-local corrections](PIKMIN2_JOINT_CORRECTIONS.md)
can now be supplied to the attachment player before hierarchy composition.
Family source callback semantics still require an explicit audit.

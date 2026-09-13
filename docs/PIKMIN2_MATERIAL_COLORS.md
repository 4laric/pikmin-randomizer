# BRK animated material colors

Codex implementation owner using shared account 4laric.
[#423](https://github.com/4laric/pikmin-randomizer/issues/423), parent #128.

This adds BRK/TRK1 color curves alongside the existing BTK texture-transform
support. The importer and sampler cover signed TEV color registers and unsigned
konst colors. An explicit native binding applies every target for one model draw,
then restores shared material values and clears the material cache. No enemy,
player package or material is automatically opted in.

## Source import

```powershell
py -3.12 -m experimental.pikmin2_material_color --source <local.brk> --output <fresh-directory>
```

Output: `material-color.json` and `material-color.txt`, both carrying the source
SHA-256. Keep source bytes and generated banks local. Package owners must include
these files in their own manifest verification; a source hash is provenance, not
authentication of an edited text bank.

Supported: one `J3D1brk1`/`TRK1` block, playback attribute 0 or 2, duration
1–32767, up to 128 material/register tracks, 4096 keys per curve and 65536 active
keys total. Files/native text banks are bounded to 4 MiB. Names, offsets, counts,
register IDs, channel arrays, tangent modes and monotonic key times are validated.
Unknown playback modes and unsupported register IDs are refused. Remap ordinals
are not interpreted as host material indices. Zero-key channels become constant
zero; single-key and both shared/independent tangent formats are supported.

Source audit anchors in the read-only Pikmin 2 checkout:
`J3DAnmTevRegKey.h` describes TRK1 offsets; `J3DMaterialAttach.cpp` uses byte 24 of
each track as the register ID; `J3DAnimation.cpp::getTevColorReg/getTevKonstReg`
defines channel sampling. Multi-key curves use Hermite interpolation, truncate
toward zero and clamp to -1024…1023 or 0…255 respectively. Constant channels
bypass interpolation clamps: signed16 is retained for CReg; konst assignment
wraps to unsigned8. Host double-precision curve evaluation is not claimed to be
bit-identical to every retail floating-point boundary.

The caller owns looping, pause, seek and terminal-frame policy. The sampler
accepts `[0,duration]` and does not advance time. Use the actor's authoritative
source frame. Failed samples leave their output untouched.

## Binding

```cpp
auto bank = p2color::read(stream); // Keep validated bank immutable and alive.
p2color::Binding binding;
// source name, source kind (0=CReg, 1=konst), source register,
// converted host material index, host register:
std::vector<p2color::Target> targets = {{"body", 0, 0, bodyIndex, 0}};
binding.bind(bank, shape, targets, sceneGeneration);
// After shape.updateAnim, on the draw thread:
binding.draw(bank, shape, gfx, actorSourceFrame, sceneGeneration);
// Before bank/model teardown or replacement:
binding.reset();
```

Supported host storage is PVW TEV registers 0–2 and konst registers 0–3. The
binding validates complete source-track coverage, destination uniqueness,
material storage, bank/shape identity and generation. Multiple registers may
target one material; one track may target several explicitly mapped materials.
Aliased TEV storage across different materials is refused, including unbound
materials. Draw rechecks storage identities before dereferencing retained state.
A scene owner must advance its nonzero generation before addresses can be reused.

All samples are computed before mutation. Bounded stack scopes restore every
register on return or exception. Multiple actors can use different phases against
one model without retaining the preceding actor's colors. Do not mutate the bank
or free model storage while a binding is live.

The converter/family owner must prove that the host material actually consumes
the selected register. A storage binding cannot establish visual equivalence:
Snow's ordinary combiner, for example, ignores the C0 register used by Crawbster's
BRK. This feature does not rewrite arbitrary J3D TEV graphs. Automatic family
adoption, BTP texture-pattern animation and combined BTK/BRK one-draw binding sets
remain separate work; do not draw the entire model once per animation track.

## Validation

The local Segmented Crawbster `dangomushi.brk` imports a 32-frame body/CReg0 track.
Source SHA-256: `3fe88a7ccc1b0d34c93519a902e05c3bd868d5138af1b82d150312b068da1608`.
All 33 integer frames match an independent Python Hermite/clamp oracle. Tests also
cover malformed source, konst import, signed/unsigned clamping, constant wrapping,
simultaneous register kinds, independent actor phases, aliases, invalid draws,
exception restoration, reset and incomplete bindings.

Focused tests: **16 passed, 377 subtests**. Full suite: **1,404 passed, 23 expected
skips, 1,052 subtests**. Native production source:
`1ec688716c450fbbd1910b1290b86303c137a662`; Windows build SHA-256:
`3c20f5132cf60471bff96016077c52fe7d60b6b52c91bfbcfa456b1b817adf97`.

`experimental.pikmin2_material_color_fixture` builds a hidden exact-head renderer
fixture. It applies the real BRK to a Snow model with an explicitly configured
diagnostic `texture * C0` combiner. It requires visible color change, identical
same-frame replay, restored register values and identical ordinary draws before
and after animation. This tests the shared renderer, **not Crawbster material
parity or completed family adoption**. Local evidence and final fixture hashes
are recorded under `output/color423/` and in #423.

The corrected diagnostic renderer passed: 277,011 changed channels, identical
same-frame replay and identical ordinary draws before/after. Captures were
inspected. Fixture SHA-256:
`f897ff14a59ab53026d179f9b15617e4fc20884c963e5a9b67e615a0a859f3fd`.
The first attempt correctly found no visible animation on Snow's unmodified
combiner; it did not consume the selected register. Only the diagnostic fixture
was changed to consume C0, not any production family material.

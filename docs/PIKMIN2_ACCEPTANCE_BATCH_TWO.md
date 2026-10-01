# Frozen P2 source-delivery batch two #1142

Implementation owner: Codex through shared GitHub account `4laric`.

This second batch combines accepted captain #1130, surface water #1124 and cave
continuation #1127 source. Co-op is outside this batch. Source delivery and
compiler/test validation do not establish current combined runtime or human
acceptance. Fresh current-source runtime acceptance is now complete; snapshot PR delivery is recorded separately after actual merge.

The clean private native source is
`38b19c5f6bef44954319cc69769ee44f9e4aa7c8`, in
`output/native-p2-acceptance-batch-two`. The private root export worktree is
`output/root-p2-acceptance-batch-two`, based on
`e388dabe272967f8ccb72979761ca7d0b53cedcf`. Native #114 was actually merged as
`62a994966cfbb2ff62fc34848cbe0b2c35968c18` and combined with accepted captain/water
main `07bac45d1f7a18b608e742fabfccc282d4d25e44`. The original reviewed producer
handoffs retain their own narrower source and runtime identities.

The first wave's source `9a76a11d9d65529690237e2ed55344302cb29b13`, landed root
`87e820d9c2855ec3894ccd7ad5b6730d406ffed7`, documentation and immutable
cave/White/journal receipts are preserved. See
[the first wave](PIKMIN2_ACCEPTANCE_WAVE_1131.md). Its generated-delivery manual
companion remains in the combined source; its first-wave runtime results are not
relabeled as second-batch runtime results.

## Actual private build and source export

The production build uses the exclusively owned
`output/native-p2-acceptance-batch-two-build` directory with Release, Ninja,
MSYS GCC, optimization and IPO enabled, JAudio disabled and the canonical fixture
guard header. The recorded preflight contains 4,103 source/tool input hashes;
independent review verified every hash unchanged. The build completed and the
recorded Ninja dry run reports `ninja: no work to do.`

The Windows production executable SHA256 is
`543c16910a923f8f0b178f2592dbbb1e74d6f5c3d517864358b3a722956e6a53`.
Its certificate is `output/p2-acceptance-batch-two/build-result01.json`, SHA256
`4f4b50780887cfe4b176d95dd51c9c747c76e36208ca267b288278a23f17bcd3`.
The certificate's preliminary `export_complete:false` is preserved; the later
actual export receipt records the completed source copy. Fresh runtime results are recorded below.

The actual export copies 4,036 tracked source/build-resource files byte-for-byte
and retains six separately inventoried historical root dependencies unchanged.
Independent review checked source and target hashes and the complete engine file
set, with no missing or extra files. Extracted assets, saves, logs and build
outputs are outside the snapshot. Native dirty state is empty.

Export evidence: `output/p2-acceptance-batch-two/export01/export.json`, SHA256
`3c30cf585166bae2080ac9869f1586e15405abb7d2921d958328a1af342a355b`.
Independent byte/input verification:
`output/p2-acceptance-batch-two/reviews/independent-build-export-bytecheck01.json`,
SHA256 `587b6bb5f741d22eca0f3b2db0233e7b8cf09b8b9f76ca7b1a397246b6e49282`.

## Actual Linux validation

Private Actions run
[36901634036](https://github.com/4laric/game-build-ci/actions/runs/36901634036)
completed successfully using both explicit source pins: root `e388dabe` and
native `38b19c5f`. Read-only inspection of the actual CCX job checked both full
Git HEADs, the build logs and executable bytes, CTest output and no-work log.

All 243 CTests passed, with no skips. All 251 actual executable link rules use
`-flto=4` as the final LTO flag and the link pool of depth 1. The Linux executable
has 13,688,376 bytes and SHA256
`a4e3174e5632cf6042215ad37a9cbd45f023cfbce2e0a3d05d966c5796f98069`.
Linux and Windows executable hashes identify separate platform artifacts.

The immutable independent build/export/CCX review is
`output/p2-acceptance-batch-two/reviews/independent-build-export-CCX-review01.json`,
SHA256 `83e51ac587f4609df34ae4244f4ddae36df04e390ece9bf24e898af052d31a2c`.
This result validates the explicit native checkout and root tooling; it is not
CI for a later committed root engine snapshot and is not Windows gameplay proof.

## Initial source freeze and focused checks

The initial engine/documentation snapshot was frozen at root
`544ecc45f2e8ff40233748456d139e4b8a1f33f4`, with native source unchanged at
`38b19c5f6bef44954319cc69769ee44f9e4aa7c8`. This source identity is the clean
runtime preflight baseline; a later evidence/documentation commit must retain
its own distinct identity.

All43 affected Python checks passed in1.384 seconds. The recorded command covers
second-captain campaign/native contracts, surface-water runtime contracts, cave
journey, fixture captain guard, squad, runner and build modules. Evidence:
`output/p2-acceptance-batch-two/focused-tests01.json`. These focused contract
checks do not establish in-engine runtime or human gameplay acceptance.

## Fresh current-source runtime acceptance

All 17 orchestration commands passed on clean root source freeze
`544ecc45f2e8ff40233748456d139e4b8a1f33f4` and the exact native source above.
The final documentation commit changes only this report and ENGINE_SOURCE.md;
the runtime consumer and engine source bytes remain fixed. Each of the three
replacement-main companions has fresh built provenance for native38, executable
hashes, complete input hashes and Ninja no-work evidence.

The captain fixture created one real native campaign card through the ordinary
SDL pause/Sunset/results path, then loaded it twice. Raw exits were 0 in 56.640,
25.360 and 25.281 seconds. Day 3, native population 20, the committed card bytes,
inventory and checked locations remained conserved on both loads. Its geometry
is the original P1 campaign scene with opted-in P2 captain code. Active, inactive,
null-state and missing-manager controls each produced raw86 without PASS.

Water round-trip and species probes produced raw0 in 12.719 and 15.156 seconds.
All 5,332 faces and three volumes retained their source geometry. The staged
19-Red/1-Blue probe observed Red drowning, Blue wet without drowning and ordinary
whistle return to dry ground with the Red timer reset. Live population remained
20. The paused/movie captain-down control produced raw86 in 0.922 seconds.
Species staging is deliberate; this does not prove natural Blue acquisition or
P2 retail body geometry/rendering.

The cave's actual floor-one native boundary returned raw42, and the ordinary
supervisor launched generated floor two, which returned raw0. The incoming live
squad was 15 Reds and 5 Blues with health and maturity conserved; five source
bud uses became zero destination uses. A separate supervisor interruption
returned raw73 after actual native42 but before atomic transfer commit. A fresh
resume recovered that pending transfer once and completed floor two with raw0.
The initialized captain-down control returned raw86 in 0.891 seconds. Standalone
restart/concurrent-parent exclusion remains producer historical evidence; those
cases were not repeated here. This is the staged CLI boundary scaffold, not a
complete in-game entrance or campaign journey.

Every native child used external 60-second supervision, current starting-Pikmin
overlay, native Red identity 1, centered 960×540 startup and initialized captain
guards. All logged child runs finished before the limit. The previously built
geometry generator is an explicitly hashed historical geometry input, not a
current-native production executable.

Runtime evidence: `output/p2-acceptance-batch-two/runtime01/assessment.json`,
SHA256 `b175a630dd55bd2ee94e323b86b0162c83a52219e6df304edbbdf171314cafb0`.
It binds current source, helper, fixture/provenance, logs and raw results.

## Delivery and remaining acceptance

The exact final root snapshot receives independent source/runtime review and
its own PR CI before merge. The integration lead verifies all 4,042 landed
engine files and records separate immutable supported captain #1130, water
#1124 and cave #1127 receipts after actual delivery. Those receipts release
source ownership; downstream consumers still verify their dependency behavior.

Human gameplay and game feel remain untested. Full P2 family/campaign acceptance,
complete cave floor progression, bridge travel and visual water validation,
physical placement relocation, mixed-mechanic play and online co-op remain open.

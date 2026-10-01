# Frozen P2 source-delivery batch two #1142

Implementation owner: Codex through shared GitHub account `4laric`.

This second batch combines accepted captain #1130, surface water #1124 and cave
continuation #1127 source. Co-op is outside this batch. Source delivery and
compiler/test validation do not establish current combined runtime or human
acceptance. Those checks remain pending at this initial documentation freeze.

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
guard header. The recorded preflight contains4103 source/tool input hashes;
independent review verified every hash unchanged. The build completed and the
recorded Ninja dry run reports `ninja: no work to do.`

The Windows production executable SHA256 is
`543c16910a923f8f0b178f2592dbbb1e74d6f5c3d517864358b3a722956e6a53`.
Its certificate is `output/p2-acceptance-batch-two/build-result01.json`, SHA256
`4f4b50780887cfe4b176d95dd51c9c747c76e36208ca267b288278a23f17bcd3`.
The certificate's preliminary `export_complete:false` is preserved; the later
actual export receipt records the completed source copy. Runtime remains pending.

The actual export copies4036 tracked source/build-resource files byte-for-byte
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

All243 CTests passed, with no skips. All251 actual executable link rules use
`-flto=4` as the final LTO flag and the link pool of depth1. The Linux executable
has13688376 bytes and SHA256
`a4e3174e5632cf6042215ad37a9cbd45f023cfbce2e0a3d05d966c5796f98069`.
Linux and Windows executable hashes identify separate platform artifacts.

The immutable independent build/export/CCX review is
`output/p2-acceptance-batch-two/reviews/independent-build-export-CCX-review01.json`,
SHA256 `83e51ac587f4609df34ae4244f4ddae36df04e390ece9bf24e898af052d31a2c`.
This result validates the explicit native checkout and root tooling; it is not
CI for a later committed root engine snapshot and is not Windows gameplay proof.

## Pending current runtime and delivery acceptance

Current-source captain save/load, water FSM and cave transfer/recovery fixtures
still require their own completed private builds, exact provenance, fresh native
20-Pikmin scenes, centered960x540 startup, canonical captain guards and bounded
60-second runs with initialized negative controls. Their producer-only historical
runs do not substitute for this combined-source acceptance.

Affected root checks, final current-source/runtime review, exact-head root snapshot
PR CI and merge, landed byte verification and genuine per-producer integration
receipts remain pending. This initial document supports a frozen source commit
for clean runtime preflight; it does not complete issue #1142 or release ownership.

Human gameplay and game feel remain untested. Full P2 family/campaign acceptance,
complete cave floor progression, bridge travel and visual water validation,
physical placement relocation, mixed-mechanic play and online co-op remain open.

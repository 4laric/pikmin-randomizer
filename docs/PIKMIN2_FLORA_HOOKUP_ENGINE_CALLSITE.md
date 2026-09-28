# Flora hookup engine callsite (#723)

Lane `flora-hookup-engine-callsite-native`, issue #723. Owner: Codex through
shared account `4laric`. This lane lands the integrated-but-unlanded #697
flora converter on the maintained line and implements its engine hookup
bridge. Owns only the ported converter, the new bridge, the guarded fixture,
the build helper, this doc, the observer and its tests. No shared edits.

## Ported converter (verbatim from #697 native 926109f2)

- `pc_port/pc_p2_flora_convert.h` blob `b73cfe4974f2bf5fb780cd8d7fd2096846cb88ec`,
  `pc_port/pc_p2_flora_convert.cpp` blob
  `59b3f4f45b93005720b2168d8b6e8281702fa4fb`, onto maintained base `a95040b6`
  (verified absent there before the port). No edits.
- M1 Candypop/Pelplant conversion policy (ip01=5, ip11=1 queen budget,
  ip13=9 queen multiplier, own-colour refund) plus M2 scenery registry.
  Engine-free; the shared-engine hook seams stay #171/#186 review surface.

## New bridge (`pc_p2_flora_hookup.{h,cpp}`)

Engine-free driver for the converter from live facts: fail-closed admission
(species/swallow/Piki-kind bounds), conversion, per-sprout receiver routing
with markers, and scenery binding with markers. `p2_flora_hookup_suite()`
runs a fixed live-facts session (BluePom 3, queen 1, Pelplant 5, one scenery
bind) with refusal cases.

## Fixture and proof

`tools/p2_flora_hookup_fixture.cpp` (replacement-main) links the converter +
bridge into the engine graph, boots the 960x540 centred window, runs the
conversion/scenery suites plus the bridge session, and prints PASS. Markers:
`P2_FLORA_HOOKUP_{ADMIT,CONVERT,SPROUT,SCENERY,DONE}` plus
`PASS P2_FLORA_HOOKUP_RUN suites=3`, with no `P2_FIXTURE_CAPTAIN_DOWN`.

## Captain safety #632

The fixture vendors the canonical guard verbatim (`scripts/p2_fixture_captain_guard.h`
sha256 `d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`),
proven by the `--guard-self-test` and `--guard-negative-test` modes (negative
exits 86 BLOCKED with no PASS). No game world is booted; no blanket
invincibility; no fake guard provider.

## Serialized follow-on (NOT this lane)

The `native/pc_port/pc_bbft.cpp` per-tick call and the `native/CMakeLists.txt`
`pikmin_pc` membership stay with `challenge-runtime-bridge-port-native`
(#722, done gen 2) and are NOT touched here. Land them only as a separate
bounded integration step under #723 with #171 owner + #186 hook review. Native commits, executable SHA-256, hook log
SHA-256 and `ninja -n` dry run are recorded in the handoff.

## Gates

All six runtime gates UNTESTED (bridge proof, not gameplay).

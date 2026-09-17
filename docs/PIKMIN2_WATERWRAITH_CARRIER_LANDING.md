# Waterwraith99 placement/bind carrier landing record (issue #657)

Recovery producer for exhausted provider-placement-catalog request 1f85c9b6.
Owner: Codex through shared account 4laric. Root-only tooling slice: no
provider/shared-file content edits beyond carrying exact producer bytes, no
builds, no runtime, no ADMIT. All six arena gates UNTESTED. Captain safety
#632 not applicable (zero runtime runs).

## Exact carrier pins (from #644 decision record)

- Root catalog: `randomizer/p2_placement_catalog.py` (+151,
  `WATERWRAITH_CANDIDATE_SPEC`, slot 568677317) in `7a21ce6a`
  ("enemy-waterwraith99-placement-provider ... (#575)"), blob
  `96ddeb89b11e678de1365856db3f5317cc6e5258`.
- Root packaging/bind: `experimental/pikmin2_muse_packaging.py` (BlackMan99 +
  owned Tyre98 sidecar) in `04d58d33`
  ("waterwraith99-packaging-provider ... (#576)"), blob
  `7f45258825a3dfa0cb7f8dc2cc9b53f91627528e`.
- Native bind (RECORDED ONLY, never merged by this slice): `e2aa476e`
  ("enemy-waterwraith99-placement-provider: native 99 bind arm + engine-free
  test (#575)"): `pc_port/pc_p2_generated_placement.cpp`
  (`1cf80986f5725425b704f7c95af191734e14346a`),
  `pc_port/pc_p2_generated_placement.h`
  (`1a58c002b9a379f779c021ace09e3577f91219b7`),
  `tools/p2_waterwraith_placement_provider_test.cpp`
  (`886857fa3a3eacace4367f3f80ac6d923678ed95`).

## Candidate branch

`codex/autofill-carrier-landing` from base
`36b868391e62cccf37d992aa2f796f3cc9c6dc31`:
`36b86839` -> `60c04608` (`cherry-pick -x 7a21ce6a`) ->
`a39af554` (`cherry-pick -x 04d58d33`).

Conflict decisions (exact, no silent resolution): BOTH cherry-picks hit
`DU` (deleted-by-us) conflicts because the files exist at the carriers'
shared parent `5486ae84` but are ABSENT at base `36b86839`. Each was resolved
with `checkout --theirs` (exact producer bytes, nothing hand-edited) and
verified blob-identical to the producer pins (`96ddeb89`, `7f452588`). The
-x linkage preserves the producer commits. No other file was touched.

## Present/absent facts

- At base `36b86839`: all carrier files ABSENT.
- At candidate HEAD `a39af554`: all six root files present at exact producer
  bytes (verified `rev-parse HEAD:<path>`).
- At canonical HEAD `ecf5f53a`: catalog and packaging ABSENT.
- At content line `3a6b34e3`: catalog and packaging ABSENT.
- Wave line: catalog PRESENT via `f353e8d1` ("p2-main-review: merge #575
  Waterwraith99 placement provider"; markers `WATERWRAITH_CANDIDATE_SPEC` +
  slot `568677317` present in a larger 36KB file); packaging PRESENT at
  byte-identical blob `7f452588`; native bind PRESENT via ancestry of
  `e2aa476e` in native-wave HEAD. **All three carriers are already integrated
  on the wave line**, so this candidate branch is a verification vehicle, not
  a needed merge - unless the integrator wants the same bytes on the content
  line, which is a separate integrator decision.

## Dependency finding (for the integrator)

The catalog module does `from . import p2_placement`, and
`randomizer/p2_placement.py` (introduced by `62b217a5`, #440 placement
schema) exists at the carrier parent `5486ae84` and on the wave line but is
ABSENT at base `36b86839` and canonical HEAD `ecf5f53a`. The carried provider
tests therefore cannot import on a bare base checkout; the landing must also
bring `p2_placement.py` (or the consumer must already have it). The carried
provider tests were NOT green on the candidate branch for exactly this
reason; the new focused tests below are hermetic and green.

## Downstream consumers

#572 (blocked gen3 rev7, consumes claim-arm/BIRTH decision plus these
carriers), recovery `1f85c9b6` + publication reviewer, #575/#576 providers
(done; awaiting integration landing).

## Helpers + tests

`experimental/pikmin2_waterwraith_carrier_landing.py`: additive stdlib-only
presence/ancestry/consistency checks failing closed on missing/divergent pins.
`tests/test_pikmin2_waterwraith_carrier_landing.py`: 7 focused tests (+6
subtests), synthetic fixtures only, green under pytest and unittest discover.
No runtime claim; the native pin is recorded, never merged.

# Height-bounded cargo ground contact (#365)

Codex, using shared account 4laric, corrected the donor-pellet transport stall
preserved in #361/PR362. The source donutswhite position, model, route links,
geometry, value 230, weight 15 and slots 25 remain unchanged. First delivery
and a fresh-process rehaul now pass on the corrected build. This is still
source visual/economy transport on donor physics, not authentic donut physics
or campaign authorization.

## Established cause and correction

`DynCreature::simulate` projected each rotated collision particle onto the
highest positive-Y map face, regardless of its height. At native particle
(175.729,29.726,-14.110), that query returned 119.781 instead of the underlying
20.5 platform: false penetration 90.065. Other samples returned 110–119 for
particles at Y32–55. Its deep-penetration branch replaced the contact normal
with a radial vector toward the pellet center and could push position up to
30 units per frame. Native logs showed large position jumps while the leader
had valid route 6,4,3,0 and 20 carriers supplied positive movement commands.

The fix uses a matched static triangle/height query below
`body Y + half cylinder height`, the existing deep-penetration threshold.
Eligibility is captured before particle ground flags reset and requires an
imported preview cargo, Purple/P2 preview support, current grounding, nonzero
pick offset, sufficient Piki carry strength, and established static-map
contact without a platform. Ordinary actors, unlifted/airborne cargo and
platform contact retain legacy queries. No candidate means no particle
contact; it does not invent floor Y0. Returned normals must be finite, unit
length and positive Y. Native movement, gravity, rotation, routes, walls and
`traceMove` remain active. This changes the artificial overhead-floor
correction; it does not grant permission to climb tall walls or move actors.

The previous replay position near (219,32) was described using native ground
readback 0. That value can be the old query's no-ground fallback: the actual
source query has no surface at that exact point. It is not evidence of a real
lower floor there.

## Actual validation

Native frozen head: `e0418c798e808bd1b29217532ebb36f4f0d89406`, based on
`d69580fa7f5441286e82b065b3e36d2bc5066cf4`, in the private
`output/native-beasts-donut-fix` worktree. Its private `build-donut` completed
591 steps with native audio enabled, test hooks disabled and IPO disabled.
Five changed native files, including the compiled policy test, are exported
under `engine/`. The shared native checkout/build was not changed.

All paths below are private `output/donut365` in `output/p2-beasts-donut-fix`.

- Baseline motion `runs/180854b2baaa4ea0863697585aed5d43` and particle
  `runs/0d3c2dbb445f421d8e2141c40f2361ed` diagnostics timed out at 60 seconds;
  their logs preserve the causal evidence. #361 outputs remain untouched.
- Fixed first `fixed-runs/6f8b688466ac4ca4815b87048b9be84e`: PASS, 37 cargo
  trace points, peak20 carriers, exact230 receipt/new1 then duplicate/new0,
  native ledger reopen count1, unchanged repairs and no descent.
- Fresh-process replay `fixed-runs/ef3b36163c1943cda483250b35f7f23b`: PASS,
  38 trace points, peak20, actual delivery/new0 and duplicate/new0. The copied
  ledger remains exactly230, SHA256
  `54c269c8bfd73e9504893700cc74dfe9b7d71ab982c6ccdbe9eaa2e208647e1d`.
- Both used `fixed-linked/fixture.exe`, SHA256
  `4fa55f9275a0c895b5d16b55effe0aad5397543100bab92720dafa4f0fdcbc86`.
- Green regression `green-runs/0ca10a9ffffe4792a3abb3e5432308cb`: PASS,
  36 points, peak20, actual two source seams, exact150 receipt and duplicate
  suppression, unchanged repairs. This uses its own external fixture linked
  against the same native build.

Both donut launches additionally assert eight actual source queries:
overlapping119.781/20.5 selects20.5; a ceiling below20.5 finds no surface;
a descending slope selects12.75370; a ceiling below that finds none; void
coordinates remain absent; actual lower floor0 remains present. The separate
radius5 wall trace ends on the blocking side at signed distance5.00001,
not at the free-motion endpoint. This is a wall collision control, not a claim
that the source donut radius50 footprint was tested.

The compiled policy test covers all64 eligibility combinations, finite/unit
normal and boundary selection, wall/downward rejection, and inherited uphill
velocity behavior. Python validation:11 tests and66 subtests passed. Independent
read-only review found no code blocker and verified first/replay input, log,
executable, receipt and economy hashes, including the query and wall controls.

## Reproduction and limits

Use the unchanged `pikmin2_beasts_floor3_donut_runtime.stage` with source
#357 `haul.json`, frozen floor3 package/assembly and caller diagnostic token.
Generate the corrected external fixture with
`pikmin2_beasts_donut_ground.fixture`, link it through
`scripts.build_pikmin2_fixture` against the clean native head above, then use
`pikmin2_beasts_donut_ground.run`. Replay staging requires the exact first
run's `p2-economy.txt`. `ground-acceptance.json` supplements the unchanged
baseline haul acceptance with #365 source query and wall evidence.
`baseline_fixture` reconstructs a read-only particle/motion observer for the
old build; the originally captured diagnostic executables and logs remain
separate immutable evidence.

No cargo teleport, source-anchor change, route repair or carrier position
forcing occurs. Controller following and initial Transport assignment remain
explicit engineering interventions. Measured donor radius20/cylinder14/scale1
still differs from source radius50/height5. Other actors, complete floor3
content, campaign reward acceptance and successful descent remain outside
this milestone. Two corrected launches establish the tested first/replay
case; broader terrain and manual gameplay acceptance remain open.

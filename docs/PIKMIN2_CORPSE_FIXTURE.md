# Corpse fixture lifecycle (#253)

Owner: Codex using shared GitHub account 4laric. This batch follows
[Atlas PR #254](https://github.com/4laric/pikmin-randomizer/pull/254) on the
dependent branch `codex/p2-cave-corpse253`. It changes the standalone test
fixture and evidence runner; production gameplay sources are unchanged.

## Diagnosis

The original P1 scaffold control left the captain across the room after the
treasure haul, assigned Pikmin to attack the Dwarf Bulborb remotely, then waited
for its corpse. `isAlive()` becomes false when the death animation starts.
`TaiDyingAction::act` calls `die()` only when that animation finishes;
`BTeki::dieSoon` then calls `PelletView::becomePellet`.

The missing-corpse failure reproduces on both the Atlas candidate and unchanged
gameplay baseline `2c08d6b8`. Continuous observation found no earlier matching
corpse. A baseline trace shows the death-animation counter stuck at **87.533**
at frames 1050, 1200 and 1350, with `grid_culled=1`, `culled=1`, `frozen=0`,
`dead_state=0`, `ai_state=0`, `motion=0`, and no bound pellet. This matches the
early return in `Creature::update` before animation/AI when camera and spatial
grid culling both apply. The run then fails the original corpse timeout.

This establishes the failure mechanism in the scripted control. It does not
establish a new natural-gameplay defect or justify changing generic culling.
Moving the fixture captain close through ordinary controller input keeps this
combat in the active area without forcing a death, corpse, reward or position.

## Change and acceptance

`--p1-control` now stages `p2-corpse-lifecycle.txt` with value `1`. The fixture
observes the initial Teki pointer and generator, death, matching PelletView
birth, state transitions, maximum XZ distance, goal target and manager removal
before its phase/UI gates. It stops dereferencing the observed enemy after
removal and scans the pellet manager instead of dereferencing a removed pellet.
The scripted enemy must match the observed identity.

After treasure delivery, the fixture walks the captain within 120 units of the
enemy using the existing controller transform, then assigns combat as before.
All existing ground, movement, repairs, treasure, native combat, corpse route
and Onion delivery requirements remain. The runner additionally rejects missing
or duplicate lifecycle events, changed identities, invalid order, absent goal,
nonfinite/short routes and missing controller approach. Thus an old executable
cannot satisfy the updated control by printing the former final PASS alone.

`--corpse-observe-only` stages value `0`: observe the original distant control
without approaching. Other fixture callers without the marker retain their
existing behavior. This is still a synthetic transport/combat regression,
not natural-play or campaign sign-off.

## Provenance and reproduction

Private root: `C:/Users/alari/pikmin-randomizer/output/p2-cave-lane`.
Private native: `../native-cave-lane`, final native commit
`0c42821d7e31132ef4bcb36ac3afc8eac26c3a71`, parent Atlas commit
`839c9f5ae0ed0dfc75d64b0054b07de4a9aaa20b`.
Separate baseline: `../native-cave-baseline253`, gameplay `2c08d6b8`, with
only this fixture file overlaid. Both builds use Release, MinGW, native JAudio,
IPO off and randomizer test hooks off. Fixture linking verifies fresh Ninja
objects before and after and records input hashes in `provenance.json`.

From the private root (the `--root` below is read-only prepared asset input):

```powershell
python -m scripts.test_pikmin2_atlas_slope --root ../.. `
  --assets C:/Users/alari/bbft/dist/cohesion/pikmin/assets `
  --output output/corpse253-repro `
  --exe output/corpse253-final/candidate-linked/fixture.exe --p1-control
```

Use the baseline-linked executable for baseline comparison; append
`--corpse-observe-only` to reproduce the distant control. Every invocation
creates a fresh UUID runtime directory and records executable/log SHA256.
The runner uses silent SDL audio and touches no prior run or shared save.

Decisive diagnosis evidence, relative to the private root:

| Run | Result |
| --- | --- |
| `output/corpse253-observe/candidate-repeat/dc1b41390276448c8b70b63287ffb908` | Missing corpse; no earlier birth |
| `output/corpse253-observe/candidate-repeat/1b4f0caad2524735a44374f727016c00` | Same failure |
| `output/corpse253-pending/baseline/d2a33a3907e84abaacd910db713b57df` | Unchanged gameplay reproduces timeout |
| `output/corpse253-approach/baseline-distant/2683f4e8f1384c708b3ab174d0f4e5e7` | Frozen animation/culling trace and timeout |

The decisive animation trace executable SHA256 is
`51f627b7dabd2e58c87476e7b9cac7e12e8627b9e104a86efe1480a6c95f4ae8`;
its log SHA256 is
`6ebcd320a95724af807df75f725d3e3a72e51845bab42ff49ad118b208ec7ff6`.

All intermediate diagnosis runs are retained, including passing distant runs.
Two intermediate runs (`corpse253-pending/candidate/dc13404fe85140f7ba6754e1bcadc53b`
and `corpse253-pending/baseline/ef5fc2eaaa284453a5eb71f7743405f4`) exited
4294967295 without a final fixture verdict; they are inconclusive, not passes
or established corpse timeouts. Two `corpse253-animation` runs launched after
the runner gained the approach flag but used the earlier observer-only binary;
their `corpse_controller_approach` metadata records requested mode, not an
executed approach. They are not approach acceptance evidence. The final runner
requires the actual approach event and full lifecycle to prevent this mismatch.

## Final validation

26 focused tests passed: corpse evidence (including negative cases), Atlas
evidence, source cargo instrumentation, fixture linker, Kogane instrumentation,
compiled cargo movement gating and compiled uphill velocity behavior.

All final runtime checks passed with full evidence validation:

| Runtime under `output/corpse253-final/` | Corpse distance / receipt |
| --- | --- |
| `candidate/a912b3fcc52b4b54bdb96ef51a237254` | 399.28 units; native Onion removal |
| `candidate/631d61fc49b64ac394840d526f5cdc09` | 398.87 units; native Onion removal |
| `baseline/d279f80615da4217a843ad4ab1d46685` | 399.39 units; native Onion removal |
| `baseline/c0a8100754dc428fa31166e6807abdd5` | 398.82 units; native Onion removal |
| `atlas/84c781df67f244b0b25f52bc24d99550` | Source `(0,10,640)`, continuous lift, one 200-Poko receipt |

Final candidate fixture SHA256:
`a12dd5682d3bf28ce44d788da79c3de20e93ae2d21ac52a3de19030938363da1`.
Final baseline fixture SHA256:
`200982882930678e8d63eaafb7e895a80b6ecdb6ca9e38a17e522774a31259f0`.
Each runtime's `evidence.json` records the log hash and lifecycle frames;
`candidate-linked/provenance.json` and `baseline-linked/provenance.json`
record their separate source/object/link inputs. The Atlas run has no corpse
lifecycle marker and confirms the existing hauling path remains usable.

## Remaining boundary

This candidate requires ordinary fixture review and integration. PR #254 merged
during this batch at root `65d7aee`; this source candidate branches from its
original `7af9ef6` and targets `codex/pikmin2-room-preview`. Runtime results above
use the explicitly listed private gameplay baselines, not that newer combined
integration build.
It does not alter Atlas gameplay, approve its shared physics semantics, resolve
natural cave return/restart QA, or claim native campaign completion. A natural
reproduction that warrants changing death/culling behavior needs a separately
scoped engine issue and review.

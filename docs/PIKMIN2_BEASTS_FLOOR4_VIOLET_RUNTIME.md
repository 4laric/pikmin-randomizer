# Floor 4 Violet conversion and pluck (#338)

Owner: Codex using shared 4laric account. This milestone connects the source
floor 4 BlackPom plan from #337/PR339 to one native Violet proxy and proves its
throw, conversion and pluck behavior. It starts with 20 Red and finishes with
15 Red and five Purple. It does not authorize campaign progress or implement
the other floor 4 actors, treasures or floor 5 descent.

Root base is frozen #336, `95df3cda051bf479681feb5c1abf62c592e35c16`.
There are **no production native changes**. The external fixture links against
the unchanged private #334 native build at
`9977856e34d54891c30260ca1d748d01e04f6e31`,
`output/native-beasts-floor4-entry/build-entry`. Parent/shared checkouts,
builds, ledgers and earlier submitted artifacts are untouched.

## Source and staging

The read-only source plans are under
`output/p2-cave-lane/output/beasts337/pop19/violet.json` and `pop20/violet.json`.
They bind the source roster, Pom parameters and frozen #330 assembly. The one
type-8 candidate is north-room instance 2, source slot 0, local position
`[125, 0, 145]`, transformed to `[295, 0, -875]`. Identity is
`forest_1:floor4:BlackPom:0`, generator **62002**, capacity five. Generator 62002
was reserved in #186 before implementation. Source yaw 175 is recorded, not
applied to the native proxy. No source route is added, reversed or removed.

The source birth rule applies Purple-population suppression on zero-based
floors below two or the specified tutorial cave. Beasts floor 4 has index three,
so declared populations 19 and 20 both retain this flower. Population is a
caller-supplied generation snapshot, not measured native global/save state.
The source-policy candidate and tests are delivered separately in PR339.

`experimental.pikmin2_beasts_floor4_violet_runtime.stage(assets, assembly,
purple, pod, output, plan_path, token)` takes Path arguments. It checks the
plan/assembly binding, selected candidate and budget, creates a fresh #334
diagnostic entry stage with 20 healthy leaf Reds, and appends exactly one native
Pom generator with Violet metadata 69. The full plan is copied as `violet.json`
and included in the stage input hashes. The token remains diagnostic. Source
identity and declared population are retained in `survey.json`.

## Grounded approach and native behavior

The first direct approach crossed the north room's central void and correctly
failed its native ground check. That failed run is preserved at
`output/floor4-338/runs/f8d8ec71aa6d46d8b83ce16faba875ed`. The unsupported segment
was confirmed against source collision. The fixture now walks around the void
through the source waypoint positions `(25,-1080)`, `(170,-1190)`, `(315,-1080)`
and `(295,-935)`. This is engineering captain steering; the directed source
carry route remains unchanged. All nine approach segments pass **837 collision
probes** across a 20-unit-wide strip, and native walking checks separation from
the floor below five units throughout the approach.

Five original Red bodies are thrown through `Navi::throwPiki`, ingested by the
existing Pom path and replaced by five Purple sprouts. Five ordered native
conversion witnesses bind generator 62002 and Red inputs. One sprout is plucked
through the captain's native NukuAdjust flow; remaining sprouts use native
InteractBikkuri interactions. The final snapshot checks 15 Red/five Purple,
all leaf, full captain health, carry strength and Purple selection identity.
The fixture does not directly recolor, create or delete these converted Pikmin.
Action selection is scripted; this is the existing P1 Pom Violet proxy, not
source P2 Pom model/FSM parity or manual gameplay sign-off.

## Evidence

All local paths below are beneath
`output/p2-beasts-floor3-track/output/floor4-338`.
The successful executable is `linked3/fixture.exe`, SHA-256
`c3a6f0a8682bdc7e371ea1d051b1ff95874c199984ec97a8c802fa00d63468e0`.
The provenance builder verifies the frozen native build and input dependencies.

| Declared Purple population | Run beneath `runs` | Native log SHA-256 |
|---|---|---|
| 19 | `bb5ad84b3617418eaefc85db9e3a613b` | `53a675b5738680b16ba3915d8f9c3b2d1f21eaf45dfd335d5524dcd0f3000861` |
| 20 | `5fd809fc38bd430688518197ae9cc4a9` | `698858cde43c0472fa0e8a45db9e617c0686141f139d2c42b86581f52fc05db1` |

Both passed, returned zero, retained health/repairs, wrote no transfer, credited
no cargo/reward and proved the same conversion/pluck outcome. Plan SHA-256 values
are respectively `16e466fddb973c3b9c482c6dd0b10bfa91b85becbf239d00ae8c5b86534b5c23`
and `122b595baac1e62b0c8490f4278621e0f061514963a8c61186110749520eca37`.
`verification.json` records both acceptance results and revalidation with the
final strict parser. The native health marker uses `health=1` (the native %.9g
format); a briefly mismatched parser literal was fixed without changing native
evidence. Input/executable hashes are checked before and after each run.
Independent read-only review identified that literal mismatch; parent verification
confirmed the correction and accepted both captured passes without further review.

Eleven focused Python tests and 48 subtests passed: source identity/budget and
declared-population validation, malformed/native wrong-floor/token/position/
throw/witness/party rejection, unsupported approach rejection, and existing
floor 4 entry/assembly and shared survey regressions. The final capture was
inspected: geometry and Purple silhouettes are visible, but substantial camera
occlusion and legacy UI remain. The image is not visual gameplay acceptance.

Reproduce by generating an external source with `fixture(native_preview_cpp,
output_cpp)`, linking through `scripts.build_pikmin2_fixture` with the exact
native SHA and private `build-entry`, staging the plan, then calling
`run(exe, directory)`. Fresh output directories are required. The new files are
independent of PR339's policy module and PR335's shared runner changes.

Remaining: natural player-controlled acceptance, P2 Pom parity, source-bound
campaign generation and boundary authorization, floor 4 terminal persistence,
other enemies/treasures/carrying, and floor 5 descent. This diagnostic stage
continues to reject floor 4 checkpoint writes and completion.

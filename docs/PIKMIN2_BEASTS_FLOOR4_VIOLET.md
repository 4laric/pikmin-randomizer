# Floor4 Violet generation and source slot (#337)

Owner: Codex using shared4laric account. Native companion: #338.

The floor4 BlackPom must remain available at a declared Purple population of 20
or more. In the read-only P2 research source,
`src/plugProjectNishimuraU/PomMgr.cpp`, `Pom::Mgr::birth` applies the Purple
suppression test only in story caves when the zero-based floor is below 2 or
the cave is `t_01`. The Beasts floor4 index is 3 and its cave is `f_01`, so that
test does not apply. Reusing the earlier floor2 generation helper here would
incorrectly suppress this flower.

The new `generation_context(population)` is scoped to story `forest_1` floor4.
It rejects invalid/non-int32 counts and always retains generator **62002**, with
five non-Purple conversion slots for `forest_1:floor4:BlackPom:0`. Same-color
refund mechanics belong to the existing conversion/runtime policy. Population
is a caller-supplied historical snapshot, not a native save readback. This source
rule does not certify successful actor allocation or player gameplay.

`prepare(iso, catalog, units, assembly, output, population, selected=(2,0))`
validates the final-floor source roster, catalog/import/assembly hashes and disc
sources. It enumerates source type8 candidates in every selected unit instance,
transforms their positions and records collision floor support. The explicit
engineering selection is instance2, `room_north3_1_tsuchi`, source slot0:

- Local position `(125,0,145)`, source yaw175 degrees.
- Unit center `(170,0,-1020)`, no quarter turn.
- World position `(295,0,-875)`, floor support Y0.
- Generator62002 reservation recorded by native companion #338 on #186.

The current authored assembly contains one type8 candidate. Selection is not
ported retail RNG or a campaign instance placement. Y is grounded from collision;
yaw is recorded without claiming native orientation. Other floor4 actors,
treasure/cargo, rewards and transitions remain outside this plan.

The actual Pom parameter block is extracted from
`enemy/parm/enemyParms.szs:pom/enemyparm.txt`; its proper slot count is five.
Parameter SHA256 `dd165853c89edfa3bf2779c377b9df5048535fda2bfa9e4aea179324de25be7e`.
The plan pins assembly SHA256
`b36841f817b7b68c4bd2edafd68098fd6c80eceaecde4169214faf4f6ee0bb66`.

## Validation and reproduction

Actual GPVE01rev0 plans are local at `output/beasts337/pop19`, `pop20`, `pop21`
and `pop20-repeat`. Every plan retains the same one-flower capacity. The repeated
population20 plans are byte-identical, SHA256
`122b595baac1e62b0c8490f4278621e0f061514963a8c61186110749520eca37`.

```powershell
python -m experimental.pikmin2_beasts_floor4_violet `
  --iso 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso' `
  --catalog ../../output/p2-cave-catalog-batch/audit-final/catalog.json `
  --units ../../output/p2-mapcode0-batch/import `
  --assembly ../p2-beasts-floor3-track/output/floor4-330/first `
  --output output/beasts337/new --global-purple-count 20
```

**13 tests and 50 subtests passed** across new floor4 policy, existing floor2
generation and final-floor source tests. They cover the 19/20/21 boundary,
int32 validation, unchanged floor2 suppression, source-slot transform/grounding,
invalid slot selection and changed assembly inputs. No native code changed in
this plan PR. Actual conversion/pluck evidence is owned by the separate #338
runtime, which consumes this plan and preserves its hash.

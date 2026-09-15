# Native boss-room geometry survey (#333)

Owner: Codex using shared 4laric account. The isolated source
`room_boss_1_tsuchi` now has a native captain traversal survey. Queen, plants,
`radar_a`, its equipment effect and the clogged geyser are omitted. This is not
floor5 campaign entry, boss combat, treasure hauling or cave completion.

The package retains the original room collision, route graph and spawn data
from #318, including the Queen→radar source ownership and final exit flags.
`build(iso, package, output)` checks the prepared room hashes and rehashes all
recorded sources against the GPVE01 revision0 disc before writing a fresh output.
The assembly wrapper is explicitly one isolated capped source room; it does not
select generated actor instances or imply a multi-room retail layout.

`stage(assets, assembly, purple, pod, output, party)` creates a fresh overlay with
twenty Red/Purple survivors. The engineering anchors are start `(0,510)`, Pod
`(-150,425)` and ship `(150,425)` in X/Z. Twelve controller goals cover the central
floor, both side areas, the far end and the return to start. Stage preparation
requires floor support at every goal and squad spawn; native checks grounded
captain movement throughout the survey. Individual squad traversal and hauling
are not certified. Source routes are preserved without adding reverse links.

Restoration uses the existing tutorial floor2 party loader, with
`party_restore_protocol_floor=2`, `campaign_entry=false` and `native_ready=false`.
The geometry and survey report are floor5. No campaign boundary token is supplied
or consumed. The host runner rejects boundary-bearing floor5 engineering runs.

## Evidence

Two fresh native runs each passed all 12 goals, preserving ten Reds, ten Purples,
mixed maturity (`index % 3`) and health 0.625. Both exited normally with zero Pokos,
unchanged repairs and no transfer file. Local paths under `output/beasts333/runs`:

| Run | Native log SHA256 |
|---|---|
| `34a4d39ca50546e39e6f55e4c4803fbd` | `4c9083020b90e53592eb03cb57c770d13b2957bd4b81e5754a4128278e4aae5e` |
| `c17919843fec4fbda63b362f3238a69c` | `4bf3064fc7abfebe5cfdcfc4e108950daf8a3bf4769295758a16a358ccf0e937` |

Fixture executable SHA256:
`2542b89f29ea3b8cd7b762c812922f42dbac06c1db3a38a968768355de78071b`.
It links the frozen native `a9627bebf79445dfff0253992a1f72e0926d955a` private
`build-failure` production build. No native source edits; fixture source is
generated externally using checked anchors. The initial link attempt used a
nonexistent build directory and stopped; the successful fresh `linked-final`
directory records full provenance and Ninja freshness observations.

Room packages `room` and `room-repeat` contain four byte-identical files.
Manifest SHA256 `5084379bc76b45f3b3ba282bf5f8c38eb42d906d8c79a4af14826ee0a53991b3`;
all hashes are in `output/beasts333/package-verification.json`. Each native run's
`acceptance.json` records unchanged inputs and executable. The capture was
inspected: geometry and party render, but approximate materials, preview actors
and P1 UI remain. This does not certify visual fidelity.

**15 tests and 38 subtests passed** across floor5, floor4, floor3 runtime/entry
and party restoration. They include changed room/disc/exit/owner rejection,
fresh output and exact fixture-anchor checks. Independent read-only review found
no blocker in this engineering scope. Floor3/4 defaults retain their prior
branches; only the floor5 opt-in and marker remapping are added.

The implementation uses a private join of #331 and #332. Concurrent #334 floor4
native entry also changes the shared runner: integrate its floor4 token-aware
branch with this floor5 token-free remapping, keeping both policies distinct.
All assets, generated fixtures, executables and captures remain local.

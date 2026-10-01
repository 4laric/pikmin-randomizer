# Floor 3 source treasure hauling (#343)

Owner: Codex using shared 4laric account. This milestone installs one actual
`dia_c_green` model from #295 at the source-bound placement from #344/PR345,
hauls it through the assembled room and corridor into the Research Pod, and
verifies an exact 150-Poko receipt without changing P1 repairs. A second fresh
process reopens the first ledger and hauls the same instance without more credit.
No floor progression or campaign reward authorization is added.

Root base is frozen #341, `cf4d648d4aef09e0d286526a99c4f1fbcd4fc452`.
There are **no production native changes**. The external fixture uses frozen
native `9977856e34d54891c30260ca1d748d01e04f6e31` and its private
`output/native-beasts-floor4-entry/build-entry`. Parent/shared native checkouts,
builds, ledgers and submitted artifacts are untouched.

## Source and runtime contract

The input plan is read-only at
`output/p2-cave-lane/output/beasts344/first/haul.json`. Its parent candidate is
PR345, root `891847b61de05e06faec3a08b8d4f1352011597f`. The plan binds the frozen
#295 `floor3.json`, model and #306 assembly hashes. It selects source treasure
row 1, north-room type-2 slot 0, local `[0,0,-25]`, transformed to
`[-85,0,-960]`. The instance is `forest_1:floor3:treasure:dia_c_green:0`.
Generator **63000** was reserved in #186 before implementation.

The real converted model has SHA-256
`39e6a982f7f5d36163a991959ec3ab7a7d505d46d5947a58a1af93d1738a9b60`,
58 vertices, 112 triangles, two shapes and three textures. Source catalog
settings are value **150**, minimum carry weight **12**, maximum slots **20**.
The stage installs one pr05-backed pellet through `P2_CARGO_1` with its exact
instance/model/settings, and configures `P2_POD_1`. No enemy, flower, corpse,
second treasure or placeholder cargo is installed.

`experimental.pikmin2_beasts_floor3_haul_runtime.stage(assets, assembly, purple,
pod, package, plan_path, output, token, replay_ledger=None)` accepts Path inputs.
The stage starts twenty healthy leaf Reds near the cargo, with engineering
captain anchor `(-85,-850)`, Pod `(-85,-280)` and ship `(85,240)`. Spawn positions
are collision-grounded by the existing staging helper. The token selects the
explicit native floor3 diagnostic entry and is not a host boundary authorization.
The copied plan, source metadata, actual model, generators and configuration
are input-hash-bound. Replay accepts only the exact first one-receipt ledger.

The source plan retains directed waypoint path **9 → 8 → 7 → 0** and its end
connectors, supported by 267 probes across a 50-unit strip. Native transport is
free to choose its normal connector into that route; the fixture does not force
visits to every waypoint. It assigns ordinary Piki Transport actions, then
follows the moving cargo with captain controller input to keep simulation active.
It never moves the cargo or carriers by position assignment during the run.
Both actual assembly seams, north **z=-510** and south **z=-340**, must be crossed
before delivery. Native trace proves movement beyond the second seam.

Beasts lifecycle `active()` currently requires cargo-free readiness. Cargo mode
therefore restores/readbacks native floor3 but leaves its lifecycle inactive.
This candidate documents that limit and keeps checkpoint/exit42 unavailable;
it does not change shared cave semantics to support a campaign cargo floor.

## Actual evidence

Local paths below are beneath
`output/p2-beasts-floor3-track/output/floor3-343`.
The successful executable `linked3/fixture.exe` is SHA-256
`4c7ff137431b94300e0d5dd591eddef1e9a53743e95a4df2c2a35d95761f803c`.
The builder records unchanged native dependency/build provenance.

| Case | Run beneath `runs` | Native log SHA-256 |
|---|---|---|
| Fresh economy | `bd2c4539ca674759b1c1866b22f67aa1` | `d1e55a34a8e83471bbec40c5dba92d7e98acabcef471d51afb06586957fe0e65` |
| Reopened economy | `bad9684c7ce041b693f6d8b5a16e1e15` | `795266cb6c70c8ce78c063be92f0087eb6a135fab7e0371b3501af7373a91997` |

Both native runs returned zero and printed PASS. They reached 20 attached Red
carriers, crossed both seams, and produced 37/36 observed cargo positions.
Fresh delivery credited 150, then the same-process duplicate hook credited zero.
The second process loaded that actual ledger, hauled the same source instance
again, and emitted two `new=0` receipts with total still 150. Each run also used
the native P2Economy reader to reopen and verify one receipt plus duplicate
rejection. Repairs stayed unchanged and no floor transfer was written.

Both runs produced identical files:

- `treasure-receipt.txt`: `treasure=forest_1:floor3:treasure:dia_c_green:0 count=1 pokos=150`, native Windows CRLF ending; SHA-256 `2af9fa55ca5b08a8c3128ba1e1fcdb78a2dcaa82607aa0143d9ebf3752ee1bea`.
- `p2-economy.txt`: P2_ECONOMY_1 and one `treasure:forest_1:floor3:treasure:dia_c_green:0 150` row, binary LF endings; SHA-256 `530496e73e288c54695be73e05568441b8707acf345d020d8dc0e5a22b11b344`.

The first host parser initially expected an LF receipt; it was corrected to the
actual Windows text-mode CRLF. Its original rejection remains in acceptance.json;
revalidated.json records the final parser pass and unchanged input/executable
hashes. The second run passed the corrected parser directly. verification.json
collects final validation of both captured runs. No native evidence was rewritten.

Independent read-only review caught initially incorrect seam observer thresholds;
these were changed to the bound assembly's -510/-340 values before the successful
runs. The first exploratory run (`8fcf08809e914e4e9f90ec57eeebee2f`) ended with code
1 after recruiting and moving cargo, without a diagnostic assertion or receipt.
It is preserved and its cause remains unconfirmed; that exit did not recur in
the two completed runs. A compile-time Pellet/Boss accessor mismatch was fixed
before the successful link. Neither exploratory artifact is acceptance evidence.

Eight focused tests and 47 subtests passed, covering source hash/identity and
settings rejection, exact first/replay receipts, insufficient carriers, missing
or premature seam traversal, altered trace, duplicate credit and floor transfer.
The final capture was inspected: Pod, room and returning Red squad are visible,
with legacy UI and foreground camera occlusion. This is not visual/manual-play
sign-off or a full cave save/resume test.

Reproduce by generating `fixture(native_preview_cpp, external_cpp)`, linking
through `scripts.build_pikmin2_fixture` with the frozen native source/build/SHA,
then calling `stage` and `run(exe, directory)`. All output directories must be
fresh. For replay, pass the completed first run's `p2-economy.txt` as replay_ledger.
The source-plan module from PR345 is a separate artifact producer, not imported
or modified by this runtime module.

Remaining: natural carrier recruitment and manual gameplay, other floor3 source
content, campaign receipt authorization, integrated cargo lifecycle/terminal
checkpoint support, and successful descent. The single engineering receipt is
not a production campaign collection or proof of full floor3 completion.

# P2 Challenge 04 ch_NARI_01kusachi — P0 import contract (lane p2-challenge-ch_nari_01kusachi, #533)

Owner: Codex through shared account `4laric`. Parent content #137; coordination #531.
Phase: **P0 only**. No claim of playability; P1/P2 remain OPEN with runtime
dependencies #136, #137, #129, #130, #131.

## Source identity (canonical, not observed)

- Source ID `ch_NARI_01kusachi`, UI index 3 (authoritative; English title unresolved).
- Disc path `user/Mukki/mapunits/caveinfo/ch_NARI_01kusachi.txt`, pinned sha256
  `b8d232f417ce3fd4b2903571a1c53234e63dec49e127d5ef5b8ef3cc34bb8d85`
  (`docs/PIKMIN2_CONTENT_INVENTORY.json` `source_sha256`, mirrored in
  `docs/PIKMIN_CONTENT_IMPORT_LANES.json`).
- Catalogued contract: 1 floor; starting roster 50 blue leaf Pikmin (native
  color index 2, maturity index 0); floor timer 180 s within a 350 s legacy
  budget; 1 bitter + 2 spicy sprays; `treasure_count_field` 0.

## Actual-source decode (observed, this slice)

Local legal source `assets/disc/PIKMIN2 for GAMECUBE.iso` (read-only) contains
the entry: **1267 bytes, sha256 `b8d232f4…bb8d85` — matches the pinned
canonical hash.** Decoded shift_jis (1184 chars) through the shared parser
(`experimental.pikmin2_cave_catalog.parse`) with retail ID sets (100 enemy IDs
from `native/pikmin2-research/.../enemyInfo.cpp`, 201 treasure IDs from
`pelletlist_us.szs`): **1 definition, floor span 1–1 — complete floor
coverage.** Full manifest: lane output `decode.json` (sha256 `7d89054c…3285a`).

Floor 1 roster (definition weights, not placements): `Tank_key`,
2× `Jigumo_silver_medal`, `Frog_turi_uki`, 3× `Catfish_wadou_kaichin`, plants
`Clover`/`Zenmai`/`Clover` (target counts 5/5/5); treasures `kan`,
`dia_c_green`; one `gate` (life 4000.0, weight 11); cap block present with
count 0. Floor parameters: `f008` pool `1_MAT_ike_kusachi.txt`, lighting
`kusachi_light_cha.ini`, unit root `hiroba`.

Resource closure: pool file present in disc; 8 unit definitions
(`cap_kusachi`, `item_cap_kusachi`, `way3_kusachi`, `way4_kusachi`,
`wayl_kusachi`, `way2_kusachi`, `way2x2_kusachi`, `room_ike_kusachi`); all
`arc.szs`/`texts.szs` unit assets present — **zero missing unit assets.**
Unsupported-actor assessment for P1: Tank (Armored Cannon Beetle larva),
Jigumo (Beady Long Legs), Frog (Wollywog) and Catfish (Water Dumple) are
engine-owned species outside this lane; no fallback behavior fabricated here.

## Adapter (`experimental/content_lanes/p2-challenge-ch_nari_01kusachi.py`)

Isolated per-lane boundary reusing the existing shared parser
(`experimental.pikmin2_cave_catalog.parse` — not forked, not edited):

- `source_identity()` — pinned identity + catalogued metadata.
- `locate_source(roots)` / `read_disc_source(iso_path)` — find the
  disc-relative path or read the pinned bytes via the existing disc reader;
  absent image/entry raises the exact missing-disc prerequisite.
- `verify_source_bytes(data)` — fail-closed sha256 check vs the pinned hash.
- `decode_stage(text, enemy_ids, treasure_ids)` — shared parse plus the
  1-floor coverage check; malformed input raises `StageDecodeError`.
- `resource_closure(cave)` — lists `f008` unit-pool references as unresolved
  without source bytes.
- `build_import_packet` / `write_packet` — JSON implementation packet under
  ignored output with verification status, floor coverage, blockers and the
  definition-not-placement limitations.

## Tests (`tests/content_lanes/test_p2_challenge_ch_nari_01kusachi.py`)

10 focused tests, all passing without disc/native/runtime: canonical-identity
parity with both JSON catalogues; missing-source prerequisite wording; staged
file location; hash-mismatch rejection; synthetic single-floor structural
decode (clearly labeled synthetic, never source evidence); 2-floor coverage
rejection; 5 malformed-input rejections; unresolved closure listing; honest
unverified packet contents; packet write round-trip with sha256.

## Blockers for P1 (exact)

1. Runtime framework #136 (Challenge timing/keys/scores/retry semantics) and
   content #137 acceptance pins.
2. Generator/actor owners #129, #130, #131 for floor construction and species
   admission; unresolved enemy admission blocks promotion, not P0.
3. Integrator cherry-picks only the three reserved files into its chosen
   integration branch; never merge this worktree's history into species wave.

## Evidence

- Focused test log: `output/workflow/content-expansion/p2-challenge-ch_nari_01kusachi/checks.log`
  (command below, exit 0).
- Real decode manifest: `output/workflow/content-expansion/p2-challenge-ch_nari_01kusachi/decode.json`
  (1267-byte hash-verified source, full roster/closure).
- Implementation packet: generated at handoff time under the lane output dir;
  delivery copy `output/deepseek-wave/inbox/content-533-p0.md`.

```powershell
py -3.12 -m pytest tests/content_lanes/test_p2_challenge_ch_nari_01kusachi.py -q
```

---

# ch_NARI_01kusachi P1 runtime import (issue #533, lane p2-challenge-ch_nari_01kusachi-p1)

Implementation owner: Codex through shared account `4laric`. This section
extends the P0 packet above with the P1 private runtime import slice. The P0
decode helpers are reused unchanged (no forked parser).

## P1 staging (`stage_run_layout` / `verify_run_layout`)

The decoded P0 packet is staged into a private run layout:

- `stage-manifest.json`: floor rows (unit pool, decoded enemy/treasure tokens
  when the decoded cave is supplied), squad rows, timers, legacy budget,
  sprays, UI index, unsupported semantics and the source hash. Weights remain
  definition inputs; nothing is placed.
- `squad.json`: the starting squad (50 blue leaf; native color 2, maturity 0).
- `run-config.json`: `window: 960x540`, squad source, unsupported list.
- `markers.txt`: the required receipt-parseable marker contract
  (`P2_KUSACHI_WINDOW`, `P2_KUSACHI_SQUAD`, `P2_KUSACHI_FLOOR_READY`,
  `P2_KUSACHI_ACTOR`, `P2_KUSACHI_PASS`).

Staging fails closed on any packet divergence (identity, floor coverage,
timers, pool/floor count). `verify_run_layout` re-checks a staged layout
without trusting it; `parse_marker_log` accepts only a full, correctly
centred (960x540) marker log and fails closed otherwise.

## Unsupported semantics (recorded, not claimed)

`challenge_host_mode`, `coop_2p`, `key_completion`, `result_screen` —
mirrored from the contract consumer
(`docs/PIKMIN2_CHALLENGE2_CONTRACT_CONSUMER.md`). No host-mode
implementation lane exists in this tree; a staged run exercises the cave
path only, never Challenge-mode rules.

## Captain safety (#632) — adoption pin gap

The canonical guard `scripts/p2_fixture_captain_guard.h` (sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`) was
added AFTER this lane's pinned root base `b08e3bdc`, so it is NOT present in
the pinned tree. It is consumed read-only from the canonical workspace and
its hash recorded by `guard_hashes()`; it is never vendored into the pinned
base and no fake guard provider is created. Any future runtime run must adopt
it (or a tested equivalent) with orimaDead/NaviDead/HP<=1 checks,
CAPTAIN_DOWN + BLOCKED exit, a parked captain and labelled protection.

## Runtime evidence and exact blocker

**Partial runtime observation achieved this slice via the integrated
#675 hook; all six gates stay UNTESTED and no playability is claimed.**
Observed in this lane's fresh private run
(`prepared/p1-kusachi-output/run-kusachi-01/`, exit 0, 1.9 s, no
CAPTAIN_DOWN, no refusal), using the verified stage-boot fixture binary
read-only (sha256
`87577167ea8e8654b09ffe8eac352664cc7f1ffcf05cb5f6040a5a8780244d34`, built
from native cap `328c214e`, merged fast-forward into this lane's native
worktree with no conflicts):

- The only challenge boot path in this native pin is
  `--experimental-challenge-level 0-4` (`pc_port/pc_bbft.cpp:47-51`), which
  selects the five P1 stage inis `stages/chal0..chal4.ini` — NOT P2 challenge
  caveinfo stages such as `ch_NARI_01kusachi`.
- The P2 challenge guarded fixture that exists
  (`native/tools/p2_challenge_guarded_boot_fixture.cpp`, lane #649) also
  boots `--experimental-challenge-level <0-4>`; it emits no `P2_KUSACHI_*`
  markers and cannot select this stage.
- The generic challenge host-mode consumer (`challenge-host-mode`, issue
  #651) is BLOCKED on `#186` shared-owner review: registering its fixture in
  the maintained CMake/CTest is a shared edit. Its owned files are not this
  lane's to edit.
- This lane owns only its three content-lane files (no native fixture), so it
  cannot add a stage-boot fixture itself without a shared-owner change.
- The cave path (#642 fixture + `pikmin2_cave_runtime_inputs.py`) boots
  caveinfo floors but requires a generator sidecar from the cave-generation
  provider (#129) and emits `P2_CAVE_*` markers, not this lane's contract.

Observed markers (verbatim from `native.log`): `P2_CHALLENGE_STAGE_FLAG
cave=ch_NARI_01kusachi`, `SIDECAR`, `TABLE` and `RESOLVED` (ui_index=3,
floors=1, roster_total=50), `WINDOW size=960x540 pos=373,263 display=1707x1067
centered=1`, `READY observed=1`, `GATES all=UNTESTED content_wired=0`, and
`PASS CHALLENGE_STAGE_BOOT`. The arena spawned 24+30 generators; the single
placement probe names the dwarf scaffold only (terrain=none, route=0), and no
squad/gameplay/extinction marker exists, so live squad, active gameplay,
collision, routes and actors are NOT claimed.

Exact remaining dependency: **arena/content wiring** for the boot arena,
owned by challenge host-mode #651 and #656 per the #675 evidence packet
("host-mode #651 and #656 remain the arena/content owners"). The boot
fixture wires no P2 cave content by design (`content_wired=0`). A fresh
heavy private build was deliberately not repeated: the accepted
prerequisite binary was verified (hash + provenance head == merged head,
source files byte-identical modulo checkout line endings) and reused
read-only, so rebuilding identical source would only duplicate work.

## Generation-4 reassessment (integrated #656 did not clear the gap)

The newly integrated prerequisite `p2-challenge-host-mode-build-harness`
(#656, root `d061a464`, native `f698955a`) was inspected and does NOT wire
P2 challenge stage content:

- its fixture `native/tools/p2_challenge_mode_fixture.cpp` embeds a hardcoded
  `ch_MUKI_metal` stage entry and runs a pure host-mode state machine
  (BOOT/TICK/RETRY); the harness doc scopes it as "game-linked build, not
  engine boot/gameplay", all six gates UNTESTED;
- `native/pc_port/pc_p2_challenge_mode.cpp` is a 33-line state machine with
  zero engine manager/spawn/loadShape references;
- native `f698955a` is on a divergent line (not an ancestor of this lane's
  head `328c214e`), so no prerequisite merge was necessary or performed;
- the #669/#675 boot path already observed this slice's window/selection
  chain with `content_wired=0` by design.

Remaining gap (exact): **P2 challenge stage content wiring** (arena geometry,
actors, starting squad) for a boot — no producer lane owns it — plus the
maintained CMake/CTest registration packet #661 still open under #186
review. Squad, collision, routes and actors remain unobserved; all six gates
UNTESTED; no playability claim.
## Generation-5 consumer verification (integrated #688, verification 2ec42405)

Consumer check PASSED (recorded via workflow.consumer_verification, status
passed): the integrated #688 bridge (root `a2bd2122`, module verified
identical to the lane worktree modulo checkout line endings) was run against
the hash-verified real `ch_NARI_01kusachi.txt` decode (1267 bytes, sha256
`b8d232f4...`) and this lane's freshly staged run layout. All 7 agreement
points true: cave id, 1 floor, pool `1_MAT_ike_kusachi.txt`, squad total 50,
timers, all 5 boot markers
(`P2_KUSACHI_BOOT/ARENA_BOUND/SQUAD/PLACEMENT_ROWS/SELECT`), actor rows
present. Evidence:
`prepared/p1-kusachi-output/consumer-check-gen5.json` (sha256
`40ef53754d51328c03ad0141b46fa6967f453f6f856e476cde2e6d24149e7f0c`).

Scope honesty: the bridge emits arena/actor/squad BINDINGS as weighted
definitions, never live placements or coordinates, and no boot with live
engine content exists yet. Squad, collision, routes and actors remain
unobserved; all six gates UNTESTED; no playability claim.
## Generation-6 content boot (integrated #695 preview reconciliation)

The accepted #695 native preview reconciliation was merged into this lane's
private native worktree (base `ab81cf5d`: #675 hook `328c214e` + #695
`4a69502e`, clean `ort` merge, head `d8f61358`). A fresh leased private build
(`output/p1-kusachi-gen6-build`, exe sha256
`0291dc712e6c7764e9c38b6c35574568722e6c9a7aff24a9d7b3a7c83551dc23`,
`ninja: no work to do.`) and a private fixture build (provenance `built`,
expected == observed head `d8f61358`, fixture sha256
`85132b2d5ca870500a06964fe104aaae4d374f2a3aa29d1547d2ba1184f8be4a`) were
run under the canonical guard (canonical `scripts/p2_fixture_captain_guard.h`
sha256 `d2f678c9...`, vendored verbatim by the #675 fixture; no CAPTAIN_DOWN).

Observed in `prepared/p1-kusachi-output/run-kusachi-gen6/native.log` (exit 0,
1.76 s), where the same boot previously aborted at
`pc_p2_preview.cpp:128` "duplicate treasure":

- `P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1` - live starting
  squad (20 red) on the isolated room preview.
- `P2_PREVIEW_PR05 room_bolts=0 staged=1 cargo=0` - one staged pr05
  treasure, no cargo, no duplicate abort.
- `P2_ROOM_GROUND` (4 samples) - real collision/ground queries.
- `P2_PLACEMENT_SLOT ... route_distance=805.3` / `P2_PLACEMENT_PROBE
  actors=1` - one actor with a route probe.
- `P2_ROOM_READY treasure=bolt carry=5 repairs=1` and
  `P2_CHALLENGE_STAGE_WINDOW size=960x540 pos=373,263 centered=1`.

Residual gap (owner/runtime business, explicitly outside this slice per the
recovery check): the fixture still reports
`P2_CHALLENGE_STAGE_GATES all=UNTESTED content_wired=0` - the kusachi
stage-specific roster/actor content is not wired; the boot exercises the
generic room preview with the 20-red starting overlay, not the 50-blue
kusachi roster. Squad-of-record, stage actors, routes and the six gates
therefore remain UNTESTED and no playability claim is made.
### Generation-7 re-verification (verification 38ef855e)

The integrated #695 producer set was unchanged, so the check was reproduced
with a fresh independent run of the pinned fixture (no rebuild): exit 0 in
1.242 s, live squad red=20, 4 ground samples, actor route probe
(route_distance=805.3), `P2_ROOM_READY treasure=bolt`, centred 960x540,
`PASS CHALLENGE_STAGE_BOOT`, no duplicate abort, no CAPTAIN_DOWN. Verdict
recorded passed + prerequisite_resolved. Evidence:
`prepared/p1-kusachi-output/gen7-runtime-evidence.json` (sha256
`0d08fd1b950fd155f6c1e0bfc999aeecdeddb1a4cf2c818c2584f9362e8102f4`). The
residual gap below is unchanged and still owner/runtime business.

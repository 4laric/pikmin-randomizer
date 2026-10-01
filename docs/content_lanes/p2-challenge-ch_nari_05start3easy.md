# ch_NARI_05start3easy P0 import packet (issue #548, lane p2-challenge-ch_nari_05start3easy)

Implementation owner: Codex through shared account `4laric`; executing worker
muse-l62 (same session, generation 2). Phase P0 only: source audit and additive
import contract. No claim of imported or playable content; full issue #548 stays
open for P1/P2.

## Source identity (two live sources, both hashed at audit time)

- Cave definition: `user/Mukki/mapunits/caveinfo/ch_NARI_05start3easy.txt`
  (2193 bytes), SHA-256
  `19dac7888d8151b26b6e8e00b021058ba93344b6b2a08455ceedcd3e243ef845`
  (matches the recorded `source_sha256` in `docs/PIKMIN_CONTENT_IMPORT_LANES.json`
  and `docs/PIKMIN2_CONTENT_INVENTORY.json` byte-for-byte).
- Stage table: `user/Matoba/challenge/stages.txt`,
  SHA-256 `59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1`;
  exactly one of its 30 stage blocks references `ch_NARI_05start3easy.txt`.
- Decoders: shared retail parser `experimental.pikmin2_cave_catalog.parse` for
  the cave half (enemy IDs from research `enemyInfo.cpp`, treasure IDs from the
  disc pellet archive); a small strict stage-block parser owned in the lane
  adapter (no shared challenge decoder exists; nothing forked).

## Stage metadata (decoded vs lane contract ? all match)

Starting roster: 1 leaf each of col0/col1/col2 (3 Pikmin); legacy time 400.0;
bitter 1 / spicy 2 dopes; 2 floors; otakara count 0; 2d UI index 15; floor
timers 120.0 s + 80.0 s. English title unresolved; source ID and UI index
authoritative per lane entry.

## Floor coverage (2 floors, same unit pool)

Unit pool `2_MAT_cent_north_tsuchi.txt`: NOT covered by the story-cave baseline
catalog (96 pools), so decoded live from disc ? SHA-256
`a487ff16fd6bb9b75e5e478670124621ae78a412853ee888c29b705139fd0d03`, 8 units
(`item_cap_tsuchi`, `way3/4/l/2/2x2_tsuchi`, `room_cent_4_tsuchi`,
`room_north_1_tsuchi`), every unit asset (arc.szs/texts.szs) verified present
in the disc table. Provenance marked `live` in the packet (not baseline).

Floor 1 enemies (9 rows): `RandPom`, `YellowKochappy_chocowhite`,
`Kochappy_ichigo`, `BlueKochappy_donguri`, `KumaKochappy_cookie_u`, `Egg`,
`Wakame_s`, `Wakame_l`, `Ooinu_s`; item `key`; one non-empty cap (`RandPom`).
Floor 2 enemies (6 rows): `Wtank_key`, `RandPom`, `Tank_silver_medal`,
`ElecHiba`, `Ooinu_l`, `Wakame_l`; items `dia_a_green`, `chess_queen_white`.
Gates: none either floor. Cargo suffixes (`chocowhite`, `ichigo`, `donguri`,
`cookie_u`, `key`, `silver_medal`) all resolve against the disc pellet catalog.
Weights are definition inputs, not placements.

## Native/framework blockers for P1 (exact)

1. Native cave/generator import hook plus Challenge-mode stage bootstrap
   (PikiCounter roster, dopes, floor timers, 2d index) ? integration owner; this
   packet wires no native path.
2. Unit-pool asset staging for `2_MAT_cent_north_tsuchi.txt` via the existing
   unit pipeline; the packet records the pool source + hash, not staged assets.
3. Seeded topology/hole selection and generator pins unproven for these 2
   floors; weights are definition inputs, not placements.
4. Enemy admission resolved per enemy roster at P1; unresolved admission blocks
   promotion, not this packet; no host chal0 fixture treated as Challenge mode.

## Adapter and tests (reserved files)

- `experimental/content_lanes/p2-challenge-ch_nari_05start3easy.py` ? isolated
  two-source adapter with live pool-decode fallback (contract load, live
  decode+hash, stage verify, cave coverage, closure verify, packet emit).
- `tests/content_lanes/test_p2_challenge_ch_nari_05start3easy.py` ? 7 focused
  tests (stage-block parse, contract match, real lanes-doc load, malformed
  block/contract/cave rejection, unreadable-source rejection). All pass on
  synthetic inputs (no disc needed).
- Integrator result file:
  `output/deepseek-wave/inbox/autofill-548-result.md` (points at this doc +
  packet JSON at `output/workflow/autofill/p2-challenge-ch_nari_05start3easy/packet/`).

No placements emitted, no runtime run, no ADMIT. P1/P2 acceptance stays OPEN.

## P1 private runtime import and first playable acceptance (#548)

The module adds a P1 import path that reuses every P0 helper (no forked parser)
and stages the decoded stage into a private run layout, then boots the
integrated Challenge content-loading runtime.

- `floor_manifest(cave, index)` / `content_sidecar` / `generate_sidecar` /
  `preview_record` / `stage_manifest_record` build the run layout:
  `p2-challenge-content.txt` (P2_CHALLENGE_CONTENT_1; stage/floor/pool/spawns/
  anchor), `p2-cave-generate.txt`, `stage-manifest.json` and `preview.json`.
- `stage_run_layout(...)` writes the four files, hashes them and fails closed on
  any missing/undecodable input; boot floor is floor 1.
- `parse_run_markers(log)` / `verify_receipt(markers)` parse and enforce the
  receipt-parseable runtime markers (content SELECTED/SPAWN_COVERED/READY/LIVE/
  PASS, room collision `P2_ROOM_GROUND`, actor `P2_PLACEMENT_PROBE`), and refuse
  a captain-down receipt.

Preserved stage facts: floors=2, floor_seconds=[120.0, 80.0], legacy_time=400.0,
bitter_sprays=1, spicy_sprays=2, treasure_count=0, ui_index=15, roster 7x3 with
starting_pikmin=3, ui_index 15; unit pool `2_MAT_cent_north_tsuchi.txt` on both
floors.

### Observed runtime receipt (private leased build)

Fresh private leased build of native `f91c2143` (elastic cap respected, leased
CLI) plus the content-loading fixture, run over the staged run layout with a
960x540 centred window. Observed markers (runtime.log):

```
[PC Port] SDL2 Window & OpenGL Context initialized successfully (960x540)
[Pikipelago] P2_ROOM_GROUND x=-85.0 z=0.0 y=0.000          (4 collision probes)
P2_PLACEMENT_PROBE actors=1 evidence_slots=1
P2_CHALLENGE_CONTENT_SELECTED cave=ch_NARI_05start3easy floor=1 pool=2_MAT_cent_north_tsuchi.txt spawns=10 anchor=hole
P2_CHALLENGE_CONTENT_SPAWN_COVERED id=<10 ids> count=1
P2_CHALLENGE_CONTENT_READY cave=ch_NARI_05start3easy floor=1 squad=20 captain_parked=1
P2_CHALLENGE_CONTENT_LIVE squad=20 actors=1 tick=2
PASS P2_CHALLENGE_CONTENT_RUN content=1
```

`verify_receipt` accepts this receipt (collision_probes=4, actor_probes=1). No
`P2_FIXTURE_CAPTAIN_DOWN`, no FAIL/REFUSED.

Captain safety (#632): the guard is adopted first-after-engine-idle, before
movie/pause/UI returns and every observed tick; the captain is parked at
`nx=+600` outside attack reach; guard header sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`. No blanket
invincibility; this is labelled protected observation.

Honest limits: the observed live squad is the current starting-Pikmin overlay
(20); the stage roster (starting_pikmin=3) is the decoded contract carried in
the manifest. All six arena gates stay UNTESTED; this is a boot/collision/actor
receipt, not gameplay acceptance. The engine's host-mode stage table
(`pc_port/pc_bbft.cpp` kP2ChallengeStages) still lists only `ch_NARI_01kusachi`,
so the `--experimental-challenge-stage` arm is not yet generic for start3easy;
that is the remaining P2 blocker for the stage-select path (scoped shared review
to the host-mode owner), not for this content-loading boot receipt.

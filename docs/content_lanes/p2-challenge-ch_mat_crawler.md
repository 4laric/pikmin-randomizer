# ch_MAT_crawler P0 import packet (issue #562, lane p2-challenge-ch_mat_crawler)

Implementation owner: Codex through shared account `4laric`; executing worker
muse-l62 (same session, generation 3). Phase P0 only: source audit and additive
import contract. No claim of imported or playable content; full issue #562 stays
open for P1/P2.

## Source identity (two live sources, both hashed at audit time)

- Cave definition: `user/Mukki/mapunits/caveinfo/ch_MAT_crawler.txt`
  (2411 bytes), SHA-256
  `ab3b2dbb238e4a0c2d1bd4c3c958fd52d25b8ee0a0245f756d6d6a138a325bbd`
  (matches the recorded `source_sha256` in `docs/PIKMIN_CONTENT_IMPORT_LANES.json`
  and `docs/PIKMIN2_CONTENT_INVENTORY.json` byte-for-byte).
- Stage table: `user/Matoba/challenge/stages.txt`,
  SHA-256 `59890efa80fe5a77d52b9a87301b97c91cd10c94ff9a3fb85c49b78dfae03cf1`;
  exactly one of its 30 stage blocks references `ch_MAT_crawler.txt`.
- Decoders: shared retail parser `experimental.pikmin2_cave_catalog.parse` for
  the cave half (enemy IDs from research `enemyInfo.cpp`, treasure IDs from the
  disc pellet archive); a small strict stage-block parser owned in the lane
  adapter (no shared challenge decoder exists; nothing forked).

## Stage metadata (decoded vs lane contract ? all match)

Starting roster: 30 flower Red (col0) + 30 flower Yellow (col1) = 60 Pikmin;
legacy time 500.0; bitter 3 / spicy 4 dopes; 2 floors; otakara count 0;
2d UI index 29; floor timers 170.0 s + 120.0 s. English title unresolved;
source ID and UI index authoritative per lane entry.

## Floor coverage (2 floors)

Floor 1 ? pool `4_units_c_e_j_l_conc.txt` (NOT in the story-cave baseline, so
decoded live from disc: SHA-256
`707e74797eb8bdb0295bb7710b03c00dd5fb38116ef649b5a85246585f66b64a`, 11 units,
every arc/texts asset present). Enemy rows (14): `Hana_silver_medal` x2,
`Armor_wadou_kaichin`, `Wealthy_gold_medal`, `Magaret` x2, `UjiA_be_dama_red`,
`UjiB_be_dama_blue`, `Tobi_donguri`, `Wakame_l`, `Wakame_s`, `Ooinu_s`,
`Ooinu_l`, `Clover`. Items (3): `key`, `haniwa`, `kouseki_suisyou`.
Gate (1): `gate` life 4000.0 weight 1 ? the first challenge lane with a live
ItemGateMgr gate; the shared parser decodes it and the packet records it.

Floor 2 ? pool `1_units_manh_conc.txt` (likewise live: SHA-256
`33ca22ce839c438e60ed54c95d80d7120b7894688d644d353b23505ebe8371b7`, 7 units).
Enemy rows (7): `SnakeWhole_key`, `KareOoinu_l` x4, `KareOoinu_s` x2.
Items: none. Gates/caps: none.

Cargo suffixes (`silver_medal`, `wadou_kaichin`, `gold_medal`, `be_dama_red`,
`be_dama_blue`, `donguri`, `key`) all resolve against the disc pellet catalog;
every weight/placement type is preserved verbatim. Weights are definition
inputs, not placements.

## Native/framework blockers for P1 (exact)

1. Native cave/generator import hook plus Challenge-mode stage bootstrap
   (PikiCounter roster, dopes, floor timers, 2d index) ? integration owner; this
   packet wires no native path.
2. Unit-pool asset staging for `4_units_c_e_j_l_conc.txt`,
   `1_units_manh_conc.txt` via the existing unit pipeline; the packet records
   pool sources + hashes, not staged assets.
3. ItemGateMgr gate decoding (floor 1, life 4000.0) needs the shared
   gate/electric manager owner; the packet records the gate roster only.
4. Seeded topology/hole selection and generator pins unproven for these 2
   floors; weights are definition inputs, not placements.
5. Enemy admission resolved per enemy roster at P1; unresolved admission blocks
   promotion, not this packet; no host chal0 fixture treated as Challenge mode.

## Adapter and tests (reserved files)

- `experimental/content_lanes/p2-challenge-ch_mat_crawler.py` ? isolated
  two-source adapter with live pool-decode fallback (contract load, live
  decode+hash, stage verify, cave coverage incl. gates, closure verify, packet
  emit).
- `tests/content_lanes/test_p2_challenge_ch_mat_crawler.py` ? 9 focused tests
  (stage parse, contract match, gate/cargo preservation, live-decode disc-gated,
  malformed block/contract/cave rejection, unreadable-source rejection). All
  pass.
- Integrator result:
  `output/deepseek-wave/inbox/autofill-562-result.md` (points at this doc +
  packet JSON at `output/workflow/autofill/p2-challenge-ch_mat_crawler/packet/`).

No placements emitted, no runtime run, no ADMIT. P1/P2 acceptance stays OPEN.
---

# ch_MAT_crawler P1 runtime import (issue #562, lane p2-challenge-ch-mat-crawler-p1)

Implementation owner: Codex through shared account `4laric`. This section
extends the P0 packet above with the P1 private runtime import slice. The P0
decode helpers are reused unchanged (no forked parser).

## P1 staging (`stage_run_layout` / `verify_run_layout`)

The decoded packet is staged into a private run layout:

- `stage-manifest.json`: floors with unit pools, enemy/treasure tokens,
  gates/caps, squad rows, timers, UI index, unsupported semantics and the
  source hash. Weights stay definition inputs; nothing is placed.
- `squad.json`: the starting squad (30 flower Red + 30 flower Yellow = 60).
- `run-config.json`: `window: 960x540`, squad source, unsupported list.
- `markers.txt`: the required receipt-parseable marker contract
  (`P2_CRAWLER_WINDOW`, `P2_CRAWLER_SQUAD`, `P2_CRAWLER_FLOOR_READY`,
  `P2_CRAWLER_ACTOR`, `P2_CRAWLER_PASS`).

Staging fails closed on any packet/contract divergence (floor count, floor
ranges, squad total, timers). `verify_run_layout` re-checks a staged layout
without trusting it.

## Unsupported semantics (recorded, not claimed)

`challenge_host_mode`, `coop_2p`, `key_completion`, `result_screen` — mirrored
from the contract consumer. No host-mode implementation lane exists; a staged
run exercises the cave/arena path only, never Challenge-mode rules.

## Runtime evidence

Recorded in the lane handoff (`prepared/p1-crawler-output/`): leased private
build, fixture provenance, fresh arena with the starting-Pikmin overlay,
960x540 centred startup, captain-safety #632 adoption with guard/source
hashes, and the observed marker log (or the exact defect if the boot cannot
complete). Six gates stay UNTESTED unless genuinely observed.

## P1 host-state boot (observed, generation 5)

Consumed the accepted `challenge-boot-native-fixture` (#672) prerequisite into
the private native worktree: fast-forwarded `fb6419d5` (native base
`ab81cf5d`, validation receipt
`output/workflow/integration-recovery/species-owner/challenge-boot-batch-validation.log`
sha256 `80b05eed3bfb5250546f1c9920d550353ed857405432197888de07d454dd90fd`),
then added the `ch_MAT_crawler` stage entry from the live P0 decode
(ui 29, 2 floors 170.0/120.0 s, roster `[[0,0,30],[0,0,30],...]`, bitter 3,
spicy 4) as native commit `69738be3` (private worktree only, not a shared
edit). The #651 host-mode module TU is unchanged.

Leased private build in `output/shard-challenge-0-p1crawler-build` via the
canonical #672 harness (`configure`, `build` pikmin_pc 618/618 with
`ninja -n` no-work, `fixture`, `guardcheck`): fixture exe sha256
`735fc0c2d77a69cb98a73759e12e37a1049bbda6b85b8e48181a2c949c043c45`.
Captain safety #632 adopted: canonical
`scripts/p2_fixture_captain_guard.h` sha256
`d2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474`
consumed read-only via `CPLUS_INCLUDE_PATH` (never copied); guard runs before
every observed tick; live self-test exit 0 with ordered
BOOT..TICK(x3)..DONE markers; compiled negative guard path exits 86 with
`P2_FIXTURE_CAPTAIN_DOWN` and no PASS.

Observed run (`challenge-boot/run-ui29.log`, leased binary, `ui=29`, exit 0):
`SQUAD_APPLIED`/`BOOT` (population 60, bitter 3, spicy 4, floor 0, 170 s),
three `TICK`s (170 -> 140 s), `FLOOR_ADVANCE` (floor 1, 120 s),
`RETRY_RESET`/`RETRY_STATE` (floor 0, 170 s), `P2_CHALLENGE_BOOT_DONE`
(end=none, score 720). The #651 consumer provably drives this stage's decoded
contract fields (stage select, squad/spray application, per-floor mTimeLimit,
descend, retry).

Scope honesty: host-state simulation only. No live squad, no 960x540 window,
no collision/routes/actors observed; all six gates stay UNTESTED. The
game-linked P2 stage boot (engine loads the cave floors with squad/actors)
remains the open gap.

## Consumer verification of #695 (game-linked no-cargo boot, generation 6)

Consumed the accepted `preview-no-cargo-room-bolt-native` (#695) prerequisite:
fast-forward merge of native `4a69502e` (the #679 + #695 preview reconciliation)
into the private native worktree (merge `2528320f`), and cherry-pick of root
`70596749` (fixture build/run helper) as `c485a321`. No conflicts.

Independently rebuilt `pikmin_pc` in the leased private build directory and
built the fixture with the accepted helper (exe sha256
`007b03f5c8e3b8d81ef713eb1c75a8cab39d0a60dca1f18843f421b22e32a48b`); guard
self-test PASS (7 rows), negative guard exit 86.

Ran the previously-failing scenario (two generator-less room `pr05` bolts, no
cargo) with my own binary in `output/preview-nocargo-runs/nocargo-two`: exit 0,
window `960x540 centered=1`, `P2_PREVIEW_PR05 room_bolts=2 staged=0 cargo=0`,
`P2_ROOM_READY treasure=bolt`, `P2_NOCARGO_RECONCILIATION_PASS treasure=1
squad_alive=20 observed=600`, `PASS NOCARGO_RECONCILIATION`, no
`P2_FIXTURE_CAPTAIN_DOWN`. Control: `nocargo-staged-double` (illegal two staged
bolts) still aborts exit 3 with `P2 preview: duplicate treasure`; `nocargo-one`
PASS. This is a game-linked boot with a live starting squad under #632.

Reported via `workflow.consumer_verification` (verification `c0c9a24b`) with
`passed=true`, `prerequisite_resolved=true`; evidence
`consumer-verify-nocargo-two.log` sha256
`18ef627a7d30545cc373ca93d954696a861ce51a5e6483deabdbd9012f2a9340`.

Remaining gap (unchanged, stage-specific): the engine still cannot boot the
decoded `ch_MAT_crawler` challenge floors with its own squad/actors; the only
game-linked challenge boot available is the fixed preview room. Six gates stay
UNTESTED.

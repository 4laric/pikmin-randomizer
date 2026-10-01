# Cave generator provider contract — read-only review for P1 phases (issue #129)

Lane `cave-generation-contract-review`; planning-only, read-only.
Implementation owner: Codex through shared account 4laric; executing
contributor Muse Spark 1.3 (worker muse-l60, generation 2). No
implementation, no builds, no shared edits, no ADMIT. All six runtime
gates UNTESTED; no level acceptance claimed. Issue #129 stays OPEN.

## What was audited (all read-only)

- Native seam `engine/pc_port/pc_p2_cave.cpp` (303 lines) +
  `pc_p2_cave.h` (17 lines), in this worktree's engine export at root
  base `33fa7a91` ("wave: re-export engine/ at native 41786627"),
  with companion headers `pc_p2_cave_anchor.h`,
  `pc_p2_cave_entry_policy.h`, `pc_p2_cave_readiness_policy.h`,
  `pc_p2_cave_transfer.h`, `pc_p2_cave_nav_diagnostics.h`.
- `docs/PIKMIN2_FAMILY_STATUS.md` (ownership snapshot) and
  `docs/PIKMIN2_FULL_IMPL_BLOCKERS.md` (current readiness).
- `docs/PIKMIN2_CAVE_CATALOG.md` / `PIKMIN2_CAVE_DEPENDENCIES.md` /
  `PIKMIN2_CAVE_CHECKPOINTS.md` (P0 inventory + dependency manifests).
- Seven completed P0 cave lanes (tutorial_2, forest_2/3/4,
  yakushima_1/2/3 = 46 floors) via `docs/PIKMIN_CONTENT_IMPORT_LANES.json`:
  floor/unit-pool/roster manifests P1 can already consume.
- Retail trace: `MapRoom::placeObjects`
  (`src/plugProjectKandoU/gameMapParts.cpp:406`) birthing
  `Cave::EnemyNode` (`include/Game/Cave/Node.h:313-339`) via
  `generalEnemyMgr->birth` (`gameMapParts.cpp:495-533`), cited verbatim
  from `docs/PIKMIN2_MAMUTA_ARENA.md` (batch-1 trace follow-ups).

## Generation entry points (pinned citations)

`engine/pc_port/pc_p2_cave.h` declares the provider boundary:

| Entry | Header line | Source line | Role |
|---|---|---|---|
| `pc_p2_cave_setup` | :4 | `pc_p2_cave.cpp:87` | entry-file squad restore; `P2_CAVE_READY` at :143 |
| `pc_p2_cave_tick` | :5 | `pc_p2_cave.cpp:239` | per-frame nav + extinction-driven checkpoint |
| `pc_p2_cave_request` | :6 | `pc_p2_cave.cpp:146` | hole/geyser descent request |
| `pc_p2_cave_checkpoint` | :7 | `pc_p2_cave.cpp:155` | transfer-file write; `P2_CAVE_TRANSFER` at :232 |
| `pc_p2_cave_exit_after_checkpoint` | :9 | `pc_p2_cave.cpp:235` | process exit code 42 |
| `pc_p2_cave_floor` / `is_beasts` | :10–11 | — | floor + Beasts selectors |
| `pc_p2_cave_boundary_token` / `receipt_prefix` | :12–13 | — | save/receipt identity |
| `pc_p2_cave_draw_transition` | :15 | `pc_p2_cave.cpp:262` | hole/geyser marker (`P2_CAVE_MARKER_DRAW` at :265) |
| `pc_p2_cave_interact` | :17 | `pc_p2_cave.cpp:147` | guarded F6 handoff |

Squad restore emits `P2_CAVE_RESTORE species=%d maturity=%d` per member
(`pc_p2_cave.cpp:113`); nav diagnostics emit `P2_CAVE_NAV …` at :67–70;
the anchor prints `P2_CAVE_ANCHOR` at :130 and the transition model
`P2_CAVE_VISUAL_READY` at :142. Entry profiles
(`pc_p2_cave_entry_policy.h:4–13`) gate versions/floors/tokens; anchors
(`pc_p2_cave_anchor.h:7–33`) enforce hole/geyser kind, radius 20–150,
and ±100000 bounds.

## Retail-vs-port gap (per P1 requirement)

| Requirement | Retail behavior | Port status | Owner work item |
|---|---|---|---|
| Floor topology from unit pools | caveinfo f008 pool + MAP unit rooms/doors assembled per floor | Absent; static preview room only | Add pool selection + room assembly driven by P0 unit manifests |
| Enemy/treasure actor spawn | `MapRoom::placeObjects` births `Cave::EnemyNode` via `generalEnemyMgr` | Absent; no caveinfo roster consumer | Add roster-driven spawner on assembled rooms |
| Door/waypoint route graph | Unit doors/links form the traversable graph | Absent; anchor radius + Pod fallback only | Add route graph from unit door links; extend #193 nav diagnostics |
| Hole/geyser placement | Transition geometry per floor from cave data | Staged sidecar file only (`p2-cave-transition.txt`) | Derive transition anchors from decoded floor data |
| Schedules | Per-floor schedule parameters gate exits | Absent; world clock pinned | Add schedule parameters to the floor-manifest consumer |
| Squad/descent persistence | Cave save filter carries squad across floors | Present: `P2_CAVE_TRANSFER` file + per-member `P2_CAVE_RESTORE` | None; consume as-is (Bulbmin transition rules preserved) |

Already provided elsewhere (cited, not duplicated): fallback ring +
down/up arrow marker (`pc_p2_cave.cpp:279–303`, `P2_CAVE_MARKER_DRAW`);
nav rate diagnostics (`#193`, `P2_CAVE_NAV` at :67–70); transfer file
format `P2_CAVE_TRANSFER_<schema>` (:222–224) with Bulbmin ledger commit
after durable write (:228); Beasts floor 2–4 paths (:96, :118–168);
`P2_BEASTS_CARGO_TERMINAL_READY` (:123). Lanes 34–51 + #468 retain all
prior generator/physical-loop behavior; consume, do not duplicate.

## Minimal port/build plan for the generator owner (files, order, validation)

1. New `engine/pc_port/pc_p2_cave_generate.{h,cpp}` reading one decoded
   floor manifest (P0 packet shape): select unit pool, place rooms,
   spawn roster minima, wire door links, derive the transition anchor.
   No changes to `pc_p2_cave.cpp` transfer/restore/checkpoint logic.
2. Narrow hook: call the generator from `pc_p2_cave_setup` after
   `P2_CAVE_READY`, reusing `p2_cave_read_anchor` validation ranges.
3. Root harness: fresh private arena per lane, current overlay squad,
   960×540 centered window; assert assembled rooms match pool geometry
   and roster spawns match caveinfo minima.
4. Validation: existing transfer files still parse; `ninja -n` clean;
   new markers enumerated in this review's checker; no ADMIT change.

## #186 review draft (for the generator owner to file)

```
#186 review request: cave generation provider seam (issue #129)

Scope: add retail cave generation behind the existing pc_p2_cave
transfer boundary. No changes to squad restore, checkpoint format,
Bulbmin transition rules, Beasts paths, or nav marker strings.
Files (audited export, engine/pc_port):
- pc_p2_cave.cpp:87 pc_p2_cave_setup (entry-file squad restore),
  :113 P2_CAVE_RESTORE, :143 P2_CAVE_READY, :155 pc_p2_cave_checkpoint,
  :232 P2_CAVE_TRANSFER, :239 pc_p2_cave_tick, :262 pc_p2_cave_draw_transition
- pc_p2_cave.h:4,5,6,7,9,10,11,12,13,15,17 entry declarations
- pc_p2_cave_anchor.h:7 P2CaveAnchor, :20 p2_cave_read_anchor
- pc_p2_cave_entry_policy.h:4 P2CaveEntryProfile, :5 p2_cave_entry_profile
Validation: P0 unit manifests resolve; assembled rooms match pool
geometry; roster spawns match caveinfo minima; existing transfer
files still parse; ninja -n clean; no ADMIT change.
```

(A machine copy of this draft is returned by
`experimental/pikmin2_cave_generation_contract.review_draft()`.)

## What P1 can already consume

- 46 floors of P0 unit/roster manifests (tutorial_2: 9, forest_2: 5,
  forest_3: 7, forest_4: 7, yakushima_1: 5, yakushima_2: 6,
  yakushima_3: 7) plus `dependencies.json`-style resource closure
  (432 entries / 167 unit candidates per `PIKMIN2_CAVE_DEPENDENCIES.md`).
- The transfer boundary: `P2_CAVE_TRANSFER_<schema>` in,
  `P2_CAVE_RESTORE` per member out — stable across this review.
- Probe tooling in this lane: `experimental/pikmin2_cave_generation_contract.py`
  (stdlib-only surface checker; 7 tests + 4 subtests pass, including a
  live audit of the engine export that skips cleanly if absent).

## Dependencies and explicit non-goals

- Provider stays with its future owner; this review unblocks nothing by
  itself. #468 (unassigned, per-treasure hazard gating) is excluded.
- Keep issue #129 OPEN until its scope is done. No runtime, build,
  shared-edit, or ADMIT change was made here.
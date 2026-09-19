# Wild-pellet (pb01) tlep format pin-discovery (#825, consumer #561)

Tooling-only pin-discovery. Owner: Codex through shared account 4laric.
Downstream blocked consumer `p2-challenge-ch_mat_route_rover-p1` (#561,
blocked gen 20). Recovery request
`1282ac9d1a5bce83b7a826f8a9fce7870411e14b3df7507f331770529daf13cb`
(scope challenge-0). #561 evidence consumed read-only; no shared/native/
CMake/manifest edits, no builds, no launches, no ADMIT, no gameplay
acceptance. All six runtime gates UNTESTED.

Root pin: `3a33cbdefd5e4057eef9fb0d824cce4510ddab05` (lane worktree
`output/workflow/autofill/planning-shards/challenge-0/prepared/wild-pellet-format-pin-root`,
branch `codex/wild-pellet-format-pin-root`). Native: none (tooling-only).
All `engine/...`, `scripts/...`, `experimental/...` citations are
worktree-relative file:line references at that pin.

## 1. Problem (traced, read-only)

#561 gen-20 staged `p2-pod.txt` (`P2_POD_1 route_rover_pod 180 15 25 /
Kochappy 2`), eliminating the gen-17 aiTransport PANIC: `run-rover-23`
reaches `P2_POD_READY`, all 7 `P2_CHALLENGE_*` markers true, `CAVE_READY
survivors=60`, no panic, no `CAPTAIN_DOWN` — then exits 3 when a wild arena
pellet (model pb01) is carried to the Pod and the harness aborts on
unregistered cargo. Evidence (all read-only, owned by the #561 lane):

- `.../p1-route-rover-launch/out/run-rover-23/native.log:824` —
  `[Pikipelago] P2_POD_READY treasure=route_rover_pod value=180 weight=15 capacity=25 pokos=0`
- `.../run-rover-23/native.log:924` —
  `[Pikipelago] P2_ROOM_READY treasure=route_rover_pod carry=15 repairs=1`
- `.../run-rover-23/native.log:995` (final line) — `Unregistered P2 pod
  cargo id=70623031 view=0000000000000000 pellet=... treasure=...; refusing
  seed side effects` (`0x70623031` = ASCII `pb01`; note `view=0`).
- `.../out/run-rover-23-result.json` — exit 3, `P2_POD_READY: true`, 7/7
  challenge markers true, `panic: false`, `captain_down: false`.
- `.../out/consumer-evidence-561-gen20.md:13-18` — root-cause chain naming
  the wild pellet, the 53 staged tlep records, and the two legitimization
  directions (staging-side tlep work or corpse-registry extension).
- `.../out/run-rover-23/assets/dataDir/stages/chal0/default.gen` —
  sha256 `8a5f1853...dd38a3d` (full: see §2), 137 records, 53 `tlep` rows.
- `.../out/run-rover-23/p2-pod.txt` — the staged pod config quoted above.

## 2. Exact wild-pellet tlep record format (pinned, no invented formats)

` tlep` rows are pellet generator records (`tlep` reversed = `pelt`,
matching `ikip`→piki / `iket`→teki / `ssob`→boss). Framing follows the
shared room parser (`scripts/preview_pikmin2_room.py:12-18`): `1.0v`
header, records opened by `    0.0v` at byte 24, big-endian record count at
byte 20. Record-relative layout, verified byte-for-byte on the staged arena:

| Bytes | Field | Value / encoding |
|---|---|---|
| 0:8 | record framing | `    0.0v` |
| 8:12 | generator id | little-endian u32 (roster/native convention) |
| 16:48 | label | 32-byte name (editor/shift-jis garbage, not identity) |
| 48:60 | position | 3 big-endian floats |
| 60:72 | offset | 3 big-endian floats (zeros observed) |
| 72:76 | kind | `tlep` |
| 76:80 | version | `0.0v` (string, unlike teki int version 10) |
| 80:84 | pellet model | 4 stored bytes, reversed-ascii FourCC |
| 84:164 | area/type params | `pint` area + `1one` spawn + `b00/b01/p00/p01/p02` keys, `ffffffff` terminators |

Observed rows are 164 bytes each. The stored-order convention is
corroborated read-only by the #654 provider
(`.../provider-runtime-fixtures/prepared/cave-overlay-root/experimental/pikmin2_cave_arena_overlay.py:29`,
`PR05_MODEL = b"50rp"`, and `:58-86` decoding generator id as LE u32 at
offset 8 with the model at row[80:84]).

Model histogram of the 53 staged tlep rows (decoded FourCC → count):
pr01×16, py01×11, pb01×10, pb05×4, py05×4, pr05×2, py20/pr20/pr10/py10/
pb10/pb20×1 each. 51 of 53 rows are non-`pr05` wild pellets. Example:
record index 14, generator id 6357100, stored model bytes `10bp`
→ `pb01`, position (-601.40, 0, 1680.85).

Pose convention: position+offset at 48:72, never Euler rotation
(`experimental/pikmin2_generator_pose.py:6-10`). The only other in-tree
`tlep` row consumer repositions rows without decoding the model
(`experimental/pikmin2_uji_bite_fixture.py:52-60`). The enemy audit
parser covers `iket|ssob` rows only, so `tlep` (and `ikip`) rows are
outside its scope (`scripts/audit_enemy_slots.py:70-76`) — no live lane
owns the wild-pellet record format.

Retail model check: `pb01` is Blue 1-pellet in the pellet table
(`engine/src/plugPikiKando/pelletMgr.cpp:1490`).

## 3. Exact corpse-registry binding (pinned)

Pod delivery is `pc_p2_preview_deliver`
(`engine/pc_port/pc_p2_preview.cpp:346-436`). For a pellet delivered with
the Pod anchor set, the receipt chain at `:360-411` is, in order:

1. `p2-cargo.txt` spec match → `treasure:<instance>`
   (`:360-361`; spec format `P2_CARGO_1`, generator/instance/model/value/
   weight/slots at `engine/pc_port/pc_p2_cargo.h:23-36`).
2. `pellet == previewTreasure` → `treasure:<treasureId>` (`:362`).
   Only `pr05`-model pellets are ever scanned into `spawned`/`previewTreasure`
   (`:178-202`, tally at `:203`); the draw gate likewise admits only
   `pr05` (`:340`).
3. Uji/mamuta/mar/bombsarai/kurage/sarai/otakara/waterwraith/king/queen/
   groink/fuefuki/longlegs sidecar receipts (`:363-406`), all keyed on
   enemy actors/views — none binds a wild pellet model or pellet
   generator id. The Uji sidecar is Teki-keyed
   (`engine/pc_port/pc_p2_sheargrub.cpp:72`, setup `:73-89`).
4. `corpses` map (`:407-410`), filled exclusively with `TEKI_Chappy`
   actors (`:120-121`, via `:114-124`; map declared at `:102`).
5. Else fail-closed abort at `:409`: `Unregistered P2 pod cargo
   id=%08x ...; refusing seed side effects` + `std::abort()` (exit 3).

`cargoFree` mode also aborts on any delivery (`:359`), and the preview
policy forbids cargo-free runs from carrying treasure actors at all
(`engine/pc_port/pc_p2_preview_policy.h:12-16`). Pod config parsing and
`P2_POD_READY` are at `:230-248`.

## 4. Finding: needs-engine-change-or-staging-suppression

No receipt branch binds wild pellet models or pellet generator ids, so
**every** non-`pr05` wild pellet delivered to a podded preview aborts at
`engine/pc_port/pc_p2_preview.cpp:409`. The aborting pellet additionally
carries a **null** `PelletView` (`view=0` in the log line), so even the
`PelletView*`-keyed `corpses` map could never match it without an
engine-side model/generator-keyed pellet receipt path. The `run-rover-23`
log also shows `P2_POD_CORPSES_REBOUND before=0 after=0`: the registry
held zero entries for this arena.

Legitimization therefore needs exactly one of:

- (A) **Staging-side suppression**: drop/neutralize non-`pr05` `tlep`
  rows before staging (no engine change; recommended first slice, §5), or
- (B) **Engine-side registry extension**: a pellet-model/generator-keyed
  receipt branch in `pc_p2_preview_deliver` (+ draw/scan coverage, shared
  `#186` review, toolchain restore, private native worktree/build and
  consumer revalidation). Not owned by any live lane; not attempted here.

The companion tool `experimental/pikmin2_wild_pellet_format_pin_discovery.py`
encodes this pin read-only (`--gen/--pod` → JSON audit, exit 2 fail-closed
on missing/malformed inputs) and is covered by
`tests/test_pikmin2_wild_pellet_format_pin_discovery.py` (synthetic-layout
unit checks plus a `WILD_PELLET_ARENA_GEN`-gated real-arena proof asserting
137 rows / 53 tlep / pb01×10 / pr05×2 / the staged sha256; skips without
the env pointer so no sibling-lane path leaks into the integration line).

## 5. First bounded executable legitimization slice (recommended)

- Title: suppress non-`pr05` wild-pellet `tlep` rows for
  `ch_MAT_route_rover` staging (direction A).
- Owned files (new lane, exact): 
...[truncated 2085 chars]

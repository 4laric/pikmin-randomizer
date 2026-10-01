# P2 smoke seeds: any playable species on any ordinary slot (#944, #948)

Owner ruling (2026-09-29): hand-played smoke seeds ignore the committed
placement approvals. Since #948 the root placement document is the only
placement rule there is: native carries no compiled slot lists, so a smoke
seed only needs an override *document* (below); no native switch is required
to bypass anything. Normal seeds keep the committed document.

Two halves:

* **Native**: spawns whatever the seed binds. A binding is refused only for a
  runtime incompatibility and always with a `reason=` (`seed-target-mismatch`,
  `protected-drop`, `no-campaign-module`, `registry-full`, or a family's
  `*_UNBOUND ... reason=host_type_mismatch` / `unstaged_*`). The
  `PIKMIN_P2_SMOKE_ANY_SLOT=1` switch (`pc_port/pc_p2_smoke_any_slot.h`) is
  still set by the launcher as the documented smoke-seed marker and keeps the
  netplay force-off latch, but no placement decision depends on it any more.
* **Root** (`scripts/p2_smoke_seed.py`): builds an override placement document
  that pins the listed species round-robin onto an area's ordinary slots
  (optionally the N nearest the landing site, `navi_start` = 0,0), pins bosses
  to arenas, generates + validates the seed with that start area, verifies the
  resolved `p2_layout` is exactly the request, stages content from a per-enum
  cache (extracting only missing species from the ISO), writes `actors.json`
  and a `play.ps1` launcher that sets the env var.

## Make and play a smoke seed (PowerShell)

```powershell
py -3.12 scripts/p2_smoke_seed.py --area foh --slots 4 --near-start `
    --species 58,32 --bosses 94:hope_snagret_pit --seed foh-any-1 `
    --out output/smoke-any/foh-any-1 --iso "C:\Users\alari\Downloads\PIKMIN2 for GAMECUBE.iso" `
    --content-cache output/p2-content-cache `
    --exe output/smoke-foh/exe-anyslot/nectar.exe
& output/smoke-any/foh-any-1/play.ps1          # or: -Exe <other nectar.exe>
```

* `--area foh|impact|navel|spring`, `--slots N|all`, `--species` in the order
  the round-robin walks the slots, `--near-start` orders slots by x/z distance
  from the ship. Arena bosses (73, 94, ...) go in `--bosses ID:ARENA`, never
  in `--species`.
* `smoke.json` in the output dir lists every slot (uid, label, position,
  distance) with its species; `placement-override.json` is the document the
  seed was generated from.
* The cache is per enum dir (`<cache>/<Enum>/`); a species the cache lacks is
  extracted from `--iso` into the run's `content/` and copied back.
* The exe must be built from native `claude/p2-placement-constraints` (#948)
  or later: no compiled slot list, every refusal logged with a `reason=`.
  An exe older than #944 logs `slot-rejected` for the sidecar-recorded
  species (57/58/78/99) on any slot outside its compiled constant.
* Every ordinary campaign generator is a candidate slot now (ground, grub,
  frog, aquatic, flying and dwarf cohorts); `--near-start` sorts them by
  distance from the ship, so the first few are the ones the owner walks
  into. Arena bosses (73/94) may also go in `--species` when the smoke
  override should put them on an ordinary slot (the override relaxes the
  footprint to the slot; real seeds keep the arena rule).

## Evidence to look for

* `P2_GENERATED_PLACEMENT source_id=58 target=<uid> generator=<uid> bound=1`.
* The family's own bind, e.g. `P2_BOMBSARAI_OWN_BIND source_id=58 token=<uid> host_type=11`.
* Any refusal carries a `reason=`; `slot-rejected` no longer exists.

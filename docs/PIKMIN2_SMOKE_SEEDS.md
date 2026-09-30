# P2 smoke seeds: any playable species on any ordinary slot (#944)

Owner ruling (2026-09-29): hand-played smoke seeds ignore the committed
placement approvals. Normal seeds keep full enforcement; nothing below changes
the committed document, the bridge, or the native default.

Two halves:

* **Native** (`pc_port/pc_p2_smoke_any_slot.h`): `PIKMIN_P2_SMOKE_ANY_SLOT=1`
  makes the generated-placement binder accept the seed's own binding on any
  slot (`P2_GENERATED_PLACEMENT ... bound=1 bypass=1` instead of
  `bound=0 reason=slot-rejected`). Unset = inert. Logged once as
  `P2_SMOKE_ANY_SLOT enabled`. `pc_p2_smoke_any_slot_force_off("netplay")`
  latches it off for a process; a netplay session start must call it. Host
  substitution (`p2campaign::hostType`) and each family's own host/content
  bind are unchanged, so a family that cannot run on its host still reports
  its usual `*_UNBOUND ... reason=host_type*` line rather than a silent accept.
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
* The exe must be built from a branch carrying `pc_p2_smoke_any_slot.h`
  (native `claude/p2-smoke-any-slot` or later). An older exe simply logs
  `slot-rejected` for the muse-observer species (41/57/58/78); their own
  family modules still bind by host type.

## Evidence to look for

* `P2_SMOKE_ANY_SLOT enabled` once at first bind.
* `P2_GENERATED_PLACEMENT source_id=58 target=<uid> generator=<uid> bound=1 bypass=1`.
* The family's own bind, e.g. `P2_BOMBSARAI_OWN_BIND source_id=58 token=<uid> host_type=11`.
* Without the env var (a normal launch of the same seed) the same binding logs
  `bound=0 reason=slot-rejected`: enforcement intact.

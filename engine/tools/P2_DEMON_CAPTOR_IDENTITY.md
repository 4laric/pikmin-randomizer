# Lane 30 dedicated captor spawn identity (#242, parent #166)

Follow-up to [the shared-semantics review packet](P2_LANE30_SHARED_SEMANTICS.md).
This slice gives lane 30 an opt-in, PC-only identity for the ordinary spawned
captor so `pc_p2_demon_manager_setup()` no longer keys on the Dwarf Bulborb
placeholder (`TEKI_Chappy`, generator id `385875968`, type `3`).

## Identity added

| Identity | Value | Scope |
|---|---|---|
| `TEKI_P2Demon` (appended teki type) | `35` | PC only. Retail types `0-34` and non-PC `TEKI_TypeCount` (`35`) are unchanged; PC `TEKI_TypeCount` becomes `36`, mirroring the `NAVISTATE_DemonDrop`/`DemonEscape` appended-ID pattern. |
| Reserved captor generator id (`Generator::_70`, readID `'dmn0'`) | `0x646D6E30` | Optional; a stager may tag the lane-30 slot with this generator id while keeping the P1 placement vehicle. |
| Legacy placeholder | generator `385875968`, type `3` | Explicit-only fallback (`PIKMIN_DEMON_ORDINARY_LEGACY_PLACEHOLDER=1`). |

The spawned actor that carries `TEKI_P2Demon` reuses the retail Chappy
parameter/strategy/sound/resource bank because no dedicated Demon teki bank
exists in the port; it is the invisible identity/lifetime anchor, and the Demon
visual is drawn by `P2DemonHost` (which suppresses the anchor draw). The
identity is the distinct numeric type id, not the resource name.

## How setup selects it

`pc_port/pc_p2_demon_identity.h` is an engine-free selector:

- `p2demonid::isDedicatedCaptorIdentity(generatorId, tekiType)` — true when the
  actor carries `TEKI_P2Demon`, or the reserved captor generator id with the
  placement vehicle type.
- `p2demonid::isLegacyPlaceholderIdentity(generatorId, tekiType)` — the old
  Dwarf Bulborb placeholder, never part of the dedicated identity.

`pc_p2_demon_host.cpp::findOrdinaryActor()` now matches on those predicates. The
opt-in path is unchanged and default-off:

- `PIKMIN_DEMON_ORDINARY=<explicit generator>/<type>` — fixed identity (unchanged;
  the existing `ordinary` runtime fixture passes `385875968`/`3` and is
  unaffected).
- `PIKMIN_DEMON_ORDINARY=1` with no explicit identity — selects the dedicated
  captor identity. It fails closed if no dedicated actor is present.
- `PIKMIN_DEMON_ORDINARY=1` + `PIKMIN_DEMON_ORDINARY_LEGACY_PLACEHOLDER=1` —
  accepts the legacy Dwarf Bulborb placeholder for regression reproduction.

`pc_p2_demon_host.cpp` also static-asserts `TEKI_P2Demon ==
p2demonid::kCaptorTekiType` and `TEKI_P2Demon < TEKI_TypeCount`, so registration
is proven at compile time.

## Tests / build evidence

- `tools/p2_demon_identity_test.cpp` (new, engine-free, CTest target
  `p2_demon_identity_test`): asserts the dedicated/legacy selection split,
  ordinary-slot rejection, and ABI-stable constant `35`. Result:
  `PASS P2_DEMON_IDENTITY`.
- Base: `4bb302c8668ca151919fbc626ace4b7f28926818` (`opencode/p2-lane30-rebase`).
  Branch: `opencode/p2-lane30-teki`, worktree `output/native-lane30-teki`.
  Private build: `output/native-lane30-teki-build` (Ninja, Release,
  `PIKMIN_NATIVE_JAUDIO=ON`, `-j4`).
- `ninja -n pikmin_pc`: `no work to do.` `bin/nectar.exe` SHA-256
  `A9215D47D4D9BA59FB8A18C507104C68C8CE4AAACB0FEC6EDAC9406208311B82`.

## Shared-file edits and review asks

| File | Edit | Review |
|---|---|---|
| `include/teki.h` | PC-only appended `TEKI_P2Demon=35` before `TEKI_TypeCount` | **#186 / lane-01 ID allocation.** Confirm the appended PC-only teki ID and PC `TEKI_TypeCount=36`, with retail `0-34` and non-PC count `35` preserved (same pattern as `NAVISTATE_DemonDrop/Escape`). |
| `src/plugPikiNakata/tekimgr.cpp` | PC-only `typeNames`/`typeIds` entry reusing the Chappy bank | **#186 / lane-01.** Confirm reusing the retail Chappy param/model/sound bank as the invisible anchor is acceptable until a dedicated Demon teki bank exists. |
| `src/plugPikiNakata/tekinakata.cpp` | PC-only `TaiChappyParameters` + `TaiChappyStrategy`/`TaiChappySoundTable` registration for `TEKI_P2Demon` | **#186 / lane-01.** Registration ownership; no retail type changed. |
| `pc_port/pc_p2_demon_identity.h`, `pc_port/pc_p2_demon_host.cpp` | New identity selector + ordinary-setup selection | Lane 30 family-local; default-off. |
| `CMakeLists.txt` | New engine-free CTest target | Additive; no new target/define. |

Lane-02 roster ask: record `TEKI_P2Demon` as the lane-30 captor spawn identity
(PC-only, default-deny until a generated seed emits it), distinct from the
Dwarf Bulborb placeholder alias.

## Runtime proof: dedicated identity spawned through the ordinary chain

The dedicated identity is now actually spawned, through an ordinary stage
generator, and bound by the production manager. No shared stager was edited.

- Branch `opencode/p2-demon-identity-spawn` from `cb624af6` (worktree
  `output/native-lane30-rebase`); private build `output/native-lane30-rebase-build`
  (`ninja -n pikmin_pc` = `no work to do.` — fixture-only change, production
  untouched). Fixture built with
  `output/p2-main-review/scripts/build_pikmin2_fixture.py` against that build.
- Fixture `output/demon-identity-fixture-01` (`status=built`, expected native
  head `5c73dec0541a4a9e150bea604eff875cdb220ed0`), exe SHA-256
  `9DD34040987C204FC76C6B38433F2319852C2B46A797B8756A0C0DBA8825022A`.
- Spawn mechanism: **lane-local post-process** (`tools/p2_demon_identity_arena.py`),
  run after `scripts/preview_pikmin2_room.py`. It rewrites only the lane-owned
  session's `dataDir/stages/chal0/default.gen`, changing the single enemy
  generator's v10 teki type byte from `3` (`TEKI_Chappy`) to `35`
  (`TEKI_P2Demon`). The generator still carries identity `385875968`; no shared
  lane-03/lane-05 file and no engine source changed.

Dedicated session
`output/demon-identity-run-01/dedicated/10548ffa333f4027a42b5a13a8476ca6`,
run `DEMON_HOST_MODE=ordinary_dedicated` (`PIKMIN_DEMON_ORDINARY=1`, no
`PIKMIN_DEMON_ORDINARY_GENERATOR/TYPE`):

```text
ARENA dedicated ... old_type=3 new_type=35
P2_DEMON_HOST_WINDOW size=960x540 pos=373,263 display=1707x1067 centered=1
DEMON_ORDINARY_IDENTITY generator=385875968 type=35 dedicated=1 legacy=0 explicit=0
DEMON_ORDINARY_BIND generator=385875968 type=35 anchor=(196.95,0.00,-165.55) captain=(121.49,0.00,157.90)
DEMON_ORDINARY tick=420 phase=1 ...                 (source target/approach)
DEMON_ORDINARY tick=480 phase=3 ... stuck=1 bound=1 (real mouth capture)
DEMON_ORDINARY tick=840 phase=2 ... state=36        (registered DemonDrop)
DEMON_STATE_RESUME owned_delivery=1 phase=3
DEMON_STATE_DAMAGE generation=1 accepted=1 before=100.000 after=90.000
PASS DEMON_HOST ordinary_spawned_captor_acquire_attack_capture_drop (ticks=898)
```

Legacy placeholder session
`output/demon-identity-run-01/legacy/b7e059bbfda344a2b7e38c5cf504a414`, run
`DEMON_HOST_MODE=ordinary_legacy` (`PIKMIN_DEMON_ORDINARY=1` +
`PIKMIN_DEMON_ORDINARY_LEGACY_PLACEHOLDER=1`):

```text
DEMON_ORDINARY_IDENTITY generator=385875968 type=3 dedicated=0 legacy=1 explicit=0
DEMON_ORDINARY_BIND generator=385875968 type=3 anchor=(187.90,0.00,-147.59) captain=(121.49,0.00,157.90)
PASS DEMON_HOST ordinary_spawned_captor_acquire_attack_capture_drop (ticks=873)
```

Regressions on the same fixture (`ordinary` explicit identity on the unpatched
legacy arena; the rest are identity-independent), all `rc=0` and `PASS`:

```text
PASS DEMON_HOST ordinary_spawned_captor_acquire_attack_capture_drop (ticks=874)
PASS DEMON_HOST natural_captor_acquire_attack_capture_drop (ticks=308)
PASS DEMON_HOST natural_idle_captor_acquire_attack_capture_drop (ticks=297)
PASS DEMON_HOST injected_capture_catchfly_drop_recovery
PASS DEMON_HOST live_owner_mouth_capture_release
PASS DEMON_HOST teardown
```

`natural`, `natural_idle`, `drop`, `livecapture` and `teardown` do not observe
the arena enemy; `ordinary` uses the unpatched legacy arena (explicit
`385875968`/`3`, `dedicated=0 legacy=0 explicit=1`). Helper:
`tools/p2_demon_identity_run.py`.

## Remaining limits

- The dedicated generator reuses the retail Chappy parameter/model/sound bank
  (there is no dedicated Demon teki bank in the port); the type id is the
  identity, and `P2DemonHost` draws the visual while the anchor is the
  lifetime/identity token.
- The spawn side is a lane-local arena post-process, not yet a lane-03
  generator/manifest bridge. Folding `TEKI_P2Demon` into the opt-in generated
  seed path (rather than rewriting stager bytes after the fact) remains the
  generated-session/admission step for assignment 1 / lane 03.
- The reserved captor generator id `0x646D6E30`/`'dmn0'` remains supported by
  the selector but is not exercised by this run; the type-35 arm is proven.

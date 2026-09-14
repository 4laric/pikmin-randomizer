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

## Remaining runtime proof

- Real-GL (reserved slot) generated-session spawn: the room stager
  (`scripts/preview_pikmin2_room.py`, root/lane-03) must emit a generator whose
  actor carries `TEKI_P2Demon` (or tag the reserved captor generator id), then
  run `PIKMIN_DEMON_ORDINARY=1` with no explicit identity and observe
  `DEMON_ORDINARY_IDENTITY ... dedicated=1` plus the natural
  acquire/attack/capture/drop chain. Not run here (no GL slot; native-only
  worktree).
- Lane-03 spawn/manifest bridge: select the dedicated identity in the opt-in
  generator rather than editing stager bytes; this native slice registers and
  selects it only.

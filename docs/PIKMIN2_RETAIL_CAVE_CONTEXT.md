# Retail cave content and scene authority (#1274)

Implementation owner: Codex through `4laric`. This lane owns retail cave source
descriptors and physical content provider binding. The #930 owner retains cave
transitions, party capture, native SAVE and cache ownership.

`experimental.pikmin2_retail_context` verifies each catalog source against the
local GPVE01 revision-0 disc, reparses the complete cave and unit definitions,
and resolves numeric enemy IDs and boss membership from the original source
`include/Game/enemyInfo.h`. Host-decoded rows cannot acquire authority by retaining
a correct source-file hash while changing their contents. Derived assets and
source text stay in ignored private output; the native generated table contains
only descriptors and roster metadata.

The authenticated catalog has 14 caves and 105 floors in original order:
`tutorial_1` 2, `tutorial_2` 9, `tutorial_3` 8, `forest_1` 5, `forest_2` 5,
`forest_3` 7, `forest_4` 7, `yakushima_1` 5, `yakushima_2` 6,
`yakushima_3` 7, `yakushima_4` 5, `last_1` 10, `last_2` 15, `last_3` 14.

Native API: `pc_port/pc_p2_retail_cave_context.h`, namespace `p2retail`.
`descriptor(cave)` and `definition(cave, floor)` expose immutable metadata.
They do not establish an installed scene. Engineering aliases return no retail
descriptor. `FloorSession::activate` requires complete provider preflight,
physical installation, and exactly one distinct actor binding for every selected
source instance. `FloorIdentityAuthority::expectedBirth` independently issues
each expected source row/ordinal/epoch/activation from the selected native floor
transaction before provider installation. A provider cannot authenticate its
own forged epoch by returning the same value twice. A partial installation revokes authority and requires native
cleanup; failed cleanup retains provider ownership for retry. An unsupported
row must fail preflight before birth. Weighted selection and gate/cap floors
currently refuse until their actual selection adapters exist.

`snapshot` requires the exact seed, visit, layout SHA-256 and native scene serial.
It exposes source member, full source SHA, catalog SHA, 1-based current floor,
max floor, story mode and in-cave status. Last-floor status derives from those
bounds. The SAVE owner must persist source/layout/visit identities and restore
actual physical content before publishing fresh-process scene authority.
The header does not change SAVE, campaign calendars or transition routing.

`LiveBinding` distinguishes `Live`, `ConsumedTreasure`, `RetiredNative` and
`SourceSuppressed`. Absent instances retain the full expected source identity,
carry no actor pointer, and require provider verification against canonical
treasury receipts or actual native SAVE/cache/population state. Consumed treasures
are not reborn. Pom birth suppression requires the actual retail population gate;
it is not death or conversion-budget consumption.

`heldDrop` additionally requires an actor/instance association and a release event
verified by that floor's actual provider. A nonzero caller-supplied event alone
does not qualify. Boss membership comes from `IS_ENEMY_BOSS`, not the bitter-drop
profile or the presence of a treasure on the last floor.

Emergence's `YellowKochappy` is **EnemyID 45**, the Snow Bulborb; four and seven
are its counts on floors one and two. Floor two also contains BlackPom 6 (two),
KareOoinu_s 91 (six), KareOoinu_l 92 (four), Clover 47 (two), and loose `map01`
(one). Loose Atlas retains its catalog strength/slots of 101 and requires actual
Purple carrying strength. Projection `map02` is also a loose surface item.
Neither source placement receives the EnemyBase boss-drop weight adjustment.

Initial native descriptor/context policy tests pass, including partial-install
cleanup and stale-scene refusal. This is **not** physical floor, gameplay or
save/resume qualification. Source Snow45, foliage92, Violet bud6, physical cargo,
selected collision/routes/exits and live provider installation must all compose
before those gates can pass. Engineering Atlas relocation and P1 dwarf templates
are not accepted as literal content.


`pc_p2_retail_cave_native.h` supplies the actual `NativeFloor` orchestrator.
Its default source45 adapter calls the Snow leaf's real resource, reservation,
birth and association functions. Additional `FamilyOps` must provide their own
native prepare/birth/bind/release/cancel/retired operations. The source registry
uses strict `SourceForm::CaveTekiInfo` provenance; `CAVE` is our association
transport marker, not a retail GenEnemy version. Source Generator leases survive
until their last actual actor retires.

The required `SceneOps` owner verifies selected card/session bytes, actual mode,
StageInfo, installed geometry/routes, Pod, exit and cargo before installation.
`prior` checks the independently selected ledger before enemy birth; verified
`RetiredNative` entries stay absent. Physical suppression still comes from the
actual Pom population query. Cargo adapters use `placement` only while the exact
selected scene is prepared; it reparses the raw source-plan bytes against the
whole-plan SHA on every lookup. `FloorProvider::commit` runs after the complete
roster is verified and before `FloorSession` publishes active authority.

BlackPom natural death already invokes its floor callback and then its own leaf
cleanup before manager reuse. Its family retirement callback must be an explicit
no-op; its `Native::onDeath` callback performs the floor receipt/registry step.
Explicit teardown instead sets `retireBeforeRelease` and calls `Native::release`.
Calling `nativeRetired` before explicit release would discard leaf ownership too
early. A partial cleanup failure must retain the owner and native allocations.

The immutable catalog accessor now compiles once in
`pc_p2_retail_cave_catalog.cpp`. CMake links its archive to native consumers;
direct standalone policy builds must also compile that source. Private context
and registry CTests pass, as do the native orchestrator and group-engine object
compiles. The actual selected `SceneOps`, full linked build, ordinary Emergence
mechanics and fresh SAVE restore remain unqualified.


Private physical composition now also provides `bindFoliage` and `bindBlackPom`.
Foliage47/91/92 shares one whole-roster reservation. BlackPom uses the source6
leaf and existing Purple core; its helper refuses missing population or donor
consumer callbacks. `FamilyOps::birth` receives the prepared floor snapshot so
population queries can authenticate the actual selected scene. Cached bud
suppression requires independent selected cache/current-population proof.

Once the actual selected scene and SAVE adapters are installed, a short ordinary
acceptance script is: start with20 Pikmin in the centered960x540 window; enter the
actual authored Emergence entrance; fight the four source Snow Bulborbs and carry
the two loose treasures into the original Pod; descend through the original hole;
fight the seven source Snow Bulborbs and walk past the6/4/2 authored foliage;
convert and pluck ten Purple Pikmin from the two Violet buds; carry source Atlas
with ten Purple and at least one ordinary Pikmin into the Pod; use the final-floor
geyser; reenter and verify defeated/consumed state; write SAVE and verify the same
state after a fresh process. This is a pending human script, not recorded evidence.
Do not substitute engineering Atlas relocation, reduced weight, synthetic intake,
receipt injection or a mocked restored roster for these mechanics. Partial exits
with uncollected cargo additionally require actual settled-body graph retention.

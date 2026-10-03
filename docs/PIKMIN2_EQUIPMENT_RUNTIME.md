# Original campaign equipment runtime (#141)

Implementation owner: Codex through shared GitHub account `4laric`.
Native slice: `e7379fefa5109b347fb630261168ae4b4e4928d5` followed by course-mask
API `99415c29184354e935012e2cd2e8b4f4ec702726` and held-whistle compatibility fix
`2019cc1d156da04e63b4e65c42932382f3c7ddab`, based on the
coordinator-approved `6d7943ed56807e59147b4c03f11004008adc6b1a`.
Retail parameter correction `d7101cc357ebc90632813a64c613aae53716bf32` follows
the composed `3f72bd8f19ab289eb5cea412cbba7e39842f2f6e` source: Boots speed 205
and Amplifier radius 130 replace incorrectly projected constructor defaults.
See [the source audit](PIKMIN2_EQUIPMENT_AUDIT.md) for all 13 source identities.

`pc_p2_equipment` derives equipment from the selected original campaign's
authenticated treasury receipt query. It grants nothing when the original-session
or treasury provider is absent. Assets, catalogs and loose P1 test fixtures cannot
enable it. There is no additional equipment save ledger: authenticated P2TR1 card
restore supplies the receipts, and queries immediately reflect the restored set.
The Key is deliberately excluded from OlimarData bits; Challenge, story Challenge
unlock and Versus Key behavior remain separate work.

`pc_p2_equipment_reconcile_courses()` applies the source `openCourse(1)` and
`openCourse(2)` effects for `map01` (item index 10, dictionary 184) and `map02`
(index 11, dictionary 185). It never opens Wistful Wild or credits Pokos. The
treasure provider calls it after successful setup and newly accepted completed
native suction. Restore reconciliation needs to occur after the selected card's
validation and the original campaign's course-0-only GameSetup baseline.
`pc_p2_equipment_courses()` exposes that same exploration mask to direct landing
admission (0 without an original session; bits 0..2 within it). The existing travel
menu reads `isStageOpen` before adding each course and omits locked entries.

| Item | Implemented native path | Remaining acceptance |
|---|---|---|
| Dream Material | InteractDenki refuses electric damage/flick | Ordinary electric contact before/after acquisition |
| Amplified Amplifier | Retail q007 130-unit maximum for whistle recruitment and rendered circle, before existing Mods radius scale | Ordinary outside-base-radius recruitment |
| Professional Noisemaker | Existing native sprout self-unbury path enabled by ownership | Ordinary whistle pluck after collection, with Mods disabled |
| Justice Alloy | Source 0.5 shield reduction on captain damage | Ordinary damaging contact comparison |
| Forged Courage | InteractFire refuses fire damage/flick | Ordinary fire contact comparison |
| Repugnant Appendage | Retail q006 205-unit movement speed and wind refusal | Ordinary movement/wind; steep-slope slip remains unsupported |
| Spherical Atlas / Geographic Projection | Source course 1 / 2 projection | Actual source collection, travel, day-end, fresh process |
| Brute Knuckles | Receipt ownership only | Source three-animation combo unsupported |
| Stellar Orb | Receipt ownership only | Source cave light ramp unsupported |
| Prototype Detector | Receipt ownership only | Source radar/map UI unsupported |
| Five-Man Napsack | Receipt ownership only | Source hold-X and carried captain unsupported |
| The Key | No equipment bit | Separate mode effects unsupported here |

Equipment numbers use authored GPVE01 `user/Abe/piki/naviParms.txt`, not only
`include/Game/NaviParms.h` constructor defaults. The private retail resource
at disc offset 770319376 is 3172 bytes, SHA-256
`dfcc8e0cf89195f06ea78fdc1a342631da4e5d2495d85380212af7d72eb2eba0`.
It authors q006=205, q007=130 and q008=0.5. Source `naviWhistle.cpp` reads q007
for the Amplifier. Earlier qualified 2019/composed 3f72 builds used constructor
values 240/200 for Boots/Amplifier and remain historical evidence; they do not
prove these corrected retail values. The correction passes both focused CTests
and a focused no-work dry run. Corrected composed native
`dc89ca98788209f9fda28be5b93a8ecf2457de97`, clean tree
`a363f3f881a3d2cf93d48498e9ec7ac9a6b67a70`, passes the actual private Linux
production build, all nine focused CTests, Ninja no-work and dependency checks.
Production ELF SHA-256 is
`f28e6064d23f2b6fa0ac6cda14d8022eb8eb3f3cff826d26049b187da366902b`.
The profile is Release NETPLAY/JAUDIO/IPO ON, OPTIMIZE OFF, j2.
The 27-file byte-identical maintained export merged in
[PR #1293](https://github.com/4laric/pikmin-randomizer/pull/1293) at
`08c9da35dc5ab35ef211f94d91362fd840854ad8`. The integration owner independently
checked the authored resource values. Ordinary equipment acquisition, map hauling
and campaign save/resume remain open. The legal resource stays private.
Existing AP benefits,
Mods and captain health settings keep their existing composition; original gear
is applied only when its authenticated selected-session query succeeds.

## Verification and gameplay script

Two focused compiled tests exercise the exact source mapping, duplicate receipt
projection, original-session exclusion, restored receipt
rollback, The Key exclusion and idempotent course reconciliation. The projection
test binds engine doubles to the actual `pc_p2_equipment.cpp`; it is engineering
evidence, not gameplay or card I/O acceptance. The five source-audit Python tests
also pass with `PIKMIN2_SOURCE` pointing at the private local research tree.
The initial `e7379fefa` Linux production build and both focused CTests pass,
with no-work dry run and executable SHA-256
`552bc4681c0ca7f1d826a11826f19c992540c8300e78a06c013c0c04c7793268`.
Final `2019cc1d1` Windows/MinGW configuration in private
`output/native-equipment-141-build` compiles all four changed real translation
units (`navi.cpp`, `naviState.cpp`, equipment and whistle-pluck), passes both focused
CMake tests and has a no-work dry run for those objects/tests. This is not a full
Windows link. Final `2019cc1d156da04e63b4e65c42932382f3c7ddab` Linux production
link and both focused CTests also pass, with no-work dry run, clean ldd and ELF
SHA-256 `7d633981b5110377daeb04c9d9fc9d98419f81923f46366d7bcbf2f1998d1dbc`
(15,590,160 bytes). SharedRunner unit `equipment-141-final2019` succeeded in the
same private build graph after preserving the initial executable and result.
Final build evidence is tracked in issue #141; build success does not prove the
gameplay behavior above.
The [immutable terminal receipt](https://github.com/4laric/pikmin-randomizer/issues/141#issuecomment-5967987553)
has SHA-256 `35b0b354184ca285df6ac32ebd5f8a4f207118addebe0d4305ebf16778034204`;
its archive has SHA-256
`f602f8de0bec00f0803c92c299c2cd0bf0c57f1f86ae0de83688c1b95f66b39b`.
The receipt, archive, production ELF and both test ELF hashes were checked locally.
The profile is Release, NETPLAY/JAUDIO/OPTIMIZE/IPO OFF, j4.

The treasure and SAVE owners retain physical receipt and card authority. Both
maps have retail min/max weight 101. Literal source placements are loose treasures:
Atlas is on `tutorial_1` floor 2 (Emergence Cave), and Projection is
`forest/initgen.txt` record 16 at (-1698.020142, -50, 2117.864746).
`PelletItem::Mgr::generatorBirth` / `genPellet::birth` do not set a squad-adjusted
minimum. The separate boss/story/last-floor exception does not apply to either
placement. Keep weight 101 and acquire actual Purple Pikmin for weighted carrying;
ten Purples plus one ordinary Pikmin supply 101 strength within the starting
20-Pikmin population. Do not relabel a loose map as a boss drop or lower its weight.

When the actual source provider and selected-card restore are composed:

1. Launch a fresh private original campaign with 20 starting Pikmin and a centered
   960x540 window. Keep legal assets, saves and logs under ignored output. Stage
   the actual tested item at the start in its valid source context and verify its
   source binding. Disable optional whistle-pluck/radius/health/speed Mods for the
   respective observations.
2. For Atlas, reach actual Emergence Cave floor 2, acquire Purples through its
   actual Violet Candypop Buds and carry the loose map to the treasure receiver.
   For Projection, carry its actual loose Awakening Wood map with sufficient
   Purple strength. Use ordinary controls. Confirm the real
   suction receipt, correct unique source ID and 200-Poko value. Do not edit the
   receipt bitmap, claim the boss-drop exception or lower either map's weight.
3. Return to travel. Atlas must enable Awakening Wood; Projection must enable
   Perplexing Pool. The other unearned course and Wistful Wild remain locked.
4. Complete and save the day normally, quit, then start a fresh process with the
   same selected card. The map remains available and its source cargo stays
   consumed. Revisit without another acquisition grant or 200-Poko credit.
5. For captain items, collect the actual source item and exercise the native path
   in the table. Record the before/after observation and a day-end/fresh-process
   repetition. Each supported path needs its own ordinary acceptance.

Until those steps pass, map collection, card persistence and captain effect
gameplay gates remain open. Asset presence and synthetic receipts satisfy none
of them.

## Short direct-play sequence

Use the verified current package's normal bindings: WASD movement, Space/left
click to throw, Left Shift/right click to whistle, and Enter to confirm. Check
F1 input settings if bindings were changed. Each effect segment should take
30–90 seconds with the actual item and its test target close to the start.

Before the package is handed to a player, its owner must verify the live source
item/receiver bindings, retain the item's retail weight and source context, and
confirm its actual original-session authority. Source actors, source assets and
an empty receipt state are prerequisites; do not create an acquired item bit.
Start with the supported squad/window baseline and unmodified captain health.
Save all logs and captures privately. Stop the segment on captain knockout.

1. **No-receipt comparison, 30–45 seconds:** keep Whistle Pluck OFF and radius,
   captain health and speed at 100%. Whistle a nearby grounded sprout; it must
   stay buried. With no Amplifier, a Pikmin outside the normal whistle circle
   must stay outside the squad. Record captain motion and one ordinary safe
   damage contact. A P1/AP fallback run proves only that fallback; it cannot be
   used as an original-campaign no-receipt run.
2. **Acquisition, 30–90 seconds:** direct Pikmin onto the actual source item and
   wait for their ordinary haul and completed receiver suction. Record its
   unique source ID/value in the treasury log. Repeat the matched comparison
   without changing settings: Professional Noisemaker should whistle-pluck the
   sprout; Amplifier should recruit the distant Pikmin. For Dream Material or
   Forged Courage, use the same actual electric/fire contact as the comparison.
   Justice Alloy should halve that accepted damage; Boots should change travel
   speed and reject the registered `InteractWind` impulse. Keep each separate
   effect test short and stop on captain danger. Wind adaptations that use a
   different receiver still need their own source review.
3. **Atlas haul:** on the actual Emergence floor-2 source, throw Reds into its
   Violet Buds and pluck the resulting Purples normally. Carry the actual loose
   weight-101 Atlas with at least ten Purples plus one ordinary Pikmin. Finish
   receiver suction, then return to travel and select newly available Awakening
   Wood. Do not lower weight, convert colors directly, move the captain/actors
   through a script, or edit the receipt state.
4. **Day-end/fresh-process:** use normal day completion and Save, quit fully,
   then relaunch the same package/card. Repeat the effect and travel selection;
   consumed cargo stays absent and no extra Pokos/acquisition event appears.

Current source-package boundary: the qualified equipment executable contains
the real effect hooks, but its original-session/treasury dependencies are
intentionally inactive until the actual providers are composed. The SAVE
foundation rejects missing typed course/resource providers before admitting an
original session. Metadata-only packages and the existing White diamond or
held-watch scaffolds cannot establish equipment acquisition. The cargo owner
will supply the first actual gear producer; the retail cave owner supplies the
loose Atlas floor and Violet Bud context. Do not turn those incomplete inputs
into an artificial successful runtime.

## Source flick receiver integration

The source receiver owner calls `pc_p2_equipment_damage(rawDamage)` from
`pc_p2_equipment.h` once when applying Koke END damage. Justice Alloy derives
ownership from the selected original session and authenticated `suit_powerup`
receipt (dictionary 193, OlimarData index 5). Missing authority or receipt returns
the input unchanged. The source shield parameter `q008` defaults to 0.5.

Retail `NaviKokeDamageState::onKeyEvent` moves Fall to Lay on END, then calls
`addDamage(mDamage, mPlaySoundOnDamage)`. Retail `addDamage` first requires an
inactive/absent movie and an active game world, applies armor, rejects a dead or
state-invincible captain and actor invincibility, subtracts the accepted damage,
emits optional feedback, and enters Dead when HP is strictly below 1.0. The
equipment API supplies only the armor projection; the receiver retains these
guards and state transitions. Do not reduce again at flick initialization or
transit. Do not use `pcNaviHurt` for this source receiver: that private wrapper
also applies P1 Mods and hardmode scaling.

The historical standalone equipment qualification pin is
`2019cc1d156da04e63b4e65c42932382f3c7ddab`.
Its initial equipment implementation is `e7379fefa5109b347fb630261168ae4b4e4928d5`,
followed by the course-mask API and held-whistle compatibility fix. Runtime
composition also needs the canonical treasure provider and genuine original
session bootstrap; linking the weak API alone grants nothing. This integration
guidance does not qualify actual armor acquisition or gameplay. The current
qualified composition is `dc89ca98788209f9fda28be5b93a8ecf2457de97`, including
the retail parameter correction and byte-identical source export in merged
[PR #1293](https://github.com/4laric/pikmin-randomizer/pull/1293). Ordinary armor
acquisition and gameplay remain open.

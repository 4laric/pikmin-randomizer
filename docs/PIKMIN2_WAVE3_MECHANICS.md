# Wave 3 mechanics lane: 26, 27, 84, 93, 99 (#964)

Lane "Mechanics species: water, Chrysanthemum, Volatile Dweevil, Waterwraith" of
the wave 3 enemy import. Tracking issue: 4laric/pikmin-randomizer#964. Branches:
root `claude/p2-wave3-mechanics` (origin/main `3fc77bf6`), native fork
`claude/p2-wave3-mechanics` (fork main `bbb9821f7`).

Owner bar applied to every species: its own P2 behaviour (the transcribed source
FSM, not the P1 AI underneath) proven by a natural kill, carry and Onion receipt
on the species' own generator token in a real campaign run. Bot power mode is
accepted. Spawn, READY and CORPSE_READY markers are not behaviour.

| id | species | status |
|---:|---|---|
| 84 | Creeping Chrysanthemum (Hana) | admitted |
| 93 | Volatile Dweevil (BombOtakara) | admitted |
| 26 | Water Dumple (Catfish) | admitted (fight on the real water slots unobserved) |
| 27 | Wogpole (Tadpole) | admitted (fight on the real water slots unobserved) |
| 99 | Waterwraith (BlackMan) + Tyre 98 | not admitted; not startable in a campaign, next steps below |

## What the assessment found (baseline exe `3ba1692e...`, fork main)

All four ordinary species already bound in the campaign and ran their source FSM.
Four defects kept them out, each reproduced before it was fixed:

1. **No corpse.** Hana, Catfish and Tadpole ended their dead clip with `die()`
   alone. The P1 host `doAI`, which normally calls `die()` then `dieSoon()`
   (`becomePellet`), is suppressed for a registered actor, so a natural kill left
   nothing to carry: `AUTOPLAY_RESULT killed=1 carried=0` (Hana `b84`, Catfish
   `g26`). They now call `pcEscapeNow()` once, like Armor, Groink and Breadbug.
2. **Hana drifted.** Its flick fired whenever a Pikmin was within 25 units, so
   under an 80-Pikmin squad it flicked back to back, chased again after every
   flick and wandered about 1200 units from home. The corpse then lay on an
   unroutable spot (`carriers=0 want=3`). Source `isStartFlick` (enemyAction.cpp:1209-1240) tests the stuck Pikmin count against the
   `ShakeOffSticking` tiers and `mFlickTimer` against `ShakeOffBlowA-D`; Hana
   now triggers on stuck count >= 3 only (the same simplification as
   `pc_p2_chappy.cpp`; the `mFlickTimer` gate is omitted, a port simplification).
   The Flick end returns to the state Flick was entered from (Walk or GoHome),
   as source `StateFlick::exec` `transit(enemy, mPreviousID)` (chappyState.cpp:2206-2207);
   an earlier "flick outside the territory goes to GoHome" rule was unsourced and
   is removed.
3. **Dweevils abort on pack slots.** `pc_p2_batch2` allowed pack generators only
   for the uji and ground families. Placement accepts every Dweevil (59-62, 93)
   on grub-cohort slots (terrain and footprint only), and a grub generator holds
   several Chappy hosts under one token, so a sampled seed that put a Dweevil
   there died with `P2_BATCH2 duplicate generator=... family=dweevil in scene`
   (seed s3, `WaterOtakara` on `spring_init_7623`). The dweevil family now binds
   every pack member. This is a base defect that also hit the admitted 59-62.
4. **Aquatic pack members drew as the P1 body.** `pc_p2_batch3` skipped every
   member after the first (`P2_SETUP_SKIP ... duplicate_generator`); water slots
   are packs of 2-3. All members now bind and draw the P2 model (run `w26`: three
   `P2_BATCH3_BIND` for one token).

Root: the placement catalog had no profile for BombOtakara 93, so no placement
document could hold it. `randomizer/p2_placement_catalog.py` gets the profile
(`terrains: ground`, the same slots as 59-62) and the document is regenerated.

Also added: P1-approximation SFX for 26, 27, 84 and 93 through
`pc_p2_sfx_policy.h` (pattern of #35, output only, unit test extended).

## Evidence (final exe `7c121533...`, native `b37a3ddea`)

Private build `output/native-w3-mechanics-build`, `ninja -n pikmin_pc`: "no work
to do". Content `output/w3-mech-content`. Runs are bot power mode, red squad,
Distant Spring, the species rebound onto `spring_init_7002` (1945764764), driver
`output/claude-orch/p2-w3-mech/botrun.py`. The "re-entry" run uses
`PIKMIN_P2_TEST_DAY_CYCLE=time:8,time:8,time:100` (`time:300` for Hana): the
species is alive at sunset on day 2 and day 3, is forgotten and rebound on each
new day, then is killed and delivered on day 4.

| id | power run | receipt | re-entry run |
|---:|---|---|---|
| 26 | `c26-26`, 73 s | `onion:p2:26:3` | `e26-26` (sunsets alive, day 4 kill and receipt) |
| 27 | `c27-27`, 57 s | `onion:p2:27:3` | `e27-27` |
| 84 | `c84-84`, 95 s | `onion:p2:84:3` | `e84-84` (day 4, 132 s) |
| 93 | `h93-93`, 39 s (rebuilt exe `6421207b...`) | `onion:p2:93:3` | `i93-93` (day 4, 44 s); `f93-93` covers the pack fix |

Log paths, hashes and line numbers are in the roster evidence entries
(`docs/PIKMIN2_ENEMY_ROSTER_EVIDENCE.json`) and the `P2_PLAYABLE_POOL` rows.

## Per-species notes and open items

**84 Hana.** Buried Sleep gate (no atari, invulnerable), emerge, walk, bite with
`attackNavi`, eat, flick, GoHome, dead. Open: the three mouth slots are one
explicit capture per bite; the White Pikmin poison is unexercised (no White
Pikmin in P1).

**93 BombOtakara.** Pursues its target; the source `stimulateBomb` 1.5 s fuse
detonates the carried Bomb, and any damage detonates it too (source
`BombOtakara::damageCallBack`). The blast goes through the shared blast
primitive. Open: the Bomb has no separate model or actor, so the carried Bomb is
not drawn; the blast in the observed runs hit no Pikmin (`pikmin_hits=0`, the
squad was outside the 90-unit radius), so Pikmin casualties from it are
unobserved in a campaign run.

**26 Catfish, 27 Tadpole.** Both take water-cohort slots only (their lane-04
profile, source: they are aquatic; 2 slots on the Forest of Hope, 8 on Distant
Spring). The port has no water plane, so they walk on land wherever they are
placed, and every kill above was on a land slot. On the real water slots
(`y=-57`, packs of 2-3) all members bind and draw, but the autoplay bot never got
within 600 units of the pack (`b26`, `w26`), so no fight was observed there.
Open: (a) a fight, kill and delivery on a real water slot; (b) a water plane or
shore rule for the FSM; (c) the Catfish flick still uses the proximity rule that
was fixed for Hana (it dies fast, so it never showed); (d) the Catfish
White-Pikmin poison path stays unexercised.

## 99 Waterwraith: not admitted

What exists: an engine-free rig for the Tyre roller and the phase machine
(`pc_p2_waterwraith*.cpp`, source-anchored), an encounter consumer, and an
opt-in registration seam that puts a fixed-placement actor into the room preview
(`p2-waterwraith-actor.txt`). What does not exist, checked this pass:

* Root: a seed layout that binds 99 is refused (`P2 layout binds unadmitted
  source ids: [99]`), as expected for an unadmitted species. `IDENTITY_FAMILY`
  knows the enum name `blackman` but has no source-id row for 99 (or 98), and
  nothing stages Waterwraith content in a campaign session. The placement
  profile (`waterwraith_candidate_profile`) treats BlackMan as an ordinary
  ground species (`is_boss` false, no encounter descriptor), which is not the
  owner's ruling: bosses go in boss arenas placed by footprint.
* Native: `pc_p2_generated_placement.cpp` handles 99 with `recordBind` only (logs
  `bound=1`, takes no actor); `hostType(99)` is the default, so nothing births a
  BlackMan; the campaign setup sweep has no Waterwraith module; the seam is
  preview-only.

Next steps, in order (a multi-session build, not started here):

1. Owner ruling: the roller accepts only Purple hits and Purple landing stuns,
   and P1 has no Purple Pikmin. Choose the P1 mapping (all colours, or a chosen
   colour) before any encounter code.
2. Root: add source-id rows for 99 (and the Tyre helper 98) to
   `IDENTITY_FAMILY`, stage the Waterwraith content, and give BlackMan an arena
   descriptor (footprint from the roller circumference 44 pi and the body,
   clearance measured per P1 arena, protected drops respected, the Emperor arena
   stays protected); placement stays constraint-derived, no slot list.
3. Native: a campaign bind that births the actor on a P1 boss arena (the P1 boss
   there is replaced), a campaign `setup` that takes the actor from the
   generated placement, real Pikmin damage receivers on the P1 engine for the
   roller (frozen window) and the dismounted body, the Tyre child and its
   crush/flick of Pikmin, the fall intro (spawn height 1100, movie skipped), and
   the source map-graph route step that the port replaced with a waypoint list.
4. Death: the dead wraith becomes a carried corpse (today a P1 number-pellet
   stand-in) and delivers `onion:p2:99:3` on its generator token.
5. Then the bot run (power mode, arena start), the re-entry run, and the smoke
   seed with `--bosses 99:<arena>`.

## Owner playtest

See the issue comment and hand-over notes for the saturated Forest of Hope smoke
seed (`scripts/p2_smoke_seed.py --area foh --near-start`).

## Review fixes (exe `6421207b1b482ba2d87ddd85d92e99eb60305117d293b4dcce65eec3e7653258`, native `601298766`)

- **93 dies with its Bomb.** Source `Obj::doUpdateCommon` (OtakaraBase.cpp:93-108):
  when the carried Bomb is no longer alive the BombOtakara sets
  `mTargetCreature = nullptr` and `mHealth = 0`. The port has no Bomb creature, so
  a detonated Bomb (fuse, damage, flick or death) zeroes the Dweevil's health on
  its own tick (`P2_BOMBOTAKARA_PAYLOAD_DEAD`). Runs `h93`/`i93` show FUSE, BLAST
  and PAYLOAD_DEAD in the same tick with no squad hits in between. The old
  `c93`/`e93` runs (Dweevil survived the blast, six squad hits) are superseded.
  Consequence: a Dweevil no longer survives a sunset alive once it has chased.
- **93 blast receivers.** `h93` L3730 `pikmin_hits=1`; `i93` L10927 `pikmin_hits=32`.
  The Bomb still has no separate model.
- **27 attacks_receivers**: Wogpole is harmless in source. The admission contract only accepts PASS, so the gate records the receiver side alone (squad damage applied, escape and death); no Wogpole attack is claimed.
- **84 evidence text** corrected (see item 2 above); re-check run `i84`: two flicks
  return to Walk, kill and receipt `onion:p2:84:3` in 68 s.

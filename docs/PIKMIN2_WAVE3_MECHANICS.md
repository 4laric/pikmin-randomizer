# Wave 3 mechanics lane: 26, 27, 84, 93, 99 (#964)

Lane "Mechanics species: water, Chrysanthemum, Volatile Dweevil, Waterwraith" of
the wave 3 enemy import. Tracking issue: 4laric/pikmin-randomizer#964. Branches:
root `claude/p2-wave3-mechanics` (origin/main `d3d4d06b`), native fork
`claude/p2-wave3-mechanics` (fork main `3dd1e905a`).

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
   `ShakeOffSticking1-3` tiers and, per tier, `mFlickTimer` (rounded) against
   `ShakeOffBlowA-D`, and resets the timer when it fires. Hana now triggers on
   stuck count >= 3 only (the same simplification as `pc_p2_chappy.cpp`). The
   `mFlickTimer` versus `ShakeOffBlow` gate and the higher stuck tiers are NOT
   implemented, so this is a simplification, not the source test.
   The Flick end returns to the state Flick was entered from (Walk or GoHome),
   as source `StateFlick::exec` `transit(enemy, mPreviousID)` (chappyState.cpp:2206-2207).
   The state is recorded in `enter()` before Flick starts (`Hana::prevState`,
   `p2hanapolicy::FlickReturn`); the first version read `prevState` without ever
   assigning it, so a flick from GoHome wrongly returned to Walk. Unit test
   `p2_hana_residual_policy_test` covers Walk and GoHome; no recorded run flicked
   from GoHome. An earlier "flick outside the territory goes to GoHome" rule was
   unsourced and is removed.
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

## Evidence (final exe `fe21fd5e99634438ca03fbc204bc86c45fbe58b4619e60825ba04f4960c6a03a`, native `535a4da10`)

The exe was built from native `1959f6b5d`; `535a4da10` only registers a CTest
target. Private build `output/native-w3-mechanics-build`, `ninja -n pikmin_pc`:
"no work to do". Content `output/p2-content-dense` (the seed now carries the
whole 48-species pool, so the old `w3-mech-content` no longer stages; prepared
sha256 `442bd8b650e1294d...`). Runs are bot power mode, red squad (93 also
yellow and blue), Distant Spring, the species rebound onto `spring_init_7002`
(1945764764), driver `output/claude-orch/p2-w3-mech/botrun.py`. The day-cycle
run uses `PIKMIN_P2_TEST_DAY_CYCLE=time:8,time:8,time:100` (`time:300` for
Hana): the species is bound at the start of each stage, alive at the day-2 and
day-3 sunsets, and killed and delivered in the third stage (`STAGE step=2
day=4`). Every log hash below was recomputed from the file after the rebuild.

| id | kill run | receipt | day-cycle run |
|---:|---|---|---|
| 26 | `j26-26`, 49 s | `onion:p2:26:3` L5930 | `l26-26` (sunsets L4608/L8941, dead L14106, receipt L15073) |
| 27 | `j27-27`, 47 s | `onion:p2:27:3` L6959 | `l27-27` (sunsets L5597/L10884, dead L17079, receipt L17894) |
| 84 | (in `k84-84`) | `onion:p2:84:3` L18679 | `k84-84`, 141 s (sunsets L4812/L9355) |
| 93 | `r93-93` blue, 42 s; `j93-93` red, 41 s | `onion:p2:93:3` L6249 / L5692 | `k93-93` (day-3 sunset L8616, dead L13040, receipt L14160) |

Earlier-exe runs (`c26`/`e26`, `c27`/`e27`, `c84`/`e84` on `7c121533...`, `h93`,
`i93`, `i84` on `6421207b...`) are kept as history; the roster no longer cites
them for admission except `h93`/`i93`, which show 93 blasts that hit Pikmin.

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
not drawn. On the final exe most runs blast with `pikmin_hits=0` (the squad is
outside the 90-unit radius); one blue-squad run (`r93` L5132) hit one Pikmin, and
the earlier-exe runs `h93` (1) and `i93` (32) also did.

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

## Review fixes (final exe `fe21fd5e...`, native `535a4da10`)

- **93 dies with its Bomb.** Source `Obj::doUpdateCommon` (OtakaraBase.cpp:93-108):
  when the carried Bomb is no longer alive the BombOtakara sets
  `mTargetCreature = nullptr` and `mHealth = 0`. The port has no Bomb creature, so
  a detonated Bomb (fuse, damage, flick or death) zeroes the Dweevil's health on
  its own tick (`P2_BOMBOTAKARA_PAYLOAD_DEAD`). Runs `r93`, `j93`, `k93` show FUSE,
  BLAST and PAYLOAD_DEAD in the same tick with no squad hits in between. The old
  `c93`/`e93` runs (Dweevil survived the blast, six squad hits) are superseded.
  Consequence: a Dweevil that has chased no longer survives a sunset alive.
- **93 blast receivers.** Final exe `r93` L5132 `pikmin_hits=1`; earlier exe `h93`
  (log sha256 `1778de329be329be...`, corrected from a wrong `27ac66ff...`) L3730
  `pikmin_hits=1` and `i93` L10927 `pikmin_hits=32`. The `i93` blast and receipt
  L12274 are both in the third stage (`STAGE step=2 day=4` at L10350); the
  sunset lines are L7194 (day 3) and L13927 (day 4). The Bomb still has no model.
- **27 attacks_receivers**: Wogpole is harmless in source. The admission contract
  only accepts PASS, so the gate records the receiver side alone (squad damage
  applied, escape and death); no Wogpole attack is claimed or observed.
- **84 flick return**: `Hana::prevState` is now assigned when Flick is entered (see
  item 2 above); no run flicked from GoHome, the unit test covers it. `k84` flicks
  came from Walk and returned to walk. The flick trigger is the stuck-count
  simplification of `isStartFlick`, not the source `mFlickTimer` gate.
- **Pool, roster and evidence** were updated together: the `randomizer/seed.py`
  `P2_PLAYABLE_POOL` rows for 26, 27, 84 and 93 cite the runs above.

## Owner playtest fixes: Hana, Water Dumple, Empress (2026-09-30, #964)

Package `output/smoke-w3-mechanics/foh-1` (previous one kept as `foh-1.prev2`).

- **Hana buried idle** (`pc_p2_hana.cpp`, `pc_p2_hana_sleep_policy.h`): the old code forced clip type1
  phase 0 while buried, which is the standing body. The source Sleep state plays type1 from frame 70
  and loops frames 30..100 (LOOP_START/LOOP_END); waking sets speed 60 and finish-motion, which plays the
  rest of the clip (ground burst at frame 120) before Walk. The wake radius is the source private radius
  70 in a seed (`wakeRadius(campaign)`); staged fixtures keep 500. Logs: `P2_HANA_SLEEP`,
  `P2_HANA_WAKE`, `P2_HANA_EMERGE_BURST`.
- **Corpse vertex explosion**: root cause is the converter (`experimental/pikmin2_rigid.joint_matrices`
  ignored the J3D scale-compensate joint flag; fix root 33db1fcc, PR #1002, cherry-picked here). Hana
  dead poses went from 651 tall and a 393x30x18 line to a 215 maximum and a 72x46x72 bud. Safety nets
  for any future bad bake: `p2motion::holdPick` steps a death-clip hold back from a spike, logged as
  `P2_POSE_HOLD_ADJUST`; `p2pose::present` refuses non-finite or exploded poses, logged as
  `P2_POSE_GUARD_REFUSED`. Converter-changed species in the admitted set: Hana, Sokkuri, UmiMushi,
  Jigumo, Tadpole, SnakeCrow, SnakeWhole, BigTreasure, BombSarai, Kabuto/Fkabuto/Rkabuto,
  FminiHoudai, Tank/Wtank (Catfish, Armor, ElecBug, Imomushi, TamagoMushi, Frog, Miulin, Otakaras and
  DangoMushi unchanged). `output/p2-content-dense-fixed` re-extracts the ground, aquatic and snagret
  families only.
- **Latch positions** (native `claude/p2-stick-surface`): a P2 mesh drawn on a P1 host kept the host's
  collision tree. Hana stuck Pikmin to a radius-9 head sphere, the Dumple to a radius-21 sphere 16 above
  a 20-tall body. `pc_p2_body_fit.h` fits spheres to the rest pose, `pc_p2_body_coll.cpp` seats them
  through `P2FlyerColl`; `P2_STICK` logs the latch against the part radius. Covered: Hana 84, Dumple 26,
  Wogpole 27, Empress 30, Crawbster 94, Sokkuri, Armor, ElecBug, Imomushi, TamagoMushi, Jigumo, UmiMushi.
  `PIKMIN_P2_BODY_COLL=0` restores the host trees.

Evidence: runs hj84, hj26, hq30c, host A/B hb84 under `output/claude-orch/p2-hana-fix/runs`, frames in
`output/claude-orch/p2-hana-fix/png`.

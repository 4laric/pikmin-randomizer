# Pikmin 2 retail disc parameters — engine lane extraction (#128)

Engine/toolchain lane deliverable for consumer issues #244 (BombSarai),
#245 (Fuefuki) and #246 (BigTreasure). All values below were extracted
verbatim from the staged user disc copy and cross-checked against the family
audits and the `native/pikmin2-research` checkout at
`632af93787b9c95b63f0c13be32b161375ce3a96`.

## Disc identity and provenance

- Image: `assets/disc/PIKMIN2 for GAMECUBE.iso` (local copy, not committed).
- Header: game code `GPVE01` (US), disc 0, revision 0, GC magic `c2339f3d`,
  size 995,557,376 bytes — matches the lane baseline "US GPVE01 revision 0".
- Extraction tool: lane-owned `experimental/pikmin2_engine_parms.py` (new in
  this batch), built read-only on `experimental/pikmin2_assets.py`
  (`disc_files`/`archive_files`; shared converter code untouched). Deterministic
  re-run: `python -m experimental.pikmin2_engine_parms --iso <iso> --output
  output/p2-engine-parms`. Structured output (local, not committed):
  `output/p2-engine-parms/engine_disc_parms.json`. Unit tests with synthetic
  fixtures: `tests/test_pikmin2_engine_parms.py` (12 tests, all passing).
- Global constant: `user/Kando/aiConstants.txt` gives `gravity 560.0`
  (units/s²; ≈ 9.333 per tick at the 60 Hz source tick rate). BombSarai/Bomb
  fall and all ballistic arcs use this shared value
  (`_aiConstants->mGravity`, e.g. `enemyBase.cpp:1888-1892`).

Disc file paths for every family: parameter and animation-manager text files
live inside the single archive `enemy/parm/enemyParms.szs`
(`<family>/enemyparm.txt`, `<family>/enemyanimmgr.txt`); model/motion
archives are `enemy/data/<Name>/model.szs` and `enemy/data/<Name>/anim.szs`.

Verification status legend: **disc** = read verbatim from the disc files
above; **source** = hardcoded in the decomp (not disc data), cited for
context; **match/differs** = comparison against the header defaults recorded
in the family audits.

## #244 — BombSarai / Careening Dirigibug (enemy ID 58)

Disc source: `enemy/parm/enemyParms.szs:bombsarai/enemyparm.txt` +
`bomb/enemyparm.txt`, `bombsarai/enemyanimmgr.txt`, `bomb/enemyanimmgr.txt`.

### Dirigibug proper parms (hover and behavior)

| Parm | Meaning (disc comment) | Retail disc | Header default | Status |
| --- | --- | --- | --- | --- |
| fp01 | 飛行高さ flight height | 70.0 | 90.0 | **differs** |
| fp03 | 状態遷移高さ transition height | 50.0 | 50.0 | match |
| fp10 | 上下の揺れ速度 pitch rate | 2.5 | 2.5 | match |
| fp11 | 上下の揺れ幅 pitch amplitude | 20.0 | 20.0 | match |
| fp21 | 上昇係数(0) free rise factor | 1.5 | 1.5 | match |
| fp22 | 上昇係数(5) laden rise factor | 1.0 | 1.0 | match |
| fp31 | 振払確率(1) free flick chance | 0.2 | 0.1 | **differs** |
| fp32 | 振払確率(5) laden flick chance | 0.8 | 0.7 | **differs** |
| fp40 | もがき時間 struggle time (s) | 0.8 | 3.0 | **differs** |

### Dirigibug general parms (consumed by FSM per audit)

| Parm | Meaning | Retail disc |
| --- | --- | --- |
| fp00 | ライフ health | 1500.0 |
| fp06 | 速度 move speed | 60.0 |
| fp09/fp10/fp11 | territory / home / private radius | 200 / 100 / 50 |
| fp12/fp13 | sight distance / angle | 200 / 180 |
| fp20/fp21 | attackable range / angle | 100 / 45 |
| fp22 | 攻撃ヒット範囲 `mAttackRadius` (bomb-drop XZ gate) | 50.0 |
| fp23 | 攻撃ヒット角度 | 15.0 |
| fp24 | 攻撃力 attack damage (Navi/Pikmin) | 10.0 |
| fp16/fp17/fp18/fp19 | flick chance / force / damage / range | 1.0 / 80 / 1.0 / 120 |
| ip01–ip07 | flick thresholds A–D / stick 1–3 | 3, 3, 8, 5, 15, 10, 30 |

### Payload Bomb parms (`bomb/enemyparm.txt`)

| Parm | Meaning | Retail disc | Header default | Status |
| --- | --- | --- | --- | --- |
| fp00 | ライフ fuse health | 4.5 | — | disc |
| fp22 | 攻撃ヒット範囲 blast radius (`mAttackRadius`) | 90.0 | — | disc |
| fp02 | 爆風範囲高さ± blast half-height | 50.0 | 50.0 | match |
| fp01 | 敵へのダメージ damage to enemies (Teki) | 500.0 | 250.0 | **differs** |
| fp24 | 攻撃力 Navi/Pikmin blast damage | 10.0 | — | disc |
| ip01 | ダメージリミット fuse arm damage limit | 1 | 2 | **differs** |
| ip02 | 誘爆リミット bomb-induction trigger limit | 15 | 50 | **differs** |
| fp12/fp20 | 視界距離 / 攻撃可能範囲 (trace/search radii) | 700 / 30 | — | disc |

Notes for the lane:

- **Blast volume:** spherical radius 90 with ±50 vertical half-height gate;
  Teki in volume take 500, Navi/Pikmin take `fp24` = 10 with directional
  knockback (source: `bombState.cpp:109-198`, audit #244 "Detonation").
- **Fuse/arm timing:** `bomb/enemyanimmgr.txt` — `hit_start.bca` fires
  KEYEVENT_2 at frame 10; `hit_loop.bca` is LOOP_START frame 0 → LOOP_END
  frame 7, i.e. an 8-frame arm loop (frames at the 60 Hz source rate).
  Detonation waits a hardcoded 10 ticks after health drain (source
  `bombState.cpp:109-198`); uncaptured escaped bombs die silently after 200
  ticks (source `bombState.cpp:53-58`). The induction countdown runs against
  disc `ip02` = 15.
- **Gravity per tick:** shared `aiConstants.txt` gravity 560.0 units/s²
  ≈ 9.33 units/tick velocity gain at 60 Hz; there is no Bomb-specific
  gravity override on disc.
- **"Bomb trace radius":** no parm with that name exists; the candidate
  disc radii are sight 700 / attackable range 30 / blast 90 (above). Flagged
  for the #244 lane to confirm which one it needs.
- `bombotakara/enemyparm.txt` (Titan Dweevil's Comedy Bomb variant) also
  exists in the same archive for the #246 lane; not re-tabulated here.

## #245 — Fuefuki / Antenna Beetle (enemy ID 41)

Disc source: `enemy/parm/enemyParms.szs:fuefuki/enemyparm.txt`,
`fuefuki/enemyanimmgr.txt`, `enemy/data/Fuefuki/anim.szs`.

### Proper parms — retail vs header defaults

| Parm | Meaning | Retail disc | Header default | Status |
| --- | --- | --- | --- | --- |
| fp01 | 出現時間(Max) ground-time cap (s) | 20.0 | 30.0 | **differs** |
| fp02 | 出現時間(Min) ground-time min (s) | 10.0 | 20.0 | **differs** |
| fp03 | 出現間隔 airborne Stay interval (s) | 3.0 | 3.0 | match |
| fp11 | フエ間隔(1) min whistle interval | 0.0 | 0.0 | match |
| fp12 | フエ間隔(2〜:隊列ナシ) re-cast, no squad (s) | 3.0 | 5.0 | **differs** |
| fp13 | フエ間隔(2〜:隊列アリ) re-cast, with squad (s) | 10.0 | 10.0 | match |
| fp21 | もがき時間 struggle time (s) | 2.5 | 3.0 | **differs** |
| fp22 | 逃げジャンプ時間 escape jump time | 0.0 | 0.0 | match |
| fp31 | 通常出現率 normal landing chance | 0.5 | 0.5 | match |

### General parms consumed by the whistle/jump mechanic

| Parm | Meaning | Retail disc |
| --- | --- | --- |
| fp22 (general) | 攻撃ヒット範囲 `mAttackRadius` — whistle radius base | 130.0 |
| fp11 (general) | プライベート距離 `mPrivateRadius` — intrusion trigger | 60.0 |
| fp00 | ライフ health | 700.0 |
| fp06 | 速度 move speed | 250.0 |
| fp09/fp10 | territory / home radius | 300 / 100 |
| fp16/fp17/fp18/fp19 | jump-flick chance / force / damage / range | 1.0 / 120 / 1.0 / 30 |
| fp23 | 攻撃ヒット角度 (whistle ring spin) | 0.1 |
| fp24 | 攻撃力 attack damage | 10.0 |

### FUEFUKIANIM motion bank (engine #128 capability)

`enemyanimmgr.txt` declares 10 animations and `enemy/data/Fuefuki/anim.szs`
contains exactly those 10 `.bca` clips — a 1:1 match with the
`FUEFUKIANIM_*` enum (`Fuefuki.h:160-172`):

| Slot | Clip file | Key events (frame, code) |
| --- | --- | --- |
| 0 Dead | dead.bca | — (END only) |
| 1 Landing | landing.bca | (21,2) (45,3) |
| 2 LandFail | landfail.bca | (21,2) (60,3) |
| 3 Move | move.bca | (4,0) (14,1) |
| 4 Pivot | pivot.bca | (4,0) (13,1) |
| 5 Wait | wait.bca | (0,0) (29,1) |
| 6 Whisle | whisle.bca | (14,0) (23,1) |
| 7 Struggle | struggle.bca | (20,0) (39,1) |
| 8 Jump | jump.bca | (3,0) (8,1) (13,2) (15,3) |
| 9 Carry | carry.bca | (0,0) (29,1) |

Event codes 0/1 = loop start/end; 2/3 = gameplay key events (lifegauge
on/down-effect at 2, struggle-enable at 3 per the audit's Land-state trace).

## #246 — BigTreasure / Titan Dweevil (enemy ID 73)

Disc source: `enemy/parm/enemyParms.szs:bigtreasure/enemyparm.txt` +
`bigtreasure/enemyanimmgr.txt`, `enemy/data/BigTreasure/model.szs`,
`enemy/data/BigTreasure/anim.szs`, `user/Abe/Pellet/us/otakara_config.txt`,
`user/Mukki/mapunits/caveinfo/last_3.txt` (Dream Den floor 14),
`user/Mukki/mapunits/caveinfo/ch_MUKI_oootakara.txt` (challenge mode),
`message/mesRes_eng.szs` (`pikmin2.bmg`).

### Five pellet configurations (weapon treasures + Louie)

From `user/Abe/Pellet/us/otakara_config.txt` (verbatim; `min`/`max` are the
carry weight / max-carrier fields):

| Pellet | BMD | Carry min | Carry max | Money | Dictionary | US name (retail BMG) |
| --- | --- | --- | --- | --- | --- | --- |
| elec | elements_elec.bmd | 30 | 40 | 1000 | 197 | Shock Therapist |
| fire | elements_fire.bmd | 30 | 40 | 1000 | 198 | Flare Cannon |
| gas | elements_gas.bmd | 30 | 40 | 1000 | 199 | Comedy Bomb |
| water | elements_water.bmd | 30 | 40 | 1000 | 200 | Monster Pump |
| loozy | otakara_loozy.bmd | 1 | 5 | 10 | 201 | King of Bugs |

Shared fields: `unique yes`, `code 0`, friction 0.1, particletype simple;
radii 35/35/37/35/12, heights 50/52/20/51/10. US names verified as whole
records in `message/mesRes_eng.szs:pikmin2.bmg` (DAT1 offsets 12872, 12904,
12930, 12954, 13156; each stored twice — pickup and list variants — with an
embedded `\n` in the four weapon names). `loozy money 10` is the verbatim
config value.

### `mPelletDropCode` finale treasure identity

- Story mode: the only story spawn is Dream Den floor 14
  (`last_3.txt`, `{c000} 4 14`), whose TekiInfo holds the single plain token
  `BigTreasure` with **no carried-cargo suffix**. Per `TekiInfo::read`
  (`gameCaveInfo.cpp:100-125`) a suffix-less token leaves
  `mOtakaraItemCode` null, so `mPelletDropCode` is null and the KEYEVENT_100
  `throwupItem()` call births nothing. The finale treasure is therefore the
  `loozy` pellet (King of Bugs) released by `releaseItemLoozy()`
  (`BigTreasure.cpp:912-920`), confirming audit Q5.
- Challenge mode (`ch_MUKI_oootakara.txt`): both spawns use the token
  `BigTreasure_key`, i.e. carried cargo `key` (the Challenge Mode key), the
  same mechanism as other `Enemy_treasure` tokens.
- Animation cross-check: `bigtreasure/enemyanimmgr.txt` `dead.bca` fires
  key event code 100 at frame 320 — the KEYEVENT_100 source anchor
  (`BigTreasureState.cpp:41-126`).

### Material animations (audit Q2) — resolved: absent on disc

`enemy/data/BigTreasure/model.szs` contains exactly one member
(`enemy.bmd`, 61,568 bytes); `anim.szs` contains 29 `.bca` clips only (the
30-slot animation manager reuses `wait2.bca` for two slots). No
`.btk` or `.brk` exists anywhere in the BigTreasure data (consistent with
the dead path statics at `BigTreasureMgr.cpp:12-13`). Retail material
animation is fully procedural through `changeMaterial`/
`updateMaterialColor`; the converter lane needs no btk/brk import for this
family. The full 30-clip animation-manager list also matches the audit's 30
registrations.

### General parms — attack-limit box and flick thresholds

| Parm | Meaning | Retail disc |
| --- | --- | --- |
| fp00 | ライフ health | 5000.0 |
| fp11 | プライベート距離 private radius | 100.0 |
| fp09 | テリトリー territory | 250.0 |
| fp10 | ホーム範囲 home radius | 75.0 |
| fp12/fp25 | sight distance / height | 300 / 50 |
| fp14/fp15 | search distance / angle | 300 / 90 |
| fp20/fp21 | attackable range / angle | 75 / 25 |
| fp22/fp23 | attack hit range / angle | 75 / 25 |
| fp24 | 攻撃力 attack damage | 10.0 |
| fp16/fp17/fp18/fp19 | flick chance / force / damage / range | 1.0 / 100 / 0.0 / 25 |
| ip01–ip07 | flick thresholds A–D / stick 1–3 | 6, 5, 12, 10, 17, 20, 22 |

The 225-unit XZ attack-limit box itself is **hardcoded** in
`isAttackLimitTime()` (`BigTreasure.cpp:356-403`), together with the
`4 + 2 × liveWeapons` second pacing and 3× timer rate near outsiders; the
disc supplies only the radii above (source, not disc, for the 225 value).
Per-weapon pre-attack/attack durations from the proper block: fp10 2.5
(elec), fp11 2.8 / fp31 2.5 (fire 1/2), fp12 2.5 (gas), fp13 2.5 (water);
fp20–fp23 all 5.0 s attack durations. Elec/fire/gas/water discharge parm
sets fe00–fe38, ff00/ff10, fg00–fg40, fw00–fw12 were extracted verbatim and
match the audit's documented roles (full values in
`output/p2-engine-parms/engine_disc_parms.json`).

## Cross-checks against the audits

- #244 audit header defaults (`BombSarai.h`, `Bomb.h`): fp01 90→**70**,
  fp31 0.1→**0.2**, fp32 0.7→**0.8**, fp40 3.0→**0.8** on disc; Bomb fp01
  250→**500**, ip01 2→**1**, ip02 50→**15**. The audit's "shipped per-enemy
  .txt parm overrides live in game assets" note is now resolved verbatim.
- #245 audit header defaults (`Fuefuki.h`): fp01 30→**20**, fp02 20→**10**,
  fp12 5.0→**3.0**, fp21 3.0→**2.5** on disc; all other proper parms match.
  Audit open question 3 (verify whistle radius against retail parms) is
  answered: base radius 130.0, XZ-only per source.
- #246 audit: Q1 (pellet configs) and Q2 (btk/brk) resolved above; Q5
  (drop code) resolved — story mode null, finale is `loozy`; Q9 partial —
  radii extracted, the 225-unit box confirmed source-hardcoded.

## Explicit gaps / not extractable

1. "Bomb trace radius" (#244 wording) maps to no named disc parm; candidate
   radii are tabulated and the consumer lane must pick.
2. `mSquadTimer` per-frame vs deltaTime cadence (#245 audit open question 2)
   is a source-behavior question, not disc data.
3. Treasure display strings exist twice in the BMG with embedded `\n`; a
   full INF1→name index map was not needed and was not built.
4. Squad-adjusted carry weight for boss `throwupItem`
   (`enemyBase.cpp:2605-2608`) is runtime logic; only the config `min`/`max`
   fields are disc data.
5. BombSarai asset filenames for the converter handoff (audit #244 open
   item): `enemy/data/BombSarai/{model,anim}.szs` and
   `enemy/data/Bomb/{model,anim}.szs` confirmed present on disc; their
   internal member lists are recorded in the JSON output, but BMD/BCK
   conversion itself is outside this extraction batch.

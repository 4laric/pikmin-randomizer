# Damagumo demon profile/mesh converter (#670)

Lane `damagumo-profile-convert`, issue #670 (OPEN, assigned 4laric).
Implementation owner: Codex through shared account 4laric. Bounded tooling
converter: consumes verified Demon/Damagumo disc bytes plus the mapped folder,
emits deterministic hash-pinned profile/mesh/slot artifacts for arena slot
312004, consumable by the #638 arena staging provider. No family/shared
edits, no builds, no runtime, no ADMIT. All six runtime gates UNTESTED.

## Verified inputs (real bytes, hash-pinned, nothing invented)

P2 disc ISO (995,557,376 B, 2,768 members via pikmin2_assets.disc_files):
- enemy/data/Damagumo/model.szs (62,368 B, sha ddb0cf45cb82e8c3732e37add680b059affd857373f1d9ea02d4a25ad74ce727)
  decodes (Yaz0) to RARC single member enemy.bmd (76,832 B).
- enemy/data/Damagumo/anim.szs (40,768 B, sha 72a00c870115b256e6921adbdc96f0410756adfcba058c65ca0f5c37763585dd)
  decodes to RARC members dead/flick/landing/wait.bca (J3D1bca1).
- Verified context (not the profile source): enemy/data/Demon/model.szs
  (12,416 B, ea8ee9ad...) + anim.szs (34,080 B, 3978f5d2...); the Demon anim
  set lacks landing/wait, so the Damagumo folder is the profile source.
- Mapped folder: Demon (consumer FOLDERS[Damagumo]).

## Derivation (deterministic stdlib; existing helpers reused read-only)

- Mesh: model_sha256 = SHA-256 of decoded enemy.bmd
  (8fc0ac7fd6c7585113cf10da12ecd7faccf807896d2d642ab0f80019fff2a961).
- Joints: BMD JNT1 names via pikmin2_sheargrub_assets.joints -> 15 names
  (kosi, l/rfoot1-3jnt, l/rhand1-3jnt, tama1, tama2); joint_count = 15.
  Textures: TEX1 u16@8 = 4.
- Special joints use the lane-contract role template (mouth rkamujnt/lkamujnt,
  stickable tama/teama, leg_tube lft1/lht1/rft1/rht1); exact-name match finds
  none, so all 8 report present:false with null index/matrix - the committed
  Houdai convention for the visual/profile slice.
- Animation rows: BCA ANF1 frame-count field (u16 at ANF1+10, validated
  1..10000, consistent with file sizes, cross-checked vs BMD joint count 15
  at ANF1+12) gives landing 70 / wait 76 / flick 70 / dead 300. Frames via the
  shared deterministic sampler {0, dur-1} + {10,16,17,30<dur}, sorted, capped
  at 32 (no source audit exists for Damagumo events; documented).
- Identity: enemy_id 56, name Damagumo, retail Beady Long Legs, bestiary 72,
  folder Demon (committed SPECIES[56] row, cited not invented).
- Slot 312004 descriptor binds the arena actor slot to this profile+mesh
  (arena_binding 312004 Damagumo).

## Emitted artifacts (deterministic; sorted JSON, fixed formatting)

- damagumo-family.json sha f9ec5030890d72fba0c890b41407aa8788b6fac53223dd62f231a3259f68ef94
- Demon/enemy.bmd sha 8fc0ac7fd6c7585113cf10da12ecd7faccf807896d2d642ab0f80019fff2a961
- damagumo-slot-312004.json sha 61019a39bf255442e49cd5d03db6f16581ab5370ab401a346341f8d077c4e37c

## Consumer acceptance (real #638 contract)

The emitted profile+mesh were fed to the actual #638 installer functions
(_damagumo_profile, _damagumo_mesh): both ACCEPTED (enemy 56 Damagumo Demon,
15 joints; 76,832 mesh bytes), and profile_text renders correctly. Required
anchors landing/wait/flick all resolve from source; nothing renamed/invented.

## Verification

pytest tests/test_pikmin2_damagumo_profile_convert.py -q -> 10 passed
(synthetic BMD/BCA fixtures, malformed/missing negatives, consumer-shape
conformance). Real-byte end-to-end recorded above, re-runnable via the module
CLI (--model/--anim/--output).

## Downstream consumers

#638 arena staging provider (slot 312004); #173 Damagumo56 observer gates
1-4/6 (needs profile/mesh/slot); open #312 (no active producer duplicated).
# Dwarf Red Bulborb source increment (#120)

`experimental/pikmin2_kochappy_profile.py` exports a source-backed Dwarf Red model and all nine shared animation clips, plus reference profiles for the three closely related dwarf Bulborbs. It does not create native actors, write placements or install a visual/behavior profile. The next integration follows [the arena contract](PIKMIN2_ENEMY_ARENA.md).

| Source species | ID | Name | Health | Movement | Purple stun duration |
|---|---:|---|---:|---:|---:|
| Kochappy | 1 | Dwarf Red Bulborb | 200 | 50 | 10 s |
| BlueKochappy | 44 | Dwarf Orange Bulborb | 250 | 60 | 5 s |
| YellowKochappy | 45 | Snow Bulborb | 150 | 50 | 5 s |

All three retail files contain five creature, 45 general and three proper parameters. Comparing every field, Red differs from Snow only at general `fp00` (health) and `fp38` (Purple stun duration). Orange differs from Snow only at `fp00` and `fp06` (movement). Shared values include turn gain 0.4/update, maximum turn 10 degrees/update, attack-entry range 30 and half-angle 20 degrees. These are retail source facts, not claims that all values are implemented natively.

## Source evidence

- `native/pikmin2-research/include/Game/enemyInfo.h` supplies distinct IDs and names. `enemyInfo.cpp` and `kochappyBaseMgr.cpp` establish shared Kochappy model/animation resources.
- `kochappy.cpp`, `bluekochappy.cpp` and `yellowkochappy.cpp` construct the same `KochappyBase::ProperAnimator` and `KochappyBase::FSM`. Their material overrides replace texture image slot 0.
- The corresponding manager files select `.1.bti` for Red, `.3.bti` for Orange and `.2.bti` for Snow and allocate `KochappyBase::Parms`.
- `EnemyParmsBase.h` names source parameter members. Attack-entry range is `mMaxAttackRange` (`fp20`), distinct from actual hit radius `mAttackRadius` (`fp22`). Purple stun duration is `mPurplePikiStunDuration` (`fp38`), consumed by the stun timer in `enemyBase.cpp`.
- All nine source clips and event catalogs are shared. `attack.bca` contains event type 2 at frame 8 and type 3 at frame 88. This extraction does not retime the P1 proxy's attack events.

The extractor verifies source IDs, constructors, texture slots, manager paths and parameter member mappings against the local decomp before writing output. Profile validation rejects missing identities, malformed groups, missing required parameters, booleans/nonfinite values and unsupported retail values. Unknown raw fields remain in the complete parameter comparison instead of being silently discarded.

## Local validation

Run:

```powershell
py -3.12 -m experimental.pikmin2_kochappy_profile --iso 'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso' --research native/pikmin2-research --output output/p2-dwarf-red-profile/validated
py -3.12 -m pytest tests/test_pikmin2_kochappy_profile.py -q
```

Use a new output directory for another run. Retail extraction and 16 reference/validation tests pass. The generated Red BMD is 11,392 bytes; nine source animations total 67,856 bytes. No additional baked pose bank is generated. Native load cost remains unmeasured.

Generated model SHA256: `068dacdda452e5e87711ce6179ca9470a7c986f105b3dd9e1c30cc6bf30b792f`. Its slot-0 texture comes from `enemy/data/Kochappy/kochappy_body_s3tc.1.bti`, SHA256 `ea943f22de184003b1e88c3a02880815da659f22d200350fe2f0dda7d0637bad`. The JSON profile records all source asset, clip and audited code hashes. Original game data stays under local output.

## Requested native boundary

A family-owned `pc_p2_kochappy.*` module should receive an immutable validated profile and a separate actor binding. Preserve distinct source species identities even while using the native `TEKI_Chappy` scaffold. Request only small central delegates for setup/bind, parameter queries, visual drawing and reset/forget lifecycle. Keep family assets/logic out of a growing central registry implementation.

Arena placements separately bind unique generator IDs and expected native type, and validate full effective XYZ. No yaw or position belongs in this profile. Source yaw remains unapplied until a real orientation path exists. Begin with one Red actor and an ordinary P1 control, then prove autonomous targeting/movement, natural combat, corpse delivery and cleanup before expanding the roster.

Health 200 is the smallest isolated gameplay increment after Red visuals. The longer Purple stun duration requires its own supported reaction path; a data field alone does not implement that reaction. Full source FSM/collision/event behavior and arena lifecycle acceptance remain unimplemented.

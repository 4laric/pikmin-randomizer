# Species-lane residual slices: ShijimiChou, ElecBug pair, TamagoMushi group

Issue [#407](https://github.com/4laric/pikmin-randomizer/issues/407). Three
additions completing the flying identity and closing two ground-invertebrate
gaps. Owner: Codex via shared `4laric`.

## ShijimiChou (Unmarked Spectralids, EnemyID 77) — flying #166

Host P1 Chappy vehicle (`TEKI_Chappy`), private generator `375004`+.
The flying arena deliberately did not stage it (helper-only), so a private
`experimental/pikmin2_shijimi_arena.py` stages a small plant-origin Yellow group
(with the `P2_FLYING_ACTORS_1` bank format) and installs the ShijimiChou poses.

| Gate | Result | Evidence |
|---|---|---|
| Identity + spawn | PASS | `P2_SHIJIMI_BIND generator=375004/375005/375006 source_id=77`; `P2_BATCH3_BIND key=flying|ShijimiChou visual_only=0` |
| Movement + animation | PASS | `wait→fly`; clips `move`; 229.2 XZ spread |
| Attacks / receivers | source-backed N/A | harmless (`damageCallBack` returns false); no attack emitted |
| Death + corpse + nectar | PASS | `P2_SHIJIMI_DEAD`→`fall`→`dead`→`P2_SHIJIMI_KILL`; source `genItem` Honey (`OBJTYPE_Water`) exactly-once per actor; `P2_SHIJIMI_CORPSE native=host_die` |
| Transport + reward | reward PASS / transport UNTESTED | nectar items born per actor; no haul fixture |
| Cleanup + re-entry | wiring PASS / re-entry UNTESTED | reset/forget wired; day/floor respawn not exercised |

Run: `output/p2-species-shijimi/3feecd8944bf421e8a864e16330da0f8`, `native.log`
`1501B5C3…8F8476AA`; isolated exe `687CAAEE…1F9A17B0`. Group leader = lowest
generator; the 25-member P2 group/sound cluster is a bounded gap.

## ElecBug two-beetle partner link (#165)

Extends `pc_p2_elecbug` with the source `Charge`/`ChildCharge` pairing: a
registered beetle entering Charge links the nearest registered beetle within the
pairing radius (reciprocal pointers), runs `Discharge`/`ChildDischarge` together,
and breaks the link on partner loss, death or press. Electrical receiver remains
the single-target `InteractKill` (no P1 `InteractDenki`).

| Gate | Result | Evidence |
|---|---|---|
| Pairing | PASS | `P2_ELECBUG_LINK generator=346002 partner=346008` (reciprocal) |
| Child states | PASS | `P2_ELECBUG_STATE … state=childcharge` / `childdischarge` |
| Paired discharge + receiver | PASS | `P2_ELECBUG_DISCHARGE … state=charge|child`; `P2_ELECBUG_SHOCK` |
| Unlink | PASS | 6 unlinks on discharge end / partner loss |
| Flip / press | UNTESTED | no Pikmin lands on the host unattended |
| Death / cleanup | UNTESTED | link break on death implemented; not exercised |

Run: `output/p2-species-elecbug-pair/35ff6f4e170c4ba988cd2c745ce3649a`,
`native.log` `4C23809E…DFF26A7`. Partner selection is nearest-first (source picks
uniformly at random); the two-beetle were staged at generators 346002/346008.

## TamagoMushi bounded group birth (#165)

Extends `pc_p2_tamago` with a bounded leader/follower swarm: a private arena
stages five TamagoMushi actors; the lowest generator leads, the others follow
within the territory radius and share the Astonish receiver. This approximates
the source manager-owned `createGroup` (10 surface / 30 cave) without birthing
new P1 Teki.

| Gate | Result | Evidence |
|---|---|---|
| Group binds | PASS | `P2_TAMAGO_LEADER generator=346004 followers=4`; per-follower `P2_TAMAGO_GROUP` |
| Emerge + follow motion | PASS | `P2_TAMAGO_FOLLOW` traces; 117.9 spread; `max_distance` 60.02 ≤ follow radius |
| Astonish receiver | PASS | 13 × `P2_TAMAGO_ASTONISH` |
| Honey reward | UNTESTED | needs a death source |
| Cleanup | wiring PASS | orphaned followers self-promote (`P2_TAMAGO_PROMOTE`); no dangling |

Run: `output/p2-species-tamagogroup/c8e89342edc74067a2a6273b69a64d68`, `native.log`
`B83D7073…FB05DAD8`. New P1 actor birth and the 10/30 count scaling remain gaps.

## Combined build

`output/native-species-build`, `nectar.exe`
`D3253B859F40073500FDBC71585E3CE0B810073E70944C1DCCA9C245D0343E34`;
`ninja -n` → no work to do. Focused suite includes the new runners/tests.

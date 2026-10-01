# Lane 15 — Unmarked Spectralids (ShijimiChou, EnemyID 77) native slice

Implementation owner: Codex via shared account `4laric`. Executing agent/session:
opencode (deepseek-v4.1-flash). Root worktree `output/p2-lane15-shijimi-root`
(branch `opencode/p2-lane15-shijimi`, base `ef34e84`); native worktree
`output/native-lane15-shijimi` (branch `opencode/p2-lane15-shijimi-native`, base
`f14c6851`). Private native build `output/native-lane15-shijimi-build`.

Source of truth (read-only decomp `native/pikmin2-research`, revision
`632af93787b9c95b63f0c13be32b161375ce3a96`): `include/Game/Entities/ShijimiChou.h`,
`src/plugProjectMorimuraU/shijimiChouState.cpp`, `shijimiChou.cpp`,
`shijimiChouMgr.cpp`.

## 1. Source identity

| Field | Value | Evidence |
|---|---|---|
| EnemyID | `EnemyID_ShijimiChou = 77` | `include/Game/enemyInfo.h:136` |
| Common name | Unmarked Spectralids | `enemyInfo.h:136` |
| Class | `Game::ShijimiChou::Obj` / `Mgr` | `ShijimiChou.h:58,160` |
| Spawn flag | `EFlag_CanBeSpawned \| 2 \| EFlag_UseOwnID`; also helper child of Tanpopo/Ooinu_l/Magaret/Damagumo | `enemyInfo.cpp:106`, `:70,76,83,90` |
| Registration | `generalEnemyMgr.cpp:471-477`; surface limit 10, cave `SHIJIMICHOU_GROUP_COUNT`=25 | `ShijimiChou.h:245` |
| Group count | 25 | `enemyInfo.h:211` |

FSM (`shijimiChouState.cpp:15-25`): `wait=0, fly=1, fall=2, dead=3, leave=4,
rest=5`. Anims (`ShijimiChou.h:285-290`): `carry=0, dead=1, move=2`. Retail
proper parms (`flying.json` / `docs/PIKMIN2_FLYING_REMAINDER_ASSETS.md`):
`fp01 max_fly=250`, `fp08 plant_fly=250`, `fp02 nectar=0.2`, `fp03 height=70`,
`fp04 pitch=0.02`, `fp05 amp=2.0`; general `fp00 health=200`, `fp06 speed=150`.

**Asset status:** already converted by the batch-1 flying family import
(`output/p2-lane-verify/flying/ShijimiChou/`): `enemy.bmd` (5600 B), `carry/dead/
move.bca`, and 6 sampled poses `fly_ShijimiChou_<clip>_{00,01}.mod` (6496 B
each). No new conversion performed. The batch-2 `pikmin2_flying_install.py`
deliberately rejects a ShijimiChou actor row (`HELPER_SPECIES`); this lane wires
an explicit Shijimi staging path over the same converted poses.

## 2. Native slice

Files (native worktree): `pc_port/pc_p2_shijimi.cpp` + `.h` +
`pc_p2_shijimi_policy.h`. Additive hooks, no-op for unregistered actors:
`CMakeLists.txt`; `include/teki.h` param chain; `src/plugPikiNakata/
tekibteki.cpp` (`pc_p2_shijimi_update` from `BTeki::update`, `pc_p2_shijimi_
suppress_ai` from `BTeki::doAI`, draw delegates); `tekimgr.cpp` reset/forget;
`pc_port/pc_p2_preview.cpp` setup.

The module loads `p2-shijimi-bank.txt`/`p2-shijimi-actors.txt`, verifies every
pose byte and material-resource equality before loading, and drives the source
state machine on the private P1 Chappy placement vehicle. Recorded port
adaptations: cluster is 2 actors (no P1 Spectralid group factory), members trace
the leader instead of the P2 group-owner offset; spawn source fixed to
plant-origin; Fall begins at health<=0 (no P1 stick latch); background effects
not ported.

## 3. Build provenance

- Generator Ninja; `gcc`/`g++`; Release; `PIKMIN_NATIVE_JAUDIO=ON`; `-j 6`.
- Build dir `output/native-lane15-shijimi-build`; target `pikmin_pc`;
  `cmake --build ... -- -n` → `ninja: no work to do.`
- `bin/nectar.exe` 7 348 638 bytes; SHA-256
  `9cc0f535aa7cb7d961334799c2050abec976b19093324b1c465a3662a77a2bbc`.

## 4. Runtime (private GL run)

`nectar.exe --experimental-pikmin2-room`, cwd = private arena
`output/p2-shijimi-lane15/d2e404d35eef4cd3a88475006b851d15/`,
`PIKMIN_P2_ROOM_WINDOW=960x540`, 35 s then terminated. Log
`shijimi-run.log`.

Witness lines:

```text
[PC Port] Experimental preview window set to 960x540 windowed and centered
[Pikipelago] P2_ROOM_PREVIEW room=room_4x4a_4_conc red=20 isolated=1
[BBFT] Direct boot: Forest of Hope day 2, 20 reds
P2_SHIJIMI_BIND generator=204001 source_id=77 visual_only=0
P2_ENEMY_READY species=ShijimiChou native_family=Chappy generator=204001 x=-150.0000000 y=30.0000000 z=1850.0000000 health=200.0 max_health=200.0 behavior=native source_FSM=implemented attack=none reward=P1_nectar source=plants leader=1 group_count=2
P2_SHIJIMI_BANK poses=6 mod_bytes=38976 texture_attach_calls=0 load_seconds=0.189
P2_SHIJIMI_DRAW corpse=0
P2_SHIJIMI_STATE generator=204001 state=wait
P2_SHIJIMI_STATE generator=204001 state=fly
P2_SHIJIMI_STATE generator=204001 state=leave
P2_SHIJIMI_KILL generator=204001 source_id=77
P2_SHIJIMI_CORPSE generator=204001 source_id=77 native=host_die
```

Natural sequence `wait -> fly -> leave -> host die` observed on both the leader
and the member, with the member tracking the leader (positions converge). No
`Extinction` in the log. Contract validator: `passed=true` (identity, ready,
window, bank, draw, wait, fly, departure, no_extinction).

## 5. Six-gate status

| Gate | Status | Note |
|---|---|---|
| 1 identity/spawn | PASS | `source_id=77`, birth XYZ matched, 20-red squad |
| 2 movement/animation | PASS | natural `wait/fly/leave` + sampled `move` poses drawn |
| 3 attacks/receivers | source-backed N/A | source `damageCallBack` returns false; no family attack |
| 4 death/corpse | UNTESTED | Fall/Dead requires a natural health endpoint; only Leave-cleanup die observed |
| 5 transport/reward | BLOCKED | `genItem` nectar marker only; reward semantics are lane 06 |
| 6 cleanup/re-entry | BLOCKED | #397 lifecycle |

Injected vs natural: everything above is natural engine execution; no fixture
lethal injection is performed by this slice.

## 6. Remaining dependency / blockers

1. Physical reward semantics (`Egg`/Honey) and receipts — lane 06.
2. Cleanup/re-entry and scene/save teardown — #397.
3. Receiver combat requires a real attacker; source `damageCallBack` is a no-op.
4. Full 25-member source group factory / sound cluster not ported.
5. Native candidate not on the maintained line; lane 01 owns export/acceptance.

## 7. Tests

`py -3.12 -m pytest tests/test_pikmin2_shijimi_install.py -q` → 11 passed.
Coverage: bank header/clip order, install+verify round-trip, wrong enemy ID,
event mismatch, pose-hash mismatch, duplicate/overlapping actors, and the
lifecycle validator (accept good, reject extinction/missing window/missing
departure).

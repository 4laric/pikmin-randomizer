# Mamuta native binding — #230 / #221

This is a buildable, opt-in P2 appearance on the P1 Miurin actor. It does not replace P1 AI, attack receivers, collision, cargo or population bookkeeping.

## Integration handoff

Copy `experimental/native_mamuta/pc_p2_mamuta.cpp`, `.h` and `_policy.h` to native `pc_port`. Generate the exact central patch with `experimental.pikmin2_mamuta_hooks.hook_patch(Path('engine'))`. The generator requires the existing Tank hook anchors and fails when their count changes; it never edits the engine. The generated patch adds CMake/setup, live and PelletView draw delegation, three manager reset sites and actor forget. Root owns applying and building this patch.

The current local patch is `output/p2-lifecycle-batch/mamuta-native-01/hooks.patch` outside the integration checkout. No shared native files were edited for this increment.

Kimi's `P2_MAMUTA_ACTORS_1` remains unchanged: 1–100 unique unsigned generator IDs followed by `Miulin`. Exact native type must be `TEKI_Miurin` (24), and all configured actors must be found once. Missing configuration cleanly declines. Invalid configured data fails closed. Loading is capped at 16 MiB/model, 48 MiB total, and validates MOD resources before loading. Host installer SHA verification remains authoritative; native does not add a different manifest or claim runtime cryptographic verification.

## What is rendered

The importer supplies three **static anchor models**, not continuous animation:

| Native condition | Source anchor |
|---|---|
| Wait1 (2) | first `wait.bca` pose |
| Type1/Type2/Type3 (10/11/12) | first `attack1.bca` pose |
| Dead (0), or registered PelletView corpse draw | last `dead.bca` pose |
| Any unsupported motion or unregistered actor | original P1 rendering |

`TAImiurin.cpp:488` selects Type1/Type2/Type3 according to captain angle and dispatches actual hand interactions at animation events. `TAImiurin.cpp:858` distinguishes `Attack` preparation from the subsequent three swings. Preparation therefore falls back to P1. `TAImiurin.cpp:844` supplies Dead. Compile-time assertions protect the numeric enum policy.

The original shape still updates native collision before draw delegation. Imported visuals use the caller's existing camera/world matrix, actor scale and position. No source animation events are synthesized. Movement can visibly return to the original P1 appearance until additional source clips are imported. The imported dead anchor does not change corpse shape, weight or carrying logic. Reset/forget remove all retained actor references; no side-spawn ownership is introduced.

Kimi arena generator 221001 is Miurin at (-150,30,1850). Generator 221002 is an ordinary Chappy control, not same-family Miurin. Runtime acceptance must include an additional unregistered Miurin control if same-family fallback is claimed.

## Validation and remaining runtime gates

`py -3.12 -m unittest tests.test_pikmin2_mamuta_native -v`: two tests pass, including compiling and executing the actual C++ policy and exact hook generation. Private compilation of the entire module also passes using frozen b602 Tank fixture headers; command/log/object are in `output/p2-lifecycle-batch/mamuta-native-01`. This is compile evidence, not current linked runtime evidence.

Root's next build should verify exact generator/full XYZ, visible wait/swing/death anchors, ordinary Chappy and Miurin fallback, manager reset/forget and absent-profile boot. No shared build or runtime execution was performed here.

## Planting observer and translation contract

Source P2 `native/pikmin2-research/src/plugProjectKandoU/interactPiki.cpp:377–442` supplies the behavior reference (revision 632af93787b9c95b63f0c13be32b161375ce3a96). In the US profile, reject invincible targets and the `GameStat::mePikis >= 99` condition; PAL subtracts zikatu before its cap decision. Successful conversion births a same-kind flower sprout and removes the original with `CKILL_DontCountAsDeath`. Bald terrain, missing manager or failed birth falls back to Walk. These are distinct branches, not an unconditional flower upgrade.

The next isolated observer must record: actor/generator identity, actual hand event, target stable identity/kind, pre/post party and sprout totals, invincibility, cap count including its region/profile, birth success and original removal reason. Required cases are normal conversion, exactly98/99 boundary, invincible, missing manager/birth failure and repeated hit on the same target. Acceptance is conservation of one same-kind individual with no death/check/receipt duplication. Existing P1 in-place flowering is only proxy evidence and must not pass that acceptance. A native translation hook needs root approval after observing the existing receiver; this binding contains no planting mutation.

## ShijimiChou ownership gate

P2 Miulin birth creates five ShijimiChou above the owner when its manager exists (`miulin.cpp:27–43`, `ShijimiChou::Mgr::createGroupByEnemy`; owner declaration in `ShijimiChou.h:188`). This module creates none. Before adding them, use an explicit live owner registry/generation token, clear or safely detach followers on owner death/forget, and clear both directions on manager reset. Save/load must rebind by stable owner identity, never serialized pointers. Tests must cover owner death first, follower death first, reset, pointer reuse and restore without the owner. A null check alone does not protect stale owner pointers.

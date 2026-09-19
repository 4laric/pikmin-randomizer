# PIKMIN2 tutorial challenge-row landing-request packet (issue #754, recovery e8e113b9)

Lane `tutorial-row-landing-request`, generation 2. Diagnosis / packet only:
this deliverable produces the exact landing spec for the pinned
`ch_ABEM_tutorial` row into `pc_bbft.cpp` `kP2ChallengeStages`, the CMake
membership assessment, the #186 decision request, and the downstream record
for the blocked consumer. It edits no engine/shared file, runs no build, and
never claims an engine unblock. No ADMIT.

## Source contract (#754, read-only)

- Lane `tutorial-stage-table-row-native`, issue #754, native commit
  `b7fdfbbe36a02ff9827240c8327ecebb55a3e712`.
- Row module `native/pc_port/pc_p2_challenge_tutorial_stage.h/.cpp`
  (blobs `cdc8c806...` / `039e1971...`), handoff-gen3 sha256
  `3d2df14222e7ab1e98d5a69486dbeed360788a250e080233d5d8e8f42e77ccc`.
- Pinned row: `ch_ABEM_tutorial`, cave path
  `user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt`, source sha
  `e21f31f7...`, ui 0, order 0, floors 2, timers [100,100], roster
  `[0,0,0],[50,0,0]`, bitter 2, spicy 2, legacy 0.0.

## Destination pins (live, drift recorded)

The launch brief named root `94582923` / native `68ac7496`; the live
integration heads at authoring are:

- root `output/dsw/wave-root` @ `f2803e423b9f30ee6fcaf79004be02b2770a5a98`.
- native `output/dsw/native-wave` @ `b944db033a3eef7aabb135372c4656d04e47bd7d`.
- `kP2ChallengeStages` at `pc_port/pc_bbft.cpp`; the table carries only the
  `ch_NARI_01kusachi` row, so the boot selects no tutorial stage.

## Generated unified landing spec (exact)

```
--- a/pc_port/pc_bbft.cpp
+++ b/pc_port/pc_bbft.cpp
@@ -47,3 +47,10 @@
       { {0,0,50}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },
       1, 2, 350.0f, 0 },
+    { "ch_ABEM_tutorial",
+      "user/Mukki/mapunits/caveinfo/ch_ABEM_tutorial.txt",
+      "e21f31f7fa5621a5922d9ee54ffb211a8e4f0e797866d70cc1edb98389ab097d",
+      0, 0, 2,
+      { 100.0f, 100.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f },
+      { {0,0,0}, {50,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0}, {0,0,0} },
+      2, 2, 0.0f, 0 },
 };
```

Insertion anchor: after the last `kP2ChallengeStages` row, before its closing
`};` (destination line 49). Field order mirrors `P2ChallengeStageRow`.

## CMake membership assessment (no edits)

Appending a data row edits the already-compiled `pc_port/pc_bbft.cpp`
translation unit; **no new `pikmin_pc` source membership is required**. The
#754 `pc_p2_challenge_tutorial_stage.cpp` module is a separate serialized
integration concern. Do NOT edit `native/CMakeLists.txt` or
`native/pc_port/pc_bbft.cpp` here (owned by the #755 / #736 line).

## #186 decision request (required before landing)

- Scope: append the pinned `ch_ABEM_tutorial` row to
  `pc_bbft.cpp` `kP2ChallengeStages` (serialized shared-file change).
- File: `native/pc_port/pc_bbft.cpp`; source pins as above.
- Options: `approve` / `approve-with-changes` / `reject`.
- This packet grants no decision and no landing.

## Downstream record

Recovery `e8e113b9`, consumer lane
`p2-challenge-ch-abem-tutorial-p1-runtime-obs` (#534). Still blocked on the
#186 decision and the serialized #755/#736 landing; no runtime claim.

## Fail-closed behavior

`validate(pc_bbft.cpp)` returns `verdict` true only when the table parses,
only the known existing row is present, the pinned row is absent, and the
emitted spec round-trips the literal. Missing struct/table, an unexpected
existing row, an already-present row, or a spec that omits the literal or
source sha all refuse. Tests:
`tests/test_pikmin2_tutorial_row_landing_request.py` (13 cases).

## Boundaries

Read-only packet job: no engine/shared edits, no builds, no launches, no
runtime runs, no ledger writes. It is diagnosis only and never an engine
unblock.
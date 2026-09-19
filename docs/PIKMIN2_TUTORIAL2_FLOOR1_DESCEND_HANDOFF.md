# Floor-1 descend-chain handoff for the #747 persistence round-trip (#817)

Lane `tutorial2-floor1-descend-handoff`, generation 2. Machine-readable
descend-chain packet emitted read-only from two DONE producers for downstream
`p2-cave-tutorial_2-p1-later-floors` (#747, blocked gen 5). No native/shared
edits, no builds, no launches, no ADMIT. All six gates UNTESTED.

## Source pins (all verified read-only)

- Floor-1 producer `p2-cave-tutorial_2-p1-runtime` (done gen 2, #152):
  root head `9fd930894c40fb6b6e8b9b4889a2583f40448519`, handoff
  `4cb92a8a98972c14ef8e8d84a0f04727b2803c49e4254b605566657a5b6f2735`.
  Brief pin `ebb643bb` (integrator-compat commit for #152) verified present
  and carrying the floor-1 adapter; origin entries cited at that pin.
- Policy producer `tutorial2-descend-policy-native` (done gen 2, #757):
  root head `1075e1ab65e211d17a8e683d921be24738ee9b60`, native head
  `eaabe9c816478b35b95e7fe8efe4de9a87096537`, handoff
  `3cacd9ac4cb778db1147e37ad71d257cd797d37f23bc6154b6bdebe2739f0128`.

## Packet contents

- Origin: tutorial_2 floor 1, pool `3_MAT_mid1_mid2_uzu1_snow.txt`,
  YellowKochappy 4 / YellowChappy 2 / Demon 2 / GasHiba 2, treasures 2,
  20-squad baseline (`squad [[1,1]]*20`, boot observed `squad_alive=20`,
  `P2_CAVE_READY floor=1/20`), anchor `hole`.
- Policy: `P2_CAVE_ENTRY_4` admits staged floors 3-8 under the 32-hex token
  contract; floors 1-7 descend, floor 8 terminal.
- Citations: adapter `experimental/content_lanes/p2-cave-tutorial_2_p1.py`
  at `ebb643bb` (:219 squad, :224 anchor, :72-94 pool/tokens/treasure, :40
  source sha); engine `native/pc_port/pc_p2_cave.cpp` at `eaabe9c8` (:58
  ENTRY_4, :59/:64 floors 3-8, :69-72 descend/terminal); registry
  `experimental/pikmin2_tutorial2_descend_policy.py` at `1075e1ab` (:18-20,
  :54-68).

## Downstream re-run check

Pin this packet and re-run the #747 persistence round-trip over floors 1-8;
floor-1 origin plus ENTRY_4 policy above are the entry/anchor authority.
Recovery `4c0b8b7263d2d917fa8c7761e03928cde1e531e825db0abd128b9533c9e697b9`.

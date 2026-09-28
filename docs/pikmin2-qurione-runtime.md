# Honeywisp integrated runtime evidence (#203)

Native b602d8c43dc6a1132821f787b99a28097c3c7521. Fresh production fixture snapshot
passed initial/final Ninja and hash checks; base/provenance.json under
output/p2-qurione203-runtime records copied link inputs and original build state.
Private fixture sources and copied headers are under snapshot/ and fixture*/.
No shared build, native edit or player save was modified.

New experimental/pikmin2_qurione_runtime.py instruments the existing original-map
observer. It performs ordinary engine updates and the established legitimate
A-input tutorial dismissal. Captain reposition is a labeled camera/proximity
stimulus. One InteractAttack(Navi,nullptr,1,false) is injected through stimulate;
no enemy state, animation or health field is directly written. This establishes
receiver behavior, not player throw collision or P2 Pikmin-only hit eligibility.

First run: observe/, exit0,25.53seconds, executable
8894d6f57e4b6ff12374d9f5682e4ddebc3c71909dc0c6026584f64cc5932908.
Requested birth/generator XYZ exactly matched for both actors; health/max1 matched
host/control. Draw delegate and native counter changes were observed. Fixed tick120
attack occurred while hidden in state1; rejected, no nectar. Preserved evidence,
not silently discarded. observe/arena.png is the captured imported white Honeywisp
silhouette plus host glow. Material fidelity is NOT accepted.

Second run: visible/, exit0,28.41seconds, executable
0f736cdedbac210111f0146bd6592644287adbec26a6e43409601ab256e0f74f.
Tick20 attack accepted during visible motion. Native DropWater state4 produced
creature pointer2 with type6 at tick33; the pointer persisted through subsequent
frames, then actor advanced through escape/dead and was removed. This is the real
P1 nectar receiver/event path. No Egg was spawned and no P2 receipt was awarded.
Unique creation count/consumption/idempotency were not instrumented and are not
claimed. The proxy had68 distinct counter values; ordinary control had2 in this
camera placement, insufficient for robust control-animation acceptance.

Gate summary: full birthXYZ/unchanged host health PASS; proxy live counter and draw
invocation PASS; visual material fidelity FAIL/needs follow-up; injected real P1
attack-to-nectar path PASS; natural thrown-Pikmin collision UNTESTED; full ordinary
control animation UNCONFIRMED; manager cleanup/reentry and mixed-scene performance
UNTESTED. The source does not provide a P2 Egg implementation through this bank.

Three focused parser tests pass. New test module tests/test_pikmin2_qurione_runtime.py
separates completion, accepted attack and positive nectar evidence so empty/rejected
runs cannot be mistaken for reward success. Runtime evidence JSONs and raw logs stay
local under output/. This is a bounded validation result, not full family sign-off.

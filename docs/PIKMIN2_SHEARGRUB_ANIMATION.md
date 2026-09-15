# Sheargrub sampled visual bank

This is an asset-only increment under #165/#154/#186. It preserves the proven P1 proxy lifecycle. No source animation event executes gameplay, and no native renderer or controller is changed.

Run `py -3.12 -m experimental.pikmin2_sheargrub_animation --imported output/p2-sheargrub-assets-batch/verified --output output/p2-uji-animation-batch/bank01`. Existing source model, registry and BCA bytes must match their import hashes. All inputs are checked before output creation. A failed conversion has no completed animation-bank.json. Source assets remain local.

The bank contains all seven registered UjiA clips and all nine UjiB clips, with at most 12 sampled rigid poses each, 256 KiB per clip and 2 MiB total. Texture/material resources must be byte-identical across each species' poses. Source frames, hashes and registry events are retained; materials remain the converter's approximation. This is sampled visual playback preparation, not skeletal animation or source AI.

| P1 TekiMotion | Source clip | Constraint |
| --- | --- | --- |
| Dead | dead | Carried corpse uses final frame |
| Damage | dead_p | P1 crush-death motion |
| WaitAct1 | appear | Waiting freezes frame0; preserve native invisibility |
| WaitAct2 | dive | Burrowing |
| Move1 | move | Movement/chasing |
| Attack | attack1 | Bridge attack for both species |
| Type1 | attack2 | Male UjiB bite only |
| Type2 | eat | Male UjiB chewing only |

The registered type5 clip is preserved but explicitly unmapped. Do not assign unknown native motions to male bite or invent a female bite. P1 strategy constructors establish these mappings: native/src/plugPikiYamashita/TAIkabekuiA.cpp:224-254 and TAIkabekuiB.cpp:251-290. P2 source UjiaState.cpp and UjibState.cpp under plugProjectNishimuraU distinguish bridge Attack1 from male Attack2/Eat; enemyanimmgr.txt gives actual BCA identities/events. Motion durations are not assumed interchangeable.

Proposed subsequent native scope: only pc_port/pc_p2_sheargrub.cpp plus an optional family-only policy helper, retaining the existing renderer callback/API. A separate strict opt-in bank file would load capped poses, select by native motion and normalized visual progress, freeze waiting/corpse endpoints, and leave native FSM, attack events, collision, corpse identity and receipts untouched. Missing opt-in must retain current static visuals. Unknown motions require an explicit fallback policy before implementation. No shared native edits are included here.

Validation: four focused tests pass. Real US-source import produced 192 MOD poses across 16 clips, totaling 1,227,648 bytes at output/p2-uji-animation-batch/bank01/animation-bank.json. All resource invariants passed. native_ready remains false until coordinated renderer integration and runtime acceptance; no visual or manual gameplay sign-off is claimed.

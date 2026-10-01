# Generator position correction

P1 common generator records store a position at byte 48 and an additive position offset at byte 60. They do not store Euler rotation in that second vector. `Generator::read` (`native/src/plugPikiKando/generator.cpp:781`) decodes the two vectors, and `Generator::getPos` (`native/include/Generator.h:960`) sums them.

The floor 2 Violet, Beasts Uji and general Emergence roster writers previously put source yaw in the offset's Y component. This elevated actors by their source angle. Native observation showed the Violet at source (-55,0,75) spawning at (-55,215,75), with its collision sphere well above the thrown Pikmin. The other Violet was elevated45 units. Earlier full-source-transform claims for these profiles were incorrect.

All three writers now use `experimental.pikmin2_generator_pose.write_position`, which writes zero generic offsets and validates the effective XYZ. Their source `angle`/`yaw` fields remain in metadata with `source_yaw_applied=false`; actor-specific orientation is not implemented through this common record. Floor2 policy is `P2_BEASTS_FLOOR2_PREPARE_3`, Emergence policy `P2_ENGINEERING_ROSTER_3`, and Uji reports `P1_POSITION_OFFSET_1`. Existing profiles/saves are not rewritten.

Thirteen focused tests pass. Regression examples decode position plus offset and reject the exact old yaw-as-height error, including215/45/300 values. Fresh local preparation validates ten Uji and six Emergence actors against intended XYZ. This does not establish their corrected native combat/hauling acceptance; previous native tests observed the old elevated profiles.

Corrected floor2 runtime against native d1efd5ac confirms both source XYZ positions with Y0. Both flowers now accept Pikmin and convert: flower0 produces2 sprouts and flower1 produces5. The existing injected-throw fixture still times out at7 instead of10, with three surviving originals Normal/unattached near flower0. Thus the height bug is resolved, but the full ten-sprout acceptance remains incomplete; no further throw-input variants or production changes were made in this fix batch.

Evidence lives locally under `output/p2-generator-offset-fix/`: native conversion log `validation/runs/849087d446784876b82ff200d845d6ef/native.log`, ten-Uji preparation `uji-runs/d5da6c5b047d42cfa05f14a555bdcabc`, and Emergence preparation `emergence-runs/16ca07e69f3b4156bddf2c7b29c5022b`.

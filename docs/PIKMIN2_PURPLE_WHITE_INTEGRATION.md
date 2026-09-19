# Purple impact and White foundation integration

2026-09-13. User-authorized parallel implementation by two Sol subagents, coordinated and reviewed by Codex through shared GitHub account `4laric`. Issues [#393](https://github.com/4laric/pikmin-randomizer/issues/393) and [#395](https://github.com/4laric/pikmin-randomizer/issues/395) remain open for their remaining implementation and gameplay gates.

## Integrated scope

Purple adds an explicit opt-in landing earthquake and registered Red Dwarf Bulborb bounce/Fit receiver. White adds separate species identity, source asset extraction, generator-bound Ivory conversion, selection/stat/rendering hooks and versioned restoration-only cave boundaries. See the [Purple specification](PIKMIN2_PURPLE_IMPACT_SPEC.md), [Purple implementation evidence](PIKMIN2_PURPLE_IMPACT_GATE_AB.md) and [White specification](PIKMIN2_WHITE_SPEC.md) for scope and limitations.

Both sets of native modules are registered in `native/CMakeLists.txt`. Shared throw/pluck/species changes were coordinated. Existing unrelated changes in `creatureCollision.cpp` and `goalItem.cpp` were preserved. No player session or shared Archipelago installation was modified.

## Integration review

- Purple arming uses a real captain throw, not every transition to Flying, which would also catch rescue behavior.
- Stun uses a dedicated Chappy state with normal damage/death actions; there is no whole-strategy freeze. Repeated state entry preserves the original return state. Unsupported enemy-state semantics remain bounded by an explicit allowlist.
- Existing Purple profiles leave impact disabled unless they request `impact red_earthquake_v1`.
- White conversion binds explicit generator IDs. The preview builder rejects combined Purple/White preview configurations rather than silently repurposing all flowers.
- White restoration schema 2 rejects every species increase until source-instance conversion accounting exists. Total-body conservation alone is insufficient authorization for a conversion. Schema 1 retains existing behavior.
- White carrying strength is one body; carrying speed has separate extracted parameters and does not depend on a loaded Purple profile.
- Extracted White `p008` has no verified live source use, so it is retained as provenance and is not applied as a 1.5 model scale. Movement remains an explicitly documented adaptation to the P1 movement path.

## Build and automated evidence

Final Windows Release production build, JAudio enabled and test hooks off, passed with both lanes integrated. Local build log: `output/p2-white-cleanup-build.log`. Executable: `native/build-randomizer/bin/nectar.exe`, SHA256 `21cd4a81455cdd18d7317a59598d556b033e029a2757eb642b7be1b7e7a3170f`.

The build used native HEAD `787345044e5f3ce559c07dc122239f967f20902f` plus the uncommitted implementation changes. That HEAD alone does not identify the complete implementation. Runtime fixture provenance records the copied inputs separately.

Focused integrated command:

```text
python -m pytest -q tests/test_pikmin2_purple.py tests/test_pikmin2_campaign.py tests/test_pikmin2_purple_emitter_reference.py tests/test_pikmin2_kochappy_stun_reference.py tests/test_pikmin2_white.py
```

Result: **24 passed, four subtests passed**, including local White extraction/preparation checks. Purple's standalone policy and source-linked Tai transition checks passed separately. The Tai harness uses structural and damage/death stubs and is supplementary ordering evidence, not native corpse-path validation. Whitespace checks passed.

## Runtime acceptance boundary

The White fixture exercised actual throws into the bound Ivory bud and real conversion/pluck callbacks: five White sprouts and fifteen remaining actors returned to twenty actors after plucking. It checked distinct White identity/selection, leaf carry power and absence of Red immunity. The scripted fixture is not controller sign-off. A private close-up then staged Whites separately and confirmed white bodies/red eyes on two visible actors; bloom and geometry obscure the others, so this is model-presence evidence rather than polished visual fidelity.

White evidence: `output/pikmin2-white395/fixture-closeup-03/provenance.json` records a successful private build; `output/pikmin2-white395/runs/2bc51e725f9f4797910ee49ef94aa150/native-white-closeup-03.log` records the passing run. Its PNG is `p2-white-closeup.png` in the same run directory, SHA256 `a954f0869421a41ecd672b79499f591e8a1a986387f978ac254231a2b890e3b6`. [Issue #395 evidence](https://github.com/4laric/pikmin-randomizer/issues/395#issuecomment-5656252484) records the remaining gates.

Purple native arena evidence subsequently passed in `output/p2-purple-impact393/run-private-02/native-window.log`, using the successful private build recorded by `fixture-private-02/provenance.json` in that lane's output directory. Actual captain throw and ground-bounce callbacks emitted an accepted earthquake; the registered Red dwarf remained active and grounded in impact state 16 for 90 frames. An actual `InteractAttack` reduced health from 200 to 195; a lethal attack entered the normal death sequence and produced the corpse. The fixture exited successfully. [Issue #393 runtime evidence](https://github.com/4laric/pikmin-randomizer/issues/393#issuecomment-5656279180) records this scripted native result.

Earlier Purple fixture attempts were not passes: nearby actors interfered, and a near-zero vertical-velocity observation rule was invalid for this engine's grounded physics. The successful private fixture isolates actors and uses sustained active-and-grounded observation. It does not prove controller play, all eligibility flags, direct-hit P2 fidelity or other enemy families.

Neither foundation completes the full species specification or a campaign. At that boundary, Purple direct-hit fidelity and White predator poisoning were still separate work; batch 2 below supersedes those two gaps. Full HipDrop flight/recovery/feedback, broader enemy coverage, White gas, buried digging, ship storage and source-bound campaign conversion remain open.

## Batch 2: landing damage and swallowed poison

The next user-authorized batch continued the two Sol lanes in private native worktrees. The prior foundation was committed as `39245d7ba3c8e6e0a92018abd8e569109464995a`. Other integration work advanced maintained native to `356e9c08`; those changes were preserved when merging White as `1fb98b323e1c17215668c30fd67f8b6d178cdd87` and Purple as `a344b472940add296df44a54b608c99d98aa0cdf`.

- [Purple direct hit](PIKMIN2_PURPLE_DIRECT_HIT.md): separate opt-in profile, registered native adult Bulborb generic landing damage `fp36=50`, independent wave/direct deduplication and supported P1 attachment-shape dispatch. The real collision fixture found and drove the fix for an unsupported attachment shape. Adult damage, lethal handling and one stable corpse passed; the additional Red dwarf crush adapter is implemented but its native eligibility/Pressed/corpse gate did not pass and remains follow-up work.
- [White swallowed poison](PIKMIN2_WHITE_POISON.md): explicit adult bindings, successful mouth-consumption callback, retail proper `fp02=750`, additive queued damage without a flick-hit count, invulnerability handling and pooled actor reuse cleanup. The native fixture passed real swallow/kill callbacks and normal corpse creation with injected mouth attachment/key event.

The combined production Release build passed with JAudio enabled, `PIKMIN_NATIVE_OPTIMIZE=OFF` and test hooks off. Build log: `output/purple-white-batch2-integration-build.log`. Production source HEAD at build: `a344b472940add296df44a54b608c99d98aa0cdf`. Executable SHA256: `2208db5f3e3cf0436491703ffd1d5cd90d2283cade1804ad96b937f32fad4dc7`. The subsequent Ninja dry run reported no work. Existing unrelated EOL-only changes in `creatureCollision.cpp` and `goalItem.cpp` remain preserved.

The focused root suite passes **41 tests and eight subtests**, including the prior foundation tests and the new `test_pikmin2_purple_direct.py` and `test_pikmin2_white_poison.py`. These source/config tests supplement the lane-specific scripted native evidence; they do not constitute controller or full campaign sign-off.

The final fixture-only Purple follow-up was merged as native `ac86dc0d4fe433d6e26d2180526c4d17877ffe58`. Production inputs and executable stayed unchanged; Ninja again reported no work. `python scripts/export_native_source.py` then refreshed **1,567** source files into `engine/`, including both abilities and their reproducible fixtures. The exported Purple direct-profile and White poison event-policy C++ tests compiled and exited zero. No binaries, disc assets, build directories or player runtime data were exported.

# Isolated regular day-end skip guard proposal (#225)

The one-Start reproducer demonstrates that finishing a phase-one day-end movie early can reveal retained P1 Tank actors after their display-list storage has been reused. This proposal prevents that specific unsafe completion; it does not change the renderer, allocator, enemy behavior or the general skip policy.

The isolated patch adds a nine-line check inside `MoviePlayer::requestSkip`, after the existing UI-owned-background check. It rejects active movie IDs found in the existing `movie32table` and `movie56table`, covering all stage translations of ChalDayEnd and TakeOff, including Final Trial. `MovieInfo` stores translated IDs, so checking only IDs32/56 would be insufficient. Intro, gameplay, phase-zero day-end and unrelated movie IDs continue through their original path.

Patch: `output/p2-lifecycle-batch/tank-skipguard-link-02/moviePlayer.patch`. It is against frozen native `b602d8c43dc6a1132821f787b99a28097c3c7521`; no shared/native source is modified. `experimental/pikmin2_tank_skip_guard.py` generates the exact guard and optional private observation logs. The production patch contains no diagnostic logging. Integration belongs to root.

## Verification boundaries

Focused tests compile and execute the actual inserted guard snippet against translation tables parsed from native source and symbolic IDs parsed from MoviePlayer.h. They cover IDs0..119, empty lists and a concurrent list containing both an intro and an unsafe day-end movie. Additional tests require accepted native landing-intro skip, correct selective-block count, no GX warnings and no changed original Tank bytes submitted. Three tests pass.

The first private fixed run is retained as inconclusive: it accepted intro40 and processed24Attack samples but hit the old movement fixture's ready900 gate before reaching day-end. It was not counted as success. The new `scripts/pikmin2_tank_skip_guard_fixture.cpp` removes that unrelated movement-completion/reset gate while retaining the same natural attacks, captain placement, one queued Start route and overall120-second bound. It is diagnostic-only; it does not force enemy actions or captain damage.

The final private patched Start/no-edge pair and allowed native intro evidence are recorded below. Ending variants outside the two regular phase-one translation families remain separately scoped. Physical controller input, normal campaign and stock-upstream reproduction are not claimed by this fixture.

## Fixed single-Start evidence

Final private executable: `output/p2-lifecycle-batch/tank-skipguard-link-04/fixture.exe`, SHA256 `2cb9e399f13c68ad33a76dca20a95c34e05c74bfc44998ceb424ccf308134a2c`. It uses the source-backed all-stage guard, with private observations and dedicated bounded fixture only. Exact compile/link/source provenance is retained through link-04/commands.json and link-02/commands.json.

`output/p2-lifecycle-batch/tank-skipguard-start-02/guard-result.json` records one scheduled/delivered/consumed Start at active demo56,22 natural Tank Attack samples, and one selective block for movie32. ChalDayEnd32 and TakeOff56 are concurrent, so the guard correctly refuses completion of their whole active list at its first unsafe member. The existing UI guard still reported allowance; the new resource-specific guard supplied the protection.

The run accepted3 native landing-intro40 skip requests and reached gameplay. It completed the120-second observation bound with zero GX warnings and zero changed original Tank bytes submitted after heap reuse. It timed out while waiting in day-end/results flow; this is not a completed campaign or save acceptance claim. The no-input control is recorded below once complete.

## Identical-binary no-input control and handoff

`output/p2-lifecycle-batch/tank-skipguard-control-01/guard-result.json` uses the exact same final executable. It records22 natural Attack samples, zero Start edges, zero selective blocks, accepted native intro skipping, normal demo56 progression, zero GX warnings and zero stale original Tank submissions across the120-second observation window. Thus the guard is inactive on the no-input path and does not disturb that control.

The isolated patch is ready for root review/integration. The final source patch remains link-02/moviePlayer.patch; link-04 only changes the private fixture to remove its unrelated movement gate. Apply only the patch, not the instrumented private moviePlayer.cpp. Root must build the integrated production target and keep normal-campaign, physical input, ending variants and stock-upstream validation distinct.

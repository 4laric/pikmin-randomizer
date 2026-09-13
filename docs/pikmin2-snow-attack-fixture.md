# Native Snow attack-entry receiver fixture (#120)

`experimental.pikmin2_snow_attack_fixture` instruments a private copy of
`native/tools/preview_p2_room.cpp`. The probe calls the production
`BTeki::attackableCreature` method on a real registered Snow actor. A controlled
Creature subclass supplies target position, alive/visible/buried flags and a
self-stick pointer. It never joins a native manager or runs an AI tick.

The fixture changes actor facing and target position between direct calls. It
updates their spatial-grid coordinates explicitly, because P1 contact eligibility
uses the grid before detailed geometry. It restores the direction before exit.
A copied original P1 predicate (contactCreature plus the original half-angle
comparison) provides the absent-policy and ordinary-actor baseline.

Cases cover 29/30/31 center distance, vertical separation with distance-squared
800 and929, both sides of the 20-degree limit, and facing wrap across 359/1.
Invisible, dead, buried and self-stuck targets must be rejected. An ordinary
same-family actor is born/reset and checked against the P1 baseline. Where the
registered Snow is removable, native manager kill/newTeki must reuse its address
and produce the original P1 result for every case. References are never forced.

No production source is patched by this harness. The method calls establish
attack-entry eligibility only. They do not measure bite hitboxes, capture,
swallowing, animations or P2 combat-state fidelity.

## Running

```powershell
py -3.12 -m experimental.pikmin2_snow_attack_fixture instrument --source native/tools/preview_p2_room.cpp --output output/my-attack-fixture/preview_p2_room.cpp
```

Compile/link the private source against a completed native build, replacing only
source/object/executable paths in the private fixture recipe. Add native/tools
to include paths. Do not link during a production rebuild. No shared binary is
replaced. Set PATH to include C:/msys64/mingw64/bin and SDL_AUDIODRIVER=dummy.

Run with `run --assets PATH --converted PATH --pod PATH --snow PATH --exe PATH
--output NEW_DIRECTORY`, adding `--policy PATH` for the extracted attack policy.
Omit policy for the P1 baseline. Outputs include native.log, capture metadata,
per-case measured squared distances/angles and evidence.json. The executable
hash is measured before launch and compared to capture provenance.

## Runtime evidence

Private fixture links fresh build-randomizer objects at native3cc4a532.
Recipe: output/p2-attack-runtime/fixture/commands.json.
Corrected fixture SHA256:
`9e2d81951719e9479a8ab46134ad5935a26dba66ba4a0e0f188531338d7754f7`.
Final output directories are baseline-grid and opted-grid under
output/p2-attack-runtime. The earlier baseline run omitted the synthetic target's
grid update and was rejected by P1 broad-phase culling. That was a fixture setup
error; no production change was made.

The P1 native yaw calculation uses approximated angles: requested19.9/20.1
positions measured approximately19.918/20.116 degrees. These bracket the source
half-angle; exact inclusive20 is covered by the compiled policy unit test.
Do not infer sub-degree P2 numerical parity from the controlled runtime test.

Eight harness tests reject missing/duplicate cases, mismatched outcomes, wrong
policy mode and failed exits; the attack-policy suite adds16 tests. Evidence
validation also independently checks enabled-policy measured geometry and the
expected positive/negative case pattern.

Final fixture revision adds a fallback for nonremovable original actors: a freshly
born ordinary actor temporarily borrows the original generator identity while
pc_p2_snow_setup registers it through the real bank loader. Generator pointers
are immediately restored, its receiver cases are checked, then native kill/birth
reuses that unreferenced actor. This is controlled fixture setup, not a natural
scene respawn; no reference counts are edited. The final opted run reused the
original actor directly, so that fallback was not needed in that run.

Final accepted runs: output/p2-attack-runtime/opted-final and baseline-final.
Final executable SHA256:
`46f91d71988e47875671495efea0d735bd9d24cf9de5c06a075246797e368f5a`.
The enabled run passed all receiver geometry, recognition, self-stick, ordinary
baseline and original-actor same-address reuse checks. There are nine harness
tests, 25 together with attack-policy tests. See each evidence.json for the
captured exact binary identity and individual measured outcomes.

# Dedicated Demon drop state prototype (#242)

Base2c08d6b8. PC-only appended ID36/Count37; retail0-35 and non-PCCount36 preserved.
New module and four narrow shared file changes are isolated in this worktree.
Exact hook-only diff: output/demon-registered-hooks.patch. Not applied to shared native.

Physics: entry rejects rope/stick/flying/ignore-gravity/disabled movement, clears
current+previous triangle and stale platform, resets fixed/on-ground status and
sets current fixed reference. Assigns actualY=-400, full target=(0,-speed,0),
volatile zero. Dry static floor only. Post-Navi Creature update zeroes actual,
target and volatile only while the same dedicated state owns grounded recovery.
Reset invalidates ownership and clears owned velocity/contact before native reset;
it does not teleport and gravity may resume under the next state at altitude.

Damage: JKoke END commits Lay before real InteractAttack. RAII guard permits
same-stack resume; restart preserves phase. Rejected damage is consumed once,
without retry, and undamaged recovery proceeds. Lethal result leaves the Dead
transition to native outer finishDamage, preventing duplicate Dead init. External
InteractAttack resume explicitly quenches drop velocity before moving to Walk.

Animation issuance: each owned motion gets a distinct retained deque listener,
with captain generation and issuance serial. It validates ownership before calling
Navi::animationKeyUpdated, preserving native finishDamage behavior. MsgAnim is
accepted only within that validated callback scope and matching motion. Existing
Damage animation callbacks through Navi have no issuance scope and cannot deliver
another drop hit. Tokens are retained, not recycled, up to a4096 lifetime cap;
admission reserves room for three motions and then refuses safely. This is a
bounded prototype lifetime, not an unlimited production allocation strategy.
Reset revokes ownership but retains listener storage. State/manager destruction
is NOT wired: callback-domain teardown before token memory disposal remains open.

Unresolved generic interruption ownership:
Generic cleanup cancels only; it intentionally does not overwrite impulses supplied
by an incoming Flick/Geyser/etc. Direct fall->Walk through an arbitrary external
transit can retain falling velocity. Known reset and external attack paths have
explicit dispositions; unknown transitions are NOT production-safe by implication.
Do not enable natural Demon capture until root resolves those callsites. No generic
StateMachine, Creature physics or damage implementation was edited to hide this.

Compatibility: normal P1 InteractAttack is not P2 KokeDamage fidelity; actual capture
binding/owner actor is absent. Scene lifetime, allocator reuse, water, moving
platforms, slope/ledge behavior and arbitrary asynchronous event delivery remain
unverified. No declaration of full enemy completion follows from this prototype.

## Registered-state runtime evidence

Production Release build succeeds with PIKMIN_NATIVE_JAUDIO=ON. Initial default
legacy-audio link failed on existing Jac_NoteDemoSkipped references; no unrelated
audio source was changed. Build/fixture base snapshot12bd4d607a7d80ec4c1ac4841cb1936cbeeec6e2.
Private fixture03 SHA2566f19f0db71cbb5c5a1d6ec85d38c3f275084c2dd9effec7acde28bbf39c20606,
manifest output/demon-registered-fixture-03/provenance.json. Earlier fixture01/02
correctly rejected preview Starting23 admission; fixture03 explicitly arranges
Walk before injecting drop. Production admission was not weakened.

All sessions under output/demon-registered-sessions, each with executable,
provenance, runner, room/helper hashes and logs:

| Mode | Session | Observed result |
|---|---|---|
| positive | 793b9768986842f181c79c7b8329785e | Real bounce/JKoke END; owned resume and restart preserve Lay3;100->90; GetUp toWalk |
| interrupt | 0196e7c0edaa4001bdd3a84255368a9e | Knockdown->Walk;90updates no pending damage |
| reset | 47aa9200f9a842a1badfe20a1bf5b67b | Falling reset; owned actual/target/volatile zero and all3 contact pointers null immediately; no late damage |
| rejected | 0324fa604b3e42d18f233fd4f0c06975 | Explicit damaged-flag setup causes one accepted=0 attempt;100HP and recovery, no retry |
| external | f79ccb956c224a03bebc9767af6e8ac1 | Real external InteractAttack calls unowned-delivery resume; cancel thenWalk;99HP, no pending10HP hit |
| flick | 7ca1bb6bd27849098d0ad244b2275d7c | Real registered ordinary Flick8 init/animation/recovery toWalk;100HP |
| fatal | 30bf945d6f6a4fc0afeaaca723ab8378 | Real200damage;100->-100; native outer finishDamage enters Dead29, stays there for30updates |
| capacity | 0557fdec6083420989e6808667428b6f |4094 fall admissions/reset cycles then refusal; retained first listener rejected after reset and newer generation |

The capacity test's calls to an obsolete listener are synthetic rejection probes,
not fabricated successful animation completions. No direct HP writes. The rejected
mode deliberately sets the existing damaged flag, not natural enemy damage.
Fixture asserts current/target/volatile magnitudes<0.001 after real Navi updates
through Knockdown/Lay/GetUp, retaining a valid ground triangle. This measures the
end of both physics passes, NOT instrumentation proving which pass first bounced.
No water/platform/contact-quiescence-at-altitude or full scene lifetime claim.

Reproduce (MinGW bin on PATH):
cmake -S . -B build-demon -DPIKMIN_NATIVE_JAUDIO=ON
cmake --build build-demon -j6
py -3.12 ../p2-groink-prototype/scripts/build_pikmin2_fixture.py --build build-demon --source . --fixture tools/p2_demon_registered_runtime.cpp --output ../NEW-FIXTURE --expected-native-head CURRENT_COMMIT
py -3.12 tools/p2_demon_registered_run.py --root ../p2-groink-prototype --assets C:/Users/alari/pikmin-local/game/assets --room ../pikmin2-room105 --fixture ../NEW-FIXTURE --output ../demon-registered-sessions

Root review must resolve generic external-transition physics and scene teardown
before enabling the receiver beyond this isolated prototype. No shared native
checkout was changed; production hooks are a proposal demonstrated privately.

Final corrected source cb357a78072a004039df103764b691b417679699 adds fail-closed
unadmitted state36 init (returns Walk instead of stranding captain) and clears
captain on failed admission. Production rebuild succeeded. Frozen fixture04,
SHA2565165ff8de957379fbd658072b6cda04da3472b0fd0d9aef6cd77c1be86a8739b,
passes all prior eight modes plus direct-unadmitted-entry fallback. Complete
nine-session index: output/demon-registered-evidence04.json. Direct guard session
d3561edbcdda4590b9a786d2df2540ca; positive0b4e3547d7a648fcb117bea43a9df4a0;
capacity a1e65686fb2649bba4e8e0a9406ff209. All earlier evidence remains preserved.

Independent review confirmed the scoped eight-mode evidence and identified the
direct-entry guard now fixed/tested. Outstanding generic interruption physics and
scene-listener lifetime are explicit production blockers, not hidden by test PASS.

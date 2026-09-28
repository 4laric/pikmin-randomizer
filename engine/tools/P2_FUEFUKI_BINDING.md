# Fuefuki hook/binding seam (#245)

Successor of the FSM bridge slice (P2_FUEFUKI_FSM.md). Per the 2026-09-13
ownership update (issue #128 assignment; docs/PIKMIN2_WORKER_HANDOFF.md),
family owners retain their registration hooks, private builds and runtime
evidence: the six request specs from the FSM doc are now lane-owned and
implemented here, except item (f) — the FUEFUKIANIM motion bank — which
stays with the engine lane's converter/material work (#128); this seam is
its consumer only. Merge/build serialization rules still apply: isolated
candidates, no shared binary overwrite, local commits only.

Lane-owned files:

- `pc_port/pc_p2_fuefuki_binding.h` — engine-free host adapter contract
  plus binder driving P2FuefukiFsm (Groink/BombSarai adapter pattern:
  host or fixture mock supplies every engine fact via callbacks; fixed
  30 Hz source ticks, no wall clock).
- `tools/p2_fuefuki_binding_test.cpp` — mock-host fixtures.
- `tools/p2_fuefuki_native_compile_check.cpp` — isolated compile candidate
  against the frozen host include tree (pc_port/pc_p2_enemy.h seam).
- Root repo `experimental/pikmin2_fuefuki_install.py` — opt-in install
  profile glue per #186 (hash-bound canonical profile, conflict refusal
  before mutation, no assets).

## Seam contract (implements FSM-doc specs a–e)

- (a) Squad scan: `P2FuefukiEnumerateFn` is a read-only enumeration of
  Pikmin within the cast-tick ring (XZ, no height gate, source
  sqrDistanceXZ) with candidate classification (living, callable,
  mouth-stuck, already-ACT_Teki). The binder queries with this tick's
  post-growth radius (source updateWhisle grows before scanning) and only
  while in Whisle. Admission itself stays in the interference policy.
- (b) Follow binding: `P2FuefukiFollowStartFn` fires exactly once per
  accepted claim; post-admission rejection is a host contract error
  counted in followErrors with the policy remaining authoritative.
  `P2FuefukiPingCollectFn` returns per-tick follower pings (source
  ActTeki timer-reset stimulus). `P2FuefukiFollowEndFn` fires once per
  release: SUSPEND (flying/bittered Success exit) or PANIC (owner death).
  One controller per Pikmin is enforced by the ownership table; a claim
  never performs a captain-ownership write. Multiple beetles in one area
  must share one table (binder-injectable) — fixture-verified.
- (c) Reclaim interception: `onCaptainWhistle` accepts only
  Panic-released followers, exactly once, then performs the lane's single
  ownership write via `P2FuefukiOwnershipWriteFn` (source InteractFue
  receiver: clear action, piki->mNavi = whistling captain, LookAt).
  `onCaptainSwitch` and `onPartyCombine` are explicit non-routes: always
  false, never write.
- (d) Health/kill: health enters per tick; the FSM commits ownerDied
  BEFORE any PANIC `followEnd` callback runs (fixture asserts
  holds()==false inside the callback). At dead-anim END the binder
  delivers `P2FuefukiKillFn` with the Carry-carcass flag.
- (e) Probes: `P2FuefukiProbeFn` supplies position, private-radius
  intruder, arrival (wall triangle or XZ dist^2 < 625) and water facts as
  plain inputs; invalid probes, failed enumerations and failed ping
  collections each fail the whole tick without mutation.
- (f) Motion bank: NOT in this seam. The 10 FUEFUKIANIM slots, key-event
  wiring and material fidelity remain #128 converter/material work; the
  binder consumes only host-supplied animation facts (animPlaying,
  keyEvent, motionFinished, turnComplete).

## Opt-in install profile (#186)

`python experimental/pikmin2_fuefuki_install.py --run-dir <private run>`
installs `p2-fuefuki-profile.txt` (canonical LF tokens: enemy 41, 9
states, 10 anims, 30 Hz cadence, seam bindings, ownership/reclaim/release
rules, motion_bank:#128 external dependency) plus a hash receipt into an
existing private run directory. Verified locally: fresh install, exact
idempotent re-install (`already-installed`), and refusal before mutation
on a tampered profile (exit 1). No arena staging, no native actor
registration, no shared/native edits.

## Build and fixture evidence (native, MinGW64 GCC)

```
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_binding_test.cpp -o ../fuefuki-binding-test.exe
../fuefuki-binding-test.exe                  # p2_fuefuki_binding_test PASS
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_interference_policy_test.cpp -o ../fuefuki-interference-policy-test.exe
../fuefuki-interference-policy-test.exe      # PASS (re-run)
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_fsm_test.cpp -o ../fuefuki-fsm-test.exe
../fuefuki-fsm-test.exe                      # PASS (re-run)
g++ -std=c++17 -Wall -Wextra -Werror -Ipc_port tools/p2_fuefuki_suspend_fallback_test.cpp -o ../fuefuki-suspend-fallback-test.exe
../fuefuki-suspend-fallback-test.exe         # PASS (this slice)
```

Private native compile against the frozen host (isolated candidate, no
shared binary/export overwrite; object written outside any build tree):

```
mkdir -p ../output/fuefuki-binding
g++ -std=c++17 -Wall -Wextra -Werror -Iinclude -Ipc_port \
    -c tools/p2_fuefuki_native_compile_check.cpp \
    -o ../output/fuefuki-binding/p2_fuefuki_native_compile_check.o
```

Result: compiles warning-clean against the frozen host include tree and
the pc_port registration seam (pc_p2_enemy.h), producing only the
isolated object. No link, no shared binary touched.

Binding fixture coverage: required-callback bind validation and rebind
refusal; full scan -> claim -> follow-start -> ping -> cast-end ->
suspend -> re-claim cycle with zero ownership writes; panic-release
ordering (table release committed before the followEnd callback);
exactly-once captain-whistle reclaim with the single ownership write;
captain switch / party combine as non-routes; kill delivery with the
Carry carcass flag; probe/NaN-probe/enumerate/ping/negative-delta tick
rejections without mutation; two binders on a shared ownership table
holding single-controller exclusivity for the same Pikmin.

## Remaining runtime-acceptance gaps

Update (#245, `P2_FUEFUKI_RUNTIME_EVIDENCE.md`): the first and fourth
bullets are now covered by a real-GL runtime run — real `pikiMgr` squad
scan, real positions/alive/mode reads, real non-routing on live objects,
and the captain-whistle reclaim through the REAL `Navi::callPikis`
(LookAt transit, then real `FormationMode` join 20 frames later). The
gaps below remain open.

- Actual follow **action** (locomotion): the ActTeki decision policy and the
  live host drive are now implemented — see `P2_FUEFUKI_FOLLOW.md` (optional
  `followerSample`/`followDrive` callbacks, `pc_p2_fuefuki_follow.h`). P1 still
  has no follow-teki action, so `pc_p2_hardlanes.cpp` realizes motion through a
  labeled `mVolatileVelocity` approximation until provider lane 12 supplies the
  real action; a real-GL run of the approximation is still open.
  traceMove/map probes beyond the flat-room distance checks are also still
  mock-side.
- Arena staging under #186 with the install profile, physical placement
  and rendered whistle ring requires the #128 motion bank and converted
  parms; fixture parms are shortened.
- Suspend brain-fallback was resolved to **Free, not Formation** (#245
  suspend-fallback slice; ActTeki::getNextAIType()==ACT_Free,
  PikiAI.h:1254; aiAction.cpp:108-110; mNavi cleared by ActFree::init,
  aiFree.cpp:33). P2FuefukiBindOut::suspendFallback now carries the source
  decision through the seam; the world-side situation-scan re-task gate
  (aiAction.cpp:92-95) stays host knowledge. Claim persistence across
  day/cave transitions remains open; P1 has no verified panic state —
  released followers stay in PIKISTATE_Normal (see evidence doc).

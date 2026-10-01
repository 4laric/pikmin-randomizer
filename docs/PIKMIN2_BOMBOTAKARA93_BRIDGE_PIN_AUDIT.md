# BombOtakara 93 dynamic-bridge pin audit (#791)

Read-only pin-discovery/ownership for shard enemies-6 (issue #592, parent #586).
Implementation owner: Codex through shared account `4laric`. Unblocks the
stranded consumer `enemy-bombotakara93-payload` (#573). All six runtime gates are
UNTESTED; this audit is contract evidence, not implementation or gameplay
acceptance. No runtime, build, manifest write or ADMIT.

## Traced binding chain (file:line)

The source-93 BombOtakara carrier is refused by the generated-placement dynamic
bridge (consumer log `P2_MUSE_BOMBOTAKARA573_BIND_REFUSED
reason=dynamic_bridge_59_62_only`):

| Step | Anchor | Effect |
|---|---|---|
| Bridge dispatch | `pc_port/pc_p2_generated_placement.cpp:113` `case 59/60/61/62: pc_p2_otakara_bind_dynamic(...)` | Only 59-62 route; source 93 has no case, falls to `default: return false` (line 124). |
| Bind entry | `pc_port/pc_p2_otakara.cpp:551` `pc_p2_otakara_bind_dynamic` | Delegates to `speciesFromSource`. |
| Source map | `pc_port/pc_p2_otakara.cpp:427-435` `speciesFromSource` | Returns a species only for `case 59/60/61/62`; `default: return -1`. `-1` makes the bind return `false`, so 93 is never bound. |

`speciesFromName` (`pc_port/pc_p2_otakara.cpp:418-425`) *does* map `BombOtakara`
to `p2dweevil::BombId`, but that path is only used by the setup file scan
(`pc_p2_otakara_setup`), not the dynamic bridge. `pc_port/pc_p2_otakara.h:22-24`
states verbatim that BombOtakara (93) is **deliberately NOT bound** by this
module: it consumes the lane-20 shared Bomb blast contract and is covered by
`pc_p2_bombotakara` plus the #616 path.
## Integration status (verbatim, verified this turn)

`integrated` = file is present in the maintained `native/` checkout.

| File | maintained `native/` | owner `autofill-native-573` | CMake membership |
|---|---|---|---|
| `pc_port/pc_p2_bomb_mgr_birth.cpp` | INTEGRATED | present | `native/CMakeLists.txt:202` |
| `pc_port/pc_p2_bomb_mgr_birth.h` | INTEGRATED | present | header |
| `pc_port/pc_p2_generated_placement.cpp` | ABSENT | present | `autofill-native-573/CMakeLists.txt:174` |
| `pc_port/pc_p2_generated_placement.h` | ABSENT | present | header |
| `pc_port/pc_p2_otakara.cpp` | ABSENT | present | `autofill-native-573/CMakeLists.txt:242` |
| `pc_port/pc_p2_otakara.h` | ABSENT | present | header |

The #616 BombMgr module (which births `P2_BOMB_MGR_SOURCE_ID == 36`, the Bomb
payload) is integrated in the maintained wave; the generated-placement bridge
and the lane-22 otakara module are not.

## Decision: correct producer

**Bind source 93 through the #616 `pc_p2_bomb_mgr_birth` path** (decision
`bind_93_via_616_bomb_mgr_birth`). Owner: lane `provider-bomb-mgr-birth`
(#616, done). Provider shard `actor-birth-projectiles` for the BombMgr/hook;
`placement-catalog` owns the generated-placement bridge.

Rejected alternative `extend_otakara_bridge_for_93`: the otakara module excludes
93 by design (`pc_p2_otakara.h:22-24`) because BombOtakara consumes the shared
Bomb blast contract; re-admitting 93 there would duplicate the #616 payload
lifecycle and the #577 pool.

## Exact missing input

1. **#186 shared-hook landing**: the engine `BTeki::update` / `doKill` callsites
   that invoke `pc_p2_bomb_mgr_birth_update` (`pc_p2_bomb_mgr_birth.cpp:373`)
   and `pc_p2_bomb_mgr_birth_forget` (`pc_p2_bomb_mgr_birth.cpp:405`) for the
   registered carrier — the Section 2 host binding exists but is not driven by
   the shared engine hook.
2. **Source-93 carrier admission**: register the BombOtakara carrier generator
   through the BombMgr carrier seam (`pc_p2_bomb_mgr_birth_carrier`,
   `pc_p2_bomb_mgr_birth.cpp:355`; sidecar `p2-bomb-mgr-birth.txt`), not the
   otakara dynamic bridge.
3. If the consumer still binds through `pc_p2_generated_placement_bind`
   (`pc_p2_generated_placement.cpp:98`), add a `case 93:` routing to the BombMgr
   path; today 93 falls to `default: return false` (line 124).

## First executable slice (engine_change)

- Add `case 93:` to `pc_port/pc_p2_generated_placement.cpp:98`
  `pc_p2_generated_placement_bind` routing to the BombMgr carrier seam.
- Reserve owned files: `pc_port/pc_p2_generated_placement.cpp`,
  `pc_port/pc_p2_generated_placement.h`.
- Build membership: `native/CMakeLists.txt` (a new file to the bridge or a new
  membership entry; the BombMgr entries at lines 201-202 already exist).
- Verification scope only (do not re-own): `pc_port/pc_p2_bomb_mgr_birth.cpp`,
  `pc_port/pc_p2_bomb_mgr_birth.h`.
- Consumer: `enemy-bombotakara93-payload` (#573) gates 1/3.

## Destination pins (read-only audit inputs)

- Wave root `fdd558123223f94d706b9a00973037553e864756`; wave native
  `a95040b66a0ffc9cdbfc649502569a29e66949a7`.
- Consumer `#573`: root `2c3d918916034de34c71aa65cd33d9bef4e97320`, native
  `7bbeb3bacdf6b6712e7d92e5b503d89653229280`.
- Provider `#616`: native `6d4cbc4afc112c02b7166ef30d8a1f684c7f3ba5`.

## #186 decision request

Review, for the shared hook, the landing of the `BTeki::update` / `doKill`
callsites that drive `pc_p2_bomb_mgr_birth_update` / `pc_p2_bomb_mgr_birth_forget`
for the source-93 BombOtakara carrier (proposed files
`pc_port/pc_p2_bomb_mgr_birth.cpp`, `pc_port/pc_p2_bomb_mgr_birth.h`) —
approve, rebase-and-approve, or reject through the canonical shared-review
channel.

## Validation

- `tests/test_pikmin2_bombotakara93_bridge_pin_audit.py`: 19 passed (source-map
  parse/refusal, drift and malformed/missing-input rejection, root presence,
  packet schema/gate/decision discipline, end-to-end run).
- Real run over maintained `native/` + owner `autofill-native-573`: admitted
  `[59, 60, 61, 62]`, refused `93`, all gates UNTESTED (`out/audit-run/`).
- No runtime, no playability claim, no ADMIT. All six gates UNTESTED.

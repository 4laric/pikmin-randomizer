# Muse ground lane handoff — Sokkuri79 ordinary-delivery bridge (l55, #495)

Parent #165; wave #491; integration #437/#186.
Implementation owner: Codex through shared account `4laric`; executing
contributor: Muse Spark 1.3 via OpenCode (`opencode/muse-spark-1.3-contributor-free`),
lane muse-ground (l55). Attempt `8d1876545742497fbd8c305f2c58ef35`, generation 1.

## Slice delivered

**Source IDs owned:** Sokkuri 79 (implemented this slice), ElecBug 28 (deferred;
untouched until the first complete Sokkuri slice, per brief ordering).

**Concrete slice:** the missing family-side ordinary-delivery bridge for
Sokkuri79. Before this slice no family module called the lane-06 ordinary
receipt path: `pc_randomizer_p2_bind_source` had zero family callers, so a
naturally killed/hauled Sokkuri corpse reaching `GoalItem::suckMe` could only
ever credit the P1-proxy Chappy check, never `onion:p2:79`. The slice binds
source 79 at Sokkuri setup (generator uid = `Generator::_70`), clears it on
`pc_p2_sokkuri_forget` (idempotent; the central `pc_p2_forget_teki` seam also
clears it), and emits `P2_SOKKURI_DELIVERY_BIND` for the observer. No shared
file is touched; no Transport/kill/credit is injected; no health, AI mode, or
extinction semantics change.

Also new: `experimental/pikmin2_muse_ground.py` (honest delivery validator:
transport PASS needs BOTH `onion:p2:79 new=1` AND natural-carry markers; a
receipt alone is interface-only), `tests/test_pikmin2_muse_ground.py` (10
unit tests, all pass), and `native/tools/p2_muse_ground_fixture.cpp` (natural
death -> corpse -> carry-observation replacement-main source; not yet built or
run — see remaining work).

ElecBug28: no module change this slice (scope ordering). Its gate rows below
preserve lane-14 evidence without relabelling.

## Ordered commits

Root base `72a2c450d7b9040545de4a440c2c32e2173ea6fa`; native base
`7b9ecaa668fd55332073446cdbdaf6424b209ea7`. Both branches clean at handoff.

| Branch | Commit | Subject |
|---|---|---|
| native `codex/muse-l55-ground-native` | `ecc80b72` | lane55: bind Sokkuri79 ordinary delivery source + muse-ground fixture source (#495) |
| root `codex/muse-l55-ground` | `50f6e89a` | lane55: Sokkuri79 delivery observer/validator + unit tests (#495) |
| root `codex/muse-l55-ground` | (this handoff) | lane55: Sokkuri79 delivery-bridge handoff (#495) |

Dirty state: none (both clean).

## Interfaces / hooks touched and why

Family-owned native change only, in `pc_port/pc_p2_sokkuri.cpp`:

- `#include "pc_randomizer.h"` (the header already documents "Called by the
  family bind path (or a fixture)").
- `pc_p2_sokkuri_setup()`: after the module bind, calls
  `pc_randomizer_p2_bind_source(view, 79, generator)` and prints
  `P2_SOKKURI_DELIVERY_BIND generator=%u source_id=79`. Rejected ids are
  logged by the callee, never fatal; 79 is in the bindable roster
  (`pc_randomizer_p2_roster.h`). Single-use: consumed by
  `pc_randomizer_p2_corpse_delivered` on delivery.
- `pc_p2_sokkuri_forget()`: also calls `pc_randomizer_p2_forget_source`
  (idempotent) so a recycled actor address can never inherit source 79.

No `teki.h`, `tekiinteraction.cpp`, `tekimgr.cpp`, `goalItem.cpp`, `navi.cpp`,
`pc_p2_preview.cpp`, CMake, roster, admission, or seed-default change. Shared
cargo changes, if needed after the first natural-carry observation, go as a
focused request to #491 — none is requested here.

## Build evidence

Leased heavy-build runner
(`output/muse-wave/control/leased_run.py --configure`), private build dir
`C:\Users\alari\pikmin-randomizer\output\msw\native-l55-build`:

- Log: `C:\Users\alari\pikmin-randomizer\output\muse-wave\l55\build-1789515320859273900.log`
  (SHA-256 `5f2ca00a15e92cd37c3b4df016bfc44c33247cd97b6e7b69cea242e941481684`).
- Native base `7b9ecaa668fd55332073446cdbdaf6424b209ea7`, dirty at build
  `M pc_port/pc_p2_sokkuri.cpp` + `?? tools/p2_muse_ground_fixture.cpp` —
  exactly the committed content (`ecc80b72`); worktree clean at handoff.
- `nectar.exe` SHA-256
  `d10ba07bbf2bff00cc91209c29e31a9f4fad673bf22b49b9cee0b535b70302cc`;
  `ninja -n` → `ninja: no work to do.` Config: Ninja + MinGW g++ Release,
  `PIKMIN_NATIVE_JAUDIO=ON`, `PIKMIN_NATIVE_OPTIMIZE=OFF`.
- First `leased_run --configure` attempt failed on a missing Ninja binary
  (`CMAKE_MAKE_PROGRAM` unset); retried with the Python Scripts Ninja on PATH
  through the same leased wrapper (no direct second build). Evidence log kept.

## Fixture adoption evidence

No runtime acceptance run this slice: no fresh arena was generated, no
executable was launched, no window/squad observation is claimed. The
replacement-main source exists (`native/tools/p2_muse_ground_fixture.cpp`)
but has no `built` provenance yet. The next slice regenerates a NEW private
arena with the current overlay/starting squad, builds the fixture through the
leased wrapper, and verifies 960x540 centred startup, live Pikmin, and no
immediate extinction before any carry observation. Honest status: UNTESTED,
not adopted.

## Tests

- `py -3.12 -m pytest tests/test_pikmin2_muse_ground.py -q` → **10 passed**.
  Log: `C:\Users\alari\pikmin-randomizer\output\muse-wave\l55\pytest-muse-ground.log`
  (SHA-256 `1f9fb0ce1e1c43148f35a905389b3e5fad27d0995fe930449aced89d879ff400`).
- Covers: natural death chain stays untransported without receipt;
  receipt-without-carry stays interface-only; receipt+carry passes; injected
  markers never pass; large prior_health fails; duplicate `new=1` breaks
  exactly-once while `new=0` duplicate keeps it; missing delivery bind fails
  identity.

## Six-gate evidence tables (per identity)

Gates 1–4 for both identities preserve the latest lane-14 natural evidence
(read-only citations); gate 5/6 stay UNTESTED per the lane-14 honesty
corrections (generator `init` re-bind / fixture forget is not full natural
scene re-entry; cargo-free arena had no lane-06 receipt). No gate is
downgraded or upgraded without findings in this slice.

### Concrete source ID

- Source ID: 79 `Sokkuri`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md natural-run2 native.log:782 | natural |
| 2. Autonomous movement and animation | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md natural-run2 native.log:826 | natural |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md natural-run2 native.log:801 | natural |
| 4. Death and corpse | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md natural-run2 native.log:904 | natural |
| 5. Actual transport and reward | UNTESTED | no natural carry plus onion:p2:79 receipt runtime yet; validator at experimental/pikmin2_muse_ground.py refuses receipt-only PASS | natural |
| 6. Cleanup and re-entry | UNTESTED | injected (cleanup natural; re-entry would be forced re-bind, not full scene re-entry) | injected |

### Concrete source ID

- Source ID: 28 `ElecBug`.

| Gate | Result | Evidence | Injected vs natural |
|---|---|---|---|
| 1. Exact identity and spawn | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md elecbug-run4a native.log:807 | natural |
| 2. Autonomous movement and animation | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md elecbug-run4a native.log:820 | natural |
| 3. Attacks and receivers | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md elecbug-run4a native.log:867 | natural |
| 4. Death and corpse | PASS (natural) | docs/PIKMIN2_LANE14_DEEPSEEK_HANDOFF.md elecbug-run4a native.log:1082 | natural |
| 5. Actual transport and reward | UNTESTED | deferred until Sokkuri slice completes; no lane-06 receipt in cargo-free arena | natural |
| 6. Cleanup and re-entry | UNTESTED | injected (cleanup natural; re-entry forced re-bind) | injected |

Checker: `py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_GROUND_HANDOFF.md`
from the lane root → exit 0, no refused PASS rows (verified before handoff).

## Assumptions

- Incremental `P2_SOKKURI_DAMAGE` + small-`prior_health` death = natural combat
  drain (lane-14 signature, unchanged).
- The lane-06 ordinary endpoint (`GoalItem::suckMe` →
  `pc_randomizer_p2_corpse_delivered` → `onion:p2:79`, single-use binding,
  no P1 double-credit) is taken as the delivery mechanism; this slice wires
  the family side only and does not re-prove the provider.
- The Skitter Leaf is harmless; natural lethal death needs the free squad to
  fully drain 120 HP (proven in lane-14 natural-run2, not re-run here).

## Remaining blockers / next step

1. Natural carry + exactly-once receipt runtime (owner: this lane, next
   slice): generate a NEW private arena with the current overlay/starting
   squad, build `native/tools/p2_muse_ground_fixture.cpp` through the leased
   wrapper, observe free-mode grasp/haul of the Sokkuri corpse with no
   `suckMe` fallback, and capture `P2_ORDINARY_P2_RECEIPT ... onion:p2:79 ...
   new=1` plus a duplicate `new=0` across restart. No dependency blocks this;
   no new shared hook is expected unless the carry observation reveals a real
   receiver/route defect (then a focused request to #491).
2. Full natural scene re-entry beyond generator recreation (lifetime lane
   concern, #397/07): not claimed here; gate 6 stays UNTESTED honestly.
3. ElecBug28 delivery/re-entry only after the Sokkuri slice completes (brief
   ordering); its module is untouched.

## Exact reproduction

```powershell
$env:PATH='C:\msys64\mingw64\bin;'+$env:PATH
py -3.12 -m pytest tests/test_pikmin2_muse_ground.py -q
py -3.12 scripts/check_p2_handoff_gates.py docs/PIKMIN2_MUSE_GROUND_HANDOFF.md
```

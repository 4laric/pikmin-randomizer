# Mid-day save codec foundation (#68)

Implementation owner: Codex through shared account 4laric. This slice adds native
standalone codec/storage modules. It adds no gameplay menu, capture hook, restore
hook or production build target. Save and quit and autosaves remain unimplemented.

## Explicit logical wire contract

`pc_port/pc_midday_codec.{h,cpp}` defines format 1: `PCMIDDAY`, little-endian
version u32, four 32-byte SHA-256 identity values (seed, session, content, schema),
generation/frame/day-end generation u64, actor/section counts u32, records, and a
whole-file SHA-256. Each actor contains a nonzero logical incarnation u64,
family/version u32, length-delimited adapter bytes and SHA-256, followed by bounded
u64 references. Each section contains family/version, length-delimited adapter
bytes and SHA-256. Counts and the complete file have fixed upper bounds (65536
actors, 1024 global sections, 16 MiB). IDs and section keys encode in sorted order;
reference list order is significant (attachment slot or formation order).

Each identity value must be nonzero. Each adapter version must be explicitly
supported. Required global sections, duplicate IDs/sections, dangling references,
counts, hashes, versions and identities validate before decoded output is exposed.
Capture supplies an independent census of every observed actor ID. `encode`
requires exact census coverage, refusing dropped actors. `decode` has no live
world yet and instead validates its entire decoded census and graph; it does not
compare against the caller's current actor census. Every actor is opaque adapter
data here: family adapters must validate their scalar representation, states,
timers and typed reference roles before restore. Codec success cannot prove that
an enemy FSM or Pikmin job is faithfully represented.

No pointers, compiler layouts, memory pages, platform handles, GL resources or
raw libc RNG state are allowed in adapter data. Float-bearing adapters must
specify IEEE-754 binary32 and reject nonfinite values and incompatible platforms;
the foundation itself contains integer framing and opaque adapter payloads.
Logical IDs must be assigned by an epoch-scoped monotonic incarnation allocator,
not a generator index alone, pointer, manager slot or recycled birth index. The
allocator counter and generator/death/birth tombstones belong in required global
sections. Adapter capability IDs need one reviewed allocation registry before
production use; test families 1 and 10 are synthetic, not gameplay capabilities.

## Publication and explicit recovery

`pc_port/pc_midday_store.{h,cpp}` requires a trusted, private, local save directory.
It acquires `WRITER.lock` through exclusive directory creation, then creates an
immutable `generation-N.checkpoint` exclusively. Checked write/flush/file sync and
close precede reopening and verifying the entire generation. It creates a unique
exclusive `commit-N.pending`, syncs it and atomically replaces `CURRENT` last.
The commit record contains current and previous-good generation IDs and SHA-256.
No saved generation, damaged file, orphan or foreign pending file is overwritten.
There is currently no retention pruning; disk management is future work.

Windows uses wide file paths, `_commit` and `MoveFileExW` with `WRITE_THROUGH`.
POSIX uses `fsync` plus atomic rename and directory sync. Process interruption
tests establish complete old-or-new visibility on the tested local Windows
filesystem. Power failure guarantees, network filesystems and Linux execution
still need platform acceptance; Windows directory durability is not claimed from
`FlushFileBuffers` on directories. A failed sync after publication reports failure
and uncertain outcome; callers inspect the committed generation and must not quit
or tell peers that commit succeeded merely because the file exists.

An interrupted process intentionally leaves its ownership lock. No timeout or
shared app PID can authorize deleting it. A future coordinator must prove the
specific writer stopped and offer explicit recovery before retrying. Reads can
inspect a committed immutable generation while a writer lock exists. Missing
`CURRENT` means no committed save, even if generations or pending files exist.

### Explicit recovery successor

Publication now writes a checksummed `WRITER.lock/owner` containing platform,
local host/boot-and-PID-namespace identity, PID and process creation identity.
Windows queries the creation FILETIME and process termination state; Linux uses
the boot ID/PID namespace and `/proc/PID/stat` start ticks. Missing/incomplete,
foreign, live or uninspectable owners refuse automatic recovery. Legacy empty
locks remain unknown: the code does not invent stopped-writer proof for them.
An OS process-lifetime gate (`WRITER.guard`, Windows share-denied handle/Linux
nonblocking flock) serializes all new writers and recovery transactions and is
automatically released when a process exits. A gate file on disk is not a lease.

`inspectRecovery` returns a proposed exact selection and hashes of the durable
owner, current commit bytes and selected checkpoint, plus inventory high-water and
day-end fence. It mutates no save state; the gate file may be created. `recover`
requires that explicit plan, takes the gate and rechecks every field before
retiring a proven stopped owner's lock to `recovered-lock-HASH`. It acquires its
own durable recovery owner, archives old CURRENT bytes to a hash-named evidence
file, then atomically publishes the selected validated generation last. Unknown
or changed ownership/metadata/selection cannot be waived by a timeout.

Commit format `PCCOMM02` adds a monotonic generation high-water u64; original
`PCCOMMIT` records remain readable. Recovery may select an older generation but
records the greatest observed generation filename/committed watermark, preventing
later save IDs from reusing a retained corrupt or orphan incarnation. Existing
evidence and exact matching interrupted pending metadata can be reused without
overwriting; changed evidence refuses. Recovery interruption leaves its own
durable owner identity and a complete old or new CURRENT; a new exact plan can
retry after proving that owner stopped.

A valid commit identifies the selectable current/previous checkpoint. A damaged
or missing commit cannot establish committed provenance, so selecting any
validated snapshot additionally requires `explicitUncommittedSelection=true`.
This is a visible forensic recovery acknowledgement, not a guessed fallback or
proof that an online host/peer agreed that snapshot. Production online recovery
must separately validate the negotiated durable commit acknowledgement. This API
must not bypass that future coordinator. Day-end-superseded selections refuse.
POSIX directory creation now syncs each new directory and its parent; Linux and
power-loss behavior still require platform execution acceptance.

The successor Windows suite passes136 standalone controls: the original codec
coverage, legacy commit-read/upgrade, durable stopped/live/foreign/unknown owner
refusal, changed-plan rejection, new save after selected recovery, and eight real
fresh-process interruptions (four original publication and four recovery
boundaries). The live-writer case pauses a real child at generation durability,
proves both its held OS gate and its independently queried live owner refuse
recovery, then releases it and waits for termination. POSIX child supervision now
uses bounded nonblocking waits; it has not been executed on Linux yet.

`load` normally returns `Current`. Damage in the current generation may return
`RecoveryAvailable`, leaving caller output unchanged. Only an explicit
`acceptPrevious` request returns `Recovered`; files remain untouched. A corrupt
commit record cannot identify a trustworthy previous generation, so returns
`Invalid` and preserves evidence for manual recovery. Binding/version/capability
failure is visible and never means a new game or silently loading init.gen.
The caller supplies the latest authoritative day-end generation watermark:
superseded current and previous generations are excluded. Mid-day and day-end
must eventually share a committed epoch/generation counter; the foundation does
not change existing day-end card formats or assign them new generations.

## Native integration plan and remaining acceptance

1. At the authoritative tick after world update/outbox drain and before the next
   tick, a coordinator establishes a read-only capture fence. Online Start/Onion
   menu ownership is not this fence. Host and peer must agree frame, ledger epoch,
   capabilities and digest. Captains must be initialized and alive under the
   current fixture guard. Capture never calls mutating day-end serializers.
2. Inventory every manager, dynamic actor, pending birth, corpse, projectile,
   attachment and global section. Adapters explicitly refuse unsupported FSMs,
   active conversions, transient transitions or missing identity; no actor is
   omitted and no P2 pool is silently narrowed. Capture scalar data and logical
   references into immutable bytes, not a background traversal of live pointers.
3. Global sections must include same-day clock accumulators, exact area/floor and
   generated descriptor/layout, deterministic gameplay RNG profile and stream
   state, incarnation counters/tombstones, typed stock/cargo/structures, AP
   consumed/pending benefit and durable receipt/outbox state, and input policy.
   Offline libc `rand` has no portable persisted state: implement an explicit
   persistable gameplay RNG mode with legacy neutrality tests before claiming
   supported offline saves. Existing sim/cosmetic RNG accessors are audit seams.
4. Audio requires logical allocation/free-event availability, type/active state,
   context actor bindings and desired carry loops. Recreate device voices and
   platform handles after references resolve. Prove device-only reconciliation
   changes no simulation state; audio is not all disposable presentation.
5. Validate bytes and all adapter data before mutating any world. Create verified
   scene/resources, allocate actors in stable ID order with normal birth rewards,
   RNG draws and child spawns suppressed, then apply scalars. A second pass
   resolves owners, attachment slots, jobs and cargo references with type checks.
   Rebuild routes/collision/UI/audio, restore RNG after initialization draws, check
   population/economy/ledger invariants and publish the world only on success.
   Establish pause and zero input edges before the first world update. A restore
   error keeps the saved bytes and must not leave a partially resumed live world.
6. Quit only after durable commit and the negotiated peer result. AP reconnect
   merges external inventory monotonically while preserving logical grant results
   and consumed counters; received reward receipts must not be blindly delayed
   as I/O. A snapshot cannot retract sent checks or replay delivered cargo.

First gameplay slice remains both captains, typed field/stored Pikmin and sprouts,
supported enemies, clock/RNG, partial structures and AP ledger on a supported
surface profile. Then active carry/jobs/combat and same-floor cave actors, online
agreed save/rejoin and finally measured autosave. Each requires fresh private,
short scripted gameplay save/restart acceptance with overlay20 Reds and centered
960x540 startup, rather than treating these standalone controls as gameplay proof.

## Standalone controls

Compile with the maintained MinGW compiler into an exclusively owned ignored
output directory (no production game or shared CMake mutation):

```powershell
C:/msys64/mingw64/bin/g++.exe -std=c++17 -O2 -Wall -Wextra -Werror `
  -I output/native-midday-save-68/pc_port `
  output/native-midday-save-68/pc_port/pc_midday_codec.cpp `
  output/native-midday-save-68/pc_port/pc_midday_store.cpp `
  output/native-midday-save-68/tools/pc_midday_codec_test.cpp `
  -o output/midday-save-68/codec-controls-build01/codec-test.exe
```

Run with one new private output directory; existing output is refused. Controls
cover deterministic encoding, malformed size/count/checksum/version/identity,
inventory/capability/reference refusal, stale day-end precedence, explicit
previous-good recovery, same-generation/orphan/foreign-lock refusal, each
durability boundary and four real fresh-process interruptions. Windows also
locks the real commit file to deny replacement and verifies old save preservation.
No actual native world save/restart, full production build or Linux test is claimed.

## Read-only world integration audit of native281

The next capture/restore design was checked against clean integration native
`281f916a220552904d1ac070c6cbe6004100f2e9` and root
`dba9bc6ba1f9a8a11763916fcdd57a448aca2bb5`; codec work remains on its independent
efe4-based branch. These are read-only source observations, not adapters or hooks.

- `src/sysDolphin/system.cpp:391` delegates online turns to the session; ordinary
  `app->idle()` is at450, followed by input log/state hash finalization. Ordinary
  capture needs a new post-update seam and a save-specific world/input fence.
  `pc_port/netplay/pc_netplay_session.cpp:5549` runs the online tick, then hashes
  state; its confirmed-frame outbox flush at5574-5575 precedes advance bookkeeping.
  Capture must follow confirmed flush and precede the next Advance. A future
  negotiated save fence is additional to existing menus and day-end save barriers.
- `include/Navi.h` exposes the two-captain spawn index via `getNaviIndex`, state
  machine, control-camera basis and health inherited from Creature. `pc_coop.h`
  explicitly describes player captain choices and co-op/VS run flags as unsaved
  session state. Capture must include both logical captain identities, role/input
  ownership and formational basis; appearance choice alone is insufficient.
- `include/Piki.h:315-354` includes leader, formation priority, active action,
  Navi owner, legacy color/maturity/current state and independent `mP2Purple`,
  `mP2White`, `mP2Bulbmin` flags. Typed identity cannot be reconstructed from the
  three legacy color slots. Census includes pending sprouts/births and stock;
  leader/Navi/action/cargo pointers become typed logical references. Purple flight
  and White ingestion attribution need separately coordinated family exports;
  `pc_p2_white_poison.h` currently exposes prepare/finish/forget/reset, not a save
  state export. Resetting that state would lose simulation-visible attribution.
- `include/WorldClock.h` has current day/hour/minute, real-seconds-into-hour,
  previous/current time, delta and rate fields. A clock adapter must preserve the
  accumulated phase/rate, then establish zero first-update delta without firing
  sunrise/sunset twice. The RNG header confirms non-deterministic draws still
  call libc rand: getter/setter availability is not offline persistence support.
- `audio_stubs.cpp:211-228` holds16 NativeEvents and an event clock;
  `Jac_CheckFreeEvents` at526 returns the gameplay-visible free count.
  `soundMgr.cpp:775-777` compares free-event availability around destroy. Logical
  event allocation/type/action/context belongs in a required global adapter;
  old voices and wall-clock `startedMs` are recreated. Desired carry loops must
  reconcile after actor references with no logical allocation side effects.
- `pc_randomizer.h:29` exposes the sim-visible randomizer payload but not the full
  live world; its outbox documentation at39-43 includes checks, benefits, Emperor,
  DeathLink and P2 delivery ledger. World restore needs consumed/pending/outbox and
  logical grant results paired to generation; neither resume_snapshot nor the
  existing day-end checkpoint API is a full-world Save-and-quit implementation.

Next concrete capture contract: independent manager census first; assign stable
birth incarnations to every captain/Pikmin/sprout/enemy/boss/cargo/structure/hazard;
request each exact typed adapter's refusal/validated output; require clock, scene,
identity/tombstone, stock/economy, RNG, audio and AP sections. Allocate all actors
before rebinding any target/owner, with birth/receipt side effects suppressed;
validate graph roles/population/economy, restore RNG after initialization and
establish pause/zero input before publication. Unsupported actor or live action
blocks Save-and-quit visibly. Shared manager birth/kill hooks, tick/menu/CMake,
family state exports and AP/save generation adoption require their real owners'
coordination before editing; no current shared source is changed by this audit.

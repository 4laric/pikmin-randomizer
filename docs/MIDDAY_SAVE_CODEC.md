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

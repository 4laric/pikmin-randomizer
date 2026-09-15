#pragma once
// Engine-free bridge to the shared pc_p2_receipt.h provider. This header keeps
// <windows.h> (pulled in by pc_p2_receipt.h for its atomic rename) out of engine
// translation units. Multiple durable ledgers at distinct paths coexist: open()
// returns an opaque handle per path, and grant()/close() take that handle, so a
// second consumer can never redirect or disable the first consumer's ledger.
// A consumer that only needs an isolated atomic write may keep using
// pc_p2_receipt_host_atomic_write(path, data) (stateless).
//
// =============================================================================
// FAMILY CONSUMER CONTRACT (lane 06). A family credits a corpse in one of two
// ways; never both for the same drop.
//
// 1. Ordinary Onion/AP receipt (this host). The family opens its own durable
//    ledger and grants exactly once; restart re-reads the same file, so a
//    re-delivered corpse is a Duplicate and a farmed source never re-arms.
//
//      #include "pc_p2_receipt_host.h"
//      static P2ReceiptHostHandle receipt = nullptr;   // file-scope, per family
//      static std::string seed = "local";              // or PIKMIN_P2_SEED when set
//      // ... at setup:   receipt = pc_p2_receipt_host_open("p2-<family>-receipts.txt");
//      // ... at delivery: grant(receipt, seed.c_str(), identity, slot, encounter);
//      //     identity = "enemy:<source_id>" (ordinary), slot = generator/actor token,
//      //     encounter = a stable event label ("corpse", "flip", "onion", ...).
//      // ... at reset:   pc_p2_receipt_host_close(receipt); receipt = nullptr;
//      // use pc_p2_receipt_host_count(receipt) instead of re-parsing the file.
//
// 2. Experimental Research-Pod corpse receipt. The family implements
//    `bool pc_p2_<family>_receipt(PelletView* /*or Pellet*/ view, unsigned& generator
//    /*, int& value*/)` that identifies its own delivered corpse and returns the
//    generator/identity token; pc_p2_preview_deliver dispatches it and credits the
//    Pod economy (`P2_POD_RECEIPT id=corpse:...`). View-less (number-pellet) corpses
//    use a Pellet*-keyed variant and must carry a synthetic identity token, because
//    no generator id survives a view-less drop. This path never writes the Onion
//    ledger and must never cover an ordinary expected check.
//
//    Natural pickup of a dropped corpse requires FREE-MODE Pikmin: an idle Pikmin
//    only searches for/carries a pellet from free mode (ActFree -> Piki::graspSituation,
//    mIdleWorkSearchRange ~100.0); formation-mode Pikmin leave a headless corpse
//    alone. A reference fixture/receiver must release the squad into free mode
//    (Navi::releasePikis() / Piki::changeMode(PikiMode::FreeMode, ...)) near the
//    corpse before asserting a natural carry.
// =============================================================================

// Opaque handle; nullptr is invalid / not opened.
typedef const void* P2ReceiptHostHandle;

// Open (or reuse) the durable ordinary receipt ledger at `path`. Returns a
// handle, or nullptr when the persisted state cannot be opened (corrupt or
// wrong-version); a missing file opens empty. Re-opening the same path returns
// the same ledger (same durable state), never a fresh one.
P2ReceiptHostHandle pc_p2_receipt_host_open(const char* path);

// The path backing a handle (diagnosis), or nullptr for an invalid handle.
const char* pc_p2_receipt_host_path(P2ReceiptHostHandle handle);

// Stable token validator (mirrors P2Receipt::validToken).
bool pc_p2_receipt_host_valid(const char* value);

// Error is distinct from a durable duplicate; callers must not consume rewards on Error.
enum class P2ReceiptHostResult { Error = -1, Duplicate = 0, Granted = 1 };

// Grant exactly once over the handle's ledger. Returns Granted only on the first
// occurrence of (seed, reward, slotOrActor, encounter). A closed/invalid handle
// returns Error (never dereferences a dangling handle).
P2ReceiptHostResult pc_p2_receipt_host_grant(P2ReceiptHostHandle handle, const char* seed,
	const char* reward, const char* slotOrActor, const char* encounter);

// Number of receipts currently recorded on the handle's ledger (0 for a closed
// or invalid handle). Lets a consumer stop re-parsing its own sidecar file.
unsigned pc_p2_receipt_host_count(P2ReceiptHostHandle handle);

// Release one handle; other handles are unaffected.
void pc_p2_receipt_host_close(P2ReceiptHostHandle handle);

// Stateless atomic write (unrelated to any open ledger).
bool pc_p2_receipt_host_atomic_write(const char* path, const char* data);

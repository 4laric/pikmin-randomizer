#pragma once

// Lane 18 small-Breadbug contest consumer bridge (#220).
//
// Engine-free bridge over lane 06's pc_p2_cargo_contest.h (P2CargoContest) and
// pc_p2_receipt.h (ReceiptLedger / FileReceiptPersistence). Those headers pull
// in <windows.h> on Windows, which collides with the engine's `typedef u32 HWND`
// in AtxStream.h, so the concrete state machine + durable ledger live in the
// matching .cpp and the engine-side family module (pc_p2_breadbug_actor.cpp)
// includes only this header. Value tokens and ints cross the boundary; no
// engine type and no <windows.h> leaks into engine translation units.
//
// Outcome: 0 = Held, 1 = Stolen, 2 = ReleasedToSource.
// Reason : 0 = None, 1 = Interrupted, 2 = OwnerDied, 3 = CarrierLost,
//          4 = Timeout, 5 = Revisit, 6 = Reset.
// Grant  : 0 = Error, 1 = Granted, 2 = Duplicate.

// Durable ordinary receipt ledger (a sidecar text file, not the native save).
// Opens the ledger used by every contest grant so a revisit/restart does not
// re-grant. Returns false on open failure.
bool pc_p2_breadbug_contest_open(const char* path);
void pc_p2_breadbug_contest_close();
// Drop all in-memory contests (keeps the durable ledger file).
void pc_p2_breadbug_contest_reset_all();

// Create a contest and return a positive handle, or 0 on failure. `identity`
// is derived from `sourceId`/`stage` via lane 06's "onion:p2:<id>:<stage>".
int pc_p2_breadbug_contest_create(int sourceId, int stage, const char* sourceToken,
                                  int minThreshold, int maxThreshold, float freezeSeconds,
                                  int requiredCarriers, int maxCarriers);
void pc_p2_breadbug_contest_destroy(int handle);
void pc_p2_breadbug_contest_begin(int handle, float nowSeconds);
// Advance one step with value-token carriers; returns the Outcome int.
int pc_p2_breadbug_contest_update(int handle, float nowSeconds,
                                  const char* const* carrierTokens,
                                  const int* carrierStrengths, int count);
int pc_p2_breadbug_contest_result(int handle);
int pc_p2_breadbug_contest_reason(int handle);
void pc_p2_breadbug_contest_interrupt(int handle);
void pc_p2_breadbug_contest_owner_died(int handle);
void pc_p2_breadbug_contest_revisit(int handle);
// Grant the ordinary receipt (exactly-once; throws-into-Error unless Stolen).
int pc_p2_breadbug_contest_grant(int handle, const char* seed,
                                 const char* slotOrActor, const char* encounter);
const char* pc_p2_breadbug_contest_identity(int handle);
bool pc_p2_breadbug_contest_receipt_granted(int handle);

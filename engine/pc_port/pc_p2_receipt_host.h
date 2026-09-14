#pragma once
// Engine-free bridge to the shared pc_p2_receipt.h provider.
//
// pc_p2_receipt.h includes <windows.h> on Windows for its atomic rename, which
// conflicts with the engine's `typedef u32 HWND` in AtxStream.h. Keeping the
// provider in its own translation unit (this one) lets family modules consume
// the ordinary-Onion receipt ledger without pulling windows.h into an engine TU.
bool pc_p2_receipt_host_open(const char* path);
bool pc_p2_receipt_host_ready();
bool pc_p2_receipt_host_valid(const char* value);
// Error is distinct from a durable duplicate; callers must not consume rewards on Error.
enum class P2ReceiptHostResult { Error = -1, Duplicate = 0, Granted = 1 };
P2ReceiptHostResult pc_p2_receipt_host_grant(const char* seed, const char* reward, const char* slotOrActor,
                              const char* encounter);
void pc_p2_receipt_host_close();

// Atomically replace a sidecar without deleting its last good version first.
bool pc_p2_receipt_host_atomic_write(const char* path, const char* data);

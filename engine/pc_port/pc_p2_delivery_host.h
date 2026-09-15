#pragma once
// Engine-free bridge to the shared pc_p2_delivery.h provider, mirroring
// pc_p2_receipt_host.h. Multiple durable delivery ledgers at distinct paths
// coexist: open() returns an opaque handle per path; deliver()/close() take it,
// so a second consumer never redirects or disables the first consumer's ledger.

// Opaque handle; nullptr is invalid / not opened.
typedef const void* P2DeliveryHostHandle;

// Open (or reuse) the durable delivery ledger at `path`. Returns a handle, or
// nullptr when the persisted state cannot be opened. Re-opening the same path
// returns the same ledger (same durable state).
P2DeliveryHostHandle pc_p2_delivery_host_open(const char* path);

// The path backing a handle, or nullptr.
const char* pc_p2_delivery_host_path(P2DeliveryHostHandle handle);

// Error is distinct from a durable duplicate; callers must not consume rewards on Error.
enum class P2DeliveryHostResult { Error = -1, Duplicate = 0, Granted = 1 };

// Ordinary P2 delivery over the handle's ledger: always p1Proxy=false and a
// non-zero bound source id. Grants exactly once per (seed, identity, slot, encounter).
P2DeliveryHostResult pc_p2_delivery_host_deliver(P2DeliveryHostHandle handle, const char* seed,
	unsigned sourceId, int tekiType, int stage, unsigned generatorToken, const char* encounter);

void pc_p2_delivery_host_close(P2DeliveryHostHandle handle);

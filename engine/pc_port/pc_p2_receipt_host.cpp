#include "pc_p2_receipt_host.h"
#include "pc_p2_receipt.h"
#include <map>
#include <memory>
#include <string>

namespace {
struct ReceiptHost {
	std::string path;
	std::unique_ptr<P2Receipt::FileReceiptPersistence> persistence;
	std::unique_ptr<P2Receipt::ReceiptLedger> ledger;
};
// Keyed by path; the handle is the stable ReceiptHost address.
std::map<std::string, std::unique_ptr<ReceiptHost>> receiptHosts;

// Resolve a handle to a live host via the registry (never dereference a dangling
// handle). A closed handle is not present, so it resolves to nullptr -> Error.
ReceiptHost* receiptHostByHandle(P2ReceiptHostHandle handle)
{
	for (auto& entry : receiptHosts) {
		if (entry.second.get() == handle) {
			return entry.second.get();
		}
	}
	return nullptr;
}
} // namespace

P2ReceiptHostHandle pc_p2_receipt_host_open(const char* path)
{
	if (!path) {
		return nullptr;
	}
	const std::string key(path);
	const auto existing = receiptHosts.find(key);
	if (existing != receiptHosts.end()) {
		return existing->second.get();
	}
	auto host = std::make_unique<ReceiptHost>();
	host->path = key;
	try {
		host->persistence = std::make_unique<P2Receipt::FileReceiptPersistence>(key);
		host->ledger = std::make_unique<P2Receipt::ReceiptLedger>(*host->persistence);
	} catch (...) {
		return nullptr;
	}
	ReceiptHost* handle = host.get();
	receiptHosts.emplace(key, std::move(host));
	return handle;
}

const char* pc_p2_receipt_host_path(P2ReceiptHostHandle handle)
{
	ReceiptHost* host = receiptHostByHandle(handle);
	return host ? host->path.c_str() : nullptr;
}

bool pc_p2_receipt_host_valid(const char* value)
{
	return value && P2Receipt::validToken(value, 128);
}

P2ReceiptHostResult pc_p2_receipt_host_grant(P2ReceiptHostHandle handle, const char* seed,
	const char* reward, const char* slotOrActor, const char* encounter)
{
	ReceiptHost* host = receiptHostByHandle(handle);
	if (!host || !seed || !reward || !slotOrActor || !encounter) {
		return P2ReceiptHostResult::Error;
	}
	try {
		return host->ledger->grant(seed, reward, slotOrActor, encounter)
		    ? P2ReceiptHostResult::Granted : P2ReceiptHostResult::Duplicate;
	} catch (...) {
		return P2ReceiptHostResult::Error;
	}
}

unsigned pc_p2_receipt_host_count(P2ReceiptHostHandle handle)
{
	ReceiptHost* host = receiptHostByHandle(handle);
	return host ? static_cast<unsigned>(host->ledger->size()) : 0;
}

void pc_p2_receipt_host_close(P2ReceiptHostHandle handle)
{
	for (auto it = receiptHosts.begin(); it != receiptHosts.end(); ++it) {
		if (it->second.get() == handle) {
			receiptHosts.erase(it);
			return;
		}
	}
}

bool pc_p2_receipt_host_atomic_write(const char* path, const char* data)
{
	if (!path || !data) {
		return false;
	}
	const std::string temporary = std::string(path) + ".tmp";
	{
		std::ofstream out(temporary, std::ios::binary | std::ios::trunc);
		if (!out) {
			return false;
		}
		out << data;
		out.flush();
		if (!out) {
			return false;
		}
	}
#ifdef _WIN32
	return ::MoveFileExA(temporary.c_str(), path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
	return std::rename(temporary.c_str(), path) == 0;
#endif
}

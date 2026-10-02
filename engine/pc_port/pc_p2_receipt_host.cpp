#include "pc_p2_receipt_host.h"
#include "pc_p2_receipt.h"
#include <map>
#include <memory>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <filesystem>
#include <fstream>

// Netplay M4 lane B2 (issue #885): P2 receipt ledgers in a netplay session.
// Strong-defined by pc_netplay_session.cpp in netplay builds only; null here in
// the default build and in the engine-free tests, where the historical file
// persistence runs unchanged.
#if defined(__GNUC__)
__attribute__((weak)) bool pc_netplay_session_active(void);
__attribute__((weak)) bool pc_netplay_is_host(void);
__attribute__((weak)) bool pc_netplay_randstate_stream_enabled(void);
#endif

namespace {
// 0 = no netplay session with the external-state stream (historical path),
// 1 = netplay host, 2 = netplay client.
int netplayRole()
{
#if defined(__GNUC__)
	if (pc_netplay_session_active == nullptr || !pc_netplay_session_active()) return 0;
	if (pc_netplay_randstate_stream_enabled == nullptr || !pc_netplay_randstate_stream_enabled()) return 0;
	return (pc_netplay_is_host == nullptr || pc_netplay_is_host()) ? 1 : 2;
#else
	return 0;
#endif
}

// In a session both peers open the same ledger bytes (the file travels with
// the host's sidecar set, or is absent on both), and every grant is decided
// in memory from them, identically on both peers. Only the host writes the
// file; a host write failure is fatal (exit 2) instead of an Error result,
// so no sim-visible branch can depend on host-only I/O. The client never
// writes: its ledger lives in memory, per path for the whole process, so a
// ledger closed at a stage boundary and reopened later reloads exactly what
// the host's reopen reads back from its file.
std::map<std::string, std::vector<P2Receipt::Key>>& clientLedgers()
{
	static std::map<std::string, std::vector<P2Receipt::Key>> ledgers;
	return ledgers;
}
class NetplayReceiptPersistence : public P2Receipt::ReceiptPersistence {
public:
	NetplayReceiptPersistence(const std::string& path, bool client) : mFile(path), mPath(path), mClient(client) {}
	bool load(std::vector<P2Receipt::Key>& out) override
	{
		if (!mClient) return mFile.load(out);
		const auto it = clientLedgers().find(mPath);
		if (it != clientLedgers().end()) {
			out = it->second;
			return true;
		}
		const bool ok = mFile.load(out); // the session-start bytes, identical to the host's
		clientLedgers()[mPath] = out;
		return ok;
	}
	void store(const std::vector<P2Receipt::Key>& keys) override
	{
		if (mClient) {
			clientLedgers()[mPath] = keys;
			return;
		}
		try {
			mFile.store(keys);
		} catch (...) {
			std::fprintf(stderr, "[netplay] P2 receipt ledger %s: host write failed\n", mPath.c_str());
			std::exit(2);
		}
	}

private:
	P2Receipt::FileReceiptPersistence mFile;
	std::string mPath;
	bool mClient;
};

std::unique_ptr<P2Receipt::ReceiptPersistence> makeReceiptPersistence(const std::string& path)
{
	const int role = netplayRole();
	if (role == 0) return std::make_unique<P2Receipt::FileReceiptPersistence>(path);
	return std::make_unique<NetplayReceiptPersistence>(path, role == 2);
}
} // namespace

namespace {
struct ReceiptHost {
	std::string path;
	std::unique_ptr<P2Receipt::ReceiptPersistence> persistence;
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
    std::error_code readError;
    const bool present = std::filesystem::exists(key, readError);
    // A client reopen uses the agreed in-memory ledger even if its original
    // file becomes inaccessible. Cold opens and every authoritative host open
    // retain the existing fail-closed file checks.
    const bool cachedClient = netplayRole() == 2 && clientLedgers().count(key) != 0;
    if (!cachedClient && (readError || (present && !std::ifstream(key).good()))) return nullptr;
	const auto existing = receiptHosts.find(key);
	if (existing != receiptHosts.end()) {
		return existing->second.get();
	}
	auto host = std::make_unique<ReceiptHost>();
	host->path = key;
	try {
		host->persistence = makeReceiptPersistence(key); // B2: netplay-aware
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
	// Netplay M4 lane B2: the client never writes a P2 ledger (its state is
	// the in-memory copy both peers derive identically).
	if (netplayRole() == 2) {
		return true;
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

int pc_p2_receipt_host_has(P2ReceiptHostHandle handle, const char* seed,
    const char* reward, const char* slotOrActor, const char* encounter)
{
    ReceiptHost* host = receiptHostByHandle(handle);
    if (!host || !seed || !reward || !slotOrActor || !encounter) return -1;
    try {
        return host->ledger->has(seed, reward, slotOrActor, encounter) ? 1 : 0;
    } catch (...) { return -1; }
}

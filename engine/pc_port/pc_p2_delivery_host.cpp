#include "pc_p2_delivery_host.h"
#include "pc_p2_delivery.h"
#include <map>
#include <memory>
#include <string>

namespace {
struct DeliveryHost {
	std::string path;
	std::unique_ptr<P2Receipt::FileReceiptPersistence> persistence;
	std::unique_ptr<P2Receipt::ReceiptLedger> ledger;
	std::unique_ptr<P2Delivery::DeliveryReceiver> receiver;
};
std::map<std::string, std::unique_ptr<DeliveryHost>> deliveryHosts;

// Resolve a handle to a live host via the registry (never dereference a dangling
// handle). A closed handle is not present, so it resolves to nullptr -> Error.
DeliveryHost* deliveryHostByHandle(P2DeliveryHostHandle handle)
{
	for (auto& entry : deliveryHosts) {
		if (entry.second.get() == handle) {
			return entry.second.get();
		}
	}
	return nullptr;
}
} // namespace

P2DeliveryHostHandle pc_p2_delivery_host_open(const char* path)
{
	if (!path) {
		return nullptr;
	}
	const std::string key(path);
	const auto existing = deliveryHosts.find(key);
	if (existing != deliveryHosts.end()) {
		return existing->second.get();
	}
	auto host = std::make_unique<DeliveryHost>();
	host->path = key;
	try {
		host->persistence = std::make_unique<P2Receipt::FileReceiptPersistence>(key);
		host->ledger = std::make_unique<P2Receipt::ReceiptLedger>(*host->persistence);
		host->receiver = std::make_unique<P2Delivery::DeliveryReceiver>(*host->ledger);
	} catch (...) {
		return nullptr;
	}
	DeliveryHost* handle = host.get();
	deliveryHosts.emplace(key, std::move(host));
	return handle;
}

const char* pc_p2_delivery_host_path(P2DeliveryHostHandle handle)
{
	DeliveryHost* host = deliveryHostByHandle(handle);
	return host ? host->path.c_str() : nullptr;
}

P2DeliveryHostResult pc_p2_delivery_host_deliver(P2DeliveryHostHandle handle, const char* seed,
	unsigned sourceId, int tekiType, int stage, unsigned generatorToken, const char* encounter)
{
	DeliveryHost* host = deliveryHostByHandle(handle);
	if (!host || !seed || !encounter || sourceId == 0) {
		return P2DeliveryHostResult::Error;
	}
	try {
		return host->receiver->deliver(seed, sourceId, tekiType, stage, generatorToken,
			encounter, /*p1Proxy=*/false)
		    ? P2DeliveryHostResult::Granted : P2DeliveryHostResult::Duplicate;
	} catch (...) {
		return P2DeliveryHostResult::Error;
	}
}

void pc_p2_delivery_host_close(P2DeliveryHostHandle handle)
{
	for (auto it = deliveryHosts.begin(); it != deliveryHosts.end(); ++it) {
		if (it->second.get() == handle) {
			deliveryHosts.erase(it);
			return;
		}
	}
}

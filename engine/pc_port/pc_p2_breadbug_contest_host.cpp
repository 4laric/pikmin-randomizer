// Lane 18 small-Breadbug contest consumer bridge implementation (#220).
// Owns a durable ordinary receipt ledger (lane 06 pc_p2_receipt.h) plus one
// P2CargoContest per handle (lane 06 pc_p2_cargo_contest.h), isolated from the
// engine so <windows.h> never reaches an engine translation unit.
#include "pc_p2_breadbug_contest_host.h"

#include "pc_p2_cargo_contest.h"
#include "pc_p2_delivery.h"

#include <map>
#include <memory>
#include <string>
#include <vector>

namespace {
std::unique_ptr<P2Receipt::FileReceiptPersistence> sPersistence;
std::unique_ptr<P2Receipt::ReceiptLedger> sLedger;
std::map<int, std::unique_ptr<P2CargoContest>> sContests;
int sNextHandle = 1;
} // namespace

bool pc_p2_breadbug_contest_open(const char* path)
{
	try {
		sPersistence = std::make_unique<P2Receipt::FileReceiptPersistence>(
		    path ? path : "p2-breadbug-contest-receipts.txt");
		sLedger = std::make_unique<P2Receipt::ReceiptLedger>(*sPersistence);
	} catch (...) {
		sContests.clear();
		sLedger.reset();
		sPersistence.reset();
		return false;
	}
	return true;
}

void pc_p2_breadbug_contest_close()
{
	sContests.clear();
	sLedger.reset();
	sPersistence.reset();
}

void pc_p2_breadbug_contest_reset_all()
{
	sContests.clear();
}

int pc_p2_breadbug_contest_create(int sourceId, int stage, const char* sourceToken,
                                  int minThreshold, int maxThreshold, float freezeSeconds,
                                  int requiredCarriers, int maxCarriers)
{
	if (!sLedger) {
		return 0;
	}
	P2CargoContestConfig config;
	config.identity = P2Delivery::p2SourceIdentity(static_cast<unsigned>(sourceId), stage);
	config.sourceToken = sourceToken ? sourceToken : "";
	config.minThreshold = minThreshold;
	config.maxThreshold = maxThreshold;
	config.freezeSeconds = freezeSeconds;
	config.requiredCarriers = requiredCarriers;
	config.maxCarriers = maxCarriers;
	const int handle = sNextHandle++;
	sContests.emplace(handle, std::make_unique<P2CargoContest>(std::move(config)));
	return handle;
}

void pc_p2_breadbug_contest_destroy(int handle)
{
	sContests.erase(handle);
}

void pc_p2_breadbug_contest_begin(int handle, float nowSeconds)
{
	auto it = sContests.find(handle);
	if (it != sContests.end()) {
		it->second->begin(nowSeconds);
	}
}

int pc_p2_breadbug_contest_update(int handle, float nowSeconds,
                                  const char* const* carrierTokens,
                                  const int* carrierStrengths, int count)
{
	auto it = sContests.find(handle);
	if (it == sContests.end()) {
		return 0;
	}
	std::vector<P2ContestCarrier> carriers;
	for (int i = 0; i < count; ++i) {
		P2ContestCarrier carrier;
		carrier.token = carrierTokens && carrierTokens[i] ? carrierTokens[i] : "";
		carrier.strength = carrierStrengths ? carrierStrengths[i] : 0;
		carriers.push_back(std::move(carrier));
	}
	return static_cast<int>(it->second->update(nowSeconds, carriers));
}

int pc_p2_breadbug_contest_result(int handle)
{
	auto it = sContests.find(handle);
	return it == sContests.end() ? 0 : static_cast<int>(it->second->result());
}

int pc_p2_breadbug_contest_reason(int handle)
{
	auto it = sContests.find(handle);
	return it == sContests.end() ? 0 : static_cast<int>(it->second->reason());
}

void pc_p2_breadbug_contest_interrupt(int handle)
{
	auto it = sContests.find(handle);
	if (it != sContests.end()) {
		it->second->interrupt();
	}
}

void pc_p2_breadbug_contest_owner_died(int handle)
{
	auto it = sContests.find(handle);
	if (it != sContests.end()) {
		it->second->onOwnerDied();
	}
}

void pc_p2_breadbug_contest_revisit(int handle)
{
	auto it = sContests.find(handle);
	if (it != sContests.end()) {
		it->second->onRevisit();
	}
}

int pc_p2_breadbug_contest_grant(int handle, const char* seed,
                                 const char* slotOrActor, const char* encounter)
{
	auto it = sContests.find(handle);
	if (it == sContests.end() || !sLedger) {
		return 0;
	}
	try {
		const bool granted = it->second->grantReceipt(*sLedger,
		                                             seed ? seed : "",
		                                             slotOrActor ? slotOrActor : "",
		                                             encounter ? encounter : "");
		return granted ? 1 : 2;
	} catch (const std::runtime_error&) {
		return 0;
	}
}

const char* pc_p2_breadbug_contest_identity(int handle)
{
	auto it = sContests.find(handle);
	return it == sContests.end() ? "" : it->second->identity().c_str();
}

bool pc_p2_breadbug_contest_receipt_granted(int handle)
{
	auto it = sContests.find(handle);
	return it != sContests.end() && it->second->receiptGranted();
}

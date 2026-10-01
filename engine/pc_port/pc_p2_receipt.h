#pragma once

// Lane 06 shared reward/cargo receipt contract (native C++ counterpart of
// experimental/pikmin2_receipts.py). Engine-free: no engine types, no retail
// asset, no save-file layout. It defines the one vocabulary that family drop
// endpoints and the cargo-contest provider (lane 18) agree on, so an ordinary
// Onion/AP reward can never be confused with the experimental Research Pod
// economy.
//
// This header is the provider surface requested by #441 / lane 18. It is not a
// source family drop and it does not write the native save: native save mutation
// stays coordinated with lane 01. See docs/PIKMIN2_REWARD_RECEIPTS.md.

#include <algorithm>
#include <cstddef>
#include <cstdio>
#include <fstream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace P2Receipt {

// Ordinary P1 Onion/AP behaviour must never share a ledger with the
// experimental Research Pod/Poko economy.
enum class Ledger { Onion, Ap, Pod };

inline const char* ledgerTag(Ledger ledger)
{
	switch (ledger) {
	case Ledger::Onion: return "onion";
	case Ledger::Ap: return "ap";
	default: return "pod";
	}
}

inline bool ordinary(Ledger ledger) { return ledger != Ledger::Pod; }

// Stable token validators mirroring the Python contract. An identity is the
// reward/source key; the other three fields are the grant-event coordinates.
inline bool validToken(const std::string& value, std::size_t limit)
{
	if (value.empty() || value.size() > limit) {
		return false;
	}
	for (char c : value) {
		const bool ok = (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
			|| (c >= '0' && c <= '9') || c == '_' || c == ':' || c == '/' || c == '-' || c == '.';
		if (!ok) {
			return false;
		}
	}
	return true;
}

inline std::string identity(const std::string& value)
{
	if (!validToken(value, 90)) {
		throw std::runtime_error("Invalid reward identity");
	}
	return value;
}

inline std::string coordinate(const std::string& value)
{
	if (!validToken(value, 128)) {
		throw std::runtime_error("Invalid receipt coordinate");
	}
	return value;
}

// Exactly-once key = (seed, identity, slot_or_actor, encounter).
using Key = std::tuple<std::string, std::string, std::string, std::string>;

inline Key receiptKey(const std::string& seed, const std::string& reward,
	const std::string& slotOrActor, const std::string& encounter)
{
	return Key(coordinate(seed), identity(reward), coordinate(slotOrActor), coordinate(encounter));
}

// Persistence boundary. Concrete backends must round-trip the sorted key list
// and reject malformed / duplicate state rather than silently resetting it.
class ReceiptPersistence {
public:
	virtual ~ReceiptPersistence() = default;
	virtual bool load(std::vector<Key>& out) = 0;
	virtual void store(const std::vector<Key>& keys) = 0;
};

class MemoryReceiptPersistence : public ReceiptPersistence {
public:
	MemoryReceiptPersistence() = default;
	explicit MemoryReceiptPersistence(std::vector<Key> keys) : mKeys(std::move(keys)) {}

	bool load(std::vector<Key>& out) override
	{
		out = mKeys;
		return true;
	}

	void store(const std::vector<Key>& keys) override { mKeys = keys; }

private:
	std::vector<Key> mKeys;
};

// Durable ordinary receipt state. This is an ordinary sidecar text file, NOT the
// Pikmin save/memory-card layout: native save mutation stays with lane 01.
// Writes go to a temp sibling and are atomically renamed, so an interrupted
// write leaves the previous good file untouched.
class FileReceiptPersistence : public ReceiptPersistence {
public:
	explicit FileReceiptPersistence(std::string path) : mPath(std::move(path)) {}

	bool load(std::vector<Key>& out) override
	{
		out.clear();
		std::ifstream input(mPath);
		if (!input.is_open()) {
			return true; // missing file starts empty
		}
		std::string header;
		if (!(input >> header) || header != "P2_RECEIPTS_1") {
			throw std::runtime_error("Invalid P2 receipt header");
		}
		std::set<Key> seen;
		std::string seed, reward, slot, encounter;
		while (input >> seed) {
			if (!(input >> reward >> slot >> encounter)) {
				throw std::runtime_error("Truncated P2 receipt record");
			}
			const Key key = receiptKey(seed, reward, slot, encounter);
			if (!seen.insert(key).second) {
				throw std::runtime_error("Duplicate persisted receipt");
			}
			out.push_back(key);
		}
		if (!input.eof()) {
			throw std::runtime_error("Cannot read P2 receipt state");
		}
		return true;
	}

	void store(const std::vector<Key>& keys) override
	{
		std::ostringstream data;
		data << "P2_RECEIPTS_1\n";
		for (const Key& key : keys) {
			data << std::get<0>(key) << ' ' << std::get<1>(key) << ' '
				<< std::get<2>(key) << ' ' << std::get<3>(key) << '\n';
		}
		const std::string temporary = mPath + ".tmp";
		{
			std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
			if (!output.is_open()) {
				throw std::runtime_error("Cannot create P2 receipt temporary file");
			}
			output << data.str();
			output.flush();
			if (!output) {
				throw std::runtime_error("Cannot flush P2 receipt state");
			}
		}
#ifdef _WIN32
		if (!::MoveFileExA(temporary.c_str(), mPath.c_str(),
			MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) {
			throw std::runtime_error("Cannot replace P2 receipt state");
		}
#else
		if (std::rename(temporary.c_str(), mPath.c_str()) != 0) {
			throw std::runtime_error("Cannot replace P2 receipt state");
		}
#endif
	}

private:
	std::string mPath;
};

// Exactly-once receipts over a persistence backend. `grant` returns true only
// for the first occurrence of a key; `reload` models a process restart over the
// same backend and never re-grants a persisted key.
class ReceiptLedger {
public:
	explicit ReceiptLedger(ReceiptPersistence& persistence) : mPersistence(persistence) { reload(); }

	std::size_t size() const { return mKeys.size(); }

	bool has(const std::string& seed, const std::string& reward,
		const std::string& slotOrActor, const std::string& encounter) const
	{
		return mKeys.count(receiptKey(seed, reward, slotOrActor, encounter)) != 0;
	}

	// Returns true only for the first occurrence of this grant event.
	bool grant(const std::string& seed, const std::string& reward,
		const std::string& slotOrActor, const std::string& encounter)
	{
		const Key key = receiptKey(seed, reward, slotOrActor, encounter);
		if (!mKeys.insert(key).second) {
			return false;
		}
		try {
			persist();
		} catch (...) {
			mKeys.erase(key);
			throw;
		}
		return true;
	}

	void reload()
	{
		std::vector<Key> loaded;
		mPersistence.load(loaded);
		std::set<Key> next;
		for (const Key& key : loaded) {
			if (!next.insert(key).second) {
				throw std::runtime_error("Duplicate persisted receipt");
			}
		}
		mKeys = std::move(next);
	}

private:
	void persist()
	{
		std::vector<Key> keys(mKeys.begin(), mKeys.end());
		std::sort(keys.begin(), keys.end());
		mPersistence.store(keys);
	}

	ReceiptPersistence& mPersistence;
	std::set<Key> mKeys;
};

// One validated reward descriptor. `drop` stays a string so family lanes carry
// the source meaning without this shared header owning it.
struct Descriptor {
	std::string version = "p2-reward-descriptor-v1";
	std::string identity;
	std::string family;
	std::string drop;   // corpse | pellet | treasure | none
	Ledger ledger = Ledger::Onion;
};

inline Descriptor validateDescriptor(const Descriptor& in)
{
	if (in.version != "p2-reward-descriptor-v1") {
		throw std::runtime_error("Unknown reward descriptor version");
	}
	Descriptor out = in;
	out.identity = P2Receipt::identity(in.identity);
	if (!validToken(in.family, 40)) {
		throw std::runtime_error("Invalid reward family lane");
	}
	if (in.drop != "corpse" && in.drop != "pellet" && in.drop != "treasure" && in.drop != "none") {
		throw std::runtime_error("Invalid reward drop kind");
	}
	return out;
}

struct ReconcileResult {
	bool ok = false;
	std::vector<std::string> ordinarySources;
	std::vector<std::string> experimentalSources;
	std::vector<std::string> missingSources;
	std::vector<std::string> podLeaks;
};

// Every expected ordinary check must have an ordinary source; a Pod-only
// descriptor covering one is a leak and is refused (mirrors the Python
// `reconcile(..., refuse_pod_leaks=True)` default).
inline ReconcileResult reconcileOrdinary(const std::vector<Descriptor>& descriptors,
	const std::vector<std::string>& expectedChecks)
{
	std::map<std::string, Descriptor> byIdentity;
	std::set<std::string> expected;
	for (const Descriptor& raw : descriptors) {
		const Descriptor descriptor = validateDescriptor(raw);
		if (!byIdentity.emplace(descriptor.identity, descriptor).second) {
			throw std::runtime_error("Duplicate reward identity");
		}
	}
	ReconcileResult result;
	for (const std::string& check : expectedChecks) {
		const std::string key = identity(check);
		if (!expected.insert(key).second) {
			throw std::runtime_error("Duplicate expected check");
		}
		const auto found = byIdentity.find(key);
		if (found == byIdentity.end()) {
			result.missingSources.push_back(key);
		} else if (!ordinary(found->second.ledger)) {
			result.podLeaks.push_back(key);
		}
	}
	for (const auto& entry : byIdentity) {
		if (ordinary(entry.second.ledger)) {
			result.ordinarySources.push_back(entry.first);
		} else {
			result.experimentalSources.push_back(entry.first);
		}
	}
	if (!result.podLeaks.empty()) {
		std::string message = "Pod-only reward leaks into ordinary ledger:";
		for (const std::string& leak : result.podLeaks) {
			message += " " + leak;
		}
		throw std::runtime_error(message);
	}
	result.ok = result.missingSources.empty() && result.podLeaks.empty();
	return result;
}

} // namespace P2Receipt

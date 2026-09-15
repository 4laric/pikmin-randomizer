#pragma once

// Lane 06 ordinary Onion/AP delivery receiver. This is the provider surface that
// connects a real P2 family corpse delivery through the durable ordinary receipt
// ledger (pc_p2_receipt.h) without ever confusing it with the P1-proxy Teki type
// the family reuses, or with the experimental Research Pod economy.
//
// Engine-free, like pc_p2_receipt.h: no engine types, no retail asset, no
// save-file layout. Native save mutation stays coordinated with lane 01. The
// P1-proxy and P2-source vocabularies share the ordinary "onion:" prefix and are
// disjoint behind "onion:p1:" / "onion:p2:", so a proxied P1 reward can never
// collide with a real P2 source, even when their numeric parts coincide. The Pod
// economy keeps its own "corpse:" identities, so an ordinary "onion:" key never
// pollutes the Pod receipt count (which filters rows by the "corpse:" prefix).
// Exactly-once, persistence and restart behaviour are inherited from
// P2Receipt::ReceiptLedger.
//
// The engine hook that calls this receiver MUST pass the bound P2 source id when
// `p1Proxy` is false; an unbound (sourceId == 0) P2 delivery is rejected rather
// than silently credited to the P1-proxy check.
//
// Python mirror: experimental/pikmin2_delivery.py.

#include "pc_p2_receipt.h"
#include <stdexcept>
#include <string>

namespace P2Delivery {

// Proxy identity for an ordinary P1 enemy encountered on `stage`.
inline std::string p1ProxyIdentity(int tekiType, int stage)
{
	return "onion:p1:" + std::to_string(tekiType) + ":" + std::to_string(stage);
}

// Source identity for an imported P2 enemy `sourceId` on `stage`.
inline std::string p2SourceIdentity(unsigned sourceId, int stage)
{
	return "onion:p2:" + std::to_string(sourceId) + ":" + std::to_string(stage);
}

// Exactly-once delivery receiver. `p1Proxy` is explicit: true selects the
// P1-proxy identity path; false selects the P2-source identity path, which
// requires a non-zero (bound) source id. Grants defer to the wrapped ledger so
// exactly-once guarantees hold unchanged.
class DeliveryReceiver {
public:
	explicit DeliveryReceiver(P2Receipt::ReceiptLedger& ledger) : mLedger(ledger) {}

	std::string identity(unsigned sourceId, int tekiType, int stage, bool p1Proxy) const
	{
		if (p1Proxy) {
			return p1ProxyIdentity(tekiType, stage);
		}
		if (sourceId == 0) {
			throw std::runtime_error("P2 delivery requires a bound source id");
		}
		return p2SourceIdentity(sourceId, stage);
	}

	std::string slotOrActor(unsigned generatorToken) const
	{
		return "g" + std::to_string(generatorToken);
	}

	bool deliver(const std::string& seed, unsigned sourceId, int tekiType, int stage,
		unsigned generatorToken, const std::string& encounter, bool p1Proxy)
	{
		return mLedger.grant(seed, identity(sourceId, tekiType, stage, p1Proxy),
			slotOrActor(generatorToken), encounter);
	}

	bool delivered(const std::string& seed, unsigned sourceId, int tekiType, int stage,
		unsigned generatorToken, const std::string& encounter, bool p1Proxy) const
	{
		return mLedger.has(seed, identity(sourceId, tekiType, stage, p1Proxy),
			slotOrActor(generatorToken), encounter);
	}

private:
	P2Receipt::ReceiptLedger& mLedger;
};

// Builds the ordinary receipt descriptor for a P2 source so reconcileOrdinary can
// assert that an expected ordinary check has a real ordinary source (never pod).
// The owning family lane supplies its tag; this shared header does not default it.
inline P2Receipt::Descriptor sourceDescriptor(unsigned sourceId, int stage,
	const std::string& family)
{
	P2Receipt::Descriptor descriptor;
	descriptor.identity = p2SourceIdentity(sourceId, stage);
	descriptor.family = family;
	descriptor.drop = "corpse";
	descriptor.ledger = P2Receipt::Ledger::Onion;
	return descriptor;
}

} // namespace P2Delivery

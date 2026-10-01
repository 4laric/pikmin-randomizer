#pragma once

// Lane 18 provider surface: the P2 cargo contest and its exactly-once receipt
// hook (lane 06 owns the shared receipt vocabulary in pc_p2_receipt.h).
//
// Requested by #441 / #220: a small PanModoki or nest must not fork the contest
// logic embedded in pc_p2_giant_breadbug_actor.cpp. Family modules supply only
// per-species parameters; this header owns the transition table.
//
// Lifetime: contest state is owned by the cargo. Carriers are passed in by
// value-token each update and never stored, so a recycled engine address cannot
// leave a dangling helper pointer. State is cleared on release, death,
// interruption, revisit and reset. Helpers/aliases never earn a receipt: the
// receipt identity is the cargo identity only.

#include <algorithm>
#include <string>
#include <vector>

#include "pc_p2_receipt.h"

enum class P2ContestOutcome { Held, Stolen, ReleasedToSource };

enum class P2ReleaseReason {
	None,
	Interrupted,
	OwnerDied,
	CarrierLost,
	Timeout,
	Revisit,
	Reset
};

struct P2ContestCarrier {
	std::string token; // stable identity, not an engine pointer
	int strength = 0;
};

struct P2CargoContestConfig {
	std::string identity;        // cargo/reward identity key
	std::string sourceToken;     // owning source/nest token
	int minThreshold = 1;        // strength needed to hold
	int maxThreshold = 0;        // strength that forces a steal; 0 = no cap
	float freezeSeconds = 0.0f;  // 0 = no timeout
	int requiredCarriers = 1;    // minimum distinct carriers to hold
	int maxCarriers = 1;         // ordered carriers considered; 0 = unbounded
};

class P2CargoContest {
public:
	explicit P2CargoContest(P2CargoContestConfig config)
		: mConfig(std::move(config)), mStarted(false), mResult(P2ContestOutcome::Held),
		  mReason(P2ReleaseReason::None), mReceiptGranted(false) {}

	void begin(float nowSeconds)
	{
		mStarted = true;
		mStartSeconds = nowSeconds;
		mResult = P2ContestOutcome::Held;
		mReason = P2ReleaseReason::None;
		mReceiptGranted = false;
	}

	// Evaluate one simulation step. `carriers` is consumed by value; nothing is
	// retained past this call. Returns the current outcome.
	P2ContestOutcome update(float nowSeconds, const std::vector<P2ContestCarrier>& carriers)
	{
		if (!mStarted) {
			return P2ContestOutcome::Held;
		}
		if (mResult != P2ContestOutcome::Held) {
			return mResult;
		}
		long long strength = 0;
		int count = 0;
		const int limit = mConfig.maxCarriers > 0
			? std::min<int>(mConfig.maxCarriers, static_cast<int>(carriers.size()))
			: static_cast<int>(carriers.size());
		for (int i = 0; i < limit; ++i) {
			if (!P2Receipt::validToken(carriers[i].token, 128)) {
				throw std::runtime_error("Invalid contest carrier token");
			}
			strength += std::max(0, carriers[i].strength);
			if (carriers[i].strength > 0) {
				++count;
			}
		}
		if (mConfig.maxThreshold > 0 && strength >= mConfig.maxThreshold) {
			mResult = P2ContestOutcome::Stolen;
			mReason = P2ReleaseReason::None;
			return mResult;
		}
		if (count < mConfig.requiredCarriers) {
			// Not enough carriers: hold unless the freeze window lapses.
			if (mConfig.freezeSeconds > 0.0f && nowSeconds - mStartSeconds >= mConfig.freezeSeconds) {
				mResult = P2ContestOutcome::ReleasedToSource;
				mReason = P2ReleaseReason::Timeout;
			}
			return mResult;
		}
		if (strength < mConfig.minThreshold) {
			return P2ContestOutcome::Held;
		}
		return P2ContestOutcome::Held;
	}

	// Cargo returns to its source on death, interruption or explicit release.
	void release(P2ReleaseReason reason)
	{
		if (mResult == P2ContestOutcome::Stolen) {
			return;
		}
		mResult = P2ContestOutcome::ReleasedToSource;
		mReason = reason;
	}

	void interrupt() { release(P2ReleaseReason::Interrupted); }
	void onOwnerDied() { release(P2ReleaseReason::OwnerDied); }
	void onCarrierLost() { release(P2ReleaseReason::CarrierLost); }
	void onRevisit() { release(P2ReleaseReason::Revisit); }

	void reset()
	{
		mStarted = false;
		mResult = P2ContestOutcome::Held;
		mReason = P2ReleaseReason::None;
		mReceiptGranted = false;
	}

	P2ContestOutcome result() const { return mResult; }
	P2ReleaseReason reason() const { return mReason; }
	const std::string& identity() const { return mConfig.identity; }
	const std::string& sourceToken() const { return mConfig.sourceToken; }
	bool receiptGranted() const { return mReceiptGranted; }

	// Exactly-once receipt for a successful steal. A repeated call for the same
	// cargo grants nothing; the ledger persists across reload/restart.
	bool grantReceipt(P2Receipt::ReceiptLedger& ledger, const std::string& seed,
		const std::string& slotOrActor, const std::string& encounter)
	{
		if (mResult != P2ContestOutcome::Stolen) {
			throw std::runtime_error("Receipt only follows a stolen cargo");
		}
		if (mReceiptGranted) {
			return false;
		}
		const bool granted = ledger.grant(seed, mConfig.identity, slotOrActor, encounter);
		if (granted) {
			mReceiptGranted = true;
		}
		return granted;
	}

private:
	P2CargoContestConfig mConfig;
	bool mStarted;
	float mStartSeconds = 0.0f;
	P2ContestOutcome mResult;
	P2ReleaseReason mReason;
	bool mReceiptGranted;
};

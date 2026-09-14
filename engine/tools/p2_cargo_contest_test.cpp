#include "pc_p2_cargo_contest.h"

#include <cassert>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>

template <class F> bool throws(F f)
{
	try {
		f();
	} catch (const std::runtime_error&) {
		return true;
	}
	return false;
}

static P2CargoContestConfig config()
{
	P2CargoContestConfig cfg;
	cfg.identity = "nest:panmodoki:1";
	cfg.sourceToken = "nest:1";
	cfg.minThreshold = 3;
	cfg.maxThreshold = 10;
	cfg.freezeSeconds = 5.0f;
	cfg.requiredCarriers = 2;
	cfg.maxCarriers = 4;
	return cfg;
}

int main()
{
	using Carrier = P2ContestCarrier;

	// Hold until enough carriers, then time out back to the source.
	{
		P2CargoContest contest(config());
		contest.begin(0.0f);
		const std::vector<Carrier> none;
		const std::vector<Carrier> one = {Carrier{"piki:1", 5}};
		assert(contest.update(0.0f, none) == P2ContestOutcome::Held);
		assert(contest.update(1.0f, one) == P2ContestOutcome::Held);
		assert(contest.update(6.0f, one) == P2ContestOutcome::ReleasedToSource);
		assert(contest.reason() == P2ReleaseReason::Timeout);
	}

	// Two carriers above the minimum hold; enough strength steals.
	{
		P2CargoContest contest(config());
		contest.begin(0.0f);
		const std::vector<Carrier> twoWeak = {Carrier{"piki:1", 2}, Carrier{"piki:2", 2}};
		const std::vector<Carrier> twoStrong = {Carrier{"piki:1", 6}, Carrier{"piki:2", 6}};
		assert(contest.update(0.0f, twoWeak) == P2ContestOutcome::Held);
		assert(contest.update(1.0f, twoStrong) == P2ContestOutcome::Stolen);

		// Exactly-once receipt across a reload of the shared ledger.
		P2Receipt::MemoryReceiptPersistence memory;
		P2Receipt::ReceiptLedger ledger(memory);
		assert(contest.grantReceipt(ledger, "seedZ", "cargo9", "enc0"));
		assert(!contest.grantReceipt(ledger, "seedZ", "cargo9", "enc0"));
		assert(contest.receiptGranted());
		assert(ledger.size() == 1);
		ledger.reload();
		assert(!ledger.grant("seedZ", "nest:panmodoki:1", "cargo9", "enc0"));
		assert(ledger.size() == 1);
	}

	// Death / interruption / revisit return the cargo to its source.
	{
		P2CargoContest contest(config());
		contest.begin(0.0f);
		const std::vector<Carrier> twoWeak = {Carrier{"piki:1", 2}, Carrier{"piki:2", 2}};
		contest.update(0.0f, twoWeak);
		contest.onOwnerDied();
		assert(contest.result() == P2ContestOutcome::ReleasedToSource);
		assert(contest.reason() == P2ReleaseReason::OwnerDied);
	}

	{
		P2CargoContest contest(config());
		contest.begin(0.0f);
		contest.interrupt();
		assert(contest.reason() == P2ReleaseReason::Interrupted);
		contest.reset();
		assert(contest.result() == P2ContestOutcome::Held);
		assert(contest.reason() == P2ReleaseReason::None);
	}

	// Reset clears the receipt latch but not the shared durable ledger.
	{
		P2CargoContest contest(config());
		contest.begin(0.0f);
		const std::vector<Carrier> twoStrong = {Carrier{"piki:1", 6}, Carrier{"piki:2", 6}};
		contest.update(0.0f, twoStrong);
		contest.reset();
		assert(!contest.receiptGranted());
	}

	// A receipt is only available after a steal.
	{
		P2CargoContest contest(config());
		contest.begin(0.0f);
		P2Receipt::MemoryReceiptPersistence memory;
		P2Receipt::ReceiptLedger ledger(memory);
		assert(throws([&] { contest.grantReceipt(ledger, "seed", "a", "b"); }));
	}

	// Invalid carrier tokens are rejected; maxCarriers bounds what is inspected.
	{
		P2CargoContest contest(config());
		contest.begin(0.0f);
		const std::vector<Carrier> bad = {Carrier{"bad token", 1}};
		assert(throws([&] { contest.update(0.0f, bad); }));
	}

	{
		P2CargoContestConfig bounded = config();
		bounded.maxCarriers = 1;
		P2CargoContest contest(bounded);
		contest.begin(0.0f);
		// The out-of-range carrier is never inspected, so its token is irrelevant.
		const std::vector<Carrier> mixed = {Carrier{"piki:1", 1}, Carrier{"bad token", 100}};
		assert(contest.update(0.0f, mixed) == P2ContestOutcome::Held);
	}

	std::printf("PASS p2_cargo_contest_test\n");
	return 0;
}

// Lane 18 small-Breadbug contest consumer bridge test (#220).
// Engine-free: exercises pc_p2_breadbug_contest_host over the shared
// P2CargoContest + durable ordinary receipt ledger (pc_p2_receipt.h).
#include "pc_p2_breadbug_contest_host.h"

#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <ctime>
#include <string>

static std::string sidecarPath()
{
	std::srand(static_cast<unsigned>(std::time(nullptr)) ^ 0x5f3759dfu);
	return "p2-breadbug-contest-test-" + std::to_string(std::rand()) + ".txt";
}

static int twoCarriers(int handle, float now)
{
	const char* tokens[] = {"piki:0", "piki:1"};
	const int strengths[] = {1, 1};
	return pc_p2_breadbug_contest_update(handle, now, tokens, strengths, 2);
}

int main()
{
	const std::string path = sidecarPath();

	// In-process: identity, held -> stolen, exactly-once latch.
	assert(pc_p2_breadbug_contest_open(path.c_str()));
	const int h = pc_p2_breadbug_contest_create(38, 0, "nest:187", 1, 2, 0.5f, 1, 0);
	assert(h > 0);
	assert(std::string(pc_p2_breadbug_contest_identity(h)) == "onion:p2:38:0");
	pc_p2_breadbug_contest_begin(h, 0.0f);
	{
		const char* one[] = {"piki:0"};
		const int oneStrength[] = {1};
		assert(pc_p2_breadbug_contest_update(h, 0.0f, one, oneStrength, 1) == 0); // Held
	}
	assert(twoCarriers(h, 0.1f) == 1); // Stolen
	assert(pc_p2_breadbug_contest_result(h) == 1);
	assert(pc_p2_breadbug_contest_grant(h, "p2-preview", "g187", "contest") == 1);  // Granted
	assert(pc_p2_breadbug_contest_receipt_granted(h));
	assert(pc_p2_breadbug_contest_grant(h, "p2-preview", "g187", "contest") == 2);  // Duplicate (latch)

	// interrupt() / onOwnerDied() release a non-stolen contest to its source.
	const int hInt = pc_p2_breadbug_contest_create(38, 0, "nest:187", 1, 2, 0.5f, 1, 0);
	pc_p2_breadbug_contest_begin(hInt, 0.0f);
	pc_p2_breadbug_contest_interrupt(hInt);
	assert(pc_p2_breadbug_contest_result(hInt) == 2);
	assert(pc_p2_breadbug_contest_reason(hInt) == 1); // Interrupted
	const int hDie = pc_p2_breadbug_contest_create(38, 0, "nest:187", 1, 2, 0.5f, 1, 0);
	pc_p2_breadbug_contest_begin(hDie, 0.0f);
	pc_p2_breadbug_contest_owner_died(hDie);
	assert(pc_p2_breadbug_contest_reason(hDie) == 2); // OwnerDied

	// Durable exactly-once across reopen (process restart / revisit model): close
	// the ledger and reopen it from disk; the persisted grant is never re-granted.
	pc_p2_breadbug_contest_close();
	assert(pc_p2_breadbug_contest_open(path.c_str()));
	const int hRe = pc_p2_breadbug_contest_create(38, 0, "nest:187", 1, 2, 0.5f, 1, 0);
	pc_p2_breadbug_contest_begin(hRe, 0.0f);
	assert(twoCarriers(hRe, 0.0f) == 1);
	assert(pc_p2_breadbug_contest_grant(hRe, "p2-preview", "g187", "contest") == 2); // Duplicate across reopen
	pc_p2_breadbug_contest_close();

	std::remove(path.c_str());
	std::printf("PASS p2_breadbug_contest_consumer_test\n");
	return 0;
}

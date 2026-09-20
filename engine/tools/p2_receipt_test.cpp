#include "pc_p2_receipt.h"

#include <cassert>
#include <cstdio>
#include <filesystem>
#include <stdexcept>
#include <string>
#include <vector>

using namespace P2Receipt;

template <class F> bool throws(F f)
{
	try {
		f();
	} catch (const std::runtime_error&) {
		return true;
	}
	return false;
}

int main(int argc, char** argv)
{
	assert(argc == 2);
	(void)argc;
	std::filesystem::path directory = argv[1];
	std::filesystem::remove_all(directory);
	std::filesystem::create_directories(directory);

	// Token validation mirrors the Python identity/coordinate contract.
	assert(identity("corpse:floor1:5000") == "corpse:floor1:5000");
	assert(throws([] { identity("bad id"); }));
	assert(throws([] { identity(""); }));
	assert(throws([] { coordinate(std::string(129, 'a')); }));

	// Exactly-once in memory, stable across reload.
	MemoryReceiptPersistence memory;
	ReceiptLedger ledger(memory);
	assert(ledger.grant("seed1", "corpse:1", "slot7", "enc0"));
	assert(!ledger.grant("seed1", "corpse:1", "slot7", "enc0"));
	assert(ledger.size() == 1);
	ledger.reload();
	assert(ledger.has("seed1", "corpse:1", "slot7", "enc0"));
	assert(!ledger.grant("seed1", "corpse:1", "slot7", "enc0")); // not re-granted
	assert(ledger.grant("seed1", "corpse:2", "slot8", "enc0"));  // genuinely new
	assert(ledger.size() == 2);

	// A different encounter is a genuinely new grant event.
	assert(ledger.grant("seed1", "corpse:1", "slot7", "enc1"));

	// Durable ordinary sidecar: a fresh ledger over the same file sees prior
	// receipts and refuses to repeat them (process restart).
	const std::string file = (directory / "receipts.txt").string();
	{
		FileReceiptPersistence disk(file);
		ReceiptLedger first(disk);
		assert(first.size() == 0);
		assert(first.grant("seedX", "treasure:dia_a_red", "actor3", "enc0"));
		assert(!first.grant("seedX", "treasure:dia_a_red", "actor3", "enc0"));
	}
	{
		FileReceiptPersistence disk(file);
		ReceiptLedger restarted(disk);
		assert(restarted.size() == 1);
		assert(!restarted.grant("seedX", "treasure:dia_a_red", "actor3", "enc0"));
		assert(restarted.grant("seedX", "treasure:dia_a_red", "actor4", "enc0"));
	}

	// Corrupt durable state is rejected rather than silently reset.
	const std::string corrupt = (directory / "corrupt.txt").string();
	{
		FILE* handle = std::fopen(corrupt.c_str(), "wb");
		assert(handle);
		const char* text = "P2_RECEIPTS_1\na b c d\na b c d\n";
		assert(std::fwrite(text, 1, std::string(text).size(), handle) == std::string(text).size());
		std::fclose(handle);
	}
	assert(throws([&] {
		FileReceiptPersistence disk(corrupt);
		std::vector<Key> keys;
		disk.load(keys);
	}));

	// A partial last row must not disappear merely because parsing reached EOF.
	for (const char* tail : {"a", "a b", "a b c", "a b c\n"}) {
		{ std::ofstream output(corrupt); output << "P2_RECEIPTS_1\na b c d\n" << tail; }
		assert(throws([&] { FileReceiptPersistence disk(corrupt); ReceiptLedger ledger(disk); }));
	}

	// Descriptor validation and ordinary/pod reconciliation.
	Descriptor corpse;
	corpse.identity = "corpse:floor1:5000";
	corpse.family = "lane-13-bulborbs";
	corpse.drop = "corpse";
	corpse.ledger = Ledger::Ap;
	const Descriptor valid = validateDescriptor(corpse);
	assert(valid.identity == corpse.identity);
	assert(throws([] {
		Descriptor bad;
		bad.version = "nope";
		bad.identity = "x";
		bad.family = "f";
		bad.drop = "corpse";
		validateDescriptor(bad);
	}));
	assert(throws([] {
		Descriptor bad;
		bad.identity = "x";
		bad.family = "f";
		bad.drop = "coin";
		validateDescriptor(bad);
	}));

	const ReconcileResult ok = reconcileOrdinary({valid}, {"corpse:floor1:5000"});
	assert(ok.ok);
	assert(ok.ordinarySources.size() == 1);
	assert(ok.missingSources.empty());

	const ReconcileResult missing = reconcileOrdinary({valid}, {"corpse:floor1:5000", "treasure:dia_blue"});
	assert(!missing.ok);
	assert(missing.missingSources.size() == 1 && missing.missingSources[0] == "treasure:dia_blue");

	Descriptor pod = valid;
	pod.identity = "corpse:floor1:5000";
	pod.ledger = Ledger::Pod;
	assert(throws([&] { reconcileOrdinary({pod}, {"corpse:floor1:5000"}); }));

	std::printf("PASS p2_receipt_test\n");
	std::filesystem::remove_all(directory);
	return 0;
}

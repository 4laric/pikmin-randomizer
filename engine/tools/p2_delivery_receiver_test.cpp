#include "pc_p2_delivery.h"

#include <cassert>
#include <cstdio>
#include <filesystem>
#include <string>
#include <vector>

#ifdef _WIN32
#include <process.h>
inline int currentPid() { return _getpid(); }
#else
#include <unistd.h>
inline int currentPid() { return static_cast<int>(getpid()); }
#endif

using namespace P2Delivery;

template <class F> bool throws(F f)
{
	try {
		f();
	} catch (const std::runtime_error&) {
		return true;
	}
	return false;
}

int main()
{
	// Consumer cohort: Snow Bulborb (YellowKochappy, source_id 45) and Dwarf
	// Orange Bulborb (BlueKochappy, source_id 44), both bound to a P1-proxy
	// TEKI_Chappy (type 3) host in the current family modules.
	constexpr unsigned kSnow = 45;
	constexpr unsigned kDwarfOrange = 44;
	constexpr int kChappyProxy = 3; // TEKI_Chappy
	constexpr bool kP1Proxy = true;
	constexpr bool kP2Source = false;

	// (1) The P2-source vocabulary never collides with the P1-proxy vocabulary,
	// and neither is "corpse:"-prefixed (so an ordinary key never pollutes the
	// Pod receipt count).
	assert(p2SourceIdentity(kSnow, 1) != p1ProxyIdentity(kChappyProxy, 1));
	assert(p2SourceIdentity(kDwarfOrange, 1) != p1ProxyIdentity(kChappyProxy, 1));
	assert(p2SourceIdentity(3, 1) != p1ProxyIdentity(3, 1));
	assert(p2SourceIdentity(kSnow, 1) == "onion:p2:45:1");
	assert(p1ProxyIdentity(kChappyProxy, 1) == "onion:p1:3:1");
	assert(p2SourceIdentity(kSnow, 1).rfind("corpse:", 0) != 0);
	assert(p1ProxyIdentity(kChappyProxy, 1).rfind("corpse:", 0) != 0);

	// (1b) The P2 path refuses an unbound source id instead of silently crediting
	// the P1-proxy check.
	{
		P2Receipt::MemoryReceiptPersistence memory;
		P2Receipt::ReceiptLedger ledger(memory);
		DeliveryReceiver receiver(ledger);
		assert(throws([&] { (void)receiver.identity(0, kChappyProxy, 1, kP2Source); }));
		assert(!throws([&] { (void)receiver.identity(0, kChappyProxy, 1, kP1Proxy); }));
	}

	// (2) Exactly-once within a single ledger; a different generator is new.
	{
		P2Receipt::MemoryReceiptPersistence memory;
		P2Receipt::ReceiptLedger ledger(memory);
		DeliveryReceiver receiver(ledger);
		assert(receiver.deliver("seed-a", kSnow, kChappyProxy, 1, 77, "tutorial_1:floor1", kP2Source));
		assert(!receiver.deliver("seed-a", kSnow, kChappyProxy, 1, 77, "tutorial_1:floor1", kP2Source));
		assert(receiver.delivered("seed-a", kSnow, kChappyProxy, 1, 77, "tutorial_1:floor1", kP2Source));
		assert(receiver.deliver("seed-a", kSnow, kChappyProxy, 1, 78, "tutorial_1:floor1", kP2Source));
	}

	// (3) Exactly-once across process restart over the durable sidecar. The temp
	// directory carries the pid so parallel CTest jobs never collide.
	const auto dir = std::filesystem::temp_directory_path()
		/ ("p2-delivery-receiver-test-" + std::to_string(currentPid()));
	std::filesystem::create_directories(dir);
	const std::string file = (dir / "receipts.txt").string();
	{
		P2Receipt::FileReceiptPersistence disk(file);
		P2Receipt::ReceiptLedger ledger(disk);
		DeliveryReceiver receiver(ledger);
		assert(receiver.deliver("seed-a", kSnow, kChappyProxy, 1, 77, "tutorial_1:floor1", kP2Source));
	}
	{
		P2Receipt::FileReceiptPersistence disk(file);
		P2Receipt::ReceiptLedger restarted(disk);
		DeliveryReceiver receiver(restarted);
		assert(!receiver.deliver("seed-a", kSnow, kChappyProxy, 1, 77, "tutorial_1:floor1", kP2Source));
		assert(receiver.delivered("seed-a", kSnow, kChappyProxy, 1, 77, "tutorial_1:floor1", kP2Source));
		assert(receiver.deliver("seed-a", kSnow, kChappyProxy, 1, 78, "tutorial_1:floor1", kP2Source));
		assert(receiver.deliver("seed-a", kDwarfOrange, kChappyProxy, 1, 77, "tutorial_1:floor1", kP2Source));
	}

	// (4) Delivering a P2 source never marks the P1-proxy check, and vice versa.
	{
		P2Receipt::MemoryReceiptPersistence memory;
		P2Receipt::ReceiptLedger ledger(memory);
		DeliveryReceiver receiver(ledger);
		assert(receiver.deliver("seed-a", kSnow, kChappyProxy, 1, 77, "tutorial_1:floor1", kP2Source));
		assert(!receiver.delivered("seed-a", 0, kChappyProxy, 1, 77, "tutorial_1:floor1", kP1Proxy));
		assert(receiver.deliver("seed-a", 0, kChappyProxy, 1, 77, "tutorial_1:floor1", kP1Proxy));
		assert(!receiver.delivered("seed-a", kSnow, kChappyProxy, 1, 77, "tutorial_1:floor2", kP2Source));
	}

	// (5) reconcileOrdinary: both cohort sources are ordinary; a pod covering
	// an ordinary expected check is refused (pod never leaks into ordinary).
	{
		const auto desc44 = sourceDescriptor(kDwarfOrange, 1, "lane-13-bulborbs");
		const auto desc45 = sourceDescriptor(kSnow, 1, "lane-13-bulborbs");
		const auto ok = P2Receipt::reconcileOrdinary(
			{desc44, desc45}, {p2SourceIdentity(kDwarfOrange, 1), p2SourceIdentity(kSnow, 1)});
		assert(ok.ok);
		assert(ok.ordinarySources.size() == 2);
		assert(ok.missingSources.empty());

		auto pod45 = sourceDescriptor(kSnow, 1, "lane-13-bulborbs");
		pod45.ledger = P2Receipt::Ledger::Pod;
		assert(throws([&] {
			P2Receipt::reconcileOrdinary({desc44, pod45},
				{p2SourceIdentity(kDwarfOrange, 1), p2SourceIdentity(kSnow, 1)});
		}));
	}

	std::filesystem::remove_all(dir);
	std::printf("PASS p2_delivery_receiver_test\n");
	return 0;
}

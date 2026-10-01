#include "pc_p2_delivery_host.h"
#include <cassert>
#include <filesystem>
#include <fstream>

#ifdef _WIN32
#include <process.h>
inline int currentPid() { return _getpid(); }
#else
#include <unistd.h>
inline int currentPid() { return static_cast<int>(getpid()); }
#endif

int main()
{
    using R = P2DeliveryHostResult;
    namespace fs = std::filesystem;
    const auto dir = fs::temp_directory_path()
        / ("p2-delivery-host-test-" + std::to_string(currentPid()));
    fs::create_directories(dir);
    const auto path = (dir / "receipts.txt").string();
    fs::remove(path);

    // Unopened / bad arguments fail closed.
    P2DeliveryHostHandle h = pc_p2_delivery_host_open(path.c_str());
    assert(h != nullptr);
    assert(pc_p2_delivery_host_path(h) == path);
    assert(pc_p2_delivery_host_deliver(h, nullptr, 45, 3, 1, 77, "corpse") == R::Error);
    assert(pc_p2_delivery_host_deliver(h, "s", 0, 3, 1, 77, "corpse") == R::Error);

    // First delivery grants; a repeat is a durable duplicate.
    assert(pc_p2_delivery_host_deliver(h, "seed-a", 45, 3, 1, 77, "corpse") == R::Granted);
    assert(pc_p2_delivery_host_deliver(h, "seed-a", 45, 3, 1, 77, "corpse") == R::Duplicate);
    assert(pc_p2_delivery_host_deliver(h, "seed-a", 44, 3, 1, 77, "corpse") == R::Granted);

    // Process restart over the same path never re-grants.
    pc_p2_delivery_host_close(h);
    h = pc_p2_delivery_host_open(path.c_str());
    assert(h != nullptr);
    assert(pc_p2_delivery_host_deliver(h, "seed-a", 45, 3, 1, 77, "corpse") == R::Duplicate);
    assert(pc_p2_delivery_host_deliver(h, "seed-a", 45, 3, 1, 78, "corpse") == R::Granted);

    // A P1-proxy delivery (sourceId 0) is never accepted here (p1Proxy always false).
    assert(pc_p2_delivery_host_deliver(h, "seed-a", 0, 3, 1, 77, "corpse") == R::Error);

    // Corrupt persisted state must be rejected, not silently replayed.
    pc_p2_delivery_host_close(h);
    { std::ofstream out(path); out << "P2_RECEIPTS_1\ns truncated\n"; }
    assert(pc_p2_delivery_host_open(path.c_str()) == nullptr);

    fs::remove(path);
    fs::remove(dir);
    return 0;
}

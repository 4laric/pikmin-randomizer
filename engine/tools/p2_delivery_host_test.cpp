#include "pc_p2_delivery_host.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string>

#ifdef _WIN32
#include <process.h>
inline int currentPid() { return _getpid(); }
#else
#include <unistd.h>
inline int currentPid() { return static_cast<int>(getpid()); }
#endif

static std::string journal(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    std::ostringstream out;
    out << in.rdbuf();
    return out.str();
}

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

    // Both endpoint orderings persist one row, unchanged after close/reopen.
    for (const char* first : {"kill", "corpse"}) {
        const auto file = (dir / (std::string(first) + "-first.txt")).string();
        auto actor = pc_p2_delivery_host_open(file.c_str());
        assert(actor != nullptr);
        assert(pc_p2_delivery_host_deliver(actor, "seed", 31, 4, 0, 77, first) == R::Granted);
        const auto saved = journal(file);
        assert(saved == "P2_RECEIPTS_1\nseed onion:p2:31:0 g77 corpse\n");
        pc_p2_delivery_host_close(actor);
        actor = pc_p2_delivery_host_open(file.c_str());
        assert(actor != nullptr);
        for (const char* endpoint : {"kill", "corpse"}) {
            assert(pc_p2_delivery_host_deliver(actor, "seed", 31, 4, 0, 77, endpoint) == R::Duplicate);
            assert(journal(file) == saved);
        }
        // A different slot is still a different actor; unrelated encounter
        // coordinates keep their pre-existing independent grant semantics.
        assert(pc_p2_delivery_host_deliver(actor, "seed", 31, 4, 0, 78, "kill") == R::Granted);
        assert(pc_p2_delivery_host_deliver(actor, "seed", 31, 4, 0, 77, "other") == R::Granted);
        pc_p2_delivery_host_close(actor);
        fs::remove(file);
    }
    // Accept each historical endpoint spelling without modifying its bytes.
    // Legacy corpse rows require no migration; pre-release kill rows also
    // consume the same actor when the corrected endpoint is first called.
    for (const char* legacy : {"corpse", "kill"}) {
        const auto file = (dir / (std::string("legacy-") + legacy + ".txt")).string();
        { std::ofstream out(file); out << "P2_RECEIPTS_1\nseed onion:p2:31:0 g77 " << legacy << "\n"; }
        const auto saved = journal(file);
        auto actor = pc_p2_delivery_host_open(file.c_str());
        assert(actor != nullptr);
        assert(pc_p2_delivery_host_deliver(actor, "seed", 31, 4, 0, 77, "kill") == R::Duplicate);
        assert(pc_p2_delivery_host_deliver(actor, "seed", 31, 4, 0, 77, "corpse") == R::Duplicate);
        assert(journal(file) == saved);
        pc_p2_delivery_host_close(actor);
        fs::remove(file);
    }

    // Corrupt persisted state must be rejected, not silently replayed.
    pc_p2_delivery_host_close(h);
    { std::ofstream out(path); out << "P2_RECEIPTS_1\ns truncated\n"; }
    assert(pc_p2_delivery_host_open(path.c_str()) == nullptr);

    fs::remove(path);
    fs::remove(dir);
    return 0;
}

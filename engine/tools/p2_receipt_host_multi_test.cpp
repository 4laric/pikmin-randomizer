#include "pc_p2_receipt_host.h"
#include <cassert>
#include <filesystem>

#ifdef _WIN32
#include <process.h>
inline int currentPid() { return _getpid(); }
#else
#include <unistd.h>
inline int currentPid() { return static_cast<int>(getpid()); }
#endif

int main()
{
    // Lane 06 per-consumer ledger contract: two consumers (a flora-shape consumer
    // on p2-flora-receipts.txt and a kogane-shape consumer on p2-kogane-receipts.txt)
    // hold independent handles; one consumer's open/grant/close never redirects or
    // disables the other's ledger. Mirrors the lane 17/22 send-back.
    using R = P2ReceiptHostResult;
    namespace fs = std::filesystem;
    const auto dir = fs::temp_directory_path()
        / ("p2-receipt-host-multi-test-" + std::to_string(currentPid()));
    fs::create_directories(dir);
    const auto floraPath = (dir / "p2-flora-receipts.txt").string();
    const auto koganePath = (dir / "p2-kogane-receipts.txt").string();
    fs::remove(floraPath);
    fs::remove(koganePath);

    P2ReceiptHostHandle flora = pc_p2_receipt_host_open(floraPath.c_str());
    P2ReceiptHostHandle kogane = pc_p2_receipt_host_open(koganePath.c_str());
    assert(flora != nullptr && kogane != nullptr && flora != kogane);
    assert(pc_p2_receipt_host_path(flora) == floraPath);
    assert(pc_p2_receipt_host_path(kogane) == koganePath);

    // Each consumer grants its own identity to its own ledger.
    assert(pc_p2_receipt_host_grant(flora, "seed", "flora-pelplant:7", "g7", "onion") == R::Granted);
    assert(pc_p2_receipt_host_grant(kogane, "seed", "kogane:9", "g9", "onion") == R::Granted);

    // Closing one consumer must not disable the other.
    pc_p2_receipt_host_close(kogane);
    assert(pc_p2_receipt_host_grant(flora, "seed", "flora-pelplant:7", "g7", "onion") == R::Duplicate);
    assert(pc_p2_receipt_host_grant(flora, "seed", "flora-pelplant:8", "g8", "onion") == R::Granted);

    // Re-opening a consumer's own path returns its (surviving) durable state.
    kogane = pc_p2_receipt_host_open(koganePath.c_str());
    assert(kogane != nullptr);
    assert(pc_p2_receipt_host_grant(kogane, "seed", "kogane:9", "g9", "onion") == R::Duplicate);
    assert(pc_p2_receipt_host_grant(kogane, "seed", "kogane:10", "g10", "onion") == R::Granted);

    // Distinct ledgers never see each other's grants.
    assert(pc_p2_receipt_host_grant(flora, "seed", "kogane:9", "g9", "onion") == R::Granted);
    assert(pc_p2_receipt_host_grant(kogane, "seed", "flora-pelplant:7", "g7", "onion") == R::Granted);

    pc_p2_receipt_host_close(flora);
    pc_p2_receipt_host_close(kogane);
    fs::remove(floraPath);
    fs::remove(koganePath);
    fs::remove(dir);
    return 0;
}

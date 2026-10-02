#include "pc_p2_receipt_host.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <cstdlib>
#include <string>

#ifdef _WIN32
#include <process.h>
inline int currentPid() { return _getpid(); }
#else
#include <unistd.h>
#include <sys/wait.h>
inline int currentPid() { return static_cast<int>(getpid()); }
#endif

static int role = 0;
bool pc_netplay_session_active() { return role != 0; }
bool pc_netplay_is_host() { return role == 1; }
bool pc_netplay_randstate_stream_enabled() { return role != 0; }

int main(int argc, char** argv)
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
    if (argc == 3 && std::string(argv[1]) == "--host-fatal") {
        role = 1;
        const std::string fatalPath = argv[2];
        fs::remove(fatalPath);
        auto host = pc_p2_receipt_host_open(fatalPath.c_str());
        assert(host != nullptr);
        fs::create_directory(fatalPath + ".tmp");
        pc_p2_receipt_host_grant(host, "seed", "reward", "g1", "onion");
        return 99; // Only the production fatal persistence path may return 2.
    }
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

    // A cold malformed client file must remain refused on every retry. It must
    // never populate the process cache from a partial parse.
    role = 2;
    const std::string clientPath = (dir / "client.txt").string();
    { std::ofstream out(clientPath); out << "P2_RECEIPTS_1\nseed truncated\n"; }
    assert(pc_p2_receipt_host_open(clientPath.c_str()) == nullptr);
    assert(pc_p2_receipt_host_open(clientPath.c_str()) == nullptr);
    { std::ofstream out(clientPath); out << "P2_RECEIPTS_1\nseed reward g1 onion\n"; }
    auto client = pc_p2_receipt_host_open(clientPath.c_str());
    assert(client != nullptr);
    assert(pc_p2_receipt_host_grant(client, "seed", "reward", "g1", "onion") == R::Duplicate);
    assert(pc_p2_receipt_host_grant(client, "seed", "reward", "g2", "onion") == R::Granted);
    pc_p2_receipt_host_close(client);
    // Replace the original file with an invalid source: cached client reopen
    // must use its memory ledger, while an authoritative host must reject it.
    { std::ofstream out(clientPath); out << "invalid\n"; }
    client = pc_p2_receipt_host_open(clientPath.c_str());
    assert(client != nullptr && pc_p2_receipt_host_count(client) == 2);
    assert(pc_p2_receipt_host_grant(client, "seed", "reward", "g2", "onion") == R::Duplicate);
    assert(pc_p2_receipt_host_grant(client, "seed", "reward", "g3", "onion") == R::Granted);
    pc_p2_receipt_host_close(client);
    { std::ifstream in(clientPath); std::string untouched; in >> untouched; assert(untouched == "invalid"); }
    role = 1;
    assert(pc_p2_receipt_host_open(clientPath.c_str()) == nullptr);

    // Execute real host persistence failure in a separate process. Both a
    // crash and a returned Error instead of fatal exit 2 fail this oracle.
    const std::string fatalPath = (dir / "fatal.txt").string();
    const std::string command = "\"" + std::string(argv[0]) + "\" --host-fatal \"" + fatalPath + "\"";
 #ifdef _WIN32
    const intptr_t fatalResult = _spawnl(_P_WAIT, argv[0], argv[0], "--host-fatal", fatalPath.c_str(), nullptr);
    assert(fatalResult == 2);
#else
    const int fatalResult = std::system(command.c_str());
    assert(WIFEXITED(fatalResult) && WEXITSTATUS(fatalResult) == 2);
#endif
    fs::remove(fatalPath + ".tmp");
    fs::remove(fatalPath);
    fs::remove(clientPath);
    fs::remove(floraPath);
    fs::remove(koganePath);
    fs::remove(dir);
    return 0;
}

#include "pc_p2_receipt_host.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <string>

#ifdef _WIN32
#include <process.h>
inline int currentPid() { return _getpid(); }
#else
#include <unistd.h>
inline int currentPid() { return static_cast<int>(getpid()); }
#endif

int main()
{
    using R = P2ReceiptHostResult;
    namespace fs = std::filesystem;
    const auto dir = fs::temp_directory_path()
        / ("p2-receipt-host-test-" + std::to_string(currentPid()));
    fs::create_directories(dir);
    const auto path = (dir / "receipts.txt").string();
    fs::remove(path);

    // Unopened handles and bad arguments fail closed.
    P2ReceiptHostHandle a = pc_p2_receipt_host_open(path.c_str());
    assert(a != nullptr);
    assert(pc_p2_receipt_host_path(a) == path);
    assert(pc_p2_receipt_host_grant(a, nullptr, "r", "a", "onion") == R::Error);
    assert(pc_p2_receipt_host_grant(a, "s", "r", "a", "onion") == R::Granted);
    assert(pc_p2_receipt_host_grant(a, "s", "r", "a", "onion") == R::Duplicate);
    assert(pc_p2_receipt_host_count(a) == 1);

    // A closed handle is no longer live: grant/count resolve to Error/0 instead of
    // dereferencing a dangling host (closed-handle UB regression).
    P2ReceiptHostHandle closed = a;
    pc_p2_receipt_host_close(a);
    assert(pc_p2_receipt_host_path(closed) == nullptr);
    assert(pc_p2_receipt_host_grant(closed, "s", "r", "a", "onion") == R::Error);
    assert(pc_p2_receipt_host_count(closed) == 0);

    // Process restart over the same path reuses the durable state (never re-grants).
    a = pc_p2_receipt_host_open(path.c_str());
    assert(a != nullptr);
    assert(pc_p2_receipt_host_grant(a, "s", "r", "a", "onion") == R::Duplicate);
    assert(pc_p2_receipt_host_grant(a, "s", "r2", "a", "onion") == R::Granted);
    assert(pc_p2_receipt_host_count(a) == 2);

    // A directory at the temporary-file path forces a real persistence failure.
    fs::create_directory(path + ".tmp");
    assert(pc_p2_receipt_host_grant(a, "s", "r3", "a", "onion") == R::Error);
    fs::remove(path + ".tmp");
    assert(pc_p2_receipt_host_grant(a, "s", "r3", "a", "onion") == R::Granted);
    pc_p2_receipt_host_close(a);

    // Corrupt persisted state is rejected, not silently replayed.
    { std::ofstream out(path); out << "P2_RECEIPTS_1\ns truncated\n"; }
    assert(pc_p2_receipt_host_open(path.c_str()) == nullptr);

    // Stateless atomic write is unaffected by any ledger.
    fs::remove(path);
    assert(pc_p2_receipt_host_atomic_write(path.c_str(), "first"));
    assert(pc_p2_receipt_host_atomic_write(path.c_str(), "second"));
    // A directory at the temporary-file path forces a real write failure and must
    // leave the last good file untouched.
    fs::create_directory(path + ".tmp");
    assert(!pc_p2_receipt_host_atomic_write(path.c_str(), "lost"));
    fs::remove(path + ".tmp");
    { std::ifstream in(path); std::string value; in >> value; assert(value == "second"); }

    fs::remove(path);
    fs::remove(dir);
    return 0;
}

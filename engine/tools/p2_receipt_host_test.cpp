#include "pc_p2_receipt_host.h"
#include <cassert>
#include <filesystem>
#include <fstream>
int main() {
    using R = P2ReceiptHostResult;
    namespace fs = std::filesystem;
    const auto dir = fs::current_path() / "p2-receipt-host-test-data";
    fs::create_directory(dir);
    const auto path = (dir / "receipts.txt").string();
    fs::remove(path);
    assert(pc_p2_receipt_host_grant("s", "r", "a", "onion") == R::Error);
    assert(pc_p2_receipt_host_open(path.c_str()));
    assert(pc_p2_receipt_host_grant(nullptr, "r", "a", "onion") == R::Error);
    assert(pc_p2_receipt_host_grant("s", "r", "a", "onion") == R::Granted);
    assert(pc_p2_receipt_host_grant("s", "r", "a", "onion") == R::Duplicate);
    pc_p2_receipt_host_close();
    assert(pc_p2_receipt_host_open(path.c_str()));
    assert(pc_p2_receipt_host_grant("s", "r", "a", "onion") == R::Duplicate);
    // A directory at the temporary-file path forces an actual persistence failure.
    fs::create_directory(path + ".tmp");
    assert(pc_p2_receipt_host_grant("s", "r2", "a", "onion") == R::Error);
    fs::remove(path + ".tmp");
    assert(pc_p2_receipt_host_grant("s", "r2", "a", "onion") == R::Granted);
    pc_p2_receipt_host_close();
    { std::ofstream out(path); out << "P2_RECEIPTS_1\ns truncated\n"; }
    assert(!pc_p2_receipt_host_open(path.c_str()));
    assert(!pc_p2_receipt_host_ready());
    fs::remove(path);
    assert(pc_p2_receipt_host_atomic_write(path.c_str(), "first"));
    assert(pc_p2_receipt_host_atomic_write(path.c_str(), "second"));
    fs::create_directory(path + ".tmp");
    assert(!pc_p2_receipt_host_atomic_write(path.c_str(), "lost"));
    { std::ifstream in(path); std::string value; in >> value; assert(value == "second"); }
    fs::remove(path + ".tmp"); fs::remove(path); fs::remove(dir);
}

#include "pc_p2_receipt_host.h"
#include "pc_p2_receipt.h"
#include <memory>
#include <string>

namespace {
std::unique_ptr<P2Receipt::FileReceiptPersistence> persistence;
std::unique_ptr<P2Receipt::ReceiptLedger> ledger;
} // namespace

bool pc_p2_receipt_host_open(const char* path)
{
	try {
		persistence = std::make_unique<P2Receipt::FileReceiptPersistence>(path ? path : "p2-receipts.txt");
		ledger = std::make_unique<P2Receipt::ReceiptLedger>(*persistence);
	} catch (...) {
		ledger.reset();
		persistence.reset();
		return false;
	}
	return true;
}

bool pc_p2_receipt_host_ready() { return ledger != nullptr; }

bool pc_p2_receipt_host_valid(const char* value)
{
	return value && P2Receipt::validToken(value, 128);
}

P2ReceiptHostResult pc_p2_receipt_host_grant(const char* seed, const char* reward, const char* slotOrActor, const char* encounter)
{
	if (!ledger || !seed || !reward || !slotOrActor || !encounter) {
		return P2ReceiptHostResult::Error;
	}
	try {
		return ledger->grant(seed, reward, slotOrActor, encounter)
		    ? P2ReceiptHostResult::Granted : P2ReceiptHostResult::Duplicate;
	} catch (...) {
		return P2ReceiptHostResult::Error;
	}
}

void pc_p2_receipt_host_close()
{
	ledger.reset();
	persistence.reset();
}

bool pc_p2_receipt_host_atomic_write(const char* path, const char* data)
{
    if (!path || !data) return false;
    const std::string temporary = std::string(path) + ".tmp";
    { std::ofstream out(temporary, std::ios::binary | std::ios::trunc);
      if (!out) return false;
      out << data; out.flush(); if (!out) return false; }
#ifdef _WIN32
    return ::MoveFileExA(temporary.c_str(), path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
#else
    return std::rename(temporary.c_str(), path) == 0;
#endif
}

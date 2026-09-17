// Receipt-ledger endpoint translation unit (lane overworld-yakushima-receipt-ledger-endpoint, #749).
//
// The policy implementation is header-inline in pc_p2_receipt_ledger_endpoint.h;
// this TU exists so the integrator can wire the module into PC_PORT_SOURCES
// under #186 review (follow-on). It is never linked by this lane.
#include "pc_p2_receipt_ledger_endpoint.h"

const char* kP2ReceiptLedgerEndpointModule =
    "pc_p2_receipt_ledger_endpoint v1 (header-inline policy; TU wired on #186 review)";

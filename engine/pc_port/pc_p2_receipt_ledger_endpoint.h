#pragma once
// Native receipt-ledger endpoint binding for overworld runtime (#749).
//
// Engine-free policy module binding the four #724 pins behind one ordered
// API. It performs NO engine calls and edits NO engine file: the engine hook
// sites stay exactly where the #724 discovery pinned them, and landing any
// hook requires explicit #186 review (recorded in the lane handoff; never
// assumed). Family FSM work, a second ledger and divergent treasure
// implementations are all out of scope.
//
// Pinned call sites (read-only references from the #724 discovery packet):
//   1. Onyon::isSuckReady :195 ............ stage SuckReady (gate check)
//   2. InteractSuckDone::actOnyon :403 ..... stage ActOnyon (suck action)
//   3. PlayData::obtainPellet_Main :800 .... stage ObtainPellet (payload)
//   4. ledger write :832 ................... stage LedgerWrite (durable grant)
//
// Contract: the four stages must occur in order per receipt attempt. Any
// out-of-order, repeated or malformed stage is refused with a marker and
// leaves the endpoint state unchanged (fail-closed). The durable grant goes
// through the caller-supplied P2Receipt::ReceiptLedger, so exactly-once and
// persistence semantics are inherited, never reimplemented.
//
// Stdlib only (plus pc_p2_receipt.h, also engine-free).
#include "pc_p2_receipt.h"

#include <cstdio>
#include <string>

namespace P2ReceiptEndpoint {

// Stage names double as marker fields; order is the contract.
inline const char* stageName(int stage)
{
    switch (stage) {
    case 0: return "Idle";
    case 1: return "SuckReady";
    case 2: return "ActOnyon";
    case 3: return "ObtainPellet";
    default: return "Unknown";
    }
}

class Endpoint {
public:
    Endpoint(P2Receipt::ReceiptLedger& ledger, const std::string& seed)
        : mLedger(ledger), mSeed(P2Receipt::coordinate(seed)), mStage(0)
    {
    }

    int stage() const { return mStage; }

    // Pin 1 (Onyon::isSuckReady :195): gate check for one receipt identity.
    bool suckReady(const std::string& identity)
    {
        if (mStage != 0) {
            return refuse("suckReady", "not-idle");
        }
        try {
            mIdentity = P2Receipt::identity(identity);
        } catch (const std::runtime_error&) {
            return refuse("suckReady", "bad-identity");
        }
        mStage = 1;
        std::printf("P2_RECEIPT_ENDPOINT stage=SuckReady identity=%s\n",
                    mIdentity.c_str());
        std::fflush(stdout);
        return true;
    }

    // Pin 2 (InteractSuckDone::actOnyon :403): bind the slot/actor.
    bool actOnyon(const std::string& slotOrActor)
    {
        if (mStage != 1) {
            return refuse("actOnyon", "order");
        }
        try {
            mSlot = P2Receipt::coordinate(slotOrActor);
        } catch (const std::runtime_error&) {
            return refuse("actOnyon", "bad-slot");
        }
        mStage = 2;
        std::printf("P2_RECEIPT_ENDPOINT stage=ActOnyon identity=%s slot=%s\n",
                    mIdentity.c_str(), mSlot.c_str());
        std::fflush(stdout);
        return true;
    }

    // Pin 3 (PlayData::obtainPellet_Main :800): bind the encounter payload.
    bool obtainPellet(const std::string& encounter)
    {
        if (mStage != 2) {
            return refuse("obtainPellet", "order");
        }
        try {
            mEncounter = P2Receipt::coordinate(encounter);
        } catch (const std::runtime_error&) {
            return refuse("obtainPellet", "bad-encounter");
        }
        mStage = 3;
        std::printf("P2_RECEIPT_ENDPOINT stage=ObtainPellet identity=%s\n",
                    mIdentity.c_str());
        std::fflush(stdout);
        return true;
    }

    // Pin 4 (ledger write :832): durable exactly-once grant, then reset.
    // Returns 1 granted, 2 duplicate (refused repeat), 0 contract refusal.
    int ledgerWrite()
    {
        if (mStage != 3) {
            refuse("ledgerWrite", "order");
            return 0;
        }
        const bool granted = mLedger.grant(mSeed, mIdentity, mSlot, mEncounter);
        std::printf("P2_RECEIPT_ENDPOINT stage=LedgerWrite identity=%s granted=%d%s\n",
                    mIdentity.c_str(), int(granted),
                    granted ? "" : " duplicate=1");
        std::fflush(stdout);
        mStage = 0;
        mIdentity.clear();
        mSlot.clear();
        mEncounter.clear();
        return granted ? 1 : 2;
    }

private:
    bool refuse(const char* stage, const char* reason)
    {
        std::printf("P2_RECEIPT_ENDPOINT_REFUSED stage=%s reason=%s state=%s\n",
                    stage, reason, stageName(mStage));
        std::fflush(stdout);
        return false;
    }

    P2Receipt::ReceiptLedger& mLedger;
    std::string mSeed;
    std::string mIdentity;
    std::string mSlot;
    std::string mEncounter;
    int mStage;
};

} // namespace P2ReceiptEndpoint

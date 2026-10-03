#pragma once
#include <cstddef>
#include <cstdint>

// Fixture diagnostic state only. Ordinary builds never arm this observer.
// Identities are sampled while callers own live native objects; stored pointer
// values are opaque receipts and are never dereferenced here or later. Receipt
// assignment is FIFO demand accounting for the native fungible pending counter,
// not a claim that native sprouts retain individual pellet-source bindings.
struct PcGoalBirthLedger {
    static constexpr std::size_t Capacity=128;
    enum class Kind { Request, Emitted, Stored, BootEmitted };
    struct Event {
        Kind kind=Kind::Request;
        std::uint64_t frame=0,receipt=0;
        std::uintptr_t onion=0,source=0,head=0;
        unsigned model=0;
        int color=-1,maturity=-1,requested=0,pendingBefore=0,pendingAfter=0;
    };
    struct Demand {
        std::uintptr_t onion=0;
        std::uint64_t receipt=0;
        int color=-1,remaining=0;
    };
    struct Conversion {
        std::uint64_t frame=0;
        std::uintptr_t bud=0,input=0,head=0;
        unsigned generator=0;
        int inputSpecies=-1,inputMaturity=-1;
    };
    Event events[Capacity]{};
    Demand demands[Capacity]{};
    Conversion conversions[Capacity]{};
    std::size_t eventCount=0,demandCount=0;
    std::size_t conversionCount=0;
    std::uint64_t lastFrame=0,nextReceipt=1;
    int emitted[3]{},stored[3]{},bootEmitted[3]{};
    bool armed=false,complete=true;

    bool begin() {
        if(armed){complete=false;return false;}
        armed=true;return true;
    }
    void refuse() { if(armed)complete=false; }
    bool ready(std::uint64_t frame,std::uintptr_t onion,int color) {
        if(!armed)return false;
        if(!complete || !onion || color<0 || color>=3 || frame<lastFrame || eventCount==Capacity) {
            complete=false;return false;
        }
        lastFrame=frame;return true;
    }
    int pending(std::uintptr_t onion) const {
        int sum=0;
        for(std::size_t i=0;i<demandCount;++i)if(demands[i].onion==onion)sum+=demands[i].remaining;
        return sum;
    }
    void request(std::uint64_t frame,std::uintptr_t onion,std::uintptr_t source,unsigned model,
                 int color,int requested,int before,int after) {
        if(!ready(frame,onion,color))return;
        if(!source || requested<0 || requested>100000 || before<0 || before>100000
           || after<0 || after>100000 || after-before!=requested || before!=pending(onion)
           || demandCount==Capacity) {complete=false;return;}
        const auto receipt=nextReceipt++;
        demands[demandCount++]={onion,receipt,color,requested};
        events[eventCount++]={Kind::Request,frame,receipt,onion,source,0,model,color,-1,requested,before,after};
    }
    void birth(std::uint64_t frame,std::uintptr_t onion,int color,std::uintptr_t head,
               int before,int after,bool storedLeaf) {
        if(!ready(frame,onion,color))return;
        if(before<=0 || before>100000 || after!=before-1 || before!=pending(onion)
           || (storedLeaf?head!=0:head==0)) {complete=false;return;}
        Demand* demand=nullptr;
        for(std::size_t i=0;i<demandCount;++i)if(demands[i].onion==onion && demands[i].remaining>0) {
            demand=&demands[i];break;
        }
        if(!demand || demand->color!=color){complete=false;return;}
        --demand->remaining;
        ++(storedLeaf?stored[color]:emitted[color]);
        events[eventCount++]={storedLeaf?Kind::Stored:Kind::Emitted,frame,demand->receipt,onion,0,head,0,color,storedLeaf?0:-1,0,before,after};
    }
    void bootBirth(std::uint64_t frame,std::uintptr_t onion,int color,std::uintptr_t head) {
        if(!ready(frame,onion,color))return;
        if(!head || pending(onion)!=0){complete=false;return;}
        ++bootEmitted[color];
        events[eventCount++]={Kind::BootEmitted,frame,nextReceipt++,onion,0,head,0,color,-1,0,0,0};
    }
    void violetConversion(std::uint64_t frame,std::uintptr_t bud,unsigned generator,
                          std::uintptr_t input,std::uintptr_t head,int inputSpecies,int inputMaturity) {
        if(!armed)return;
        if(!complete || frame<lastFrame || !bud || !generator || !input || !head
           || input==head || inputSpecies<0 || inputSpecies>5 || inputMaturity<0 || inputMaturity>2
           || conversionCount==Capacity){complete=false;return;}
        lastFrame=frame;
        conversions[conversionCount++]={frame,bud,input,head,generator,inputSpecies,inputMaturity};
    }
    bool settled() const {
        if(!armed || !complete)return false;
        for(std::size_t i=0;i<demandCount;++i)if(demands[i].remaining)return false;
        return true;
    }
};

inline PcGoalBirthLedger pc_goal_birth_ledger;

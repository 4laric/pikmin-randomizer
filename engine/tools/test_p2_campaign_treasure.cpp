#include "pc_p2_campaign_treasure_state.h"
#include <cassert>
#include <iostream>

static p2treasure::Catalog sample() {
    p2treasure::Catalog catalog;
    for(int i=0; i<201; ++i) {
        p2treasure::Entry entry;
        entry.id = i==0 ? "dia_a_red" : "source_" + std::to_string(i);
        entry.kind="otakara";entry.classification=p2treasure::Classification::Campaign;
        entry.unique=true;entry.dictionary=i+1;entry.index=i;
        entry.value=i==0?180:50;entry.strength=1;entry.slots=3;
        catalog.entries.push_back(entry);
    }
    return catalog;
}
int main() {
    using namespace p2treasurestate;
    auto catalog=sample();const std::string source(64,'a');State ledger;
    assert(ledger.credit(catalog,"dia_a_red",180)==Credit::Invalid);
    assert(ledger.bind(source));assert(!ledger.bind(std::string(64,'b')));
    assert(ledger.credit(catalog,"unknown",180)==Credit::Invalid);
    assert(ledger.credit(catalog,"dia_a_red",181)==Credit::Invalid);
    assert(ledger.credit(catalog,"dia_a_red",180)==Credit::Added);
    assert(ledger.credit(catalog,"dia_a_red",180)==Credit::Duplicate);
    assert(ledger.credit(catalog,"source_200",50)==Credit::Added);
    const auto progress=ledger.progress(catalog,true);
    assert(progress.pokos==230 && progress.collected==2 && progress.available==201);
    const auto record=encode(ledger.snapshot());assert(record.size()==MaxRecordBytes);
    Snapshot decoded;assert(decode(record,catalog,source,decoded));
    State resumed;assert(resumed.restore(decoded,catalog,source));
    assert(resumed.seen(catalog,"dia_a_red") && resumed.seen(catalog,"source_200"));
    assert(resumed.credit(catalog,"source_200",50)==Credit::Duplicate);
    assert(resumed.progress(catalog,false).pokos==230);
    const auto before=encode(resumed.snapshot());
    for (const auto& bad : {record+" ", record.substr(1), std::string(1000,'x')}) {
        auto copy=decoded;assert(!decode(bad,catalog,source,copy));assert(encode(copy)==record);
    }
    auto bad=record;bad.back()='2';assert(!decode(bad,catalog,source,decoded)); // spare bit
    bad=record;bad.back()='A';assert(!decode(bad,catalog,source,decoded));
    bad=record;bad[6]='b';assert(!decode(bad,catalog,source,decoded)); // catalog identity
    assert(!decode(record,catalog,std::string(64,'b'),decoded));
    auto changed=sample();changed.entries[1].dictionary=1;
    assert(!resumed.restore(decoded,changed,source));assert(encode(resumed.snapshot())==before);
    changed=sample();changed.entries[1].classification=p2treasure::Classification::ModeOnly;
    assert(resumed.credit(changed,"source_1",50)==Credit::Invalid);
    auto invalid=decoded;invalid.bits.back()|=0x80;
    assert(!resumed.restore(invalid,catalog,source));assert(encode(resumed.snapshot())==before);
    for(int i=1;i<200;++i)assert(ledger.credit(catalog,"source_"+std::to_string(i),50)==Credit::Added);
    assert(ledger.progress(catalog,true).phase()==p2economy::Phase::Complete);
    // Rollback only comes from an authenticated enclosing card generation.
    assert(resumed.restore(decoded,catalog,source));assert(resumed.progress(catalog,true).collected==2);
    resumed.reset();assert(!resumed.active());assert(resumed.progress(catalog,true).pokos==180);
    std::cout<<"P2 treasure state codec/unique union controls PASS (synthetic, no gameplay claim)\n";
}

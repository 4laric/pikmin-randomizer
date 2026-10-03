#include "pc_p2_campaign_treasure_held_config.h"
#include <cassert>
#include <iostream>
static p2treasure::Catalog sample() {
    p2treasure::Catalog catalog;
    for(int i=0;i<201;++i) {
        p2treasure::Entry entry;entry.id=i==86?"watch":"sample_"+std::to_string(i);
        entry.dictionary=i+1;entry.kind=i<188?"otakara":"item";entry.index=i<188?i:i-188;
        if(i==73)entry.index=86;
        if(i==86)entry.index=73;
        entry.classification=p2treasure::Classification::Campaign;entry.unique=true;
        entry.value=i==86?110:50;entry.strength=i==86?30:1;entry.slots=i==86?40:3;
        catalog.entries.push_back(entry);
    }return catalog;
}
int main() {
    using namespace p2treasureheld;
    const auto catalog=sample();const std::string a(64,'a'),b(64,'b'),c(64,'c'),d(64,'d');
    const std::string receiver="64d283dc22622fc928e11423ed0b8f7a400f89251fd6c204974315ff1e998ce7:tutorial/defaultgen.txt#0";
    const std::string header=std::string("P2_TREASURE_HELD_1 ")+p2treasure::RetailDigest+" "+a+" "+b+" "+c+" "+d+" "+receiver+" 1376000414 tutorial ";
    const std::string row="1382830758 33 841 watch "+a+"\n";
    assert(decode(catalog,841)==catalog.find("watch"));
    for(int code:{0,-1,32768,1,2<<8,3<<8|188,4<<8|73})assert(!decode(catalog,code));
    Config config;assert(parse(header+"1\n"+row,catalog,config));
    assert(config.rows.size()==1&&config.rows[0].code==841&&config.receiver==1376000414);
    assert(config.identity==p2treasureplacements::hash(header+"1\n"+row));const auto before=config.identity;
    p2original::CatalogRow original;original.course="tutorial";original.enemy.uid=1382830758;
    original.enemy.source=33;original.enemy.treasureCode=841;
    assert(find(config,original));original.enemy.treasureCode=0;assert(!find(config,original));
    original.enemy.treasureCode=841;original.enemy.source=1;assert(!find(config,original));
    original.enemy.source=33;original.course="forest";assert(!find(config,original));
    for(const auto& bad:std::vector<std::string>{header+"0\n",header+"202\n",header+"1\n"+row+"extra",
        header+"2\n"+row+row,header+"1\n1382830758 33 842 watch "+a,
        header+"1\n1382830758 33 841 unknown "+a,header+"1\n1376000414 33 841 watch "+a,
        header+"1\n4294967296 33 841 watch "+a,header+"1\n1382830758 256 841 watch "+a,
        header+"1\n1382830758 33 841 watch "+std::string(64,'A'),std::string(p2treasureplacements::MaxBytes+1,'x')}) {
        assert(!parse(bad,catalog,config));assert(config.identity==before&&config.rows.size()==1);
    }
    auto changed=header+"1\n"+row;changed.replace(changed.find("tutorial/defaultgen.txt#0"),23,"tutorial/defaultgen.txt#1");
    assert(!parse(changed,catalog,config));
    p2treasurestate::State ledger;assert(ledger.bind(before));
    assert(ledger.credit(catalog,"watch",110)==p2treasurestate::Credit::Added);
    assert(ledger.credit(catalog,"watch",110)==p2treasurestate::Credit::Duplicate);
    assert(ledger.progress(catalog,false).pokos==110&&ledger.progress(catalog,false).collected==1);
    std::cout<<"P2 literal held descriptor/code841/unique receipt controls PASS (synthetic, no gameplay claim)\n";
}

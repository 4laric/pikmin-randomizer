#include "pc_p2_campaign_treasure_config.h"
#include <cassert>
#include <iostream>
static p2treasure::Catalog sample() {
    p2treasure::Catalog catalog;
    for(int i=0;i<201;++i) {
        p2treasure::Entry entry;entry.id="source_"+std::to_string(i);entry.dictionary=i+1;
        entry.classification=p2treasure::Classification::Campaign;entry.unique=true;
        entry.value=50;entry.strength=1;entry.slots=3;catalog.entries.push_back(entry);
    }return catalog;
}
int main(int argc,char** argv) {
    using namespace p2treasureplacements;
    if(argc==3) {
        p2treasure::Catalog retail;assert(retail.load_retail(argv[1]));
        std::string bytes;assert(bounded(argv[2],MaxBytes,bytes));Config placements;
        assert(parse(bytes,retail,placements));
        std::cout<<"P2 actual retail catalog/placement descriptor PASS rows="<<placements.rows.size()<<" source="<<placements.source<<" (no gameplay claim)\n";
        return 0;
    }
    assert(argc==1);
    const auto catalog=sample();const std::string digest(64,'a');
    const std::string head=std::string("P2_TREASURE_PLACEMENTS_1 ")+p2treasure::RetailDigest+" "+digest+" ";
    const std::string row="0 42 7 source_0 "+digest+" "+digest+"\n";
    Config parsed;assert(parse(head+"1\n"+row,catalog,parsed));
    assert(parsed.rows.size()==1&&parsed.rows[0].cargo==42&&parsed.rows[0].receiver==7);
    assert(parsed.source==hash(head+"1\n"+row));const auto before=parsed.source;
    const std::vector<std::string> refused={
        head+"0\n",head+"202\n",head+"1\n"+row+"extra",
        head+"2\n"+row+row, // repeated unique source
        head+"1\n0 7 7 source_0 "+digest+" "+digest,
        head+"1\n0 4294967296 7 source_0 "+digest+" "+digest,
        head+"1\n5 42 7 source_0 "+digest+" "+digest,
        head+"1\n0 42 7 unknown "+digest+" "+digest,
        head+"1\n0 42 7 ../escape "+digest+" "+digest,
        head+"1\n0 42 7 source_0 "+std::string(64,'A')+" "+digest,
        head+"2\n"+row+"0 43 42 source_1 "+digest+" "+digest, // receiver is another cargo
        std::string(MaxBytes+1,'x')};
    for(const auto& bytes:refused){assert(!parse(bytes,catalog,parsed));assert(parsed.source==before&&parsed.rows.size()==1);}
    auto changed=head+"1\n"+row;changed[25]='b';assert(!parse(changed,catalog,parsed));
    assert(!parse(head+"2\n"+row+"0 43 7 source_1 "+digest+" "+std::string(64,'b'),catalog,parsed));
    assert(parse(head+"2\n"+row+"1 42 7 source_1 "+digest+" "+digest,catalog,parsed)); // stage scopes UID
    assert(parsed.rows.size()==2);
    std::cout<<"P2 treasure placement bounds/identity controls PASS (synthetic, no gameplay claim)\n";
}

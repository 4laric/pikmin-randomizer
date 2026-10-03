#include "pc_p2_campaign_economy.h"
#include <cassert>
#include <iostream>
#include <sstream>

static p2treasure::Catalog sample() {
    p2treasure::Catalog catalog;
    std::istringstream input("P2_TREASURE_CATALOG_1 4\n"
        "dia_a_red otakara campaign 0 1 180 15 25 0 yes\n"
        "heavy otakara campaign 1 2 10000 1000 100 0 yes\n"
        "mode item mode_only 0 3 10000 1 1 0 yes\n"
        "unused item unused 1 4 10000 1 1 0 yes\n");
    assert(catalog.read(input)); return catalog;
}
int main(int argc, char** argv) {
    auto catalog = sample();
    assert(catalog.find("heavy")->strength == 1000); // strength can exceed slots
    p2economy::CollectionView view(catalog);
    assert(!view.progress().hoard_complete());
    assert(!view.observe("unknown",180));
    assert(!view.observe("mode",10000)); assert(!view.observe("unused",10000));
    assert(!view.observe("dia_a_red",181)); assert(view.progress().pokos == 0);
    assert(view.observe("dia_a_red",180)); assert(!view.observe("dia_a_red",180));
    assert(view.progress().pokos == 180 && view.progress().remaining() == 9820);
    assert(view.progress().phase() == p2economy::Phase::RepayingDebt);
    assert(view.observe("heavy",10000)); assert(view.progress().phase() == p2economy::Phase::Complete);
    assert((p2economy::Progress{9999,2,2}.remaining() == 1));
    assert((p2economy::Progress{9999,2,2}.phase() == p2economy::Phase::RepayingDebt));
    assert((p2economy::Progress{10000,1,2}.phase() == p2economy::Phase::TreasureHunt));
    assert((p2economy::Progress{UINT64_MAX,0,0}.remaining() == 0));
    assert((!p2economy::Progress{10000,0,0}.hoard_complete()));
    assert(p2economy::ship_summary(false,&catalog) == "0 Pokos | Debt 10000 | Hoard 0/2");
    assert(p2economy::ship_summary(true,&catalog) == "180 Pokos | Debt 9820 | Hoard 1/2");
    assert(p2economy::ship_summary(true,nullptr) == "180 Pokos | Debt 9820 | Catalog not staged");
    const auto original = catalog.entries.size();
    const char* invalid[] = {
        "P2_TREASURE_CATALOG_1 -1", "P2_TREASURE_CATALOG_1 202", "P2_TREASURE_CATALOG_1 1",
        "P2_TREASURE_CATALOG_1 1 a item bad 0 1 0 1 1 0 yes",
        "P2_TREASURE_CATALOG_1 1 a item campaign 0 1 -1 1 1 0 yes",
        "P2_TREASURE_CATALOG_1 1 ../a item campaign 0 1 0 1 1 0 yes",
        "P2_TREASURE_CATALOG_1 1 a item campaign 0 1 0 1 129 0 yes",
        "P2_TREASURE_CATALOG_1 1 a item campaign 0 1 0 1 1 0 yes trailing",
        "P2_TREASURE_CATALOG_1 2 a item campaign 0 1 0 1 1 0 yes a item campaign 1 2 0 1 1 0 yes",
        "P2_TREASURE_CATALOG_1 2 a item campaign 0 1 0 1 1 0 yes b item campaign 1 1 0 1 1 0 yes",
        "P2_TREASURE_CATALOG_1 2 a item campaign 0 1 0 1 1 0 yes b item campaign 0 2 0 1 1 0 yes"
    };
    for (const auto* text : invalid) {
        std::istringstream input(text); assert(!catalog.read(input)); assert(catalog.entries.size() == original);
    }
    if (argc > 1) {
        p2treasure::Catalog retail; assert(retail.load_retail(argv[1]));
        assert(retail.campaign_count() == 201);
        const auto* diamond = retail.find("dia_a_red");
        assert(diamond && diamond->value == 180 && diamond->strength == 15 && diamond->slots == 25);
        assert(p2economy::ship_summary(true,&retail) == "180 Pokos | Debt 9820 | Hoard 1/201");
        assert(!retail.load_retail("missing-catalog.txt")); assert(retail.campaign_count() == 201);
        if (argc > 2) assert(!retail.load_retail(argv[2]));
        std::cout << "P2 retail numeric catalog verified: 201\n";
    }
    std::cout << "P2 campaign economy controls PASS (synthetic; no gameplay claim)\n";
}

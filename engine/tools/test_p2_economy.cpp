#include "pc_p2_economy.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <stdexcept>
template<class F> void rejects(F f) { bool failed=false;try{f();}catch(const std::runtime_error&){failed=true;}assert(failed); }
int main(int argc,char** argv) {
    assert(argc==2);std::filesystem::path directory=argv[1];
    std::filesystem::create_directory(directory);
    auto path=(directory/"ledger.txt").string();
    P2Economy ledger;ledger.load(path);
    assert(ledger.credit("treasure:dia_a_red",180));
    assert(!ledger.credit("treasure:dia_a_red",180));
    rejects([&]{ledger.credit("treasure:dia_a_red",181);});
    assert(ledger.credit("corpse:1",2));
    P2Economy reload;reload.load(path);assert(reload.total()==182 && reload.count()==2);
    assert(!reload.credit("corpse:1",2));
    std::filesystem::create_directory(path+".tmp");
    rejects([&]{reload.credit("corpse:2",2);});
    assert(reload.total()==182 && reload.count()==2);
    P2Economy disk;disk.load(path);assert(disk.total()==182);
    auto bad=(directory/"bad.txt").string();
    std::ofstream(bad)<<"P2_ECONOMY_1\nx 1\nx 2\n";
    rejects([&]{reload.load(bad);});assert(reload.total()==182);
    rejects([&]{reload.credit("bad id",1);});
    rejects([&]{reload.credit("negative",-1);});
}

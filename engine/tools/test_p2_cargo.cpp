#include "pc_p2_cargo.h"
#include <cassert>
#include <sstream>
#include <iostream>
static bool rejects(const std::string& text){try{std::istringstream in(text);p2ReadCargo(in);return false;}catch(const std::runtime_error&){return true;}}
int main(){
    std::istringstream in("P2_CARGO_1 2 5000 tutorial_1:floor1:treasure:0 citrus 180 3 8 5001 tutorial_1:floor1:treasure:1 quencher 100 5 10");
    auto specs=p2ReadCargo(in);assert(specs.size()==2&&specs[0].weight==3&&specs[1].value==100);
    for(const char* bad:{"P2_CARGO_1 0","P2_CARGO_1 33","P2_CARGO_1 1 -1 x m 0 1 1","P2_CARGO_1 1 4294967296 x m 0 1 1","P2_CARGO_1 1 1 x ../m 0 1 1","P2_CARGO_1 1 1 x m 0 0 1","P2_CARGO_1 1 1 x m 0 1 129","P2_CARGO_1 1 1 x m 1000001 1 1","P2_CARGO_1 1 1 x m 0 1 1 extra","P2_CARGO_1 2 1 x m 0 1 1 1 y n 0 1 1","P2_CARGO_1 2 1 x m 0 1 1 2 x n 0 1 1","P2_CARGO_1 2 1 x m 0 1 1 2 y m 0 1 1"})assert(rejects(bad));
    std::cout<<"PASS P2 cargo protocol: distinct rows, numeric bounds, unsafe paths and duplicate actors/IDs/models\n";
}

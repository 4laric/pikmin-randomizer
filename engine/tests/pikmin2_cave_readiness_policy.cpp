#include "pc_p2_cave_readiness_policy.h"
#include <cassert>
#include <sstream>
#include <cstdio>
int main(){
    for(bool beasts:{false,true})for(int floor:{1,2,3,4})for(bool free:{false,true})for(bool preview:{false,true}){
        assert(p2CavePreviewReady(beasts,floor,free,preview,false,0,-1,false)==(beasts?free:preview));
    }
    assert(p2CavePreviewReady(true,3,false,true,true,1,0,true));
    for(int floor:{1,2,4,5})assert(!p2CavePreviewReady(true,floor,false,true,true,1,0,true));
    assert(!p2CavePreviewReady(true,3,false,false,true,1,0,true));
    assert(!p2CavePreviewReady(true,3,false,true,false,1,0,true));
    for(int count:{0,2,32})assert(!p2CavePreviewReady(true,3,false,true,true,count,0,true));
    for(int pokos:{-1,1,150})assert(!p2CavePreviewReady(true,3,false,true,true,1,pokos,true));
    const std::string token(64,'a'),valid="P2_BEASTS_CARGO_TERMINAL_1\n"+token+"\n";
    {std::istringstream in(valid);assert(p2CargoTerminalOptIn(in,true,3,token));}
    for(const auto& text:{std::string(),valid+"extra\n",std::string("bad\n")+token,valid.substr(0,valid.size()-2)}){
        std::istringstream in(text);assert(!p2CargoTerminalOptIn(in,true,3,token));
    }
    {std::istringstream in(valid);assert(!p2CargoTerminalOptIn(in,true,4,token));}
    {std::istringstream in(valid);assert(!p2CargoTerminalOptIn(in,false,3,token));}
    {std::istringstream in(valid);assert(!p2CargoTerminalOptIn(in,true,3,std::string(64,'b')));}
    std::puts("PASS cave readiness: legacy matrix, explicit floor3 single cargo pre-receipt gate, token/profile rejection");
}

#pragma once
#include <istream>
#include <string>

inline bool p2CargoTerminalOptIn(std::istream& in,bool beasts,int floor,const std::string& token){
    std::string header,expected,extra;
    return beasts && floor==3 && bool(in>>header>>expected) && !(in>>extra) && in.eof()
        && header=="P2_BEASTS_CARGO_TERMINAL_1" && expected==token;
}
inline bool p2CavePreviewReady(bool beasts,int floor,bool cargoFree,bool preview,bool pod,int cargoCount,int pokos,bool cargoTerminal){
    if(!beasts)return preview;
    if(cargoFree)return true;
    return cargoTerminal && floor==3 && preview && pod && cargoCount==1 && pokos==0;
}

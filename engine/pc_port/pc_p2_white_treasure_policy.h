#pragma once
#include "pc_p2_white_campaign_policy.h"
#include "netplay/pc_netplay_sha256.h"
#include <fstream>
#include <sstream>
#include <array>
namespace p2whitetreasure {
inline std::string hash(const std::string& bytes) {std::uint8_t digest[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),digest);return pc_netplay_sha::hex(digest,32);}
struct Config {
    int stage = -1;
    std::uint32_t cargo = 0, receiver = 0;
    std::array<std::string, 3> hashes;
    std::string identity() const {
        std::ostringstream text;text<<stage<<' '<<cargo<<' '<<receiver;
        for(const auto& hash:hashes)text<<' '<<hash;
        return hash(text.str());
    }
};
inline bool hex(const std::string& text) {
    return text.size()==64&&text.find_first_not_of("0123456789abcdef")==std::string::npos;
}
inline bool parse(std::istream& in,Config& out) {
    Config next;std::string word;unsigned long long cargo,receiver;
    if(!(in>>word>>next.stage>>cargo>>receiver)||word!="P2_WHITE_TREASURE_CAMPAIGN_1"||next.stage<0||next.stage>4||!cargo||cargo>UINT32_MAX||!receiver||receiver>UINT32_MAX||cargo==receiver)return false;
    next.cargo=static_cast<std::uint32_t>(cargo);next.receiver=static_cast<std::uint32_t>(receiver);
    for(auto& hash:next.hashes)if(!(in>>hash)||!hex(hash))return false;
    if(in>>word)return false;out=next;return true;
}
inline bool profile(std::istream& in) {
    std::string magic,id,corpse,extra;int value,minimum,maximum,corpseValue;
    return bool(in>>magic>>id>>value>>minimum>>maximum>>corpse>>corpseValue)&&magic=="P2_POD_1"&&id=="dia_a_red"&&value==180&&minimum==15&&maximum==25&&corpse=="Kochappy"&&corpseValue==2&&!(in>>extra);
}
inline bool bounded_bytes(const char* path,std::string& out,std::size_t bound) {
    std::ifstream in(path,std::ios::binary);if(!in)return false;
    std::string next;char buffer[4096];
    while(in.read(buffer,sizeof(buffer))||in.gcount()){
        const auto count=static_cast<std::size_t>(in.gcount());if(count>bound-next.size())return false;next.append(buffer,count);
    }
    if(!in.eof())return false;out=next;return true;
}
inline bool read_config(Config& out) {
    std::string bytes;if(!bounded_bytes("p2-white-treasure-campaign.txt",bytes,512))return false;
    std::istringstream input(bytes);Config next;if(!parse(input,next))return false;
    const char* paths[]={"p2-pod.txt","assets/dataDir/courses/pikmin2room/treasure.mod","assets/dataDir/courses/pikmin2room/pod.mod"};
    for(int i=0;i<3;++i){if(!bounded_bytes(paths[i],bytes,i?32u*1024u*1024u:512u)||hash(bytes)!=next.hashes[i])return false;if(i==0){std::istringstream source(bytes);if(!profile(source))return false;}}
    out=next;return true;
}
struct Ledger {
    bool delivered=false;
    bool credit(){if(delivered)return false;delivered=true;return true;}
    int total()const{return delivered?180:0;}
    void write(std::ostream& out,const Config& config)const{out<<' '<<config.identity()<<' '<<int(delivered);}
    bool read(std::istream& in,const Config& config){std::string id;int flag;if(!(in>>id>>flag)||id!=config.identity()||(flag!=0&&flag!=1))return false;delivered=flag==1;return true;}
};
inline Ledger ledger;
}

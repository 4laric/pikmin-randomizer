#pragma once
#include "pc_p2_ship_store.h"
#include <cstdint>
#include <istream>
#include <ostream>
#include <map>
#include <set>
#include <string>
#include <utility>
namespace p2whitecampaign {
using Key = std::pair<int, std::uint32_t>;
struct Config {
    std::set<Key> ivory;
    bool matches(int stage, std::uint32_t uid) const {return uid && ivory.count({stage,uid});}
};
inline bool parse(std::istream& in, Config& out) {
    Config next;std::string word;int count;
    if(!(in>>word>>count)||word!="P2_WHITE_CAMPAIGN_1"||count<1||count>32)return false;
    for(int i=0;i<count;++i){int stage;unsigned long long uid;
        if(!(in>>stage>>uid)||stage<0||stage>4||uid==0||uid>UINT32_MAX||!next.ivory.emplace(stage,static_cast<std::uint32_t>(uid)).second)return false;}
    if(in>>word)return false;out=next;return true;
}
struct Budget {
    std::map<Key,int> spent;
    int get(Key key) const {auto p=spent.find(key);return p==spent.end()?0:p->second;}
    bool record(Key key,int count,const Config& cfg){
        if(!cfg.matches(key.first,key.second)||count<get(key)||count>5||count<0)return false;
        spent[key]=count;return true;
    }
    bool read(std::istream& in,const Config& cfg){
        Budget next;int count;if(!(in>>count)||count<0||count>32)return false;
        for(int i=0;i<count;++i){int stage,used;unsigned long long uid;
            if(!(in>>stage>>uid>>used)||uid==0||uid>UINT32_MAX||!cfg.matches(stage,static_cast<std::uint32_t>(uid))||used<0||used>5||!next.spent.emplace(Key{stage,static_cast<std::uint32_t>(uid)},used).second)return false;}
        *this=next;return true;
    }
    void write(std::ostream& out)const{out<<' '<<spent.size();for(const auto& row:spent)out<<' '<<row.first.first<<' '<<row.first.second<<' '<<row.second;}
};
inline Budget budget;
inline bool read_stock(std::istream& in,p2ship::Store& stock,bool whiteEnabled){
    p2ship::Store next;if(!next.read(in))return false;
    if(!whiteEnabled&&(next.counts[1][0]||next.counts[1][1]||next.counts[1][2]))return false;
    stock=next;return true;
}
inline int maturity(const p2ship::Store& stock,int species){
    if(species!=3&&species!=4)return -1;
    for(int m=2;m>=0;--m)if(stock.counts[species-3][m])return m;
    return -1;
}
inline bool withdrawal_enabled(bool campaign,bool purpleLoaded,bool whiteLoaded,int species){
    return campaign&&((species==3&&purpleLoaded)||(species==4&&whiteLoaded));
}
inline int next_choice(int current,bool whiteLoaded){return whiteLoaded&&current==3?4:3;}
}

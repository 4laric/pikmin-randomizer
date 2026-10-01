#pragma once
#include <cstdint>
#include <istream>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>
struct P2CargoSpec {
    uint32_t generator;
    std::string instance,model;
    int value,weight,slots;
};
inline bool p2CargoSafe(const std::string& value,bool colon,size_t limit) {
    if(value.empty() || value.size()>limit)return false;
    for(unsigned char c:value)if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||(colon&&(c==':'||c=='/'))))return false;
    return true;
}
inline uint32_t p2CargoNumber(const std::string& word,uint32_t low,uint32_t high) {
    uint64_t result=0;if(word.empty())throw std::runtime_error("missing cargo number");
    for(unsigned char c:word){if(c<'0'||c>'9')throw std::runtime_error("invalid cargo number");result=result*10+c-'0';if(result>high)throw std::runtime_error("cargo number out of range");}
    if(result<low)throw std::runtime_error("cargo number below minimum");return uint32_t(result);
}
inline std::vector<P2CargoSpec> p2ReadCargo(std::istream& in) {
    std::string word,count;
    if(!(in>>word>>count)||word!="P2_CARGO_1")throw std::runtime_error("invalid cargo header");
    uint32_t size=p2CargoNumber(count,1,32);
    std::vector<P2CargoSpec> result;std::set<uint32_t> generators;std::set<std::string> ids,models;
    for(uint32_t i=0;i<size;++i){
        std::string generator,value,weight,slots;P2CargoSpec row;
        if(!(in>>generator>>row.instance>>row.model>>value>>weight>>slots))throw std::runtime_error("truncated cargo row");
        row.generator=p2CargoNumber(generator,0,0xffffffffU);row.value=p2CargoNumber(value,0,1000000);row.weight=p2CargoNumber(weight,1,1000);row.slots=p2CargoNumber(slots,1,128);
        if(!p2CargoSafe(row.instance,true,90)||!p2CargoSafe(row.model,false,64))throw std::runtime_error("unsafe cargo identity/model");
        if(!generators.insert(row.generator).second||!ids.insert(row.instance).second||!models.insert(row.model).second)throw std::runtime_error("duplicate cargo row/model/identity");
        result.push_back(row);
    }
    if(in>>word)throw std::runtime_error("unexpected cargo trailing data");return result;
}

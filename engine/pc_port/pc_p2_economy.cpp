#include "pc_p2_economy.h"
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <limits>
#include <sstream>
#include <stdexcept>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <io.h>
#else
#include <unistd.h>
#endif

static void valid(const std::string& id,int value) {
    if(id.empty() || id.size()>100 || id.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:/-")!=std::string::npos || value<0 || value>1000000)
        throw std::runtime_error("Invalid P2 receipt");
}
void P2Economy::load(const std::string& file) {
    std::map<std::string,int> next;
    if(std::filesystem::exists(file)) {
        std::ifstream in(file);std::string line;
        if(!std::getline(in,line) || line!="P2_ECONOMY_1")throw std::runtime_error("Invalid P2 ledger header");
        while(std::getline(in,line)) {
            std::istringstream row(line);std::string id,extra;int value;
            if(!(row>>id>>value) || row>>extra)throw std::runtime_error("Invalid P2 ledger row");
            valid(id,value);
            if(!next.emplace(id,value).second)throw std::runtime_error("Duplicate P2 ledger row");
        }
        if(!in.eof())throw std::runtime_error("Cannot read P2 ledger");
    }
    long long sum=0;for(auto& receipt:next)sum+=receipt.second;
    if(sum>std::numeric_limits<int>::max())throw std::runtime_error("P2 economy overflow");
    receipts=std::move(next);path=file;
}
int P2Economy::total() const { int sum=0;for(auto& receipt:receipts)sum+=receipt.second;return sum; }
bool P2Economy::credit(const std::string& id,int value) {
    valid(id,value);
    auto found=receipts.find(id);
    if(found!=receipts.end()) {
        if(found->second!=value)throw std::runtime_error("P2 receipt value changed");
        return false;
    }
    if(path.empty() || total()>std::numeric_limits<int>::max()-value)throw std::runtime_error("Invalid P2 economy state");
    auto next=receipts;next.emplace(id,value);
    std::string data="P2_ECONOMY_1\n";
    for(auto& receipt:next)data+=receipt.first+" "+std::to_string(receipt.second)+"\n";
    const std::string temporary=path+".tmp";
    FILE* file=std::fopen(temporary.c_str(),"wb");
    if(!file)throw std::runtime_error("Cannot create P2 ledger temporary file");
    bool ok=std::fwrite(data.data(),1,data.size(),file)==data.size() && std::fflush(file)==0;
#ifdef _WIN32
    if(ok)ok=::_commit(::_fileno(file))==0;
#else
    if(ok)ok=::fsync(::fileno(file))==0;
#endif
    if(std::fclose(file)!=0)ok=false;
    if(!ok)throw std::runtime_error("Cannot flush P2 ledger");
#ifdef _WIN32
    if(!::MoveFileExA(temporary.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))
        throw std::runtime_error("Cannot replace P2 ledger");
#else
    if(std::rename(temporary.c_str(),path.c_str())!=0)throw std::runtime_error("Cannot replace P2 ledger");
#endif
    receipts=std::move(next);return true;
}

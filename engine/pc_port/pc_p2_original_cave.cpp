#include "pc_p2_original_cave.h"
#include "netplay/pc_netplay_sha256.h"
#include <cmath>
#include <cstring>
#include <fstream>
#include <set>
#include <sstream>
namespace p2original {
namespace {
bool fail(std::string& e,const char* text){e=text;return false;}
bool hex(const std::string& s){return s.size()==64&&s.find_first_not_of("0123456789abcdef")==std::string::npos;}
bool leaf(const std::string& s){return !s.empty()&&s.size()<=128&&s.find("..") == std::string::npos
    &&s.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")==std::string::npos;}
}
bool validateCave(const CaveRecord& r,std::string& e){
    const auto hash=r.sourceKey.rfind('#'),slash=r.sourceKey.find('/');
    if(!hex(r.sourceSha)||r.sourceKey.size()>2048||slash==std::string::npos||slash==0
        ||hash==std::string::npos||hash<=slash+1||hash+1==r.sourceKey.size()
        ||r.sourceKey.find("..")!=std::string::npos||r.sourceKey.find("//")!=std::string::npos
        ||r.sourceKey.find('#')!=hash||r.sourceKey[hash-1]=='/'
        ||r.sourceKey.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/_.-#")!=std::string::npos)
        return fail(e,"invalid literal Cave source identity");
    const auto index=r.sourceKey.substr(hash+1);
    if(index.find_first_not_of("0123456789")!=std::string::npos||(index.size()>1&&index[0]=='0'))
        return fail(e,"noncanonical Cave source record index");
    unsigned char sha[32];pc_netplay_sha::sha256(r.sourceKey.data(),r.sourceKey.size(),sha);
    if(r.uid!=(0x52000000u|(unsigned(sha[0])<<16)|(unsigned(sha[1])<<8)|sha[2]))
        return fail(e,"Cave UID/source key mismatch");
    if(!leaf(r.caveFile)||r.caveFile.size()<5||r.caveFile.substr(r.caveFile.size()-4)!=".txt"
        ||!leaf(r.unitsFile)||r.unitsFile.size()<5||r.unitsFile.substr(r.unitsFile.size()-4)!=".txt"
        ||r.caveId.size()!=4||r.caveId.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")!=std::string::npos)
        return fail(e,"invalid literal Cave target/files");
    if(r.reserved!=0||r.resurrectionDays!=0||r.dayLimit< -1)
        return fail(e,"Cave respawn/cache flags require a separate supported provider");
    for(unsigned i=0;i<3;++i)if(!std::isfinite(r.position[i])||!std::isfinite(r.offset[i])
        ||!std::isfinite(r.rotation[i])||!std::isfinite(r.position[i]+r.offset[i])
        ||std::fabs(r.position[i])>100000||std::fabs(r.offset[i])>100000
        ||std::fabs(r.rotation[i])>100000||std::fabs(r.position[i]+r.offset[i])>100000)
        return fail(e,"invalid literal Cave transform");
    for(unsigned i=0;i<10;++i){
        const bool color=i>=4&&i<=6;
        if(r.parameterTypes[i]!=(color?1u:4u)||!std::isfinite(r.parameters[i])
            ||std::fabs(r.parameters[i])>1000000
            ||(color&&(r.parameters[i]<0||r.parameters[i]>255||std::floor(r.parameters[i])!=r.parameters[i])))
            return fail(e,"unsupported Cave0002 typed parameter tail");
    }
    e.clear();return true;
}
std::string caveDigest(const CaveRecord& r){
    std::string bytes;
    auto text=[&](const std::string& s){bytes+=s;bytes.push_back('\0');};
    auto word=[&](std::uint32_t v){for(unsigned i=0;i<4;++i)bytes.push_back(char(v>>(8*i)));};
    auto real=[&](float f){std::uint32_t v;static_assert(sizeof(v)==sizeof(f),"f32");std::memcpy(&v,&f,4);word(v);};
    text("GenItem0002/Cave0002");text(r.sourceSha);text(r.sourceKey);text(r.caveFile);text(r.unitsFile);text(r.caveId);
    word(r.uid);word(r.reserved);word(unsigned(r.resurrectionDays));word(unsigned(r.dayLimit));
    for(const auto* a:{&r.position,&r.offset,&r.rotation})for(float v:*a)real(v);
    for(unsigned i=0;i<10;++i){word(r.parameterTypes[i]);real(r.parameters[i]);}
    unsigned char sha[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),sha);
    return pc_netplay_sha::hex(sha,32);
}
static bool parseStream(std::istream& in,std::vector<CaveRecord>& out,std::string& e){
    std::string magic;unsigned count;
    if(!(in>>magic>>count)||magic!="P2_ORIGINAL_CAVE_1"||!count||count>4096)
        return fail(e,"invalid original Cave manifest envelope/capacity");
    std::vector<CaveRecord> rows;std::set<unsigned> uids;std::set<std::string> keys;
    for(unsigned i=0;i<count;++i){
        CaveRecord r;std::string object,local;
        if(!(in>>r.uid>>r.sourceKey>>r.sourceSha>>object>>local>>r.reserved>>r.resurrectionDays>>r.dayLimit
            >>r.caveFile>>r.unitsFile>>r.caveId)||object!="0002"||local!="0002")
            return fail(e,"invalid Cave literal identity/version");
        for(auto* a:{&r.position,&r.offset,&r.rotation})for(float& f:*a)if(!(in>>f))return fail(e,"truncated Cave transform");
        for(unsigned j=0;j<10;++j)if(!(in>>r.parameterTypes[j]>>r.parameters[j]))return fail(e,"truncated Cave typed tail");
        if(!validateCave(r,e)||!uids.insert(r.uid).second||!keys.insert(r.sourceKey).second)return fail(e,"invalid/duplicate Cave record");
        rows.push_back(r);
    }
    if(in>>magic||!in.eof())return fail(e,"trailing or unreadable Cave manifest");
    out.swap(rows);e.clear();return true;
}
bool parseCaves(const std::string& bytes,std::vector<CaveRecord>& out,std::string& e){
    if(bytes.empty()||bytes.size()>4*1024*1024)return fail(e,"original Cave input size invalid");
    std::istringstream in(bytes);return parseStream(in,out,e);
}
bool readCaves(const std::string& path,std::vector<CaveRecord>& out,std::string& e){
    std::ifstream in(path,std::ios::binary|std::ios::ate);
    if(!in)return fail(e,"original Cave manifest missing");
    const auto size=in.tellg();if(size<=0||size>4*1024*1024)return fail(e,"original Cave input size invalid");
    std::string bytes(static_cast<std::size_t>(size),'\0');in.seekg(0);
    if(!in.read(&bytes[0],size))return fail(e,"original Cave manifest unreadable");
    return parseCaves(bytes,out,e);
}
bool caveCache(const CaveRecord& r,std::vector<std::uint8_t>& out,std::string& e){
    if(!validateCave(r,e))return false;
    std::vector<std::uint8_t> bytes(104,0);std::memcpy(bytes.data(),"CVC1",4);
    const auto digest=caveDigest(r);std::memcpy(bytes.data()+4,digest.data(),64);
    for(unsigned i=0;i<4;++i)bytes[68+i]=std::uint8_t(r.uid>>(i*8));
    pc_netplay_sha::sha256(bytes.data(),72,bytes.data()+72);out.swap(bytes);e.clear();return true;
}
bool caveRestore(const CaveRecord& r,const std::vector<std::uint8_t>& bytes,std::string& e){
    std::vector<std::uint8_t> expected;if(!caveCache(r,expected,e))return false;
    if(bytes!=expected)return fail(e,"original Cave cache version/checksum/typed source mismatch");
    e.clear();return true;
}
}

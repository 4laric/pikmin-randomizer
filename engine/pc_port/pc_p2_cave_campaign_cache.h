#pragma once
#include "save/pc_generator_cache_validation.h"
#include <istream>
#include <ostream>
#include <string>

// Two independent images of the existing native GeneratorCache card format.
// No new stage ID is inserted into its fixed five-stage directory.
struct P2CaveCacheBanks {
    static constexpr unsigned heapSize = 0x6c00;
    static constexpr unsigned imageSize = 8 + heapSize + 5 * 37;
    bool inside = false;
    std::string surface, floor;

    static bool imageValid(const std::string& bytes) {
        if (bytes.size() != imageSize) return false;
        auto word = [&bytes](unsigned offset) {
            std::uint32_t value = 0;
            for (unsigned i=0;i<4;++i) value = (value<<8)|static_cast<unsigned char>(bytes[offset+i]);
            return value;
        };
        struct Entry {
            std::uint32_t mStageID, mCacheHeapOffset, mTotalCacheSize, mGenCacheSize,
                mCreatureCacheSize, mUfoPartsCacheSize, mGenCount, mCreatureCount, mUfoPartsCount;
        };
        std::array<std::uint8_t,5> states{};
        std::array<Entry,5> entries{};
        for (unsigned i=0;i<5;++i) {
            unsigned offset = 8 + heapSize + i*37;
            states[i] = static_cast<unsigned char>(bytes[offset++]);
            entries[i] = {word(offset),word(offset+4),word(offset+8),word(offset+12),
                word(offset+16),word(offset+20),word(offset+24),word(offset+28),word(offset+32)};
        }
        const auto used = word(0), free = word(4);
        if (used > heapSize || free > heapSize) return false;
        return pc::save::validateGeneratorCacheLayout(int(used),int(free),int(heapSize),0,states,entries);
    }
    bool valid() const {
        return (inside ? imageValid(surface) : surface.empty())
            && (floor.empty() || imageValid(floor));
    }
    bool enter(const std::string& snapshot) {
        if (inside || !valid() || !imageValid(snapshot)) return false;
        surface=snapshot; inside=true; return true;
    }
    bool captureFloor(const std::string& snapshot) {
        if (!inside || !valid() || !imageValid(snapshot)) return false;
        floor=snapshot; return true;
    }
    bool leave(const std::string& snapshot) {
        if (!captureFloor(snapshot)) return false;
        surface.clear(); inside=false; return true;
    }
    static std::string hex(const std::string& bytes) {
        if (bytes.empty()) return "-";
        const char* digits="0123456789abcdef";
        std::string result;result.reserve(bytes.size()*2);
        for(unsigned char byte:bytes){result+=digits[byte>>4];result+=digits[byte&15];}
        return result;
    }
    static bool unhex(const std::string& text,std::string& bytes) {
        if(text=="-"){bytes.clear();return true;}
        if(text.size()!=imageSize*2)return false;
        std::string parsed;parsed.reserve(imageSize);
        auto nibble=[](char c){return c>='0'&&c<='9'?c-'0':c>='a'&&c<='f'?c-'a'+10:-1;};
        for(unsigned i=0;i<text.size();i+=2){int a=nibble(text[i]),b=nibble(text[i+1]);
            if(a<0||b<0)return false;
            parsed+=char(a*16+b);}
        if(!imageValid(parsed))return false;
        bytes=std::move(parsed);return true;
    }
    bool read(std::istream& input) {
        std::string marker,version,active,surfaceHex,floorHex;
        P2CaveCacheBanks parsed;
        if(!(input>>marker>>version>>active>>surfaceHex>>floorHex)
            ||marker!="CAVE_CACHE"||version!="1"||(active!="0"&&active!="1")
            ||!unhex(surfaceHex,parsed.surface)||!unhex(floorHex,parsed.floor))return false;
        parsed.inside=active=="1";
        if(!parsed.valid())return false;
        *this=std::move(parsed);return true;
    }
    void write(std::ostream& output) const {
        output<<" CAVE_CACHE 1 "<<int(inside)<<' '<<hex(surface)<<' '<<hex(floor);
    }
};

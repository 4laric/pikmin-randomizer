#pragma once
#include "netplay/pc_netplay_sha256.h"
#include <string>
namespace p2original {
// External catalog identity only. This is NOT a retail Piki runtime UID and
// must never be installed as a fake native Generator/personality.
inline unsigned originalSourceCatalogUid(const std::string& key){
 unsigned char bytes[32];pc_netplay_sha::sha256(key.data(),key.size(),bytes);
 return 0x52000000u|(unsigned(bytes[0])<<16)|(unsigned(bytes[1])<<8)|bytes[2];
}
}

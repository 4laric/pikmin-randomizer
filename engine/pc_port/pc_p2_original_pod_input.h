#pragma once
#include "pc_p2_original_pod.h"
#include "netplay/pc_netplay_sha256.h"
namespace p2originalpod {
// Byte-integrity policy shared with the native loader. It does not authenticate
// a provider, select a scene, allocate an actor, or issue any receipt.
inline bool selectedResource(const SourceInput& input,const std::string& role,
                             const char* expected,std::string& out,std::string& error){
 std::string bytes;
 if(!input||!input(role,bytes,error))return false;
 if(bytes.empty()||bytes.size()>32*1024*1024){error="pod_selected_resource_size";return false;}
 unsigned char hash[32];pc_netplay_sha::sha256(bytes.data(),bytes.size(),hash);
 if(pc_netplay_sha::hex(hash,32)!=expected){error="pod_selected_resource_hash";return false;}
 out=std::move(bytes);return true;
}
}

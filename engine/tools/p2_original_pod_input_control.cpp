#include "pc_p2_original_pod_input.h"
#include <cassert>
#include <fstream>
#include <iterator>
#include <iostream>
int main(int argc,char** argv){
 assert(argc==2);std::ifstream in(argv[1],std::ios::binary);assert(in);
 std::string source{std::istreambuf_iterator<char>(in),{}};assert(!source.empty());
 unsigned reads=0;std::string out="unchanged",error;
 p2originalpod::SourceInput input=[&](const std::string& role,std::string& bytes,std::string&){
  ++reads;if(role!=p2originalpod::convertedModelRole)return false;bytes=source;return true;
 };
 assert(p2originalpod::selectedResource(input,p2originalpod::convertedModelRole,
                                      p2originalpod::convertedModelSha256,out,error));
 assert(reads==1&&out==source);const auto retained=out;
 source[0]^=1; // Change the backing input after its exact verified output was retained.
 assert(out==retained&&reads==1);
 assert(!p2originalpod::selectedResource(input,p2originalpod::convertedModelRole,
                                       p2originalpod::convertedModelSha256,out,error));
 assert(out==retained&&reads==2);
 assert(!p2originalpod::selectedResource(input,"foreign-role",p2originalpod::convertedModelSha256,out,error));
 assert(out==retained);
 assert(!p2originalpod::selectedResource({},p2originalpod::convertedModelRole,
                                       p2originalpod::convertedModelSha256,out,error));
 std::cout<<"PASS actual Pod model one-read retention/corruption/missing-input policy; no scene or gameplay authority\n";
}

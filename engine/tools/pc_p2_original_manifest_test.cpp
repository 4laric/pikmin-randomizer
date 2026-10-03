#include "pc_p2_original_manifest.h"
#include <iostream>
#include <stdexcept>
#include <fstream>
#include <iterator>
using namespace p2original;
unsigned checks=0;void check(bool b){++checks;if(!b)throw std::runtime_error("manifest control "+std::to_string(checks));}
int main(int argc,char** argv){std::string e,bytes;SourceManifest m,out;m.fingerprint=std::string(64,'a');
 CatalogRow row;row.course="tutorial";row.member="nonloop/3-9.txt";row.index=0;row.sourceKey="tutorial/nonloop/3-9.txt#0";row.enemy.uid=originalGeneratorUid(row.sourceKey);row.enemy.count=1;row.enemy.position={-400.922485f,0,2646.80151f};row.enemy.directionDegrees=50;row.enemy.generatorVersion="0001";row.enemy.generatorTail={"3","1","2"};
 GeneratorState state;state.uid=row.enemy.uid;state.count=1;state.reserved=5;state.resurrectionDays=-1;m.rows={row};m.literal={state};
 check(writeSourceManifest(m,"tutorial",bytes,e));check(readSourceManifest(bytes,"tutorial",out,e));
 check(out.fingerprint==m.fingerprint&&out.rows.size()==1&&out.literal.size()==1);check(out.rows[0].enemy.position.x==row.enemy.position.x&&out.rows[0].enemy.position.z==row.enemy.position.z);check(out.rows[0].enemy.generatorTail==row.enemy.generatorTail&&out.rows[0].sourceKey==row.sourceKey);check(out.literal[0].resurrectionDays==-1&&out.literal[0].dayLimit==-1&&out.literal[0].reserved==5);
 const auto prior=out.fingerprint;
 for(size_t n=0;n<bytes.size();++n){check(!readSourceManifest(bytes.substr(0,n),"tutorial",out,e));check(out.fingerprint==prior);}
 auto bad=bytes;bad[30]^=1;check(!readSourceManifest(bad,"tutorial",out,e));check(!readSourceManifest(bytes,"forest",out,e));check(!readSourceManifest(bytes+"trailing","tutorial",out,e));
 auto altered=m;altered.literal[0].activation=1;check(!writeSourceManifest(altered,"tutorial",bad,e));altered=m;altered.literal.push_back(state);check(!writeSourceManifest(altered,"tutorial",bad,e));altered=m;altered.rows[0].enemy.deathCount=1;check(!writeSourceManifest(altered,"tutorial",bad,e));altered=m;altered.rows[0].enemy.uid++;check(!writeSourceManifest(altered,"tutorial",bad,e));altered=m;altered.literal[0].uid++;check(!writeSourceManifest(altered,"tutorial",bad,e));
 if(argc==3){
  std::ifstream input(argv[1],std::ios::binary);check(bool(input));
  std::string staged((std::istreambuf_iterator<char>(input)),std::istreambuf_iterator<char>());
  check(readSourceManifest(staged,argv[2],out,e));
  check(writeSourceManifest(out,argv[2],bytes,e));check(bytes==staged);
  std::cout<<"staged source rows "<<out.rows.size()<<"\n";
 }else check(argc==1);
 std::cout<<"PASS original manifest "<<checks<<" controls\n";
}

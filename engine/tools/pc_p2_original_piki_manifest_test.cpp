#include "pc_p2_original_piki_manifest.h"
#include "pc_p2_original_source_uid.h"
#include <iostream>
#include <fstream>
#include <iterator>
#include <stdexcept>
using namespace p2original;
unsigned checks=0;void check(bool ok){++checks;if(!ok)throw std::runtime_error("Piki manifest control "+std::to_string(checks));}
int main(int argc,char** argv){
 PikiSourceRecord row;row.sourceKey="tutorial/defaultgen.txt#5";row.sourceSha=std::string(64,'b');row.spawn.uid=originalSourceCatalogUid(row.sourceKey);row.spawn.count=5;row.spawn.species=1;row.spawn.wildParameter=1;row.spawn.position={-585.95697f,0,2782.98999f};
 PikiManifest m,out;m.campaign=std::string(64,'a');m.rows={row};std::string bytes,e;
 check(writePikiManifest(m,bytes,e));check(readPikiManifest(bytes,out,e));check(out.campaign==m.campaign&&out.catalog.size()==64&&out.catalog!=out.campaign);
 check(out.rows[0].spawn.uid==row.spawn.uid&&out.rows[0].spawn.count==5&&out.rows[0].spawn.wildParameter==1&&out.rows[0].spawn.position==row.spawn.position);
 std::string encoded;check(writePikiManifest(out,encoded,e)&&encoded==bytes);const auto previous=out.catalog;
 for(size_t n=0;n<bytes.size();++n){check(!readPikiManifest(bytes.substr(0,n),out,e));check(out.catalog==previous);}
 auto altered=m;altered.catalog=std::string(64,'c');check(!writePikiManifest(altered,encoded,e));
 altered=m;altered.rows[0].spawn.uid++;check(!writePikiManifest(altered,encoded,e));
 altered=m;altered.rows[0].objectVersion="0002";check(!writePikiManifest(altered,encoded,e));
 altered=m;altered.rows.push_back(row);check(!writePikiManifest(altered,encoded,e));
 altered=m;altered.rows[0].sourceKey="tutorial/../defaultgen.txt#5";check(!writePikiManifest(altered,encoded,e));
 auto corrupt=bytes;corrupt[130]^=1;check(!readPikiManifest(corrupt,out,e));
 check(readPikiManifest(bytes,out,e));std::vector<unsigned> active={row.spawn.uid},decoded={7};std::string census;
 check(writePikiActive(out,"tutorial",5,active,census,e));check(readPikiActive(census,out,"tutorial",5,decoded,e)&&decoded==active);
 for(size_t n=0;n<census.size();++n){check(!readPikiActive(census.substr(0,n),out,"tutorial",5,decoded,e));check(decoded==active);}
 check(!readPikiActive(census,out,"tutorial",4,decoded,e));check(!readPikiActive(census,out,"forest",5,decoded,e));
 check(!writePikiActive(out,"tutorial",5,{row.spawn.uid,row.spawn.uid},encoded,e));check(!writePikiActive(out,"tutorial",5,{row.spawn.uid+1},encoded,e));
 check(writePikiActive(out,"tutorial",5,{},census,e));check(readPikiActive(census,out,"tutorial",5,decoded,e)&&decoded.empty());
 if(argc==2){std::ifstream file(argv[1],std::ios::binary);check(bool(file));std::string staged((std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());check(readPikiManifest(staged,out,e));check(writePikiManifest(out,encoded,e)&&encoded==staged);std::cout<<"actual full-calendar Piki rows "<<out.rows.size()<<"\n";}
 else check(argc==1);
 std::cout<<"PASS original Piki manifest "<<checks<<" controls\n";
}

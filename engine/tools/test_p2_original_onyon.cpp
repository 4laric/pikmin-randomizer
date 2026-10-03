#include "pc_p2_original_onyon.h"
#include <cstdio>
#include <limits>
#include <cstdlib>
using namespace p2original;
unsigned checks=0;
void check(bool ok,const char* s){++checks;if(!ok){std::fprintf(stderr,"FAIL ONYON %s\n",s);std::exit(1);}}
int main(int argc,char** argv){
 check(argc==2,"literal original manifest argument");std::string e;std::vector<OnyonRecord> rows;
 check(readOnyons(argv[1],rows,e),e.c_str());check(rows.size()==5,"actual tutorial five onyn records");
 check(rows[0].index==4&&rows[0].sourceKey=="tutorial/defaultgen.txt#0","literal ship identity");
 check(rows[1].index==1&&rows[2].index==0&&rows[3].index==2&&rows[4].index==1&&rows[4].afterBoot==0,"RGB camp and separate wild red source rows");
 check(rows[0].rotation[1]<-121&&rows[0].position[2]>3033,"authored source transform preserved");
 for(const auto& row:rows){check(validateOnyon(row,e),"actual source row validates");for(unsigned mask=0;mask<8;++mask){bool expected=row.index==4||(bool(mask&(1<<row.index))==bool(row.afterBoot));check(onyonEligible(row,mask)==expected,"source afterBoot matrix");}}
 const auto original=onyonDigest(rows[0]);auto changed=rows[0];changed.position[0]+=0.25f;check(onyonDigest(changed)!=original,"cache detects changed literal float with unchanged source SHA");
 changed=rows[0];changed.afterBoot^=1;check(onyonDigest(changed)!=original,"cache detects changed source tail");
 changed=rows[0];changed.index=3;check(!validateOnyon(changed,e),"pod refuses missing physical provider");
 changed=rows[0];changed.uid^=1;check(!validateOnyon(changed,e),"source UID mismatch refuses");
 changed=rows[0];changed.position[0]=std::numeric_limits<float>::infinity();check(!validateOnyon(changed,e),"nonfinite literal transform refuses");
 changed=rows[0];changed.afterBoot=2;check(!validateOnyon(changed,e),"unsupported tail refuses");
 auto saved=rows;check(!readOnyons("file-that-does-not-exist",rows,e)&&rows[0].uid==saved[0].uid,"failed load preserves previous output");
 std::printf("PASS ORIGINAL_ONYON controls=%u literal_rows=%zu physical_births=0\n",checks,rows.size());
}

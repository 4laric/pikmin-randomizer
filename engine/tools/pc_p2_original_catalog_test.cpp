#include "pc_p2_original_catalog.h"
#include <cstdio>
#include <limits>
using namespace p2original;
int main(){unsigned checks=0,failed=0;auto check=[&](bool b){++checks;if(!b)++failed;};
 Catalog c;CatalogRow row;row.course="tutorial";row.member="defaultgen.txt";row.sourceKey="tutorial/defaultgen.txt#0";row.enemy.uid=originalGeneratorUid(row.sourceKey);row.enemy.source=0;row.enemy.count=3;
 const std::string fingerprint(64,'a');std::string e;unsigned admitted=0;auto capability=[&](const CatalogRow& r,std::string&){++admitted;return r.enemy.source==0;};
 check(c.install(fingerprint,{row},capability,e));check(admitted==1);check(c.find(row.enemy.uid)&&c.find(row.enemy.uid)->enemy.source==0);check(c.find(0)==nullptr);
 auto bad=row;bad.enemy.uid^=1;check(!c.install(fingerprint,{bad},capability,e));check(c.find(row.enemy.uid)!=nullptr);
 bad=row;bad.sourceKey="tutorial/defaultgen.txt#00";check(!c.install(fingerprint,{bad},capability,e));
 bad=row;bad.course="..";check(!c.install(fingerprint,{bad},capability,e));
 bad=row;bad.member="nonloop/5-29.txt";bad.sourceKey="tutorial/nonloop/5-29.txt#0";bad.enemy.uid=originalGeneratorUid(bad.sourceKey);check(c.install(fingerprint,{bad},capability,e));check(c.install(fingerprint,{row},capability,e));
 bad=row;bad.member="nonloop/../5-29.txt";bad.sourceKey="tutorial/nonloop/../5-29.txt#0";bad.enemy.uid=originalGeneratorUid(bad.sourceKey);check(!c.install(fingerprint,{bad},capability,e));
 check(!c.install(fingerprint,{row,row},capability,e));check(!c.install("bad",{row},capability,e));check(!c.install(fingerprint,{row},{},e));
 bad=row;bad.enemy.appearRadius=std::numeric_limits<float>::quiet_NaN();check(!c.install(fingerprint,{bad},capability,e));
 bad=row;bad.enemy.birthType=256;check(!c.install(fingerprint,{bad},capability,e));
 bad=row;bad.enemy.generatorTail={std::string(4097,'x')};check(!c.install(fingerprint,{bad},capability,e));
 bad=row;bad.index=1;bad.sourceKey="tutorial/defaultgen.txt#1";bad.enemy.uid=originalGeneratorUid(bad.sourceKey);bad.enemy.source=91;
 check(!c.install(std::string(64,'b'),{row,bad},capability,e));check(c.fingerprint()==fingerprint&&c.find(bad.enemy.uid)==nullptr);
 int a=0,b=0,g=0,other=0;std::uint64_t h=777,k=0,gh=0;check(!c.bind(&a,row.enemy.uid,0,1,h,e)&&h==777);check(c.bindGenerator(&g,row.enemy.uid,gh,e));check(!c.bindGenerator(&other,row.enemy.uid,k,e));unsigned uid=0;check(c.generatorUid(&g,gh,uid)&&uid==row.enemy.uid);check(!c.generatorUid(&g,gh+1,uid));check(!c.bind(nullptr,row.enemy.uid,0,1,h,e)&&h==777);check(!c.bind(&a,row.enemy.uid,3,1,h,e));check(!c.bind(&a,row.enemy.uid,0,0,h,e));
 check(c.bind(&a,row.enemy.uid,0,1,h,e));check(!c.bind(&a,row.enemy.uid,1,1,k,e));check(!c.bind(&b,row.enemy.uid,0,1,k,e));check(c.bind(&b,row.enemy.uid,1,1,k,e));
 InstanceIdentity identity;check(c.lookup(&a,h,identity)&&identity.generator==row.enemy.uid&&identity.ordinal==0&&identity.epoch==1&&identity.catalog==fingerprint);
 check(!c.install(fingerprint,{row},capability,e));check(!c.forgetGenerator(&g,gh));check(!c.forget(&a,h+1));check(c.forget(&a,h));check(!c.lookup(&a,h,identity));
 std::uint64_t next=0;check(!c.bind(&a,row.enemy.uid,0,1,next,e));check(c.bind(&a,row.enemy.uid,0,2,next,e)&&next!=h);check(!c.forget(&a,h));check(c.lookup(&a,next,identity)&&identity.epoch==2);
 check(c.forget(&a,next)&&c.forget(&b,k));check(c.forgetGenerator(&g,gh));check(c.bindGenerator(&g,row.enemy.uid,k,e)&&k!=gh);check(!c.forgetGenerator(&g,gh));check(c.forgetGenerator(&g,k));check(c.install(std::string(64,'b'),{row},capability,e));check(c.bindGenerator(&g,row.enemy.uid,gh,e));check(c.bind(&a,row.enemy.uid,0,1,next,e));check(!c.lookup(&a,h,identity));check(c.lookup(&a,next,identity)&&identity.catalog==std::string(64,'b'));
 std::printf("original_catalog checks=%u failures=%u engine=0 persistent_cache=0\n",checks,failed);return failed?1:0;
}

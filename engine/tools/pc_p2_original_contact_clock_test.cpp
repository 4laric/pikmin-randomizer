#include "pc_p2_original_contact_clock.h"
#include <cstdio>
#include <cstdlib>
#include <limits>
int main(){
 unsigned checks=0;auto check=[&](bool ok){++checks;if(!ok){std::fprintf(stderr,"FAIL contact clock %u\n",checks);std::exit(1);}};
 p2original::ContactClock c;check(c.formationable()&&c.frames()==0);
 check(c.update(21,0,0)&&c.frames()==0);
 c.disband();check(c.frames()==60&&!c.formationable());
 check(c.update(0,0,0)&&c.frames()==60);
 check(c.update(20,0,0)&&c.frames()==60);
 check(c.update(12,16,0)&&c.frames()==60);
 check(c.update(-20,0,0)&&c.frames()==60);
 check(!c.update(std::numeric_limits<float>::quiet_NaN(),0,0)&&c.frames()==60);
 check(!c.update(0,std::numeric_limits<float>::infinity(),0)&&c.frames()==60);
 check(!c.update(std::numeric_limits<float>::max(),0,0)&&c.frames()==60);
 check(!c.restore(61)&&c.frames()==60);check(!c.restore(~0u)&&c.frames()==60);
 for(unsigned n=60;n>0;--n){check(c.update(0,-21,0)&&c.frames()==n-1);}
 check(c.formationable());check(c.update(0,0,21)&&c.frames()==0);
 check(c.restore(1)&&!c.formationable());check(c.update(0,0,20)&&c.frames()==1);
 check(c.update(0,0,20.01f)&&c.frames()==0);c.disband();c.reset();check(c.frames()==0);
 for(unsigned n=0;n<=60;++n){check(c.restore(n)&&c.frames()==n&&c.formationable()==(n==0));}
 std::printf("PASS ORIGINAL_CONTACT_CLOCK checks=%u\n",checks);return 0;
}

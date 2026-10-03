#include "p2_original_snagret_captain_guard.h"
#include <cassert>
#include <limits>
int main(int argc,char**){
 if(argc==2){p2_fixture_require_captain(true,true,0,0);return 1;}
 assert(!p2_fixture_captain_down(false,false,100));
 assert(!p2_fixture_captain_down(false,false,1.5f));
 assert(p2_fixture_captain_down(false,false,1));
 assert(p2_fixture_captain_down(true,false,100));
 assert(p2_fixture_captain_down(false,true,100));
 assert(p2_fixture_captain_down(false,false,std::numeric_limits<float>::quiet_NaN()));
 assert(p2_fixture_captain_down(false,false,std::numeric_limits<float>::infinity()));
 return 0;
}

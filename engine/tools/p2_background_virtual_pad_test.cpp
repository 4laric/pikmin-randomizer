#include "pc_background_virtual_pad.h"
#include <cstdio>
#include <cstdlib>
static void require(bool ok,const char* name){if(!ok){std::printf("FAIL %s\n",name);std::exit(1);}std::printf("PASS %s\n",name);}
int main(){
 require(pc_background_virtual_pad_allowed(0,true,true,true,true),"selected_virtual_P1");
 require(!pc_background_virtual_pad_allowed(0,true,true,true,false),"physical_P1_rejected");
 require(!pc_background_virtual_pad_allowed(0,true,false,true,true),"unready_session_rejected");
 require(!pc_background_virtual_pad_allowed(0,false,true,true,true),"background_flag_off_rejected");
 require(!pc_background_virtual_pad_allowed(0,true,true,false,true),"implicit_selection_rejected");
 require(!pc_background_virtual_pad_allowed(1,true,true,true,true),"P2_rejected");
 require(!pc_background_virtual_pad_allowed(-1,true,true,true,true),"invalid_player_rejected");
}

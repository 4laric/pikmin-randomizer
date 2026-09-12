// Manual, bounded entrance only. Production cave process remains separate.
#define main previous_boundary_main
#include "pikmin2_entrance_fixture.cpp"
#undef main
#include "pc_p2_cave.h"
#include <atomic>
#include <fstream>
#include <string>

static std::atomic<bool> descend{false};
static std::atomic<bool> settingsOpen{false};
static bool returned=false;
static std::string entryToken;
// Private link uses --wrap=pc_window_set_settings_menu_open. Forward all behavior.
extern "C" void __real_pc_window_set_settings_menu_open(bool);
extern "C" void __wrap_pc_window_set_settings_menu_open(bool open){
 settingsOpen=open;__real_pc_window_set_settings_menu_open(open);
}
static int filterInput(void*, SDL_Event* event){
 if(event->type==SDL_KEYDOWN || event->type==SDL_KEYUP){
  const auto key=event->key.keysym.scancode;
  // This private App owns F6; do not also queue pc_window's cave request.
  if(key==SDL_SCANCODE_F6){
   if(event->type==SDL_KEYDOWN && !event->key.repeat && !returned && !settingsOpen)descend=true;
   return 0;
  }
 }
 return 1;
}
class ManualEntranceApp:public PlugPikiApp {
public:
 int idle() override {
  const int result=PlugPikiApp::idle();
  if(pc_p2_preview_ready() && pc_p2_preview_treasure())
   pc_p2_preview_treasure()->mConfig->mCarryMinPikis.mValue=1000;
  if(SDL_Window* w=SDL_GL_GetCurrentWindow())SDL_SetWindowTitle(w,returned?
   "Pikipelago bounded entrance - returned | Trip complete; close to stop":
   "Pikipelago bounded entrance - radius 60 | F6 at orange marker: enter cave");
  if(!descend.exchange(false) || settingsOpen)return result;
  // Existing native pause, actor, anchor, living-squad and confirmation guards.
  if(!pc_p2_cave_checkpoint(true))return result;
  Navi* n=naviMgr->getNavi();
  std::ofstream pos("surface-position.tmp");pos.precision(9);
  pos<<entryToken<<'\n'<<n->mSRT.t.x<<' '<<n->mSRT.t.y<<' '<<n->mSRT.t.z<<'\n';
  pos.close();
  if(!pos || std::rename("surface-position.tmp","surface-position.txt")!=0){
   std::fprintf(stderr,"Manual entrance position commit failed; preserve run for recovery.\n");
   std::fflush(nullptr);std::_Exit(3);
  }
  std::puts("P2_MANUAL_ENTRANCE_HANDOFF");std::fflush(nullptr);std::_Exit(42);
 }
};
int main(int argc,char**argv){
 std::ifstream mode("manual-entrance.txt");std::string value;mode>>value;
 if(value!="enter" && value!="returned")return 3;returned=value=="returned";
 std::ifstream entry("p2-cave-entry.txt");std::string header;entry>>header>>entryToken;
 if(header!="P2_CAVE_ENTRY_1" || entryToken.size()!=32)return 3;
 SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 if(!pc_pikipelago_room_preview() || !pc_window_init("Pikipelago bounded entrance",960,720))return 3;
 pc_settings_init();SDL_SetEventFilter(filterInput,nullptr);
 gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();
 gsys->run(new ManualEntranceApp());return 0;
}

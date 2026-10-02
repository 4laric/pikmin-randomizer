// Production state consumer + host publication tests; not paired gameplay (#1148).
#include "pc_randomizer.h"
#include "pc_p2_ship_store.h"
#include "netplay/pc_netplay_randstate.h"
#include <filesystem>
#include <fstream>
#include <sstream>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#ifdef _WIN32
#include <process.h>
#define TEST_PID _getpid()
#else
#include <unistd.h>
#include <sys/wait.h>
#define TEST_PID getpid()
#endif
namespace {pc_randstate::PcRandState published;bool have=false;int failures=0;uint64_t invalidBefore=0;
void invalid_exit() {std::printf("INVALID_ATOMIC_%s\n",pc_randomizer_hash()==invalidBefore?"UNCHANGED":"MUTATED");}
}
#define CHECK(x) do{if(!(x)){std::printf("FAIL %d %s\n",__LINE__,#x);++failures;}}while(0)
bool pc_netplay_session_active(){return true;}
bool pc_netplay_is_host(){return true;}
bool pc_netplay_randstate_stream_enabled(){return true;}
void pc_netplay_randstate_publish(const pc_randstate::PcRandState& s){published=s;have=true;}
bool pc_netplay_hold_active(){return false;}
uint32_t pc_netplay_current_frame(){return 64;}
int main(int argc,char**argv){
 namespace fs=std::filesystem;
 const bool tl=argc>1&&!std::strcmp(argv[1],"thelynk");
 const auto root=fs::temp_directory_path()/("coop-state-consumer-"+std::to_string(TEST_PID));
 const std::string sessionToken(64,'b');
 const auto run=root/"runs"/sessionToken;fs::create_directories(run);
 const char* token=sessionToken.c_str();const std::string fingerprint(64,'a');
 if(argc==3) {
  const std::string fault=argv[2];const auto log=root/"negative.log";
  const std::string command="\"\""+std::string(argv[0])+"\" "+(tl?"thelynk":"p1")+" "+fault+" child > \""+log.string()+"\" 2>&1\"";
#ifdef _WIN32
  const int result=std::system(command.c_str());
#else
  const int raw=std::system(command.substr(1,command.size()-2).c_str());
  const int result=WIFEXITED(raw)?WEXITSTATUS(raw):-1;
#endif
  std::ifstream input(log);std::string text((std::istreambuf_iterator<char>(input)),{});input.close();
  CHECK(result==2);
  std::string expected="noncanonical net randomizer state";
  if(fault=="bad-mode")expected="net randomizer state differs from authenticated bootstrap";
  if(fault=="bad-unknown")expected=tl?"unsupported or malformed bootstrap":"invalid state: identity, version or range mismatch";
  if(fault=="bad-trailing")expected=tl?"trailing TheLynk state":"invalid state: identity, version or range mismatch";
  if(fault=="bad-progression")expected=tl?"invalid/retracted TheLynk inventory":"state attempted to retract received progression";
  CHECK(text.find(expected)!=std::string::npos);
  CHECK(text.find("INVALID_ATOMIC_UNCHANGED")!=std::string::npos);
  CHECK(text.find("INVALID_ATOMIC_MUTATED")==std::string::npos);
  std::printf("negative exit%d: %s",result,text.c_str());fs::remove_all(root);return failures?1:0;
 }
 std::ostringstream bootstrap,state;
 if(tl){
  bootstrap<<"PIKMIN_THELYNK 1\nSESSION "<<token<<"\nFINGERPRINT "<<fingerprint<<"\nCHECKS 330";
  for(unsigned i=0;i<330;++i)bootstrap<<' '<<(i<30?71400+i:71500+i-30);
  bootstrap<<"\nEND\n";
  state<<"THELYNK_STATE 1 "<<token<<" 1 "<<((1u<<30)-1)<<" CHECKS 2 71429 71799 BONUSES";
  for(int i=0;i<18;++i)state<<" 1";
 }else{
  bootstrap<<"PIKMIN_RANDOMIZER 9\nSESSION "<<token<<"\nFINGERPRINT "<<fingerprint
   <<"\nPROFILE foh-day2\nCATALOG gameplay-checks-v9\nPLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\nCOLOR red\nCHECKSET 6\nENEMIES 0\nBENEFITS 1\nMATURITY 1\nDAY_LENGTH 3 25\nWHISTLE_PLUCK 1\nDEATHLINK 1\nEND\n";
  state<<"PIKMIN_STATE 9 "<<token<<" 1 25 0 0 CHECKS 1 57 BENEFITS 2 0 0 0 0 MATURITY 1 2 0 DAYLENGTH 3 WHISTLEPLUCK 1 DEATHLINK 16909060";
 }
 state<<" END\n";
 {std::ofstream b(run/"bootstrap.txt");b<<bootstrap.str();std::ofstream t(run/"state.txt");t<<state.str();}
 std::string path=(run/"bootstrap.txt").string();char seed[]="--randomizer-seed";char name[]="state_test";char* args[]={name,seed,path.data()};
 CHECK(pc_randomizer_init(3,args));CHECK(have);CHECK(published.mode==(tl?2:1));CHECK(published.gen==1);
 // Host poll publishes only; simulation state waits for the common-frame apply.
 CHECK(pc_randomizer_repairs()==0);
 uint8_t wire[pc_randstate::kStateBytes];pc_randstate::encode(published,wire);pc_randstate::PcRandState decoded;
 CHECK(pc_randstate::decode(wire,sizeof(wire),decoded));
 CHECK(pc_randomizer_apply_net_state(decoded));
 pc_randstate::PcRandState actual;CHECK(pc_randomizer_get_net_state(&actual));CHECK(pc_randstate::payload_equal(decoded,actual));
 CHECK(pc_randomizer_repairs()==(tl?30:25));
 if(argc>3) {
  invalidBefore=pc_randomizer_hash();std::atexit(invalid_exit);
  const std::string fault=argv[2];
  if(fault=="bad-unknown"||fault=="bad-trailing") {
   std::string malformed=state.str();
   if(fault=="bad-unknown")malformed.insert(malformed.rfind("END"),"UNKNOWN 1 ");
   else malformed+="UNKNOWN\n";
   {std::ofstream output(run/"state.txt");output<<malformed;}
   pc_randomizer_force_net_publish();return 0;
  }
  if(fault=="bad-progression"){if(tl)decoded.thelynkParts=0;else decoded.repairs=0;}
  else if(fault=="bad-mode")decoded.mode=tl?1:2;
  else if(tl)decoded.maturity[0]=1;else decoded.thelynkBonuses[17]=1;
  pc_randomizer_apply_net_state(decoded);return 0; // Parent requires exit2 and precise refusal/atomicity markers.
 }
 if(tl){CHECK(actual.checkCount==330);CHECK(actual.thelynkBonuses[17]==1);CHECK(actual.checks[329/8]&(1u<<(329%8)));}
 else{CHECK(pc_randomizer_maturity(0)==1&&pc_randomizer_maturity(1)==2);CHECK(pc_randomizer_whistle_pluck()==1);CHECK(pc_randomizer_day_length_multiplier()==1.75f);}
 const auto h=pc_randomizer_hash();CHECK(pc_randomizer_apply_net_state(decoded));CHECK(pc_randomizer_hash()==h);
 p2ship::stock.counts[0][0]++;CHECK(pc_randomizer_hash()!=h);p2ship::stock.counts[0][0]--;CHECK(pc_randomizer_hash()==h);
 if(tl){CHECK(pc_randomizer_thelynk_bonus(17)>0);pc_randomizer_thelynk_consume(17);}
 else CHECK(pc_randomizer_consume_benefit(static_cast<PcBenefit>(0)));
 CHECK(pc_randomizer_hash()!=h);
 if(!tl) {
  decoded.deathLinks=UINT32_MAX;CHECK(pc_randomizer_apply_net_state(decoded));
  for(int i=0;i<3;++i){CHECK(pc_randomizer_deathlink_casualties()==1);pc_randomizer_deathlink_consume(1);}
  CHECK(pc_randomizer_deathlink_casualties()==0);
  CHECK(pc_randomizer_apply_net_state(decoded));CHECK(pc_randomizer_deathlink_casualties()==0);
 }
 fs::remove_all(root);std::printf("STATE_CONSUMER_PASS failures=%d\n",failures);return failures?1:0;
}

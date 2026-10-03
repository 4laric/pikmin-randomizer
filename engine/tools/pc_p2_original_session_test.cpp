#include "pc_p2_original_session.h"
#include "pc_p2_original_source_uid.h"
#include "pc_p2_original_progress.h"
#include <chrono>
#include <filesystem>
#include <iostream>
#include <stdexcept>
static unsigned checks=0;
static void check(bool ok){++checks;if(!ok)throw std::runtime_error("original session control "+std::to_string(checks));}
static void save(const std::string& name,const std::string& bytes){std::ofstream file(name,std::ios::binary);file.write(bytes.data(),bytes.size());check(bool(file));}
int main(int argc,char** argv){
 check(argc==2);auto root=std::filesystem::absolute(argv[1])/std::to_string(std::chrono::steady_clock::now().time_since_epoch().count());
 check(std::filesystem::create_directories(root/"p2-original"));check(std::filesystem::create_directories(root/"assets"));std::filesystem::current_path(root);
 const std::string campaign(64,'a');std::string reason,bytes;std::map<std::string,std::string> files;
 for(const char* course:{"tutorial","forest","yakushima","last"}){
  p2original::SourceManifest m;m.fingerprint=campaign;p2original::CatalogRow row;row.course=course;row.member="defaultgen.txt";row.index=0;row.sourceKey=std::string(course)+"/defaultgen.txt#0";row.enemy.uid=p2original::originalGeneratorUid(row.sourceKey);row.enemy.count=1;row.enemy.generatorVersion="0001";row.enemy.generatorTail={"3","1","2"};
  p2original::GeneratorState state;state.uid=row.enemy.uid;state.count=1;state.reserved=5;state.resurrectionDays=-1;m.rows={row};m.literal={state};
  check(p2original::writeSourceManifest(m,course,bytes,reason));const auto path=std::string("p2-original/")+course+".p2c";files[path]=p2treasureplacements::hash(bytes);save(path,bytes);
 }
 p2original::PikiManifest pikis;pikis.campaign=campaign;p2original::PikiSourceRecord row;row.sourceKey="tutorial/defaultgen.txt#1";row.sourceSha=std::string(64,'b');row.spawn.uid=p2original::originalSourceCatalogUid(row.sourceKey);row.spawn.count=5;row.spawn.species=1;row.spawn.wildParameter=1;pikis.rows={row};
 check(p2original::writePikiManifest(pikis,bytes,reason));files["p2-original/campaign.p2pk"]=p2treasureplacements::hash(bytes);save("p2-original/campaign.p2pk",bytes);
 const std::string rawStages="selected original calendar control";
 files["p2-original/stages.txt"]=p2treasureplacements::hash(rawStages);save("p2-original/stages.txt",rawStages);
 std::ostringstream calendar;calendar<<"P2_SOURCE_CALENDAR 1 "<<campaign<<' '<<p2treasureplacements::hash(rawStages)<<" 4\n";
 for(const char* course:{"tutorial","forest","yakushima","last"}){const bool tutorial=std::string(course)=="tutorial";calendar<<course<<" 1\ndefaultgen.txt "<<std::string(64,'b')<<' '<<(tutorial?2:1)<<'\n';calendar<<p2original::originalGeneratorUid(std::string(course)+"/defaultgen.txt#0")<<" 0 teki\n";if(tutorial)calendar<<row.spawn.uid<<" 1 piki\n";calendar<<"0\n0\n";}calendar<<"END\n";
 bytes=calendar.str();files["p2-original/calendar.p2sc"]=p2treasureplacements::hash(bytes);save("p2-original/calendar.p2sc",bytes);
 bytes="actual physical input control";files["assets/terrain.bin"]=p2treasureplacements::hash(bytes);save("assets/terrain.bin",bytes);
 const std::string bank="explicit selected source bank";files["p2-original-egg-bank.txt"]=p2treasureplacements::hash(bank);save("p2-original-egg-bank.txt",bank);
 std::ostringstream out;out<<"P2_ORIGINAL_SESSION 1 "<<campaign<<' '<<files.size()<<'\n';for(const auto& f:files)out<<f.first<<' '<<f.second<<'\n';out<<"END\n";const auto descriptor=out.str(),fingerprint=p2treasureplacements::hash(descriptor);save("p2-original-session.txt",descriptor);
 p2originalsession::Bundle bundle;check(p2originalsession::load(fingerprint,campaign,bundle,reason));check(bundle.files==files);check(!p2original::originalProgress().ready());
 std::string selectedInput="old output";check(p2originalsession::input(bundle,"p2-original-egg-bank.txt",selectedInput,reason));check(selectedInput==bank);
 save("p2-original-egg-bank.txt","changed source bank");check(!p2originalsession::input(bundle,"p2-original-egg-bank.txt",selectedInput,reason));check(selectedInput==bank);
 check(!p2originalsession::input(bundle,"assets/unselected.bin",selectedInput,reason));check(selectedInput==bank);
 check(!p2originalsession::input(bundle,"p2-original/../card.sav",selectedInput,reason));check(selectedInput==bank);
 check(!p2originalsession::load(fingerprint,campaign,bundle,reason));save("p2-original-egg-bank.txt",bank);check(p2originalsession::load(fingerprint,campaign,bundle,reason));
 check(p2originalsession::path("size20-joints.txt"));check(!p2originalsession::path("p2-original-unknown-bank.txt"));
 for(std::size_t n=0;n<descriptor.size()-1;++n){auto old=bundle;check(!p2originalsession::parse(descriptor.substr(0,n),fingerprint,campaign,bundle));check(bundle.files==old.files);}
 check(!p2originalsession::parse(descriptor,fingerprint,std::string(64,'c'),bundle));
 save("assets/terrain.bin","changed physical terrain");check(!p2originalsession::load(fingerprint,campaign,bundle,reason));check(!p2original::originalProgress().ready());save("assets/terrain.bin",bytes);
 bytes="corrupt selected manifest";save("p2-original/tutorial.p2c",bytes);check(!p2originalsession::load(fingerprint,campaign,bundle,reason));
 for(const char* p:{"assets/../card.sav","assets//x","p2-original/./x","assets/x:y","/assets/x","assets/x\\y"})check(!p2originalsession::path(p));
 std::cout<<"PASS original immutable session "<<checks<<" controls (codec/inputs only) profile="<<root.string()<<'\n';
}

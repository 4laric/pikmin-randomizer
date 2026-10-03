#pragma once
#include "pc_p2_original_manifest.h"
#include "pc_p2_original_piki_manifest.h"
#include "pc_p2_original_calendar.h"
#include "pc_p2_campaign_treasure_config.h"
#include <map>
namespace p2originalsession {
// The bootstrap fingerprint is the SHA256 of this exact immutable descriptor.
// Environment variables can locate resources but cannot select their identity.
struct Bundle {std::string campaign;std::map<std::string,std::string> files;};
inline bool rootInput(const std::string& p){
 for(const char* name:{"p2-treasure-placements.txt","p2-treasure-catalog.txt",
 "p2-pelplant-resources.txt","p2-chappy-bank.txt","p2-frog.txt","p2-uji-bank.txt",
 "p2-ground-bank.txt","p2-original-red-bank.txt","p2-kochappy-profile.txt",
 "p2-original-tank-bank.txt","foliage-bank.txt","p2-aquatic-bank.txt",
 "p2-snagret-bank.txt","p2-flying-bank.txt","p2-hanachirashi-joints.txt",
 "p2-original-cannon-bank.txt","p2-original-cannon-attach.txt","p2-original-stone-bank.txt",
 "p2-original-gas-bank.txt","p2-original-egg-bank.txt","p2-original-wisp-bank.txt",
 "p2-original-honey-bank.txt"})if(p==name)return true;
 for(unsigned size:{1u,5u,10u,20u})for(const char* kind:{"bank","joints"})
  if(p=="size"+std::to_string(size)+"-"+kind+".txt")return true;
 return false;
}
inline bool path(const std::string& p){
 if(rootInput(p))return true;
 if(p.empty()||p.size()>512||(p.compare(0,7,"assets/")&&p.compare(0,12,"p2-original/")))return false;
 std::size_t start=0;
 for(std::size_t i=0;i<=p.size();++i){
  if(i==p.size()||p[i]=='/'){const auto part=p.substr(start,i-start);if(part.empty()||part=="."||part=="..")return false;start=i+1;}
  else if(!((p[i]>='a'&&p[i]<='z')||(p[i]>='A'&&p[i]<='Z')||(p[i]>='0'&&p[i]<='9')||p[i]=='_'||p[i]=='-'||p[i]=='.'))return false;
 }return true;
}
inline bool parse(const std::string& bytes,const std::string& fingerprint,const std::string& campaign,Bundle& out){
 if(bytes.empty()||bytes.size()>16*1024*1024||!p2treasurestate::digest(fingerprint)||!p2treasurestate::digest(campaign)||p2treasureplacements::hash(bytes)!=fingerprint)return false;
 std::istringstream in(bytes);std::string magic,version,name,hash,previous;unsigned count=0;Bundle next;
 if(!(in>>magic>>version>>next.campaign>>count)||magic!="P2_ORIGINAL_SESSION"||version!="1"||next.campaign!=campaign||count<5||count>65536)return false;
 for(unsigned i=0;i<count;++i){if(!(in>>name>>hash)||!path(name)||!p2treasurestate::digest(hash)||(!previous.empty()&&name<=previous)||!next.files.emplace(name,hash).second)return false;previous=name;}
 if(!(in>>name)||name!="END"||(in>>name))return false;
 for(const char* course:{"tutorial","forest","yakushima","last"})if(!next.files.count(std::string("p2-original/")+course+".p2c"))return false;
 if(!next.files.count("p2-original/campaign.p2pk"))return false;
 if(!next.files.count("p2-original/calendar.p2sc")||!next.files.count("p2-original/stages.txt"))return false;
 out=std::move(next);return true;
}
inline bool input(const Bundle& bundle,const std::string& role,std::string& bytes,std::string& error){
 if(!path(role)){error="original immutable input path invalid";return false;}
 const auto found=bundle.files.find(role);std::string next;
 if(found==bundle.files.end()||!p2treasureplacements::bounded(role,128*1024*1024,next)
    ||p2treasureplacements::hash(next)!=found->second){error="original immutable input is absent or changed: "+role;return false;}
 bytes=std::move(next);error.clear();return true;
}
inline bool verify(const Bundle& bundle,std::string& error){
 // Hash every selected physical input before adopting scalar state or spawning.
 for(const auto& entry:bundle.files){std::string bytes;if(!p2treasureplacements::bounded(entry.first,128*1024*1024,bytes)||p2treasureplacements::hash(bytes)!=entry.second){error="original session physical input changed: "+entry.first;return false;}}
 std::set<unsigned> sources;
 std::string calendarBytes,rawStages;
 p2original::SourceCalendar calendar;
 if(!input(bundle,"p2-original/calendar.p2sc",calendarBytes,error)||calendarBytes.size()>16*1024*1024
    ||!input(bundle,"p2-original/stages.txt",rawStages,error)||rawStages.size()>1024*1024
    ||!calendar.read(calendarBytes,bundle.campaign,p2treasureplacements::hash(rawStages),error))return false;
 for(const char* course:{"tutorial","forest","yakushima","last"}){
  std::string bytes;p2original::SourceManifest manifest;
  if(!input(bundle,std::string("p2-original/")+course+".p2c",bytes,error)||bytes.size()>4*1024*1024||!p2original::readSourceManifest(bytes,course,manifest,error)||manifest.fingerprint!=bundle.campaign)return false;
  for(const auto& row:manifest.rows){std::string key;const auto* source=calendar.source(row.enemy.uid,&key);
   if(!source||source->kind!="teki"||key!=row.sourceKey||!sources.insert(row.enemy.uid).second){error="original source UID/calendar identity mismatch";return false;}}
 }
 std::string bytes;p2original::PikiManifest pikis;
 if(!input(bundle,"p2-original/campaign.p2pk",bytes,error)||bytes.size()>4*1024*1024||!p2original::readPikiManifest(bytes,pikis,error)||pikis.campaign!=bundle.campaign)return false;
 for(const auto& row:pikis.rows){std::string key,sha;const auto* source=calendar.source(row.spawn.uid,&key,&sha);
  if(!source||source->kind!="piki"||key!=row.sourceKey||sha!=row.sourceSha||!sources.insert(row.spawn.uid).second){error="original Piki source calendar identity mismatch";return false;}}
 for(const auto& course:calendar.courses())for(const auto& member:course.second.members)for(const auto& row:member.second.sources)
  if((row.kind=="piki"||row.kind=="teki")&&!sources.count(row.uid)){error="original immutable actor manifest omitted calendar source";return false;}
 error.clear();return true;
}
inline bool load(const std::string& fingerprint,const std::string& campaign,Bundle& out,std::string& error){
 std::string bytes;Bundle next;
 if(!p2treasureplacements::bounded("p2-original-session.txt",16*1024*1024,bytes)||!parse(bytes,fingerprint,campaign,next)||!verify(next,error))return false;
 out=std::move(next);return true;
}
}

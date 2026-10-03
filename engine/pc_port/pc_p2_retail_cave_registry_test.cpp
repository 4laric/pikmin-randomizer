#include "pc_p2_retail_cave_registry.h"
#include "pc_p2_retail_cave_plan.h"
#include <cassert>
#include <fstream>
#include <iostream>
int main(int argc,char** argv){
 std::vector<p2original::CatalogRow> rows;std::string error;
 assert(p2retail::catalogRows("tutorial_1",2,rows,error)&&rows.size()==5);
 assert(rows[0].enemy.source==6&&rows[1].enemy.source==45&&rows[2].enemy.source==91&&rows[3].enemy.source==92&&rows[4].enemy.source==47);
 p2original::Catalog catalog;unsigned callbacks=0;
 auto capability=[&](const p2original::CatalogRow& row,std::string&){++callbacks;return row.sourceForm==p2original::SourceForm::CaveTekiInfo;};
 const auto& pin=p2retail::descriptor("tutorial_1")->catalogSha256;
 assert(catalog.install(pin,rows,capability,error)&&callbacks==5);
 auto forged=rows;forged[0].caveSourceSha256[0]='0';callbacks=0;
 assert(!catalog.install(pin,forged,capability,error)&&callbacks==0);
 forged=rows;forged[0].enemy.source=4;assert(!catalog.install(pin,forged,capability,error));
 forged=rows;forged[0].sourceForm=p2original::SourceForm::SurfaceGenEnemy;
 assert(!catalog.install(pin,forged,capability,error));
 assert(!p2retail::catalogRows("engineeredforest_1",1,rows,error));
 if(argc==3){
  std::ifstream in(argv[1],std::ios::binary);std::string bytes((std::istreambuf_iterator<char>(in)),{});
  p2retail::FloorPlan plan;
  assert(p2retail::parseFloorPlan(bytes,argv[2],plan,error));
  assert(plan.cave=="tutorial_1"&&plan.actors.size()==(plan.floor==1?6u:22u));
  bytes[0]='X';assert(!p2retail::parseFloorPlan(bytes,argv[2],plan,error));
 }
 std::cout<<"PASS authenticated cave registry/source-form/forged-source/selected-plan policy\n";
}

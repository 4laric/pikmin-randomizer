#pragma once
#include "pc_p2_original_catalog.h"
#include "pc_p2_retail_cave_context.h"

namespace p2retail {
// Reuse the original native registry's UID/ordinal/epoch/activation machinery.
// This is a TekiInfo association envelope, never a synthetic GenEnemy record.
inline bool catalogRows(const std::string& id,unsigned number,
                        std::vector<p2original::CatalogRow>& out,std::string& error){
 const auto* cave=descriptor(id);const auto* floor=cave?definition(*cave,number):nullptr;
 if(!floor){error="retail cave descriptor missing";return false;}
 std::vector<p2original::CatalogRow> next;
 for(unsigned index=0;index<floor->rows.size();++index){
  const auto& source=floor->rows[index];
  if(source.kind=="loose_treasure")continue; // owned by canonical treasury
  if(source.sourceId<0||source.minimum()>10||source.weight()){
   error="retail cave literal requires unsupported selection/count";return false;
  }
  p2original::CatalogRow row;
  row.course=cave->cave;row.member=cave->source;row.index=number*256+index;
  row.sourceKey=row.course+"/"+row.member+"#"+std::to_string(row.index);
  row.enemy.uid=p2original::originalGeneratorUid(row.sourceKey);
  row.enemy.source=unsigned(source.sourceId);row.enemy.count=source.minimum();
  row.enemy.generatorVersion="CAVE";
  row.sourceForm=p2original::SourceForm::CaveTekiInfo;
  row.caveFloor=number;row.caveRow=index;row.caveSourceSha256=cave->sourceSha256;
  next.push_back(std::move(row));
 }
 out=std::move(next);error.clear();return true;
}
}

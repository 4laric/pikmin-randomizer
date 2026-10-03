#pragma once
#include "pc_p2_original_piki_spawn.h"
#include <vector>
namespace p2original {
struct PikiSourceRecord {
 std::string sourceKey,sourceSha,recordVersion="v0.3",objectVersion="0001";
 PikiSpawnRecord spawn;
 unsigned reserved=0;
 int resurrectionDays=0,dayLimit=-1;
};
// One immutable all-calendar catalog across all surface courses. Campaign
// selection and literal catalog digest are distinct authenticated bindings.
struct PikiManifest {std::string campaign,catalog;std::vector<PikiSourceRecord> rows;};
bool validatePikiSource(const PikiSourceRecord&,std::string&);
bool writePikiManifest(const PikiManifest&,std::string& bytes,std::string&);
bool readPikiManifest(const std::string& bytes,PikiManifest&,std::string&);
// Selected calendar census, separately bound to full catalog/campaign/day.
bool writePikiActive(const PikiManifest&,const std::string& course,unsigned day,const std::vector<unsigned>&,std::string& bytes,std::string&);
bool readPikiActive(const std::string& bytes,const PikiManifest&,const std::string& course,unsigned day,std::vector<unsigned>&,std::string&);
}

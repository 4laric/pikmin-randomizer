#pragma once
#include "pc_p2_original_catalog.h"
#include "pc_p2_original_lifecycle.h"
namespace p2original {
struct SourceManifest {
 std::string fingerprint;
 std::vector<CatalogRow> rows;
 std::vector<GeneratorState> literal;
};
// Private staging sidecar. Canonical little-endian scalars, exact source
// floats and a SHA256 integrity trailer; contains no original game assets.
bool readSourceManifest(const std::string& bytes,const std::string& course,SourceManifest&,std::string&);
bool writeSourceManifest(const SourceManifest&,const std::string& course,std::string&,std::string&);
}

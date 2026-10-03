#pragma once
#include "pc_p2_original_honey_snapshot.h"
#include <array>
namespace p2originalresource { namespace honey {
// Both fingerprints are required actual installed identities; no defaults.
// Campaign fingerprint binds the envelope. Every row separately preserves its
// source catalog fingerprint, which may differ and is checked against journal.
// The journal is explicitly course-local. Rows must cover every born Honey
// child, including terminal history. An active receiver must be refused by the
// native snapshot owner before this pointer-free body codec is called.
bool encodeSnapshots(const std::vector<Snapshot>&,const std::string& campaignFingerprint,const std::string& sourceBankFingerprint,const std::array<ReceiverClip,7>&,const EggContents&,std::string& out,std::string& error);
bool decodeSnapshots(const std::string&,const std::string& campaignFingerprint,const std::string& sourceBankFingerprint,const std::array<ReceiverClip,7>&,const EggContents&,std::vector<Snapshot>& out,std::string& error);
} }

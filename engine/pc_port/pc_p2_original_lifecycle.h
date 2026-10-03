#pragma once
#include <cstdint>
#include <string>
namespace p2original {
// Original gameGenerator.cpp enemy-group cache, not P1 alive/latest-spawn-day
// semantics. count is the prevalidated Teki count (retail placement capacity10);
// non-Teki object/creature cache adapters require their own typed payloads.
struct GeneratorState {
 unsigned uid=0,count=0,reserved=0,deathCount=0,dayNum=0;
 int resurrectionDays=0,dayLimit=-1;
 std::uint64_t epoch=0,activation=0;
};
struct GenerationDecision {GeneratorState next;bool generate=false,expired=false,resetDeaths=false;unsigned remaining=0;};
// No RNG/birth/floor/global writes. A real adapter commits next only after its
// group transaction is owned. RAM without TrackDeath loads saved creatures
// separately; generate=false must never be interpreted as discard saved actors.
bool decideOriginalGeneration(const GeneratorState&,unsigned currentDay,bool disc,GenerationDecision&,std::string&);
// Advance once for ordinary course entry/RAM rehydration before any birth or
// cached creature load. Do NOT call during full fresh-process checkpoint scene
// restore: that operation preserves exact saved activation and graph refs.
bool beginOriginalActivation(const GeneratorState&,GeneratorState&,std::string&);
bool originalDeath(const GeneratorState&,GeneratorState&,std::string&);
// Native OGC2 cache payload carries original counters, epoch and catalog binding.
// It is distinct from AP SLT1. Decoder validates checksum/binding/UID/count and
// outputs atomically; enclosing native cache owns publication and actor state.
bool encodeOriginalState(const std::string& fingerprint,const GeneratorState&,std::string& bytes,std::string&);
bool decodeOriginalState(const std::string& fingerprint,unsigned uid,unsigned count,const std::string& bytes,GeneratorState&,std::string&);
}

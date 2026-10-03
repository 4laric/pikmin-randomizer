#pragma once
#include "pc_midday_render_descriptors.h"
namespace pc_midday {
struct PrototypeTextureBinding {u32 materialSlot=0;u64 id=0,factory=0;};
struct PrototypeShapeBinding {
 u64 content=0;BaseShape* model=nullptr;
 u64 materials=0,materialFactory=0,tevs=0,tevFactory=0;
 std::vector<PrototypeTextureBinding> textures;
};
struct PrototypeRenderCensus {
 u64 generation=0;
 std::vector<RenderObservation> observations;
 std::set<u64> required;
 RenderDescriptorIndex descriptors;
};
// Bindings come from the source-defined loaded scene asset inventory, never
// checkpoint pointers. Capture all initialized prototype allocations, not merely
// those selected by active instances. Caller retains installed model backing and
// the stopped initialized whole scene through this observation and later capture.
// This component does not assert that the caller's model list is the full scene.
bool observePrototypeRender(u64 generation,const std::vector<PrototypeShapeBinding>&,
 const ConstructorFence&,PrototypeRenderCensus&,std::string&);
}

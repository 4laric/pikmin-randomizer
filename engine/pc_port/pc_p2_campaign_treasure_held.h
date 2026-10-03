#pragma once
#include <string>
class BTeki;class Pellet;class UfoItem;class Graphics;struct Matrix4f;struct Vector3f;struct Suckable;
namespace p2original {struct CatalogRow;struct InstanceIdentity;}
bool pc_p2_campaign_treasure_held_resources(const p2original::CatalogRow&,std::string&);
bool pc_p2_campaign_treasure_held_spawn(BTeki*,const p2original::CatalogRow&,const p2original::InstanceIdentity&,
                                     const Vector3f& position,const Vector3f& velocity,std::string&);
Suckable* pc_p2_campaign_treasure_held_goal(Pellet*);
bool pc_p2_campaign_treasure_held_owns(Pellet*);
bool pc_p2_campaign_treasure_held_deliver(Pellet*);
bool pc_p2_campaign_treasure_held_draw(Pellet*,Graphics&,Matrix4f&);
bool pc_p2_campaign_treasure_held_draw_receiver(UfoItem*,Graphics&,const Matrix4f&);
void pc_p2_campaign_treasure_held_retire(Pellet*);
// Pending uncollected physical graphs are not represented by the 201 bits.
// SAVE must refuse them until its typed physical graph owner can restore them.
unsigned pc_p2_campaign_treasure_held_pending();
// Call before course/App-heap teardown, while a refusal can preserve the scene.
bool pc_p2_campaign_treasure_held_unload(std::string&);

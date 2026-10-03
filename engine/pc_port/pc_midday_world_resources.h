#pragma once
#include "pc_midday_actor_archive.h"
class ShapeDynMaterials; class Material; class PVWTextureData; class PVWTevInfo;
class Joint;
class CollGroup;
struct DynCollShape; struct CreaturePlatMgr;
namespace pc_midday {
// Canonical resource records: shared texture arrays are not duplicated per actor.
// Factories allocate from content-bound descriptors before callback-free binding.
// One canonical ResourceId per native allocation; array elements use exact slots.
// Runtime cross-allocation links use AnyLive with exact compiled targetType and
// mandatory source-array/order role checks. Shared content-backed textures use
// Content. ResourceSelf/Subobject only describes the current ResourceId.
bool world_texture_data_fields(PVWTextureData&,ActorArchive&);
bool world_texture_data_schema(const ActorFields&,const std::string&,std::vector<FieldSchema>&,std::string&);
bool world_tev_fields(PVWTevInfo&,ActorArchive&);
bool world_tev_schema(const ActorFields&,const std::string&,std::vector<FieldSchema>&,std::string&);
bool world_material_fields(Material&,ActorArchive&);
bool world_material_schema(const ActorFields&,const std::string&,std::vector<FieldSchema>&,std::string&);
bool world_materials_fields(ShapeDynMaterials&,ActorArchive&);
bool world_materials_schema(const ActorFields&,const std::string&,std::vector<FieldSchema>&,std::string&);
bool world_dyn_shape_fields(DynCollShape&,ActorArchive&);
bool world_dyn_shape_schema(const ActorFields&,const std::string&,std::vector<FieldSchema>&,std::string&);
bool world_platform_fields(CreaturePlatMgr&,ActorArchive&);
bool world_platform_schema(const ActorFields&,const std::string&,std::vector<FieldSchema>&,std::string&);
bool world_joint_fields(Joint&,ActorArchive&);
bool world_joint_schema(const ActorFields&,const std::string&,std::vector<FieldSchema>&,std::string&);
}

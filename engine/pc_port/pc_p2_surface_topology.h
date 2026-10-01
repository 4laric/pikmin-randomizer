#pragma once
#include "pc_p2_surface_topology_policy.h"
class BaseShape;
class CollTriInfo;
class Vector3f;
void pc_p2_surface_topology_reset();
void pc_p2_surface_topology_init(BaseShape* model);
bool pc_p2_surface_topology_owns(BaseShape* model,const CollTriInfo* tri);
const std::vector<p2surface::Incident>* pc_p2_surface_incidents(BaseShape* model,const CollTriInfo* tri,int edge);
p2surface::Crossing pc_p2_surface_continuation(BaseShape* model,const CollTriInfo* tri,int edge,const Vector3f& position);
unsigned pc_p2_surface_ambiguous_queries();

#pragma once
class BaseShape;
class Creature;
class Vector3f;
void pc_p2_surface_water_reset();
void pc_p2_surface_water_init(BaseShape* model);
bool pc_p2_surface_water_active();
int pc_p2_surface_water_count();
int pc_p2_surface_water_box(const Vector3f& position, float radius);
int pc_p2_surface_water_attribute(const Creature* creature, int legacyAttribute);

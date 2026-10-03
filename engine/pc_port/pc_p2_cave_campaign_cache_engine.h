#pragma once
// Called by the ordinary stage provider at its committed entry/return boundary.
// These operations only switch native generator-cache images; no preview flags,
// actor health/count writes, scene loads, or standalone transfer files.
void pc_p2_cave_campaign_cache_enter(int surfaceStage);
void pc_p2_cave_campaign_cache_return();
void pc_p2_cave_campaign_cache_capture();
void pc_p2_cave_campaign_cache_restore_floor();

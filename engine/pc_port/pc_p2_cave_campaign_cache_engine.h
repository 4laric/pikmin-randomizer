#pragma once
// Called by the ordinary stage provider at its committed entry/return boundary.
// These operations only switch native generator-cache images; no preview flags,
// actor health/count writes, scene loads, or standalone transfer files.
// Caller must flush the live Generator/creature state into GeneratorCache
// before entry capture and floor return capture. Return must run before the
// surface scene initializes. These image operations do not perform actor flush,
// party/head persistence, teardown, or map-provider selection themselves.
void pc_p2_cave_campaign_cache_enter(int surfaceStage);
void pc_p2_cave_campaign_cache_return();
void pc_p2_cave_campaign_cache_capture();
void pc_p2_cave_campaign_cache_restore_floor();

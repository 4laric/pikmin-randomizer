#pragma once
class Pellet;
class GoalItem;
class Graphics;
struct Matrix4f;
struct Suckable;
void pc_p2_campaign_treasure_setup();
// Read-only canonical receipt query for equipment/unlock policy. No grant.
bool pc_p2_campaign_treasure_seen(const char* retailId);
Suckable* pc_p2_campaign_treasure_goal(Pellet*);
bool pc_p2_campaign_treasure_deliver(Pellet*);
bool pc_p2_campaign_treasure_draw(Pellet*,Graphics&,Matrix4f&);
bool pc_p2_campaign_treasure_is_pod(GoalItem*);
bool pc_p2_campaign_treasure_draw_pod(GoalItem*,Graphics&,Matrix4f&);

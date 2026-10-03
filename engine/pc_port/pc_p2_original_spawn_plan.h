#pragma once
#include <functional>
#include <string>
#include <vector>
namespace p2original {
struct Position {float x=0,y=0,z=0;};
struct EnemyRecord {
 unsigned source=0,uid=0,birthType=0,count=0,deathCount=0,spawnType=1;
 Position position,offset;
 float directionDegrees=0,appearRadius=100,enemySize=0;
 int treasureCode=0;unsigned pelletColor=3,pelletSize=1,pelletMinimum=1,pelletMaximum=8;
 float pelletProbability=0;
 std::string generatorVersion="????";std::vector<std::string> generatorTail;
};
struct SpawnPlan {EnemyRecord source;std::vector<Position> positions;};
// Read-only common placement from retail GenObjectEnemy::generate. This does
// not validate family admission or translate opaque species generator tails.
// Draw/trig/root math/floor are supplied by the source-qualified engine adapter.
// No native singleton, actor allocation, init or source field is mutated here.
struct Math {
 std::function<bool(float&,std::string&)> draw;
 std::function<bool(float,float&,float&,std::string&)> sinCos;
 std::function<bool(float,float&,std::string&)> squareRoot;
 // Retail interleaves each floor query with that actor birth. A real birth
 // adapter uses false here and performs floor+birth per actor unless it has
 // separately proved that batching floor queries cannot change geometry.
 bool mapAvailable=false;
 std::function<bool(const Position&,float&,std::string&)> floor;
};
// Original source has two ten-element local arrays. Refuse larger counts rather
// than reproducing its overflow or silently truncating content. Output is atomic;
// caller must own rollback of external RNG if a callback fails after draws.
bool planSpawns(const EnemyRecord&,const Math&,SpawnPlan&,std::string&);
}

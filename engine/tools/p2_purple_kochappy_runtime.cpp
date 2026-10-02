// #1155 engineering-preview real receiver diagnostic; no positive actor/state writes.
#include <SDL2/SDL.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include "system.h"
#include "AIConstant.h"
#include "CreatureProp.h"
#include "App.h"
#include "Node.h"
#include "FlowController.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "Kontroller.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Camera.h"
#include "Piki.h"
#include "PikiState.h"
#include "PikiMgr.h"
#include "PikiHeadItem.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "Pellet.h"
#include "teki.h"
#include "TekiPersonality.h"
#include "Generator.h"
#include "MapMgr.h"
#include "Shape.h"
#include "Collision.h"
#include "Route.h"
#include "GameStat.h"
#include "PlayerState.h"
#include <vector>
#include "KeyConfig.h"
#include "pc_bbft.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_kochappy_fsm.h"
#include "pc_kochappy_gather_input.h"
#include "pc_p2_surface_water.h"
#include "pc_p2_purple.h"
#include "pc_p2_kochappy_stun.h"
#include "pc_p2_purple_flight.h"
#include "Boss.h"
#include "Pom.h"
#include "PaniAnimator.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include "p2_fixture_captain_guard.h"
namespace {
constexpr unsigned Target=0x50323101;
// Read-only inherited member pointer applied to the genuine Boss instance.
struct BossObserver:Boss {
 static float frame(Boss& b){return (b.*(&BossObserver::mAnimator)).getCounter();}
 static int motion(Boss& b){return (b.*(&BossObserver::mAnimator)).getCurrentMotionIndex();}
};
SDL_Joystick* pad=nullptr;
bool human(){return std::getenv("P2_PURPLE_KOCHAPPY_HUMAN")!=nullptr;}
void require(bool yes,const char* message){if(!yes){std::printf("FAIL P2_PURPLE_KOCHAPPY %s\n",message);std::fflush(nullptr);std::_Exit(1);}}
float distance(const Vector3f& a,const Vector3f& b){float x=a.x-b.x,z=a.z-b.z;return std::sqrt(x*x+z*z);}
void input(unsigned keys=0,int x=0,int y=0,int cx=0,int cy=0){
 if(!pad)return;
 pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,SDL_JoystickInstanceID(pad));pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_A,(keys&KBBTN_A)!=0);
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_B,(keys&KBBTN_B)!=0);
 SDL_JoystickSetVirtualButton(pad,SDL_CONTROLLER_BUTTON_DPAD_RIGHT,(keys&KBBTN_DPAD_RIGHT)!=0);
 // SDL->PAD divides by256; Controller normalizes the resulting GC axis by74.
 require(x>=-74&&x<=74&&y>=-74&&y<=74&&cx>=-74&&cx<=74&&cy>=-74&&cy<=74,"ordinary GC axis domain");
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(x*256));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(-y*256));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTX,Sint16(cx*256));
 SDL_JoystickSetVirtualAxis(pad,SDL_CONTROLLER_AXIS_RIGHTY,Sint16(-cy*256));SDL_JoystickUpdate();
}
void point(Navi* n,const Vector3f& goal,bool walk,unsigned keys=0,float walkStop=15.f){
 const Vector3f& from=walk?n->mSRT.t:n->mCursorWorldPos;
 float dx=goal.x-from.x,dz=goal.z-from.z,d=std::sqrt(dx*dx+dz*dz);int x=0,y=0;
 if(d>(walk?walkStop:6.f)){const Vector3f& axis=n->controlCamera()->mViewXAxis;float power=walk?65:22;
  x=int(std::lround(power*(dx*axis.x+dz*axis.z)/d));y=int(std::lround(power*(dx*axis.z-dz*axis.x)/d));}
 input(keys,x,y);
}
// ROUTE_GUARD_KERNEL_BEGIN
struct RouteVec {double x,y,z;};
RouteVec rvadd(RouteVec a,RouteVec b){return {a.x+b.x,a.y+b.y,a.z+b.z};}
RouteVec rvsub(RouteVec a,RouteVec b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
RouteVec rvscale(RouteVec a,double s){return {a.x*s,a.y*s,a.z*s};}
double rvdot(RouteVec a,RouteVec b){return a.x*b.x+a.y*b.y+a.z*b.z;}
bool rvfinite(RouteVec a){return std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z);}
RouteVec routeEdgeClosest(RouteVec p,RouteVec a,RouteVec b){auto d=rvsub(b,a);double q=rvdot(d,d);return q>1e-20?rvadd(a,rvscale(d,std::clamp(rvdot(rvsub(p,a),d)/q,0.,1.))):a;}
double routeTriangleDistance(RouteVec p,RouteVec a,RouteVec b,RouteVec c){
 if(!rvfinite(p)||!rvfinite(a)||!rvfinite(b)||!rvfinite(c))return -1.;
 auto ab=rvsub(b,a),ac=rvsub(c,a),ap=rvsub(p,a);double d1=rvdot(ab,ap),d2=rvdot(ac,ap);
 double area=rvdot(ab,ab)*rvdot(ac,ac)-rvdot(ab,ac)*rvdot(ab,ac);
 RouteVec q=a;
 if(area<=1e-12){double best=1e300;for(auto e:{routeEdgeClosest(p,a,b),routeEdgeClosest(p,a,c),routeEdgeClosest(p,b,c)})best=std::min(best,std::sqrt(rvdot(rvsub(p,e),rvsub(p,e))));return best;}
 if(d1<=0&&d2<=0)q=a;
 else {auto bp=rvsub(p,b);double d3=rvdot(ab,bp),d4=rvdot(ac,bp);
  if(d3>=0&&d4<=d3)q=b;
  else {double vc=d1*d4-d3*d2;
   if(vc<=0&&d1>=0&&d3<=0)q=rvadd(a,rvscale(ab,d1/(d1-d3)));
   else {auto cp=rvsub(p,c);double d5=rvdot(ab,cp),d6=rvdot(ac,cp);
    if(d6>=0&&d5<=d6)q=c;
    else {double vb=d5*d2-d1*d6;
     if(vb<=0&&d2>=0&&d6<=0)q=rvadd(a,rvscale(ac,d2/(d2-d6)));
     else {double va=d3*d6-d5*d4;
      if(va<=0&&(d4-d3)>=0&&(d5-d6)>=0)q=rvadd(b,rvscale(rvsub(c,b),(d4-d3)/((d4-d3)+(d5-d6))));
      else {double denom=va+vb+vc;if(!(denom>0))return -1.;q=rvadd(a,rvadd(rvscale(ab,vb/denom),rvscale(ac,vc/denom)));}
     }
    }
   }
  }
 }
 return std::sqrt(rvdot(rvsub(p,q),rvsub(p,q)));
}
// ROUTE_GUARD_KERNEL_END
// Engineering-only original57-face corridor; no actor/terrain coordinates are assigned.
struct ReceiverWaypoint {float x,z;};
constexpr ReceiverWaypoint ReceiverRoute[]={
 {-826.906677246f,2242.203287760f},
 {-819.150024414f,2206.459960938f},
 {-795.126688639f,2184.250000000f},
 {-791.895019531f,2172.310058594f},
 {-789.580017090f,2158.780029297f},
 {-766.015014648f,2135.775024414f},
 {-762.066670736f,2099.743367513f},
 {-750.625000000f,2083.755065918f},
 {-731.703328451f,2073.536743164f},
 {-724.014984131f,2040.390075684f},
 {-706.329996745f,2018.303385417f},
 {-712.565002441f,2000.905029297f},
 {-709.530008952f,1987.540039062f},
 {-687.210021973f,1967.470031738f},
 {-677.363342285f,1915.930013021f},
 {-664.315002441f,1893.489990234f},
 {-651.516662598f,1870.180013021f},
 {-641.794982910f,1818.205017090f},
 {-626.599995931f,1770.376668294f},
 {-626.940002441f,1743.784973145f},
 {-633.093343099f,1714.250000000f},
 {-620.805023193f,1664.950012207f},
 {-619.036682129f,1615.236694336f},
 {-605.855010986f,1595.265014648f},
 {-594.769999186f,1576.760009766f},
 {-594.049987793f,1527.780029297f},
 {-562.023325602f,1498.463338216f},
 {-556.735000610f,1477.820007324f},
 {-546.336659749f,1452.539998372f},
 {-511.754989624f,1420.904968262f},
 {-482.873321533f,1395.869995117f},
 {-461.539993286f,1392.815002441f},
 {-445.309997559f,1393.480021159f},
 {-418.979995728f,1370.305053711f},
 {-388.823333740f,1385.923380534f},
 {-376.809997559f,1381.480041504f},
 {-353.490000407f,1379.253377279f},
 {-317.680007935f,1395.980041504f},
 {-293.490005493f,1415.670043945f},
 {-286.810005188f,1436.105041504f},
 {-283.406672160f,1448.630045573f},
 {-302.555007935f,1445.420043945f},
 {-296.813334147f,1456.350016276f},
 {-306.919998169f,1447.684997559f},
 {-317.833333333f,1442.813313802f},
 {-312.494995117f,1455.639953613f},
 {-325.623331706f,1456.846638997f},
 {-318.604995728f,1468.734985352f},
 {-314.159993490f,1475.893310547f},
 {-328.574996948f,1474.734985352f},
 {-323.533335368f,1510.989990234f},
 {-309.360000610f,1536.854980469f},
 {-297.586669922f,1541.319986979f},
 {-293.745010376f,1566.875000000f},
 {-284.386678060f,1591.430013021f},
 {-289.560012817f,1612.020019531f},
 {-307.103342692f,1638.726684570f},
 {-303.930007935f,1666.340026855f},
 {-275.523340861f,1682.003336589f},
 {-280.450004578f,1702.734985352f},
 {-257.676671346f,1730.246663411f},
 {-277.160003662f,1738.705017090f},
 {-303.799997965f,1762.203328451f},
 {-284.604995728f,1797.234985352f},
 {-254.543329875f,1810.833333333f},
 {-275.749992371f,1823.614990234f},
 {-296.366663615f,1834.543334961f},
 {-266.010002136f,1847.215026855f},
 {-286.523330688f,1859.570027669f},
 {-332.574996948f,1870.340026855f},
 {-363.896667480f,1889.463338216f},
 {-377.044998169f,1905.994995117f},
 {-387.886667887f,1919.460001628f},
 {-368.559997559f,1915.335021973f},
 {-379.196665446f,1929.296671549f},
 {-364.009994507f,1920.750000000f},
 {-351.373331706f,1912.010009766f},
 {-363.285003662f,1925.875000000f},
 {-346.223337809f,1939.156656901f},
 {-356.285003662f,1961.469970703f},
 {-367.110005697f,1998.956624349f},
 {-394.615005493f,2015.574951172f},
 {-412.486673991f,2025.626627604f},
 {-418.495010376f,2059.829956055f},
 {-434.180002848f,2086.439941406f},
 {-456.889999390f,2092.694946289f},
 {-463.490000407f,2083.583333333f},
 {-471.119995117f,2102.510009766f},
 {-484.490000407f,2090.630045573f},
 {-488.389999390f,2103.265014648f},
 {-503.073333740f,2105.726643880f},
 {-498.994995117f,2125.154907227f},
 {-512.573323568f,2137.953287760f},
 {-536.084991455f,2137.099975586f},
 {-569.809997559f,2136.343343099f},
 {-584.850006104f,2122.739990234f},
 {-606.826680501f,2103.840006510f},
 {-644.020019531f,2100.435058594f},
 {-671.170003255f,2114.566731771f},
 {-688.125000000f,2104.435058594f},
 {-685.860005697f,2088.410074870f},
 {-703.399993896f,2099.595092773f},
 {-714.626668294f,2113.043375651f},
 {-735.338510132f,2140.373461914f},
 {-751.380004883f,2163.403320312f},
 {-758.529998779f,2175.135009766f},
 {-762.889994303f,2187.840006510f},
 {-748.539978027f,2178.040039062f},
 {-738.309977214f,2168.576660156f},
 {-744.729980469f,2181.449951172f},
 {-709.096659342f,2196.609944661f},
 {-704.720001221f,2220.089965820f},
 {-704.610005697f,2262.119954427f},
};
constexpr int ReceiverRouteCount=sizeof(ReceiverRoute)/sizeof(ReceiverRoute[0]);
constexpr float ReceiverRouteReach=.5f;
struct RouteFloor {float y;int face;};
constexpr RouteFloor ReceiverRouteFloor[]={
 {55.426667531f,2928},
 {54.350000381f,2928},
 {55.293333689f,2936},
 {53.590000153f,2936},
 {52.393333435f,2929},
 {53.590000153f,2929},
 {52.393333435f,2947},
 {53.590000153f,2947},
 {54.973333995f,2935},
 {53.870000839f,2935},
 {55.420000712f,2933},
 {54.260000229f,2933},
 {52.840000153f,2946},
 {54.260000229f,2946},
 {52.840000153f,2945},
 {54.260000229f,2945},
 {54.943333944f,2930},
 {53.155000687f,2930},
 {54.473333995f,2931},
 {53.555000305f,2931},
 {52.370000203f,2944},
 {53.555000305f,2944},
 {52.370000203f,2934},
 {53.555000305f,2934},
 {54.670000712f,2937},
 {53.450000763f,2937},
 {55.993334452f,2938},
 {55.540000916f,2938},
 {53.693333944f,2932},
 {55.540000916f,2932},
 {53.693333944f,2926},
 {55.540000916f,2926},
 {55.366667430f,2939},
 {52.510000229f,2939},
 {53.496667226f,2940},
 {52.735000610f,2940},
 {51.823333740f,2925},
 {52.735000610f,2925},
 {51.823333740f,2927},
 {52.735000610f,2927},
 {54.753334045f,2941},
 {57.130001068f,2941},
 {62.913335164f,1292},
 {64.975002289f,1292},
 {67.900001526f,1278},
 {74.115001678f,1278},
 {79.580001831f,1228},
 {82.495002747f,1228},
 {84.786669413f,1275},
 {89.940002441f,1275},
 {94.883333842f,1239},
 {97.069999695f,1239},
 {93.786666870f,1238},
 {95.994998932f,1238},
 {98.050000509f,1294},
 {103.465000153f,1294},
 {108.876665751f,1421},
 {110.930000305f,1421},
 {108.683334351f,1418},
 {111.944999695f,1418},
 {111.896667480f,1424},
 {115.750000000f,1424},
 {125.306666056f,1423},
 {128.110000610f,1423},
 {119.990000407f,1369},
 {124.084999084f,1369},
 {128.173334757f,1402},
 {120.050003052f,1402},
 {121.493334452f,1398},
 {130.365001678f,1398},
 {137.426668803f,1399},
 {137.965000153f,1399},
 {138.653333028f,1234},
 {132.204998016f,1234},
 {128.316665649f,1310},
 {122.459999084f,1310},
 {118.306666056f,1393},
 {115.270000458f,1393},
 {113.513333639f,4775},
 {115.270000458f,4775},
 {116.846666972f,4783},
 {120.270000458f,4783},
 {120.180000305f,4787},
 {120.000000000f,4787},
 {120.000000000f,4794},
 {120.000000000f,4794},
 {120.000000000f,4793},
 {120.000000000f,4793},
 {120.000000000f,4792},
 {120.000000000f,4792},
 {120.000000000f,4796},
 {120.000000000f,4796},
 {120.000000000f,4797},
 {120.000000000f,4797},
 {117.126665751f,4784},
 {115.689998627f,4784},
 {109.463333130f,4799},
 {104.194999695f,4799},
 {101.573333740f,4777},
 {96.670001984f,4777},
 {90.583335876f,2168},
 {87.370002747f,2168},
 {85.046669006f,1409},
 {82.789501572f,1409},
 {86.803334554f,1266},
 {90.005001068f,1266},
 {95.176666260f,1223},
 {100.924999237f,1223},
 {105.016665141f,1344},
 {109.359996796f,1344},
 {118.163332621f,1349},
 {120.645000458f,1349},
 {116.396667480f,1341},
};
// Read-only original static-map wall cache; no actor or terrain fields are changed.
struct RouteWall {RouteVec a,b,c;};
std::vector<RouteWall> receiverRouteWalls;
const Shape* receiverRouteShape=nullptr;
// ROUTE_LAYOUT_POLICY_BEGIN
// Governed full.mod keeps14161 converted render vertices, then3027 original
// collision vertices; all5332 source triangles reference that appended suffix.
constexpr int ReceiverRenderVertexPrefix=14161;
constexpr int ReceiverSourceVertexCount=3027;
constexpr int ReceiverTotalVertexCount=ReceiverRenderVertexPrefix+ReceiverSourceVertexCount;
constexpr bool receiverMapLayout(int faces,int vertices,bool triangles,bool positions){
 return faces==5332 && vertices==ReceiverTotalVertexCount && triangles && positions;
}
constexpr bool receiverSourceVertex(unsigned index){
 return index>=unsigned(ReceiverRenderVertexPrefix) && index<unsigned(ReceiverTotalVertexCount);
}
// ROUTE_LAYOUT_POLICY_END
void receiverWallCache(){
 require(mapMgr&&mapMgr->mMapModel,"route actual map missing");auto* shape=mapMgr->mMapModel;
 if(!receiverRouteShape)std::printf("P2_PURPLE_KOCHAPPY_ROUTE_LAYOUT faces=%d vertices=%d render_prefix=%d source_vertices=%d expected_total=%d actor_writes=0\n",shape->mTriCount,shape->mVertexCount,ReceiverRenderVertexPrefix,ReceiverSourceVertexCount,ReceiverTotalVertexCount);
 require(receiverMapLayout(shape->mTriCount,shape->mVertexCount,shape->mTriList!=nullptr,shape->mVertexList!=nullptr),"route governed map layout changed");
 if(receiverRouteShape){require(receiverRouteShape==shape,"route map replaced");return;}
 for(int i=0;i<shape->mTriCount;++i){const auto& t=shape->mTriList[i];
  for(int k=0;k<3;++k)require(receiverSourceVertex(t.mVertexIndices[k]),"route original collision vertex suffix changed");
  float ny=t.mTriangle.mNormal.y;require(std::isfinite(ny),"route nonfinite plane");if(!(ny>-.5f&&ny<.5f))continue;
  RouteVec v[3];for(int k=0;k<3;++k){require(t.mVertexIndices[k]<unsigned(shape->mVertexCount),"route bad wall vertex");const auto& p=shape->mVertexList[t.mVertexIndices[k]];v[k]={p.x,p.y,p.z};require(rvfinite(v[k]),"route nonfinite vertex");}
  receiverRouteWalls.push_back({v[0],v[1],v[2]});
 }
 require(!receiverRouteWalls.empty(),"route original walls missing");receiverRouteShape=shape;
}
void receiverCheckSphere(RouteVec center,double rejectRadius){
 require(rvfinite(center)&&std::isfinite(rejectRadius)&&rejectRadius>0,"route invalid sphere");
 for(const auto& w:receiverRouteWalls){
  if(center.x<std::min({w.a.x,w.b.x,w.c.x})-rejectRadius||center.x>std::max({w.a.x,w.b.x,w.c.x})+rejectRadius
   ||center.y<std::min({w.a.y,w.b.y,w.c.y})-rejectRadius||center.y>std::max({w.a.y,w.b.y,w.c.y})+rejectRadius
   ||center.z<std::min({w.a.z,w.b.z,w.c.z})-rejectRadius||center.z>std::max({w.a.z,w.b.z,w.c.z})+rejectRadius)continue;
  double d=routeTriangleDistance(center,w.a,w.b,w.c);require(std::isfinite(d)&&d>rejectRadius,"route unsafe static wall contact/shortcut");
 }
}
void receiverRouteClearance(Navi* n,int target){
 receiverWallCache();require(target>=0&&target<ReceiverRouteCount,"route bad target");double radius=n->mCollisionRadius;
 require(std::isfinite(radius)&&std::fabs(radius-8.5)<.001,"route actual collision radius differs from screened source");
 double offset=n->isCreatureFlag(CF_EnableGroundOffset)?n->mGroundOffset:0.;require(std::isfinite(offset),"route invalid ground offset");
 RouteVec center={n->mSRT.t.x,n->mSRT.t.y-offset+radius,n->mSRT.t.z};receiverCheckSphere(center,radius+.10);
 const auto& f=ReceiverRouteFloor[target];const auto& w=ReceiverRoute[target];const auto& tri=mapMgr->mMapModel->mTriList[f.face];double ny=tri.mTriangle.mNormal.y;
 require(std::isfinite(ny)&&ny>.5,"route target source floor changed");
 // Slope-aware intended sphere height. This is a geometric guide, not a physics prediction.
 RouteVec guide={w.x,double(f.y)+radius/ny,w.z};double length=std::sqrt(rvdot(rvsub(guide,center),rvsub(guide,center)));
 require(std::isfinite(length)&&length<512,"route shortcut span invalid");int steps=std::max(1,int(std::ceil(length/.25)));
 // Distance to any triangle is1-Lipschitz; maxsamplegap.25 means any unsampled
 // point iswithin.125 of a checked sample. Inflate by.125 to reject entire line.
 for(int j=0;j<=steps;++j)receiverCheckSphere(rvadd(center,rvscale(rvsub(guide,center),double(j)/steps)),radius+.10+.125);
}
// INCLINE_OBSERVER90_BEGIN
// Fixture-only post-idle observation. Ground is reset by Creature::move;
// collision latch is reset by Creature::updateAI. Normal/model/wall pointers
// are retained engine fields, never an asserted fresh callback by themselves.
double receiverCounterMilliseconds(Uint64 start,Uint64 end,Uint64 frequency){
 return frequency&&end>=start?double(end-start)*1000./double(frequency):-1.;
}
void receiverInclineObserve(Navi* n,int target,int age){
 const Uint64 start=SDL_GetPerformanceCounter(),frequency=SDL_GetPerformanceFrequency();
 if(!mapMgr||!mapMgr->mMapModel||target<0||target>=ReceiverRouteCount)return;
 auto* shape=mapMgr->mMapModel;int groundFace=-1,retainedNormalFace=-1,retainedWallFace=-1;
 for(int i=0;i<shape->mTriCount;++i){const auto& t=shape->mTriList[i];
  if(n->mGroundTriangle==&t)groundFace=i;
  if(n->mCollNormal==&t.mTriangle.mNormal)retainedNormalFace=i;
  if(n->mWallPlane==&t.mTriangle)retainedWallFace=i;
 }
 const int face=ReceiverRouteFloor[target].face;const auto& t=shape->mTriList[face];
 const double offset=n->isCreatureFlag(CF_EnableGroundOffset)?n->mGroundOffset:0.;
 const RouteVec center={n->mSRT.t.x,n->mSRT.t.y-offset+n->mCollisionRadius,n->mSRT.t.z};
 RouteVec v[3];for(int k=0;k<3;++k){const auto& p=shape->mVertexList[t.mVertexIndices[k]];v[k]={p.x,p.y,p.z};}
 const auto& normal=t.mTriangle.mNormal;
 const double signedPlane=center.x*normal.x+center.y*normal.y+center.z*normal.z-t.mTriangle.mOffset;
 const double triangleDistance=routeTriangleDistance(center,v[0],v[1],v[2]);
 const double observeMs=receiverCounterMilliseconds(start,SDL_GetPerformanceCounter(),frequency);
 std::printf("P2_PURPLE_KOCHAPPY_INCLINE_OBSERVE age=%d waypoint=%d post_idle=1 state=%d collision_latch=%u ground_ptr=%p ground_face=%d retained_normal_ptr=%p retained_normal_face=%d retained_wall_ptr=%p retained_wall_face=%d retained_model_ptr=%p pointer_alone_fresh_contact=0 sphere=%.6f,%.6f,%.6f target_face=%d target_normal=%.6f,%.6f,%.6f plane_distance=%.6f triangle_distance=%.6f radius=%.6f frame_time=%.6f gravity=%.6f acceleration=%.6f bounce=%.6f air_resistance=%.6f flags=%u velocity=%.6f,%.6f,%.6f target_velocity=%.6f,%.6f,%.6f bias=%.6f,%.6f,%.6f observer_compute_ms=%.6f print_cost_included=0 actor_writes=0\n",
  age,target,n->getCurrState()->getID(),unsigned(n->mCollisionOccurred),static_cast<void*>(n->mGroundTriangle),groundFace,static_cast<void*>(n->mCollNormal),retainedNormalFace,static_cast<const void*>(n->mWallPlane),retainedWallFace,static_cast<void*>(n->mCurrCollisionModel),center.x,center.y,center.z,face,normal.x,normal.y,normal.z,signedPlane,triangleDistance,n->mCollisionRadius,gsys->getFrameTime(),AICONST.mGravity(),n->mProps->mCreatureProps.mAcceleration(),n->mProps->mCreatureProps.mBounceFactor(),n->mAirResistance,unsigned(n->mCreatureFlags),n->mVelocity.x,n->mVelocity.y,n->mVelocity.z,n->mTargetVelocity.x,n->mTargetVelocity.y,n->mTargetVelocity.z,n->_B0.x,n->_B0.y,n->_B0.z,observeMs);
}
void receiverObservedClearance(Navi* n,int target,int age){
 const Uint64 start=SDL_GetPerformanceCounter(),frequency=SDL_GetPerformanceFrequency();
 receiverRouteClearance(n,target);
 const double elapsed=receiverCounterMilliseconds(start,SDL_GetPerformanceCounter(),frequency);
 std::printf("P2_PURPLE_KOCHAPPY_CLEARANCE_COST age=%d waypoint=%d clearance_ms=%.6f print_cost_included=0 original_call_count=1 actor_writes=0\n",age,target,elapsed);
}
double receiverGuideSpan(Navi* n,int target){
 require(target>=0&&target<ReceiverRouteCount,"reentry source guide index invalid");
 const double radius=n->mCollisionRadius;
 require(std::isfinite(radius)&&std::fabs(radius-8.5)<.001,"reentry native radius changed");
 const double offset=n->isCreatureFlag(CF_EnableGroundOffset)?n->mGroundOffset:0.;
 require(std::isfinite(offset),"reentry invalid ground offset");
 const auto& f=ReceiverRouteFloor[target];const auto& w=ReceiverRoute[target];
 const double ny=mapMgr->mMapModel->mTriList[f.face].mTriangle.mNormal.y;
 require(std::isfinite(ny)&&ny>.5,"reentry original source floor changed");
 const RouteVec center={n->mSRT.t.x,n->mSRT.t.y-offset+radius,n->mSRT.t.z};
 const RouteVec guide={w.x,double(f.y)+radius/ny,w.z};
 return std::sqrt(rvdot(rvsub(guide,center),rvsub(guide,center)));
}
// INCLINE_OBSERVER90_END
class PurpleKochappyApp:public PlugPikiApp {
 int frame=0,age=0,phase=0,start=0,settled=0,throwCount=0;
 int receiverWaypoint=0;
 bool gatherDiverted=false;
 PcKochappyReentryProgress reentryProgress;
 bool seenCaptain=false,wasActive=false,sawFit=false,sawPause=false,recovered=false,deathDuringStun=false;
 Teki* enemy=nullptr;Pom* violet=nullptr;Piki* purple=nullptr;
 PcKochappyFsmSnapshot pausedFsm;
 Generator* enemyGenerator=nullptr;Generator* violetGenerator=nullptr;
 unsigned violetGeneratorId=0;
 void requireCurrentActors() {
  // Cached addresses are comparison tokens only until their current manager
  // owns them. Never call a receiver/profile hook on an absent cached actor.
  Teki* currentEnemy=nullptr;Pom* currentViolet=nullptr;
  Iterator ts(tekiMgr);CI_LOOP(ts){Teki* t=static_cast<Teki*>(*ts);
   if(t!=enemy)continue;
   require(!currentEnemy,"duplicate current enemy address");
   require(t->mGenerator==enemyGenerator&&t->mGenerator&&t->mGenerator->_70==Target,"enemy generator identity changed");
   currentEnemy=t;
  }
  Iterator bs(bossMgr);CI_LOOP(bs){Boss* b=static_cast<Boss*>(*bs);
   if(b!=violet)continue;
   require(!currentViolet,"duplicate current Violet address");
   require(b->mObjType==OBJTYPE_Pom&&b->mGenerator==violetGenerator&&b->mGenerator&&unsigned(b->mGenerator->_70)==violetGeneratorId,"Violet generator identity changed");
   currentViolet=static_cast<Pom*>(b);
  }
  require(currentEnemy&&currentViolet,"observed actor no longer owned by current manager");
  require(pc_p2_kochappy_registered(currentEnemy)&&pc_p2_kochappy_fsm_suppress_ai(currentEnemy),"current enemy receiver/FSM lifetime lost");
  require(currentViolet->isAlive()&&pc_p2_violet(currentViolet),"current Violet lifetime/profile lost");
 }
 // Fixture-local observation ledger; pointer/slot is process-local, not a durable Pikmin UID.
 Piki* initialBodies[20]={};unsigned initialGeneratorIds[20]={};int initialBodyCount=0,lastObservedLive=-1;
 void observePopulation(int live) {
  if(age%10!=0&&live==lastObservedLive)return;
  lastObservedLive=live;bool present[20]={};int purpleHeads=0,otherHeads=0,captured=0;
  Iterator observed(pikiMgr);CI_LOOP(observed){Piki* p=static_cast<Piki*>(*observed);if(!p)continue;
   int slot=-1;for(int i=0;i<initialBodyCount;++i)if(initialBodies[i]==p){slot=i;present[i]=true;break;}
   unsigned generator=p->mGenerator?unsigned(p->mGenerator->_70):0;
   if(p->getStickObject()==violet)++captured;
   const Vector3f normal=p->mGroundTriangle?p->mGroundTriangle->mTriangle.mNormal:Vector3f(0,0,0);
   std::printf("P2_PURPLE_KOCHAPPY_BODY age=%d slot=%d ptr=%p generator_present=%d generator=%u baseline_generator=%u alive=%d health=%.3f state=%d mode=%d purple=%d mouth=%d sticker=%p violet_sticker=%d water_timer=%u xyz=%.4f,%.4f,%.4f velocity=%.4f,%.4f,%.4f terrain=%.4f ground=%d normal=%.4f,%.4f,%.4f\n",
    age,slot,static_cast<void*>(p),int(p->mGenerator!=nullptr),generator,slot>=0?initialGeneratorIds[slot]:0,int(p->isAlive()),p->mHealth,p->getCurrState()?p->getState():-1,int(p->mMode),int(pc_p2_is_purple(p)),int(p->isStickToMouth()),static_cast<void*>(p->getStickObject()),int(p->getStickObject()==violet),unsigned(p->mInWaterTimer),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z,p->mVelocity.x,p->mVelocity.y,p->mVelocity.z,mapMgr->getMinY(p->mSRT.t.x,p->mSRT.t.z,true),int(p->mGroundTriangle!=nullptr),normal.x,normal.y,normal.z);
  }
  // Compare pointer tokens only; never dereference a body absent from the current manager.
  for(int i=0;i<initialBodyCount;++i)if(!present[i])std::printf("P2_PURPLE_KOCHAPPY_BODY_MISSING age=%d slot=%d ptr=%p baseline_generator=%u durable_identity=0\n",age,i,static_cast<void*>(initialBodies[i]),initialGeneratorIds[i]);
  Iterator sprouts(itemMgr->getPikiHeadMgr());CI_LOOP(sprouts){PikiHeadItem* h=static_cast<PikiHeadItem*>(*sprouts);if(!h)continue;
   if(h->isAlive()){if(h->mP2Purple)++purpleHeads;else ++otherHeads;}
   std::printf("P2_PURPLE_KOCHAPPY_HEAD age=%d ptr=%p alive=%d purple=%d white=%d bulbmin=%d seed_color=%d state=%d generator_present=%d generator=%u owner=%d parent_onion=%p pullable=%d xyz=%.4f,%.4f,%.4f velocity=%.4f,%.4f,%.4f terrain=%.4f input_UID_mapping=unavailable\n",
    age,static_cast<void*>(h),int(h->isAlive()),int(h->mP2Purple),int(h->mP2White),int(h->mP2Bulbmin),h->mSeedColor,h->getCurrState()?h->getCurrState()->getID():-1,int(h->mGenerator!=nullptr),h->mGenerator?unsigned(h->mGenerator->_70):0,h->mPcOwner,static_cast<void*>(h->mParentOnion),int(h->canPullout()),h->mSRT.t.x,h->mSRT.t.y,h->mSRT.t.z,h->mVelocity.x,h->mVelocity.y,h->mVelocity.z,mapMgr->getMinY(h->mSRT.t.x,h->mSRT.t.z,true));
  }
  std::printf("P2_PURPLE_KOCHAPPY_POPULATION age=%d field=%d purple_heads=%d other_heads=%d field_plus_heads=%d captured=%d dead=%d fall=%d victim=%d born=%d map=%d all=%d violet_generator=%u violet_state=%d violet_motion=%d violet_frame=%.4f loaded_cycle_capacity=%d loaded_min_cycles=%d loaded_max_cycles=%d source_violet_lifetime_capacity=5 remaining_budget=private_unobserved enemy_health=%.3f enemy_xyz=%.4f,%.4f,%.4f\n",
   age,live,purpleHeads,otherHeads,live+purpleHeads+otherHeads,captured,int(GameStat::deadPikis),int(GameStat::fallPikis),int(GameStat::victimPikis),int(GameStat::bornPikis),int(GameStat::mapPikis),int(GameStat::allPikis),violet->mGenerator?unsigned(violet->mGenerator->_70):0,violet->getCurrentState(),BossObserver::motion(*violet),BossObserver::frame(*violet),C_POM_PARM(violet,mMaxPikiPerCycle),C_POM_PARM(violet,mMinCycles),C_POM_PARM(violet,mMaxCycles),enemy->mHealth,enemy->mSRT.t.x,enemy->mSRT.t.y,enemy->mSRT.t.z);
  std::fflush(nullptr);
 }
 float pausedCounter=0,lastCounter=0,activeSeconds=0;
public:
 int idle() override {
  int result=PlugPikiApp::idle();
  // First post-idle boundary, also during movies, pause and disappearance.
  Navi* n=naviMgr?naviMgr->getNavi():nullptr;
  const bool initialized=n&&n->getCurrState();if(initialized)seenCaptain=true;
  const bool forced=std::getenv("P2_PURPLE_KOCHAPPY_FORCE_DOWN")!=nullptr;
  const bool paused=std::getenv("P2_PURPLE_KOCHAPPY_PAUSED_DOWN")!=nullptr;
  if(initialized&&paused)gameflow.mPauseAll=true; // negative test only
  if(seenCaptain&&!initialized){std::puts("P2_FIXTURE_CAPTAIN_MISSING outcome=BLOCKED");p2_fixture_require_captain(true,true,0,frame);}
  if(initialized)p2_fixture_require_captain(GameStat::orimaDead||forced||paused,
   naviMgr->isNaviDead(n)||n->getCurrState()->getID()==NAVISTATE_Dead,n->mHealth,frame);
  ++frame;require(frame<3600,"frame bound; supervisor additionally caps60wallseconds");
  if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!initialized||!pikiMgr||!tekiMgr||!itemMgr||!bossMgr)return result;
  if(gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
  if(phase==0&&(n->getCurrState()->getID()!=NAVISTATE_Walk||++settled<45))return result;
  ++age;int live=0,red=0,purples=0;purple=nullptr;
  Iterator bodies(pikiMgr);CI_LOOP(bodies){Piki* p=static_cast<Piki*>(*bodies);if(!p->isAlive())continue;++live;
   if(pc_p2_is_purple(p)){++purples;purple=p;}else if(p->mColor==Red)++red;}
  require(purples<=1,"duplicate natural Purple body");
  if(phase==0){
   require(live==20&&red==20&&purples==0,"current20nativeRed baseline, no injectedPurple");
   Iterator baseline(pikiMgr);CI_LOOP(baseline){Piki* p=static_cast<Piki*>(*baseline);if(p&&p->isAlive()&&initialBodyCount<20){initialBodies[initialBodyCount]=p;initialGeneratorIds[initialBodyCount]=p->mGenerator?unsigned(p->mGenerator->_70):0;++initialBodyCount;}}
   require(pc_p2_purples_enabled()&&pc_p2_purple_flight_enabled(),"actual Purplebank/flight profiles");
   Iterator ts(tekiMgr);CI_LOOP(ts){Teki* t=static_cast<Teki*>(*ts);if(t->mGenerator&&t->mGenerator->_70==Target){require(!enemy,"duplicateRed");enemy=t;}}
   Iterator bs(bossMgr);CI_LOOP(bs){Boss* b=static_cast<Boss*>(*bs);if(b->isAlive()&&b->mObjType==OBJTYPE_Pom&&pc_p2_violet(static_cast<Pom*>(b))){require(!violet,"duplicateViolet");violet=static_cast<Pom*>(b);}}
   require(enemy&&violet&&pc_p2_kochappy_registered(enemy)&&pc_p2_kochappy_fsm_suppress_ai(enemy),"actualRedownFSM and nativeViolet");
   require(enemy->mGenerator&&violet->mGenerator,"source actor generator identities missing");
   enemyGenerator=enemy->mGenerator;violetGenerator=violet->mGenerator;violetGeneratorId=unsigned(violetGenerator->_70);
   require(std::fabs(enemy->mHealth-200)<.01f,"sourceRedhealth200");
   std::puts("P2_PURPLE_KOCHAPPY_READY engineering_preview=1 startingRed=20 startingPurple=0 actor_writes=0 tutorial_AP_gate=OPEN");std::fflush(nullptr);
   if(std::getenv("P2_PURPLE_KOCHAPPY_READY_ONLY"))std::_Exit(0);
   phase=1;start=age;
  }
  requireCurrentActors();
  if(human())return result;
  if(age%60==0){std::printf("P2_PURPLE_KOCHAPPY_PROGRESS phase=%d age=%d hp=%.2f live=%d red=%d purple=%d followers=%d\n",phase,age,n->mHealth,live,red,purples,n->getPlatePikis());std::fflush(nullptr);}
  if(phase==1){
   require(live==20&&red==20&&purples==0,"ordinary route preserves current20nativeRed until throw");
   observePopulation(live);
   const float radius=C_NAVI_PARM(n,mCursorMaxRadius);
   require(std::isfinite(radius)&&radius>20,"loaded cursor radius permits ordinary approach");
   const float approach=std::min(65.f,radius*.5f);
   if(age%30==0){
    std::printf("P2_PURPLE_KOCHAPPY_APPROACH_OBSERVE age=%d state=%d actual_pad_b=%d actual_mainstick=%.4f,%.4f loaded_radius=%.4f loaded_neutral=%.4f loaded_move_threshold=%.4f distance=%.4f approach=%.4f captain=%.4f,%.4f,%.4f velocity=%.4f,%.4f,%.4f violet=%.4f,%.4f,%.4f terrain_mid=%.4f terrain_bud=%.4f followers=%d\n",
     age,n->getCurrState()->getID(),int(SDL_JoystickGetButton(pad,SDL_CONTROLLER_BUTTON_B)),n->mKontroller->getMainStickX(),n->mKontroller->getMainStickY(),radius,C_NAVI_PARM(n,mNeutralStickThreshold),C_NAVI_PARM(n,mCursorMoveStickThreshold),distance(n->mSRT.t,violet->mSRT.t),approach,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->mVelocity.x,n->mVelocity.y,n->mVelocity.z,violet->mSRT.t.x,violet->mSRT.t.y,violet->mSRT.t.z,mapMgr->getMinY((n->mSRT.t.x+violet->mSRT.t.x)*.5f,(n->mSRT.t.z+violet->mSRT.t.z)*.5f,true),mapMgr->getMinY(violet->mSRT.t.x,violet->mSRT.t.z,true),n->getPlatePikis());
    std::fflush(nullptr);
   }
   // Aim the real whistle at an ungathered body; neutral whistle at a stale
   // cursor can leave alive free Pikmin outside its circle indefinitely.
   // Keep the exact20-follower approach gate and all mechanic oracles below.
   if(n->getPlatePikis()<20){
    Piki* gather=nullptr;float nearest=1e30f;Iterator idle(pikiMgr);CI_LOOP(idle){Piki* p=static_cast<Piki*>(*idle);
     if(!p||!p->isAlive()||p->mColor!=Red||pc_p2_is_purple(p)||p->mMode!=PikiMode::FreeMode||!p->mIsCallable)continue;
     int slot=-1;for(int i=0;i<initialBodyCount;++i)if(initialBodies[i]==p){slot=i;break;}
     require(slot>=0&&p->mGenerator&&unsigned(p->mGenerator->_70)==initialGeneratorIds[slot],"gather current original roster identity");
     const float d=distance(n->mSRT.t,p->mSRT.t);require(std::isfinite(d),"gather target distance finite");
     if(d<nearest){nearest=d;gather=p;}}
    if(gather){
     if(receiverWaypoint>0)gatherDiverted=true;
     if(age%30==0)std::printf("P2_PURPLE_KOCHAPPY_GATHER_CURSOR age=%d followers=%d target_generator=%u target_callable=%d target_state=%d target_xyz=%.4f,%.4f,%.4f cursor_xyz=%.4f,%.4f,%.4f loaded_whistle_min=%.4f loaded_whistle_max=%.4f whistle_timer=%.4f SDL_aim=1 actor_writes=0\n",
      age,n->getPlatePikis(),gather->mGenerator?unsigned(gather->mGenerator->_70):0,int(gather->mIsCallable),gather->getState(),gather->mSRT.t.x,gather->mSRT.t.y,gather->mSRT.t.z,n->mCursorWorldPos.x,n->mCursorWorldPos.y,n->mCursorWorldPos.z,C_NAVI_PARM(n,mWhistleMinRadius),C_NAVI_PARM(n,mWhistleMaxRadius),n->mWhistleTimer);
     const float whistle=C_NAVI_PARM(n,mWhistleMaxRadius);
     const auto plan=pc_kochappy_gather_input(nearest,radius,whistle,C_NAVI_PARM(n,mNeutralStickThreshold),C_NAVI_PARM(n,mCursorMoveStickThreshold));
     require(plan!=PcKochappyGatherInput::Refuse,"loaded ordinary gather input bands invalid");
     if(age%30==0)std::printf("P2_PURPLE_KOCHAPPY_GATHER_INPUT age=%d target_generator=%u captain_target_xz=%.4f cursor_target_xz=%.4f loaded_whistle_max=%.4f loaded_cursor_max=%.4f walk=%d native_recruitment_strict_xz=1 actor_writes=0\n",age,unsigned(gather->mGenerator->_70),nearest,distance(n->mCursorWorldPos,gather->mSRT.t),whistle,radius,int(plan==PcKochappyGatherInput::Walk));
     point(n,gather->mSRT.t,plan==PcKochappyGatherInput::Walk,KeyConfig::_instance->mSetCursorKey.mBind,radius+whistle*.5f);return result;
    }
   }
   if(age%30==0){
    const Vector3f ground=n->mGroundTriangle?n->mGroundTriangle->mTriangle.mNormal:Vector3f(0,0,0);
    const Vector3f wall=n->mWallPlane?n->mWallPlane->mNormal:Vector3f(0,0,0);
    const Vector3f axis=n->controlCamera()->mViewXAxis;
    std::printf("P2_PURPLE_KOCHAPPY_MOVE_CONTACT age=%d ground=%d ground_normal=%.4f,%.4f,%.4f wall=%d wall_normal=%.4f,%.4f,%.4f collision_radius=%.4f target_velocity=%.4f,%.4f,%.4f camera_xaxis=%.4f,%.4f,%.4f own_floor=%.4f SDL_left_axes=%d,%d axis_contract=GC74_to_SDL256 actor_writes=0\n",
     age,int(n->mGroundTriangle!=nullptr),ground.x,ground.y,ground.z,int(n->mWallPlane!=nullptr),wall.x,wall.y,wall.z,n->mCollisionRadius,n->mTargetVelocity.x,n->mTargetVelocity.y,n->mTargetVelocity.z,axis.x,axis.y,axis.z,mapMgr->getMinY(n->mSRT.t.x,n->mSRT.t.z,true),int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_LEFTX)),int(SDL_JoystickGetAxis(pad,SDL_CONTROLLER_AXIS_LEFTY)));
    std::fflush(nullptr);
   }
   if(n->getPlatePikis()==20&&age-start>30){
    if(gatherDiverted){
     require(reentryProgress.mayBegin(receiverWaypoint),"route repeated gather diversion without forward progress or budget exhausted");
     require(receiverWaypoint<=ReceiverRouteCount,"route reentry history exceeds original route");
     receiverWallCache(); // validate the current owned source map before guide reads
     double spans[ReceiverRouteCount];for(int i=0;i<receiverWaypoint;++i)spans[i]=receiverGuideSpan(n,i);
     const int chosen=pc_kochappy_route_reentry(spans,ReceiverRouteCount,receiverWaypoint);
     require(chosen>=0,"route no bounded previously visited reentry guide");
     // Check the unchanged sphere/path padding and strict512 span BEFORE any
     // planner rewind. Actor position and original waypoints remain untouched.
     receiverObservedClearance(n,chosen,age);
     require(reentryProgress.begin(receiverWaypoint,chosen),"route reentry progress invariant");
     std::printf("P2_PURPLE_KOCHAPPY_REENTRY age=%d original_next=%d previously_visited=%d count=%d span=%.4f followers=20 unchanged_clearance=1 ordinary_replay=1 actor_writes=0\n",age,receiverWaypoint,chosen,reentryProgress.count,spans[chosen]);
     receiverWaypoint=chosen;gatherDiverted=false;
    }
    // Do not replace the strict loaded50-unit approach with an easier endpoint.
    // Follow each original corridor centroid/portal through ordinary SDL only.
    if(receiverWaypoint<ReceiverRouteCount)receiverObservedClearance(n,receiverWaypoint,age);
    if(receiverWaypoint<ReceiverRouteCount)receiverInclineObserve(n,receiverWaypoint,age);
    while(receiverWaypoint<ReceiverRouteCount){
     const auto& w=ReceiverRoute[receiverWaypoint];const Vector3f goal(w.x,0.f,w.z);
     if(distance(n->mSRT.t,goal)>ReceiverRouteReach)break;
     std::printf("P2_PURPLE_KOCHAPPY_ROUTE_REACHED age=%d waypoint=%d followers=%d captain=%.4f,%.4f,%.4f actor_writes=0\n",age,receiverWaypoint,n->getPlatePikis(),n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z);
     ++receiverWaypoint;
    }
    if(receiverWaypoint<ReceiverRouteCount){
     const auto& w=ReceiverRoute[receiverWaypoint];const Vector3f goal(w.x,0.f,w.z);
     if(age%30==0)std::printf("P2_PURPLE_KOCHAPPY_ROUTE_TARGET age=%d waypoint=%d total=%d target_xz=%.4f,%.4f distance=%.4f reach=%.4f followers=%d live=%d SDL_walk=1 actor_writes=0\n",age,receiverWaypoint,ReceiverRouteCount,w.x,w.z,distance(n->mSRT.t,goal),ReceiverRouteReach,n->getPlatePikis(),live);
     receiverObservedClearance(n,receiverWaypoint,age);
     point(n,goal,true,KeyConfig::_instance->mSetCursorKey.mBind,ReceiverRouteReach);return result;
    }
    if(distance(n->mSRT.t,violet->mSRT.t)>approach){point(n,violet->mSRT.t,true,KeyConfig::_instance->mSetCursorKey.mBind);return result;}
    std::printf("P2_PURPLE_KOCHAPPY_APPROACH loaded_cursor_radius=%.4f captain_bud_xz=%.4f target_distance=%.4f SDL_walk=1\n",radius,distance(n->mSRT.t,violet->mSRT.t),approach);
    phase=2;start=age;
   }
   input(KeyConfig::_instance->mSetCursorKey.mBind);return result;
  }
  if(phase==2){
   PikiHeadItem* head=nullptr;Iterator hs(itemMgr->getPikiHeadMgr());CI_LOOP(hs){PikiHeadItem* h=static_cast<PikiHeadItem*>(*hs);if(h->isAlive()&&h->mP2Purple){require(!head,"more than one convertedPurple");head=h;}}
   if(head){input();phase=3;start=age;return result;}
   // Hold/release the ordinary A throw. Never call throwPiki or transit actors.
   int cycle=(age-start)%120;point(n,violet->mSRT.t,false,cycle>=30&&cycle<48?KeyConfig::_instance->mThrowKey.mBind:0);
   if(cycle<70||age%30==0){
    int captured=0,index=0;Iterator samples(pikiMgr);
    CI_LOOP(samples){Piki* p=static_cast<Piki*>(*samples);if(!p->isAlive())continue;
     if(p->getStickObject()==violet)++captured;
     if(p->getState()==PIKISTATE_Flying||p->mMode!=PikiMode::FormationMode){
      std::printf("P2_PURPLE_KOCHAPPY_THROW_OBSERVE age=%d index=%d state=%d mode=%d violet_sticker=%d xyz=%.4f,%.4f,%.4f velocity=%.4f,%.4f,%.4f\n",
       age,index,p->getState(),int(p->mMode),int(p->getStickObject()==violet),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z,p->mVelocity.x,p->mVelocity.y,p->mVelocity.z);
     }++index;
    }
    std::printf("P2_PURPLE_KOCHAPPY_AIM_OBSERVE age=%d cycle=%d actual_pad_a=%d captain=%.4f,%.4f,%.4f cursor=%.4f,%.4f,%.4f violet=%.4f,%.4f,%.4f registered=%d state=%d motion=%d anim_frame=%.4f captured=%d enemy_health=%.2f\n",
     age,cycle,int(SDL_JoystickGetButton(pad,SDL_CONTROLLER_BUTTON_A)),n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->mCursorWorldPos.x,n->mCursorWorldPos.y,n->mCursorWorldPos.z,
     violet->mSRT.t.x,violet->mSRT.t.y,violet->mSRT.t.z,int(pc_p2_violet(violet)),violet->getCurrentState(),BossObserver::motion(*violet),BossObserver::frame(*violet),captured,enemy->mHealth);
    std::fflush(nullptr);
   }
   require(age-start<600,"ordinaryViolet conversion did not complete");return result;
  }
  if(phase==3){
   if(purples==1&&purple&&purple->getState()==PIKISTATE_Normal){require(live==20&&red==19,"one-for-one ordinary20body conversion");
    std::puts("P2_PURPLE_KOCHAPPY_CONVERSION live=20 Red=19 Purple=1 SDL_throw_pluck=1 species_writes=0");phase=4;start=age;input();return result;}
   PikiHeadItem* head=nullptr;Iterator hs(itemMgr->getPikiHeadMgr());CI_LOOP(hs){PikiHeadItem* h=static_cast<PikiHeadItem*>(*hs);if(h->isAlive()&&h->mP2Purple)head=h;}
   if(!head&&purples==1){input();require(age-start<600,"ordinaryPurple birth/formation timeout");return result;}
   require(head,"ordinaryPurple sprout disappeared");
   if(distance(n->mSRT.t,head->mSRT.t)>20)point(n,head->mSRT.t,true);
   else input(head->canPullout()?KeyConfig::_instance->mExtractKey.mBind:0);
   require(age-start<600,"ordinary approach/pluck timeout");return result;
  }
  require(purple&&purple->isAlive(),"naturalPurple lifetime lost");
  if(phase==4){
   if(n->getPlatePikis()<20){input(KeyConfig::_instance->mSetCursorKey.mBind);return result;}
   if(distance(n->mSRT.t,enemy->mSRT.t)>120){point(n,enemy->mSRT.t,true);return result;}
   phase=5;start=age;input();
  }
  const bool active=pc_p2_kochappy_stun_active(enemy);
  const auto fsm=pc_p2_kochappy_fsm_observe(enemy);
  require(fsm.available&&std::isfinite(fsm.stateTime),"current ownFSM snapshot unavailable");
  require(enemy->mTekiAnimator,"current enemy animator absent");
  const float counter=enemy->mTekiAnimator->getCounter();
  if(active){
   if(!wasActive){pausedFsm=fsm;pausedCounter=counter;activeSeconds=0;std::printf("P2_PURPLE_KOCHAPPY_ACTIVE counter=%.6f health=%.2f state=%d stateTime=%.6f attack=%d swallow=%d flick=%d\n",counter,enemy->mHealth,fsm.state,fsm.stateTime,int(fsm.attackFired),int(fsm.swallowFired),int(fsm.flickFired));}
   require(pc_kochappy_overlay_preserved(pausedFsm,fsm),"ownFSM clock/state/one-shot changed during active overlay");
   require(enemy->getTekiOption(TEKIOPT_ManualAnimation)&&enemy->mMotionSpeed==0,"actual ownmotion overlay notpaused");
   require(std::fabs(counter-pausedCounter)<.001f,"actual animator advanced during receiveroverlay");
   sawPause=true;activeSeconds+=gsys->getFrameTime();if(activeSeconds>1.5f)sawFit=true;
   // Whistle through the normal control path to prevent continuous Pikmin
   // attacking from hiding the source10s recovery boundary with early death.
   if(phase==5)input(KeyConfig::_instance->mSetCursorKey.mBind);
  }
  if(wasActive&&!active&&phase==5){
   require(!fsm.stunPaused&&!fsm.terminal&&enemy->mHealth>0,"natural recovery entered terminal state or retained pause");
   std::printf("P2_PURPLE_KOCHAPPY_RECOVERY elapsed=%.3f counter=%.6f fit=%d\n",activeSeconds,counter,int(sawFit));
   if(sawFit){require(activeSeconds>=10,"RedFit recovered before source10s");phase=6;start=age;lastCounter=counter;input();}
  }
  if(phase==7&&wasActive&&!active&&enemy->mHealth<=0){require(fsm.terminal&&!fsm.stunPaused,"terminal interruption missing ownFSM terminal/unpause");deathDuringStun=true;}
  wasActive=active;
  if(phase==5&&!active){
   const int cycle=(age-start)%150;
   // Cycle once while holding A: the native selection path chooses Purple.
   Vector3f aim=enemy->mSRT.t;aim.x+=40; // ordinary cursor target near quake radius, no actor relocation
   point(n,aim,false,cycle<18?(KeyConfig::_instance->mThrowKey.mBind|(cycle==10&&throwCount==0?KBBTN_DPAD_RIGHT:0)):0);
   if(cycle==18)++throwCount;
   require(throwCount<8,"natural Purple receiver/Fit not observed after bounded throws");
  }
  if(phase==6){input();if(age-start>60){require(std::fabs(counter-lastCounter)>.001f,"animator failed toresume");require(pc_kochappy_clock_resumed(pausedFsm,fsm),"ownFSM clock failed toresume naturally");recovered=true;phase=7;start=age;}}
  if(phase==7){
   // Further ordinary throws allow natural damage/death to interrupt another
   // overlay. Success requires the observed active->terminal boundary.
   if(!enemy->isAlive()||enemy->mHealth<=0){
    require(sawPause&&sawFit&&recovered,"receiver recovery prerequisite missing");
    std::printf("P2_PURPLE_KOCHAPPY_MECHANIC_RECOVERY_PASS natural_impact=1 motion_pause_resume=1 RedFit10=1 actor_writes=0 death_during_stun=%d tutorial_AP_gate=OPEN\n",int(deathDuringStun));
    std::fflush(nullptr);std::_Exit(deathDuringStun?0:3);
   }
   int cycle=(age-start)%60;point(n,enemy->mSRT.t,false,cycle<18?KeyConfig::_instance->mThrowKey.mBind:0);
   // No forced source selection/state/damage. Unobserved terminal interruption
   // remains a failed diagnostic rather than a production approval.
   require(age-start<600,"natural damage/death interruption timeout");
  }
  return result;
 }
};
}
int main(int argc,char**argv){
 require(std::getenv("PIKMIN_P2_TEST_START_DAY")&&!std::strcmp(std::getenv("PIKMIN_P2_TEST_START_DAY"),"5"),"inherit existing test-only actual day5 bootstrap");
 SDL_setenv("SDL_AUDIODRIVER","dummy",1);SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");SDL_SetMainReady();pc_gpu_preference_apply();pc_bbft_init(argc,argv);
 require(pc_pikipelago_room_preview(),"engineering room-preview required; tutorial/AP acceptance OPEN");
 if(!pc_window_init("Purple own Kochappy engineering diagnostic",960,540))return 3;
 pc_settings_init();pc_window_set_control_mode(PC_CONTROL_CLASSIC);pc_window_set_display_mode(0);pc_window_set_window_size(960,540);pc_window_center();
 SDL_Window* w=SDL_GL_GetCurrentWindow();int width,height,x,y;SDL_GetWindowSize(w,&width,&height);SDL_GetWindowPosition(w,&x,&y);SDL_Rect b{};SDL_GetDisplayBounds(SDL_GetWindowDisplayIndex(w),&b);
 require(width==960&&height==540&&std::abs(x-(b.x+(b.w-width)/2))<=2&&std::abs(y-(b.y+(b.h-height)/2))<=2,"centered960x540 baseline");
 std::printf("P2_PURPLE_KOCHAPPY_WINDOW size=%dx%d centered=1\n",width,height);
 if(!human()){
  int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);require(device>=0,"virtual pad attach");
  char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));std::string mapping=std::string(guid)+",Tutorial acceptance pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
  require(SDL_GameControllerAddMapping(mapping.c_str())>=0,"virtual pad mapping");pad=SDL_JoystickOpen(device);require(pad,"virtual pad open");
  pc_window_set_stick_invert(0);pc_window_set_cstick_invert(0);pc_window_set_gamepad_binding(PC_KEY_ACT_A,SDL_CONTROLLER_BUTTON_A);pc_window_set_gamepad_binding(PC_KEY_ACT_B,SDL_CONTROLLER_BUTTON_B);pc_window_set_gamepad_binding(PC_KEY_ACT_DPAD_RIGHT,SDL_CONTROLLER_BUTTON_DPAD_RIGHT);input();
 }
 gsys->Initialise();pc_settings_p2d_init();nodeMgr=new NodeMgr();gsys->run(new PurpleKochappyApp());return 0;
}

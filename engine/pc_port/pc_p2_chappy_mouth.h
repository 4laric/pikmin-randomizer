#pragma once
// Source mouth-slot eating for the Chappy family (#884). Engine-free so the
// runtime (pc_p2_chappy.cpp, pc_p2_kochappy_fsm.cpp) and
// tools/p2_chappy_mouth_test.cpp compile the same decision code.
//
// Source of truth (read-only decomp `native/pikmin2-research`):
//   EnemyFunc::eatPikmin            src/plugProjectYamashitaU/enemyAction.cpp:1107-1142
//   EatPikminDefaultCondition       src/plugProjectYamashitaU/enemyAction.cpp:2113-2122
//   MouthCollPart::getPosition      src/plugProjectKandoU/collinfo.cpp:1641-1644 (joint world translation)
//   MouthSlots::setup (zero offset) src/plugProjectKandoU/collinfo.cpp:1694-1698
//   initMouthSlots:
//     ChappyBase (2, 33, 43)  5 x kamu1..5 r=35  src/plugProjectYamashitaU/ChappyBase.cpp:232-244
//     KumaChappy (35)         5 x kamu1..5 r=35  src/plugProjectNishimuraU/KumaChappy.cpp:157-169
//     LeafChappy (67)         3 x kamu1..3 r=30  src/plugProjectNishimuraU/LeafChappy.cpp:77-87
//     KumaKochappy (76)       1 x kamu     r=15  src/plugProjectNishimuraU/KumaKochappy.cpp:147-155
//     KochappyBase (44)       1 x kamu     r=15  src/plugProjectYamashitaU/KochappyBase.cpp:175-183
//     KingChappy (53)         9 x kamu1..9 r=25*mScaleModifier  src/plugProjectMorimuraU/kingChappy.cpp:993-1001
//   Eat event: attack KEYEVENT_2 (frame 10 adults/Kuma/Leaf, chappyState.cpp:1615-1646,
//     KumaChappyState.cpp:241-246; frame 8 KumaKo/Kochappy, KumaKochappyState.cpp:180-184,
//     kochappyState.cpp:1403-1414). King: every frame after attack KEYEVENT_3 = 40 until
//     KEYEVENT_END (kingChappyState.cpp:148-158, 225-248).
//
// Slot tables: model-space translation of each kamuN joint at the eat frame(s),
// evaluated from the retail enemy.bmd + attack.bca with the pose-bank J3D path
// (output/claude-orch/p2-884/chappy_mouth_slots.py -> chappy_mouth_slots.txt):
//   Chappy/Yellow/Kuma  model 40d73fca.. / faf57b52.. attack 8037b720..  (identical slot rows)
//   FireChappy          model c73bfc5f.. attack e4e63e53..
//   LeafChappy          model 4200ba23.. attack 5bf01472..
//   KumaKo/BlueKochappy model 611331b5.. attack 44b87c73..  (shared Kochappy skeleton)
//   KingChappy          model 44934adc.. attack 5f766fa2..  frames 40..94 (clip 95, END exclusive)
// Convention: +z facing, +y up from the feet; world = actor + R_y(heading) *
// (local * scale), local +z -> (sin h, 0, cos h), local +x -> (cos h, 0, -sin h),
// the same heading convention the FSMs drive with (atan2(dx, dz)).
// Every row sits in front of the feet plane (min z - radius > 0), so a Pikmin
// at or behind the actor can never be eaten, as in the source.
#include <cmath>

namespace p2chappymouth {

constexpr int MaxSlots = 9;

struct Vec3 {
    float x, y, z;
};

struct Profile {
    unsigned source;         // P2 EnemyID
    int slots;               // source initMouthSlots count
    float radius;            // MouthCollPart::mRadius (before scale)
    float scale;             // mScaleModifier (1.0 for every admitted actor)
    int firstFrame;          // eat event frame (KEYEVENT_2) or King window start (KEYEVENT_3)
    int lastFrame;           // == firstFrame for one-shot bites; 94 for the King window
    const float (*table)[3]; // [(lastFrame - firstFrame + 1) * slots] model-space kamuN
};

namespace data {
inline constexpr float kChappyTable[][3] = {
    {-23.117f, 17.664f, 61.190f},
    {-37.945f, 16.353f, 52.317f},
    {-18.941f, -5.566f, 74.475f},
    {22.921f, -1.486f, 59.404f},
    {18.670f, 4.952f, 75.621f},
};
inline constexpr float kFireTable[][3] = {
    {-20.902f, 23.940f, 63.780f},
    {-34.806f, 23.605f, 59.950f},
    {-12.755f, 9.970f, 86.267f},
    {27.308f, 10.104f, 66.264f},
    {24.222f, 21.126f, 80.358f},
};
inline constexpr float kLeafTable[][3] = {
    {-12.021f, 9.185f, 31.819f},
    {9.951f, 2.285f, 39.788f},
    {-9.984f, -3.163f, 39.087f},
};
inline constexpr float kKochappyTable[][3] = {
    {-1.714f, 3.376f, 29.979f},
};
inline constexpr float kKingTable[][3] = {
    /* 40 */ {-10.422f, 41.567f, 61.539f}, {-6.731f, 46.399f, 61.729f}, {5.690f, 50.813f, 62.719f}, {-5.174f, 46.173f, 59.017f}, {-10.334f, 39.329f, 57.749f}, {12.732f, 31.503f, 54.900f}, {-7.311f, 35.713f, 55.500f}, {13.774f, 42.132f, 59.023f}, {6.885f, 44.440f, 59.577f},
    /* 41 */ {-12.243f, 16.246f, 93.001f}, {-8.017f, 21.584f, 94.764f}, {6.120f, 24.589f, 97.777f}, {-6.212f, 26.892f, 90.848f}, {-12.104f, 21.360f, 87.178f}, {14.083f, 17.862f, 80.973f}, {-8.667f, 21.705f, 82.919f}, {15.286f, 21.994f, 89.837f}, {7.468f, 23.620f, 91.244f},
    /* 42 */ {-13.441f, 6.863f, 108.095f}, {-9.040f, 6.261f, 111.026f}, {5.669f, -5.198f, 114.308f}, {-7.110f, 12.563f, 107.383f}, {-13.277f, 10.411f, 102.948f}, {14.259f, 13.525f, 96.051f}, {-9.617f, 15.626f, 98.459f}, {15.437f, 8.202f, 105.868f}, {7.224f, 8.438f, 107.509f},
    /* 43 */ {-14.313f, 8.286f, 109.244f}, {-9.672f, 11.906f, 114.024f}, {5.726f, 10.489f, 124.858f}, {-7.681f, 17.313f, 110.788f}, {-14.079f, 13.044f, 106.136f}, {14.049f, 11.523f, 97.809f}, {-10.408f, 14.786f, 100.265f}, {15.430f, 12.694f, 109.688f}, {7.033f, 13.876f, 111.524f},
    /* 44 */ {-15.424f, 1.672f, 110.614f}, {-10.581f, 8.256f, 115.662f}, {5.456f, 16.077f, 128.706f}, {-8.450f, 17.410f, 113.210f}, {-15.017f, 13.405f, 108.421f}, {13.715f, 12.371f, 100.028f}, {-11.276f, 15.537f, 102.559f}, {15.166f, 12.788f, 112.010f}, {6.588f, 13.873f, 113.879f},
    /* 45 */ {-16.374f, 6.121f, 112.636f}, {-11.492f, 8.087f, 117.340f}, {4.614f, 2.346f, 127.347f}, {-9.328f, 15.316f, 114.794f}, {-16.020f, 12.570f, 110.145f}, {13.311f, 14.347f, 102.402f}, {-12.163f, 16.843f, 104.868f}, {14.728f, 10.801f, 113.472f}, {5.979f, 11.321f, 115.240f},
    /* 46 */ {-17.147f, 13.614f, 116.579f}, {-12.251f, 12.129f, 120.531f}, {3.864f, -2.330f, 127.578f}, {-10.147f, 15.762f, 116.527f}, {-16.993f, 12.762f, 111.917f}, {12.771f, 13.935f, 103.909f}, {-13.092f, 16.642f, 106.366f}, {14.275f, 11.132f, 115.319f}, {5.397f, 11.788f, 117.114f},
    /* 47 */ {-18.274f, 9.852f, 117.329f}, {-13.104f, 13.353f, 122.208f}, {3.778f, 12.035f, 133.642f}, {-10.878f, 18.781f, 118.634f}, {-17.895f, 14.552f, 113.876f}, {12.134f, 12.651f, 105.109f}, {-14.030f, 16.212f, 107.646f}, {13.845f, 13.890f, 117.566f}, {4.879f, 15.180f, 119.479f},
    /* 48 */ {-19.421f, 4.785f, 118.403f}, {-14.053f, 11.248f, 123.360f}, {3.431f, 19.111f, 136.515f}, {-11.600f, 20.306f, 120.444f}, {-18.708f, 16.292f, 115.629f}, {11.667f, 14.657f, 106.913f}, {-14.771f, 18.249f, 109.468f}, {13.367f, 15.306f, 119.323f}, {4.305f, 16.558f, 121.238f},
    /* 49 */ {-20.012f, 10.314f, 119.777f}, {-14.777f, 12.197f, 124.416f}, {2.179f, 6.513f, 134.777f}, {-12.303f, 19.359f, 121.454f}, {-19.433f, 16.585f, 116.833f}, {11.366f, 17.582f, 108.804f}, {-15.311f, 20.642f, 111.251f}, {12.842f, 14.332f, 120.264f}, {3.678f, 15.073f, 122.060f},
    /* 50 */ {-20.155f, 18.108f, 122.692f}, {-15.104f, 16.505f, 126.642f}, {1.250f, 1.899f, 134.200f}, {-12.779f, 20.027f, 122.424f}, {-19.992f, 17.054f, 117.889f}, {10.984f, 17.160f, 109.746f}, {-15.813f, 20.676f, 112.140f}, {12.459f, 14.656f, 121.362f}, {3.252f, 15.617f, 123.155f},
    /* 51 */ {-20.832f, 14.663f, 122.822f}, {-15.435f, 17.958f, 127.502f}, {1.764f, 16.300f, 138.826f}, {-12.908f, 23.205f, 123.721f}, {-20.253f, 19.073f, 119.093f}, {10.645f, 15.737f, 110.463f}, {-16.157f, 20.412f, 112.838f}, {12.346f, 17.288f, 122.849f}, {3.155f, 18.992f, 124.701f},
    /* 52 */ {-21.492f, 9.615f, 123.200f}, {-15.850f, 15.819f, 127.911f}, {1.996f, 23.203f, 140.679f}, {-12.907f, 24.603f, 124.786f}, {-20.257f, 20.733f, 120.073f}, {10.753f, 17.192f, 111.653f}, {-16.047f, 22.252f, 113.955f}, {12.303f, 18.259f, 123.927f}, {3.100f, 20.056f, 125.743f},
    /* 53 */ {-20.935f, 14.883f, 123.636f}, {-15.756f, 16.416f, 128.107f}, {0.521f, 9.886f, 138.345f}, {-12.848f, 23.285f, 125.099f}, {-20.068f, 20.802f, 120.537f}, {11.246f, 19.427f, 112.968f}, {-15.530f, 24.404f, 115.062f}, {12.238f, 16.477f, 124.245f}, {2.995f, 17.909f, 125.904f},
    /* 54 */ {-19.619f, 22.177f, 125.573f}, {-14.957f, 20.122f, 129.383f}, {-0.230f, 4.248f, 136.911f}, {-12.357f, 23.258f, 125.279f}, {-19.565f, 20.720f, 120.780f}, {11.648f, 17.953f, 113.410f}, {-14.931f, 23.841f, 115.265f}, {12.491f, 15.670f, 124.697f}, {3.304f, 17.476f, 126.275f},
    /* 55 */ {-19.138f, 18.140f, 124.558f}, {-14.078f, 20.726f, 129.157f}, {1.363f, 17.143f, 140.486f}, {-11.099f, 25.590f, 125.684f}, {-18.351f, 22.158f, 120.991f}, {12.397f, 15.178f, 113.795f}, {-13.769f, 22.964f, 115.164f}, {13.334f, 16.740f, 125.689f}, {4.297f, 19.528f, 127.151f},
    /* 56 */ {-20.123f, 12.413f, 122.813f}, {-14.967f, 17.651f, 127.858f}, {0.369f, 22.366f, 141.652f}, {-11.076f, 26.010f, 125.523f}, {-17.951f, 23.295f, 120.381f}, {12.675f, 14.017f, 114.934f}, {-12.895f, 23.949f, 115.003f}, {12.623f, 15.094f, 126.650f}, {3.710f, 18.587f, 127.642f},
    /* 57 */ {-19.035f, 16.636f, 120.870f}, {-15.423f, 17.100f, 125.840f}, {-4.833f, 7.331f, 137.615f}, {-11.616f, 23.384f, 124.161f}, {-17.644f, 22.855f, 118.778f}, {12.826f, 12.061f, 116.138f}, {-11.720f, 24.987f, 114.593f}, {10.831f, 9.145f, 126.499f}, {2.111f, 13.348f, 126.811f},
    /* 58 */ {-14.839f, 25.471f, 121.825f}, {-13.111f, 20.623f, 125.492f}, {-7.758f, -3.480f, 132.519f}, {-9.791f, 22.892f, 122.813f}, {-15.011f, 23.935f, 117.372f}, {14.384f, 9.187f, 116.912f}, {-8.499f, 26.085f, 113.995f}, {10.836f, 4.756f, 126.272f}, {2.563f, 10.216f, 126.023f},
    /* 59 */ {-8.951f, 29.303f, 121.440f}, {-8.330f, 23.664f, 124.822f}, {-6.745f, -2.663f, 131.176f}, {-5.189f, 24.558f, 121.955f}, {-9.680f, 26.198f, 116.479f}, {17.081f, 6.704f, 117.162f}, {-3.048f, 27.181f, 113.388f}, {12.645f, 3.217f, 126.195f}, {5.254f, 10.003f, 125.621f},
    /* 60 */ {-0.992f, 29.554f, 120.498f}, {-1.133f, 24.372f, 123.844f}, {-2.921f, -0.761f, 130.220f}, {1.846f, 24.961f, 121.118f}, {-1.907f, 27.023f, 115.851f}, {20.659f, 3.834f, 116.087f}, {4.437f, 26.935f, 112.761f}, {15.839f, 1.347f, 124.924f}, {9.773f, 9.130f, 124.489f},
    /* 61 */ {11.939f, 30.291f, 119.511f}, {10.906f, 25.528f, 122.748f}, {4.551f, 2.061f, 128.987f}, {13.433f, 25.451f, 119.887f}, {10.504f, 28.345f, 115.136f}, {25.758f, -0.372f, 113.072f}, {15.974f, 26.571f, 111.568f}, {21.187f, -1.420f, 122.050f}, {17.375f, 7.826f, 122.263f},
    /* 62 */ {29.763f, 29.836f, 116.655f}, {28.274f, 25.685f, 120.092f}, {18.626f, 5.102f, 127.836f}, {29.867f, 25.075f, 116.875f}, {27.642f, 28.737f, 112.774f}, {33.480f, -4.318f, 107.989f}, {31.316f, 25.361f, 108.224f}, {30.470f, -3.946f, 117.681f}, {29.434f, 6.378f, 118.565f},
    /* 63 */ {48.478f, 26.194f, 109.723f}, {47.977f, 22.138f, 113.528f}, {40.808f, 2.516f, 124.134f}, {48.145f, 21.782f, 109.959f}, {45.660f, 26.066f, 106.696f}, {45.059f, -8.524f, 99.557f}, {46.768f, 22.421f, 100.974f}, {45.620f, -8.365f, 110.082f}, {46.232f, 2.385f, 111.456f},
    /* 64 */ {54.759f, 26.085f, 104.058f}, {55.486f, 22.117f, 107.857f}, {53.280f, 2.166f, 118.831f}, {54.986f, 22.014f, 104.236f}, {51.870f, 26.169f, 101.259f}, {52.935f, -9.715f, 92.537f}, {52.037f, 22.478f, 95.094f}, {55.412f, -9.429f, 103.377f}, {55.283f, 1.762f, 105.176f},
    /* 65 */ {48.033f, 27.001f, 107.004f}, {49.718f, 23.783f, 110.384f}, {52.563f, 5.095f, 118.538f}, {49.414f, 23.706f, 106.680f}, {45.400f, 26.367f, 103.767f}, {56.188f, -6.848f, 90.047f}, {46.763f, 22.970f, 97.023f}, {58.118f, -5.594f, 101.458f}, {54.987f, 4.844f, 104.834f},
    /* 66 */ {36.896f, 24.237f, 112.450f}, {39.630f, 23.008f, 115.422f}, {48.766f, 10.372f, 120.962f}, {39.646f, 22.695f, 111.415f}, {34.915f, 22.152f, 108.683f}, {57.789f, 0.388f, 88.810f}, {37.783f, 19.763f, 101.001f}, {58.672f, 3.397f, 101.152f}, {51.786f, 10.346f, 106.412f},
    /* 67 */ {23.644f, 18.633f, 120.526f}, {27.728f, 19.701f, 121.691f}, {44.262f, 15.675f, 121.038f}, {28.900f, 20.171f, 116.210f}, {24.582f, 16.591f, 114.154f}, {54.884f, 13.555f, 88.695f}, {28.186f, 16.824f, 105.979f}, {54.654f, 16.187f, 100.943f}, {45.365f, 17.506f, 107.962f},
    /* 68 */ {15.827f, 12.809f, 127.816f}, {19.875f, 17.340f, 126.281f}, {39.005f, 26.500f, 116.749f}, {19.756f, 19.315f, 120.229f}, {16.905f, 12.801f, 119.713f}, {42.175f, 29.314f, 90.751f}, {18.400f, 15.307f, 112.427f}, {43.450f, 31.999f, 100.311f}, {35.318f, 27.323f, 108.629f},
    /* 69 */ {17.010f, 13.565f, 128.207f}, {17.731f, 20.215f, 125.812f}, {27.972f, 38.823f, 112.754f}, {14.062f, 20.869f, 121.733f}, {14.637f, 12.453f, 122.421f}, {23.182f, 36.577f, 93.917f}, {12.809f, 14.024f, 116.850f}, {25.552f, 42.474f, 100.069f}, {22.184f, 35.106f, 108.535f},
    /* 70 */ {19.798f, 19.708f, 124.363f}, {16.527f, 25.586f, 122.401f}, {14.170f, 43.734f, 110.039f}, {10.090f, 22.969f, 120.991f}, {14.549f, 15.213f, 121.800f}, {6.333f, 32.721f, 97.944f}, {10.544f, 13.950f, 118.249f}, {7.803f, 41.768f, 101.341f}, {9.437f, 35.990f, 108.660f},
    /* 71 */ {21.146f, 20.221f, 119.212f}, {15.387f, 24.588f, 118.678f}, {4.305f, 38.541f, 110.713f}, {6.923f, 20.055f, 119.392f}, {13.599f, 13.719f, 119.190f}, {-4.671f, 23.920f, 102.011f}, {8.390f, 10.885f, 117.057f}, {-3.785f, 33.678f, 104.537f}, {0.879f, 29.959f, 109.952f},
    /* 72 */ {21.170f, 13.748f, 114.643f}, {14.637f, 17.606f, 115.310f}, {-0.043f, 29.624f, 111.395f}, {4.086f, 13.368f, 117.244f}, {11.018f, 7.564f, 116.094f}, {-11.825f, 16.126f, 103.525f}, {4.664f, 4.907f, 114.592f}, {-9.726f, 25.121f, 106.150f}, {-3.769f, 21.968f, 110.189f},
    /* 73 */ {10.433f, 5.876f, 116.158f}, {4.747f, 10.860f, 116.546f}, {-8.166f, 24.249f, 112.628f}, {-7.872f, 10.668f, 118.153f}, {-2.548f, 3.945f, 117.547f}, {-24.149f, 15.388f, 104.262f}, {-9.912f, 3.298f, 115.724f}, {-19.217f, 22.469f, 106.844f}, {-13.809f, 18.838f, 111.022f},
    /* 74 */ {-20.373f, -4.979f, 121.586f}, {-22.943f, 2.203f, 121.433f}, {-26.876f, 20.615f, 117.504f}, {-33.551f, 9.646f, 118.826f}, {-31.898f, 1.296f, 118.272f}, {-40.136f, 23.457f, 102.766f}, {-37.315f, 5.208f, 114.142f}, {-34.289f, 25.958f, 108.443f}, {-32.785f, 19.780f, 112.862f},
    /* 75 */ {-62.396f, -1.978f, 108.273f}, {-61.932f, 5.588f, 109.572f}, {-56.670f, 23.865f, 113.032f}, {-63.900f, 17.085f, 104.361f}, {-64.563f, 8.677f, 101.618f}, {-51.858f, 32.326f, 98.361f}, {-63.384f, 14.602f, 97.688f}, {-52.473f, 32.120f, 106.080f}, {-56.516f, 25.887f, 106.492f},
    /* 76 */ {-79.237f, 23.516f, 80.707f}, {-77.595f, 30.644f, 83.015f}, {-71.502f, 46.242f, 92.705f}, {-71.970f, 38.560f, 81.022f}, {-73.101f, 29.674f, 77.832f}, {-56.569f, 43.746f, 92.820f}, {-68.092f, 32.240f, 78.383f}, {-61.991f, 48.291f, 95.329f}, {-66.458f, 44.615f, 90.527f},
    /* 77 */ {-72.905f, 33.360f, 64.064f}, {-72.146f, 40.253f, 66.512f}, {-71.144f, 55.232f, 76.829f}, {-65.866f, 45.538f, 69.523f}, {-66.063f, 36.248f, 67.003f}, {-59.346f, 47.778f, 89.623f}, {-62.058f, 37.177f, 71.405f}, {-64.524f, 54.863f, 86.461f}, {-65.916f, 51.717f, 79.863f},
    /* 78 */ {-63.364f, 35.504f, 62.200f}, {-63.755f, 42.404f, 63.467f}, {-67.681f, 57.684f, 69.139f}, {-59.072f, 46.620f, 68.643f}, {-58.261f, 36.924f, 67.708f}, {-61.198f, 49.377f, 87.276f}, {-56.126f, 37.527f, 73.340f}, {-64.981f, 57.298f, 80.926f}, {-63.551f, 53.789f, 75.547f},
    /* 79 */ {-55.932f, 34.560f, 67.610f}, {-56.986f, 41.479f, 67.323f}, {-63.677f, 57.153f, 67.107f}, {-53.706f, 45.485f, 72.254f}, {-52.203f, 35.463f, 72.847f}, {-61.348f, 50.468f, 86.411f}, {-51.425f, 36.470f, 78.285f}, {-64.054f, 58.197f, 78.804f}, {-60.847f, 53.927f, 75.338f},
    /* 80 */ {-51.578f, 33.830f, 74.481f}, {-52.541f, 40.761f, 73.210f}, {-59.314f, 56.985f, 69.404f}, {-49.471f, 44.668f, 77.062f}, {-47.796f, 34.196f, 78.427f}, {-59.197f, 53.161f, 88.599f}, {-47.503f, 35.912f, 83.450f}, {-61.457f, 60.430f, 80.787f}, {-57.597f, 54.991f, 78.340f},
    /* 81 */ {-48.206f, 34.511f, 81.433f}, {-48.657f, 41.396f, 79.689f}, {-54.012f, 58.279f, 74.497f}, {-44.831f, 44.765f, 82.343f}, {-43.461f, 33.576f, 83.881f}, {-53.204f, 57.932f, 93.794f}, {-42.689f, 36.055f, 88.664f}, {-55.809f, 64.946f, 86.159f}, {-52.391f, 57.879f, 83.737f},
    /* 82 */ {-43.772f, 35.737f, 88.343f}, {-43.873f, 42.644f, 86.754f}, {-48.087f, 60.473f, 82.379f}, {-39.218f, 44.784f, 88.188f}, {-38.365f, 32.821f, 88.934f}, {-43.304f, 60.332f, 101.508f}, {-36.345f, 35.150f, 93.555f}, {-47.034f, 68.335f, 94.875f}, {-44.948f, 60.204f, 91.556f},
    /* 83 */ {-38.116f, 34.928f, 94.147f}, {-37.929f, 42.173f, 93.379f}, {-40.997f, 61.821f, 91.867f}, {-32.782f, 43.287f, 93.548f}, {-32.719f, 31.134f, 92.554f}, {-30.988f, 55.785f, 108.970f}, {-29.223f, 31.882f, 96.696f}, {-35.860f, 66.052f, 104.636f}, {-35.676f, 58.559f, 100.007f},
    /* 84 */ {-32.971f, 27.811f, 97.330f}, {-32.923f, 35.044f, 98.039f}, {-35.890f, 53.791f, 101.172f}, {-27.573f, 37.822f, 97.190f}, {-27.631f, 28.066f, 93.949f}, {-20.413f, 37.096f, 112.148f}, {-22.782f, 26.387f, 96.789f}, {-26.870f, 48.128f, 111.622f}, {-28.254f, 45.286f, 106.236f},
    /* 85 */ {-27.455f, 19.071f, 96.787f}, {-27.309f, 25.194f, 98.824f}, {-29.183f, 39.462f, 105.717f}, {-22.347f, 30.336f, 97.855f}, {-23.176f, 24.323f, 93.509f}, {-8.830f, 18.758f, 107.362f}, {-17.162f, 21.720f, 94.347f}, {-15.994f, 27.342f, 110.421f}, {-19.508f, 29.049f, 106.145f},
    /* 86 */ {-19.496f, 18.290f, 95.514f}, {-18.579f, 23.232f, 97.693f}, {-17.157f, 33.606f, 105.082f}, {-14.521f, 28.803f, 96.188f}, {-17.132f, 24.612f, 92.366f}, {4.397f, 15.481f, 99.635f}, {-10.767f, 22.432f, 91.369f}, {-1.469f, 21.784f, 104.567f}, {-7.249f, 24.689f, 102.100f},
    /* 87 */ {-10.424f, 21.271f, 92.227f}, {-8.484f, 24.612f, 94.014f}, {-2.970f, 29.789f, 100.183f}, {-5.581f, 29.982f, 91.935f}, {-9.899f, 27.325f, 89.218f}, {15.435f, 17.709f, 90.088f}, {-4.249f, 26.234f, 86.849f}, {12.169f, 21.159f, 95.754f}, {5.036f, 24.376f, 95.101f},
    /* 88 */ {-2.550f, 23.051f, 86.331f}, {0.503f, 24.651f, 87.692f}, {10.067f, 24.492f, 92.137f}, {2.344f, 29.746f, 85.415f}, {-3.233f, 28.409f, 83.617f}, {21.941f, 20.977f, 79.582f}, {0.897f, 28.970f, 80.499f}, {21.870f, 21.070f, 85.329f}, {14.534f, 23.823f, 86.129f},
    /* 89 */ {3.524f, 23.913f, 79.495f}, {7.423f, 24.200f, 80.382f}, {19.774f, 20.498f, 82.889f}, {8.224f, 29.317f, 77.991f}, {1.924f, 28.838f, 76.818f}, {24.431f, 25.509f, 70.130f}, {4.314f, 31.158f, 73.526f}, {27.311f, 22.559f, 75.487f}, {20.545f, 24.247f, 77.116f},
    /* 90 */ {7.367f, 26.175f, 73.195f}, {11.682f, 25.788f, 73.704f}, {25.185f, 20.847f, 74.867f}, {11.490f, 31.256f, 70.915f}, {4.896f, 31.249f, 70.069f}, {24.261f, 31.943f, 62.392f}, {5.869f, 34.907f, 66.696f}, {29.258f, 26.867f, 67.547f}, {23.269f, 27.447f, 69.475f},
    /* 91 */ {7.865f, 34.937f, 67.007f}, {12.277f, 34.819f, 67.342f}, {25.996f, 31.126f, 68.104f}, {11.276f, 39.010f, 63.947f}, {4.679f, 38.338f, 63.205f}, {22.058f, 38.357f, 55.665f}, {4.818f, 40.882f, 59.698f}, {28.151f, 35.383f, 60.923f}, {22.655f, 35.987f, 62.767f},
    /* 92 */ {3.899f, 41.361f, 60.775f}, {8.171f, 41.397f, 61.181f}, {21.563f, 38.523f, 62.267f}, {7.397f, 44.666f, 57.372f}, {1.176f, 43.649f, 56.451f}, {18.891f, 43.122f, 49.911f}, {1.628f, 45.411f, 52.922f}, {24.235f, 41.515f, 55.388f}, {18.671f, 42.154f, 56.898f},
    /* 93 */ {-1.937f, 45.952f, 54.924f}, {2.014f, 46.183f, 55.555f}, {14.725f, 44.128f, 57.489f}, {2.160f, 48.611f, 51.679f}, {-3.389f, 47.264f, 50.524f}, {15.579f, 46.510f, 45.311f}, {-2.024f, 48.390f, 47.085f}, {19.120f, 46.065f, 50.912f}, {13.288f, 46.661f, 52.002f},
    /* 94 */ {-7.063f, 47.754f, 50.573f}, {-3.602f, 48.090f, 51.471f}, {7.910f, 46.540f, 54.357f}, {-2.497f, 50.187f, 47.749f}, {-7.287f, 48.739f, 46.370f}, {12.707f, 48.411f, 42.157f}, {-4.950f, 49.714f, 43.010f}, {14.277f, 48.278f, 47.877f}, {8.263f, 48.701f, 48.657f},
};
} // namespace data

inline constexpr Profile kProfiles[] = {
    {2, 5, 35.0f, 1.0f, 10, 10, data::kChappyTable},
    {33, 5, 35.0f, 1.0f, 10, 10, data::kFireTable},
    {35, 5, 35.0f, 1.0f, 10, 10, data::kChappyTable},
    {43, 5, 35.0f, 1.0f, 10, 10, data::kChappyTable},
    {53, 9, 25.0f, 1.0f, 40, 94, data::kKingTable},
    {67, 3, 30.0f, 1.0f, 10, 10, data::kLeafTable},
    {76, 1, 15.0f, 1.0f, 8, 8, data::kKochappyTable},
    {44, 1, 15.0f, 1.0f, 8, 8, data::kKochappyTable},
};

static_assert(sizeof(data::kChappyTable) / sizeof(data::kChappyTable[0]) == 5, "Chappy table rows");
static_assert(sizeof(data::kFireTable) / sizeof(data::kFireTable[0]) == 5, "Fire table rows");
static_assert(sizeof(data::kLeafTable) / sizeof(data::kLeafTable[0]) == 3, "Leaf table rows");
static_assert(sizeof(data::kKochappyTable) / sizeof(data::kKochappyTable[0]) == 1, "Kochappy table rows");
static_assert(sizeof(data::kKingTable) / sizeof(data::kKingTable[0]) == 55 * 9, "King table rows");

inline const Profile* profileForSource(unsigned source)
{
    for (const Profile& p : kProfiles) {
        if (p.source == source) return &p;
    }
    return nullptr;
}

inline bool frameInWindow(const Profile& p, int frame)
{
    return frame >= p.firstFrame && frame <= p.lastFrame;
}

inline float effectiveRadius(const Profile& p)
{
    return p.radius * p.scale;
}

// Model-space kamuN position (scaled). `frame` is clamped to the table window.
inline Vec3 slotLocal(const Profile& p, int frame, int slot)
{
    if (frame < p.firstFrame) frame = p.firstFrame;
    if (frame > p.lastFrame) frame = p.lastFrame;
    const float* row = p.table[(frame - p.firstFrame) * p.slots + slot];
    return Vec3{row[0] * p.scale, row[1] * p.scale, row[2] * p.scale};
}

inline Vec3 localToWorld(const Vec3& actor, float heading, const Vec3& local)
{
    const float s = std::sin(heading), c = std::cos(heading);
    return Vec3{actor.x + local.x * c + local.z * s, actor.y + local.y, actor.z - local.x * s + local.z * c};
}

inline Vec3 toLocal(const Vec3& actor, float heading, const Vec3& world)
{
    const float s = std::sin(heading), c = std::cos(heading);
    const float dx = world.x - actor.x, dz = world.z - actor.z;
    return Vec3{dx * c - dz * s, world.y - actor.y, dx * s + dz * c};
}

inline Vec3 slotWorld(const Profile& p, int frame, int slot, const Vec3& actor, float heading)
{
    return localToWorld(actor, heading, slotLocal(p, frame, slot));
}

inline float distance(const Vec3& a, const Vec3& b)
{
    const float dx = a.x - b.x, dy = a.y - b.y, dz = a.z - b.z;
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}

// One Pikmin as the eat pass sees it (snapshotted before any stimulate).
struct Prey {
    Vec3 pos;
    bool alive;
    bool visible;
    bool buried;
    bool stuckToSelf;     // stuck to this eater's body (source piki->mSticker == enemy)
    bool stuckToAnyMouth; // isStickToMouth() on any eater
    bool stuckToAny;      // isStickTo() on anything (diagnostics / legacy oracle only)
};

// Source EatPikminDefaultCondition (isPikmin && mSticker != enemy &&
// !isStickToMouth) plus the P1 "active Piki" test that the P2 pikiMgr
// population implies (live, drawn, not a buried sprout). A Pikmin stuck to
// another creature is eligible, exactly as in the source; the P1
// InteractSwallow receiver ends that stick first (interactBattle.cpp:547-551).
inline bool eligible(const Prey& p)
{
    return p.alive && p.visible && !p.buried && !p.stuckToSelf && !p.stuckToAnyMouth;
}

// One source EnemyFunc::eatPikmin pass (enemyAction.cpp:1117-1138). For each
// eligible prey in manager order: take the first EMPTY slot in index order
// whose 3D distance is strictly < radius, stimulate it, mark the slot occupied
// only when the receiver accepted, then move to the next prey either way.
// There is no overflow path: no reachable empty slot means no capture.
// `occupied[p.slots]` is in/out. `stimulate(preyIndex, slotIndex)` returns the
// receiver result. Returns the number of accepted captures.
template <class Stimulate>
int eat(const Profile& p, int frame, const Vec3& actor, float heading, const Prey* prey, int count,
        bool* occupied, Stimulate&& stimulate)
{
    if (!frameInWindow(p, frame) || p.slots <= 0 || p.slots > MaxSlots) return 0;
    Vec3 slotPos[MaxSlots];
    for (int i = 0; i < p.slots; ++i) slotPos[i] = slotWorld(p, frame, i, actor, heading);
    const float radius = effectiveRadius(p);
    int eaten = 0;
    for (int n = 0; n < count; ++n) {
        if (!eligible(prey[n])) continue;
        for (int i = 0; i < p.slots; ++i) {
            if (occupied[i]) continue;
            if (distance(slotPos[i], prey[n].pos) < radius) {
                if (stimulate(n, i)) {
                    occupied[i] = true;
                    ++eaten;
                }
                break;
            }
        }
    }
    return eaten;
}

// P2 slot -> P1 host 'slot' CollPart child. Hosts with fewer children than
// the P2 slot count share parts (i % hostCount); -1 when the host has no
// mouth part at all, which refuses the capture (never a null-part swallow).
inline int hostPartIndex(int slot, int hostCount)
{
    return hostCount > 0 ? slot % hostCount : -1;
}

// Diagnostics only (never decides a capture): index of the nearest prey within
// `radius` of the actor feet (3D) that passes `accept`, or -1.
template <class Accept>
int nearestIndex(const Prey* prey, int count, const Vec3& actor, float radius, Accept&& accept)
{
    int best = -1;
    float bestD = radius;
    for (int n = 0; n < count; ++n) {
        if (!accept(prey[n])) continue;
        const float d = distance(prey[n].pos, actor);
        if (d < bestD) {
            bestD = d;
            best = n;
        }
    }
    return best;
}

// The pre-#884 selection filter (alive, not stuck anywhere); used only for the
// legacy_would_eat_behind log field.
inline bool legacyEdible(const Prey& p)
{
    return p.alive && !p.stuckToAnyMouth && !p.stuckToAny;
}

// ---- Window diagnostics (never decide a capture) ---------------------------
// Largest horizontal reach of any slot over the profile's window plus the
// radius: prey beyond it (or at/behind the feet plane) cannot be captured.
inline float maxReach(const Profile& p)
{
    float best = 0.0f;
    for (int f = p.firstFrame; f <= p.lastFrame; ++f) {
        for (int i = 0; i < p.slots; ++i) {
            const Vec3 l = slotLocal(p, f, i);
            const float r = std::sqrt(l.x * l.x + l.z * l.z);
            if (r > best) best = r;
        }
    }
    return best + effectiveRadius(p);
}

// Aggregated over every evaluated eat frame of one bite / King window.
struct WindowDiag {
    int frames = 0;             // eat frames observed
    float closest = -1.0f;      // min 3D distance eligible prey -> FREE slot (<0: none)
    Vec3 closestLocal{0, 0, 0}; // that prey in the actor-local frame at that frame
    int closestFrame = -1;
    int closestSlot = -1;
    int front = 0;       // max per frame: eligible prey with local z > 0 within maxReach
    int stuckSelf = 0;   // max per frame: Pikmin stuck to this eater's body (not the mouth)
    int eligibleMin = -1; // min per frame eligible count (eligible= in the log is the max)
};

// Observe one eat frame BEFORE eat() mutates `occupied`.
inline void observe(WindowDiag& d, const Profile& p, int frame, const Vec3& actor, float heading, const Prey* prey,
                    int count, const bool* occupied)
{
    if (!frameInWindow(p, frame) || p.slots <= 0 || p.slots > MaxSlots) return;
    ++d.frames;
    Vec3 slotPos[MaxSlots];
    for (int i = 0; i < p.slots; ++i) slotPos[i] = slotWorld(p, frame, i, actor, heading);
    const float reach = maxReach(p);
    int front = 0, stuck = 0, elig = 0;
    for (int n = 0; n < count; ++n) {
        if (prey[n].alive && prey[n].stuckToSelf) ++stuck;
        if (!eligible(prey[n])) continue;
        ++elig;
        const Vec3 l = toLocal(actor, heading, prey[n].pos);
        if (l.z > 0.0f && std::sqrt(l.x * l.x + l.z * l.z) <= reach) ++front;
        for (int i = 0; i < p.slots; ++i) {
            if (occupied[i]) continue;
            const float dist = distance(slotPos[i], prey[n].pos);
            if (d.closest < 0.0f || dist < d.closest) {
                d.closest = dist;
                d.closestLocal = l;
                d.closestFrame = frame;
                d.closestSlot = i;
            }
        }
    }
    if (front > d.front) d.front = front;
    if (stuck > d.stuckSelf) d.stuckSelf = stuck;
    if (d.eligibleMin < 0 || elig < d.eligibleMin) d.eligibleMin = elig;
}

// ---- KingChappy targeting (#884 runtime diagnosis) --------------------------
// Source KingChappy::Obj::searchTarget (kingChappy.cpp:1131-1178) and
// Obj::checkAttack (kingChappy.cpp:1778-1822). The Emperor never starts the
// tongue attack on a target inside its "invisible range" (proper fp06): the
// tongue slots only reach ground prey from ~75 units out (kKingTable frames
// 41..94), so a target under the chin would make the whole 40..94 window
// sweep empty ground. Pikmin are also filtered to a +-50 height band and must
// be nearer than the nearest captain in the search cone (shared searchDist).
// Retail values: KingChappy/enemyparm.txt (fp06 = 80; the decomp default is 70).
namespace king {
constexpr float SearchDistance = 500.0f; // general fp14
constexpr float SearchAngleDeg = 120.0f; // general fp15
constexpr float SearchHeight = 50.0f;    // searchTarget minY/maxY (kingChappy.cpp:1155-1157)
constexpr float InvisibleRange = 80.0f;  // proper fp06 "invisible range"
constexpr float AttackRange = 130.0f;    // general fp20 (3D: Creature::getSqrTargetSeparation)
constexpr float AttackAngleDeg = 30.0f;  // general fp21
constexpr float DegToRad = 3.14159265f / 180.0f;

inline float angDist(const Vec3& actor, float heading, const Vec3& target)
{
    float a = std::atan2(target.x - actor.x, target.z - actor.z) - heading;
    while (a > 3.14159265f) a -= 2.0f * 3.14159265f;
    while (a < -3.14159265f) a += 2.0f * 3.14159265f;
    return a;
}

inline float sqrXZ(const Vec3& a, const Vec3& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return dx * dx + dz * dz;
}

// Source searchTarget: getNearestNavi within fp14/fp15, then each searchable
// Pikmin in the +-50 band and search cone with invisible^2 < distXZ^2 <
// current best (the captain's distance when one was found). Returns -2 for
// the captain, a Pikmin index, or -1 for no target.
struct Candidate {
    Vec3 pos;
    bool searchable;      // Piki::isSearchable (alive, not stuck to a mouth)
    bool latched = false; // stuck to THIS King's body (never eaten: EatPikminDefaultCondition)
};

inline int selectTarget(const Vec3& actor, float heading, const Vec3* navi, const Candidate* piki, int count)
{
    int best = -1;
    float bestSq = SearchDistance * SearchDistance;
    const float cone = SearchAngleDeg * DegToRad;
    if (navi && std::fabs(angDist(actor, heading, *navi)) <= cone) {
        const float d = sqrXZ(*navi, actor);
        if (d < bestSq) {
            bestSq = d;
            best = -2;
        }
    }
    const float inv = InvisibleRange * InvisibleRange;
    for (int n = 0; n < count; ++n) {
        if (!piki[n].searchable) continue;
        const Vec3& q = piki[n].pos;
        if (q.y < actor.y - SearchHeight || q.y > actor.y + SearchHeight) continue;
        if (std::fabs(angDist(actor, heading, q)) > cone) continue;
        const float d = sqrXZ(q, actor);
        if (d < bestSq && d > inv) {
            bestSq = d;
            best = n;
        }
    }
    return best;
}

// Source checkAttack: isTargetAttackable (3D range fp20, angle fp21) and the
// target must lie outside the invisible range (XZ), else no attack. The
// reason is logged by the runtime on every refused tick (rate-limited
// P2_CHAPPY_KING_GATE) so a zero-attack run still carries its geometry.
enum Gate { GateOk = 0, GateNoTarget, GateRange, GateAngle, GateInvisible };

inline const char* gateName(Gate g)
{
    switch (g) {
    case GateOk: return "ok";
    case GateNoTarget: return "no_target";
    case GateRange: return "range";
    case GateAngle: return "angle";
    case GateInvisible: return "invisible";
    }
    return "?";
}

inline Gate gateReason(const Vec3& actor, float heading, const Vec3* target)
{
    if (!target) return GateNoTarget;
    const float dx = target->x - actor.x, dy = target->y - actor.y, dz = target->z - actor.z;
    if (dx * dx + dy * dy + dz * dz >= AttackRange * AttackRange) return GateRange;
    if (std::fabs(angDist(actor, heading, *target)) > AttackAngleDeg * DegToRad) return GateAngle;
    return sqrXZ(*target, actor) > InvisibleRange * InvisibleRange ? GateOk : GateInvisible;
}

inline bool attackGate(const Vec3& actor, float heading, const Vec3& target)
{
    return gateReason(actor, heading, &target) == GateOk;
}

// ---- Pursuit (#884 round 2) -------------------------------------------------
// Source StateWalk::exec (kingChappyState.cpp:69-107): walkFunc (searchTarget +
// EnemyFunc::walkToTarget(mGoalPosition) + the 120-frame stall check,
// kingChappy.cpp:1585-1612), checkTurn (|angle to goal| > proper fp01 ->
// Turn, kingChappy.cpp:2505-2521), the incubation timer (ip01 -> walk home,
// Hide at home) and setNextGoal on reaching the goal (kingChappy.cpp:1103-1124).
// StateTurn::exec (kingChappyState.cpp:1800-1823) turns by turnFunc until the
// angle is under proper fp07 (with a target) or 0.5 rad. Retail values from
// KingChappy/enemyparm.txt. Times are source frames (1/30 s); the runtime
// passes dt*30, and a fractional step keeps the per-frame turn law exact at
// integer frames: remaining angle *= (1 - fp08) per frame, capped by fp28.
constexpr float TurnFactor = 0.02f;         // general fp08 rotation speed rate
constexpr float MaxTurnDeg = 30.0f;         // general fp28 max rotation per frame
constexpr float RequiredTurnDeg = 60.0f;    // proper fp01 (decomp default 20)
constexpr float TurnEndDeg = 40.0f;         // proper fp07 with a target (decomp default 10)
constexpr float TurnEndNoTargetRad = 0.5f;  // StateTurn::exec default threshold
constexpr float MoveSpeed = 45.0f;          // general fp06
constexpr float Territory = 300.0f;         // general fp09
constexpr float HomeRadius = 30.0f;         // general fp10
constexpr float ReachGoal = 20.0f;          // StateWalk isReachToGoal(20)
constexpr float StallFrames = 120.0f;       // walkFunc mWalkingTimer
constexpr float StallDistSq = 900.0f;       // walkFunc: moved < 30 in 120 frames
constexpr float SearchDelayFrames = 120.0f; // walkFunc / wallCallback mSearchDelayTimer
constexpr float IncubationFrames = 500.0f;  // proper ip01 (retail 500)
constexpr float FlickShoutRate = 0.5f;      // proper fp13: checkFlick WarCry chance below half life

inline float wrapAngle(float a)
{
    while (a > 3.14159265f) a -= 2.0f * 3.14159265f;
    while (a < -3.14159265f) a += 2.0f * 3.14159265f;
    return a;
}

// EnemyBase::turnToTarget over `frames` source frames. Returns the new heading;
// `angOut` receives the angle to `goal` BEFORE the turn (source turnFunc value).
inline float turnStep(float heading, const Vec3& actor, const Vec3& goal, float frames, float* angOut = nullptr)
{
    const float ang = angDist(actor, heading, goal);
    if (angOut) *angOut = ang;
    if (!(frames > 0.0f)) return heading;
    float step = ang * (1.0f - std::pow(1.0f - TurnFactor, frames));
    const float cap = MaxTurnDeg * DegToRad * frames;
    if (step > cap) step = cap;
    if (step < -cap) step = -cap;
    return wrapAngle(heading + step);
}

inline bool needsTurn(const Vec3& actor, float heading, const Vec3& goal)
{
    return std::fabs(angDist(actor, heading, goal)) > RequiredTurnDeg * DegToRad;
}

struct Walker {
    Vec3 home{0, 0, 0};
    Vec3 goal{0, 0, 0};           // mGoalPosition
    float searchDelay = 0.0f;     // mSearchDelayTimer (frames)
    float walkFrames = 0.0f;      // mWalkingTimer
    Vec3 stallPos{0, 0, 0};       // mPrevWalkingCheckPosition
    float noTargetFrames = 0.0f;  // StateWalk::mNoTargetTimer
    bool targetDropped = false;   // this walkTick's stall check cleared mTargetCreature
};

inline void initWalker(Walker& w, const Vec3& home)
{
    w = Walker{};
    w.home = home;
    w.goal = home;
    w.stallPos = home;
}

inline bool goalIsHome(const Walker& w) { return w.goal.x == w.home.x && w.goal.z == w.home.z; }

inline bool outOfTerritory(const Walker& w, const Vec3& pos, float scale)
{
    const float r = scale * Territory;
    return sqrXZ(w.home, pos) > r * r;
}

// searchTarget early-outs (kingChappy.cpp:1135-1145): delay timer, or the goal
// is home and the King is beyond 0.8 of its territory.
inline bool canSearch(const Walker& w, const Vec3& pos)
{
    if (w.searchDelay > 0.0f) return false;
    return !(goalIsHome(w) && outOfTerritory(w, pos, 0.8f));
}

// doSimulation decrements the delay every frame in every state.
inline void tickDelay(Walker& w, float frames)
{
    w.searchDelay -= frames;
    if (w.searchDelay < 0.0f) w.searchDelay = 0.0f;
}

// StateWalk::init: the no-target timer restarts only when a target is held.
inline void enterWalk(Walker& w, bool hasTarget)
{
    if (hasTarget) w.noTargetFrames = 0.0f;
}

// setNextGoal (kingChappy.cpp:1103-1124). r0/r1 are uniform [0,1] draws.
inline void nextGoal(Walker& w, const Vec3& pos, const Vec3* target, float r0, float r1)
{
    if (outOfTerritory(w, pos, 1.0f)) {
        w.goal = w.home;
        return;
    }
    if (target) {
        w.goal = *target;
        return;
    }
    const float rad = Territory * (0.3f + r0);
    const float a = 2.0f * 3.14159265f * r1;
    w.goal = Vec3{w.home.x + rad * std::sin(a), w.home.y, w.home.z + rad * std::cos(a)};
}

enum WalkResult { WalkOn = 0, WalkTurn, WalkHide };

// One StateWalk::exec tick (before checkFlick / checkAttack, which the caller
// evaluates first because a later source transit overrides an earlier one).
// `target` is this tick's searchTarget result. Updates `heading` (walkToTarget);
// the caller drives forward at MoveSpeed along it.
inline WalkResult walkTick(Walker& w, const Vec3& pos, float& heading, const Vec3* target, float frames, float r0,
                           float r1)
{
    w.targetDropped = false;
    if (target) w.goal = *target; // searchTarget tail (kingChappy.cpp:1181-1183)
    heading = turnStep(heading, pos, w.goal, frames);
    w.walkFrames += frames;
    if (w.walkFrames > StallFrames) {
        if (sqrXZ(pos, w.stallPos) < StallDistSq) {
            w.searchDelay = SearchDelayFrames;
            w.goal = w.home;
            target = nullptr;
            w.targetDropped = true; // mTargetCreature = nullptr: checkAttack has no target this tick
        }
        w.stallPos = pos;
        w.walkFrames = 0.0f;
    }
    const WalkResult turn = needsTurn(pos, heading, w.goal) ? WalkTurn : WalkOn;
    if (!target) w.noTargetFrames += frames;
    if (outOfTerritory(w, pos, 1.0f) || w.noTargetFrames > IncubationFrames) {
        w.goal = w.home;
        w.noTargetFrames = IncubationFrames;
        if (sqrXZ(pos, w.home) < HomeRadius * HomeRadius) {
            w.noTargetFrames = 0.0f;
            return WalkHide;
        }
    } else if (sqrXZ(pos, w.goal) < ReachGoal * ReachGoal) {
        nextGoal(w, pos, target, r0, r1);
    }
    return turn;
}

// One StateTurn::exec tick toward the target (if any) else the goal. Returns
// true when the turn is done (angle before this tick under the threshold).
inline bool turnTick(float& heading, const Vec3& pos, const Vec3& aim, bool hasTarget, float frames)
{
    float ang = 0.0f;
    heading = turnStep(heading, pos, aim, frames, &ang);
    const float thr = hasTarget ? TurnEndDeg * DegToRad : TurnEndNoTargetRad;
    return std::fabs(ang) < thr;
}

// Gate-refusal diagnostics (P2_CHAPPY_KING_GATE). Free = searchable and not
// latched to this King's body; latched Pikmin are counted apart because the
// source eat condition never takes them (they feed the flick's stuck count).
//   under_chin: free Pikmin in the search cone inside the invisible range
//   band:       free Pikmin that would pass the attack gate
//   front:      free Pikmin that some kamu slot of the 40..94 tongue window
//               actually reaches (tongueReaches), NOT merely "ahead within
//               max reach": the under-chin ground zone (local z up to 60;
//               the first reachable ground is z 65 at x +10..+30) is
//               unreachable at every frame and is excluded (round 3).
//   latched:    Pikmin latched to the body (any position)
struct Census {
    int underChin = 0;
    int band = 0;
    int front = 0;
    int latched = 0;
};

// True when any slot of any frame of the profile's window comes strictly
// within the slot radius of `q` (the eatPikmin distance test, over the whole
// window). Prefiltered by the feet plane and the maximum horizontal reach.
inline bool tongueReaches(const Profile& p, float reach, const Vec3& actor, float heading, const Vec3& q)
{
    const Vec3 l = toLocal(actor, heading, q);
    if (l.z <= 0.0f || l.x * l.x + l.z * l.z > reach * reach) return false;
    const float r = effectiveRadius(p);
    for (int f = p.firstFrame; f <= p.lastFrame; ++f) {
        for (int i = 0; i < p.slots; ++i) {
            if (distance(slotWorld(p, f, i, actor, heading), q) < r) return true;
        }
    }
    return false;
}

inline Census census(const Vec3& actor, float heading, const Candidate* piki, int count, const Profile* prof)
{
    Census c;
    const float cone = SearchAngleDeg * DegToRad;
    const float reach = prof ? maxReach(*prof) : 0.0f;
    for (int n = 0; n < count; ++n) {
        if (!piki[n].searchable) continue;
        if (piki[n].latched) {
            ++c.latched;
            continue;
        }
        const Vec3& q = piki[n].pos;
        const float ang = std::fabs(angDist(actor, heading, q));
        const float d = sqrXZ(q, actor);
        if (ang <= cone && d <= InvisibleRange * InvisibleRange) ++c.underChin;
        if (attackGate(actor, heading, q)) ++c.band;
        if (prof && tongueReaches(*prof, reach, actor, heading, q)) ++c.front;
    }
    return c;
}

// ---- Flick / shake-off (#884 round 3) ---------------------------------------
// Source Obj::checkFlick (kingChappy.cpp:2429-2470), called from StateWalk
// (kingChappyState.cpp:93) and StateTurn (:1822) only:
//   * every call, each live captain whose 3D separation is inside proper fp06
//     (80) adds 0.1 to EnemyBase::mFlickTimer;
//   * EnemyBase::addDamage adds flickSpeed (1.0 from Obj::damageCallBack,
//     kingChappy.cpp:824-848) on every damaging hit, in every state
//     (enemyBase.cpp:2762-2773; EB_FlickEnabled is set in onInit, :1074);
//   * EnemyFunc::isStartFlick(this, false) (enemyAction.cpp:1209-1240) rounds
//     the timer, truncates it to u8 and compares it with the shake-off blow
//     threshold of the stuck-Pikmin tier (mStuckPikminCount, onStickStart/End
//     enemyBase.cpp:2716-2733);
//   * below half life, proper fp13 (0.5) of the starts become WarCry.
// The timer is reset only by the shake itself (StateFlick KEYEVENT_3
// kingChappyState.cpp:914, StateWarCry KEYEVENT_4 :1658), the bomb damage
// event (StateDamage KEYEVENT_4 :1742) and doFinishStoneState
// (kingChappy.cpp:947).
// StateFlick KEYEVENT_3 (kingChappyState.cpp:867-918): InteractPress
// (general fp24) on Pikmin and captains inside the trampling disc (proper fp08
// around mFootPosition = position - 10 * facing, kingChappy.cpp:233-235, y in
// (foot.y - 5, foot.y + 25)), then flickNearbyPikmin (3D < general fp19, not
// stuck to the King), flickStickPikmin (general fp16 chance, angle
// facing + pi) and, only when no captain was trampled, flickNearbyNavi
// (3D < fp19), all with knockback fp17 and damage fp18
// (enemyAction.cpp:768-850). StateWarCry KEYEVENT_4 (:1620-1659) does the
// same three flicks without the trample.
// Retail values: output/p2play/content/KingChappy/enemyparm.txt; key frames:
// enemyanimmgr.txt (flick.bca 30:2 35:3, cry.bca 65:4).
constexpr float NaviFlickPerFrame = 0.1f; // checkFlick, per captain inside fp06
constexpr float FlickPerHit = 1.0f;       // damageCallBack addDamage(.., 1.0f)
constexpr int ShakeOffBlowA = 6;          // general ip01
constexpr int ShakeOffSticking1 = 5;      // general ip02
constexpr int ShakeOffBlowB = 12;         // general ip03
constexpr int ShakeOffSticking2 = 10;     // general ip04
constexpr int ShakeOffBlowC = 17;         // general ip05
constexpr int ShakeOffSticking3 = 20;     // general ip06
constexpr int ShakeOffBlowD = 22;         // general ip07
constexpr float ShakeChance = 1.0f;       // general fp16
constexpr float ShakeKnockback = 200.0f;  // general fp17
constexpr float ShakeDamage = 1.0f;       // general fp18
constexpr float ShakeRange = 60.0f;       // general fp19 (x mScaleModifier, 1)
constexpr float TramplingRange = 45.0f;   // proper fp08 (x mScaleModifier, 1)
constexpr float TrampleDamage = 5.0f;     // general fp24 (InteractPress damage)
constexpr float FootBack = 10.0f;         // doUpdate mFootPosition offset
constexpr float TrampleAbove = 25.0f;     // yMax = foot.y + 25
constexpr float TrampleBelow = 5.0f;      // yMin = yMax - 30
constexpr int FlickEventFrame = 35;       // flick.bca KEYEVENT_3
constexpr int CryShakeFrame = 65;         // cry.bca KEYEVENT_4

// isStartFlick threshold for a stuck count (the rounded timer must exceed it).
inline int flickThreshold(int stuck)
{
    if (stuck < ShakeOffSticking1) return ShakeOffBlowA;
    if (stuck < ShakeOffSticking2) return ShakeOffBlowB;
    if (stuck < ShakeOffSticking3) return ShakeOffBlowC;
    return ShakeOffBlowD;
}

// EnemyFunc::isStartFlick without the reset (KingChappy passes false):
// round half away from zero, (int), then u8 truncation.
inline bool isStartFlick(float timer, int stuck)
{
    const float rounded = timer >= 0.0f ? timer + 0.5f : timer - 0.5f;
    const int flickInt = (unsigned char)(int)rounded;
    return flickInt > flickThreshold(stuck);
}

// One checkFlick call spanning `frames` source frames: accrue 0.1 per frame
// per captain inside fp06 (`naviInRange`), then test the start condition.
inline bool checkFlick(float& timer, int naviInRange, int stuck, float frames)
{
    if (naviInRange > 0 && frames > 0.0f) timer += NaviFlickPerFrame * float(naviInRange) * frames;
    return isStartFlick(timer, stuck);
}

// checkFlick's captain test: 3D separation (Creature::getTargetSeparation)
// strictly inside proper fp06.
inline bool naviInInvisibleRange(const Vec3& actor, const Vec3& navi)
{
    const float dx = navi.x - actor.x, dy = navi.y - actor.y, dz = navi.z - actor.z;
    return dx * dx + dy * dy + dz * dz < InvisibleRange * InvisibleRange;
}

inline Vec3 footPosition(const Vec3& actor, float heading)
{
    return Vec3{actor.x - FootBack * std::sin(heading), actor.y, actor.z - FootBack * std::cos(heading)};
}

// StateFlick KEYEVENT_3 trample test for a Pikmin or captain position.
inline bool tramples(const Vec3& foot, const Vec3& q)
{
    const float yMax = foot.y + TrampleAbove;
    const float yMin = yMax - (TrampleAbove + TrampleBelow);
    return q.y < yMax && q.y > yMin && sqrXZ(foot, q) < TramplingRange * TramplingRange;
}

// flickNearbyPikmin / flickNearbyNavi: 3D distance strictly inside fp19.
inline bool inShakeRange(const Vec3& actor, const Vec3& q)
{
    const float dx = q.x - actor.x, dy = q.y - actor.y, dz = q.z - actor.z;
    return dx * dx + dy * dy + dz * dz < ShakeRange * ShakeRange;
}

// flickStickPikmin: angle = roundAng(getFaceDir() + pi), in [0, 2pi).
inline float flickStuckAngle(float heading)
{
    float a = heading + 3.14159265f;
    while (a >= 2.0f * 3.14159265f) a -= 2.0f * 3.14159265f;
    while (a < 0.0f) a += 2.0f * 3.14159265f;
    return a;
}

// ---- Walk / Turn transition priorities (#884 round 3) -----------------------
// Source StateWalk::exec (kingChappyState.cpp:69-107) runs, in order:
// walkFunc (search, walkToTarget, stall) + checkTurn, [Hide as a deferred
// mNextState], checkDead, checkFlick, checkAttack. checkTurn and checkFlick
// transit with mAllowAnimBlending = true, so startMotionSelf starts a blend
// (kingChappy.cpp:2528-2556; BlendAnimator::startBlend sets mIsBlendEnabled,
// sysShape.cpp:244-255) whenever the walk clip is not on its last frame, and
// every later check*(true) returns early while that blend is enabled
// (checkFlick :2435-2439, checkAttack :1784-1790). Hence, with the walk clip
// mid-loop: Turn > Flick/WarCry > Attack > Hide > keep walking. A sighting by
// itself never leaves Walk: WarCry is reached only through checkFlick (below
// half life) or checkDead. Adaptation: the rare tick on the walk clip's last
// frame (no blend, so a later transit would win) is not modelled.
enum WalkNext { NextWalk = 0, NextTurn, NextFlick, NextWarCry, NextAttack, NextHide };

inline const char* walkNextName(WalkNext n)
{
    switch (n) {
    case NextWalk: return "walk";
    case NextTurn: return "turn";
    case NextFlick: return "flick";
    case NextWarCry: return "warcry";
    case NextAttack: return "attack";
    case NextHide: return "hide";
    }
    return "?";
}

struct WalkInputs {
    WalkResult walker = WalkOn; // walkTick: WalkTurn (checkTurn), WalkHide (deferred), WalkOn
    bool flickStart = false;    // checkFlick fired (the caller skips checkFlick after WalkTurn: blend)
    bool shout = false;         // below half life and the fp13 roll: the flick becomes WarCry
    bool inRange = false;       // checkAttack gate after walkFunc (a stall drops the target)
    bool hasTarget = false;     // searchTarget found something; never a transition by itself
};

inline WalkNext walkStateStep(const WalkInputs& in)
{
    if (in.walker == WalkTurn) return NextTurn;
    if (in.flickStart) return in.shout ? NextWarCry : NextFlick;
    if (in.inRange) return NextAttack;
    if (in.walker == WalkHide) return NextHide;
    return NextWalk;
}

// Source StateTurn::exec (kingChappyState.cpp:1800-1823): turnFunc, then
// checkDead / checkFlick; the flick transit wins over the turn ending.
inline WalkNext turnStateStep(bool turnDone, bool flickStart, bool shout)
{
    if (flickStart) return shout ? NextWarCry : NextFlick;
    return turnDone ? NextWalk : NextTurn;
}

// Source KingChappy::Obj::damageCallBack (kingChappy.cpp:824-848). The King
// takes damage, and so the addDamage flickSpeed (FlickPerHit) into
// mFlickTimer, only from:
//   bittered              -> damage * 0.1 (EB_Bittered; no P1 path sets it)
//   a collision part      -> damage * 1.0 if the attacker is alive and stuck
//                            (Creature::isStickTo, to anything)
//   no collision part     -> damage * 0.2 if the attacker is alive, stands
//                            below King.y + 5 and is within 40 XZ of the
//                            King centre (strict)
// Everything else returns false: no damage, no flick.
constexpr float DamageLowHeight = 5.0f;     // creaturePos.y < 5 + mPosition.y
constexpr float DamageLowRadius = 40.0f;    // sqrDistanceXZ < SQUARE(40)
constexpr float PartlessDamageRate = 0.2f;  // addDamage(damage * 0.2f, 1.0f)
constexpr float BitteredDamageRate = 0.1f;  // addDamage(damage * 0.1f, 1.0f)

enum DamageAccept { DamageRefused = 0, DamageStuck, DamageLowPartless, DamageBittered };

struct DamageAttacker {
    bool present = false;     // InteractAttack::mOwner != nullptr
    bool hasCollPart = false; // source mCollPart != nullptr (see sourceHasCollPart)
    bool alive = false;       // Creature::isAlive
    bool stuck = false;       // Creature::isStickTo (to anything)
    Vec3 pos{0.0f, 0.0f, 0.0f};
};

// Source collision-part presence for a hit the P1 host delivers. A source
// captain punch always carries a part: NaviPunchState::hitCallback attacks
// only when collpart is non-null and builds InteractAttack(mNavi, damage,
// collpart) (R naviState.cpp:1614-1627). damageCallBack therefore always
// takes the collision-part branch for a punch and, a captain never being
// isStickTo, refuses it from any position. The P1 host punch
// (W naviState.cpp:3237) passes collPart nullptr, so a captain owner is
// mapped back to "has a part"; every other attacker keeps the host part.
inline bool sourceHasCollPart(bool hostHasPart, bool ownerIsNavi)
{
    return hostHasPart || ownerIsNavi;
}

inline DamageAccept damageAccept(const Vec3& king, const DamageAttacker& a, bool bittered)
{
    if (bittered) return DamageBittered;
    // The source dereferences the attacker unconditionally; an ownerless hit
    // (no P1 attacker reaches the King this way) is refused here.
    if (!a.present || !a.alive) return DamageRefused;
    if (a.hasCollPart) return a.stuck ? DamageStuck : DamageRefused;
    if (!(a.pos.y < DamageLowHeight + king.y)) return DamageRefused;
    const float dx = a.pos.x - king.x, dz = a.pos.z - king.z;
    return dx * dx + dz * dz < DamageLowRadius * DamageLowRadius ? DamageLowPartless : DamageRefused;
}

inline float damageRate(DamageAccept d)
{
    switch (d) {
    case DamageStuck: return 1.0f;
    case DamageLowPartless: return PartlessDamageRate;
    case DamageBittered: return BitteredDamageRate;
    default: return 0.0f;
    }
}
} // namespace king

} // namespace p2chappymouth

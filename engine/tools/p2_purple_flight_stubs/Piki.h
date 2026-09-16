#pragma once
#include <cmath>
#include <cstdint>

constexpr float PI=3.14159265358979323846f;
inline float roundAng(float value){return value;}
enum { CF_IgnoreGravity=1, CF_UsePriorityFaceDir=2 };
struct Vector3f {
    float x=0,y=0,z=0;
    Vector3f()=default; Vector3f(float a,float b,float c):x(a),y(b),z(c){}
    void set(float a,float b,float c){x=a;y=b;z=c;}
    void set(float value){x=y=z=value;}
    float length()const{return std::sqrt(x*x+y*y+z*z);}
    Vector3f operator-(const Vector3f& rhs)const{return {x-rhs.x,y-rhs.y,z-rhs.z};}
};
struct SRT { Vector3f t; };
class Piki {
public:
    bool alive=true,purple=true;unsigned flags=0;Vector3f mVelocity,mTargetVelocity;SRT mSRT;float mFaceDirection=0;
    bool isAlive()const{return alive;}
    bool isCreatureFlag(int flag)const{return (flags&unsigned(flag))!=0;}
    void setCreatureFlag(int flag){flags|=unsigned(flag);}
    void resetCreatureFlag(int flag){flags&=~unsigned(flag);}
};

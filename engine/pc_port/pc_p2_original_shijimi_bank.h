#pragma once
#include <memory>
#include <string>
#include <vector>
class Creature;class Shape;struct Matrix4f;
namespace p2original { namespace shijimi {
// Genuine source rig/animation backend. Bodies own their private flattened
// geometry; mechanical joint0 and keys are independent of render visibility.
class SourceBank {
public:
 SourceBank();~SourceBank();
 bool prepare(Shape*&,std::string&);
 bool motion(const Creature*,unsigned motion,float sourceFrame,Shape&,std::string&);
 bool advance(const Creature*,Shape&,float seconds,std::vector<int>& keys,std::string&);
 bool joint0(const Creature*,const Matrix4f& root,Matrix4f&,std::string&)const;
 bool capture(const Creature*,std::string& bytes,std::string&)const;
 bool validate(const std::string& bytes,std::string&)const;
 bool restore(const Creature*,Shape&,const std::string& bytes,std::string&);
 void forget(const Creature*);
 const std::string& fingerprint()const;
private:
 struct Impl;std::unique_ptr<Impl> m;
};
} }

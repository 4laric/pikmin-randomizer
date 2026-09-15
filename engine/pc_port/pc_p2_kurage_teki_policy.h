#pragma once
#include <istream>
namespace p2kurage { struct Binding { unsigned generator; int type; }; inline bool read(std::istream& in, Binding& out){std::string magic,tail;int count;if(!(in>>magic>>count)||magic!="P2_KURAGE_TEKI_1"||count!=1)return false;if(!(in>>out.generator>>out.type)||out.generator==0||out.type!=0)return false;return !(in>>tail);} }

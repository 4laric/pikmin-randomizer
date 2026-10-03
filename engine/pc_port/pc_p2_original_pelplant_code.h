#pragma once
#include <array>
namespace p2original { namespace pelplant {
// Native ID32's string view follows host byte order. Retail source semantics
// consume four ordered bytes; decode the numeric ID only at this boundary.
inline std::array<char,5> sourceCode(unsigned code){
 return {{char((code>>24)&255),char((code>>16)&255),char((code>>8)&255),char(code&255),0}};
}
} }

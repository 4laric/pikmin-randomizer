#include "pc_p2_kurage_teki_policy.h"
#include <sstream>
int main(){p2kurage::Binding b{};std::istringstream ok("P2_KURAGE_TEKI_1 1 7 0");if(!p2kurage::read(ok,b)||b.generator!=7)return 1;for(const char* s:{"P2_KURAGE_TEKI_1 2 7 0","P2_KURAGE_TEKI_1 1 7 3","bad"}){std::istringstream x(s);if(p2kurage::read(x,b))return 2;}return 0;}

#ifndef PC_P2_UJI_ANIMATION_H
#define PC_P2_UJI_ANIMATION_H
#include "pc_p2_animation.h"
namespace p2uji {
inline bool parse(std::istream& input,std::vector<p2animation::Clip> (&banks)[2]) {
    std::string word;if(!(input>>word)||word!="P2_UJI_ANIMATION_1")return false;
    std::vector<p2animation::Clip> parsed[2];
    for(int kind=0;kind<2;++kind){
        if(!(input>>word)||word!=(kind?"UjiB":"UjiA"))return false;
        std::vector<std::string> names={"dead","dead_p","appear","dive","move","attack1"};
        if(kind){names.push_back("attack2");names.push_back("eat");}names.push_back("type5");
        for(const auto& name:names){
            p2animation::Clip clip;
            if(!(input>>clip.name>>clip.count>>clip.duration)||clip.name!=name||clip.count<1||clip.count>12||clip.duration<1||clip.duration>10000)return false;
            for(int i=0;i<clip.count;++i){int frame;if(!(input>>frame)||frame<0||frame>=clip.duration||(i&&frame<=clip.frames.back()))return false;clip.frames.push_back(frame);}
            if(clip.frames.front()!=0||clip.frames.back()!=clip.duration-1)return false;
            parsed[kind].push_back(clip);
        }
    }
    if(input>>word)return false;
    banks[0]=parsed[0];banks[1]=parsed[1];return true;
}
}
#endif

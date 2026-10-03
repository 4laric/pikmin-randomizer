#include "pc_p2_original_session.h"
#include "pc_p2_original_treasure_input.h"
#include <filesystem>
#include <iostream>
// Read-only literal metadata verification. No bootstrap, actor/resource
// admission, state adoption, card creation or gameplay qualification.
int main(int argc,char** argv) {
    if((argc!=3&&argc!=4)||!p2treasurestate::digest(argv[2])
       ||(argc==4&&!p2treasurestate::digest(argv[3])))return 2;
    const auto directory=std::filesystem::canonical(argv[1]);
    std::filesystem::current_path(directory);
    p2originalsession::Bundle bundle;bundle.campaign=argv[2];
    for(const auto& file:std::filesystem::recursive_directory_iterator(".")) {
        if(!file.is_regular_file())continue;
        const auto role=file.path().lexically_relative(".").generic_string();std::string bytes;
        if(!p2originalsession::path(role))continue;
        if(!p2treasureplacements::bounded(role,128*1024*1024,bytes))return 3;
        bundle.files[role]=p2treasureplacements::hash(bytes);
    }
    std::string error;
    if(!p2originalsession::verify(bundle,error)){std::cerr<<error<<'\n';return 4;}
    if(argc==4) {
        p2treasure::Catalog catalog;
        if(!p2originalsession::treasureInput(bundle,argv[3],catalog,error)){std::cerr<<error<<'\n';return 5;}
    }
    std::cout<<"PASS actual literal metadata campaign="<<bundle.campaign
             <<" files="<<bundle.files.size()<<" treasure_input="<<(argc==4?argv[3]:"none")
             <<" actor_admission=0 gameplay=0\n";
}

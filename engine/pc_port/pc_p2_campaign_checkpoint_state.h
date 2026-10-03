#pragma once
#include "pc_p2_original_progress.h"
#include "pc_p2_original_lifecycle.h"
#include "pc_p2_original_calendar_state.h"
#include "pc_p2_campaign_treasure_state.h"
#include <istream>
#include <ostream>
// Coherent scalar state inside the selected native-card authentication envelope.
// These codecs never reconstruct actors or authorize an unverified source.
struct P2CampaignCheckpointState {
    bool present=false;
    std::string original,progress,context,frontier,calendar,treasure;
    static constexpr std::size_t MaxFrontier=105+20*65536;
    static bool fingerprint(const std::string& s){return p2treasurestate::digest(s);}
    static std::string hex(const std::string& bytes){
        static const char* digits="0123456789abcdef";std::string out;out.reserve(bytes.size()*2);
        for(unsigned char c:bytes){out+=digits[c>>4];out+=digits[c&15];}return out;
    }
    static bool unhex(const std::string& wire,std::size_t minimum,std::size_t maximum,std::string& out){
        if(wire.size()%2||wire.size()<minimum*2||wire.size()>maximum*2
            ||wire.find_first_not_of("0123456789abcdef")!=std::string::npos)return false;
        auto digit=[](char c){return c<='9'?c-'0':c-'a'+10;};
        std::string bytes;bytes.reserve(wire.size()/2);
        for(std::size_t i=0;i<wire.size();i+=2)bytes+=char((digit(wire[i])<<4)|digit(wire[i+1]));
        out.swap(bytes);return true;
    }
    bool originalValid() const{
        if(original.empty())return progress.empty()&&context.empty()&&frontier.empty()&&calendar.empty();
        if(!fingerprint(original)||progress.size()!=104||context.size()!=106
            ||frontier.size()<105||frontier.size()>MaxFrontier||calendar.size()!=p2original::CalendarLedger::Bytes)return false;
        p2original::Progress staged; p2original::IncarnationFrontier identities;p2original::CalendarLedger loaded;std::string reason;
        return staged.decode(progress,original,reason)&&staged.decodeContext(context,original,reason)
            &&identities.decode(original,frontier,reason)&&loaded.decode(original,staged.context().day,calendar,reason);
    }
    bool valid(const p2treasure::Catalog* catalog=nullptr,const std::string& expectedTreasure={})const{
        if(!present)return original.empty()&&progress.empty()&&context.empty()&&frontier.empty()&&calendar.empty()&&treasure.empty();
        if((original.empty()&&treasure.empty())||!originalValid())return false;
        if(treasure.empty())return expectedTreasure.empty();
        p2treasurestate::Snapshot staged;
        return catalog&&p2treasurestate::decode(treasure,*catalog,expectedTreasure,staged);
    }
    bool matches(const std::string& campaign,const std::string& source,const p2treasure::Catalog* catalog=nullptr)const{
        return original==campaign&&treasure.empty()==source.empty()&&valid(catalog,source)
            &&present==(!campaign.empty()||!source.empty());
    }
    bool read(std::istream& in,const p2treasure::Catalog* catalog=nullptr,const std::string& source={}){
        P2CampaignCheckpointState next;std::string tag,version,wire;int originalFlag=-1,treasureFlag=-1;
        if(!(in>>tag>>version>>originalFlag)||tag!="CAMPAIGN_STATE"||(version!="1"&&version!="2")
            ||(originalFlag!=0&&originalFlag!=1))return false;
        if(originalFlag){
            if(version!="2")return false; // Prior source cards lack real calendar ownership.
            if(!(in>>next.original>>wire)||!unhex(wire,104,104,next.progress)
                ||!(in>>wire)||!unhex(wire,106,106,next.context)
                ||!(in>>wire)||!unhex(wire,105,MaxFrontier,next.frontier)
                ||!(in>>wire)||!unhex(wire,p2original::CalendarLedger::Bytes,p2original::CalendarLedger::Bytes,next.calendar))return false;
        }
        if(!(in>>treasureFlag)||(treasureFlag!=0&&treasureFlag!=1))return false;
        if(treasureFlag&&(!(in>>wire)||!unhex(wire,p2treasurestate::MaxRecordBytes,p2treasurestate::MaxRecordBytes,next.treasure)))return false;
        next.present=true;if(!next.valid(catalog,source))return false;
        *this=std::move(next);return true;
    }
    void write(std::ostream& out)const{
        if(!present)return;
        out<<" CAMPAIGN_STATE 2 "<<int(!original.empty());
        if(!original.empty())out<<' '<<original<<' '<<hex(progress)<<' '<<hex(context)<<' '<<hex(frontier)<<' '<<hex(calendar);
        out<<' '<<int(!treasure.empty());if(!treasure.empty())out<<' '<<hex(treasure);
    }
};

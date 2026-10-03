#include "pc_p2_original_gen_object.h"
#include "pc_p2_original_group_engine.h"
#include "Stream.h"
#include <cstdio>
#include <cstdlib>
namespace {
constexpr unsigned adapterVersion=0x4f473032u; // OG02, distinct from species version.
[[noreturn]] void failure(const std::string& e){std::fprintf(stderr,"P2_ORIGINAL_GEN_OBJECT_FAIL %s\n",e.c_str());std::abort();}
GenObject* makeOriginal(){return new GenObjectOriginalEnemy;}
bool validate(const p2original::GeneratorState& state,std::string& e){
 const auto& actors=p2original::originalActors();const auto* row=actors.find(state.uid);std::string checked;
 if(!row||state.count!=row->enemy.count){e="original object UID/count not in admitted catalog";return false;}
 if(row->sourceForm!=p2original::SourceForm::SurfaceGenEnemy){e="surface GenEnemy object cannot consume cave TekiInfo";return false;}
 return p2original::encodeOriginalState(actors.fingerprint(),state,checked,e);
}
}
GenObjectOriginalEnemy::GenObjectOriginalEnemy():GenObject(0x70326f67u,"original P2 enemy group"){}
void pc_p2_original_gen_object_register(){
 auto* factory=GenObjectFactory::factory;
 if(!factory)failure("native generator factory absent");
 for(int i=0;i<factory->mSpawnerCount;++i)if(factory->mSpawnerInfo[i].mID==0x70326f67u)return;
 if(factory->mSpawnerCount>=factory->mMaxSpawners)failure("original generator factory capacity exhausted");
 factory->registerMember(0x70326f67u,&makeOriginal,"original P2 enemy group",adapterVersion);
}
void GenObjectOriginalEnemy::doRead(RandomAccessStream& input){
 if(mVersion!=adapterVersion)failure("original generator adapter version mismatch");
 if(Generator::ramMode)return; // OGC2 follows in the actual RAM hook.
 p2original::GeneratorState next;next.uid=unsigned(input.readInt());
 const auto* row=p2original::originalActors().find(next.uid);
 if(!row)failure("original disc object has unknown UID");
 next.count=row->enemy.count;next.reserved=unsigned(input.readInt());
 next.resurrectionDays=input.readInt();next.dayLimit=input.readInt();
 std::string e;if(!validate(next,e))failure(e);mState=next;
}
void GenObjectOriginalEnemy::doWrite(RandomAccessStream& output){
 if(Generator::ramMode)return;
 std::string e;if(!validate(mState,e))failure(e);
 output.writeInt(int(mState.uid));output.writeInt(int(mState.reserved));
 output.writeInt(mState.resurrectionDays);output.writeInt(mState.dayLimit);
}
void GenObjectOriginalEnemy::ramLoadParameters(RandomAccessStream& input){
 if(input.getPending()<132)failure("truncated original native OGC2 object");
 std::string bytes(132,'\0');for(char& byte:bytes)byte=char(input.readByte());
 unsigned uid=0;for(unsigned i=0;i<4;++i)uid|=unsigned(static_cast<unsigned char>(bytes[68+i]))<<(8*i);
 const auto* row=p2original::originalActors().find(uid);
 if(!row)failure("cached original member UID absent from current source authority");
 p2original::GeneratorState next;std::string e;
 if(!p2original::decodeOriginalState(p2original::originalActors().fingerprint(),uid,row->enemy.count,bytes,next,e))failure(e);
 mState=next;mOwner=nullptr;
}
void GenObjectOriginalEnemy::ramSaveParameters(RandomAccessStream& output){
 p2original::GeneratorState state;unsigned alive=0;std::string bytes,e;
 if(!mOwner||!pc_p2_original_groups().state(mOwner,state,alive)||state.uid!=mState.uid)failure("original cache writer lost live generator ownership");
 if(!pc_p2_original_groups().cache(mOwner,p2original::originalActors().fingerprint(),bytes,e))failure(e);
 if(output.getPending()<int(bytes.size()))failure("native generator cache capacity exhausted before OGC2 object");
 for(unsigned char byte:bytes)output.writeByte(byte);
}
Creature* GenObjectOriginalEnemy::birth(BirthInfo&){failure("uninstalled original generator attempted P1 birth fallback");}
bool pc_p2_original_gen_object_collect(Generator* generator,const p2original::GeneratorState& literal,p2original::GroupBinding& out,std::string& e){
 auto* object=generator?dynamic_cast<GenObjectOriginalEnemy*>(generator->mGenObject):nullptr;
 if(!object){e="native generator is not an original enemy object";return false;}
 if(!validate(literal,e)||!validate(object->mState,e))return false;
 const auto& actual=object->mState;
 if(literal.uid!=actual.uid||literal.count!=actual.count||literal.reserved!=actual.reserved||literal.resurrectionDays!=actual.resurrectionDays||literal.dayLimit!=actual.dayLimit
    ||literal.epoch||literal.activation||literal.deathCount||literal.dayNum||(object->mOwner&&object->mOwner!=generator)){
  e="original native object/source metadata or owner mismatch";return false;
 }
 p2original::GroupBinding next;next.generator=generator;next.state=actual;
 // P1 cache short-position fields are compatibility observations. Original
 // common placement always uses the immutable catalog's authored floats.
 generator->_70=actual.uid;generator->mCarryOverFlags=actual.reserved;
 generator->mRespawnInterval=actual.resurrectionDays;generator->mDayLimit=actual.dayLimit;
 object->mOwner=generator;out=next;e.clear();return true;
}

// Codec3 independent golden/layout/reassembly checks (#1148); oracle remains active with NDEBUG.
#include "netplay/pc_netplay_randstate.h"
#include "netplay/pc_netplay_gekko_input.h"
#include <cstdio>
#include <cstring>
#include <initializer_list>
using namespace pc_randstate;
int failures=0;
#define CHECK(x) do {if(!(x)){std::printf("FAIL %d: %s\n",__LINE__,#x);++failures;}} while(0)
const uint8_t golden[kStateBytes]={0x03,0x01,0xff,0x03,0x00,0x02,0x09,0x00,0x01,0x19,0xa5,0x03,0x01,0x07,0x01,0x00,0x40,0x30,0x20,0x10,0x00,0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x80,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x80,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x80,0x00,0x01,0x02,0x00,0x01,0x02,0x00,0x01,0x02,0x00,0x01,0x02,0x01,0x02,0x00,0x00,0x00,0x01,0x01,0x01,0x02,0x01,0x03,0x01,0x04,0x01,0x05,0x01,0x06,0x01,0x07,0x01,0x08,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x09,0x00,0x00,0x00,0x05,0x26,0xa5,0x45}; // independently packed by Python struct + zlib
void repair(uint8_t* p){uint32_t crc=crc32(p,kPayloadBytes);for(int i=0;i<4;++i)p[164+i]=uint8_t(crc>>(8*i));}
void feed(Reassembler& r,const uint8_t* wire,uint32_t start){for(uint8_t i=0;i<kFragCount;++i)r.feed(true,frag_seq_make(i),wire+4*i,i+1==kFragCount,start+i);}

// Explicit regression cases carried forward from codec2 sections 5..10.
void reassembly_regressions() {
 PcRandState one;one.gen=1;one.repairs=1;
 PcRandState two=one;two.gen=2;two.repairs=2;
 uint8_t a[kStateBytes],b[kStateBytes];encode(one,a);encode(two,b);
 PcRandState got;
 // Fragment zero is the generation boundary; remaining fragments can arrive
 // reordered. LAST is advisory even when absent or spuriously early.
 for(bool earlyLast : {false,true}) {
  Reassembler r;r.feed(true,0,a,earlyLast,1);
  for(int i=41;i>=1;--i)r.feed(true,frag_seq_make(uint8_t(i)),a+4*i,false,42-uint32_t(i));
  CHECK(r.has_pending()&&r.pending_gen()==1&&r.pending_frame()==64);
  CHECK(r.take_pending(got)&&payload_equal(got,one));
 }
 Reassembler r;
 r.feed(true,0,a,false,1);r.feed(false,1,a+4,false,2);r.feed(true,1,nullptr,false,2);
 r.feed(true,64,a+4,true,2);CHECK(!r.has_pending());
 // Interrupted generation never borrows a prefix from another generation.
 for(uint8_t i=1;i<12;++i)r.feed(true,i,a+4*i,false,i+1);
 feed(r,b,20);CHECK(r.has_pending()&&r.pending_gen()==2);
 CHECK(r.take_pending(got)&&got.repairs==2&&payload_equal(got,two));
 r.mark_applied(2);feed(r,a,100);CHECK(!r.has_pending());
 // Later generations use completion+1; first generations floor at64, or
 // retain completion+1 when delivery finishes after that minimum.
 r.reset();feed(r,a,70);CHECK(r.pending_frame()==112);
 CHECK(r.take_pending(got));r.mark_applied(got.gen);
 feed(r,b,120);CHECK(r.pending_frame()==162);
 // Preserve newest pending content and its original apply frame across a
 // duplicate or an older complete transfer before it is consumed.
 const uint32_t arm=r.pending_frame();feed(r,b,200);
 CHECK(r.pending_gen()==2&&r.pending_frame()==arm);
 feed(r,a,300);CHECK(r.pending_gen()==2&&r.pending_frame()==arm);
 PcRandState three=two;three.gen=3;three.repairs=3;uint8_t c[kStateBytes];encode(three,c);
 feed(r,c,400);CHECK(r.pending_gen()==3&&r.pending_frame()==442);
 CHECK(!r.discard_pending_upto(2));CHECK(r.discard_pending_upto(3));
 r.mark_applied(3);feed(r,b,500);CHECK(!r.has_pending());
 // Reset clears partial slots, pending metadata and the applied watermark.
 feed(r,c,600);r.feed(true,0,a,false,700);r.feed(true,1,a+4,false,701);r.reset();
 CHECK(!r.has_pending()&&r.pending_gen()==0&&r.pending_frame()==0&&r.applied_gen()==0);
 CHECK(!r.take_pending(got));
 for(uint8_t i=2;i<42;++i)r.feed(true,i,a+4*i,false,702+i);
 CHECK(!r.has_pending());feed(r,a,800);CHECK(r.pending_gen()==1);
 // CRC failure clears the complete buffer and permits the next good transfer.
 r.reset();uint8_t bad[kStateBytes];std::memcpy(bad,a,sizeof(bad));bad[90]^=1;
 feed(r,bad,1);CHECK(!r.has_pending());feed(r,b,60);CHECK(r.pending_gen()==2);
 // Generation IDs are strictly increasing uint32 values within one session.
 // Wrap to1 is refused after UINT32_MAX; only explicit session reset restarts.
 r.reset();r.mark_applied(UINT32_MAX);feed(r,a,1);CHECK(!r.has_pending());
 r.reset();feed(r,a,1);CHECK(r.pending_gen()==1);
 PcNetplayInput input;input.buttons=0x1234;input.flags=pc_netplay_gekko::kFlagsRandChunk|pc_netplay_gekko::kFlagsHold;
 input.fragSeq=frag_seq_make(41);input.fragData[0]=0xde;input.fragData[3]=0xef;
 uint8_t iw[16];CHECK(pc_netplay_input_encode(input,iw)==16);
 CHECK(iw[10]==5&&iw[11]==41&&iw[12]==0xde&&iw[15]==0xef);
 PcNetplayInput decoded;CHECK(pc_netplay_input_decode(iw,16,decoded));
 CHECK(decoded.buttons==0x1234&&decoded.flags==5&&decoded.fragSeq==41&&decoded.fragData[3]==0xef);
 PcNetplayInput idle;pc_netplay_input_encode(idle,iw);for(int i=10;i<16;++i)CHECK(iw[i]==0);
}

int main(){
 reassembly_regressions();
 CHECK(kStateBytes==168 && kFragCount==42 && pc_netplay_gekko::kInputBytes==16);
 PcRandState st;CHECK(decode(golden,sizeof(golden),st));CHECK(st.deathLinks==0x10203040 && st.benefits[8]==264);
 for(unsigned i : {191u,192u,255u,256u,329u,511u})CHECK(st.checks[i/8]&(1u<<(i%8)));
 uint8_t wire[kStateBytes];CHECK(encode(st,wire)==168);CHECK(!std::memcmp(wire,golden,168));
 CHECK(encode(st,nullptr)==0);CHECK(!decode(nullptr,168,st));
 PcRandState variations=st;variations.repairs--;CHECK(!payload_equal(st,variations));
 variations=st;variations.benefits[8]++;CHECK(!payload_equal(st,variations));
 variations=st;variations.checks[511/8]^=1u<<(511%8);CHECK(!payload_equal(st,variations));
 variations=st;variations.crc++;CHECK(payload_equal(st,variations));
 variations=st;std::memset(variations.checks,255,kCheckBytes);uint8_t full[kStateBytes];encode(variations,full);PcRandState round;
 CHECK(decode(full,kStateBytes,round)&&round.checks[63]==255);
 full[167]^=1;CHECK(!decode(full,kStateBytes,round));
 PcRandState changed=st;changed.gen=55;CHECK(payload_equal(st,changed));changed.maturity[2]=1;CHECK(!payload_equal(st,changed));
 for(unsigned off : {0u,1u,2u,4u,6u,7u,8u,15u,103u,158u,159u,160u}){
  uint8_t bad[168];std::memcpy(bad,golden,168);
  if(off==0)bad[off]=2;else if(off==1)bad[off]=0;else if(off==2)bad[3]|=128;
  else if(off==4){bad[4]=1;bad[5]=2;}else if(off==6)bad[off]=10;else if(off==8)bad[off]=2;
  else if(off==160)std::memset(bad+160,0,4);else bad[off]=1;
  repair(bad);PcRandState sentinel;sentinel.gen=123;CHECK(!decode(bad,168,sentinel));CHECK(sentinel.gen==123);
 }
 PcRandState sentinel;sentinel.gen=123;CHECK(!decode(wire,167,sentinel));CHECK(!decode(wire,169,sentinel));
 wire[24]^=1;CHECK(!decode(wire,168,sentinel));std::memcpy(wire,golden,168);
 for(uint8_t i=0;i<42;++i)CHECK(frag_seq_index(frag_seq_make(i))==i && frag_seq_stream(frag_seq_make(i))==0);
 for(unsigned delay=1;delay<=8;++delay){
  Reassembler a,b;feed(a,wire,delay);feed(b,wire,delay);
  CHECK(a.has_pending()&&b.has_pending()&&a.pending_frame()==64&&b.pending_frame()==64);
  PcRandState x,y;CHECK(a.take_pending(x)&&b.take_pending(y)&&payload_equal(x,y));a.mark_applied(9);b.mark_applied(9);
  feed(a,wire,100);CHECK(!a.has_pending());
 }
 Reassembler r;r.feed(true,42,wire,false,1);r.feed(true,64,wire,false,1);CHECK(!r.has_pending());
 for(uint8_t i=0;i<41;++i){r.feed(true,i,wire+4*i,false,i);r.feed(true,i,wire+4*i,false,i);}CHECK(!r.has_pending());
 r.feed(true,41,wire+164,true,41);CHECK(r.has_pending());CHECK(!r.discard_pending_upto(8));CHECK(r.discard_pending_upto(9));CHECK(!r.has_pending());
 PcRandState tl;tl.mode=2;tl.schema=1;tl.checkCount=330;tl.gen=1;tl.repairs=30;tl.thelynkParts=(1u<<30)-1;tl.thelynkBonuses[17]=330;
 encode(tl,wire);CHECK(decode(wire,168,st));CHECK(st.thelynkBonuses[17]==330&&st.repairs==30);
 tl.checks[329/8]|=1u<<(329%8);encode(tl,wire);CHECK(decode(wire,168,st));
 tl.checks[330/8]|=1u<<(330%8);encode(tl,wire);CHECK(!decode(wire,168,st));
 std::printf("codec3 failures=%d\n",failures);return failures?1:0;
}

/** Bounded C++26 runtime transport for the complete tactical intent surface. */
#include "tactical_intent.h"
#include <array>
#include <cstddef>
#include <cstdint>
#include <mutex>
namespace ufo { namespace presentation { namespace tactical_intent { namespace {
constexpr std::size_t CAP=256,RCAP=256;
template<typename T,std::size_t N> class Ring{public:bool push(const T&v){if(c==N)return false;a[w]=v;w=(w+1)%N;++c;return true;}bool pop(T&v){if(!c)return false;v=a[r];r=(r+1)%N;--c;return true;}bool full()const{return c==N;}void clear(){r=w=c=0;}private:std::array<T,N>a{};std::size_t r=0,w=0,c=0;};
std::mutex m;Ring<TacticalIntent,CAP>q;Ring<TacticalIntentResult,RCAP>rq;uint64_t seq=1;
TacticalIntent make(TacticalIntentKind k, canonical::EntityId e=canonical::EntityId()){TacticalIntent v={};v.kind=k;v.entity=e;return v;}
uint64_t alloc(){const uint64_t s=seq++;if(seq==0)seq=1;return s;}
TacticalIntentSubmission submit(TacticalIntent v){std::lock_guard<std::mutex>l(m);TacticalIntentSubmission s={0,false};if(q.full())return s;v.sequence=alloc();if(!q.push(v))return s;s.sequence=v.sequence;s.accepted=true;return s;}
}
TacticalIntentSubmission submitSetReactionFire(canonical::EntityId e,bool b){auto v=make(TacticalIntentKind::SetReactionFire,e);v.value0=b?1:0;return submit(v);}
TacticalIntentSubmission submitSetReservedTimeUnits(canonical::EntityId e,int32_t a,int32_t b){auto v=make(TacticalIntentKind::SetReservedTimeUnits,e);v.value0=a;v.value1=b;return submit(v);}
TacticalIntentSubmission submitAbortMission(){return submit(make(TacticalIntentKind::AbortMission));}
TacticalIntentSubmission submitClearShotReservation(canonical::EntityId e,int32_t c){auto v=make(TacticalIntentKind::ClearShotReservation,e);v.value0=c;return submit(v);}
TacticalIntentSubmission submitEndTurn(){return submit(make(TacticalIntentKind::EndTurn));}
TacticalIntentSubmission submitMoveActor(canonical::EntityId e,int32_t x,int32_t y,int32_t z){auto v=make(TacticalIntentKind::MoveActor,e);v.value0=x;v.value1=y;v.value2=z;return submit(v);}
TacticalIntentSubmission submitReload(canonical::EntityId e,int32_t c){auto v=make(TacticalIntentKind::Reload,e);v.value0=c;return submit(v);}
TacticalIntentSubmission submitSelectReactionFireMode(canonical::EntityId e,int32_t h,int32_t f,int32_t w){auto v=make(TacticalIntentKind::SelectReactionFireMode,e);v.value0=h;v.value1=f;v.value2=w;return submit(v);}
TacticalIntentSubmission submitSetCrouchState(canonical::EntityId e,bool b){auto v=make(TacticalIntentKind::SetCrouchState,e);v.value0=b?1:0;return submit(v);}
TacticalIntentSubmission submitSetShotReservation(canonical::EntityId e,int32_t s,int32_t c){auto v=make(TacticalIntentKind::SetShotReservation,e);v.value0=s;v.value1=c;return submit(v);}
TacticalIntentSubmission submitShoot(canonical::EntityId e,int32_t x,int32_t y,int32_t z,int32_t t,int32_t f,int32_t a){auto v=make(TacticalIntentKind::Shoot,e);v.value0=x;v.value1=y;v.value2=z;v.value3=t;v.value4=f;v.value5=a;return submit(v);}
TacticalIntentSubmission submitUse(canonical::EntityId e,canonical::EntityId t){auto v=make(TacticalIntentKind::Use,e);v.targetEntity=t;return submit(v);}
TacticalIntentSubmission submitUseHeadgear(canonical::EntityId e){return submit(make(TacticalIntentKind::UseHeadgear,e));}
TacticalIntentSubmission submitTurnActor(canonical::EntityId e,int32_t d){auto v=make(TacticalIntentKind::TurnActor,e);v.value0=d;return submit(v);}
TacticalIntentSubmission submitInventoryMove(canonical::EntityId e,int32_t fc,int32_t fx,int32_t fy,int32_t tc,int32_t tx,int32_t ty){auto v=make(TacticalIntentKind::InventoryMove,e);v.value0=fc;v.value1=fx;v.value2=fy;v.value3=tc;v.value4=tx;v.value5=ty;return submit(v);}
bool pollTacticalIntentResult(TacticalIntentResult*out){if(!out)return false;std::lock_guard<std::mutex>l(m);return rq.pop(*out);}
namespace legacy{bool tryPopTacticalIntent(TacticalIntent*out){if(!out)return false;std::lock_guard<std::mutex>l(m);return q.pop(*out);}void publishTacticalIntentResult(const TacticalIntentResult&v){std::lock_guard<std::mutex>l(m);if(rq.full()){TacticalIntentResult d={};rq.pop(d);}rq.push(v);}void resetTacticalIntentRuntime(){std::lock_guard<std::mutex>l(m);q.clear();rq.clear();}}
} } }

#include "../../src/client/presentation/strategic_intent.h"
#include "../../src/client/presentation/tactical_intent.h"
#include <cassert>
#include <cstring>
using namespace ufo;
int main(){
    presentation::intent::legacy::resetStrategicIntentRuntime();
    presentation::tactical_intent::legacy::resetTacticalIntentRuntime();
    const auto s1=presentation::intent::submitSetCampaignTimeLapse(3);
    const auto s2=presentation::intent::submitRenameBase(canonical::BaseId(2),"A very ordinary base name");
    assert(s1.accepted && s2.accepted && s2.sequence>s1.sequence);
    presentation::StrategicIntent si={};
    assert(presentation::intent::legacy::tryPopStrategicIntent(&si));
    assert(si.kind==presentation::StrategicIntentKind::SetCampaignTimeLapse && si.value==3 && si.value0==3);
    assert(presentation::intent::legacy::tryPopStrategicIntent(&si));
    assert(si.kind==presentation::StrategicIntentKind::RenameBase && si.base.value==2);
    assert(std::strcmp(si.text,"A very ordinary base name")==0);
    const auto t1=presentation::tactical_intent::submitMoveActor(canonical::EntityId(9),10,11,2);
    const auto t2=presentation::tactical_intent::submitInventoryMove(canonical::EntityId(9),1,2,3,4,5,6);
    assert(t1.accepted && t2.accepted && t2.sequence>t1.sequence);
    presentation::TacticalIntent ti={};
    assert(presentation::tactical_intent::legacy::tryPopTacticalIntent(&ti));
    assert(ti.kind==presentation::TacticalIntentKind::MoveActor && ti.value0==10 && ti.value2==2);
    assert(presentation::tactical_intent::legacy::tryPopTacticalIntent(&ti));
    assert(ti.kind==presentation::TacticalIntentKind::InventoryMove && ti.value5==6);
    return 0;
}

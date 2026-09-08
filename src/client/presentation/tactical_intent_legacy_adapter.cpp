/**
 * @file
 * @brief Client-Main adapter from typed tactical intents to existing server request protocol.
 */
#include "../client.h"
#include "../battlescape/cl_actor.h"
#include "../battlescape/cl_battlescape.h"
#include "../battlescape/cl_localentity.h"
#include "tactical_intent.h"
#include "tactical_intent_legacy_adapter.h"
#include <cstdint>

namespace ufo { namespace presentation { namespace legacy { namespace {
const unsigned int MAX_TACTICAL_INTENTS_PER_FRAME = 64;
le_t* resolveLocalEntity(canonical::EntityId id) {
    if(!id.isValid() || id.value>=MAX_EDICTS) return nullptr;
    le_t* le=&cl.LEs[id.value];
    if(!le->inuse || le->entnum!=static_cast<int>(id.value)) return nullptr;
    return le;
}
le_t* resolveOwnedTacticalActor(canonical::EntityId id) {
    le_t* a=resolveLocalEntity(id); if(!a || !LE_IsActor(a)) return nullptr;
    if(a->team!=cls.team || a->pnum!=cl.pnum) return nullptr;
    return a;
}
bool tacticalTransportReady(){return cls.state==ca_active && cls.netStream!=nullptr && CL_BattlescapeRunning();}
bool gridCoord(int32_t v){return v>=0 && v<=255;}
} // anon

void applyPendingTacticalIntents() {
    for(unsigned int i=0;i<MAX_TACTICAL_INTENTS_PER_FRAME;++i) {
        TacticalIntent in={}; if(!tactical_intent::legacy::tryPopTacticalIntent(&in)) break;
        TacticalIntentResult out={}; out.sequence=in.sequence;out.kind=in.kind;out.entity=in.entity;
        out.disposition=TacticalIntentDisposition::RejectedByClientBoundary;
        const bool ready=tacticalTransportReady();
        le_t* actor=ready?resolveOwnedTacticalActor(in.entity):nullptr;
        switch(in.kind) {
        case TacticalIntentKind::SetReactionFire:
            if(actor){MSG_Write_PA(PA_STATE,actor->entnum,in.value0!=0?STATE_REACTION:~STATE_REACTION);out.disposition=TacticalIntentDisposition::ForwardedToServer;} break;
        case TacticalIntentKind::SetReservedTimeUnits:
            if(actor&&in.value0>=0&&in.value1>=0){MSG_Write_PA(PA_RESERVE_STATE,actor->entnum,in.value0,in.value1);out.disposition=TacticalIntentDisposition::ForwardedToServer;} break;
        case TacticalIntentKind::ClearShotReservation:
            if(actor&&in.value0>=0){MSG_Write_PA(PA_RESERVE_STATE,actor->entnum,0,in.value0);out.disposition=TacticalIntentDisposition::ForwardedToServer;} break;
        case TacticalIntentKind::SetShotReservation:
            if(actor&&in.value0>=0&&in.value1>=0){MSG_Write_PA(PA_RESERVE_STATE,actor->entnum,in.value0,in.value1);out.disposition=TacticalIntentDisposition::ForwardedToServer;} break;
        case TacticalIntentKind::MoveActor:
            if(actor&&gridCoord(in.value0)&&gridCoord(in.value1)&&gridCoord(in.value2)){
                pos3_t to;to[0]=in.value0;to[1]=in.value1;to[2]=in.value2;
                MSG_Write_PA(PA_MOVE,actor->entnum,to);out.disposition=TacticalIntentDisposition::ForwardedToServer;
            } break;
        case TacticalIntentKind::TurnActor:
            if(actor&&in.value0>=0&&in.value0<=255){MSG_Write_PA(PA_TURN,actor->entnum,in.value0);out.disposition=TacticalIntentDisposition::ForwardedToServer;} break;
        case TacticalIntentKind::Shoot:
            if(actor&&gridCoord(in.value0)&&gridCoord(in.value1)&&gridCoord(in.value2)&&in.value4>=0){
                pos3_t at;at[0]=in.value0;at[1]=in.value1;at[2]=in.value2;
                MSG_Write_PA(PA_SHOOT,actor->entnum,at,in.value3,in.value4,in.value5);out.disposition=TacticalIntentDisposition::ForwardedToServer;
            } break;
        case TacticalIntentKind::Use: {
            le_t* target=ready?resolveLocalEntity(in.targetEntity):nullptr;
            if(actor&&target&&actor->clientAction==target){MSG_Write_PA(PA_USE,actor->entnum,target->entnum);out.disposition=TacticalIntentDisposition::ForwardedToServer;}
            break; }
        case TacticalIntentKind::InventoryMove:
            if(actor&&in.value0>=0&&in.value0<CID_MAX&&in.value3>=0&&in.value3<CID_MAX){
                MSG_Write_PA(PA_INVMOVE,actor->entnum,in.value0,in.value1,in.value2,in.value3,in.value4,in.value5);
                out.disposition=TacticalIntentDisposition::ForwardedToServer;
            } break;
        case TacticalIntentKind::SelectReactionFireMode:
            if(actor&&in.value0>=0&&in.value1>=0){MSG_Write_PA(PA_REACT_SELECT,actor->entnum,in.value0,in.value1,in.value2);out.disposition=TacticalIntentDisposition::ForwardedToServer;} break;
        case TacticalIntentKind::SetCrouchState:
            if(actor){MSG_Write_PA(PA_STATE,actor->entnum,in.value0!=0?STATE_CROUCHED:~STATE_CROUCHED);out.disposition=TacticalIntentDisposition::ForwardedToServer;} break;
        case TacticalIntentKind::UseHeadgear:
            if(actor&&actor->inv.getHeadgear()){
                MSG_Write_PA(PA_SHOOT,actor->entnum,actor->pos,ST_HEADGEAR,0,0);
                out.disposition=TacticalIntentDisposition::ForwardedToServer;
            } break;
        case TacticalIntentKind::Reload:
            /* Deliberately fail closed in v1: CL_ActorReload is void and may reject
             * locally without exposing whether a PA_INVMOVE request was emitted.
             * Extract a bool-returning request helper before reporting ForwardedToServer. */
            break;
        case TacticalIntentKind::EndTurn:
            if(ready && cls.isOurRound()){
                dbuffer msg;
                NET_WriteByte(&msg,clc_endround);
                NET_WriteMsg(cls.netStream,msg);
                out.disposition=TacticalIntentDisposition::ForwardedToServer;
            } break;
        case TacticalIntentKind::AbortMission:
            /* Deliberately fail closed in v1: legacy game_abort is a private command callback.
             * Extract a public client/server request helper before enabling this typed path. */
            break;
        }
        tactical_intent::legacy::publishTacticalIntentResult(out);
    }
}
void resetTacticalIntentAdapter(){tactical_intent::legacy::resetTacticalIntentRuntime();}
} } }

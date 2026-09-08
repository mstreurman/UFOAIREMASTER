/**
 * @file
 * @brief Main-thread legacy campaign adapter for typed strategic intents.
 *
 * Strict-authority v1 rule: only already-qualified canonical owner paths are
 * applied here. Newly catalogued actions fail closed until their legacy UI
 * callback rules are extracted into campaign-owned helpers; they are never
 * routed through Cmd_ExecuteString/Cbuf/cvars from presentation.
 */
#include "../cl_shared.h"
#include "../cgame/campaign/cp_aircraft.h"
#include "../cgame/campaign/cp_campaign.h"
#include "../cgame/campaign/cp_geoscape.h"
#include "../cgame/campaign/cp_missions.h"
#include "../cgame/campaign/cp_time.h"
#include "../cgame/campaign/cp_ufo.h"
#include "strategic_intent.h"
#include "strategic_intent_legacy_adapter.h"
#include <cmath>
#include <cstdint>
#include <limits>

namespace ufo { namespace presentation { namespace legacy { namespace {
const unsigned int MAX_STRATEGIC_INTENTS_PER_FRAME = 64;
const uint32_t UFO_AIRCRAFT_ID_BIT = 0x80000000u;
mission_t* resolveMission(canonical::MissionId id) {
    if (!id.isValid() || id.value > static_cast<uint32_t>(std::numeric_limits<int>::max())) return nullptr;
    return MIS_GetByIdx(static_cast<int>(id.value));
}
aircraft_t* resolvePhalanxAircraft(canonical::AircraftId id) {
    if (!id.isValid() || (id.value & UFO_AIRCRAFT_ID_BIT) != 0) return nullptr;
    if (id.value > static_cast<uint32_t>(std::numeric_limits<int>::max())) return nullptr;
    return AIR_AircraftGetFromIDX(static_cast<int>(id.value));
}
base_t* resolveBase(canonical::BaseId id) {
    if (!id.isValid() || id.value > static_cast<uint32_t>(std::numeric_limits<int>::max())) return nullptr;
    return B_GetFoundedBaseByIDX(static_cast<int>(id.value));
}
aircraft_t* resolveUfoAircraft(canonical::AircraftId id) {
    if (!id.isValid() || (id.value & UFO_AIRCRAFT_ID_BIT) == 0) return nullptr;
    const uint32_t idx=id.value & ~UFO_AIRCRAFT_ID_BIT;
    if (idx >= static_cast<uint32_t>(ccs.numUFOs)) return nullptr;
    aircraft_t* ufo=UFO_GetByIDX(static_cast<int>(idx));
    return ufo&&AIR_IsUFO(ufo)?ufo:nullptr;
}
bool resolveAircraftDestination(const StrategicPosition& position, vec2_t destination) {
    if (!std::isfinite(position.longitude) || !std::isfinite(position.latitude) || !std::isfinite(position.altitude)) return false;
    if (position.longitude < -180.0f || position.longitude > 180.0f || position.latitude < -90.0f || position.latitude > 90.0f) return false;
    Vector2Set(destination, position.longitude, position.latitude);
    return true;
}
canonical::MissionId selectedMissionId() {
    const mission_t* p=GEO_GetSelectedMission(); return p&&p->idx>=0?canonical::MissionId(static_cast<uint32_t>(p->idx)):canonical::MissionId();
}
canonical::AircraftId selectedAircraftId() {
    const aircraft_t* p=GEO_GetSelectedAircraft(); return p&&p->idx>=0?canonical::AircraftId(static_cast<uint32_t>(p->idx)):canonical::AircraftId();
}
} // anon

void applyPendingStrategicIntents() {
    for (unsigned int i=0;i<MAX_STRATEGIC_INTENTS_PER_FRAME;++i) {
        StrategicIntent in={}; if(!intent::legacy::tryPopStrategicIntent(&in)) break;
        StrategicIntentResult out={}; out.sequence=in.sequence; out.kind=in.kind;
        out.disposition=StrategicIntentDisposition::RejectedByCanonical; out.canonicalValue=-1;
        switch(in.kind) {
        case StrategicIntentKind::SetCampaignTimeLapse:
            if(CP_TrySetGameTimeLapse(in.value)) out.disposition=StrategicIntentDisposition::Applied;
            out.canonicalValue=ccs.gameLapse; break;
        case StrategicIntentKind::SelectMission: {
            /* Deprecated compatibility path. New presentation owns viewed selection locally. */
            mission_t* m=resolveMission(in.mission); if(m){GEO_SelectMission(m);if(GEO_GetSelectedMission()==m)out.disposition=StrategicIntentDisposition::Applied;}
            out.mission=selectedMissionId(); out.canonicalValue=out.mission.isValid()?static_cast<int32_t>(out.mission.value):-1; break; }
        case StrategicIntentKind::SelectAircraft: {
            /* Deprecated compatibility path. New presentation owns viewed selection locally. */
            aircraft_t* a=resolvePhalanxAircraft(in.aircraft); if(a){GEO_SelectAircraft(a);if(GEO_GetSelectedAircraft()==a)out.disposition=StrategicIntentDisposition::Applied;}
            out.aircraft=selectedAircraftId(); out.canonicalValue=out.aircraft.isValid()?static_cast<int32_t>(out.aircraft.value):-1; break; }
        case StrategicIntentKind::SendAircraftToMission: {
            aircraft_t* a=resolvePhalanxAircraft(in.aircraft); mission_t* m=resolveMission(in.mission);
            if(a&&m&&AIR_SendAircraftToMission(a,m)) out.disposition=StrategicIntentDisposition::Applied;
            if(a){out.aircraft=canonical::AircraftId(static_cast<uint32_t>(a->idx));out.canonicalValue=static_cast<int32_t>(a->status);} if(m)out.mission=canonical::MissionId(static_cast<uint32_t>(m->idx)); break; }
        case StrategicIntentKind::ReturnAircraftToBase: {
            aircraft_t* a=resolvePhalanxAircraft(in.aircraft); if(a&&AIR_IsAircraftOnGeoscape(a)){AIR_AircraftReturnToBase(a);if(a->status==AIR_RETURNING)out.disposition=StrategicIntentDisposition::Applied;}
            if(a){out.aircraft=canonical::AircraftId(static_cast<uint32_t>(a->idx));out.canonicalValue=static_cast<int32_t>(a->status);} break; }

        case StrategicIntentKind::ChangeAircraftHomebase: {
            aircraft_t* a=resolvePhalanxAircraft(in.aircraft); base_t* b=resolveBase(in.base);
            if(a&&b&&AIR_TryChangeHomebase(a,b)) out.disposition=StrategicIntentDisposition::Applied;
            if(a){out.aircraft=canonical::AircraftId(static_cast<uint32_t>(a->idx));out.canonicalValue=static_cast<int32_t>(a->status);} break; }
        case StrategicIntentKind::PursueUfo: {
            aircraft_t* a=resolvePhalanxAircraft(in.aircraft); aircraft_t* u=resolveUfoAircraft(in.targetAircraft);
            if(a&&u&&AIR_TryPursueUFO(a,u)==AIR_PURSUIT_APPLIED) out.disposition=StrategicIntentDisposition::Applied;
            if(a){out.aircraft=canonical::AircraftId(static_cast<uint32_t>(a->idx));out.canonicalValue=static_cast<int32_t>(a->status);} break; }
        case StrategicIntentKind::SetAircraftDestination: {
            aircraft_t* a=resolvePhalanxAircraft(in.aircraft); vec2_t destination;
            if(a&&resolveAircraftDestination(in.position,destination)&&AIR_TrySetAircraftDestination(a,destination)) out.disposition=StrategicIntentDisposition::Applied;
            if(a){out.aircraft=canonical::AircraftId(static_cast<uint32_t>(a->idx));out.canonicalValue=static_cast<int32_t>(a->status);} break; }
        case StrategicIntentKind::StartAircraft: {
            aircraft_t* a=resolvePhalanxAircraft(in.aircraft);
            if(a&&AIR_TryStartAircraft(a)==AIR_START_APPLIED) out.disposition=StrategicIntentDisposition::Applied;
            if(a){out.aircraft=canonical::AircraftId(static_cast<uint32_t>(a->idx));out.canonicalValue=static_cast<int32_t>(a->status);} break; }
        case StrategicIntentKind::StopAircraft: {
            aircraft_t* a=resolvePhalanxAircraft(in.aircraft);
            if(a&&AIR_TryStopAircraft(a)) out.disposition=StrategicIntentDisposition::Applied;
            if(a){out.aircraft=canonical::AircraftId(static_cast<uint32_t>(a->idx));out.canonicalValue=static_cast<int32_t>(a->status);} break; }

        /* Strict-authority catalog is transport-complete, but these actions stay
         * rejected until callback-owned validation/mutation is moved into its
         * canonical campaign subsystem. No command-string fallback is allowed. */
        case StrategicIntentKind::AcceptUfoSaleOffer:
        case StrategicIntentKind::AssignEmployeeToAircraft:
        case StrategicIntentKind::AssignResearch:
        case StrategicIntentKind::AutoResolveMission:
        case StrategicIntentKind::BuildBase:
        case StrategicIntentKind::BuildFacility:
        case StrategicIntentKind::BuildInstallation:
        case StrategicIntentKind::BuyAircraft:
        case StrategicIntentKind::BuyItem:
        case StrategicIntentKind::BuyUGV:
        case StrategicIntentKind::DecreaseProduction:
        case StrategicIntentKind::DeequipEmployee:
        case StrategicIntentKind::DeleteEmployee:
        case StrategicIntentKind::DestroyAntimatterFacility:
        case StrategicIntentKind::DestroyFacility:
        case StrategicIntentKind::DestroyInstallation:
        case StrategicIntentKind::DestroyStoredUfo:
        case StrategicIntentKind::EquipAircraftItem:
        case StrategicIntentKind::EquipBaseDefenceItem:
        case StrategicIntentKind::HireOrFireEmployee:
        case StrategicIntentKind::IncreaseProduction:
        case StrategicIntentKind::KillContainedAlien:
        case StrategicIntentKind::KillContainedAliens:
        case StrategicIntentKind::LoadGame:
        case StrategicIntentKind::LoadLastSave:
        case StrategicIntentKind::MaxAssignResearch:
        case StrategicIntentKind::MoveProductionDown:
        case StrategicIntentKind::MoveProductionUp:
        case StrategicIntentKind::RemoveAircraftItem:
        case StrategicIntentKind::RemoveBaseDefenceItem:
        case StrategicIntentKind::RenameAircraft:
        case StrategicIntentKind::RenameBase:
        case StrategicIntentKind::RenameEmployee:
        case StrategicIntentKind::RenameInstallation:
        case StrategicIntentKind::SaveGame:
        case StrategicIntentKind::SellAircraft:
        case StrategicIntentKind::SellItem:
        case StrategicIntentKind::SellUGV:
        case StrategicIntentKind::SetAirDefenceAutoFire:
        case StrategicIntentKind::SetAirDefenceTarget:
        case StrategicIntentKind::SetAutoSellPolicy:
        case StrategicIntentKind::SetEmployeeSkin:
        case StrategicIntentKind::SetProductionAmount:
        case StrategicIntentKind::StartMission:
        case StrategicIntentKind::StartTransfer:
        case StrategicIntentKind::StopProduction:
        case StrategicIntentKind::StopResearch:
        case StrategicIntentKind::StoreRecoveredUfo:
        case StrategicIntentKind::TransferStoredUfo:
            break;
        }
        intent::legacy::publishStrategicIntentResult(out);
    }
}
void resetStrategicIntentAdapter(){intent::legacy::resetStrategicIntentRuntime();}
} } }

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
#include "../cgame/campaign/cp_research.h"
#include "../cgame/campaign/cp_time.h"
#include "../cgame/campaign/cp_ufo.h"
#include "strategic_intent.h"
#include "strategic_intent_legacy_adapter.h"
#include <cmath>
#include <cstddef>
#include <cstring>
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
technology_t* resolveTechnology(canonical::TechnologyId id) {
    if (!id.isValid() || id.value > static_cast<uint32_t>(std::numeric_limits<int>::max())) return nullptr;
    return RS_GetTechByIDX(static_cast<int>(id.value));
}
aircraft_t* resolveUfoAircraft(canonical::AircraftId id) {
    if (!id.isValid() || (id.value & UFO_AIRCRAFT_ID_BIT) == 0) return nullptr;
    const uint32_t idx=id.value & ~UFO_AIRCRAFT_ID_BIT;
    if (idx >= static_cast<uint32_t>(ccs.numUFOs)) return nullptr;
    aircraft_t* ufo=UFO_GetByIDX(static_cast<int>(idx));
    return ufo&&AIR_IsUFO(ufo)?ufo:nullptr;
}
bool resolveStrategicPosition2(const StrategicPosition& position, vec2_t destination) {
    if (!std::isfinite(position.longitude) || !std::isfinite(position.latitude) || !std::isfinite(position.altitude)) return false;
    if (position.longitude < -180.0f || position.longitude > 180.0f || position.latitude < -90.0f || position.latitude > 90.0f) return false;
    Vector2Set(destination, position.longitude, position.latitude);
    return true;
}
bool resolveAircraftDestination(const StrategicPosition& position, vec2_t destination) {
    return resolveStrategicPosition2(position, destination);
}
installation_t* resolveInstallation(canonical::InstallationId id) {
    if (!id.isValid() || id.value > static_cast<uint32_t>(std::numeric_limits<int>::max())) return nullptr;
    return INS_GetByIDX(static_cast<int>(id.value));
}
template <std::size_t N>
const char* resolveBoundedText(const char (&text)[N]) {
    return std::memchr(text, '\0', N) ? text : nullptr;
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

        case StrategicIntentKind::AssignResearch: {
            base_t* b=resolveBase(in.base); technology_t* tech=resolveTechnology(in.technology);
            if(b&&tech&&RS_TryChangeScientists(tech,b,in.value0)==RS_CHANGE_APPLIED) out.disposition=StrategicIntentDisposition::Applied;
            if(tech) out.canonicalValue=tech->scientists; break; }
        case StrategicIntentKind::MaxAssignResearch: {
            base_t* b=resolveBase(in.base); technology_t* tech=resolveTechnology(in.technology);
            if(b&&tech&&RS_TryMaxAssignScientists(tech,b)==RS_CHANGE_APPLIED) out.disposition=StrategicIntentDisposition::Applied;
            if(tech) out.canonicalValue=tech->scientists; break; }
        case StrategicIntentKind::StopResearch: {
            base_t* b=resolveBase(in.base); technology_t* tech=resolveTechnology(in.technology);
            if(b&&tech&&RS_TryStopResearch(tech,b)==RS_CHANGE_APPLIED) out.disposition=StrategicIntentDisposition::Applied;
            if(tech) out.canonicalValue=tech->scientists; break; }

        case StrategicIntentKind::BuildBase: {
            vec2_t pos; base_t* b=nullptr; const char* name=resolveBoundedText(in.text);
            if(name&&resolveStrategicPosition2(in.position,pos)&&B_TryBuildBase(pos,name,&b)==B_BUILD_APPLIED){out.disposition=StrategicIntentDisposition::Applied;out.canonicalValue=b?b->idx:-1;}
            break; }
        case StrategicIntentKind::RenameBase: {
            base_t* b=resolveBase(in.base); const char* name=resolveBoundedText(in.text);
            if(b&&name&&B_TrySetName(b,name)){out.disposition=StrategicIntentDisposition::Applied;out.canonicalValue=b->idx;}
            break; }
        case StrategicIntentKind::BuildFacility: {
            base_t* b=resolveBase(in.base); const char* definition=resolveBoundedText(in.key0); building_t* facility=nullptr;
            if(b&&definition&&B_TryBuildFacility(b,definition,in.value0,in.value1,&facility)==B_FACILITY_BUILD_APPLIED){out.disposition=StrategicIntentDisposition::Applied;out.canonicalValue=facility?facility->idx:-1;}
            break; }
        case StrategicIntentKind::DestroyFacility: {
            base_t* b=resolveBase(in.base);
            if(b&&B_TryDestroyFacility(b,in.value0)==B_FACILITY_DESTROY_APPLIED){out.disposition=StrategicIntentDisposition::Applied;out.canonicalValue=in.value0;}
            break; }
        case StrategicIntentKind::BuildInstallation: {
            vec2_t pos; installation_t* installation=nullptr; const char* definition=resolveBoundedText(in.key0); const char* name=resolveBoundedText(in.text);
            const installationTemplate_t* tpl=definition?INS_GetInstallationTemplateByID(definition):nullptr;
            if(tpl&&name&&resolveStrategicPosition2(in.position,pos)&&INS_TryBuildInstallation(tpl,pos,name,&installation)==INS_BUILD_APPLIED){out.disposition=StrategicIntentDisposition::Applied;out.canonicalValue=installation?installation->idx:-1;}
            break; }
        case StrategicIntentKind::RenameInstallation: {
            installation_t* installation=resolveInstallation(in.installation); const char* name=resolveBoundedText(in.text);
            if(installation&&name&&INS_TrySetName(installation,name)){out.disposition=StrategicIntentDisposition::Applied;out.canonicalValue=installation->idx;}
            break; }
        case StrategicIntentKind::DestroyInstallation: {
            installation_t* installation=resolveInstallation(in.installation);
            if(installation){const int idx=installation->idx;if(INS_TryDestroyInstallation(installation)){out.disposition=StrategicIntentDisposition::Applied;out.canonicalValue=idx;}}
            break; }

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
        case StrategicIntentKind::AutoResolveMission:
        case StrategicIntentKind::BuyAircraft:
        case StrategicIntentKind::BuyItem:
        case StrategicIntentKind::BuyUGV:
        case StrategicIntentKind::DecreaseProduction:
        case StrategicIntentKind::DeequipEmployee:
        case StrategicIntentKind::DeleteEmployee:
        case StrategicIntentKind::DestroyAntimatterFacility:
        case StrategicIntentKind::DestroyStoredUfo:
        case StrategicIntentKind::EquipAircraftItem:
        case StrategicIntentKind::EquipBaseDefenceItem:
        case StrategicIntentKind::HireOrFireEmployee:
        case StrategicIntentKind::IncreaseProduction:
        case StrategicIntentKind::KillContainedAlien:
        case StrategicIntentKind::KillContainedAliens:
        case StrategicIntentKind::LoadGame:
        case StrategicIntentKind::LoadLastSave:
        case StrategicIntentKind::MoveProductionDown:
        case StrategicIntentKind::MoveProductionUp:
        case StrategicIntentKind::RemoveAircraftItem:
        case StrategicIntentKind::RemoveBaseDefenceItem:
        case StrategicIntentKind::RenameAircraft:
        case StrategicIntentKind::RenameEmployee:
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
        case StrategicIntentKind::StoreRecoveredUfo:
        case StrategicIntentKind::TransferStoredUfo:
            break;
        }
        intent::legacy::publishStrategicIntentResult(out);
    }
}
void resetStrategicIntentAdapter(){intent::legacy::resetStrategicIntentRuntime();}
} } }

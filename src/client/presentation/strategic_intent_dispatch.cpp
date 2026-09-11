/** Bounded C++26 runtime transport for the strict strategic intent surface. */
#include "strategic_intent.h"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <mutex>
namespace ufo { namespace presentation { namespace intent { namespace {
constexpr std::size_t CAP=256, RCAP=256;
template<typename T,std::size_t N> class Ring { public: bool push(const T& v){if(c==N)return false;a[w]=v;w=(w+1)%N;++c;return true;} bool pop(T& v){if(!c)return false;v=a[r];r=(r+1)%N;--c;return true;} bool full()const{return c==N;} void clear(){r=w=c=0;} private: std::array<T,N>a{};std::size_t r=0,w=0,c=0;};
std::mutex m; Ring<StrategicIntent,CAP> q; Ring<StrategicIntentResult,RCAP> rq; uint64_t seq=1;
uint64_t alloc(){const uint64_t s=seq++;if(seq==0)seq=1;return s;}
StrategicIntent make(StrategicIntentKind k){StrategicIntent v={};v.kind=k;return v;}
template<std::size_t N> void copyBounded(char (&dst)[N], const char* src){if(!src){dst[0]='\0';return;}std::strncpy(dst,src,N-1);dst[N-1]='\0';}
StrategicIntentSubmission submit(StrategicIntent v){std::lock_guard<std::mutex>l(m);StrategicIntentSubmission s={0,false};if(q.full())return s;v.sequence=alloc();if(!q.push(v))return s;s.sequence=v.sequence;s.accepted=true;return s;}
} // anon
StrategicIntentSubmission submitSetCampaignTimeLapse(int32_t gameLapse)
{
    StrategicIntent v = make(StrategicIntentKind::SetCampaignTimeLapse);
    v.value = gameLapse; v.value0 = gameLapse;
    return submit(v);
}

StrategicIntentSubmission submitSelectMission(canonical::MissionId mission)
{
    StrategicIntent v = make(StrategicIntentKind::SelectMission);
    v.mission = mission;
    return submit(v);
}

StrategicIntentSubmission submitSelectAircraft(canonical::AircraftId aircraft)
{
    StrategicIntent v = make(StrategicIntentKind::SelectAircraft);
    v.aircraft = aircraft;
    return submit(v);
}

StrategicIntentSubmission submitSendAircraftToMission(canonical::AircraftId aircraft, canonical::MissionId mission)
{
    StrategicIntent v = make(StrategicIntentKind::SendAircraftToMission);
    v.aircraft = aircraft; v.mission = mission;
    return submit(v);
}

StrategicIntentSubmission submitReturnAircraftToBase(canonical::AircraftId aircraft)
{
    StrategicIntent v = make(StrategicIntentKind::ReturnAircraftToBase);
    v.aircraft = aircraft;
    return submit(v);
}

StrategicIntentSubmission submitAcceptUfoSaleOffer(canonical::UfoSaleOfferId offer)
{
    StrategicIntent v = make(StrategicIntentKind::AcceptUfoSaleOffer);
    v.offer = offer;
    return submit(v);
}

StrategicIntentSubmission submitAssignEmployeeToAircraft(canonical::EmployeeId employee, canonical::AircraftId aircraft, bool assigned)
{
    StrategicIntent v = make(StrategicIntentKind::AssignEmployeeToAircraft);
    v.employee = employee; v.aircraft = aircraft; v.value0 = assigned ? 1 : 0;
    return submit(v);
}

StrategicIntentSubmission submitAssignResearch(canonical::BaseId base, canonical::TechnologyId technology, int32_t scientistDelta)
{
    StrategicIntent v = make(StrategicIntentKind::AssignResearch);
    v.base = base; v.technology = technology; v.value0 = scientistDelta;
    return submit(v);
}

StrategicIntentSubmission submitAutoResolveMission(canonical::MissionId mission, canonical::AircraftId missionAircraft, canonical::AircraftId interceptorAircraft)
{
    StrategicIntent v = make(StrategicIntentKind::AutoResolveMission);
    v.mission = mission; v.aircraft = missionAircraft; v.targetAircraft = interceptorAircraft;
    return submit(v);
}

StrategicIntentSubmission submitBuildBase(StrategicPosition position, const char* name)
{
    StrategicIntent v = make(StrategicIntentKind::BuildBase);
    v.position = position; copyBounded(v.text, name);
    return submit(v);
}

StrategicIntentSubmission submitBuildFacility(canonical::BaseId base, const char* facilityDefinition, int32_t column, int32_t row)
{
    StrategicIntent v = make(StrategicIntentKind::BuildFacility);
    v.base = base; v.value0 = column; v.value1 = row; copyBounded(v.key0, facilityDefinition);
    return submit(v);
}

StrategicIntentSubmission submitBuildInstallation(StrategicPosition position, const char* installationDefinition, const char* name)
{
    StrategicIntent v = make(StrategicIntentKind::BuildInstallation);
    v.position = position; copyBounded(v.key0, installationDefinition); copyBounded(v.text, name);
    return submit(v);
}

StrategicIntentSubmission submitBuyAircraft(canonical::BaseId base, const char* aircraftDefinition)
{
    StrategicIntent v = make(StrategicIntentKind::BuyAircraft);
    v.base = base; copyBounded(v.key0, aircraftDefinition);
    return submit(v);
}

StrategicIntentSubmission submitBuyItem(canonical::BaseId base, canonical::ItemId item, int32_t count)
{
    StrategicIntent v = make(StrategicIntentKind::BuyItem);
    v.base = base; v.item = item; v.value0 = count;
    return submit(v);
}

StrategicIntentSubmission submitBuyUGV(canonical::BaseId base, const char* ugvDefinition)
{
    StrategicIntent v = make(StrategicIntentKind::BuyUGV);
    v.base = base; copyBounded(v.key0, ugvDefinition);
    return submit(v);
}

StrategicIntentSubmission submitChangeAircraftHomebase(canonical::AircraftId aircraft, canonical::BaseId base)
{
    StrategicIntent v = make(StrategicIntentKind::ChangeAircraftHomebase);
    v.aircraft = aircraft; v.base = base;
    return submit(v);
}

StrategicIntentSubmission submitDecreaseProduction(canonical::BaseId base, canonical::ProductionId production, int32_t amount)
{
    StrategicIntent v = make(StrategicIntentKind::DecreaseProduction);
    v.base = base; v.production = production; v.value0 = amount;
    return submit(v);
}

StrategicIntentSubmission submitDeequipEmployee(canonical::BaseId base, canonical::EmployeeId employee)
{
    StrategicIntent v = make(StrategicIntentKind::DeequipEmployee);
    v.base = base; v.employee = employee;
    return submit(v);
}

StrategicIntentSubmission submitDeleteEmployee(canonical::EmployeeId employee)
{
    StrategicIntent v = make(StrategicIntentKind::DeleteEmployee);
    v.employee = employee;
    return submit(v);
}

StrategicIntentSubmission submitDestroyAntimatterFacility(canonical::BaseId base, int32_t facilityIndex)
{
    StrategicIntent v = make(StrategicIntentKind::DestroyAntimatterFacility);
    v.base = base; v.value0 = facilityIndex;
    return submit(v);
}

StrategicIntentSubmission submitDestroyFacility(canonical::BaseId base, canonical::FacilityId facility)
{
    StrategicIntent v = make(StrategicIntentKind::DestroyFacility);
    v.base = base; v.facility = facility;
    return submit(v);
}

StrategicIntentSubmission submitDestroyInstallation(canonical::InstallationId installation)
{
    StrategicIntent v = make(StrategicIntentKind::DestroyInstallation);
    v.installation = installation;
    return submit(v);
}

StrategicIntentSubmission submitDestroyStoredUfo(canonical::StoredUfoId storedUfo)
{
    StrategicIntent v = make(StrategicIntentKind::DestroyStoredUfo);
    v.storedUfo = storedUfo;
    return submit(v);
}

StrategicIntentSubmission submitEquipAircraftItem(canonical::AircraftId aircraft, int32_t slotType, int32_t slotIndex, int32_t zone, canonical::ItemId item)
{
    StrategicIntent v = make(StrategicIntentKind::EquipAircraftItem);
    v.aircraft = aircraft; v.value0 = slotType; v.value1 = slotIndex; v.value2 = zone; v.item = item;
    return submit(v);
}

StrategicIntentSubmission submitEquipBaseDefenceItem(canonical::BaseId base, canonical::InstallationId installation, int32_t defenceType, int32_t slotIndex, canonical::ItemId item)
{
    StrategicIntent v = make(StrategicIntentKind::EquipBaseDefenceItem);
    v.base = base; v.installation = installation; v.value0 = defenceType; v.value1 = slotIndex; v.item = item;
    return submit(v);
}

StrategicIntentSubmission submitHireOrFireEmployee(canonical::BaseId base, canonical::EmployeeId employee, bool hire)
{
    StrategicIntent v = make(StrategicIntentKind::HireOrFireEmployee);
    v.base = base; v.employee = employee; v.value0 = hire ? 1 : 0;
    return submit(v);
}

StrategicIntentSubmission submitIncreaseProduction(canonical::BaseId base, canonical::ProductionId production, int32_t amount)
{
    StrategicIntent v = make(StrategicIntentKind::IncreaseProduction);
    v.base = base; v.production = production; v.value0 = amount;
    return submit(v);
}

StrategicIntentSubmission submitCreateProduction(canonical::BaseId base, int32_t subjectKind, canonical::ItemId item, canonical::StoredUfoId storedUfo, const char* aircraftDefinition, int32_t amount)
{
    StrategicIntent v = make(StrategicIntentKind::CreateProduction);
    v.base = base; v.value0 = subjectKind; v.item = item; v.storedUfo = storedUfo; v.value1 = amount; copyBounded(v.key0, aircraftDefinition);
    return submit(v);
}

StrategicIntentSubmission submitKillContainedAlien(canonical::BaseId base, canonical::TechnologyId technology)
{
    StrategicIntent v = make(StrategicIntentKind::KillContainedAlien);
    v.base = base; v.technology = technology;
    return submit(v);
}

StrategicIntentSubmission submitKillContainedAliens(canonical::BaseId base)
{
    StrategicIntent v = make(StrategicIntentKind::KillContainedAliens);
    v.base = base;
    return submit(v);
}

StrategicIntentSubmission submitLoadGame(const char* slot)
{
    StrategicIntent v = make(StrategicIntentKind::LoadGame);
    copyBounded(v.key0, slot);
    return submit(v);
}

StrategicIntentSubmission submitLoadLastSave()
{
    StrategicIntent v = make(StrategicIntentKind::LoadLastSave);

    return submit(v);
}

StrategicIntentSubmission submitMaxAssignResearch(canonical::BaseId base, canonical::TechnologyId technology)
{
    StrategicIntent v = make(StrategicIntentKind::MaxAssignResearch);
    v.base = base; v.technology = technology;
    return submit(v);
}

StrategicIntentSubmission submitMoveProductionDown(canonical::BaseId base, canonical::ProductionId production)
{
    StrategicIntent v = make(StrategicIntentKind::MoveProductionDown);
    v.base = base; v.production = production;
    return submit(v);
}

StrategicIntentSubmission submitMoveProductionUp(canonical::BaseId base, canonical::ProductionId production)
{
    StrategicIntent v = make(StrategicIntentKind::MoveProductionUp);
    v.base = base; v.production = production;
    return submit(v);
}

StrategicIntentSubmission submitPursueUfo(canonical::AircraftId aircraft, canonical::AircraftId ufo)
{
    StrategicIntent v = make(StrategicIntentKind::PursueUfo);
    v.aircraft = aircraft; v.targetAircraft = ufo;
    return submit(v);
}

StrategicIntentSubmission submitRemoveAircraftItem(canonical::AircraftId aircraft, int32_t slotType, int32_t slotIndex, int32_t zone)
{
    StrategicIntent v = make(StrategicIntentKind::RemoveAircraftItem);
    v.aircraft = aircraft; v.value0 = slotType; v.value1 = slotIndex; v.value2 = zone;
    return submit(v);
}

StrategicIntentSubmission submitRemoveBaseDefenceItem(canonical::BaseId base, canonical::InstallationId installation, int32_t defenceType, int32_t slotIndex)
{
    StrategicIntent v = make(StrategicIntentKind::RemoveBaseDefenceItem);
    v.base = base; v.installation = installation; v.value0 = defenceType; v.value1 = slotIndex;
    return submit(v);
}

StrategicIntentSubmission submitRenameAircraft(canonical::AircraftId aircraft, const char* name)
{
    StrategicIntent v = make(StrategicIntentKind::RenameAircraft);
    v.aircraft = aircraft; copyBounded(v.text, name);
    return submit(v);
}

StrategicIntentSubmission submitRenameBase(canonical::BaseId base, const char* name)
{
    StrategicIntent v = make(StrategicIntentKind::RenameBase);
    v.base = base; copyBounded(v.text, name);
    return submit(v);
}

StrategicIntentSubmission submitRenameEmployee(canonical::EmployeeId employee, const char* name)
{
    StrategicIntent v = make(StrategicIntentKind::RenameEmployee);
    v.employee = employee; copyBounded(v.text, name);
    return submit(v);
}

StrategicIntentSubmission submitRenameInstallation(canonical::InstallationId installation, const char* name)
{
    StrategicIntent v = make(StrategicIntentKind::RenameInstallation);
    v.installation = installation; copyBounded(v.text, name);
    return submit(v);
}

StrategicIntentSubmission submitSaveGame(const char* slot, const char* comment)
{
    StrategicIntent v = make(StrategicIntentKind::SaveGame);
    copyBounded(v.key0, slot); copyBounded(v.text, comment);
    return submit(v);
}

StrategicIntentSubmission submitSellAircraft(canonical::AircraftId aircraft)
{
    StrategicIntent v = make(StrategicIntentKind::SellAircraft);
    v.aircraft = aircraft;
    return submit(v);
}

StrategicIntentSubmission submitSellItem(canonical::BaseId base, canonical::ItemId item, int32_t count)
{
    StrategicIntent v = make(StrategicIntentKind::SellItem);
    v.base = base; v.item = item; v.value0 = count;
    return submit(v);
}

StrategicIntentSubmission submitSellUGV(canonical::EmployeeId employee)
{
    StrategicIntent v = make(StrategicIntentKind::SellUGV);
    v.employee = employee;
    return submit(v);
}

StrategicIntentSubmission submitSetAirDefenceAutoFire(canonical::BaseId base, canonical::InstallationId installation, bool enabled)
{
    StrategicIntent v = make(StrategicIntentKind::SetAirDefenceAutoFire);
    v.base = base; v.installation = installation; v.value0 = enabled ? 1 : 0;
    return submit(v);
}

StrategicIntentSubmission submitSetAirDefenceTarget(canonical::BaseId base, canonical::InstallationId installation, canonical::AircraftId ufo)
{
    StrategicIntent v = make(StrategicIntentKind::SetAirDefenceTarget);
    v.base = base; v.installation = installation; v.targetAircraft = ufo;
    return submit(v);
}

StrategicIntentSubmission submitSetAircraftDestination(canonical::AircraftId aircraft, StrategicPosition position)
{
    StrategicIntent v = make(StrategicIntentKind::SetAircraftDestination);
    v.aircraft = aircraft; v.position = position;
    return submit(v);
}

StrategicIntentSubmission submitSetAutoSellPolicy(canonical::ItemId item, bool enabled)
{
    StrategicIntent v = make(StrategicIntentKind::SetAutoSellPolicy);
    v.item = item; v.value0 = enabled ? 1 : 0;
    return submit(v);
}

StrategicIntentSubmission submitSetEmployeeSkin(canonical::EmployeeId employee, int32_t bodySkin)
{
    StrategicIntent v = make(StrategicIntentKind::SetEmployeeSkin);
    v.employee = employee; v.value0 = bodySkin;
    return submit(v);
}

StrategicIntentSubmission submitSetProductionAmount(canonical::BaseId base, canonical::ProductionId production, int32_t amount)
{
    StrategicIntent v = make(StrategicIntentKind::SetProductionAmount);
    v.base = base; v.production = production; v.value0 = amount;
    return submit(v);
}

StrategicIntentSubmission submitStartAircraft(canonical::AircraftId aircraft)
{
    StrategicIntent v = make(StrategicIntentKind::StartAircraft);
    v.aircraft = aircraft;
    return submit(v);
}

StrategicIntentSubmission submitStartMission(canonical::MissionId mission, canonical::AircraftId aircraft)
{
    StrategicIntent v = make(StrategicIntentKind::StartMission);
    v.mission = mission; v.aircraft = aircraft;
    return submit(v);
}

StrategicIntentSubmission submitStartTransfer(canonical::TransferManifestId manifest)
{
    StrategicIntent v = make(StrategicIntentKind::StartTransfer);
    v.transferManifest = manifest;
    return submit(v);
}

StrategicIntentSubmission submitStopAircraft(canonical::AircraftId aircraft)
{
    StrategicIntent v = make(StrategicIntentKind::StopAircraft);
    v.aircraft = aircraft;
    return submit(v);
}

StrategicIntentSubmission submitStopProduction(canonical::BaseId base, canonical::ProductionId production)
{
    StrategicIntent v = make(StrategicIntentKind::StopProduction);
    v.base = base; v.production = production;
    return submit(v);
}

StrategicIntentSubmission submitStopResearch(canonical::BaseId base, canonical::TechnologyId technology)
{
    StrategicIntent v = make(StrategicIntentKind::StopResearch);
    v.base = base; v.technology = technology;
    return submit(v);
}

StrategicIntentSubmission submitStoreRecoveredUfo(const char* ufoDefinition, float conditionPercent, canonical::InstallationId installation)
{
    StrategicIntent v = make(StrategicIntentKind::StoreRecoveredUfo);
    copyBounded(v.key0, ufoDefinition); v.scalar0 = conditionPercent; v.installation = installation;
    return submit(v);
}

StrategicIntentSubmission submitTransferStoredUfo(canonical::StoredUfoId storedUfo, canonical::InstallationId installation)
{
    StrategicIntent v = make(StrategicIntentKind::TransferStoredUfo);
    v.storedUfo = storedUfo; v.installation = installation;
    return submit(v);
}

bool pollStrategicIntentResult(StrategicIntentResult* out){if(!out)return false;std::lock_guard<std::mutex>l(m);return rq.pop(*out);}
namespace legacy {
bool tryPopStrategicIntent(StrategicIntent* out){if(!out)return false;std::lock_guard<std::mutex>l(m);return q.pop(*out);}
void publishStrategicIntentResult(const StrategicIntentResult& v){std::lock_guard<std::mutex>l(m);if(rq.full()){StrategicIntentResult d={};rq.pop(d);}rq.push(v);}
void resetStrategicIntentRuntime(){std::lock_guard<std::mutex>l(m);q.clear();rq.clear();}
} } } }

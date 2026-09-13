/**
 * @file
 * @brief Complete C++11-compatible strategic authoritative intent surface from the strict M1 authority inventory.
 */
#pragma once
#include "canonical_identity.h"
#include "strategic_position.h"
#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace ufo { namespace presentation {
enum class StrategicIntentKind : uint8_t {
    SetCampaignTimeLapse = 1,
    SelectMission = 2,
    SelectAircraft = 3,
    SendAircraftToMission = 4,
    ReturnAircraftToBase = 5,
    AcceptUfoSaleOffer = 6,
    AssignEmployeeToAircraft = 7,
    AssignResearch = 8,
    AutoResolveMission = 9,
    BuildBase = 10,
    BuildFacility = 11,
    BuildInstallation = 12,
    BuyAircraft = 13,
    BuyItem = 14,
    BuyUGV = 15,
    ChangeAircraftHomebase = 16,
    DecreaseProduction = 17,
    DeequipEmployee = 18,
    DeleteEmployee = 19,
    DestroyAntimatterFacility = 20, /* deprecated tombstone: internal scripted event, not a presentation intent */
    DestroyFacility = 21,
    DestroyInstallation = 22,
    DestroyStoredUfo = 23,
    EquipAircraftItem = 24,
    EquipBaseDefenceItem = 25,
    HireOrFireEmployee = 26,
    IncreaseProduction = 27,
    KillContainedAlien = 28,
    KillContainedAliens = 29,
    LoadGame = 30,
    LoadLastSave = 31,
    MaxAssignResearch = 32,
    MoveProductionDown = 33,
    MoveProductionUp = 34,
    PursueUfo = 35,
    RemoveAircraftItem = 36,
    RemoveBaseDefenceItem = 37,
    RenameAircraft = 38,
    RenameBase = 39,
    RenameEmployee = 40,
    RenameInstallation = 41,
    SaveGame = 42,
    SellAircraft = 43,
    SellItem = 44,
    SellUGV = 45,
    SetAirDefenceAutoFire = 46,
    SetAirDefenceTarget = 47,
    SetAircraftDestination = 48,
    SetAutoSellPolicy = 49,
    SetEmployeeSkin = 50,
    SetProductionAmount = 51,
    StartAircraft = 52,
    StartMission = 53,
    StartTransfer = 54,
    StopAircraft = 55,
    StopProduction = 56,
    StopResearch = 57,
    StoreRecoveredUfo = 58,
    TransferStoredUfo = 59,
    CreateProduction = 60,
};
enum class StrategicIntentDisposition : uint8_t { Applied = 1, RejectedByCanonical = 2 };

constexpr std::size_t STRATEGIC_TRANSFER_MAX_ITEMS = 1024;
constexpr std::size_t STRATEGIC_TRANSFER_MAX_EMPLOYEES = 512;
constexpr std::size_t STRATEGIC_TRANSFER_MAX_AIRCRAFT = 64;
constexpr std::size_t STRATEGIC_TRANSFER_MAX_ALIEN_TYPES = 128;
constexpr std::size_t STRATEGIC_TRANSFER_TEAM_KEY_BYTES = 96;

struct StrategicTransferItem {
    canonical::ItemId item;
    int32_t amount;
};

struct StrategicTransferAlien {
    char teamDefinition[STRATEGIC_TRANSFER_TEAM_KEY_BYTES];
    int32_t alive;
    int32_t dead;
};

struct StrategicTransferManifest {
    canonical::BaseId source;
    canonical::BaseId destination;
    int32_t antimatter;
    uint32_t itemCount;
    StrategicTransferItem items[STRATEGIC_TRANSFER_MAX_ITEMS];
    uint32_t employeeCount;
    canonical::EmployeeId employees[STRATEGIC_TRANSFER_MAX_EMPLOYEES];
    uint32_t aircraftCount;
    canonical::AircraftId aircraft[STRATEGIC_TRANSFER_MAX_AIRCRAFT];
    uint32_t alienCount;
    StrategicTransferAlien aliens[STRATEGIC_TRANSFER_MAX_ALIEN_TYPES];
};

static_assert(std::is_standard_layout<StrategicTransferManifest>::value,
    "StrategicTransferManifest must remain standard-layout");
static_assert(std::is_trivially_copyable<StrategicTransferManifest>::value,
    "StrategicTransferManifest must remain trivially copyable");
struct StrategicIntent {
    uint64_t sequence;
    StrategicIntentKind kind;
    int32_t value; /* compatibility scalar for the qualified SetCampaignTimeLapse lane */
    int32_t value0, value1, value2, value3, value4, value5;
    float scalar0;
    StrategicPosition position;
    canonical::MissionId mission;
    canonical::AircraftId aircraft;
    canonical::AircraftId targetAircraft;
    canonical::BaseId base;
    canonical::FacilityId facility;
    canonical::InstallationId installation;
    canonical::NationId nation;
    canonical::EmployeeId employee;
    canonical::TechnologyId technology;
    canonical::ProductionId production;
    canonical::DefenceSlotId defenceSlot;
    canonical::ItemId item;
    canonical::StoredUfoId storedUfo;
    canonical::UfoRecoveryId recovery;
    canonical::UfoSaleOfferId offer;
    canonical::TransferManifestId transferManifest;
    char key0[96];
    char key1[96];
    char text[128];
};
struct StrategicIntentSubmission { uint64_t sequence; bool accepted; };
struct StrategicIntentResult {
    uint64_t sequence; StrategicIntentKind kind; StrategicIntentDisposition disposition;
    int32_t canonicalValue; canonical::MissionId mission; canonical::AircraftId aircraft;
};
static_assert(std::is_standard_layout<StrategicIntent>::value, "StrategicIntent must remain standard-layout");
static_assert(std::is_trivially_copyable<StrategicIntent>::value, "StrategicIntent must remain trivially copyable");
static_assert(std::is_standard_layout<StrategicIntentResult>::value, "StrategicIntentResult must remain standard-layout");
static_assert(std::is_trivially_copyable<StrategicIntentResult>::value, "StrategicIntentResult must remain trivially copyable");
namespace intent {
StrategicIntentSubmission submitSetCampaignTimeLapse(int32_t gameLapse);
/** @deprecated strict M1 authority inventory classifies viewed mission selection as presentation context. */
StrategicIntentSubmission submitSelectMission(canonical::MissionId mission);
/** @deprecated strict M1 authority inventory classifies viewed aircraft selection as presentation context. */
StrategicIntentSubmission submitSelectAircraft(canonical::AircraftId aircraft);
StrategicIntentSubmission submitSendAircraftToMission(canonical::AircraftId aircraft, canonical::MissionId mission);
StrategicIntentSubmission submitReturnAircraftToBase(canonical::AircraftId aircraft);

StrategicIntentSubmission submitAcceptUfoSaleOffer(canonical::UfoSaleOfferId offer);
StrategicIntentSubmission submitAssignEmployeeToAircraft(canonical::EmployeeId employee, canonical::AircraftId aircraft, bool assigned);
StrategicIntentSubmission submitAssignResearch(canonical::BaseId base, canonical::TechnologyId technology, int32_t scientistDelta);
StrategicIntentSubmission submitAutoResolveMission(canonical::MissionId mission, canonical::AircraftId missionAircraft, canonical::AircraftId interceptorAircraft);
StrategicIntentSubmission submitBuildBase(StrategicPosition position, const char* name);
StrategicIntentSubmission submitBuildFacility(canonical::BaseId base, const char* facilityDefinition, int32_t column, int32_t row);
StrategicIntentSubmission submitBuildInstallation(StrategicPosition position, const char* installationDefinition, const char* name);
StrategicIntentSubmission submitBuyAircraft(canonical::BaseId base, const char* aircraftDefinition);
StrategicIntentSubmission submitBuyItem(canonical::BaseId base, canonical::ItemId item, int32_t count);
StrategicIntentSubmission submitBuyUGV(canonical::BaseId base, const char* ugvDefinition);
StrategicIntentSubmission submitChangeAircraftHomebase(canonical::AircraftId aircraft, canonical::BaseId base);
StrategicIntentSubmission submitDecreaseProduction(canonical::BaseId base, canonical::ProductionId production, int32_t amount);
StrategicIntentSubmission submitDeequipEmployee(canonical::BaseId base, canonical::EmployeeId employee);
StrategicIntentSubmission submitDeleteEmployee(canonical::EmployeeId employee);
StrategicIntentSubmission submitDestroyFacility(canonical::BaseId base, canonical::FacilityId facility);
StrategicIntentSubmission submitDestroyInstallation(canonical::InstallationId installation);
StrategicIntentSubmission submitDestroyStoredUfo(canonical::StoredUfoId storedUfo);
StrategicIntentSubmission submitEquipAircraftItem(canonical::AircraftId aircraft, int32_t slotType, int32_t slotIndex, int32_t zone, canonical::ItemId item);
StrategicIntentSubmission submitEquipBaseDefenceItem(canonical::BaseId base, canonical::InstallationId installation, canonical::DefenceSlotId defenceSlot, canonical::ItemId item);
StrategicIntentSubmission submitHireOrFireEmployee(canonical::BaseId base, canonical::EmployeeId employee, bool hire);
StrategicIntentSubmission submitIncreaseProduction(canonical::BaseId base, canonical::ProductionId production, int32_t amount);
StrategicIntentSubmission submitCreateProduction(canonical::BaseId base, int32_t subjectKind, canonical::ItemId item, canonical::StoredUfoId storedUfo, const char* aircraftDefinition, int32_t amount);
StrategicIntentSubmission submitKillContainedAlien(canonical::BaseId base, canonical::TechnologyId technology);
StrategicIntentSubmission submitKillContainedAliens(canonical::BaseId base);
StrategicIntentSubmission submitLoadGame(const char* slot);
StrategicIntentSubmission submitLoadLastSave(const char* resolvedSlot);
StrategicIntentSubmission submitMaxAssignResearch(canonical::BaseId base, canonical::TechnologyId technology);
StrategicIntentSubmission submitMoveProductionDown(canonical::BaseId base, canonical::ProductionId production);
StrategicIntentSubmission submitMoveProductionUp(canonical::BaseId base, canonical::ProductionId production);
StrategicIntentSubmission submitPursueUfo(canonical::AircraftId aircraft, canonical::AircraftId ufo);
StrategicIntentSubmission submitRemoveAircraftItem(canonical::AircraftId aircraft, int32_t slotType, int32_t slotIndex, int32_t zone);
StrategicIntentSubmission submitRemoveBaseDefenceItem(canonical::BaseId base, canonical::InstallationId installation, canonical::DefenceSlotId defenceSlot);
StrategicIntentSubmission submitRenameAircraft(canonical::AircraftId aircraft, const char* name);
StrategicIntentSubmission submitRenameBase(canonical::BaseId base, const char* name);
StrategicIntentSubmission submitRenameEmployee(canonical::EmployeeId employee, const char* name);
StrategicIntentSubmission submitRenameInstallation(canonical::InstallationId installation, const char* name);
StrategicIntentSubmission submitSaveGame(const char* slot, const char* comment);
StrategicIntentSubmission submitSellAircraft(canonical::AircraftId aircraft);
StrategicIntentSubmission submitSellItem(canonical::BaseId base, canonical::ItemId item, int32_t count);
StrategicIntentSubmission submitSellUGV(canonical::EmployeeId employee);
StrategicIntentSubmission submitSetAirDefenceAutoFire(canonical::BaseId base, canonical::InstallationId installation, bool enabled);
StrategicIntentSubmission submitSetAirDefenceTarget(canonical::BaseId base, canonical::InstallationId installation, canonical::AircraftId ufo);
StrategicIntentSubmission submitSetAircraftDestination(canonical::AircraftId aircraft, StrategicPosition position);
StrategicIntentSubmission submitSetAutoSellPolicy(canonical::ItemId item, bool enabled);
StrategicIntentSubmission submitSetEmployeeSkin(canonical::EmployeeId employee, int32_t bodySkin);
StrategicIntentSubmission submitSetProductionAmount(canonical::BaseId base, canonical::ProductionId production, int32_t amount);
StrategicIntentSubmission submitStartAircraft(canonical::AircraftId aircraft);
StrategicIntentSubmission submitStartMission(canonical::MissionId mission, canonical::AircraftId aircraft);
StrategicIntentSubmission submitStartTransfer(const StrategicTransferManifest& manifest);
StrategicIntentSubmission submitStopAircraft(canonical::AircraftId aircraft);
StrategicIntentSubmission submitStopProduction(canonical::BaseId base, canonical::ProductionId production);
StrategicIntentSubmission submitStopResearch(canonical::BaseId base, canonical::TechnologyId technology);
StrategicIntentSubmission submitStoreRecoveredUfo(canonical::UfoRecoveryId recovery, canonical::InstallationId installation);
StrategicIntentSubmission submitTransferStoredUfo(canonical::StoredUfoId storedUfo, canonical::InstallationId installation);

bool pollStrategicIntentResult(StrategicIntentResult* result);
namespace legacy { bool tryPopStrategicIntent(StrategicIntent* intent); bool takeTransferManifest(canonical::TransferManifestId manifest, StrategicTransferManifest* value); void publishStrategicIntentResult(const StrategicIntentResult& result); void resetStrategicIntentRuntime(); }
} // intent
} } // ufo::presentation

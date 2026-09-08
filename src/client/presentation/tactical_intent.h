/**
 * @file
 * @brief Complete C++11-compatible tactical authoritative intent surface from strict command + direct protocol inventory.
 */
#pragma once
#include "canonical_identity.h"
#include <cstdint>
#include <type_traits>
namespace ufo { namespace presentation {
enum class TacticalIntentKind : uint8_t {
    SetReactionFire = 1,
    SetReservedTimeUnits = 2,
    AbortMission = 3,
    ClearShotReservation = 4,
    EndTurn = 5,
    MoveActor = 6,
    Reload = 7,
    SelectReactionFireMode = 8,
    SetCrouchState = 9,
    SetShotReservation = 10,
    Shoot = 11,
    Use = 12,
    UseHeadgear = 13,
    TurnActor = 14,
    InventoryMove = 15
};
enum class TacticalIntentDisposition : uint8_t { ForwardedToServer = 1, RejectedByClientBoundary = 2 };
struct TacticalIntent {
    uint64_t sequence;
    TacticalIntentKind kind;
    canonical::EntityId entity;
    canonical::EntityId targetEntity;
    int32_t value0, value1, value2, value3, value4, value5, value6;
};
struct TacticalIntentSubmission { uint64_t sequence; bool accepted; };
struct TacticalIntentResult { uint64_t sequence; TacticalIntentKind kind; TacticalIntentDisposition disposition; canonical::EntityId entity; };
static_assert(std::is_standard_layout<TacticalIntent>::value,"TacticalIntent must remain standard-layout");
static_assert(std::is_trivially_copyable<TacticalIntent>::value,"TacticalIntent must remain trivially copyable");
namespace tactical_intent {
TacticalIntentSubmission submitSetReactionFire(canonical::EntityId entity, bool enabled);
TacticalIntentSubmission submitSetReservedTimeUnits(canonical::EntityId entity, int32_t shotTus, int32_t crouchTus);
TacticalIntentSubmission submitAbortMission();
TacticalIntentSubmission submitClearShotReservation(canonical::EntityId entity, int32_t crouchTus);
TacticalIntentSubmission submitEndTurn();
TacticalIntentSubmission submitMoveActor(canonical::EntityId entity, int32_t x, int32_t y, int32_t z);
TacticalIntentSubmission submitReload(canonical::EntityId entity, int32_t containerId);
TacticalIntentSubmission submitSelectReactionFireMode(canonical::EntityId entity, int32_t hand, int32_t fireMode, int32_t weaponIndex);
TacticalIntentSubmission submitSetCrouchState(canonical::EntityId entity, bool crouched);
TacticalIntentSubmission submitSetShotReservation(canonical::EntityId entity, int32_t shotTus, int32_t crouchTus);
TacticalIntentSubmission submitShoot(canonical::EntityId entity, int32_t x, int32_t y, int32_t z, int32_t shotType, int32_t fireMode, int32_t targetingAlign);
TacticalIntentSubmission submitUse(canonical::EntityId entity, canonical::EntityId targetEntity);
TacticalIntentSubmission submitUseHeadgear(canonical::EntityId entity);
TacticalIntentSubmission submitTurnActor(canonical::EntityId entity, int32_t direction);
TacticalIntentSubmission submitInventoryMove(canonical::EntityId entity, int32_t fromContainer, int32_t fromX, int32_t fromY, int32_t toContainer, int32_t toX, int32_t toY);
bool pollTacticalIntentResult(TacticalIntentResult* result);
namespace legacy { bool tryPopTacticalIntent(TacticalIntent* intent); void publishTacticalIntentResult(const TacticalIntentResult& result); void resetTacticalIntentRuntime(); }
} } }

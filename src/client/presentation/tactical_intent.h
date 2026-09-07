/**
 * @file
 * @brief C++11-compatible typed tactical presentation intent contract.
 */
#pragma once

#include "canonical_identity.h"

#include <cstdint>
#include <type_traits>

namespace ufo {
namespace presentation {

enum class TacticalIntentKind : uint8_t {
	SetReactionFire = 1,
	SetReservedTimeUnits = 2
};

enum class TacticalIntentDisposition : uint8_t {
	ForwardedToServer = 1,
	RejectedByClientBoundary = 2
};

struct TacticalIntent {
	uint64_t sequence;
	TacticalIntentKind kind;
	canonical::EntityId entity;
	int32_t value0;
	int32_t value1;
};

struct TacticalIntentSubmission {
	uint64_t sequence;
	bool accepted;
};

struct TacticalIntentResult {
	uint64_t sequence;
	TacticalIntentKind kind;
	TacticalIntentDisposition disposition;
	canonical::EntityId entity;
};

static_assert(std::is_standard_layout<TacticalIntent>::value,
	"TacticalIntent must remain standard-layout");
static_assert(std::is_trivially_copyable<TacticalIntent>::value,
	"TacticalIntent must remain trivially copyable");
static_assert(std::is_standard_layout<TacticalIntentResult>::value,
	"TacticalIntentResult must remain standard-layout");
static_assert(std::is_trivially_copyable<TacticalIntentResult>::value,
	"TacticalIntentResult must remain trivially copyable");

namespace tactical_intent {

/**
 * Queue a reaction-fire state request for a canonical tactical actor.
 *
 * ForwardedToServer means only that the existing PA_STATE request was emitted.
 * The game server remains authoritative and the resulting tactical event /
 * publication is the canonical confirmation.
 */
TacticalIntentSubmission submitSetReactionFire(canonical::EntityId entity, bool enabled);

/**
 * Queue shot/crouch TU reservation values for a canonical tactical actor.
 *
 * ForwardedToServer means only that the existing PA_RESERVE_STATE request was
 * emitted. The server remains authoritative.
 */
TacticalIntentSubmission submitSetReservedTimeUnits(
	canonical::EntityId entity,
	int32_t shotTus,
	int32_t crouchTus);

bool pollTacticalIntentResult(TacticalIntentResult* result);

namespace legacy {

bool tryPopTacticalIntent(TacticalIntent* intent);
void publishTacticalIntentResult(const TacticalIntentResult& result);
void resetTacticalIntentRuntime();

} // namespace legacy
} // namespace tactical_intent
} // namespace presentation
} // namespace ufo

/**
 * @file
 * @brief Immutable value-only tactical state published to presentation consumers.
 */
#pragma once

#include "canonical_identity.h"

#include <cstdint>
#include <type_traits>
#include <utility>
#include <vector>

namespace ufo {
namespace presentation {

struct GridPosition {
	uint8_t x;
	uint8_t y;
	uint8_t z;
};

struct TacticalActorView {
	canonical::EntityId entity;
	GridPosition gridPosition;
	GridPosition previousGridPosition;
	int32_t team;
	int32_t playerNumber;
	int32_t characterUcn;
	int32_t timeUnits;
	int32_t maxTimeUnits;
	int32_t hitPoints;
	int32_t maxHitPoints;
	int32_t stun;
	int32_t morale;
	int32_t maxMorale;
	uint16_t stateFlags;
	int32_t fieldSize;
};

class TacticalSnapshot {
public:
	TacticalSnapshot() noexcept : publicationSerial_(0) {}

	TacticalSnapshot(uint64_t publicationSerial, std::vector<TacticalActorView> actors) :
		publicationSerial_(publicationSerial),
		actors_(std::move(actors))
	{
	}

	uint64_t publicationSerial() const noexcept
	{
		return publicationSerial_;
	}

	const std::vector<TacticalActorView>& actors() const noexcept
	{
		return actors_;
	}

private:
	uint64_t publicationSerial_;
	std::vector<TacticalActorView> actors_;
};

static_assert(sizeof(GridPosition) == 3, "presentation grid positions must preserve the canonical three-byte grid coordinates");
static_assert(sizeof(decltype(TacticalActorView::stateFlags)) == sizeof(uint16_t), "tactical state flags must remain a 16-bit canonical protocol value");
static_assert(std::is_standard_layout<TacticalActorView>::value, "tactical actor publication values must remain standard-layout");
static_assert(std::is_trivially_copyable<TacticalActorView>::value, "tactical actor publication values must remain trivially copyable");

} // namespace presentation
} // namespace ufo

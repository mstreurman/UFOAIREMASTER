/**
 * @file
 * @brief Shared value-only strategic world position used by intents and snapshots.
 */
#pragma once

#include <type_traits>

namespace ufo {
namespace presentation {

struct StrategicPosition {
	float longitude;
	float latitude;
	float altitude;
};

static_assert(std::is_standard_layout<StrategicPosition>::value,
	"StrategicPosition must remain standard-layout");
static_assert(std::is_trivially_copyable<StrategicPosition>::value,
	"StrategicPosition must remain trivially copyable");
static_assert(sizeof(StrategicPosition) == sizeof(float) * 3,
	"StrategicPosition must remain exactly three floats");

} // namespace presentation
} // namespace ufo

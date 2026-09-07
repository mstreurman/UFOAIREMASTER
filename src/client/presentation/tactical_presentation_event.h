/**
 * @file
 * @brief Ordered value-only envelope for canonical tactical events exposed to presentation.
 */
#pragma once

#include <cstdint>
#include <limits>
#include <type_traits>

namespace ufo {
namespace presentation {

enum class TacticalPresentationEventKind : uint16_t {
	CanonicalMirrorUpdated = 1
};

struct CanonicalEventTypeId {
	uint16_t value;

	CanonicalEventTypeId() noexcept : value(invalidValue()) {}
	explicit CanonicalEventTypeId(uint16_t value_) noexcept : value(value_) {}

	static constexpr uint16_t invalidValue() noexcept
	{
		return std::numeric_limits<uint16_t>::max();
	}

	bool isValid() const noexcept
	{
		return value != invalidValue();
	}
};

struct TacticalPresentationEventHeader {
	uint64_t sequence;
	uint64_t scheduledPresentationTime;
	TacticalPresentationEventKind kind;
	CanonicalEventTypeId canonicalType;
};

static_assert(std::is_standard_layout<TacticalPresentationEventKind>::value, "tactical presentation event kinds must remain standard-layout");
static_assert(std::is_trivially_copyable<TacticalPresentationEventKind>::value, "tactical presentation event kinds must remain trivially copyable");
static_assert(sizeof(CanonicalEventTypeId) == sizeof(uint16_t), "canonical event type IDs must remain 16-bit value types");
static_assert(std::is_standard_layout<CanonicalEventTypeId>::value, "canonical event type IDs must remain standard-layout");
static_assert(std::is_trivially_copyable<CanonicalEventTypeId>::value, "canonical event type IDs must remain trivially copyable");
static_assert(!std::is_convertible<uint16_t, CanonicalEventTypeId>::value, "canonical event type IDs must not accept implicit integer conversion");
static_assert(std::is_standard_layout<TacticalPresentationEventHeader>::value, "tactical presentation event headers must remain standard-layout");
static_assert(std::is_trivially_copyable<TacticalPresentationEventHeader>::value, "tactical presentation event headers must remain trivially copyable");

} // namespace presentation
} // namespace ufo

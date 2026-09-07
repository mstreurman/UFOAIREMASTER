/**
 * @file
 * @brief Strong value-only identifiers for canonical state exposed to presentation.
 */
#pragma once

#include <cstdint>
#include <limits>
#include <type_traits>

namespace ufo {
namespace canonical {

struct EntityId {
	uint32_t value;

	EntityId() noexcept : value(invalidValue()) {}
	explicit EntityId(uint32_t value_) noexcept : value(value_) {}

	static constexpr uint32_t invalidValue() noexcept
	{
		return std::numeric_limits<uint32_t>::max();
	}

	bool isValid() const noexcept
	{
		return value != invalidValue();
	}
};

inline bool operator==(EntityId lhs, EntityId rhs) noexcept
{
	return lhs.value == rhs.value;
}

inline bool operator!=(EntityId lhs, EntityId rhs) noexcept
{
	return !(lhs == rhs);
}

static_assert(sizeof(EntityId) == sizeof(uint32_t), "canonical EntityId must remain a 32-bit value type");
static_assert(std::is_standard_layout<EntityId>::value, "canonical EntityId must remain standard-layout");
static_assert(std::is_trivially_copyable<EntityId>::value, "canonical EntityId must remain trivially copyable");
static_assert(!std::is_convertible<uint32_t, EntityId>::value, "canonical EntityId must not accept implicit integer conversion");

} // namespace canonical
} // namespace ufo

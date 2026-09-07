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

/**
 * Stable strategic identities cross the canonical/presentation boundary by
 * value.  They are not save-format IDs and do not imply a legacy storage
 * layout.  The strategic adapter owns translation from legacy campaign state
 * and, where necessary, generation-safe mapping for the campaign/load
 * lifetime described by Architecture 078.
 */
namespace detail {

template<typename DomainTag>
struct StableId {
	uint32_t value;

	StableId() noexcept : value(invalidValue()) {}
	explicit StableId(uint32_t value_) noexcept : value(value_) {}

	static constexpr uint32_t invalidValue() noexcept
	{
		return std::numeric_limits<uint32_t>::max();
	}

	bool isValid() const noexcept
	{
		return value != invalidValue();
	}
};

template<typename DomainTag>
inline bool operator==(StableId<DomainTag> lhs, StableId<DomainTag> rhs) noexcept
{
	return lhs.value == rhs.value;
}

template<typename DomainTag>
inline bool operator!=(StableId<DomainTag> lhs, StableId<DomainTag> rhs) noexcept
{
	return !(lhs == rhs);
}

struct MissionIdTag;
struct AircraftIdTag;
struct BaseIdTag;
struct InstallationIdTag;
struct NationIdTag;
struct EmployeeIdTag;
struct TechnologyIdTag;
struct ProductionIdTag;
struct MessageIdTag;
struct ItemIdTag;

} // namespace detail

using MissionId = detail::StableId<detail::MissionIdTag>;
using AircraftId = detail::StableId<detail::AircraftIdTag>;
using BaseId = detail::StableId<detail::BaseIdTag>;
using InstallationId = detail::StableId<detail::InstallationIdTag>;
using NationId = detail::StableId<detail::NationIdTag>;
using EmployeeId = detail::StableId<detail::EmployeeIdTag>;
using TechnologyId = detail::StableId<detail::TechnologyIdTag>;
using ProductionId = detail::StableId<detail::ProductionIdTag>;
using MessageId = detail::StableId<detail::MessageIdTag>;
using ItemId = detail::StableId<detail::ItemIdTag>;

#define UFOAI_CANONICAL_ID_CONTRACT(TypeName) \
	static_assert(sizeof(TypeName) == sizeof(uint32_t), #TypeName " must remain a 32-bit value type"); \
	static_assert(std::is_standard_layout<TypeName>::value, #TypeName " must remain standard-layout"); \
	static_assert(std::is_trivially_copyable<TypeName>::value, #TypeName " must remain trivially copyable"); \
	static_assert(!std::is_convertible<uint32_t, TypeName>::value, #TypeName " must not accept implicit integer conversion")

UFOAI_CANONICAL_ID_CONTRACT(MissionId);
UFOAI_CANONICAL_ID_CONTRACT(AircraftId);
UFOAI_CANONICAL_ID_CONTRACT(BaseId);
UFOAI_CANONICAL_ID_CONTRACT(InstallationId);
UFOAI_CANONICAL_ID_CONTRACT(NationId);
UFOAI_CANONICAL_ID_CONTRACT(EmployeeId);
UFOAI_CANONICAL_ID_CONTRACT(TechnologyId);
UFOAI_CANONICAL_ID_CONTRACT(ProductionId);
UFOAI_CANONICAL_ID_CONTRACT(MessageId);
UFOAI_CANONICAL_ID_CONTRACT(ItemId);

#undef UFOAI_CANONICAL_ID_CONTRACT

} // namespace canonical
} // namespace ufo

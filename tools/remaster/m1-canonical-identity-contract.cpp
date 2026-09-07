/**
 * @file
 * @brief Standalone C++11 contract test for M1 canonical presentation identities.
 */

#include "src/client/presentation/canonical_identity.h"

#include <cstdint>
#include <iostream>
#include <type_traits>

namespace {

template<typename Needle, typename... Haystack>
struct Contains;

template<typename Needle>
struct Contains<Needle> : std::false_type {};

template<typename Needle, typename Head, typename... Tail>
struct Contains<Needle, Head, Tail...>
	: std::integral_constant<bool,
		std::is_same<Needle, Head>::value || Contains<Needle, Tail...>::value> {};

template<typename Id>
struct IdentityShape
	: std::integral_constant<bool,
		sizeof(Id) == sizeof(uint32_t)
		&& std::is_standard_layout<Id>::value
		&& std::is_trivially_copyable<Id>::value
		&& !std::is_pointer<Id>::value
		&& !std::is_convertible<uint32_t, Id>::value> {};

template<typename Target, typename... Sources>
struct NoCrossConstructionFrom;

template<typename Target>
struct NoCrossConstructionFrom<Target> : std::true_type {};

template<typename Target, typename Head, typename... Tail>
struct NoCrossConstructionFrom<Target, Head, Tail...>
	: std::integral_constant<bool,
		!std::is_constructible<Target, Head>::value
		&& !std::is_constructible<Head, Target>::value
		&& NoCrossConstructionFrom<Target, Tail...>::value> {};

template<typename... Types>
struct AllCrossNonConstructible;

template<>
struct AllCrossNonConstructible<> : std::true_type {};

template<typename Head, typename... Tail>
struct AllCrossNonConstructible<Head, Tail...>
	: std::integral_constant<bool,
		NoCrossConstructionFrom<Head, Tail...>::value
		&& AllCrossNonConstructible<Tail...>::value> {};

template<typename... Types>
struct AllDistinct;

template<>
struct AllDistinct<> : std::true_type {};

template<typename Head, typename... Tail>
struct AllDistinct<Head, Tail...>
	: std::integral_constant<bool,
		!Contains<Head, Tail...>::value && AllDistinct<Tail...>::value> {};

template<typename Id>
bool checkId(uint32_t sample)
{
	const Id invalid;
	if (invalid.isValid() || invalid.value != Id::invalidValue())
		return false;

	const Id first(sample);
	const Id same(sample);
	const Id different(sample + 1U);
	return first.isValid()
		&& first.value == sample
		&& first == same
		&& first != different;
}

} // namespace

int main()
{
	using namespace ufo::canonical;

	static_assert(AllDistinct<
		EntityId,
		MissionId,
		AircraftId,
		BaseId,
		InstallationId,
		NationId,
		EmployeeId,
		TechnologyId,
		ProductionId,
		MessageId,
		ItemId>::value,
		"canonical presentation identity domains must remain distinct types");

	static_assert(IdentityShape<EntityId>::value, "EntityId shape contract failed");
	static_assert(IdentityShape<MissionId>::value, "MissionId shape contract failed");
	static_assert(IdentityShape<AircraftId>::value, "AircraftId shape contract failed");
	static_assert(IdentityShape<BaseId>::value, "BaseId shape contract failed");
	static_assert(IdentityShape<InstallationId>::value, "InstallationId shape contract failed");
	static_assert(IdentityShape<NationId>::value, "NationId shape contract failed");
	static_assert(IdentityShape<EmployeeId>::value, "EmployeeId shape contract failed");
	static_assert(IdentityShape<TechnologyId>::value, "TechnologyId shape contract failed");
	static_assert(IdentityShape<ProductionId>::value, "ProductionId shape contract failed");
	static_assert(IdentityShape<MessageId>::value, "MessageId shape contract failed");
	static_assert(IdentityShape<ItemId>::value, "ItemId shape contract failed");

	static_assert(AllCrossNonConstructible<
		EntityId,
		MissionId,
		AircraftId,
		BaseId,
		InstallationId,
		NationId,
		EmployeeId,
		TechnologyId,
		ProductionId,
		MessageId,
		ItemId>::value,
		"canonical presentation identity domains must reject cross-domain construction");

	static_assert(!std::is_convertible<MissionId, AircraftId>::value,
		"MissionId must not convert to AircraftId");
	static_assert(!std::is_convertible<AircraftId, BaseId>::value,
		"AircraftId must not convert to BaseId");
	static_assert(!std::is_convertible<BaseId, InstallationId>::value,
		"BaseId must not convert to InstallationId");
	static_assert(!std::is_convertible<TechnologyId, ProductionId>::value,
		"TechnologyId must not convert to ProductionId");
	static_assert(!std::is_convertible<ItemId, TechnologyId>::value,
		"ItemId must not convert to TechnologyId");

	const bool ok =
		checkId<EntityId>(1U)
		&& checkId<MissionId>(2U)
		&& checkId<AircraftId>(3U)
		&& checkId<BaseId>(4U)
		&& checkId<InstallationId>(5U)
		&& checkId<NationId>(6U)
		&& checkId<EmployeeId>(7U)
		&& checkId<TechnologyId>(8U)
		&& checkId<ProductionId>(9U)
		&& checkId<MessageId>(10U)
		&& checkId<ItemId>(11U);

	if (!ok) {
		std::cerr << "M1 canonical identity contract: FAIL\n";
		return 1;
	}

	std::cout << "M1 canonical identity contract: PASS (11 distinct 32-bit domains)\n";
	return 0;
}

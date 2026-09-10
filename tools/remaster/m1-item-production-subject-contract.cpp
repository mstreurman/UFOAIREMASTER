/**
 * @file
 * @brief M1 ItemId + production-subject public contract.
 */
#include "src/client/presentation/strategic_snapshot.h"

#include <iostream>
#include <type_traits>
#include <utility>
#include <vector>

using namespace ufo::presentation;

static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().itemDefinitions()),
	const std::vector<StrategicItemDefinitionView>&>::value,
	"item definition publication must be const-only");

static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().aircraftDefinitions()),
	const std::vector<StrategicAircraftDefinitionView>&>::value,
	"aircraft definition publication must be const-only");

int main()
{
	StrategicItemDefinitionView item;
	item.id = ufo::canonical::ItemId(7);
	item.technology = ufo::canonical::TechnologyId(3);
	item.scriptId = "laser_rifle";
	item.name = "Laser Rifle";

	StrategicAircraftDefinitionView aircraft;
	aircraft.technology = ufo::canonical::TechnologyId(4);
	aircraft.scriptId = "craft_stiletto";
	aircraft.name = "Stiletto";

	StrategicProductionView itemProduction;
	itemProduction.item = item.id;
	itemProduction.storedUfo = ufo::canonical::StoredUfoId();
	itemProduction.aircraftDefinition.clear();

	StrategicProductionView aircraftProduction;
	aircraftProduction.item = ufo::canonical::ItemId();
	aircraftProduction.storedUfo = ufo::canonical::StoredUfoId();
	aircraftProduction.aircraftDefinition = aircraft.scriptId;

	StrategicProductionView disassembly;
	disassembly.item = ufo::canonical::ItemId();
	disassembly.storedUfo = ufo::canonical::StoredUfoId(99);
	disassembly.aircraftDefinition.clear();

	if (item.id.value != 7U || item.scriptId != "laser_rifle")
		return 1;
	if (aircraft.scriptId != "craft_stiletto")
		return 2;
	if (itemProduction.item.value != 7U || itemProduction.storedUfo.isValid()
			|| !itemProduction.aircraftDefinition.empty())
		return 3;
	if (aircraftProduction.item.isValid() || aircraftProduction.storedUfo.isValid()
			|| aircraftProduction.aircraftDefinition != "craft_stiletto")
		return 4;
	if (disassembly.item.isValid() || disassembly.storedUfo.value != 99U
			|| !disassembly.aircraftDefinition.empty())
		return 5;

	std::cout << "M1 ItemId + production subject public contract: PASS\n";
	return 0;
}

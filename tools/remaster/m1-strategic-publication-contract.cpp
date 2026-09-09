/**
 * @file
 * @brief Standalone C++11 contract test for immutable strategic snapshots.
 */

#include "src/client/presentation/strategic_snapshot.h"

#include <cstdint>
#include <iostream>
#include <memory>
#include <type_traits>
#include <utility>
#include <vector>

namespace {

using namespace ufo::presentation;

static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().missions()),
	const std::vector<StrategicMissionView>&>::value,
	"mission publication must be const-only");
static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().aircraft()),
	const std::vector<StrategicAircraftView>&>::value,
	"aircraft publication must be const-only");
static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().bases()),
	const std::vector<StrategicBaseView>&>::value,
	"base publication must be const-only");
static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().installations()),
	const std::vector<StrategicInstallationView>&>::value,
	"installation publication must be const-only");
static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().nations()),
	const std::vector<StrategicNationView>&>::value,
	"nation publication must be const-only");
static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().technologies()),
	const std::vector<StrategicTechnologyView>&>::value,
	"technology publication must be const-only");
static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().productions()),
	const std::vector<StrategicProductionView>&>::value,
	"production publication must be const-only");
static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().storedUfos()),
	const std::vector<StrategicStoredUfoView>&>::value,
	"stored UFO publication must be const-only");
static_assert(std::is_same<
	decltype(std::declval<const StrategicSnapshot&>().messages()),
	const std::vector<StrategicMessageView>&>::value,
	"message publication must be const-only");

StrategicSnapshot makeSnapshot(uint64_t serial, int32_t credits, const char* aircraftName)
{
	StrategicSelectionView selection;
	selection.mission = ufo::canonical::MissionId(10);
	selection.aircraft = ufo::canonical::AircraftId(20);

	StrategicMissionView mission;
	mission.id = ufo::canonical::MissionId(10);
	mission.position = StrategicPosition{1.0f, 2.0f, 0.0f};
	mission.category = 3;
	mission.stage = 4;
	mission.active = true;
	mission.onGeoscape = true;
	mission.crashed = false;

	StrategicAircraftView aircraft;
	aircraft.id = ufo::canonical::AircraftId(20);
	aircraft.position = StrategicPosition{5.0f, 6.0f, 7.0f};
	aircraft.status = 8;
	aircraft.fuel = 9;
	aircraft.damage = 10;
	aircraft.ufo = false;
	aircraft.detected = true;
	aircraft.landed = false;
	aircraft.hiddenFromGeoscape = false;
	aircraft.name = aircraftName;

	StrategicBaseView base;
	base.id = ufo::canonical::BaseId(30);
	base.position = StrategicPosition{11.0f, 12.0f, 13.0f};
	base.status = 1;
	base.alienInterest = 0.25f;
	base.founded = true;
	base.selected = true;
	base.name = "Alpha";

	StrategicInstallationView installation;
	installation.id = ufo::canonical::InstallationId(40);
	installation.position = StrategicPosition{14.0f, 15.0f, 16.0f};
	installation.status = 2;
	installation.type = 1;
	installation.damage = 3;
	installation.maxDamage = 100;
	installation.alienInterest = 0.5f;
	installation.selected = false;
	installation.name = "Radar";

	StrategicNationView nation;
	nation.id = ufo::canonical::NationId(50);
	nation.position = StrategicPosition{17.0f, 18.0f, 0.0f};
	nation.happiness = 0.75f;
	nation.xviInfection = 2;
	nation.maxFunding = 1000;
	nation.scriptId = "nation_x";
	nation.name = "Nation X";

	StrategicTechnologyView technology;
	technology.id = ufo::canonical::TechnologyId(70);
	technology.base = ufo::canonical::BaseId(30);
	technology.status = 1;
	technology.researchable = true;
	technology.collected = true;
	technology.scientists = 4;
	technology.time = 12.0f;
	technology.overallTime = 20.0f;
	technology.name = "Laser";

	StrategicProductionView production;
	production.id = ufo::canonical::ProductionId(80);
	production.base = ufo::canonical::BaseId(30);
	production.technology = ufo::canonical::TechnologyId(70);
	production.queueIndex = 2;
	production.type = 0;
	production.amount = 5;
	production.frame = 10;
	production.totalFrames = 100;

	StrategicStoredUfoView storedUfo;
	storedUfo.id = ufo::canonical::StoredUfoId(90);
	storedUfo.installation = ufo::canonical::InstallationId(40);
	storedUfo.status = 1;
	storedUfo.condition = 0.75f;
	storedUfo.disassembling = false;
	storedUfo.ufoDefinition = "craft_ufo_scout";

	StrategicMessageView message;
	message.id = ufo::canonical::MessageId(60);
	message.time = StrategicCampaignTime{7, 123};
	message.type = 4;
	message.title = "Title";
	message.text = "Body";
	message.iconName = "icons/message_info";

	return StrategicSnapshot(
		serial,
		StrategicCampaignTime{6, 321},
		credits,
		5,
		selection,
		std::vector<StrategicMissionView>(1, mission),
		std::vector<StrategicAircraftView>(1, aircraft),
		std::vector<StrategicBaseView>(1, base),
		std::vector<StrategicInstallationView>(1, installation),
		std::vector<StrategicNationView>(1, nation),
		std::vector<StrategicTechnologyView>(1, technology),
		std::vector<StrategicProductionView>(1, production),
		std::vector<StrategicStoredUfoView>(1, storedUfo),
		std::vector<StrategicMessageView>(1, message));
}

} // namespace

int main()
{
	using namespace ufo::presentation;

	std::shared_ptr<const StrategicSnapshot> first =
		std::make_shared<const StrategicSnapshot>(makeSnapshot(1, 100, "Stiletto"));
	std::shared_ptr<const StrategicSnapshot> second =
		std::make_shared<const StrategicSnapshot>(makeSnapshot(2, 200, "Firebird"));

	if (first->publicationSerial() != 1 || second->publicationSerial() != 2)
		return 1;
	if (first->credits() != 100 || second->credits() != 200)
		return 2;
	if (first->aircraft().at(0).name != "Stiletto")
		return 3;
	if (second->aircraft().at(0).name != "Firebird")
		return 4;
	if (first->missions().at(0).id.value != 10U)
		return 5;
	if (first->bases().at(0).id.value != 30U)
		return 6;
	if (first->installations().at(0).id.value != 40U)
		return 7;
	if (first->nations().at(0).id.value != 50U)
		return 8;
	if (first->messages().at(0).id.value != 60U)
		return 9;
	if (first->technologies().at(0).id.value != 70U)
		return 10;
	if (first->technologies().at(0).base.value != 30U)
		return 11;
	if (first->productions().at(0).id.value != 80U)
		return 12;
	if (first->productions().at(0).base.value != 30U)
		return 13;
	if (first->productions().at(0).technology.value != 70U)
		return 14;
	if (first->productions().at(0).queueIndex != 2)
		return 15;
	if (first->storedUfos().at(0).id.value != 90U)
		return 16;
	if (first->storedUfos().at(0).installation.value != 40U)
		return 17;
	if (first->storedUfos().at(0).ufoDefinition != "craft_ufo_scout")
		return 18;

	std::cout << "M1 strategic snapshot contract: PASS (immutable value-only root categories + research/production/stored-UFO)\n";
	return 0;
}

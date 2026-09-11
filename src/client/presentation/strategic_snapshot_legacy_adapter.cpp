/**
 * @file
 * @brief Legacy campaign -> immutable strategic snapshot projection.
 */

#include "../cl_shared.h"
#include "../cgame/campaign/cp_campaign.h"
#include "../cgame/campaign/cp_employee.h"
#include "../cgame/campaign/cp_messages.h"
#include "../cgame/campaign/cp_missions.h"
#include "../cgame/campaign/cp_uforecovery.h"
#include "strategic_snapshot_legacy_adapter.h"

#include <cstdint>
#include <cstddef>
#include <map>
#include <string>
#include <utility>
#include <vector>

namespace ufo {
namespace presentation {
namespace legacy {
namespace {

const uint32_t UFO_AIRCRAFT_ID_BIT = 0x80000000u;
std::map<const uiMessageListNodeMessage_t*, canonical::MessageId> messageIds;
uint32_t nextMessageId = 0;

template<typename Id>
Id indexedId(int idx)
{
	if (idx < 0)
		return Id();
	return Id(static_cast<uint32_t>(idx));
}

canonical::AircraftId aircraftId(const aircraft_t* aircraft, bool ufo)
{
	if (!aircraft || aircraft->idx < 0)
		return canonical::AircraftId();
	const uint32_t value = static_cast<uint32_t>(aircraft->idx);
	if ((value & UFO_AIRCRAFT_ID_BIT) != 0)
		return canonical::AircraftId();
	return canonical::AircraftId(ufo ? (value | UFO_AIRCRAFT_ID_BIT) : value);
}

canonical::MessageId messageId(const uiMessageListNodeMessage_t* message)
{
	const std::map<const uiMessageListNodeMessage_t*, canonical::MessageId>::const_iterator found = messageIds.find(message);
	if (found != messageIds.end())
		return found->second;

	if (nextMessageId == canonical::MessageId::invalidValue())
		return canonical::MessageId();
	const canonical::MessageId id(nextMessageId++);
	messageIds.insert(std::make_pair(message, id));
	return id;
}

StrategicPosition position3(const float* pos)
{
	StrategicPosition out = {pos[0], pos[1], pos[2]};
	return out;
}

StrategicPosition position2(const float* pos)
{
	StrategicPosition out = {pos[0], pos[1], 0.0f};
	return out;
}

StrategicCampaignTime campaignTime(const DateTime& date)
{
	StrategicCampaignTime out = {
		static_cast<int32_t>(date.getDateAsDays()),
		static_cast<int32_t>(date.getTimeAsSeconds())
	};
	return out;
}

std::string valueString(const char* value)
{
	return value ? std::string(value) : std::string();
}

StrategicMissionView projectMission(const mission_t& mission)
{
	StrategicMissionView out;
	out.id = indexedId<canonical::MissionId>(mission.idx);
	out.position = position2(mission.pos);
	out.category = static_cast<int32_t>(mission.category);
	out.stage = static_cast<int32_t>(mission.stage);
	out.active = mission.active;
	out.onGeoscape = mission.onGeoscape;
	out.crashed = mission.crashed;
	return out;
}

StrategicAircraftView projectAircraft(const aircraft_t& aircraft, bool ufo)
{
	StrategicAircraftView out;
	out.id = aircraftId(&aircraft, ufo);
	out.homeBase = aircraft.homebase ? indexedId<canonical::BaseId>(aircraft.homebase->idx) : canonical::BaseId();
	out.mission = aircraft.mission ? indexedId<canonical::MissionId>(aircraft.mission->idx) : canonical::MissionId();
	out.position = position3(aircraft.pos);
	out.status = static_cast<int32_t>(aircraft.status);
	out.fuel = aircraft.fuel;
	out.damage = aircraft.damage;
	out.ufo = ufo;
	out.detected = aircraft.detected;
	out.landed = aircraft.landed;
	out.hiddenFromGeoscape = aircraft.notOnGeoscape;
	out.name = valueString(aircraft.name);
	return out;
}

StrategicBaseView projectBase(const base_t& base)
{
	StrategicBaseView out;
	out.id = indexedId<canonical::BaseId>(base.idx);
	out.position = position3(base.pos);
	out.status = static_cast<int32_t>(base.baseStatus);
	out.alienInterest = base.alienInterest;
	out.founded = base.founded;
	out.selected = base.selected;
	out.name = valueString(base.name);
	return out;
}

StrategicFacilityView projectFacility(const base_t& base, const building_t& facility)
{
	StrategicFacilityView out;
	out.id = canonical::FacilityId(B_GetFacilityRuntimeId(&facility));
	out.base = indexedId<canonical::BaseId>(base.idx);
	out.column = static_cast<int32_t>(facility.pos[0]);
	out.row = static_cast<int32_t>(facility.pos[1]);
	out.status = static_cast<int32_t>(facility.buildingStatus);
	out.definition = valueString(facility.id);
	return out;
}

StrategicInstallationView projectInstallation(const installation_t& installation)
{
	StrategicInstallationView out;
	out.id = indexedId<canonical::InstallationId>(installation.idx);
	out.position = position3(installation.pos);
	out.status = static_cast<int32_t>(installation.installationStatus);
	out.type = installation.installationTemplate
		? static_cast<int32_t>(installation.installationTemplate->type)
		: -1;
	out.damage = installation.installationDamage;
	out.maxDamage = installation.installationTemplate ? installation.installationTemplate->maxDamage : 0;
	out.alienInterest = installation.alienInterest;
	out.selected = installation.selected;
	out.name = valueString(installation.name);
	return out;
}

StrategicNationView projectNation(const nation_t& nation)
{
	StrategicNationView out;
	out.id = indexedId<canonical::NationId>(nation.idx);
	out.position = position2(nation.pos);
	const nationInfo_t* info = NAT_GetCurrentMonthInfo(&nation);
	out.happiness = info ? info->happiness : 0.0f;
	out.xviInfection = info ? info->xviInfection : 0;
	out.maxFunding = nation.maxFunding;
	out.scriptId = valueString(nation.id);
	out.name = valueString(nation.name);
	return out;
}

StrategicTechnologyView projectTechnology(const technology_t& technology)
{
	StrategicTechnologyView out;
	out.id = indexedId<canonical::TechnologyId>(technology.idx);
	out.base = technology.base
		? indexedId<canonical::BaseId>(technology.base->idx)
		: canonical::BaseId();
	out.status = static_cast<int32_t>(technology.statusResearch);
	out.researchable = technology.statusResearchable;
	out.collected = technology.statusCollected;
	out.scientists = technology.scientists;
	out.time = technology.time;
	out.overallTime = technology.overallTime;
	out.name = valueString(technology.name);
	return out;
}

StrategicItemDefinitionView projectItemDefinition(const objDef_t& item)
{
	StrategicItemDefinitionView out;
	out.id = indexedId<canonical::ItemId>(item.idx);
	const technology_t* technology = nullptr;
	if (item.idx >= 0 && item.idx < static_cast<int>(lengthof(ccs.objDefTechs)))
		technology = ccs.objDefTechs[item.idx];
	out.technology = technology
		? indexedId<canonical::TechnologyId>(technology->idx)
		: canonical::TechnologyId();
	out.scriptId = valueString(item.id);
	out.name = valueString(item.name);
	return out;
}

StrategicAircraftDefinitionView projectAircraftDefinition(const aircraft_t& aircraft)
{
	StrategicAircraftDefinitionView out;
	out.technology = aircraft.tech
		? indexedId<canonical::TechnologyId>(aircraft.tech->idx)
		: canonical::TechnologyId();
	out.scriptId = valueString(aircraft.id);
	out.name = valueString(aircraft.name);
	return out;
}

StrategicProductionView projectProduction(const base_t& base, const production_t& production)
{
	StrategicProductionView out;
	out.id = canonical::ProductionId(PR_GetProductionRuntimeId(&production));
	out.base = indexedId<canonical::BaseId>(base.idx);
	const technology_t* technology = PR_GetTech(&production.data);
	out.technology = technology
		? indexedId<canonical::TechnologyId>(technology->idx)
		: canonical::TechnologyId();
	out.item = canonical::ItemId();
	out.storedUfo = canonical::StoredUfoId();
	out.aircraftDefinition.clear();
	switch (production.data.type) {
	case PRODUCTION_TYPE_ITEM:
		if (production.data.data.item)
			out.item = indexedId<canonical::ItemId>(production.data.data.item->idx);
		break;
	case PRODUCTION_TYPE_AIRCRAFT:
		if (production.data.data.aircraft)
			out.aircraftDefinition = valueString(production.data.data.aircraft->id);
		break;
	case PRODUCTION_TYPE_DISASSEMBLY:
		if (production.data.data.ufo)
			out.storedUfo = indexedId<canonical::StoredUfoId>(production.data.data.ufo->idx);
		break;
	default:
		break;
	}
	out.queueIndex = production.idx;
	out.type = static_cast<int32_t>(production.data.type);
	out.amount = production.amount;
	out.frame = production.frame;
	out.totalFrames = production.totalFrames;
	return out;
}

StrategicStoredUfoView projectStoredUfo(const storedUFO_t& ufo)
{
	StrategicStoredUfoView out;
	out.id = indexedId<canonical::StoredUfoId>(ufo.idx);
	out.installation = ufo.installation
		? indexedId<canonical::InstallationId>(ufo.installation->idx)
		: canonical::InstallationId();
	out.status = static_cast<int32_t>(ufo.status);
	out.condition = ufo.condition;
	out.disassembling = ufo.disassembly != nullptr;
	out.ufoDefinition = valueString(ufo.id);
	return out;
}


StrategicUfoRecoveryView projectUfoRecovery(const ufoRecovery_t* recovery)
{
	StrategicUfoRecoveryView out;
	if (!recovery || !Q_strvalid(recovery->ufoDefinition))
		return out;
	out.id = canonical::UfoRecoveryId(recovery->runtimeId);
	out.condition = recovery->condition;
	out.ufoDefinition = valueString(recovery->ufoDefinition);
	return out;
}

StrategicUfoSaleOfferView projectUfoSaleOffer(const ufoSaleOffer_t& offer)
{
	StrategicUfoSaleOfferView out;
	out.id = canonical::UfoSaleOfferId(offer.runtimeId);
	out.recovery = canonical::UfoRecoveryId(offer.recoveryRuntimeId);
	out.nation = offer.nation ? indexedId<canonical::NationId>(offer.nation->idx) : canonical::NationId();
	out.price = offer.price;
	const ufoRecovery_t* recovery = UR_GetPendingRecovery();
	out.ufoDefinition = recovery && recovery->runtimeId == offer.recoveryRuntimeId
		? valueString(recovery->ufoDefinition) : std::string();
	return out;
}

StrategicEmployeeView projectEmployee(const Employee& employee)
{
	StrategicEmployeeView out;
	out.id = indexedId<canonical::EmployeeId>(employee.chr.ucn);
	out.base = employee.baseHired
		? indexedId<canonical::BaseId>(employee.baseHired->idx)
		: canonical::BaseId();
	const aircraft_t* assignedAircraft = AIR_IsEmployeeInAircraft(&employee, nullptr);
	out.aircraft = aircraftId(assignedAircraft, false);
	out.type = static_cast<int32_t>(employee.getType());
	out.bodySkin = employee.chr.bodySkin;
	out.hired = employee.isHired();
	out.transfer = employee.transfer;
	out.name = valueString(employee.chr.name);
	return out;
}

StrategicMessageView projectMessage(const uiMessageListNodeMessage_t& message)
{
	StrategicMessageView out;
	out.id = messageId(&message);
	out.time = campaignTime(message.date);
	out.type = static_cast<int32_t>(message.type);
	out.title = valueString(message.title);
	out.text = valueString(message.text);
	out.iconName = valueString(message.iconName);
	return out;
}

} // namespace

StrategicSnapshot buildCurrentStrategicSnapshot(uint64_t publicationSerial)
{
	std::vector<StrategicMissionView> missions;
	MIS_Foreach(mission) {
		missions.push_back(projectMission(*mission));
	}

	std::vector<StrategicAircraftView> aircraft;
	AIR_Foreach(craft) {
		aircraft.push_back(projectAircraft(*craft, false));
	}
	for (int i = 0; i < ccs.numUFOs; ++i) {
		aircraft.push_back(projectAircraft(ccs.ufos[i], true));
	}

	std::vector<StrategicBaseView> bases;
	for (int i = 0; i < ccs.numBases; ++i) {
		bases.push_back(projectBase(ccs.bases[i]));
	}

	std::vector<StrategicFacilityView> facilities;
	base_t* facilityBase = nullptr;
	while ((facilityBase = B_GetNext(facilityBase)) != nullptr) {
		building_t* facility = nullptr;
		while ((facility = B_GetNextBuilding(facilityBase, facility)) != nullptr)
			facilities.push_back(projectFacility(*facilityBase, *facility));
	}

	std::vector<StrategicInstallationView> installations;
	INS_Foreach(installation) {
		installations.push_back(projectInstallation(*installation));
	}

	std::vector<StrategicNationView> nations;
	NAT_Foreach(nation) {
		nations.push_back(projectNation(*nation));
	}

	std::vector<StrategicTechnologyView> technologies;
	for (int i = 0; i < ccs.numTechnologies; ++i) {
		const technology_t* technology = RS_GetTechByIDX(i);
		if (technology)
			technologies.push_back(projectTechnology(*technology));
	}

	std::vector<StrategicItemDefinitionView> itemDefinitions;
	for (int i = 0; i < cgi->csi->numODs; ++i)
		itemDefinitions.push_back(projectItemDefinition(cgi->csi->ods[i]));

	std::vector<StrategicAircraftDefinitionView> aircraftDefinitions;
	for (int i = 0; i < ccs.numAircraftTemplates; ++i)
		aircraftDefinitions.push_back(projectAircraftDefinition(ccs.aircraftTemplates[i]));

	std::vector<StrategicProductionView> productions;
	base_t* productionBase = nullptr;
	while ((productionBase = B_GetNext(productionBase)) != nullptr) {
		const production_queue_t* queue = PR_GetProductionForBase(productionBase);
		for (int i = 0; i < queue->numItems; ++i)
			productions.push_back(projectProduction(*productionBase, queue->items[i]));
	}

	std::vector<StrategicStoredUfoView> storedUfos;
	US_Foreach(ufo) {
		storedUfos.push_back(projectStoredUfo(*ufo));
	}


	const StrategicUfoRecoveryView ufoRecovery = projectUfoRecovery(UR_GetPendingRecovery());
	std::vector<StrategicUfoSaleOfferView> ufoSaleOffers;
	for (std::size_t i = 0; i < UR_GetUfoSaleOfferCount(); ++i) {
		const ufoSaleOffer_t* offer = UR_GetUfoSaleOfferAt(i);
		if (offer)
			ufoSaleOffers.push_back(projectUfoSaleOffer(*offer));
	}

	std::vector<StrategicEmployeeView> employees;
	for (int type = 0; type < MAX_EMPL; ++type) {
		E_Foreach(type, employee) {
			employees.push_back(projectEmployee(*employee));
		}
	}

	std::vector<StrategicMessageView> messages;
	for (uiMessageListNodeMessage_t* message = cgi->UI_MessageGetStack(); message; message = message->next) {
		messages.push_back(projectMessage(*message));
	}

	StrategicSelectionView selection;
	selection.mission = ccs.geoscape.selectedMission
		? indexedId<canonical::MissionId>(ccs.geoscape.selectedMission->idx)
		: canonical::MissionId();
	selection.aircraft = aircraftId(ccs.geoscape.selectedAircraft, false);
	selection.ufo = aircraftId(ccs.geoscape.selectedUFO, true);
	const base_t* selectedBase = B_GetCurrentSelectedBase();
	selection.base = selectedBase ? indexedId<canonical::BaseId>(selectedBase->idx) : canonical::BaseId();
	const installation_t* selectedInstallation = INS_GetCurrentSelectedInstallation();
	selection.installation = selectedInstallation
		? indexedId<canonical::InstallationId>(selectedInstallation->idx)
		: canonical::InstallationId();

	return StrategicSnapshot(
		publicationSerial,
		campaignTime(ccs.date),
		ccs.credits,
		ccs.gameTimeScale,
		selection,
		std::move(missions),
		std::move(aircraft),
		std::move(bases),
		std::move(installations),
		std::move(nations),
		std::move(technologies),
		std::move(productions),
		std::move(storedUfos),
		std::move(messages),
		std::move(itemDefinitions),
		std::move(aircraftDefinitions),
		std::move(employees),
		std::move(facilities),
		ufoRecovery,
		std::move(ufoSaleOffers));
}

void resetStrategicSnapshotAdapter()
{
	messageIds.clear();
	nextMessageId = 0;
}

} // namespace legacy
} // namespace presentation
} // namespace ufo

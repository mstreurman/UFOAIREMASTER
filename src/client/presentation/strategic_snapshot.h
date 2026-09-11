/**
 * @file
 * @brief Immutable value-only strategic/campaign presentation snapshot.
 */
#pragma once

#include "canonical_identity.h"
#include "strategic_position.h"

#include <cstdint>
#include <string>
#include <utility>
#include <vector>

namespace ufo {
namespace presentation {

struct StrategicCampaignTime {
	int32_t day;
	int32_t seconds;
};

struct StrategicMissionView {
	canonical::MissionId id;
	StrategicPosition position;
	int32_t category;
	int32_t stage;
	bool active;
	bool onGeoscape;
	bool crashed;
};

struct StrategicAircraftView {
	canonical::AircraftId id;
	canonical::BaseId homeBase;
	canonical::MissionId mission;
	StrategicPosition position;
	int32_t status;
	int32_t fuel;
	int32_t damage;
	bool ufo;
	bool detected;
	bool landed;
	bool hiddenFromGeoscape;
	std::string name;
};

struct StrategicBaseView {
	canonical::BaseId id;
	StrategicPosition position;
	int32_t status;
	float alienInterest;
	bool founded;
	bool selected;
	std::string name;
};

struct StrategicFacilityView {
	canonical::FacilityId id;
	canonical::BaseId base;
	int32_t column;
	int32_t row;
	int32_t status;
	std::string definition;
};

struct StrategicInstallationView {
	canonical::InstallationId id;
	StrategicPosition position;
	int32_t status;
	int32_t type;
	int32_t damage;
	int32_t maxDamage;
	float alienInterest;
	bool selected;
	std::string name;
};

struct StrategicNationView {
	canonical::NationId id;
	StrategicPosition position;
	float happiness;
	int32_t xviInfection;
	int32_t maxFunding;
	std::string scriptId;
	std::string name;
};

struct StrategicTechnologyView {
	canonical::TechnologyId id;
	canonical::BaseId base;
	int32_t status;
	bool researchable;
	bool collected;
	int32_t scientists;
	float time;
	float overallTime;
	std::string name;
};

struct StrategicItemDefinitionView {
	canonical::ItemId id;
	canonical::TechnologyId technology;
	std::string scriptId;
	std::string name;
};

struct StrategicAircraftDefinitionView {
	canonical::TechnologyId technology;
	std::string scriptId;
	std::string name;
};

struct StrategicProductionView {
	canonical::ProductionId id;
	canonical::BaseId base;
	canonical::TechnologyId technology;
	canonical::ItemId item;
	canonical::StoredUfoId storedUfo;
	std::string aircraftDefinition;
	int32_t queueIndex;
	int32_t type;
	int32_t amount;
	int32_t frame;
	int32_t totalFrames;
};

struct StrategicStoredUfoView {
	canonical::StoredUfoId id;
	canonical::InstallationId installation;
	int32_t status;
	float condition;
	bool disassembling;
	std::string ufoDefinition;
};


struct StrategicUfoRecoveryView {
	canonical::UfoRecoveryId id;
	float condition;
	std::string ufoDefinition;
	StrategicUfoRecoveryView() : condition(0.0f) {}
};

struct StrategicUfoSaleOfferView {
	canonical::UfoSaleOfferId id;
	canonical::UfoRecoveryId recovery;
	canonical::NationId nation;
	int32_t price;
	std::string ufoDefinition;
};

struct StrategicEmployeeView {
	canonical::EmployeeId id;
	canonical::BaseId base;
	canonical::AircraftId aircraft;
	int32_t type;
	int32_t bodySkin;
	bool hired;
	bool transfer;
	std::string name;
};

struct StrategicMessageView {
	canonical::MessageId id;
	StrategicCampaignTime time;
	int32_t type;
	std::string title;
	std::string text;
	std::string iconName;
};

struct StrategicSelectionView {
	canonical::MissionId mission;
	canonical::AircraftId aircraft;
	canonical::AircraftId ufo;
	canonical::BaseId base;
	canonical::InstallationId installation;
};

class StrategicSnapshot {
public:
	StrategicSnapshot(
		uint64_t publicationSerial,
		StrategicCampaignTime campaignTime,
		int32_t credits,
		int32_t gameTimeScale,
		StrategicSelectionView selection,
		std::vector<StrategicMissionView> missions,
		std::vector<StrategicAircraftView> aircraft,
		std::vector<StrategicBaseView> bases,
		std::vector<StrategicInstallationView> installations,
		std::vector<StrategicNationView> nations,
		std::vector<StrategicTechnologyView> technologies,
		std::vector<StrategicProductionView> productions,
		std::vector<StrategicStoredUfoView> storedUfos,
		std::vector<StrategicMessageView> messages,
		std::vector<StrategicItemDefinitionView> itemDefinitions = std::vector<StrategicItemDefinitionView>(),
		std::vector<StrategicAircraftDefinitionView> aircraftDefinitions = std::vector<StrategicAircraftDefinitionView>(),
		std::vector<StrategicEmployeeView> employees = std::vector<StrategicEmployeeView>(),
		std::vector<StrategicFacilityView> facilities = std::vector<StrategicFacilityView>(),
		StrategicUfoRecoveryView ufoRecovery = StrategicUfoRecoveryView(),
		std::vector<StrategicUfoSaleOfferView> ufoSaleOffers = std::vector<StrategicUfoSaleOfferView>())
		: publicationSerial_(publicationSerial),
		  campaignTime_(campaignTime),
		  credits_(credits),
		  gameTimeScale_(gameTimeScale),
		  selection_(selection),
		  missions_(std::move(missions)),
		  aircraft_(std::move(aircraft)),
		  bases_(std::move(bases)),
		  installations_(std::move(installations)),
		  nations_(std::move(nations)),
		  technologies_(std::move(technologies)),
		  productions_(std::move(productions)),
		  storedUfos_(std::move(storedUfos)),
		  messages_(std::move(messages)),
		  itemDefinitions_(std::move(itemDefinitions)),
		  aircraftDefinitions_(std::move(aircraftDefinitions)),
		  employees_(std::move(employees)),
		  facilities_(std::move(facilities)),
		  ufoRecovery_(std::move(ufoRecovery)),
		  ufoSaleOffers_(std::move(ufoSaleOffers))
	{
	}

	uint64_t publicationSerial() const noexcept { return publicationSerial_; }
	StrategicCampaignTime campaignTime() const noexcept { return campaignTime_; }
	int32_t credits() const noexcept { return credits_; }
	int32_t gameTimeScale() const noexcept { return gameTimeScale_; }
	const StrategicSelectionView& selection() const noexcept { return selection_; }
	const std::vector<StrategicMissionView>& missions() const noexcept { return missions_; }
	const std::vector<StrategicAircraftView>& aircraft() const noexcept { return aircraft_; }
	const std::vector<StrategicBaseView>& bases() const noexcept { return bases_; }
	const std::vector<StrategicInstallationView>& installations() const noexcept { return installations_; }
	const std::vector<StrategicNationView>& nations() const noexcept { return nations_; }
	const std::vector<StrategicTechnologyView>& technologies() const noexcept { return technologies_; }
	const std::vector<StrategicProductionView>& productions() const noexcept { return productions_; }
	const std::vector<StrategicStoredUfoView>& storedUfos() const noexcept { return storedUfos_; }
	const std::vector<StrategicMessageView>& messages() const noexcept { return messages_; }
	const std::vector<StrategicItemDefinitionView>& itemDefinitions() const noexcept { return itemDefinitions_; }
	const std::vector<StrategicAircraftDefinitionView>& aircraftDefinitions() const noexcept { return aircraftDefinitions_; }
	const std::vector<StrategicEmployeeView>& employees() const noexcept { return employees_; }
	const std::vector<StrategicFacilityView>& facilities() const noexcept { return facilities_; }
	const StrategicUfoRecoveryView& ufoRecovery() const noexcept { return ufoRecovery_; }
	const std::vector<StrategicUfoSaleOfferView>& ufoSaleOffers() const noexcept { return ufoSaleOffers_; }

private:
	uint64_t publicationSerial_;
	StrategicCampaignTime campaignTime_;
	int32_t credits_;
	int32_t gameTimeScale_;
	StrategicSelectionView selection_;
	std::vector<StrategicMissionView> missions_;
	std::vector<StrategicAircraftView> aircraft_;
	std::vector<StrategicBaseView> bases_;
	std::vector<StrategicInstallationView> installations_;
	std::vector<StrategicNationView> nations_;
	std::vector<StrategicTechnologyView> technologies_;
	std::vector<StrategicProductionView> productions_;
	std::vector<StrategicStoredUfoView> storedUfos_;
	std::vector<StrategicMessageView> messages_;
	std::vector<StrategicItemDefinitionView> itemDefinitions_;
	std::vector<StrategicAircraftDefinitionView> aircraftDefinitions_;
	std::vector<StrategicEmployeeView> employees_;
	std::vector<StrategicFacilityView> facilities_;
	StrategicUfoRecoveryView ufoRecovery_;
	std::vector<StrategicUfoSaleOfferView> ufoSaleOffers_;
};

} // namespace presentation
} // namespace ufo

/**
 * @file
 * @brief Main-thread legacy campaign adapter for typed strategic intents.
 */

#include "../cl_shared.h"
#include "../cgame/campaign/cp_aircraft.h"
#include "../cgame/campaign/cp_campaign.h"
#include "../cgame/campaign/cp_geoscape.h"
#include "../cgame/campaign/cp_missions.h"
#include "../cgame/campaign/cp_time.h"
#include "strategic_intent.h"
#include "strategic_intent_legacy_adapter.h"

#include <cstdint>
#include <limits>

namespace ufo {
namespace presentation {
namespace legacy {
namespace {

const unsigned int MAX_STRATEGIC_INTENTS_PER_FRAME = 64;
const uint32_t UFO_AIRCRAFT_ID_BIT = 0x80000000u;

mission_t* resolveMission(canonical::MissionId id)
{
	if (!id.isValid() || id.value > static_cast<uint32_t>(std::numeric_limits<int>::max()))
		return nullptr;
	return MIS_GetByIdx(static_cast<int>(id.value));
}

aircraft_t* resolvePhalanxAircraft(canonical::AircraftId id)
{
	if (!id.isValid() || (id.value & UFO_AIRCRAFT_ID_BIT) != 0)
		return nullptr;
	if (id.value > static_cast<uint32_t>(std::numeric_limits<int>::max()))
		return nullptr;
	return AIR_AircraftGetFromIDX(static_cast<int>(id.value));
}

canonical::MissionId selectedMissionId()
{
	const mission_t* selected = GEO_GetSelectedMission();
	return selected && selected->idx >= 0
		? canonical::MissionId(static_cast<uint32_t>(selected->idx))
		: canonical::MissionId();
}

canonical::AircraftId selectedAircraftId()
{
	const aircraft_t* selected = GEO_GetSelectedAircraft();
	return selected && selected->idx >= 0
		? canonical::AircraftId(static_cast<uint32_t>(selected->idx))
		: canonical::AircraftId();
}

} // namespace

void applyPendingStrategicIntents()
{
	for (unsigned int i = 0; i < MAX_STRATEGIC_INTENTS_PER_FRAME; ++i) {
		StrategicIntent intentValue = {};
		if (!intent::legacy::tryPopStrategicIntent(&intentValue))
			break;

		StrategicIntentResult result = {};
		result.sequence = intentValue.sequence;
		result.kind = intentValue.kind;
		result.disposition = StrategicIntentDisposition::RejectedByCanonical;
		result.canonicalValue = -1;

		switch (intentValue.kind) {
		case StrategicIntentKind::SetCampaignTimeLapse:
			if (CP_TrySetGameTimeLapse(intentValue.value))
				result.disposition = StrategicIntentDisposition::Applied;
			result.canonicalValue = ccs.gameLapse;
			break;

		case StrategicIntentKind::SelectMission: {
			mission_t* mission = resolveMission(intentValue.mission);
			if (mission) {
				GEO_SelectMission(mission);
				if (GEO_GetSelectedMission() == mission)
					result.disposition = StrategicIntentDisposition::Applied;
			}
			result.mission = selectedMissionId();
			result.canonicalValue = result.mission.isValid()
				? static_cast<int32_t>(result.mission.value)
				: -1;
			break;
		}

		case StrategicIntentKind::SelectAircraft: {
			aircraft_t* aircraft = resolvePhalanxAircraft(intentValue.aircraft);
			if (aircraft) {
				GEO_SelectAircraft(aircraft);
				if (GEO_GetSelectedAircraft() == aircraft)
					result.disposition = StrategicIntentDisposition::Applied;
			}
			result.aircraft = selectedAircraftId();
			result.canonicalValue = result.aircraft.isValid()
				? static_cast<int32_t>(result.aircraft.value)
				: -1;
			break;
		}

		case StrategicIntentKind::SendAircraftToMission: {
			aircraft_t* aircraft = resolvePhalanxAircraft(intentValue.aircraft);
			mission_t* mission = resolveMission(intentValue.mission);
			if (aircraft && mission && AIR_SendAircraftToMission(aircraft, mission))
				result.disposition = StrategicIntentDisposition::Applied;
			if (aircraft) {
				result.aircraft = canonical::AircraftId(static_cast<uint32_t>(aircraft->idx));
				result.canonicalValue = static_cast<int32_t>(aircraft->status);
			}
			if (mission)
				result.mission = canonical::MissionId(static_cast<uint32_t>(mission->idx));
			break;
		}

		case StrategicIntentKind::ReturnAircraftToBase: {
			aircraft_t* aircraft = resolvePhalanxAircraft(intentValue.aircraft);
			if (aircraft && AIR_IsAircraftOnGeoscape(aircraft)) {
				AIR_AircraftReturnToBase(aircraft);
				if (aircraft->status == AIR_RETURNING)
					result.disposition = StrategicIntentDisposition::Applied;
			}
			if (aircraft) {
				result.aircraft = canonical::AircraftId(static_cast<uint32_t>(aircraft->idx));
				result.canonicalValue = static_cast<int32_t>(aircraft->status);
			}
			break;
		}
		}

		intent::legacy::publishStrategicIntentResult(result);
	}
}

void resetStrategicIntentAdapter()
{
	intent::legacy::resetStrategicIntentRuntime();
}

} // namespace legacy
} // namespace presentation
} // namespace ufo

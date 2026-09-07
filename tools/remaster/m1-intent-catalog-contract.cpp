#include "../../src/client/presentation/strategic_intent.h"
#include "../../src/client/presentation/tactical_intent.h"

#include <cstdint>
#include <iostream>

int main()
{
	using namespace ufo::presentation;

	intent::legacy::resetStrategicIntentRuntime();

	const StrategicIntentSubmission s0 = intent::submitSetCampaignTimeLapse(4);
	const StrategicIntentSubmission s1 = intent::submitSelectMission(ufo::canonical::MissionId(11u));
	const StrategicIntentSubmission s2 = intent::submitSelectAircraft(ufo::canonical::AircraftId(12u));
	const StrategicIntentSubmission s3 = intent::submitSendAircraftToMission(
		ufo::canonical::AircraftId(12u), ufo::canonical::MissionId(11u));
	const StrategicIntentSubmission s4 = intent::submitReturnAircraftToBase(
		ufo::canonical::AircraftId(12u));

	if (!s0.accepted || !s1.accepted || !s2.accepted || !s3.accepted || !s4.accepted)
		return 10;
	if (!(s0.sequence < s1.sequence && s1.sequence < s2.sequence
			&& s2.sequence < s3.sequence && s3.sequence < s4.sequence))
		return 11;

	StrategicIntent strategic = {};
	const StrategicIntentKind expectedKinds[] = {
		StrategicIntentKind::SetCampaignTimeLapse,
		StrategicIntentKind::SelectMission,
		StrategicIntentKind::SelectAircraft,
		StrategicIntentKind::SendAircraftToMission,
		StrategicIntentKind::ReturnAircraftToBase
	};
	for (const StrategicIntentKind expected : expectedKinds) {
		if (!intent::legacy::tryPopStrategicIntent(&strategic) || strategic.kind != expected)
			return 12;
	}
	if (strategic.aircraft != ufo::canonical::AircraftId(12u))
		return 13;

	tactical_intent::legacy::resetTacticalIntentRuntime();

	const TacticalIntentSubmission t0 = tactical_intent::submitSetReactionFire(
		ufo::canonical::EntityId(21u), true);
	const TacticalIntentSubmission t1 = tactical_intent::submitSetReservedTimeUnits(
		ufo::canonical::EntityId(21u), 12, 4);
	if (!t0.accepted || !t1.accepted || t1.sequence <= t0.sequence)
		return 20;

	TacticalIntent tactical = {};
	if (!tactical_intent::legacy::tryPopTacticalIntent(&tactical)
			|| tactical.kind != TacticalIntentKind::SetReactionFire
			|| tactical.entity != ufo::canonical::EntityId(21u)
			|| tactical.value0 != 1)
		return 21;
	if (!tactical_intent::legacy::tryPopTacticalIntent(&tactical)
			|| tactical.kind != TacticalIntentKind::SetReservedTimeUnits
			|| tactical.value0 != 12
			|| tactical.value1 != 4)
		return 22;

	tactical_intent::legacy::resetTacticalIntentRuntime();
	TacticalIntentSubmission last = {};
	for (int i = 0; i < 256; ++i) {
		last = tactical_intent::submitSetReactionFire(
			ufo::canonical::EntityId(static_cast<uint32_t>(i)), (i & 1) != 0);
		if (!last.accepted)
			return 23;
	}
	const TacticalIntentSubmission overflow = tactical_intent::submitSetReactionFire(
		ufo::canonical::EntityId(1u), true);
	if (overflow.accepted || overflow.sequence != 0)
		return 24;

	const uint64_t beforeReset = last.sequence;
	tactical_intent::legacy::resetTacticalIntentRuntime();
	const TacticalIntentSubmission afterReset = tactical_intent::submitSetReactionFire(
		ufo::canonical::EntityId(1u), false);
	if (!afterReset.accepted || afterReset.sequence <= beforeReset)
		return 25;

	std::cout << "M1 expanded intent runtime contract: PASS\n";
	return 0;
}

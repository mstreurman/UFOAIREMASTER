#include "../../src/client/presentation/strategic_intent.h"
#include "../../src/client/presentation/tactical_intent.h"

#include <cstdint>
#include <cstring>
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

	intent::legacy::resetStrategicIntentRuntime();
	StrategicTransferManifest manifest = {};
	manifest.source = ufo::canonical::BaseId(1u);
	manifest.destination = ufo::canonical::BaseId(2u);
	manifest.antimatter = 3;
	manifest.itemCount = 1;
	manifest.items[0].item = ufo::canonical::ItemId(9u);
	manifest.items[0].amount = 2;
	const StrategicIntentSubmission transfer = intent::submitStartTransfer(manifest);
	if (!transfer.accepted)
		return 14;
	StrategicIntent transferIntent = {};
	if (!intent::legacy::tryPopStrategicIntent(&transferIntent)
			|| transferIntent.kind != StrategicIntentKind::StartTransfer
			|| !transferIntent.transferManifest.isValid())
		return 15;
	StrategicTransferManifest consumed = {};
	if (!intent::legacy::takeTransferManifest(transferIntent.transferManifest, &consumed)
			|| consumed.source != manifest.source
			|| consumed.destination != manifest.destination
			|| consumed.itemCount != 1
			|| consumed.items[0].item != manifest.items[0].item
			|| consumed.items[0].amount != 2)
		return 16;
	if (intent::legacy::takeTransferManifest(transferIntent.transferManifest, &consumed))
		return 17;

	intent::legacy::resetStrategicIntentRuntime();
	const StrategicIntentSubmission loadLast = intent::submitLoadLastSave("slot-last");
	if (!loadLast.accepted)
		return 18;
	StrategicIntent loadLastIntent = {};
	if (!intent::legacy::tryPopStrategicIntent(&loadLastIntent)
			|| loadLastIntent.kind != StrategicIntentKind::LoadLastSave
			|| std::strcmp(loadLastIntent.key0, "slot-last") != 0)
		return 19;

	StrategicTransferManifest oversized = {};
	oversized.itemCount = static_cast<uint32_t>(STRATEGIC_TRANSFER_MAX_ITEMS + 1);
	if (intent::submitStartTransfer(oversized).accepted)
		return 26;

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

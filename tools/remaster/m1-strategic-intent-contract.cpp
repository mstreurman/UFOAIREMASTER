#include "../../src/client/presentation/strategic_intent.h"

#include <cstdint>
#include <iostream>

using namespace ufo::presentation;

int main()
{
	intent::legacy::resetStrategicIntentRuntime();

	const StrategicIntentSubmission first = intent::submitSetCampaignTimeLapse(3);
	const StrategicIntentSubmission second = intent::submitSetCampaignTimeLapse(4);
	if (!first.accepted || !second.accepted || first.sequence == 0 || second.sequence <= first.sequence)
		return 10;

	StrategicIntent popped = {};
	if (!intent::legacy::tryPopStrategicIntent(&popped))
		return 11;
	if (popped.sequence != first.sequence || popped.kind != StrategicIntentKind::SetCampaignTimeLapse || popped.value != 3)
		return 12;

	StrategicIntentResult applied = {};
	applied.sequence = popped.sequence;
	applied.kind = popped.kind;
	applied.disposition = StrategicIntentDisposition::Applied;
	applied.canonicalValue = 3;
	intent::legacy::publishStrategicIntentResult(applied);

	StrategicIntentResult observed = {};
	if (!intent::pollStrategicIntentResult(&observed))
		return 13;
	if (observed.sequence != first.sequence || observed.disposition != StrategicIntentDisposition::Applied || observed.canonicalValue != 3)
		return 14;

	if (!intent::legacy::tryPopStrategicIntent(&popped) || popped.sequence != second.sequence || popped.value != 4)
		return 15;

	intent::legacy::resetStrategicIntentRuntime();

	StrategicIntentSubmission last = {};
	for (int i = 0; i < 256; ++i) {
		last = intent::submitSetCampaignTimeLapse(i % 8);
		if (!last.accepted)
			return 20;
	}
	const StrategicIntentSubmission overflow = intent::submitSetCampaignTimeLapse(1);
	if (overflow.accepted || overflow.sequence != 0)
		return 21;

	uint64_t previous = 0;
	for (int i = 0; i < 256; ++i) {
		if (!intent::legacy::tryPopStrategicIntent(&popped))
			return 22;
		if (popped.sequence <= previous)
			return 23;
		previous = popped.sequence;
	}
	if (intent::legacy::tryPopStrategicIntent(&popped))
		return 24;

	const StrategicIntentSubmission beforeReset = intent::submitSetCampaignTimeLapse(2);
	if (!beforeReset.accepted)
		return 25;
	intent::legacy::resetStrategicIntentRuntime();
	if (intent::legacy::tryPopStrategicIntent(&popped))
		return 26;
	const StrategicIntentSubmission afterReset = intent::submitSetCampaignTimeLapse(2);
	if (!afterReset.accepted || afterReset.sequence <= beforeReset.sequence)
		return 27;

	std::cout << "M1 strategic intent runtime contract: PASS\n";
	return 0;
}

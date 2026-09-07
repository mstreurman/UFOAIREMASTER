/**
 * @file
 * @brief Main-thread legacy campaign adapter for typed strategic intents.
 */

#include "../cl_shared.h"
#include "../cgame/campaign/cp_campaign.h"
#include "../cgame/campaign/cp_time.h"
#include "strategic_intent.h"
#include "strategic_intent_legacy_adapter.h"

namespace ufo {
namespace presentation {
namespace legacy {
namespace {

const unsigned int MAX_STRATEGIC_INTENTS_PER_FRAME = 64;

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

		switch (intentValue.kind) {
		case StrategicIntentKind::SetCampaignTimeLapse:
			if (CP_TrySetGameTimeLapse(intentValue.value))
				result.disposition = StrategicIntentDisposition::Applied;
			break;
		}

		result.canonicalValue = ccs.gameLapse;
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

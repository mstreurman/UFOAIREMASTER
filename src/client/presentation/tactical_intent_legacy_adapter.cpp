/**
 * @file
 * @brief Client-Main adapter from typed tactical intents to existing PA_* requests.
 */

#include "../client.h"
#include "../battlescape/cl_actor.h"
#include "../battlescape/cl_battlescape.h"
#include "../battlescape/cl_localentity.h"
#include "tactical_intent.h"
#include "tactical_intent_legacy_adapter.h"

#include <cstdint>

namespace ufo {
namespace presentation {
namespace legacy {
namespace {

const unsigned int MAX_TACTICAL_INTENTS_PER_FRAME = 64;

le_t* resolveOwnedTacticalActor(canonical::EntityId entity)
{
	if (!entity.isValid() || entity.value >= MAX_EDICTS)
		return nullptr;

	le_t* actor = &cl.LEs[entity.value];
	if (!actor->inuse || actor->entnum != static_cast<int>(entity.value))
		return nullptr;
	if (!LE_IsActor(actor))
		return nullptr;
	if (actor->team != cls.team || actor->pnum != cl.pnum)
		return nullptr;
	return actor;
}

bool tacticalTransportReady()
{
	return cls.state == ca_active
		&& cls.netStream != nullptr
		&& CL_BattlescapeRunning();
}

} // namespace

void applyPendingTacticalIntents()
{
	for (unsigned int i = 0; i < MAX_TACTICAL_INTENTS_PER_FRAME; ++i) {
		TacticalIntent intentValue = {};
		if (!tactical_intent::legacy::tryPopTacticalIntent(&intentValue))
			break;

		TacticalIntentResult result = {};
		result.sequence = intentValue.sequence;
		result.kind = intentValue.kind;
		result.entity = intentValue.entity;
		result.disposition = TacticalIntentDisposition::RejectedByClientBoundary;

		le_t* actor = tacticalTransportReady()
			? resolveOwnedTacticalActor(intentValue.entity)
			: nullptr;

		if (actor) {
			switch (intentValue.kind) {
			case TacticalIntentKind::SetReactionFire:
				MSG_Write_PA(
					PA_STATE,
					actor->entnum,
					intentValue.value0 != 0 ? STATE_REACTION : ~STATE_REACTION);
				result.disposition = TacticalIntentDisposition::ForwardedToServer;
				break;

			case TacticalIntentKind::SetReservedTimeUnits:
				if (intentValue.value0 >= 0 && intentValue.value1 >= 0) {
					MSG_Write_PA(
						PA_RESERVE_STATE,
						actor->entnum,
						intentValue.value0,
						intentValue.value1);
					result.disposition = TacticalIntentDisposition::ForwardedToServer;
				}
				break;
			}
		}

		tactical_intent::legacy::publishTacticalIntentResult(result);
	}
}

void resetTacticalIntentAdapter()
{
	tactical_intent::legacy::resetTacticalIntentRuntime();
}

} // namespace legacy
} // namespace presentation
} // namespace ufo

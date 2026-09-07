#include "../../src/client/presentation/strategic_intent.h"

#include <cstdint>
#include <type_traits>

int main()
{
	using namespace ufo::presentation;
	static_assert(std::is_standard_layout<StrategicIntent>::value, "");
	static_assert(std::is_trivially_copyable<StrategicIntent>::value, "");
	static_assert(std::is_standard_layout<StrategicIntentResult>::value, "");
	static_assert(std::is_trivially_copyable<StrategicIntentResult>::value, "");

	StrategicIntent intent = {};
	intent.sequence = 7;
	intent.kind = StrategicIntentKind::SetCampaignTimeLapse;
	intent.value = 4;

	StrategicIntentResult result = {};
	result.sequence = intent.sequence;
	result.kind = intent.kind;
	result.disposition = StrategicIntentDisposition::Applied;
	result.canonicalValue = intent.value;

	return result.canonicalValue == 4 ? 0 : 1;
}

/**
 * @file
 * @brief C++11-compatible typed strategic presentation intent contract.
 */
#pragma once

#include <cstdint>
#include <type_traits>

namespace ufo {
namespace presentation {

enum class StrategicIntentKind : uint8_t {
	SetCampaignTimeLapse = 1
};

enum class StrategicIntentDisposition : uint8_t {
	Applied = 1,
	RejectedByCanonical = 2
};

struct StrategicIntent {
	uint64_t sequence;
	StrategicIntentKind kind;
	int32_t value;
};

struct StrategicIntentSubmission {
	uint64_t sequence;
	bool accepted;
};

struct StrategicIntentResult {
	uint64_t sequence;
	StrategicIntentKind kind;
	StrategicIntentDisposition disposition;
	int32_t canonicalValue;
};

static_assert(std::is_standard_layout<StrategicIntent>::value,
	"StrategicIntent must remain standard-layout");
static_assert(std::is_trivially_copyable<StrategicIntent>::value,
	"StrategicIntent must remain trivially copyable");
static_assert(std::is_standard_layout<StrategicIntentResult>::value,
	"StrategicIntentResult must remain standard-layout");
static_assert(std::is_trivially_copyable<StrategicIntentResult>::value,
	"StrategicIntentResult must remain trivially copyable");

namespace intent {

/**
 * Queue a request to set the canonical campaign time-lapse index.
 *
 * The returned sequence is non-zero only when the bounded queue accepted the
 * intent. Acceptance into this queue is not canonical acceptance.
 */
StrategicIntentSubmission submitSetCampaignTimeLapse(int32_t gameLapse);

/**
 * Poll canonical application/rejection feedback for previously accepted
 * intents. The next StrategicSnapshot remains authoritative.
 */
bool pollStrategicIntentResult(StrategicIntentResult* result);

namespace legacy {

/** Main/canonical ownership only. */
bool tryPopStrategicIntent(StrategicIntent* intent);

/** Main/canonical ownership only. */
void publishStrategicIntentResult(const StrategicIntentResult& result);

/**
 * Drop pending intents/results at campaign lifetime boundaries.
 * Sequence allocation intentionally remains process-monotonic.
 */
void resetStrategicIntentRuntime();

} // namespace legacy
} // namespace intent
} // namespace presentation
} // namespace ufo

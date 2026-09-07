/**
 * @file
 * @brief Bounded C++26 runtime transport for tactical presentation intents.
 */

#include "tactical_intent.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <mutex>

namespace ufo {
namespace presentation {
namespace tactical_intent {
namespace {

constexpr std::size_t TACTICAL_INTENT_CAPACITY = 256;
constexpr std::size_t TACTICAL_INTENT_RESULT_CAPACITY = 256;

template<typename T, std::size_t Capacity>
class FixedRing {
public:
	bool push(const T& value)
	{
		if (count_ == Capacity)
			return false;
		values_[write_] = value;
		write_ = (write_ + 1) % Capacity;
		++count_;
		return true;
	}

	bool pop(T& value)
	{
		if (count_ == 0)
			return false;
		value = values_[read_];
		read_ = (read_ + 1) % Capacity;
		--count_;
		return true;
	}

	bool full() const
	{
		return count_ == Capacity;
	}

	void clear()
	{
		read_ = 0;
		write_ = 0;
		count_ = 0;
	}

private:
	std::array<T, Capacity> values_{};
	std::size_t read_ = 0;
	std::size_t write_ = 0;
	std::size_t count_ = 0;
};

std::mutex tacticalIntentMutex;
FixedRing<TacticalIntent, TACTICAL_INTENT_CAPACITY> pendingTacticalIntents;
FixedRing<TacticalIntentResult, TACTICAL_INTENT_RESULT_CAPACITY> tacticalIntentResults;
uint64_t nextTacticalIntentSequence = 1;

uint64_t allocateSequence()
{
	const uint64_t sequence = nextTacticalIntentSequence++;
	if (nextTacticalIntentSequence == 0)
		nextTacticalIntentSequence = 1;
	return sequence;
}

TacticalIntentSubmission submit(TacticalIntent value)
{
	std::lock_guard<std::mutex> lock(tacticalIntentMutex);

	TacticalIntentSubmission submission = {0, false};
	if (pendingTacticalIntents.full())
		return submission;

	value.sequence = allocateSequence();
	if (!pendingTacticalIntents.push(value))
		return submission;

	submission.sequence = value.sequence;
	submission.accepted = true;
	return submission;
}

} // namespace

TacticalIntentSubmission submitSetReactionFire(canonical::EntityId entity, bool enabled)
{
	TacticalIntent value = {};
	value.kind = TacticalIntentKind::SetReactionFire;
	value.entity = entity;
	value.value0 = enabled ? 1 : 0;
	return submit(value);
}

TacticalIntentSubmission submitSetReservedTimeUnits(
	canonical::EntityId entity,
	int32_t shotTus,
	int32_t crouchTus)
{
	TacticalIntent value = {};
	value.kind = TacticalIntentKind::SetReservedTimeUnits;
	value.entity = entity;
	value.value0 = shotTus;
	value.value1 = crouchTus;
	return submit(value);
}

bool pollTacticalIntentResult(TacticalIntentResult* result)
{
	if (!result)
		return false;

	std::lock_guard<std::mutex> lock(tacticalIntentMutex);
	return tacticalIntentResults.pop(*result);
}

namespace legacy {

bool tryPopTacticalIntent(TacticalIntent* intent)
{
	if (!intent)
		return false;

	std::lock_guard<std::mutex> lock(tacticalIntentMutex);
	return pendingTacticalIntents.pop(*intent);
}

void publishTacticalIntentResult(const TacticalIntentResult& result)
{
	std::lock_guard<std::mutex> lock(tacticalIntentMutex);

	if (tacticalIntentResults.full()) {
		TacticalIntentResult discarded = {};
		tacticalIntentResults.pop(discarded);
	}
	tacticalIntentResults.push(result);
}

void resetTacticalIntentRuntime()
{
	std::lock_guard<std::mutex> lock(tacticalIntentMutex);
	pendingTacticalIntents.clear();
	tacticalIntentResults.clear();
}

} // namespace legacy
} // namespace tactical_intent
} // namespace presentation
} // namespace ufo

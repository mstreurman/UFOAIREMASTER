/**
 * @file
 * @brief Bounded C++26 runtime transport for strategic presentation intents.
 */

#include "strategic_intent.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <mutex>

namespace ufo {
namespace presentation {
namespace intent {
namespace {

constexpr std::size_t STRATEGIC_INTENT_CAPACITY = 256;
constexpr std::size_t STRATEGIC_INTENT_RESULT_CAPACITY = 256;

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

std::mutex intentMutex;
FixedRing<StrategicIntent, STRATEGIC_INTENT_CAPACITY> pendingIntents;
FixedRing<StrategicIntentResult, STRATEGIC_INTENT_RESULT_CAPACITY> intentResults;
uint64_t nextIntentSequence = 1;

uint64_t allocateSequence()
{
	const uint64_t sequence = nextIntentSequence++;
	if (nextIntentSequence == 0)
		nextIntentSequence = 1;
	return sequence;
}

StrategicIntentSubmission submit(StrategicIntent value)
{
	std::lock_guard<std::mutex> lock(intentMutex);

	StrategicIntentSubmission submission = {0, false};
	if (pendingIntents.full())
		return submission;

	value.sequence = allocateSequence();
	if (!pendingIntents.push(value))
		return submission;

	submission.sequence = value.sequence;
	submission.accepted = true;
	return submission;
}

} // namespace

StrategicIntentSubmission submitSetCampaignTimeLapse(int32_t gameLapse)
{
	StrategicIntent value = {};
	value.kind = StrategicIntentKind::SetCampaignTimeLapse;
	value.value = gameLapse;
	return submit(value);
}

StrategicIntentSubmission submitSelectMission(canonical::MissionId mission)
{
	StrategicIntent value = {};
	value.kind = StrategicIntentKind::SelectMission;
	value.mission = mission;
	return submit(value);
}

StrategicIntentSubmission submitSelectAircraft(canonical::AircraftId aircraft)
{
	StrategicIntent value = {};
	value.kind = StrategicIntentKind::SelectAircraft;
	value.aircraft = aircraft;
	return submit(value);
}

StrategicIntentSubmission submitSendAircraftToMission(
	canonical::AircraftId aircraft,
	canonical::MissionId mission)
{
	StrategicIntent value = {};
	value.kind = StrategicIntentKind::SendAircraftToMission;
	value.aircraft = aircraft;
	value.mission = mission;
	return submit(value);
}

StrategicIntentSubmission submitReturnAircraftToBase(canonical::AircraftId aircraft)
{
	StrategicIntent value = {};
	value.kind = StrategicIntentKind::ReturnAircraftToBase;
	value.aircraft = aircraft;
	return submit(value);
}

bool pollStrategicIntentResult(StrategicIntentResult* result)
{
	if (!result)
		return false;

	std::lock_guard<std::mutex> lock(intentMutex);
	return intentResults.pop(*result);
}

namespace legacy {

bool tryPopStrategicIntent(StrategicIntent* intent)
{
	if (!intent)
		return false;

	std::lock_guard<std::mutex> lock(intentMutex);
	return pendingIntents.pop(*intent);
}

void publishStrategicIntentResult(const StrategicIntentResult& result)
{
	std::lock_guard<std::mutex> lock(intentMutex);

	/*
	 * Result feedback is presentation-only. If a consumer disappears, keep the
	 * queue bounded by discarding the oldest feedback; the next immutable
	 * StrategicSnapshot remains the authoritative resynchronization source.
	 */
	if (intentResults.full()) {
		StrategicIntentResult discarded = {};
		intentResults.pop(discarded);
	}
	intentResults.push(result);
}

void resetStrategicIntentRuntime()
{
	std::lock_guard<std::mutex> lock(intentMutex);
	pendingIntents.clear();
	intentResults.clear();
}

} // namespace legacy
} // namespace intent
} // namespace presentation
} // namespace ufo

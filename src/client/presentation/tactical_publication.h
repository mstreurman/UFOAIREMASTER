/**
 * @file
 * @brief Immutable tactical snapshot/event publication seam for presentation consumers.
 */
#pragma once

#include "tactical_presentation_event.h"
#include "tactical_snapshot.h"

#include <cstdint>
#include <memory>
#include <utility>

namespace ufo {
namespace presentation {

class TacticalPublication {
public:
	TacticalPublication(TacticalSnapshot snapshot, TacticalPresentationEventHeader event) :
		snapshot_(std::move(snapshot)),
		event_(event)
	{
	}

	const TacticalSnapshot& snapshot() const noexcept
	{
		return snapshot_;
	}

	const TacticalPresentationEventHeader& event() const noexcept
	{
		return event_;
	}

private:
	TacticalSnapshot snapshot_;
	TacticalPresentationEventHeader event_;
};

using TacticalPublicationPtr = std::shared_ptr<const TacticalPublication>;

/**
 * Acquire the most recently completed immutable publication.
 * Production of publications remains ordered on the legacy client event thread;
 * read-side acquisition is safe for later presentation fan-out.
 */
TacticalPublicationPtr latestTacticalPublication() noexcept;

namespace legacy {

/**
 * Publish after a legacy EV_* callback has finished mutating the canonical client mirror.
 * The legacy event enum itself does not cross this boundary; only its stable numeric identity does.
 */
void publishAfterCanonicalEvent(uint16_t canonicalEventType, uint64_t scheduledPresentationTime);

} // namespace legacy
} // namespace presentation
} // namespace ufo

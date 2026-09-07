/**
 * @file
 * @brief Ordered immutable tactical publications owned by the presentation boundary.
 */

#include "tactical_publication.h"
#include "tactical_snapshot_legacy_adapter.h"

#include <atomic>
#include <utility>

namespace {

std::atomic<uint64_t> publicationSequence(0);
std::atomic<ufo::presentation::TacticalPublicationPtr> latestPublication;

} // namespace

namespace ufo {
namespace presentation {

TacticalPublicationPtr latestTacticalPublication() noexcept
{
	return latestPublication.load(std::memory_order_acquire);
}

namespace legacy {

void publishAfterCanonicalEvent(uint16_t canonicalEventType, uint64_t scheduledPresentationTime)
{
	/* Canonical mirror mutation remains single-threaded and ordered.  The atomic
	 * counter/publication handoff only makes completed immutable publications safe
	 * to acquire from later presentation consumers. */
	const uint64_t sequence = publicationSequence.fetch_add(1, std::memory_order_relaxed) + 1;
	TacticalSnapshot snapshot = buildCurrentClientSnapshot(sequence);

	TacticalPresentationEventHeader event = {};
	event.sequence = sequence;
	event.scheduledPresentationTime = scheduledPresentationTime;
	event.kind = TacticalPresentationEventKind::CanonicalMirrorUpdated;
	event.canonicalType = CanonicalEventTypeId(canonicalEventType);

	const TacticalPublicationPtr publication =
		std::make_shared<const TacticalPublication>(std::move(snapshot), event);
	latestPublication.store(publication, std::memory_order_release);
}

} // namespace legacy
} // namespace presentation
} // namespace ufo

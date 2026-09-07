/**
 * @file
 * @brief Thread-safe immutable strategic snapshot handoff.
 */

#include "strategic_publication.h"
#include "strategic_snapshot_legacy_adapter.h"

#include <atomic>
#include <mutex>
#include <utility>

namespace ufo {
namespace presentation {
namespace {

std::atomic<uint64_t> publicationSequence(0);
std::mutex publicationMutex;
StrategicSnapshotPtr latestSnapshot;

} // namespace

StrategicSnapshotPtr latestStrategicSnapshot()
{
	std::lock_guard<std::mutex> lock(publicationMutex);
	return latestSnapshot;
}

namespace legacy {

void publishAfterCanonicalCampaignUpdate()
{
	const uint64_t sequence = publicationSequence.fetch_add(1, std::memory_order_relaxed) + 1;
	StrategicSnapshot snapshot = buildCurrentStrategicSnapshot(sequence);
	StrategicSnapshotPtr publication = std::make_shared<const StrategicSnapshot>(std::move(snapshot));

	std::lock_guard<std::mutex> lock(publicationMutex);
	latestSnapshot = publication;
}

void resetStrategicPublication()
{
	resetStrategicSnapshotAdapter();
	std::lock_guard<std::mutex> lock(publicationMutex);
	latestSnapshot.reset();
}

} // namespace legacy
} // namespace presentation
} // namespace ufo

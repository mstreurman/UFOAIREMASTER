#include "src/client/presentation/canonical_identity.h"
#include <algorithm>
#include <iostream>
#include <vector>
using ufo::canonical::ProductionId;

struct Entry { int idx; ProductionId id; int amount; };

static Entry* resolve(std::vector<Entry>& queue, ProductionId id) {
    for (std::vector<Entry>::iterator it = queue.begin(); it != queue.end(); ++it)
        if (it->id == id) return &*it;
    return nullptr;
}
static void repair(std::vector<Entry>& queue) {
    for (std::size_t i = 0; i < queue.size(); ++i) queue[i].idx = static_cast<int>(i);
}
static bool stopById(std::vector<Entry>& queue, ProductionId id) {
    Entry* entry = resolve(queue, id);
    if (!entry) return false;
    const int idx = entry->idx;
    queue.erase(queue.begin() + idx);
    repair(queue);
    return true;
}
static bool moveDownById(std::vector<Entry>& queue, ProductionId id) {
    Entry* entry = resolve(queue, id);
    if (!entry || entry->idx >= static_cast<int>(queue.size()) - 1) return false;
    const int idx = entry->idx;
    std::swap(queue[idx], queue[idx + 1]);
    repair(queue);
    return true;
}
int main() {
    const ProductionId a(100), b(101), c(102);
    std::vector<Entry> queue;
    queue.push_back(Entry{0, a, 1});
    queue.push_back(Entry{1, b, 4});
    queue.push_back(Entry{2, c, 7});
    if (!stopById(queue, a)) return 1;
    if (queue.size()!=2 || queue[0].id!=b || queue[0].idx!=0 || queue[0].amount!=4) return 2;
    if (moveDownById(queue, a)) return 3;
    if (queue[0].id!=b || queue[0].idx!=0 || queue[0].amount!=4) return 4;
    if (!moveDownById(queue, b)) return 5;
    if (queue[1].id!=b || queue[1].idx!=1 || queue[1].amount!=4) return 6;
    if (queue[0].id!=c || queue[0].idx!=0 || queue[0].amount!=7) return 7;
    if (stopById(queue, a)) return 8;
    std::cout << "M1 production stale-intent contract: PASS\n";
    return 0;
}

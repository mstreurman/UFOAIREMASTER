#include <cstdlib>
#include <iostream>

#include "../../src/server/sv_spatial.h"

namespace {

void require (const bool condition, const char* label)
{
    if (!condition) {
        std::cerr << "M1.1b.2a map-bounds direct fixture: FAIL: " << label << '\n';
        std::exit(1);
    }
}

bool inside (const vec3_t mins, const vec3_t maxs, const float x, const float y, const float z)
{
    const vec3_t point = {x, y, z};
    return SV_CanonicalPointWithinMapBounds(mins, maxs, point);
}

} // namespace

int main ()
{
    const vec3_t mins = {-96.0f, -64.0f, -16.0f};
    const vec3_t maxs = {160.0f, 224.0f, 80.0f};

    require(inside(mins, maxs, 0.0f, 0.0f, 0.0f), "interior point rejected");
    require(inside(mins, maxs, -96.0f, -64.0f, -16.0f), "minimum corner must be inclusive");
    require(inside(mins, maxs, 160.0f, 224.0f, 80.0f), "maximum corner must be inclusive");
    require(inside(mins, maxs, -96.0f, 32.0f, 16.0f), "minimum X face must be inclusive");
    require(inside(mins, maxs, 160.0f, 32.0f, 16.0f), "maximum X face must be inclusive");
    require(inside(mins, maxs, 32.0f, -64.0f, 16.0f), "minimum Y face must be inclusive");
    require(inside(mins, maxs, 32.0f, 224.0f, 16.0f), "maximum Y face must be inclusive");
    require(inside(mins, maxs, 32.0f, 32.0f, -16.0f), "minimum Z face must be inclusive");
    require(inside(mins, maxs, 32.0f, 32.0f, 80.0f), "maximum Z face must be inclusive");

    require(!inside(mins, maxs, -96.25f, 32.0f, 16.0f), "point below minimum X accepted");
    require(!inside(mins, maxs, 160.25f, 32.0f, 16.0f), "point above maximum X accepted");
    require(!inside(mins, maxs, 32.0f, -64.25f, 16.0f), "point below minimum Y accepted");
    require(!inside(mins, maxs, 32.0f, 224.25f, 16.0f), "point above maximum Y accepted");
    require(!inside(mins, maxs, 32.0f, 32.0f, -16.25f), "point below minimum Z accepted");
    require(!inside(mins, maxs, 32.0f, 32.0f, 80.25f), "point above maximum Z accepted");
    require(!inside(mins, maxs, -120.0f, 300.0f, 100.0f), "multi-axis outside point accepted");

    std::cout << "M1.1b.2a map-bounds direct fixture: PASS\n";
    std::cout << "  service: isOnMap\n";
    std::cout << "  cases: 16\n";
    std::cout << "  boundary semantics: inclusive min/max\n";
    return 0;
}

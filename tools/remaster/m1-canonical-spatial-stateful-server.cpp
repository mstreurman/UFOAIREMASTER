/**
 * @file
 * @brief Server-side oracle bridge for the M1 canonical spatial stateful fixture.
 *
 * game.h intentionally aliases edict_t differently across the server/game ABI:
 * server code sees SrvEdict while game code sees Edict.  Keep the direct
 * SV_Trace oracle in a server-only translation unit and expose a C-linkage
 * bridge whose public signature does not mention edict_t.
 */

#include "../../src/server/server.h"

extern "C" trace_t M1_CanonicalServerTrace (const Line& traceLine, const AABB& box, int contentmask)
{
	return SV_Trace(traceLine, box, nullptr, contentmask);
}

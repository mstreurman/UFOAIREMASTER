/**
 * @file
 * @brief M1-only integration tests for expanded strategic/tactical intent catalogs.
 *
 * Injected from the root CMake seam only when UFOAI_M1_INTENT_CATALOG_TESTS=ON.
 * The sealed src/tests/CMakeLists.txt remains untouched.
 */

#include "../../src/tests/test_shared.h"
#include "../../src/client/client.h"
#include "../../src/client/cl_lua.h"
#include "../../src/client/cgame/cl_game.h"
#include "../../src/client/cgame/campaign/cp_alien_interest.h"
#include "../../src/client/cgame/campaign/cp_campaign.h"
#include "../../src/client/cgame/campaign/cp_geoscape.h"
#include "../../src/client/cgame/campaign/cp_missions.h"
#include "../../src/client/presentation/strategic_intent.h"
#include "../../src/client/presentation/strategic_intent_legacy_adapter.h"
#include "../../src/client/presentation/strategic_publication.h"
#include "../../src/client/presentation/tactical_intent.h"
#include "../../src/client/presentation/tactical_intent_legacy_adapter.h"
#include "../../src/client/renderer/r_state.h"
#include "../../src/client/ui/ui_main.h"
#include "../../src/shared/images.h"

namespace {

const int M1_CATALOG_INVENTORY_TAG = 2038;

void FreeCatalogInventory(void* data)
{
	Mem_Free(data);
}

void* AllocCatalogInventory(size_t size)
{
	return Mem_PoolAlloc(size, com_genericPool, M1_CATALOG_INVENTORY_TAG);
}

void FreeAllCatalogInventory()
{
	Mem_FreeTag(com_genericPool, M1_CATALOG_INVENTORY_TAG);
}

const inventoryImport_t catalogInventoryImport = {
	FreeCatalogInventory,
	FreeAllCatalogInventory,
	AllocCatalogInventory
};

void ResetCatalogInventory()
{
	cls.i.destroyInventoryInterface();
	cls.i.initInventory("m1IntentCatalog", &csi, &catalogInventoryImport);
}

campaign_t* CatalogCampaign()
{
	return CP_GetCampaign("main");
}

class M1IntentCatalogTest: public ::testing::Test {
protected:
	static void SetUpTestSuite()
	{
		TEST_Init();

		cl_genericPool = Mem_CreatePool("Client: Generic");
		cp_campaignPool = Mem_CreatePool("Client: Local (per game)");
		cp_missiontest = Cvar_Get("cp_missiontest", "0");
		vid_imagePool = Mem_CreatePool("Vid: Image system");

		r_state.active_texunit = &r_state.texunits[0];
		R_FontInit();
		CL_InitLua();
		UI_Init();
		GAME_InitStartup();

		OBJZERO(cls);
		Com_ParseScripts(false);
		Cmd_ExecuteString("game_setmode campaign");
		Cmd_AddCommand("msgoptions_set", Cmd_Dummy_f);

		CL_SetClientState(ca_disconnected);
		cls.realtime = Sys_Milliseconds();
	}

	static void TearDownTestSuite()
	{
		ufo::presentation::legacy::resetStrategicIntentAdapter();
		ufo::presentation::legacy::resetTacticalIntentAdapter();
		CP_ResetCampaignData();
		TEST_Shutdown();
	}

	void SetUp() override
	{
		ufo::presentation::legacy::resetStrategicIntentAdapter();
		ufo::presentation::legacy::resetTacticalIntentAdapter();
		CP_ResetCampaignData();
		CP_ParseCampaignData();

		campaign_t* campaign = CatalogCampaign();
		ASSERT_NE(nullptr, campaign);
		CP_ReadCampaignData(campaign);

		ResetCatalogInventory();
		CP_UpdateCredits(MAX_CREDITS);

		GEO_Shutdown();
		GEO_Init(campaign->map);

		ccs.curCampaign = campaign;
		cgi->UI_InitStack("geoscape", "campaign_main");
		ASSERT_TRUE(CP_OnGeoscape());

		CL_SetClientState(ca_disconnected);
		cls.netStream = nullptr;
	}
};

TEST_F(M1IntentCatalogTest, SelectMissionUsesTypedIdentityAndPublishesSelection)
{
	ccs.overallInterest = 36;
	INT_ResetAlienInterest();

	mission_t* mission = CP_CreateNewMission(INTERESTCATEGORY_RECON, false);
	ASSERT_NE(nullptr, mission);
	ASSERT_GE(mission->idx, 0);

	const ufo::canonical::MissionId missionId(static_cast<uint32_t>(mission->idx));
	const ufo::presentation::StrategicIntentSubmission submission =
		ufo::presentation::intent::submitSelectMission(missionId);
	ASSERT_TRUE(submission.accepted);

	EXPECT_NE(mission, GEO_GetSelectedMission());

	ufo::presentation::legacy::applyPendingStrategicIntents();
	EXPECT_EQ(mission, GEO_GetSelectedMission());

	ufo::presentation::StrategicIntentResult result = {};
	ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&result));
	EXPECT_EQ(submission.sequence, result.sequence);
	EXPECT_EQ(ufo::presentation::StrategicIntentKind::SelectMission, result.kind);
	EXPECT_EQ(ufo::presentation::StrategicIntentDisposition::Applied, result.disposition);
	EXPECT_EQ(missionId, result.mission);

	ufo::presentation::legacy::publishAfterCanonicalCampaignUpdate();
	const ufo::presentation::StrategicSnapshotPtr snapshot =
		ufo::presentation::latestStrategicSnapshot();
	ASSERT_TRUE(snapshot);
	EXPECT_EQ(missionId, snapshot->selection().mission);
}

TEST_F(M1IntentCatalogTest, InvalidStrategicIdentitiesAreRejectedInOrder)
{
	const ufo::canonical::MissionId badMission(0x7ffffff0u);
	const ufo::canonical::AircraftId badAircraft(0x7ffffff1u);

	const ufo::presentation::StrategicIntentSubmission selectAircraft =
		ufo::presentation::intent::submitSelectAircraft(badAircraft);
	const ufo::presentation::StrategicIntentSubmission send =
		ufo::presentation::intent::submitSendAircraftToMission(badAircraft, badMission);
	const ufo::presentation::StrategicIntentSubmission returnToBase =
		ufo::presentation::intent::submitReturnAircraftToBase(badAircraft);

	ASSERT_TRUE(selectAircraft.accepted);
	ASSERT_TRUE(send.accepted);
	ASSERT_TRUE(returnToBase.accepted);
	ASSERT_LT(selectAircraft.sequence, send.sequence);
	ASSERT_LT(send.sequence, returnToBase.sequence);

	ufo::presentation::legacy::applyPendingStrategicIntents();

	const ufo::presentation::StrategicIntentKind expected[] = {
		ufo::presentation::StrategicIntentKind::SelectAircraft,
		ufo::presentation::StrategicIntentKind::SendAircraftToMission,
		ufo::presentation::StrategicIntentKind::ReturnAircraftToBase
	};

	for (const ufo::presentation::StrategicIntentKind kind : expected) {
		ufo::presentation::StrategicIntentResult result = {};
		ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&result));
		EXPECT_EQ(kind, result.kind);
		EXPECT_EQ(
			ufo::presentation::StrategicIntentDisposition::RejectedByCanonical,
			result.disposition);
	}
}

TEST_F(M1IntentCatalogTest, TacticalIntentNeverClaimsCanonicalApplicationAtClientBoundary)
{
	const ufo::canonical::EntityId actor(7u);

	const ufo::presentation::TacticalIntentSubmission reaction =
		ufo::presentation::tactical_intent::submitSetReactionFire(actor, true);
	const ufo::presentation::TacticalIntentSubmission reserve =
		ufo::presentation::tactical_intent::submitSetReservedTimeUnits(actor, 12, 4);

	ASSERT_TRUE(reaction.accepted);
	ASSERT_TRUE(reserve.accepted);
	ASSERT_LT(reaction.sequence, reserve.sequence);

	/* Deliberately disconnected: no PA_* request can be forwarded. */
	ufo::presentation::legacy::applyPendingTacticalIntents();

	ufo::presentation::TacticalIntentResult first = {};
	ufo::presentation::TacticalIntentResult second = {};
	ASSERT_TRUE(ufo::presentation::tactical_intent::pollTacticalIntentResult(&first));
	ASSERT_TRUE(ufo::presentation::tactical_intent::pollTacticalIntentResult(&second));

	EXPECT_EQ(reaction.sequence, first.sequence);
	EXPECT_EQ(reserve.sequence, second.sequence);
	EXPECT_EQ(
		ufo::presentation::TacticalIntentDisposition::RejectedByClientBoundary,
		first.disposition);
	EXPECT_EQ(
		ufo::presentation::TacticalIntentDisposition::RejectedByClientBoundary,
		second.disposition);
}

} // namespace

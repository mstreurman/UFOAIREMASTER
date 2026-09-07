/**
 * @file
 * @brief M1-only end-to-end strategic typed-intent integration fixture.
 *
 * Injected into ufotestall only with UFOAI_M1_STRATEGIC_INTENT_TESTS=ON.
 * The sealed src/tests/CMakeLists.txt remains untouched.
 */

#include "../../src/tests/test_shared.h"
#include "../../src/client/client.h"
#include "../../src/client/cl_lua.h"
#include "../../src/client/cgame/cl_game.h"
#include "../../src/client/cgame/campaign/cp_campaign.h"
#include "../../src/client/cgame/campaign/cp_geoscape.h"
#include "../../src/client/cgame/campaign/cp_time.h"
#include "../../src/client/presentation/strategic_intent.h"
#include "../../src/client/presentation/strategic_intent_legacy_adapter.h"
#include "../../src/client/presentation/strategic_publication.h"
#include "../../src/client/renderer/r_state.h"
#include "../../src/client/ui/ui_main.h"
#include "../../src/shared/images.h"

namespace {

const int M1_INTENT_INVENTORY_TAG = 1938;

void FreeIntentInventory(void* data)
{
	Mem_Free(data);
}

void* AllocIntentInventory(size_t size)
{
	return Mem_PoolAlloc(size, com_genericPool, M1_INTENT_INVENTORY_TAG);
}

void FreeAllIntentInventory()
{
	Mem_FreeTag(com_genericPool, M1_INTENT_INVENTORY_TAG);
}

const inventoryImport_t intentInventoryImport = {
	FreeIntentInventory,
	FreeAllIntentInventory,
	AllocIntentInventory
};

void ResetIntentInventory()
{
	cls.i.destroyInventoryInterface();
	cls.i.initInventory("m1StrategicIntent", &csi, &intentInventoryImport);
}

campaign_t* IntentCampaign()
{
	return CP_GetCampaign("main");
}

class M1StrategicIntentTest: public ::testing::Test {
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
		CP_ResetCampaignData();
		TEST_Shutdown();
	}

	void SetUp() override
	{
		ufo::presentation::legacy::resetStrategicIntentAdapter();
		CP_ResetCampaignData();
		CP_ParseCampaignData();

		campaign_t* campaign = IntentCampaign();
		ASSERT_NE(nullptr, campaign);
		CP_ReadCampaignData(campaign);

		ResetIntentInventory();
		CP_UpdateCredits(MAX_CREDITS);

		GEO_Shutdown();
		GEO_Init(campaign->map);

		ccs.curCampaign = campaign;
		ccs.campaignStats.basesBuilt = 1;
		cgi->UI_InitStack("geoscape", "campaign_main");
		ASSERT_TRUE(CP_OnGeoscape());

		ccs.gameLapse = 1;
		CP_UpdateTime();
		ASSERT_EQ(1, ccs.gameLapse);
	}
};

TEST_F(M1StrategicIntentTest, AcceptedIntentMutatesOnlyThroughCanonicalAdapter)
{
	const ufo::presentation::StrategicIntentSubmission submission =
		ufo::presentation::intent::submitSetCampaignTimeLapse(4);
	ASSERT_TRUE(submission.accepted);
	ASSERT_NE(0u, submission.sequence);

	/* Submission itself is presentation-only and must not optimistically mutate canonical state. */
	EXPECT_EQ(1, ccs.gameLapse);

	ufo::presentation::legacy::applyPendingStrategicIntents();
	EXPECT_EQ(4, ccs.gameLapse);

	ufo::presentation::StrategicIntentResult result = {};
	ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&result));
	EXPECT_EQ(submission.sequence, result.sequence);
	EXPECT_EQ(ufo::presentation::StrategicIntentKind::SetCampaignTimeLapse, result.kind);
	EXPECT_EQ(ufo::presentation::StrategicIntentDisposition::Applied, result.disposition);
	EXPECT_EQ(4, result.canonicalValue);

	ufo::presentation::legacy::publishAfterCanonicalCampaignUpdate();
	const ufo::presentation::StrategicSnapshotPtr snapshot =
		ufo::presentation::latestStrategicSnapshot();
	ASSERT_TRUE(snapshot);
	EXPECT_EQ(DateTime::SECONDS_PER_HOUR, snapshot->gameTimeScale());
}

TEST_F(M1StrategicIntentTest, CanonicalValidationRejectsInvalidLapse)
{
	const int originalLapse = ccs.gameLapse;
	const int originalScale = ccs.gameTimeScale;

	const ufo::presentation::StrategicIntentSubmission submission =
		ufo::presentation::intent::submitSetCampaignTimeLapse(99);
	ASSERT_TRUE(submission.accepted);

	ufo::presentation::legacy::applyPendingStrategicIntents();

	EXPECT_EQ(originalLapse, ccs.gameLapse);
	EXPECT_EQ(originalScale, ccs.gameTimeScale);

	ufo::presentation::StrategicIntentResult result = {};
	ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&result));
	EXPECT_EQ(submission.sequence, result.sequence);
	EXPECT_EQ(ufo::presentation::StrategicIntentDisposition::RejectedByCanonical, result.disposition);
	EXPECT_EQ(originalLapse, result.canonicalValue);
}

TEST_F(M1StrategicIntentTest, CampaignResetDropsPendingPresentationIntentState)
{
	const ufo::presentation::StrategicIntentSubmission before =
		ufo::presentation::intent::submitSetCampaignTimeLapse(3);
	ASSERT_TRUE(before.accepted);

	ufo::presentation::legacy::resetStrategicIntentAdapter();
	ufo::presentation::legacy::applyPendingStrategicIntents();

	EXPECT_EQ(1, ccs.gameLapse);

	ufo::presentation::StrategicIntentResult result = {};
	EXPECT_FALSE(ufo::presentation::intent::pollStrategicIntentResult(&result));

	const ufo::presentation::StrategicIntentSubmission after =
		ufo::presentation::intent::submitSetCampaignTimeLapse(2);
	ASSERT_TRUE(after.accepted);
	EXPECT_GT(after.sequence, before.sequence);
}

} // namespace

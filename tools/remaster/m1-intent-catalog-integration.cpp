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
#include "../../src/client/cgame/campaign/cp_mapfightequip.h"
#include "../../src/client/cgame/campaign/cp_uforecovery.h"
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


const aircraft_t* FirstCatalogUfoTemplate()
{
	for (int i = 0; i < ccs.numAircraftTemplates; ++i) {
		const aircraft_t* aircraft = &ccs.aircraftTemplates[i];
		if (AIR_IsUFO(aircraft))
			return aircraft;
	}
	return nullptr;
}

installation_t* MakeCatalogUfoYard(const char* name, float longitude)
{
	const installationTemplate_t* tpl = INS_GetInstallationTemplateByType(INSTALLATION_UFOYARD);
	if (!tpl)
		return nullptr;
	vec2_t pos = {longitude, 0.0f};
	installation_t* yard = INS_Build(tpl, pos, name);
	if (!yard)
		return nullptr;
	yard->installationStatus = INSTALLATION_WORKING;
	yard->ufoCapacity.max = 4;
	yard->ufoCapacity.cur = 0;
	return yard;
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



TEST_F(M1IntentCatalogTest, AircraftConfigurationOwnersPreserveStructuralSlotSemantics)
{
	/* Match the real campaign startup prerequisite for aircraft equipment.
	 * CP_ReadCampaignData is followed by RS_InitTree before equipment-tech
	 * lookups are legal. Entity construction remains deliberately absent. */
	campaign_t* campaign = CatalogCampaign();
	ASSERT_NE(nullptr, campaign);
	RS_InitTree(campaign, false);

	const aircraft_t* aircraftTemplate = nullptr;
	for (int i = 0; i < ccs.numAircraftTemplates; ++i) {
		const aircraft_t* candidate = &ccs.aircraftTemplates[i];
		if (!AIR_IsUFO(candidate) && candidate->maxWeapons > 0) {
			aircraftTemplate = candidate;
			break;
		}
	}
	ASSERT_NE(nullptr, aircraftTemplate);

	base_t base = {};
	base.idx = 0;
	base.founded = true;
	base.baseStatus = BASE_WORKING;

	aircraft_t aircraft = {};
	aircraft.idx = 0;
	aircraft.tpl = const_cast<aircraft_t*>(aircraftTemplate);
	aircraft.defaultName = aircraftTemplate->defaultName;
	aircraft.ufotype = UFO_NONE;
	aircraft.homebase = &base;
	aircraft.status = AIR_HOME;
	aircraft.maxWeapons = 1;
	aircraft.maxElectronics = 0;

	AII_InitialiseSlot(&aircraft.weapons[0], &aircraft, nullptr, nullptr, AC_ITEM_WEAPON);
	AII_InitialiseSlot(&aircraft.shield, &aircraft, nullptr, nullptr, AC_ITEM_SHIELD);
	aircraftSlot_t* slot = &aircraft.weapons[0];

	const technology_t* originalTech = nullptr;
	const objDef_t* originalItem = nullptr;
	technology_t** weaponTechs = AII_GetCraftitemTechsByType(AC_ITEM_WEAPON);
	for (technology_t** current = weaponTechs; current && *current; ++current) {
		const technology_t* tech = *current;
		if (!RS_IsResearched_ptr(tech))
			continue;
		const objDef_t* item = INVSH_GetItemByID(tech->provides);
		if (!item || item->isVirtual)
			continue;
		if (item->craftitem.type != AC_ITEM_WEAPON || item->craftitem.installationTime <= 0)
			continue;
		if (AII_GetItemWeightBySize(item) > slot->size)
			continue;
		originalTech = tech;
		originalItem = item;
		break;
	}
	ASSERT_NE(nullptr, originalTech);
	ASSERT_NE(nullptr, originalItem);
	ASSERT_GE(originalItem->idx, 0);

	/* One spare copy keeps the inherited eligibility predicate true. The
	 * remove/re-add cancellation path below never mutates storage. */
	base.storage.numItems[originalItem->idx] = 1;
	slot->item = originalItem;
	slot->installationTime = 0;
	AII_UpdateAircraftStats(&aircraft);

	ASSERT_TRUE(AIR_TrySetName(&aircraft, "M1 Configuration Craft"));
	EXPECT_STREQ("M1 Configuration Craft", aircraft.name);

	const aircraftEquipmentMutationResult_t remove =
		AII_TryRemoveAircraftItem(&aircraft, AC_ITEM_WEAPON, 0, ZONE_MAIN);
	ASSERT_EQ(AII_AIRCRAFT_EQUIPMENT_APPLIED, remove);
	ASSERT_EQ(originalItem, slot->item);
	ASSERT_EQ(-originalItem->craftitem.installationTime, slot->installationTime);
	ASSERT_EQ(1, base.storage.numItems[originalItem->idx]);

	const aircraftEquipmentMutationResult_t equip =
		AII_TryEquipAircraftItem(&aircraft, AC_ITEM_WEAPON, 0, ZONE_MAIN, originalItem->idx);
	ASSERT_EQ(AII_AIRCRAFT_EQUIPMENT_APPLIED, equip);
	ASSERT_EQ(originalItem, slot->item);
	ASSERT_EQ(0, slot->installationTime);
	ASSERT_EQ(1, base.storage.numItems[originalItem->idx]);

	EXPECT_EQ(
		AII_AIRCRAFT_EQUIPMENT_INVALID_SLOT,
		AII_TryRemoveAircraftItem(&aircraft, AC_ITEM_WEAPON, 99, ZONE_MAIN));
	EXPECT_EQ(
		AII_AIRCRAFT_EQUIPMENT_INVALID_SLOT,
		AII_TryEquipAircraftItem(&aircraft, AC_ITEM_WEAPON, 0, ZONE_AMMO, originalItem->idx));
}
TEST_F(M1IntentCatalogTest, UfoRecoveryOwnersBindOneShotRecoveryAndRejectReplay)
{
	const aircraft_t* ufo = FirstCatalogUfoTemplate();
	ASSERT_NE(nullptr, ufo);
	installation_t* firstYard = MakeCatalogUfoYard("M1 Recovery Yard A", 10.0f);
	installation_t* secondYard = MakeCatalogUfoYard("M1 Recovery Yard B", 20.0f);
	ASSERT_NE(nullptr, firstYard);
	ASSERT_NE(nullptr, secondYard);

	mission_t recoveryMission = {};
	recoveryMission.ufo = const_cast<aircraft_t*>(ufo);
	recoveryMission.crashed = true;
	Com_sprintf(recoveryMission.onwin, sizeof(recoveryMission.onwin),
		"ui_push popup_uforecovery \"Recovered UFO\" \"%s\" \"%s\" \"crashed\" 0.42",
		ufo->id, ufo->model);
	ASSERT_TRUE(UR_BeginRecoveryFromMission(&recoveryMission));

	ufo::presentation::legacy::publishAfterCanonicalCampaignUpdate();
	ufo::presentation::StrategicSnapshotPtr snapshot = ufo::presentation::latestStrategicSnapshot();
	ASSERT_TRUE(snapshot);
	const ufo::canonical::UfoRecoveryId recoveryId = snapshot->ufoRecovery().id;
	ASSERT_TRUE(recoveryId.isValid());
	EXPECT_STREQ(ufo->id, snapshot->ufoRecovery().ufoDefinition.c_str());
	EXPECT_FLOAT_EQ(0.42f, snapshot->ufoRecovery().condition);

	const ufo::presentation::StrategicIntentSubmission store =
		ufo::presentation::intent::submitStoreRecoveredUfo(
			recoveryId, ufo::canonical::InstallationId(static_cast<uint32_t>(firstYard->idx)));
	ASSERT_TRUE(store.accepted);
	ufo::presentation::legacy::applyPendingStrategicIntents();
	ufo::presentation::StrategicIntentResult storeResult = {};
	ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&storeResult));
	ASSERT_EQ(ufo::presentation::StrategicIntentDisposition::Applied, storeResult.disposition);
	ASSERT_GE(storeResult.canonicalValue, 0);

	storedUFO_t* stored = US_GetStoredUFOByIDX(storeResult.canonicalValue);
	ASSERT_NE(nullptr, stored);
	EXPECT_FLOAT_EQ(0.42f, stored->condition);
	EXPECT_EQ(firstYard, stored->installation);
	EXPECT_EQ(nullptr, UR_GetPendingRecovery());

	const ufo::presentation::StrategicIntentSubmission storeReplay =
		ufo::presentation::intent::submitStoreRecoveredUfo(
			recoveryId, ufo::canonical::InstallationId(static_cast<uint32_t>(secondYard->idx)));
	ASSERT_TRUE(storeReplay.accepted);
	ufo::presentation::legacy::applyPendingStrategicIntents();
	ufo::presentation::StrategicIntentResult storeReplayResult = {};
	ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&storeReplayResult));
	EXPECT_EQ(ufo::presentation::StrategicIntentDisposition::RejectedByCanonical, storeReplayResult.disposition);

	/* Complete recovery transit so the inherited transfer owner becomes eligible. */
	stored->status = SUFO_STORED;
	stored->arrive = ccs.date;
	const ufo::canonical::StoredUfoId storedId(static_cast<uint32_t>(stored->idx));
	const ufo::presentation::StrategicIntentSubmission transfer =
		ufo::presentation::intent::submitTransferStoredUfo(
			storedId, ufo::canonical::InstallationId(static_cast<uint32_t>(secondYard->idx)));
	ASSERT_TRUE(transfer.accepted);
	ufo::presentation::legacy::applyPendingStrategicIntents();
	ufo::presentation::StrategicIntentResult transferResult = {};
	ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&transferResult));
	ASSERT_EQ(ufo::presentation::StrategicIntentDisposition::Applied, transferResult.disposition);
	stored = US_GetStoredUFOByIDX(static_cast<int>(storedId.value));
	ASSERT_NE(nullptr, stored);
	EXPECT_EQ(secondYard, stored->installation);
	EXPECT_EQ(SUFO_TRANSFERED, stored->status);

	const ufo::presentation::StrategicIntentSubmission destroy =
		ufo::presentation::intent::submitDestroyStoredUfo(storedId);
	ASSERT_TRUE(destroy.accepted);
	ufo::presentation::legacy::applyPendingStrategicIntents();
	ufo::presentation::StrategicIntentResult destroyResult = {};
	ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&destroyResult));
	ASSERT_EQ(ufo::presentation::StrategicIntentDisposition::Applied, destroyResult.disposition);
	EXPECT_EQ(nullptr, US_GetStoredUFOByIDX(static_cast<int>(storedId.value)));

	recoveryMission.crashed = false;
	Com_sprintf(recoveryMission.onwin, sizeof(recoveryMission.onwin),
		"ui_push popup_uforecovery \"Recovered UFO\" \"%s\" \"%s\" \"landed\" 1.00",
		ufo->id, ufo->model);
	ASSERT_TRUE(UR_BeginRecoveryFromMission(&recoveryMission));
	const ufoRecovery_t* pending = UR_GetPendingRecovery();
	ASSERT_NE(nullptr, pending);
	ASSERT_GT(UR_GetUfoSaleOfferCount(), 0u);

	ufo::presentation::legacy::publishAfterCanonicalCampaignUpdate();
	snapshot = ufo::presentation::latestStrategicSnapshot();
	ASSERT_TRUE(snapshot);
	ASSERT_TRUE(snapshot->ufoRecovery().id.isValid());
	ASSERT_FALSE(snapshot->ufoSaleOffers().empty());
	const ufo::presentation::StrategicUfoSaleOfferView* offer = nullptr;
	for (const ufo::presentation::StrategicUfoSaleOfferView& candidate : snapshot->ufoSaleOffers()) {
		if (candidate.price > 0) {
			offer = &candidate;
			break;
		}
	}
	ASSERT_NE(nullptr, offer);
	EXPECT_EQ(snapshot->ufoRecovery().id, offer->recovery);
	ASSERT_TRUE(offer->id.isValid());

	CP_UpdateCredits(1000);
	const ufo::presentation::StrategicIntentSubmission accept =
		ufo::presentation::intent::submitAcceptUfoSaleOffer(offer->id);
	ASSERT_TRUE(accept.accepted);
	ufo::presentation::legacy::applyPendingStrategicIntents();
	ufo::presentation::StrategicIntentResult acceptResult = {};
	ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&acceptResult));
	ASSERT_EQ(ufo::presentation::StrategicIntentDisposition::Applied, acceptResult.disposition);
	ASSERT_GT(ccs.credits, 1000);
	const int creditsAfterAccept = ccs.credits;
	EXPECT_EQ(nullptr, UR_GetPendingRecovery());
	EXPECT_EQ(0u, UR_GetUfoSaleOfferCount());

	const ufo::presentation::StrategicIntentSubmission replay =
		ufo::presentation::intent::submitAcceptUfoSaleOffer(offer->id);
	ASSERT_TRUE(replay.accepted);
	ufo::presentation::legacy::applyPendingStrategicIntents();
	ufo::presentation::StrategicIntentResult replayResult = {};
	ASSERT_TRUE(ufo::presentation::intent::pollStrategicIntentResult(&replayResult));
	EXPECT_EQ(ufo::presentation::StrategicIntentDisposition::RejectedByCanonical, replayResult.disposition);
	EXPECT_EQ(creditsAfterAccept, ccs.credits);
}

} // namespace

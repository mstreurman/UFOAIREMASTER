#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def body(text, signature):
    start = text.find(signature)
    if start < 0:
        raise AssertionError("missing function: " + signature)
    brace = text.find("{", start)
    depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    raise AssertionError("unterminated function: " + signature)

def require(text, tokens, label):
    for token in tokens:
        if token not in text:
            raise AssertionError(label + ": missing " + token)

def forbid(text, tokens, label):
    for token in tokens:
        if token in text:
            raise AssertionError(label + ": forbidden " + token)

try:
    owner_h = read("src/client/cgame/campaign/cp_mapfightequip.h")
    owner = read("src/client/cgame/campaign/cp_mapfightequip.cpp")
    callbacks = read("src/client/cgame/campaign/cp_fightequip_callbacks.cpp")
    aircraft_h = read("src/client/cgame/campaign/cp_aircraft.h")
    aircraft = read("src/client/cgame/campaign/cp_aircraft.cpp")
    aircraft_callbacks = read("src/client/cgame/campaign/cp_aircraft_callbacks.cpp")
    adapter = read("src/client/presentation/strategic_intent_legacy_adapter.cpp")

    require(owner_h, [
        "aircraftEquipmentMutationResult_t",
        "AII_TryEquipAircraftItem(",
        "AII_TryRemoveAircraftItem(",
    ], "aircraft equipment owner API")

    resolver = body(owner, "static aircraftSlot_t* AII_ResolveAircraftEquipmentSlot (")
    require(resolver, [
        "slotIndex < 0", "case AC_ITEM_AMMO:", "zone != ZONE_AMMO",
        "resolvedType = AC_ITEM_WEAPON", "case AC_ITEM_WEAPON:",
        "case AC_ITEM_SHIELD:", "case AC_ITEM_ELECTRONICS:",
        "zone != ZONE_MAIN", "AII_GetAircraftSlotByIDX(",
    ], "structural aircraft slot resolver")
    forbid(resolver, ["airequipSelectedSlot", "B_GetCurrentSelectedBase("], "structural aircraft slot resolver")

    equip = body(owner, "aircraftEquipmentMutationResult_t AII_TryEquipAircraftItem (")
    require(equip, [
        "AIR_IsUFO(aircraft)", "!aircraft->homebase", "!AIR_IsAircraftInBase(aircraft)",
        "itemIndex < 0", "itemIndex >= cgi->csi->numODs", "INVSH_GetItemByIDX(itemIndex)",
        "item->isVirtual", "ccs.objDefTechs[item->idx]", "RS_IsResearched_ptr(tech)",
        "item->craftitem.type < AC_ITEM_AMMO", "AIM_SelectableCraftItem(slot, tech)",
        "item->craftitem.type != slot->type", "AII_GetItemWeightBySize(item) > slot->size",
        "currentItemWillBeReclaimed", "queuedItemWillBeReclaimed", "B_BaseHasItem(aircraft->homebase, item)",
        "AII_AddAmmoToSlot(base, tech, slot)", "slot->nextItem",
        "slot->installationTime == slot->item->craftitem.installationTime",
        "slot->installationTime == -slot->item->craftitem.installationTime",
        "AII_RemoveNextItemFromSlot(base, slot, false)",
        "AII_AddItemToSlot(base, tech, slot, true)", "AII_AutoAddAmmo(slot)",
        "AII_UpdateAircraftStats(aircraft)",
    ], "aircraft equipment add owner")
    forbid(equip, ["UI_", "Cmd_ExecuteString(", "Cvar_Set(", "airequipSelected"], "aircraft equipment add owner")

    remove = body(owner, "aircraftEquipmentMutationResult_t AII_TryRemoveAircraftItem (")
    require(remove, [
        "AII_ResolveAircraftEquipmentSlot(", "if (!slot->item)",
        "slot->installationTime < slot->item->craftitem.installationTime",
        "AII_RemoveItemFromSlot(base, slot, true)",
        "AII_RemoveItemFromSlot(base, slot, false)",
        "AII_RemoveNextItemFromSlot(base, slot, false)",
        "slot->nextAmmo", "AII_RemoveNextItemFromSlot(base, slot, true)",
        "beforeInstallationTime", "const bool changed", "AII_UpdateAircraftStats(aircraft)",
    ], "aircraft equipment remove owner")
    forbid(remove, ["UI_", "Cmd_ExecuteString(", "Cvar_Set(", "airequipSelected"], "aircraft equipment remove owner")

    legacy_add = body(callbacks, "static void AIM_AircraftEquipAddItem_f (")
    legacy_remove = body(callbacks, "static void AIM_AircraftEquipRemoveItem_f (")
    require(legacy_add, [
        "AIM_CheckAirequipSelectedSlot(aircraft)", "zone != airequipSelectedZone",
        "AII_TryEquipAircraftItem(", "AIM_AircraftEquipMenuUpdate()",
    ], "legacy aircraft equip callback")
    require(legacy_remove, [
        "AIM_CheckAirequipSelectedSlot(aircraft)", "AII_TryRemoveAircraftItem(",
        "AIM_AircraftEquipMenuUpdate()",
    ], "legacy aircraft remove callback")
    for legacy, label in ((legacy_add, "legacy aircraft equip callback"), (legacy_remove, "legacy aircraft remove callback")):
        forbid(legacy, [
            "AII_AddItemToSlot(", "AII_AddAmmoToSlot(", "AII_RemoveItemFromSlot(",
            "AII_RemoveNextItemFromSlot(", "AII_UpdateAircraftStats(",
        ], label + " mutation")

    require(aircraft_h, ["AIR_TrySetName(aircraft_t* aircraft, const char* name);"], "aircraft rename API")
    rename = body(aircraft, "bool AIR_TrySetName (")
    require(rename, [
        "AIR_IsUFO(aircraft)", "Q_strnull(newName)", "_(aircraft->defaultName)",
        "newName[i] > 0x20", "Com_IsValidName(newName)",
        "Q_strncpyz(aircraft->name, newName, sizeof(aircraft->name))",
    ], "aircraft rename owner")
    forbid(rename, ["Cvar_", "UI_", "Cmd_ExecuteString("], "aircraft rename owner")
    legacy_rename = body(aircraft_callbacks, "static void AIR_ChangeAircraftName_f (")
    require(legacy_rename, ["AIR_TrySetName(", 'Cvar_GetString("mn_aircraftname")'], "legacy aircraft rename callback")
    forbid(legacy_rename, ["Q_strncpyz(", "Com_IsValidName("], "legacy aircraft rename mutation")

    for kind, call in (
        ("EquipAircraftItem", "AII_TryEquipAircraftItem("),
        ("RemoveAircraftItem", "AII_TryRemoveAircraftItem("),
        ("RenameAircraft", "AIR_TrySetName("),
    ):
        case = re.search(r"case StrategicIntentKind::" + kind + r"\s*:(.*?)(?=\n\s*case StrategicIntentKind::|\n\s*/\*)", adapter, re.S)
        if not case or call not in case.group(1):
            raise AssertionError(kind + " typed adapter does not reach canonical owner")
    forbid(adapter, ["Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue("], "strategic adapter")

    with (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open() as f:
        cov = {r["semantic_action"]: r for r in csv.DictReader(f, delimiter="\t") if r["domain"] == "strategic"}
    expected_sources = {
        "EquipAircraftItem": "src/client/cgame/campaign/cp_mapfightequip.cpp",
        "RemoveAircraftItem": "src/client/cgame/campaign/cp_mapfightequip.cpp",
        "RenameAircraft": "src/client/cgame/campaign/cp_aircraft.cpp",
    }
    for action, source in expected_sources.items():
        if cov[action]["authority_bridge"] != "canonical_applied":
            raise AssertionError(action + " is not canonical_applied")
        if cov[action]["owner_source"] != source:
            raise AssertionError(action + " owner source mismatch")

    with (ROOT / "tools/remaster/m1-canonical-identity-registry.tsv").open() as f:
        reg = {r["identity"]: r for r in csv.DictReader(f, delimiter="\t")}
    if reg["AircraftEquipmentSlot"]["intent_status"] != "aircraft_equipment_owners_qualified":
        raise AssertionError("AircraftEquipmentSlot structural contract not qualified")
    if reg["AircraftEquipmentSlot"]["mapping_status"] != "structural_tuple":
        raise AssertionError("AircraftEquipmentSlot must remain structural, not a minted runtime ID")
    if reg["ItemId"]["intent_status"] != "create_production_market_aircraft_equipment_owners_qualified":
        raise AssertionError("ItemId aircraft-equipment owner status stale")

    integration = read("tools/remaster/m1-intent-catalog-integration.cpp")
    expansion = read("tools/remaster/test-m1-intent-catalog-expansion.py")
    require(integration, [
        "AircraftConfigurationOwnersPreserveStructuralSlotSemantics",
        "campaign_t* campaign = CatalogCampaign()",
        "RS_InitTree(campaign, false)",
        "base_t base = {}", "aircraft_t aircraft = {}",
        "aircraft.tpl = const_cast<aircraft_t*>(aircraftTemplate)",
        "AIR_TrySetName(&aircraft, \"M1 Configuration Craft\")",
        "AII_TryRemoveAircraftItem(&aircraft, AC_ITEM_WEAPON, 0, ZONE_MAIN)",
        "ASSERT_EQ(-originalItem->craftitem.installationTime, slot->installationTime)",
        "AII_TryEquipAircraftItem(&aircraft, AC_ITEM_WEAPON, 0, ZONE_MAIN, originalItem->idx)",
        "ASSERT_EQ(0, slot->installationTime)",
        "AII_TryRemoveAircraftItem(&aircraft, AC_ITEM_WEAPON, 99, ZONE_MAIN)",
        "AII_TryEquipAircraftItem(&aircraft, AC_ITEM_WEAPON, 0, ZONE_AMMO, originalItem->idx)",
    ], "aircraft configuration runtime integration")
    forbid(integration, [
        "B_SetUpFirstBase" + "(campaign, base);",
        "B_" + "Build(campaign,",
        "AIR_" + "NewAircraft(",
    ], "aircraft configuration runtime integration")
    research_init = integration.find("RS_InitTree(campaign, false)")
    equipment_lookup = integration.find("AII_GetCraftitemTechsByType(AC_ITEM_WEAPON)")
    if research_init < 0 or equipment_lookup < 0 or research_init >= equipment_lookup:
        raise AssertionError("aircraft configuration runtime integration: research tree must initialize before equipment technology lookup")
    require(expansion, ['"[  PASSED  ] 5 tests."', '"  integration GoogleTests: 5/5"'], "aircraft runtime integration gate")

    save_h = read("src/client/cgame/campaign/cp_save.h")
    common_h = read("src/common/common.h")
    if not re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h):
        raise AssertionError("save version changed")
    if not re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h):
        raise AssertionError("protocol version changed")

    print("PASS M1 aircraft configuration owner extraction")
    print("  Equip/Remove: fixed structural AircraftId + slotType/slotIndex/zone re-resolved at execution")
    print("  replacement/install/ammo/storage/stat semantics remain in canonical cp_mapfightequip owner")
    print("  RenameAircraft: canonical validation/default-name restoration in cp_aircraft owner")
    print("  no AircraftEquipmentSlot runtime ID minted")
    print("  authority: strategic 47/57 applied, 10 fail-closed")
    print("  save v4 / protocol 18 unchanged")
except AssertionError as exc:
    print("FAIL M1 aircraft configuration owner extraction: " + str(exc), file=sys.stderr)
    raise SystemExit(1)

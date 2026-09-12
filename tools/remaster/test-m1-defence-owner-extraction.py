#!/usr/bin/env python3
from pathlib import Path
import csv, re, sys
ROOT = Path(__file__).resolve().parents[2]

def read(rel): return (ROOT / rel).read_text(encoding="utf-8")
def body(text, signature):
    start = text.find(signature)
    if start < 0: raise AssertionError("missing function: " + signature)
    brace = text.find("{", start); depth = 0
    for i in range(brace, len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0: return text[start:i+1]
    raise AssertionError("unterminated function: " + signature)
def require(text, tokens, label):
    for token in tokens:
        if token not in text: raise AssertionError(label + ": missing " + token)
def forbid(text, tokens, label):
    for token in tokens:
        if token in text: raise AssertionError(label + ": forbidden " + token)
try:
    base = read("src/client/cgame/campaign/cp_base.h")
    owner_h = read("src/client/cgame/campaign/cp_mapfightequip.h")
    owner = read("src/client/cgame/campaign/cp_mapfightequip.cpp")
    callbacks = read("src/client/cgame/campaign/cp_basedefence_callbacks.cpp")
    popup = read("src/client/cgame/campaign/cp_popup.cpp")
    intent = read("src/client/presentation/strategic_intent.h")
    dispatch = read("src/client/presentation/strategic_intent_dispatch.cpp")
    adapter = read("src/client/presentation/strategic_intent_legacy_adapter.cpp")
    snapshot = read("src/client/presentation/strategic_snapshot.h")
    projection = read("src/client/presentation/strategic_snapshot_legacy_adapter.cpp")

    require(base, ["uint32_t runtimeId;", "Runtime-only logical battery identity; never serialized"], "baseWeapon runtime identity")
    require(owner_h, ["baseDefenceMutationResult_t", "BDEF_GetDefenceSlotRuntimeId(", "BDEF_GetBaseWeaponByRuntimeId(", "BDEF_TryEquipItem(", "BDEF_TryRemoveItem(", "BDEF_TrySetAutoFire(", "BDEF_TrySetTarget("], "defence owner API")
    require(owner, ["BDEF_MintDefenceSlotRuntimeId", "battery->runtimeId = BDEF_MintDefenceSlotRuntimeId()", "laser->runtimeId = BDEF_MintDefenceSlotRuntimeId()", "base->batteries[base->numBatteries].runtimeId = BDEF_MintDefenceSlotRuntimeId()", "REMOVE_ELEM(base->batteries", "REMOVE_ELEM(base->lasers"], "generation-safe compaction identity")
    equip = body(owner, "baseDefenceMutationResult_t BDEF_TryEquipItem (")
    require(equip, ["BDEF_ResolveWeapon(", "BDEF_IsActiveWeapon(", "ccs.objDefTechs[item->idx]", "AIM_SelectableCraftItem(slot, tech)", "AII_RemoveItemFromSlot(storageBase, slot, false)", "AII_AddItemToSlot(storageBase, tech, slot, true)", "AII_AutoAddAmmo(slot)", "Preserve inherited base-defence queue semantics exactly"], "defence equip owner")
    remove = body(owner, "baseDefenceMutationResult_t BDEF_TryRemoveItem (")
    require(remove, ["slot->installationTime < slot->item->craftitem.installationTime", "AII_RemoveItemFromSlot(storageBase, slot, true)", "AII_RemoveItemFromSlot(storageBase, slot, false)", "slot->nextItem"], "defence remove owner")
    auto = body(owner, "baseDefenceMutationResult_t BDEF_TrySetAutoFire (")
    require(auto, ["base->numBatteries", "base->numLasers", "installation->numBatteries", "weapon->target = nullptr"], "aggregate autofire owner")
    target = body(owner, "baseDefenceMutationResult_t BDEF_TrySetTarget (")
    require(target, ["UFO_IsUFOSeenOnGeoscape(ufo)", "AII_BaseCanShoot(base)", "AII_InstallationCanShoot(installation)", "installation->installationTemplate->maxBatteries", "base->numBatteries", "base->numLasers"], "aggregate target owner")
    for signature, label in (("static void BDEF_AddItem_f (void)", "legacy add"), ("static void BDEF_RemoveItem_f (void)", "legacy remove"), ("static void BDEF_ChangeAutoFire (void)", "legacy autofire")):
        require(body(callbacks, signature), ["BDEF_Try"], label)
    forbid(body(callbacks, "static void BDEF_AddItem_f (void)"), ["AII_AddItemToSlot(", "AII_RemoveItemFromSlot("], "legacy add mutation")
    forbid(body(callbacks, "static void BDEF_RemoveItem_f (void)"), ["AII_RemoveItemFromSlot("], "legacy remove mutation")
    popup_fn = body(popup, "static void CL_PopupInterceptBaseClick_f (void)")
    require(popup_fn, ["BDEF_TrySetTarget(base, installation, GEO_GetSelectedUFO())"], "legacy target delegate")
    forbid(popup_fn, ["batteries[i].target = GEO_GetSelectedUFO()", "lasers[i].target = GEO_GetSelectedUFO()"], "legacy target mutation")

    require(intent, ["canonical::DefenceSlotId defenceSlot;", "submitEquipBaseDefenceItem(canonical::BaseId base, canonical::InstallationId installation, canonical::DefenceSlotId defenceSlot, canonical::ItemId item)", "submitRemoveBaseDefenceItem(canonical::BaseId base, canonical::InstallationId installation, canonical::DefenceSlotId defenceSlot)"], "typed DefenceSlotId transport")
    forbid(intent, ["submitEquipBaseDefenceItem(canonical::BaseId base, canonical::InstallationId installation, int32_t defenceType", "submitRemoveBaseDefenceItem(canonical::BaseId base, canonical::InstallationId installation, int32_t defenceType"], "mutable ordinal transport")
    require(dispatch, ["v.defenceSlot = defenceSlot"], "dispatch DefenceSlotId")
    for kind, call in (("EquipBaseDefenceItem", "BDEF_TryEquipItem("), ("RemoveBaseDefenceItem", "BDEF_TryRemoveItem("), ("SetAirDefenceAutoFire", "BDEF_TrySetAutoFire("), ("SetAirDefenceTarget", "BDEF_TrySetTarget(")):
        m = re.search(r"case StrategicIntentKind::" + kind + r"\s*:(.*?)(?=\n\s*case StrategicIntentKind::|\n\s*/\*)", adapter, re.S)
        if not m or call not in m.group(1): raise AssertionError(kind + " adapter owner mapping missing")
    fail = adapter[adapter.find("/* Strict-authority catalog"):]
    for kind in ("EquipBaseDefenceItem", "RemoveBaseDefenceItem", "SetAirDefenceAutoFire", "SetAirDefenceTarget"):
        if "case StrategicIntentKind::" + kind + ":" in fail: raise AssertionError(kind + " remains fail-closed")
    forbid(adapter, ["Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue("], "strategic adapter")

    require(snapshot, ["struct StrategicDefenceSlotView", "canonical::DefenceSlotId id;", "const std::vector<StrategicDefenceSlotView>& defenceSlots() const noexcept"], "defence immutable snapshot")
    require(projection, ["projectDefenceSlot", "BDEF_GetDefenceSlotRuntimeId(&weapon)", "std::vector<StrategicDefenceSlotView> defenceSlots", "std::move(defenceSlots)"], "defence snapshot projection")

    with (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open() as f:
        cov = {r["semantic_action"]: r for r in csv.DictReader(f, delimiter="\t") if r["domain"] == "strategic"}
    for action in ("EquipBaseDefenceItem", "RemoveBaseDefenceItem", "SetAirDefenceAutoFire", "SetAirDefenceTarget"):
        if cov[action]["authority_bridge"] != "canonical_applied": raise AssertionError(action + " not canonical_applied")
        if cov[action]["owner_source"] != "src/client/cgame/campaign/cp_mapfightequip.cpp": raise AssertionError(action + " owner source mismatch")
    with (ROOT / "tools/remaster/m1-canonical-identity-registry.tsv").open() as f:
        reg = {r["identity"]: r for r in csv.DictReader(f, delimiter="\t")}
    d = reg["DefenceSlotId"]
    if (d["classification"], d["mapping_status"], d["publication_status"], d["intent_status"]) != ("runtime_direct", "runtime_mapping_implemented", "published", "defence_owners_qualified"):
        raise AssertionError("DefenceSlotId registry not fully qualified")
    with (ROOT / "tools/remaster/m1-canonical-identity-lifetime-registry.tsv").open() as f:
        life = {r["identity"]: r for r in csv.DictReader(f, delimiter="\t")}
    if life["DefenceSlotId"]["second_pass_status"] != "qualified_runtime_mapping": raise AssertionError("DefenceSlotId lifetime mapping not qualified")
    if "not serialized" not in life["DefenceSlotId"]["save_semantics"]: raise AssertionError("DefenceSlotId runtime-only save contract missing")

    integration = read("tools/remaster/m1-intent-catalog-integration.cpp")
    expansion = read("tools/remaster/test-m1-intent-catalog-expansion.py")
    require(integration, ["DefenceOwnersUseRuntimeIdentityAcrossCompaction", "BDEF_RemoveBattery(&base, BASEDEF_MISSILE, 0)", "EXPECT_EQ(secondId, BDEF_GetDefenceSlotRuntimeId(&base.batteries[0]))", "EXPECT_EQ(nullptr, BDEF_GetBaseWeaponByRuntimeId(&base, firstId))"], "defence runtime integration")
    require(expansion, ['"--gtest_filter=M1IntentCatalogTest.*"'], "defence runtime integration gate")
    save_h = read("src/client/cgame/campaign/cp_save.h"); common = read("src/common/common.h")
    if not re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h): raise AssertionError("save version changed")
    if not re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common): raise AssertionError("protocol version changed")

    print("PASS M1 defence owner extraction")
    print("  DefenceSlotId: runtime-only baseWeapon_t metadata; fresh after load; compaction-safe; stale IDs reject")
    print("  Equip/Remove: explicit BaseId-or-InstallationId + DefenceSlotId + ItemId re-resolution")
    print("  AutoFire/Target: inherited aggregate all-battery semantics preserved")
    print("  aggregate authority accounting is centralized")
    print("  integration ownership: shared M1IntentCatalogTest lane")
    print("  save v4 / protocol 18 unchanged")
except AssertionError as exc:
    print("FAIL M1 defence owner extraction: " + str(exc), file=sys.stderr)
    raise SystemExit(1)

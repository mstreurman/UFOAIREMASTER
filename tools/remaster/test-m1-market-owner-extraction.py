#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

class GateError(RuntimeError):
    pass

def require(cond, message):
    if not cond:
        raise GateError(message)

def text(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def function_body(source, signature):
    start = source.find(signature)
    require(start >= 0, "missing function: " + signature)
    brace = source.find("{", start)
    require(brace >= 0, "missing function body: " + signature)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise GateError("unterminated function: " + signature)

def main():
    market_h = text("src/client/cgame/campaign/cp_market.h")
    market_cpp = text("src/client/cgame/campaign/cp_market.cpp")
    market_cb = text("src/client/cgame/campaign/cp_market_callbacks.cpp")
    adapter = text("src/client/presentation/strategic_intent_legacy_adapter.cpp")

    owners = (
        "BS_TryBuyAircraft", "BS_TryBuyItem", "BS_TryBuyUGV",
        "BS_TrySellAircraft", "BS_TrySellItem", "BS_TrySellUGV",
        "BS_TrySetAutoSellPolicy",
    )
    for token in owners + ("BS_IsMutationAccepted",):
        require(token in market_h and token in market_cpp, "Market owner missing: " + token)

    for signature in (
        "marketMutationResult_t BS_TryBuyAircraft",
        "marketMutationResult_t BS_TryBuyItem",
        "marketMutationResult_t BS_TryBuyUGV",
        "marketMutationResult_t BS_TrySellAircraft",
        "marketMutationResult_t BS_TrySellItem",
        "marketMutationResult_t BS_TrySellUGV",
        "marketMutationResult_t BS_TrySetAutoSellPolicy",
    ):
        owner = function_body(market_cpp, signature)
        for banned in ("UI_", "Cvar_", "Cbuf_", "Cmd_", "CP_Popup"):
            require(banned not in owner, signature + ": presentation behavior leaked into canonical owner: " + banned)

    buy_aircraft = function_body(market_cpp, "marketMutationResult_t BS_TryBuyAircraft")
    for token in (
        "B_GetFoundedBaseByIDX(baseIdx)", "AIR_GetAircraftSilent(aircraftDefinition)",
        "B_GetBuildingStatus(base, B_COMMAND)", "B_GetBuildingStatus(base, B_POWER)",
        "AIR_AircraftAllowed(base)", "CAP_GetFreeCapacity(base, AIR_GetHangarCapacityType(aircraft))",
        "BS_GetAircraftOnMarket(aircraft)", "BS_GetAircraftBuyingPrice(aircraft)", "BS_BuyAircraft(aircraft, base)",
    ):
        require(token in buy_aircraft, "BuyAircraft owner contract missing: " + token)

    buy_item = function_body(market_cpp, "marketMutationResult_t BS_TryBuyItem")
    require("std::min(requestedCount, BS_GetItemOnMarket(od))" in buy_item, "BuyItem lost market-stock partial fill")
    require("std::min(count, ccs.credits / price)" in buy_item, "BuyItem lost credit partial fill")
    require("std::min(count, CAP_GetFreeCapacity(base, CAP_ITEMS) / od->size)" in buy_item, "BuyItem lost storage partial fill")
    require("count < requestedCount" in buy_item and "BS_MARKET_MUTATION_APPLIED_PARTIAL" in buy_item, "BuyItem must report partial application")
    require("BS_BuyItem(od, base, count)" in buy_item, "BuyItem must delegate final mutation to strict low-level helper")
    low_buy_item = function_body(market_cpp, "bool BS_BuyItem")
    for token in ("B_AddToStorage(base, od, count)", "BS_RemoveItemFromMarket(od, count)", "CP_UpdateCredits(ccs.credits - BS_GetItemBuyingPrice(od) * count)"):
        require(token in low_buy_item, "strict item-buy delta contract missing: " + token)

    sell_item = function_body(market_cpp, "marketMutationResult_t BS_TrySellItem")
    require("std::min(requestedCount, B_ItemInBase(od, base))" in sell_item, "SellItem lost base-stock partial fill")
    require("BS_GetItemSellingPrice" not in sell_item, "SellItem invented a sale-price eligibility rule")
    require("BS_SellItem(od, base, count)" in sell_item, "SellItem must delegate final mutation to strict low-level helper")
    low_sell_item = function_body(market_cpp, "bool BS_SellItem")
    for token in ("B_AddToStorage(base, od, -count)", "BS_AddItemToMarket(od, count)", "CP_UpdateCredits(ccs.credits + BS_GetItemSellingPrice(od) * count)"):
        require(token in low_sell_item, "strict item-sell delta contract missing: " + token)

    sell_aircraft = function_body(market_cpp, "marketMutationResult_t BS_TrySellAircraft")
    require(sell_aircraft.index("AIR_IsAircraftInBase(aircraft)") < sell_aircraft.index("AIR_RemoveEmployees(*aircraft)"),
            "SellAircraft must prove in-base state before crew mutation")
    require(sell_aircraft.index("AIR_RemoveEmployees(*aircraft)") < sell_aircraft.index("BS_SellAircraft(aircraft)"),
            "SellAircraft must remove crew before strict sale")
    low_sell_aircraft = function_body(market_cpp, "bool BS_SellAircraft")
    require("BS_ProcessCraftItemSale" in low_sell_aircraft and "AIR_DeleteAircraft(aircraft)" in low_sell_aircraft,
            "strict aircraft sale no longer preserves equipment return / AIR_DeleteAircraft lifecycle")

    buy_ugv = function_body(market_cpp, "marketMutationResult_t BS_TryBuyUGV")
    for token in (
        "E_CountUnhiredRobotsByType(ugv)", "BS_GetItemOnMarket(ugvWeapon)",
        "ccs.credits < ugv->price", "UGV_SIZE + ugvWeapon->size", "BS_BuyUGV(ugv, base)",
    ):
        require(token in buy_ugv, "BuyUGV owner lost inherited coupling: " + token)

    sell_ugv = function_body(market_cpp, "marketMutationResult_t BS_TrySellUGV")
    require("E_GetEmployeeByTypeFromChrUCN(EMPL_ROBOT, employeeUcn)" in sell_ugv, "SellUGV must re-resolve EmployeeId/UCN as robot")
    require("robot->transfer" in sell_ugv, "SellUGV must preserve transfer rejection")
    require("isAwayFromBase" not in sell_ugv, "SellUGV must not invent blanket away-from-base rejection")
    require("BS_SellUGV(robot)" in sell_ugv, "SellUGV must retain canonical Employee::unhire path")
    low_sell_ugv = function_body(market_cpp, "bool BS_SellUGV")
    require("robot->unhire()" in low_sell_ugv, "low-level UGV sale no longer preserves Employee::unhire semantics")
    for token in ("BS_AddItemToMarket(ugvWeapon, 1)", "CP_UpdateCredits(ccs.credits + ugv->price)", "B_AddToStorage(base, ugvWeapon, -1)"):
        require(token in low_sell_ugv, "strict UGV-sale delta contract missing: " + token)

    autosell = function_body(market_cpp, "marketMutationResult_t BS_TrySetAutoSellPolicy")
    for token in ("od->isVirtual", "od->notOnMarket", "RS_GetTechForItem(od)", "RS_IsResearched_ptr(tech)"):
        require(token in autosell, "autosell desired-state contract missing: " + token)
    require("ccs.eMarket.autosell[od->idx] = enabled;" in autosell, "autosell owner must assign the explicit desired state")
    require("BS_MARKET_MUTATION_NO_CHANGE" in autosell, "autosell explicit true/false must be idempotent")
    require("!ccs.eMarket.autosell" not in autosell, "canonical autosell owner must not toggle")

    legacy_buy = function_body(market_cb, "static void BS_Buy_f")
    for token in ("BS_TryBuyAircraft(", "BS_TryBuyItem(", "BS_TryBuyUGV(", "BS_TrySellAircraft(", "BS_TrySellItem(", "BS_TrySellUGV("):
        require(token in legacy_buy, "legacy Market callback does not converge on owner: " + token)
    for token in ("BS_BuyAircraft(", "BS_BuyItem(", "BS_BuyUGV(", "BS_SellAircraft(", "BS_SellItem(", "BS_SellUGV(", "AIR_RemoveEmployees("):
        require(token not in legacy_buy, "legacy Market callback still owns canonical mutation/normalization: " + token)
    legacy_autosell = function_body(market_cb, "static void BS_SetAutosell_f")
    require("BS_TrySetAutoSellPolicy(" in legacy_autosell, "legacy autosell does not converge on canonical desired-state owner")
    require("? atoi(cgi->Cmd_Argv(2)) != 0" in legacy_autosell and ": !ccs.eMarket.autosell[od->idx]" in legacy_autosell,
            "legacy toggle must normalize to explicit desired bool before owner invocation")

    actions = ("BuyAircraft", "BuyItem", "BuyUGV", "SellAircraft", "SellItem", "SellUGV", "SetAutoSellPolicy")
    fail_block = adapter[adapter.index("/* Strict-authority catalog is transport-complete"):]
    for action in actions:
        require("case StrategicIntentKind::" + action + ":" in adapter, "typed owner case missing: " + action)
        require("case StrategicIntentKind::" + action + ":" not in fail_block, action + " remains fail-closed")
    for token in owners:
        require(token + "(" in adapter or token == "BS_TrySetAutoSellPolicy" and "BS_TrySetAutoSellPolicy(" in adapter,
                "typed adapter does not invoke owner: " + token)
    for banned in ("Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue("):
        require(banned not in adapter, "typed strategic adapter contains banned fallback: " + banned)

    require("SAVE_MARKET_AUTOSELL, market->autosell[i]" in market_cpp, "autosell save persistence regressed")
    require("market->autosell[od->idx] = cgi->XML_GetBool" in market_cpp, "autosell load persistence regressed")

    coverage = list(csv.DictReader((ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open(encoding="utf-8"), delimiter="\t"))
    strategic = {r["semantic_action"]: r for r in coverage if r["domain"] == "strategic"}
    for action in actions:
        require(strategic[action]["authority_bridge"] == "canonical_applied", action + " is not canonical_applied")
    require(sum(r["authority_bridge"] == "canonical_applied" for r in strategic.values()) == 38, "strategic canonical-applied accounting must be 38")
    require(sum(r["authority_bridge"] == "owner_extraction_pending_fail_closed" for r in strategic.values()) == 20, "strategic fail-closed accounting must be 20")

    common_h = text("src/common/common.h")
    save_h = text("src/client/cgame/campaign/cp_save.h")
    require(re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h) is not None, "protocol version changed from 18")
    require(re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h) is not None, "save version changed from 4")

    print("PASS M1 Market canonical owner extraction")
    print("PASS partial-fill item buy/sell and aircraft/UGV lifecycle preservation guards")
    print("PASS legacy and typed Market paths converge on seven campaign owners")
    print("PASS autosell explicit desired state + existing save persistence")
    print("PASS authority accounting: strategic 38/20; tactical unchanged 13/2")
    print("PASS save v4 and protocol 18 unchanged")

if __name__ == "__main__":
    try:
        main()
    except GateError as exc:
        print("FAIL M1 Market owner extraction: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

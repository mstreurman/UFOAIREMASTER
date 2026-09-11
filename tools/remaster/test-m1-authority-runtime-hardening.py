#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

class GateError(RuntimeError):
    pass

def require(cond, msg):
    if not cond:
        raise GateError(msg)

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def function_body(text, signature):
    pos = text.find(signature)
    require(pos >= 0, "missing function: " + signature)
    start = text.find("{", pos)
    require(start >= 0, "missing body: " + signature)
    depth = 0
    state = "code"
    i = start
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ""
        if state == "code":
            if c == "/" and n == "/":
                state = "line"; i += 1
            elif c == "/" and n == "*":
                state = "block"; i += 1
            elif c == '"':
                state = "string"
            elif c == "'":
                state = "char"
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[pos:i + 1]
        elif state == "line":
            if c == "\n":
                state = "code"
        elif state == "block":
            if c == "*" and n == "/":
                state = "code"; i += 1
        elif state == "string":
            if c == "\\":
                i += 1
            elif c == '"':
                state = "code"
        elif state == "char":
            if c == "\\":
                i += 1
            elif c == "'":
                state = "code"
        i += 1
    raise GateError("unterminated function: " + signature)

def main():
    building_h = read("src/client/cgame/campaign/cp_building.h")
    base_h = read("src/client/cgame/campaign/cp_base.h")
    base_cpp = read("src/client/cgame/campaign/cp_base.cpp")
    aircraft_h = read("src/client/cgame/campaign/cp_aircraft.h")
    aircraft_cpp = read("src/client/cgame/campaign/cp_aircraft.cpp")
    market_cpp = read("src/client/cgame/campaign/cp_market.cpp")
    intent_h = read("src/client/presentation/strategic_intent.h")
    dispatch = read("src/client/presentation/strategic_intent_dispatch.cpp")
    adapter = read("src/client/presentation/strategic_intent_legacy_adapter.cpp")
    snapshot_h = read("src/client/presentation/strategic_snapshot.h")
    snapshot_cpp = read("src/client/presentation/strategic_snapshot_legacy_adapter.cpp")

    require("uint32_t runtimeId;" in building_h, "building_t runtime FacilityId missing")
    require("B_GetFacilityByRuntimeId(" in base_h, "FacilityId resolver declaration missing")
    require("B_TryDestroyFacilityById(" in base_h, "FacilityId destroy owner declaration missing")
    require("buildingNew->runtimeId = B_AllocateFacilityRuntimeId();" in base_cpp,
            "new facility runtime identity assignment missing")
    require("building->runtimeId = B_AllocateFacilityRuntimeId();" in base_cpp,
            "load-time facility runtime identity reconstruction missing")

    build = function_body(base_cpp, "facilityBuildResult_t B_TryBuildFacility (")
    for token in (
        "buildingTemplate->mandatory",
        "RS_IsResearched_ptr(buildingTemplate->tech)",
        "buildingTemplate->maxCount >= 0",
        "B_GetNumberOfBuildingsInBaseByTemplate(base, buildingTemplate)",
    ):
        require(token in build, "BuildFacility eligibility missing: " + token)

    destroy = function_body(base_cpp, "facilityDestroyResult_t B_TryDestroyFacilityById (")
    require("B_GetFacilityByRuntimeId(base, runtimeId)" in destroy,
            "DestroyFacility does not re-resolve FacilityId")

    require("canonical::FacilityId facility;" in intent_h, "typed FacilityId payload missing")
    require("submitDestroyFacility(canonical::BaseId base, canonical::FacilityId facility)" in intent_h,
            "DestroyFacility API still transports compacting facilityIndex")
    require("v.facility = facility" in dispatch, "DestroyFacility dispatcher does not carry FacilityId")
    require("B_TryDestroyFacilityById(b,in.facility.value)" in adapter,
            "legacy adapter does not re-resolve FacilityId")
    require("struct StrategicFacilityView" in snapshot_h, "facility publication view missing")
    require("canonical::FacilityId id;" in snapshot_h, "facility publication identity missing")
    require("B_GetFacilityRuntimeId(&facility)" in snapshot_cpp,
            "facility snapshot does not publish runtime identity")

    stop = function_body(aircraft_cpp, "bool AIR_TryStopAircraft (")
    require("AIR_IsAircraftOnGeoscape(aircraft)" in stop, "StopAircraft state guard missing")

    pursuit = function_body(aircraft_cpp, "aircraftPursuitResult_t AIR_TryPursueUFO (")
    require("AIR_CanIntercept(aircraft)" in pursuit, "PursueUfo inherited intercept gate missing")
    require("AIR_PURSUIT_NOT_INTERCEPTABLE" in aircraft_h, "pursuit rejection result missing")

    mission = function_body(aircraft_cpp, "aircraftMissionSendResult_t AIR_TrySendAircraftToMission (")
    for token in ("AIR_GetTeamSize(", "AII_ReloadAircraftWeapons(", "GEO_SetInterceptorAircraft(",
                  "B_IsUnderAttack(", "AIR_AircraftHasEnoughFuel(", "GEO_CalcLine("):
        require(token in mission, "mission owner lost inherited behavior: " + token)
    for forbidden in ("UI_", "CP_Popup(", "MS_AddNewMessage("):
        require(forbidden not in mission, "mission owner still contains presentation side effect: " + forbidden)
    wrapper = function_body(aircraft_cpp, "bool AIR_SendAircraftToMission (")
    for token in ("AIR_TrySendAircraftToMission(", 'UI_PushWindow("popup_baseattack")',
                  "CP_Popup(", "MS_AddNewMessage("):
        require(token in wrapper, "legacy mission wrapper lost presentation behavior: " + token)
    require("AIR_TrySendAircraftToMission(a,m)" in adapter,
            "typed mission intent still enters presentation wrapper")

    buy_air = function_body(market_cpp, "marketMutationResult_t BS_TryBuyAircraft (")
    require("RS_IsResearched_ptr(aircraft->tech)" in buy_air,
            "BuyAircraft research gate missing")
    buy_ugv = function_body(market_cpp, "marketMutationResult_t BS_TryBuyUGV (")
    require("RS_GetTechByProvided(ugv->id)" in buy_ugv and "RS_IsResearched_ptr(tech)" in buy_ugv,
            "BuyUGV research gate missing")
    buy_item = function_body(market_cpp, "marketMutationResult_t BS_TryBuyItem (")
    require("RS_IsResearched_ptr" not in buy_item,
            "BuyItem incorrectly inherited aircraft/UGV-only research restriction")

    common_h = read("src/common/common.h")
    save_h = read("src/client/cgame/campaign/cp_save.h")
    require(re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h) is not None,
            "protocol version changed")
    require(re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h) is not None,
            "save version changed")

    print("PASS M1 runtime authority hardening")
    print("PASS FacilityId is runtime-only and published; save v4 unchanged")
    print("PASS BuildFacility / StopAircraft / PursueUfo / mission-send / Market gates hardened")
    print("PASS protocol 18 unchanged")

if __name__ == "__main__":
    try:
        main()
    except GateError as exc:
        print("FAIL M1 runtime authority hardening: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

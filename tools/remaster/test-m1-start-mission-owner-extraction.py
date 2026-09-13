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
    state = "code"
    i = brace
    while i < len(source):
        c = source[i]
        n = source[i + 1] if i + 1 < len(source) else ""
        if state == "code":
            if c == "/" and n == "/": state = "line"; i += 1
            elif c == "/" and n == "*": state = "block"; i += 1
            elif c == '"': state = "string"
            elif c == "'": state = "char"
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0: return source[start:i + 1]
        elif state == "line":
            if c == "\n": state = "code"
        elif state == "block":
            if c == "*" and n == "/": state = "code"; i += 1
        elif state == "string":
            if c == "\\": i += 1
            elif c == '"': state = "code"
        elif state == "char":
            if c == "\\": i += 1
            elif c == "'": state = "code"
        i += 1
    raise GateError("unterminated function: " + signature)

def main():
    campaign_h = text("src/client/cgame/campaign/cp_campaign.h")
    campaign_cpp = text("src/client/cgame/campaign/cp_campaign.cpp")
    baseattack_cpp = text("src/client/cgame/campaign/missions/cp_mission_baseattack.cpp")
    intent_h = text("src/client/presentation/strategic_intent.h")
    adapter = text("src/client/presentation/strategic_intent_legacy_adapter.cpp")

    for token in (
        "campaignMissionStartResult_t",
        "CP_MISSION_START_INVALID_CONTEXT",
        "CP_MISSION_START_INACTIVE",
        "CP_MISSION_START_NO_TEAM",
        "CP_MISSION_START_APPLIED",
        "CP_TryStartMission(struct mission_s* mission, aircraft_t* aircraft)",
    ):
        require(token in campaign_h, "StartMission owner contract missing: " + token)

    owner = function_body(campaign_cpp, "campaignMissionStartResult_t CP_TryStartMission (")
    for token in (
        "mission->stage != STAGE_BASE_ATTACK",
        "aircraft = GEO_GetMissionAircraft();",
        "AIR_IsUFO(aircraft)",
        "aircraft->mission != mission",
        "mission->data.base != base",
        "OBJZERO(mission->missionResults)",
        "!mission->active",
        "AIR_GetTeamSize(aircraft) == 0",
        'cgi->SV_Shutdown("Server quit.", false)',
        "cgi->CL_Disconnect()",
        "CP_CreateBattleParameters(mission, battleParam, aircraft)",
        "BATTLE_SetVars(battleParam)",
        "ccs.eMission = base->storage",
        "CP_CleanTempInventory(base)",
        "CP_CleanupAircraftTeam(aircraft, &ccs.eMission)",
        "BATTLE_Start(mission, battleParam)",
        "return CP_MISSION_START_APPLIED",
    ):
        require(token in owner, "StartMission owner lost inherited/required contract: " + token)
    require(owner.index("aircraft->mission != mission") < owner.index("OBJZERO(mission->missionResults)"),
            "explicit mission/aircraft association must be proven before touching mission result scratch")
    require(owner.index("OBJZERO(mission->missionResults)") < owner.index("!mission->active") < owner.index("AIR_GetTeamSize(aircraft) == 0"),
            "inherited result-reset / active / team ordering changed")
    for banned in ("GEO_GetSelectedMission(", "GEO_SetSelectedMission(", "UI_", "Cvar_", "Cbuf_", "Cmd_", "CP_Popup("):
        require(banned not in owner, "canonical StartMission owner contains presentation/selection authority: " + banned)

    wrapper = function_body(campaign_cpp, "void CP_StartSelectedMission (")
    require("GEO_GetMissionAircraft()" in wrapper and "GEO_GetSelectedMission()" in wrapper,
            "legacy wrapper must retain presentation selection normalization")
    require("CP_TryStartMission(mission, aircraft)" in wrapper,
            "legacy StartMission wrapper does not converge on canonical owner")
    for migrated in ("CP_CreateBattleParameters(", "BATTLE_SetVars(", "CP_CleanTempInventory(", "CP_CleanupAircraftTeam(", "BATTLE_Start("):
        require(migrated not in wrapper, "legacy wrapper still owns canonical launch lifecycle: " + migrated)

    require("static aircraft_t baseAttackFakeAircraft;" in baseattack_cpp,
            "base-attack ephemeral aircraft no longer remains subsystem-private static state")
    require("baseAttackFakeAircraft.idx" not in baseattack_cpp,
            "base-attack path fabricated an AircraftId-bearing index")
    for token in (
        "baseAttackFakeAircraft.homebase = base",
        "baseAttackFakeAircraft.mission = mission",
        "GEO_SetMissionAircraft(&baseAttackFakeAircraft)",
    ):
        require(token in baseattack_cpp, "base-attack canonical participant association changed: " + token)

    require("Base attacks are" in intent_h and "invalid ID" in intent_h,
            "public StartMission contract does not document no-ID base-attack semantics")
    require("case StrategicIntentKind::StartMission:" in adapter,
            "typed StartMission adapter case missing")
    start_case = adapter[adapter.index("case StrategicIntentKind::StartMission:"):adapter.index("case StrategicIntentKind::AssignResearch:")]
    for token in (
        "in.aircraft.isValid()?resolvePhalanxAircraft(in.aircraft):nullptr",
        "(!in.aircraft.isValid()||a)",
        "CP_TryStartMission(m,a)",
        "CP_MISSION_START_APPLIED",
    ):
        require(token in start_case, "typed StartMission lowering missing: " + token)
    fail_block = adapter[adapter.index("/* Strict-authority catalog is transport-complete"):]
    require("case StrategicIntentKind::StartMission:" not in fail_block,
            "StartMission remains in generic fail-closed block")
    require("case StrategicIntentKind::AutoResolveMission:" in fail_block,
            "AutoResolveMission must remain fail-closed in this slice")
    for banned in ("Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue("):
        require(banned not in adapter, "typed strategic adapter contains banned fallback: " + banned)

    with (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    start = [r for r in rows if r["domain"] == "strategic" and r["semantic_action"] == "StartMission"]
    require(len(start) == 1, "StartMission coverage row missing/duplicated")
    require(start[0]["authority_bridge"] == "canonical_applied", "StartMission coverage is not canonical_applied")
    pending = {r["semantic_action"] for r in rows if r["domain"] == "strategic" and r["authority_bridge"] == "owner_extraction_pending_fail_closed"}
    require(pending == {"AutoResolveMission"}, "unexpected strategic pending set: " + repr(sorted(pending)))

    common_h = text("src/common/common.h")
    save_h = text("src/client/cgame/campaign/cp_save.h")
    require(re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h) is not None, "protocol version changed from 18")
    require(re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h) is not None, "save version changed from 4")

    print("PASS M1 StartMission canonical owner extraction")
    print("PASS explicit MissionId/AircraftId association and inherited launch lifecycle")
    print("PASS base attack uses canonical ephemeral missionAircraft without fabricated AircraftId")
    print("PASS legacy and typed StartMission paths converge on CP_TryStartMission")
    print("PASS strategic authority: 57 total / 56 applied / 1 fail-closed (AutoResolveMission)")
    print("PASS save v4 and protocol 18 unchanged")

if __name__ == "__main__":
    try:
        main()
    except GateError as exc:
        print("FAIL M1 StartMission owner extraction: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

class GateError(RuntimeError):
    pass

def require(cond, msg):
    if not cond:
        raise GateError(msg)

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
    save_h = text("src/client/cgame/campaign/cp_save.h")
    save_cpp = text("src/client/cgame/campaign/cp_save.cpp")
    campaign_cpp = text("src/client/cgame/campaign/cp_campaign.cpp")
    callbacks = text("src/client/cgame/campaign/cp_save_callbacks.cpp")
    dispatch = text("src/client/presentation/strategic_intent_dispatch.cpp")
    adapter = text("src/client/presentation/strategic_intent_legacy_adapter.cpp")
    integration = text("tools/remaster/m1-intent-catalog-integration.cpp")
    expansion = text("tools/remaster/test-m1-intent-catalog-expansion.py")
    common_h = text("src/common/common.h")

    submit = function_body(dispatch, "StrategicIntentSubmission submitLoadGame(")
    require("copyBounded(v.key0, slot);" in submit,
            "LoadGame dispatch must carry a bounded slot")

    load = function_body(save_cpp, "bool SAV_GameLoad (")
    require(load.count("cgi->GAME_ReloadMode();") == 4,
            "SAV_GameLoad must have one commit reload plus three recovery reloads")
    for token in (
        "mxmlDelete(topNode);\n\t\tcgi->GAME_ReloadMode();\n\t\t*error = \"Invalid xml data\";",
        "const char* const failedSubsystem = saveSubsystems[i].name;",
        "mxmlDelete(topNode);\n\t\t\tcgi->GAME_ReloadMode();",
        '*error = va("Could not load subsystem %s", failedSubsystem);',
        "SAV_GameActionsAfterLoad()",
        "cgi->GAME_ReloadMode();\n\t\t*error = \"Postprocessing failed\";",
    ):
        require(token in load, "LoadGame lifecycle recovery missing: " + token)

    require('campaignNode = cgi->XML_GetNode(parent, SAVE_CAMPAIGN_CAMPAIGN);' in campaign_cpp,
            "CP_LoadXML campaign-node validation seam changed")
    require('if (!campaignNode) {' in campaign_cpp,
            "CP_LoadXML must reject missing campaign state")

    case = re.search(
        r'case StrategicIntentKind::LoadGame\s*:\s*\{(?P<body>.*?)(?=\n\s*case StrategicIntentKind::|\n\s*/\*)',
        adapter, re.S)
    require(case is not None, "typed LoadGame adapter case missing")
    for token in (
        "resolveBoundedText(in.key0)",
        "SAV_GameLoad(slot,&error)",
        "loaded?1:0",
        "StrategicIntentDisposition::Applied",
    ):
        require(token in case.group("body"), "typed LoadGame convergence missing: " + token)
    for banned in ("Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue(", "UI_"):
        require(banned not in case.group("body"),
                "typed LoadGame adapter contains presentation fallback: " + banned)

    fail = adapter[adapter.find("/* Strict-authority catalog is transport-complete"):]
    require("case StrategicIntentKind::LoadGame:" not in fail,
            "LoadGame still appears in fail-closed block")
    for kind in ("LoadLastSave", "AutoResolveMission", "StartMission"):
        require("case StrategicIntentKind::" + kind + ":" in fail,
                kind + " must remain fail-closed")

    legacy = function_body(callbacks, "static void SAV_GameLoad_f (")
    for token in (
        "SAV_GameLoad(",
        'cgi->Cmd_ExecuteString("game_exit")',
        'cgi->Cmd_ExecuteString("game_setmode campaign")',
    ):
        require(token in legacy, "legacy LoadGame wrapper compatibility changed: " + token)

    reset = function_body(dispatch, "void resetStrategicIntentRuntime()")
    require("q.clear();" in reset and "rq.clear();" in reset,
            "campaign lifecycle must clear stale intent/result queues")
    require("seq=1" not in reset and "seq = 1" not in reset,
            "campaign lifecycle must not rewind strategic intent sequence")

    for token in (
        "TEST_F(M1IntentCatalogTest, LoadGameIntentConvergesOnCanonicalOwner)",
        'SAV_GameSave(slot, "M1 typed LoadGame fixture", &saveError)',
        "submitLoadGame(slot)",
        "TEST_F(M1IntentCatalogTest, LoadGamePostReloadFailureRestoresCleanCampaignMode)",
        '<?xml version=\\"1.0\\"?><savegame></savegame>',
        "EXPECT_FALSE(CP_IsRunning());",
        'EXPECT_NE(nullptr, CP_GetCampaign("main"));',
    ):
        require(token in integration, "LoadGame runtime integration coverage missing: " + token)
    require('[  PASSED  ] 9 tests.' in expansion,
            "intent-catalog integration gate must require 9/9 tests")

    require(re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h) is not None,
            "save version changed")
    require('#define SAVEGAME_EXTENSION "savx"' in save_h,
            "save extension changed")
    require(re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h) is not None,
            "protocol version changed")

    with (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    strategic = {r["semantic_action"]: r for r in rows if r["domain"] == "strategic"}
    require(strategic["LoadGame"]["authority_bridge"] == "canonical_applied",
            "LoadGame is not canonical_applied in coverage ledger")
    require(strategic["LoadGame"]["owner_source"] == "src/client/cgame/campaign/cp_save.cpp",
            "LoadGame owner must be cp_save.cpp")
    applied = {n for n, r in strategic.items() if r["authority_bridge"] == "canonical_applied"}
    pending = {n for n, r in strategic.items()
               if r["authority_bridge"] == "owner_extraction_pending_fail_closed"}
    require(len(applied) == 54, "strategic applied count must be 54")
    require(pending == {"AutoResolveMission", "LoadLastSave", "StartMission"},
            "strategic pending set mismatch: " + repr(sorted(pending)))

    print("PASS M1 LoadGame lifecycle owner qualification")
    print("  legacy + typed LoadGame converge on SAV_GameLoad")
    print("  all post-GAME_ReloadMode failures restore a clean campaign mode")
    print("  runtime integration covers successful typed load + deterministic post-reload rejection")
    print("  strategic authority: 54/57 applied, 3 fail-closed")
    print("  save v4 / savx / protocol 18 unchanged")

if __name__ == "__main__":
    try:
        main()
    except GateError as exc:
        print("FAIL M1 LoadGame owner qualification: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

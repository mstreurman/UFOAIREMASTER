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
    callbacks = text("src/client/cgame/campaign/cp_save_callbacks.cpp")
    intent_h = text("src/client/presentation/strategic_intent.h")
    dispatch = text("src/client/presentation/strategic_intent_dispatch.cpp")
    adapter = text("src/client/presentation/strategic_intent_legacy_adapter.cpp")
    integration = text("tools/remaster/m1-intent-catalog-integration.cpp")
    expansion = text("tools/remaster/test-m1-intent-catalog-expansion.py")
    common_h = text("src/common/common.h")

    require("submitLoadLastSave(const char* resolvedSlot)" in intent_h,
            "LoadLastSave must require explicit resolved slot context")
    require("submitLoadLastSave()" not in intent_h,
            "no-argument LoadLastSave transport remains public")

    submit = function_body(dispatch, "StrategicIntentSubmission submitLoadLastSave(")
    for token in (
        "StrategicIntentKind::LoadLastSave",
        "copyBounded(v.key0, resolvedSlot);",
    ):
        require(token in submit, "LoadLastSave bounded transport missing: " + token)
    for banned in ("Cvar_Get(", "Cvar_Set(", "cl_lastsave"):
        require(banned not in submit,
                "dispatch must not resolve archived last-save context: " + banned)

    case = re.search(
        r'case StrategicIntentKind::LoadLastSave\s*:\s*\{(?P<body>.*?)(?=\n\s*case StrategicIntentKind::|\n\s*/\*)',
        adapter, re.S)
    require(case is not None, "typed LoadLastSave adapter case missing")
    body = case.group("body")
    for token in (
        "resolveBoundedText(in.key0)",
        "!cgi->CL_OnBattlescape()",
        "!CP_IsRunning()",
        "SAV_GameLoad(slot,&error)",
        "loaded?1:0",
        "StrategicIntentDisposition::Applied",
    ):
        require(token in body, "LoadLastSave split/owner convergence missing: " + token)
    for banned in (
        "Cvar_Get(", "Cvar_Set(", "Cvar_SetValue(", "cl_lastsave",
        "Cmd_ExecuteString(", "Cbuf_AddText(", "UI_",
    ):
        require(banned not in body,
                "typed LoadLastSave adapter contains hidden-context/presentation fallback: " + banned)

    fail = adapter[adapter.find("/* Strict-authority catalog is transport-complete"):]
    require("case StrategicIntentKind::LoadLastSave:" not in fail,
            "LoadLastSave still appears in fail-closed block")
    for kind in ("AutoResolveMission", "StartMission"):
        require("case StrategicIntentKind::" + kind + ":" in fail,
                kind + " must remain fail-closed")

    legacy = function_body(callbacks, "static void SAV_GameContinue_f (")
    for token in (
        "cgi->CL_OnBattlescape()",
        "!CP_IsRunning()",
        "SAV_GameLoad(cl_lastsave->string, &error)",
        "cgi->UI_PopWindow(false)",
    ):
        require(token in legacy, "legacy game_continue split changed: " + token)
    require('cl_lastsave = cgi->Cvar_Get("cl_lastsave", "", CVAR_ARCHIVE' in callbacks,
            "archived cl_lastsave application context disappeared")

    for token in (
        "TEST_F(M1IntentCatalogTest, LoadLastSaveExplicitSlotPreservesContinueSplit)",
        'SAV_GameSave(slot, "M1 typed LoadLastSave fixture", &saveError)',
        "submitLoadLastSave(slot)",
        "EXPECT_TRUE(CP_IsRunning());",
        "cgi->GAME_ReloadMode();",
        "ASSERT_FALSE(CP_IsRunning());",
        "StrategicIntentDisposition::RejectedByCanonical",
        "StrategicIntentDisposition::Applied",
    ):
        require(token in integration,
                "LoadLastSave runtime split coverage missing: " + token)
    require('[  PASSED  ] 10 tests.' in expansion,
            "intent-catalog integration lane must require 10/10 tests")

    require(re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h) is not None,
            "save version changed")
    require('#define SAVEGAME_EXTENSION "savx"' in save_h,
            "save extension changed")
    require(re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h) is not None,
            "protocol version changed")

    with (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    strategic = {r["semantic_action"]: r for r in rows if r["domain"] == "strategic"}
    row = strategic["LoadLastSave"]
    require(row["authority_bridge"] == "canonical_applied",
            "LoadLastSave is not canonical_applied")
    require(row["owner_source"] == "src/client/cgame/campaign/cp_save.cpp",
            "LoadLastSave must converge on SAV_GameLoad owner in cp_save.cpp")
    require("explicit bounded slot" in row["note"],
            "coverage note must record explicit presentation-resolved slot boundary")

    applied = {n for n, r in strategic.items() if r["authority_bridge"] == "canonical_applied"}
    pending = {n for n, r in strategic.items()
               if r["authority_bridge"] == "owner_extraction_pending_fail_closed"}
    require(len(applied) == 55, "strategic applied count must be 55")
    require(pending == {"AutoResolveMission", "StartMission"},
            "strategic pending set mismatch: " + repr(sorted(pending)))

    print("PASS M1 LoadLastSave boundary normalization")
    print("  archived cl_lastsave remains application/presentation context")
    print("  typed LoadLastSave carries an explicit bounded resolved slot")
    print("  running-campaign/Battlescape continue branches remain presentation-owned")
    print("  authoritative branch converges on existing SAV_GameLoad")
    print("  strategic authority: 55/57 applied, 2 fail-closed")
    print("  save v4 / savx / protocol 18 unchanged")

if __name__ == "__main__":
    try:
        main()
    except GateError as exc:
        print("FAIL M1 LoadLastSave owner qualification: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

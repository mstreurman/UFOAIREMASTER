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
    callbacks = text("src/client/cgame/campaign/cp_save_callbacks.cpp")
    intent_h = text("src/client/presentation/strategic_intent.h")
    dispatch = text("src/client/presentation/strategic_intent_dispatch.cpp")
    adapter = text("src/client/presentation/strategic_intent_legacy_adapter.cpp")
    common_h = text("src/common/common.h")

    for token in (
        "submitSaveGame(const char* slot, const char* comment)",
        "char key0[96];",
        "char text[128];",
    ):
        require(token in intent_h, "bounded SaveGame transport missing: " + token)
    require("copyBounded(v.key0, slot); copyBounded(v.text, comment);" in dispatch,
            "SaveGame dispatch must carry bounded slot + comment")

    save = function_body(save_cpp, "bool SAV_GameSave (")
    for token in (
        "SAV_GameSaveAllowed(error)",
        "SAVEGAME_EXTENSION",
        "SAVE_FILE_VERSION",
        "SAVE_ROOTNODE",
        "saveSubsystems[i].save(node)",
    ):
        require(token in save, "canonical save owner contract missing: " + token)
    for banned in ("UI_", "Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue("):
        require(banned not in save, "presentation dispatch leaked into SAV_GameSave: " + banned)

    legacy_save = function_body(callbacks, "static void SAV_GameSave_f (")
    require("SAV_GameSave(cgi->Cmd_Argv(1), comment, &error)" in legacy_save,
            "legacy SaveGame callback no longer converges on SAV_GameSave")

    require('#include "../cgame/campaign/cp_save.h"' in adapter,
            "strategic adapter does not include canonical save API")
    save_case = re.search(
        r"case StrategicIntentKind::SaveGame\s*:(.*?)(?=\n\s*case StrategicIntentKind::|\n\s*/\*)",
        adapter, re.S
    )
    require(save_case is not None, "typed SaveGame adapter case missing")
    body = save_case.group(1)
    for token in (
        "resolveBoundedText(in.key0)",
        "resolveBoundedText(in.text)",
        "SAV_GameSave(slot,comment,&error)",
        "StrategicIntentDisposition::Applied",
    ):
        require(token in body, "typed SaveGame convergence missing: " + token)
    for banned in ("Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue(", "UI_"):
        require(banned not in body, "typed SaveGame adapter contains presentation fallback: " + banned)

    fail = adapter[adapter.find("/* Strict-authority catalog is transport-complete"):]
    require("case StrategicIntentKind::SaveGame:" not in fail,
            "SaveGame still appears in fail-closed block")
    for kind in ("LoadGame", "LoadLastSave", "AutoResolveMission", "StartMission"):
        require("case StrategicIntentKind::" + kind + ":" in fail,
                kind + " must remain fail-closed in this batch")

    load = function_body(save_cpp, "bool SAV_GameLoad (")
    reload_pos = load.find("cgi->GAME_ReloadMode();")
    require(reload_pos >= 0, "SAV_GameLoad mode reload seam missing")
    post_reload = load[reload_pos:]
    for token in (
        "saveSubsystems[i].load(node)",
        "SAV_GameActionsAfterLoad()",
        "return false;",
    ):
        require(token in post_reload,
                "load must retain observable post-GAME_ReloadMode failure seam: " + token)

    legacy_load = function_body(callbacks, "static void SAV_GameLoad_f (")
    for token in (
        "SAV_GameLoad(",
        'cgi->Cmd_ExecuteString("game_exit")',
        'cgi->Cmd_ExecuteString("game_setmode campaign")',
    ):
        require(token in legacy_load, "legacy LoadGame recovery contract missing: " + token)

    cont = function_body(callbacks, "static void SAV_GameContinue_f (")
    for token in (
        "cgi->CL_OnBattlescape()",
        "!CP_IsRunning()",
        "SAV_GameLoad(cl_lastsave->string, &error)",
        "cgi->UI_PopWindow(false)",
    ):
        require(token in cont, "LoadLastSave split semantics missing: " + token)
    require('cl_lastsave = cgi->Cvar_Get("cl_lastsave", "", CVAR_ARCHIVE' in callbacks,
            "cl_lastsave must remain archived presentation/application context")

    require(re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h) is not None,
            "save version changed")
    require('#define SAVEGAME_EXTENSION "savx"' in save_h,
            "save extension changed")
    require(re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h) is not None,
            "protocol version changed")

    with (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    strategic = {r["semantic_action"]: r for r in rows if r["domain"] == "strategic"}
    require(strategic["SaveGame"]["authority_bridge"] == "canonical_applied",
            "SaveGame is not canonical_applied in coverage ledger")
    require(strategic["SaveGame"]["owner_source"] == "src/client/cgame/campaign/cp_save.cpp",
            "SaveGame owner must be the existing cp_save.cpp serializer")
    applied = {n for n, r in strategic.items() if r["authority_bridge"] == "canonical_applied"}
    pending = {n for n, r in strategic.items()
               if r["authority_bridge"] == "owner_extraction_pending_fail_closed"}
    require(len(applied) == 53, "strategic applied count must be 53")
    require(pending == {"AutoResolveMission", "LoadGame", "LoadLastSave", "StartMission"},
            "strategic pending set mismatch: " + repr(sorted(pending)))

    print("PASS M1 SaveGame canonical owner qualification")
    print("  legacy + typed SaveGame converge on existing SAV_GameSave")
    print("  canonical save eligibility + v4 serializer remain unchanged")
    print("  LoadGame/LoadLastSave stay fail-closed across the post-reload failure seam")
    print("  authority: strategic 53/57 applied, 4 fail-closed")
    print("  save v4 / savx / protocol 18 unchanged")

if __name__ == "__main__":
    try:
        main()
    except GateError as exc:
        print("FAIL M1 SaveGame owner qualification: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

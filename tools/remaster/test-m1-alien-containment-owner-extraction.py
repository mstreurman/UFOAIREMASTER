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
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0: return text[start:i+1]
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
    owner_h = read("src/client/cgame/campaign/cp_aliencont.h")
    owner = read("src/client/cgame/campaign/cp_aliencont.cpp")
    callbacks = read("src/client/cgame/campaign/cp_aliencont_callbacks.cpp")
    adapter = read("src/client/presentation/strategic_intent_legacy_adapter.cpp")

    require(owner_h, ["alienContainmentMutationResult_t", "AC_TryKillContainedAlien(", "AC_TryKillContainedAliens("], "containment owner API")
    one = body(owner, "alienContainmentMutationResult_t AC_TryKillContainedAlien (")
    require(one, [
        "if (!base)", "if (!technology)", "if (!base->alienContainment)",
        "base->alienContainment->list()", "RS_GetTechForTeam(item->teamDef) != technology",
        "item->alive <= 0", "base->alienContainment->add(item->teamDef, -1, 1)",
        "cgi->LIST_Delete(&list)", "AC_CONTAINMENT_MUTATION_NO_LIVE_ALIENS",
    ], "single containment owner")
    forbid(one, ["UI_", "Cmd_ExecuteString(", "Cvar_Set("], "single containment owner")

    all_body = body(owner, "alienContainmentMutationResult_t AC_TryKillContainedAliens (")
    require(all_body, [
        "if (!base)", "if (!base->alienContainment)", "base->alienContainment->list()",
        "const int alive = item->alive", "base->alienContainment->add(item->teamDef, -alive, alive)",
        "alive > 0 && accepted", "cgi->LIST_Delete(&list)", "AC_CONTAINMENT_MUTATION_NO_LIVE_ALIENS",
    ], "kill-all containment owner")
    forbid(all_body, ["UI_", "Cmd_ExecuteString(", "Cvar_Set("], "kill-all containment owner")

    legacy_one = body(callbacks, "static void AC_KillOne_f (")
    legacy_all = body(callbacks, "static void AC_KillAll_f (")
    require(legacy_one, ["RS_GetTechByID(", "AC_TryKillContainedAlien(", 'Cmd_ExecuteString("ui_aliencont_init")'], "legacy single callback")
    require(legacy_all, ["AC_TryKillContainedAliens(", 'Cmd_ExecuteString("ui_aliencont_init")'], "legacy kill-all callback")
    forbid(legacy_one, ["alienContainment->add(", "LIST_Foreach("], "legacy single callback mutation")
    forbid(legacy_all, ["alienContainment->add(", "LIST_Foreach("], "legacy kill-all callback mutation")

    for kind, call in (("KillContainedAlien", "AC_TryKillContainedAlien("), ("KillContainedAliens", "AC_TryKillContainedAliens(")):
        case = re.search(r"case StrategicIntentKind::" + kind + r"\s*:(.*?)(?=\n\s*case StrategicIntentKind::|\n\s*/\*)", adapter, re.S)
        if not case or call not in case.group(1):
            raise AssertionError(kind + " typed adapter does not reach canonical owner")
    forbid(adapter, ["Cmd_ExecuteString(", "Cbuf_AddText(", "Cvar_Set(", "Cvar_SetValue("], "strategic adapter")

    with (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open() as f:
        cov = {r["semantic_action"]: r for r in csv.DictReader(f, delimiter="\t") if r["domain"] == "strategic"}
    for action in ("KillContainedAlien", "KillContainedAliens"):
        if cov[action]["authority_bridge"] != "canonical_applied":
            raise AssertionError(action + " is not canonical_applied")
        if cov[action]["owner_source"] != "src/client/cgame/campaign/cp_aliencont.cpp":
            raise AssertionError(action + " owner source is not cp_aliencont.cpp")

    with (ROOT / "tools/remaster/m1-canonical-identity-registry.tsv").open() as f:
        reg = {r["identity"]: r for r in csv.DictReader(f, delimiter="\t")}
    if reg["ContainedAlienSpecies"]["intent_status"] != "containment_owners_qualified":
        raise AssertionError("ContainedAlienSpecies aggregate contract not qualified")
    if "do not mint individual AlienId" not in reg["ContainedAlienSpecies"]["required_action"]:
        raise AssertionError("containment identity contract must forbid individual AlienId invention")

    save_h = read("src/client/cgame/campaign/cp_save.h")
    common_h = read("src/common/common.h")
    if not re.search(r"#\s*define\s+SAVE_FILE_VERSION\s+4\b", save_h):
        raise AssertionError("save version changed")
    if not re.search(r"#\s*define\s+PROTOCOL_VERSION\s+18\b", common_h):
        raise AssertionError("protocol version changed")

    print("PASS M1 alien containment owner extraction")
    print("  KillContainedAlien: BaseId + TechnologyId aggregate owner; all matching team definitions preserved")
    print("  KillContainedAliens: canonical live-to-dead conversion through AlienContainment::add")
    print("  no AlienId invented; callbacks retain UI refresh only")
    print("  aggregate strategic authority accounting is centralized")
    print("  save v4 / protocol 18 unchanged")
except AssertionError as exc:
    print("FAIL M1 alien containment owner extraction: " + str(exc), file=sys.stderr)
    raise SystemExit(1)

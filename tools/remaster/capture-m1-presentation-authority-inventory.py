#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REGISTRY_REL = Path("tools/remaster/m1-presentation-authority-seed.tsv")
DECOMPOSITION_REL = Path("tools/remaster/m1-presentation-authority-decomposition.tsv")
OUT_REL = Path(".build/m1-presentation-authority")

FINAL_AUTHORITIES = {
    "PRESENTATION_ONLY", "PRESENTATION_CONTEXT", "READ_ONLY",
    "STRATEGIC_CANONICAL", "TACTICAL_SERVER",
}
ANALYSIS_AUTHORITIES = {"UNCLASSIFIED", "SPLIT_REQUIRED"}
ALL_AUTHORITIES = FINAL_AUTHORITIES | ANALYSIS_AUTHORITIES

SCOPES = {
    "PRESENTATION_ACTION", "PRESENTATION_PROJECTION", "SESSION_CONTROL",
    "APPLICATION_PERSISTENCE", "CANONICAL_LIFECYCLE", "CANONICAL_MAINTENANCE",
    "SCRIPTED_CANONICAL_EVENT", "MULTIPLAYER_SESSION", "SKIRMISH_SESSION",
    "DEBUG_TOOLING", "INTERNAL_PROTOCOL", "UNCLASSIFIED_SCOPE",
}

UI_TOKENS = (
    "UI_PushWindow", "UI_PopWindow", "UI_ExecuteConfunc", "UI_Popup",
    "UI_PopupButton", "CP_Popup", "HUD_DisplayMessage", "UP_OpenWith",
    "S_StartLocalSample",
)
HIDDEN_CONTEXT_TOKENS = (
    "B_GetCurrentSelectedBase", "GEO_GetSelectedMission", "GEO_GetSelectedAircraft",
    "selectedProduction", "selectedData", "selActor", "cl_selected",
    "mousePos", "mouseActor", "mousePendPos", "currentDisplayedObject",
)
CANONICAL_MUTATION_HINTS = (
    "B_Build(", "B_Destroy(", "B_SetName(", "B_BuildBuilding(",
    "B_BuildingDestroy(", "CP_UpdateCredits(", "AIR_AircraftReturnToBase(",
    "AIR_SendAircraftToMission(", "AIR_SendAircraftPursuingUFO(",
    "AIR_MoveAircraftIntoNewHomebase(", "RS_AssignScientist(",
    "RS_RemoveScientist(", "RS_StopResearch(", "PR_QueueNew(",
    "PR_QueueDelete(", "PR_QueueMove(", "PR_IncreaseProduction(",
    "PR_DecreaseProduction(", "BS_Buy", "BS_Sell", "E_HireEmployee(",
    "E_DeleteEmployee(", "GEO_CalcLine(",
)

COMMAND_TABLE_RE = re.compile(
    r"(?:static\s+)?const\s+cmdList_t\s+[A-Za-z_]\w*\s*\[\]\s*=\s*\{(?P<body>.*?)\n\};",
    re.S,
)
COMMAND_ENTRY_RE = re.compile(r'\{\s*"(?P<name>[^"]+)"\s*,\s*(?P<handler>[A-Za-z_]\w*)\s*,')
ADD_COMMAND_RE = re.compile(
    r'(?:(?:cgi->)?Cmd_AddCommand)\s*\(\s*"(?P<name>[^"]+)"\s*,\s*(?P<handler>[A-Za-z_]\w*)'
)
CGAME_EXPORT_RE = re.compile(r'\be\.(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<handler>[A-Za-z_]\w*)\s*;')
REVIEWED_CGAME_EXPORT_FIELDS = {
    "Init", "Shutdown", "Spawn", "Results", "IsItemUseable", "GetModelForItem",
    "GetEquipmentDefinition", "UpdateCharacterValues", "IsTeamKnown", "GetSelectedChr",
    "Drop", "InitializeBattlescape", "InitMissionBriefing", "RunFrame", "DrawBaseLayout",
    "DrawBaseLayoutTooltip", "GetTeamDef", "MapDraw", "MapDrawMarkers", "MapClick",
}
DIRECT_PRESENTATION_INPUT_EXPORTS = {"MapClick"}
PA_RE = re.compile(r"MSG_Write_PA\s*\(\s*(PA_[A-Z0-9_]+)")
ENDROUND_RE = re.compile(r"\bclc_endround\b")
SV_WIN_RE = re.compile(r'["\']sv\s+win\b')

PA_SEMANTICS = {
    "PA_MOVE": "MoveActor",
    "PA_SHOOT": "Shoot",
    "PA_TURN": "TurnActor",
    "PA_USE": "Use",
    "PA_INVMOVE": "InventoryMove",
    "PA_STATE": "ActorStateChange",
    "PA_RESERVE_STATE": "SetReservedTimeUnits",
    "PA_REACTION_SELECT": "SelectReactionFireMode",
    "PA_REACT_SELECT": "SelectReactionFireMode",
}
CONTROL_NAMES = {"if", "for", "while", "switch", "catch"}

@dataclass
class RegistryEntry:
    source: str
    entry_kind: str
    name: str
    handler: str
    scope: str
    authority: str
    semantic_action: str
    api_relevance: str
    confidence: str
    rationale: str

@dataclass
class DecompositionEntry:
    source: str
    entry_kind: str
    name: str
    component: str
    authority: str
    semantic_action: str
    api_relevance: str
    rationale: str

@dataclass
class Row:
    entry_kind: str
    name: str
    handler: str
    scope: str
    authority: str
    semantic_action: str
    api_relevance: str
    confidence: str
    source: str
    line: int
    preprocessor_guard: str
    protocol_kinds: str
    legacy_presentation_side_effects: str
    hidden_context_dependency: str
    signals: str
    handler_body_sha256: str
    rationale: str

class CaptureError(RuntimeError):
    pass

def require(cond: bool, msg: str) -> None:
    if not cond:
        raise CaptureError(msg)

def repo_root() -> Path:
    p = subprocess.run(["git","rev-parse","--show-toplevel"], text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if p.returncode != 0:
        raise CaptureError("not inside a Git work tree")
    return Path(p.stdout.rstrip("\n")).resolve()

def git_head(root: Path) -> str:
    p = subprocess.run(["git","rev-parse","HEAD"], cwd=root, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return p.stdout.strip() if p.returncode == 0 else "unknown"

def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1

def strip_comments_preserve_layout(text: str) -> str:
    out = list(text)
    state = "code"
    i = 0
    while i < len(text):
        c = text[i]
        n = text[i+1] if i+1 < len(text) else ""
        if state == "code":
            if c == "/" and n == "/":
                out[i] = out[i+1] = " "
                state = "line"; i += 2; continue
            if c == "/" and n == "*":
                out[i] = out[i+1] = " "
                state = "block"; i += 2; continue
            if c == '"': state = "string"
            elif c == "'": state = "char"
        elif state == "line":
            if c == "\n": state = "code"
            else: out[i] = " "
        elif state == "block":
            if c == "*" and n == "/":
                out[i] = out[i+1] = " "
                state = "code"; i += 2; continue
            if c != "\n": out[i] = " "
        else:
            quote = '"' if state == "string" else "'"
            if c == "\\": i += 2; continue
            if c == quote: state = "code"
        i += 1
    return "".join(out)

def blank_if0_blocks(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out = list(lines)
    stack: list[bool] = []
    disabled = 0
    for i, line in enumerate(lines):
        s = line.lstrip()
        entering = False
        if s.startswith("#if"):
            expr = s[3:].strip()
            is_zero = bool(re.match(r"0(?:\s|$)", expr))
            stack.append(is_zero)
            if is_zero:
                disabled += 1
            entering = True
        if disabled > 0:
            out[i] = "".join("\n" if ch == "\n" else " " for ch in line)
        if s.startswith("#endif") and stack:
            was_zero = stack.pop()
            if was_zero:
                disabled = max(0, disabled - 1)
    return "".join(out)

def preprocessor_guards(text: str) -> list[str]:
    guards, stack = [], []
    for line in text.splitlines():
        s = line.lstrip()
        if s.startswith("#ifdef "): stack.append(s.split(None,1)[1].strip())
        elif s.startswith("#ifndef "): stack.append("!" + s.split(None,1)[1].strip())
        elif s.startswith("#if "): stack.append(s[4:].strip())
        elif s.startswith("#elif ") and stack: stack[-1] = s[6:].strip()
        elif s.startswith("#else") and stack: stack[-1] = "ELSE(" + stack[-1] + ")"
        guards.append(" && ".join(stack))
        if s.startswith("#endif") and stack: stack.pop()
    return guards

def matching_brace(code: str, open_pos: int) -> int:
    depth, state, i = 0, "code", open_pos
    while i < len(code):
        c = code[i]
        if state == "code":
            if c == '"': state = "string"
            elif c == "'": state = "char"
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0: return i
        else:
            quote = '"' if state == "string" else "'"
            if c == "\\": i += 2; continue
            if c == quote: state = "code"
        i += 1
    return len(code)-1

def active_source(original: str) -> str:
    return blank_if0_blocks(strip_comments_preserve_layout(original))

def extract_handler_body(original: str, active: str, handler: str) -> tuple[str,int]:
    if not handler: return "", -1
    pat = re.compile(r"\b" + re.escape(handler) + r"\s*\([^;{}]*\)\s*(?:const\s*)?\{", re.S)
    matches = list(pat.finditer(active))
    if len(matches) != 1: return "", -1
    m = matches[0]
    op = active.find("{", m.start(), m.end())
    end = matching_brace(active, op)
    return original[op+1:end], m.start()

def enclosing_handler(original: str, active: str, offset: int) -> str:
    candidates = []
    pat = re.compile(r"\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?\{", re.S)
    for m in pat.finditer(active):
        name = m.group(1)
        if name in CONTROL_NAMES: continue
        op = active.find("{", m.start(), m.end())
        if op > offset: break
        end = matching_brace(active, op)
        if op <= offset <= end:
            candidates.append((end-op, name))
    if not candidates: return ""
    candidates.sort()
    return candidates[0][1]

def load_registry(path: Path):
    expected = ["source","entry_kind","name","handler","scope","authority",
                "semantic_action","api_relevance","confidence","rationale"]
    require(path.is_file(), f"missing registry: {path}")
    result = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        require(r.fieldnames == expected, "unexpected v2 authority registry schema")
        for d in r:
            require(d["scope"] in SCOPES - {"UNCLASSIFIED_SCOPE"}, f"invalid scope {d['scope']}")
            if d["scope"] == "PRESENTATION_ACTION":
                require(d["authority"] in ALL_AUTHORITIES, f"invalid authority {d['authority']}")
            e = RegistryEntry(**d)
            result.setdefault((e.source,e.entry_kind,e.name), []).append(e)
    return result

def registry_lookup(registry, source, kind, name, handler):
    c = registry.get((source,kind,name), [])
    exact = [e for e in c if e.handler == handler]
    if len(exact) == 1: return exact[0]
    wild = [e for e in c if e.handler == ""]
    return wild[0] if len(wild) == 1 else None

def load_decompositions(path: Path):
    expected = ["source","entry_kind","name","component","authority",
                "semantic_action","api_relevance","rationale"]
    require(path.is_file(), f"missing decomposition registry: {path}")
    result = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        require(r.fieldnames == expected, "unexpected decomposition registry schema")
        for d in r:
            require(d["authority"] in FINAL_AUTHORITIES,
                    f"decomposition component must have final authority: {d}")
            require(bool(d["semantic_action"]),
                    f"decomposition component missing semantic action: {d}")
            e = DecompositionEntry(**d)
            result.setdefault((e.source,e.entry_kind,e.name), []).append(e)
    for key, items in result.items():
        require(len(items) >= 2, f"decomposition requires at least two semantic components: {key}")
        components = [x.component for x in items]
        require(len(components) == len(set(components)),
                f"duplicate decomposition component: {key}")
    return result

def decomposition_for(decompositions, row):
    return decompositions.get((row.source,row.entry_kind,row.name), [])

def split_is_resolved(decompositions, row):
    items = decomposition_for(decompositions,row)
    return len(items) >= 2 and all(
        x.authority in FINAL_AUTHORITIES and bool(x.semantic_action) for x in items
    )

def auto_scope(source: str, name: str, guard: str):
    low = name.lower()
    if "DEBUG" in guard or low.startswith("debug") or low.startswith("grid_"):
        return "DEBUG_TOOLING", "Strong DEBUG/prefix scope heuristic."
    if "/multiplayer/" in source:
        return "MULTIPLAYER_SESSION", "Source-owned multiplayer session/control command."
    if "/skirmish/" in source:
        return "SKIRMISH_SESSION", "Source-owned skirmish session/control command."
    if source == "src/client/cgame/cl_map_callbacks.cpp":
        return "SESSION_CONTROL", "Map-selection/server-setup command."
    return "UNCLASSIFIED_SCOPE", "No reviewed registry or strong scope heuristic."

def signals_for(body: str):
    pa = sorted(set(PA_RE.findall(body)))
    ui = [t for t in UI_TOKENS if t in body]
    hidden = [t for t in HIDDEN_CONTEXT_TOKENS if t in body]
    mut = [t.rstrip("(") for t in CANONICAL_MUTATION_HINTS if t in body]
    parts = []
    if ui: parts.append("ui=" + ",".join(ui))
    if hidden: parts.append("context=" + ",".join(hidden))
    if mut: parts.append("mutation_hint=" + ",".join(mut))
    if pa: parts.append("pa=" + ",".join(pa))
    digest = hashlib.sha256(body.encode()).hexdigest() if body else ""
    return ",".join(pa), "yes" if ui else "no", "yes" if hidden else "no", ";".join(parts), digest

def discover_source_files(root: Path):
    files = []
    for suffix in ("*.cpp","*.c"):
        files.extend((root/"src/client").rglob(suffix))
    return sorted(p for p in files if p.is_file())

def command_scope_file(rel: str):
    return rel.startswith("src/client/cgame/") or rel.startswith("src/client/battlescape/") or rel=="src/client/cl_inventory_callbacks.cpp"

def row_from_entry(original, active, guards, registry, rel, kind, name, handler, offset):
    body,_ = extract_handler_body(original,active,handler)
    pa,ui,hidden,sig,digest = signals_for(body)
    line = line_number(original,offset)
    guard = guards[line-1] if 0 < line <= len(guards) else ""
    reg = registry_lookup(registry,rel,kind,name,handler)
    if reg:
        scope,auth,sem,relevance,conf,rat = reg.scope,reg.authority,reg.semantic_action,reg.api_relevance,reg.confidence,reg.rationale
    else:
        scope,rat = auto_scope(rel,name,guard)
        auth,sem,relevance = "","","no"
        conf = "AUTO" if scope!="UNCLASSIFIED_SCOPE" else "NONE"
    return Row(kind,name,handler,scope,auth,sem,relevance,conf,rel,line,guard,pa,ui,hidden,sig,digest,rat)

def capture(root: Path, registry):
    rows, violations = [], []
    for path in discover_source_files(root):
        rel = path.relative_to(root).as_posix()
        original = path.read_text(encoding="utf-8", errors="replace")
        active = active_source(original)
        guards = preprocessor_guards(original)

        if command_scope_file(rel):
            seen = set()
            for table in COMMAND_TABLE_RE.finditer(active):
                body, base = table.group("body"), table.start("body")
                for e in COMMAND_ENTRY_RE.finditer(body):
                    name,handler = e.group("name"),e.group("handler")
                    if (name,handler) in seen: continue
                    seen.add((name,handler))
                    rows.append(row_from_entry(original,active,guards,registry,rel,"command",name,handler,base+e.start()))
            for e in ADD_COMMAND_RE.finditer(active):
                name,handler = e.group("name"),e.group("handler")
                if (name,handler) in seen: continue
                seen.add((name,handler))
                rows.append(row_from_entry(original,active,guards,registry,rel,"command",name,handler,e.start()))

        if rel == "src/client/cgame/campaign/cl_game_campaign.cpp":
            for e in CGAME_EXPORT_RE.finditer(active):
                field = e.group("name")
                handler = e.group("handler")
                if field not in REVIEWED_CGAME_EXPORT_FIELDS:
                    violations.append(f"{rel}: unreviewed cgame export field e.{field} -> {handler}")
                    continue
                if field in DIRECT_PRESENTATION_INPUT_EXPORTS:
                    rows.append(row_from_entry(original,active,guards,registry,rel,"direct_entry",field,handler,e.start()))

        for m in PA_RE.finditer(active):
            pa = m.group(1)
            handler = enclosing_handler(original,active,m.start())
            body,_ = extract_handler_body(original,active,handler)
            _,ui,hidden,sig,digest = signals_for(body)
            line = line_number(original,m.start())
            guard = guards[line-1] if 0 < line <= len(guards) else ""
            rows.append(Row("protocol_request",pa,handler,"INTERNAL_PROTOCOL","TACTICAL_SERVER",
                PA_SEMANTICS.get(pa,""),"yes","DIRECT",rel,line,guard,pa,ui,hidden,
                ("direct_protocol=MSG_Write_PA;"+sig).strip(";"),digest,
                "Direct tactical client/server request; server remains authoritative."))

        for regex,name,semantic in ((ENDROUND_RE,"clc_endround","EndTurn"),(SV_WIN_RE,"sv win","AbortMission")):
            for m in regex.finditer(active):
                handler = enclosing_handler(original,active,m.start())
                body,_ = extract_handler_body(original,active,handler)
                _,ui,hidden,sig,digest = signals_for(body)
                line = line_number(original,m.start())
                guard = guards[line-1] if 0 < line <= len(guards) else ""
                rows.append(Row("protocol_request",name,handler,"INTERNAL_PROTOCOL","TACTICAL_SERVER",
                    semantic,"yes","DIRECT",rel,line,guard,name,ui,hidden,
                    ("direct_protocol="+name+";"+sig).strip(";"),digest,
                    "Direct non-PA tactical client/server authority request."))

        if rel.startswith("src/client/presentation/") and not rel.endswith("_legacy_adapter.cpp"):
            forbidden = []
            if re.search(r'#include\s+"[^"]*cgame/', active): forbidden.append("campaign/cgame include")
            if "ccs." in active or "ccs->" in active: forbidden.append("direct ccs access")
            if "MSG_Write_PA" in active: forbidden.append("direct PA_* send outside legacy adapter")
            if forbidden: violations.append(f"{rel}: " + ", ".join(forbidden))

    uniq = {(r.entry_kind,r.name,r.handler,r.source,r.line):r for r in rows}
    return sorted(uniq.values(), key=lambda r:(r.source,r.line,r.entry_kind,r.name)), violations

def unresolved(rows, decompositions):
    out = []
    for r in rows:
        if r.scope == "UNCLASSIFIED_SCOPE":
            out.append(r)
        elif r.scope == "PRESENTATION_ACTION":
            if r.authority in FINAL_AUTHORITIES:
                pass
            elif r.authority == "SPLIT_REQUIRED" and split_is_resolved(decompositions,r):
                pass
            else:
                out.append(r)
        elif r.entry_kind == "protocol_request" and not r.semantic_action:
            out.append(r)
    return out

FIELDS = ["entry_kind","name","handler","scope","authority","semantic_action","api_relevance",
          "confidence","source","line","preprocessor_guard","protocol_kinds",
          "legacy_presentation_side_effects","hidden_context_dependency","signals",
          "handler_body_sha256","rationale"]

def write_tsv(path: Path, rows: Iterable[Row]):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w = csv.DictWriter(f,delimiter="\t",fieldnames=FIELDS,lineterminator="\n")
        w.writeheader()
        for r in rows: w.writerow(r.__dict__)

def write_review_pack(path: Path, items, root: Path):
    blocks = ["# M1 Presentation Authority — Unresolved Review Pack","",
              "Only unresolved active entries are included.",""]
    for r in items:
        blocks += [f"## {r.entry_kind}: `{r.name}`","",
                   f"- Source: `{r.source}:{r.line}`",
                   f"- Handler: `{r.handler or '(none)'}`",
                   f"- Scope: `{r.scope}`",
                   f"- Authority: `{r.authority or '(none)'}`",
                   f"- Guard: `{r.preprocessor_guard or '(none)'}`",
                   f"- Signals: `{r.signals or '(none)'}`",
                   f"- Body SHA-256: `{r.handler_body_sha256 or '(unresolved body)'}`",""]
        src = root/r.source
        if src.is_file() and r.handler:
            original = src.read_text(encoding="utf-8",errors="replace")
            body,_ = extract_handler_body(original,active_source(original),r.handler)
            if body:
                lines = body.strip("\n").splitlines()
                blocks += ["```cpp",*lines[:120]]
                if len(lines)>120: blocks.append(f"// ... clipped {len(lines)-120} additional lines ...")
                blocks += ["```",""]
        blocks += [f"Current rationale: {r.rationale}",""]
    path.write_text("\n".join(blocks),encoding="utf-8")

SEMANTIC_FIELDS = [
    "source","entry_kind","legacy_name","component","authority",
    "semantic_action","api_relevance","rationale",
]

def semantic_actions(rows, decompositions):
    out = []
    for r in rows:
        if r.scope != "PRESENTATION_ACTION":
            continue
        if r.authority in FINAL_AUTHORITIES:
            out.append({
                "source": r.source,
                "entry_kind": r.entry_kind,
                "legacy_name": r.name,
                "component": "",
                "authority": r.authority,
                "semantic_action": r.semantic_action or r.name,
                "api_relevance": r.api_relevance,
                "rationale": r.rationale,
            })
        elif r.authority == "SPLIT_REQUIRED":
            for e in decomposition_for(decompositions,r):
                out.append({
                    "source": r.source,
                    "entry_kind": r.entry_kind,
                    "legacy_name": r.name,
                    "component": e.component,
                    "authority": e.authority,
                    "semantic_action": e.semantic_action,
                    "api_relevance": e.api_relevance,
                    "rationale": e.rationale,
                })
    out.sort(key=lambda x: (
        x["authority"],x["semantic_action"],x["source"],x["legacy_name"],x["component"]
    ))
    return out

def write_semantic_tsv(path: Path, items):
    with path.open("w",encoding="utf-8",newline="") as f:
        w = csv.DictWriter(f,delimiter="\t",fieldnames=SEMANTIC_FIELDS,lineterminator="\n")
        w.writeheader()
        w.writerows(items)

def write_intent_candidates(path: Path, items):
    authoritative = [
        x for x in items
        if x["authority"] in {"STRATEGIC_CANONICAL","TACTICAL_SERVER"}
        and x["api_relevance"] == "yes"
    ]
    write_semantic_tsv(path,authoritative)

def write_summary(path: Path, rows, violations, head, decompositions):
    commands = [r for r in rows if r.entry_kind=="command"]
    direct = [r for r in rows if r.entry_kind=="direct_entry"]
    protocols = [r for r in rows if r.entry_kind=="protocol_request"]
    unr = unresolved(rows,decompositions)
    scopes = Counter(r.scope for r in commands+direct)
    auths = Counter(r.authority for r in commands+direct if r.scope=="PRESENTATION_ACTION")
    hidden = sum(r.hidden_context_dependency=="yes" for r in commands+direct)
    mixed = sum(r.scope=="PRESENTATION_ACTION" and r.authority in {"STRATEGIC_CANONICAL","TACTICAL_SERVER"}
                and r.legacy_presentation_side_effects=="yes" for r in commands+direct)
    lines = ["# M1 Presentation Action Authority Inventory Capture — v2","",
             f"**HEAD:** `{head}`",
             f"**Active commands discovered:** {len(commands)}",
             f"**Direct presentation input entries:** {len(direct)}",
             f"**Direct protocol request callsites:** {len(protocols)}",
             f"**Unresolved entries:** {len(unr)}",
             f"**Presentation source-guard violations:** {len(violations)}",
             f"**Resolved semantic decompositions:** {sum(1 for r in commands+direct if r.authority == 'SPLIT_REQUIRED' and split_is_resolved(decompositions,r))}","",
             "## Scope counts","","```text"]
    for k in sorted(SCOPES): lines.append(f"{k:28s} {scopes.get(k,0)}")
    lines += ["```","","## PRESENTATION_ACTION authority counts","","```text"]
    for k in sorted(FINAL_AUTHORITIES|ANALYSIS_AUTHORITIES): lines.append(f"{k:24s} {auths.get(k,0)}")
    lines += ["```","",f"Hidden-context dependencies detected: **{hidden}**",
              f"Authoritative presentation actions with legacy UI side effects: **{mixed}**","",
              "## Protocol semantic coverage","","```text"]
    pc = Counter((r.name,r.semantic_action or "UNMAPPED") for r in protocols)
    for (name,sem),count in sorted(pc.items()): lines.append(f"{name:22s} -> {sem:28s} {count}")
    lines += ["```",""]
    if unr:
        lines += ["## Unresolved active entries",""]
        for r in unr:
            lines.append(f"- `{r.entry_kind}` `{r.name}` -> `{r.handler or '(none)'}` — scope `{r.scope}` authority `{r.authority or '(none)'}` — `{r.source}:{r.line}`")
        lines.append("")
    if violations:
        lines += ["## Presentation source-guard violations",""]
        lines += [f"- `{x}`" for x in violations]
        lines.append("")
    lines += ["## Strict interpretation","",
              "`--strict` passes only with zero unresolved entries and zero presentation source-guard violations.",""]
    path.write_text("\n".join(lines),encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict",action="store_true")
    ap.add_argument("--output-dir",type=Path,default=None)
    args = ap.parse_args()
    root = repo_root()
    registry = load_registry(root/REGISTRY_REL)
    decompositions = load_decompositions(root/DECOMPOSITION_REL)
    rows,violations = capture(root,registry)
    unr = unresolved(rows,decompositions)
    out = args.output_dir.resolve() if args.output_dir else root/OUT_REL
    out.mkdir(parents=True,exist_ok=True)
    write_tsv(out/"inventory.tsv",rows)
    write_tsv(out/"unresolved.tsv",unr)
    write_summary(out/"summary.md",rows,violations,git_head(root),decompositions)
    write_review_pack(out/"review-pack.md",unr,root)
    semantic = semantic_actions(rows,decompositions)
    write_semantic_tsv(out/"semantic-actions.tsv",semantic)
    write_intent_candidates(out/"intent-candidates.tsv",semantic)

    commands = [r for r in rows if r.entry_kind=="command"]
    direct = [r for r in rows if r.entry_kind=="direct_entry"]
    protocols = [r for r in rows if r.entry_kind=="protocol_request"]
    print("M1 presentation authority inventory v3 capture: PASS")
    print(f"  active commands discovered: {len(commands)}")
    print(f"  direct presentation input entries: {len(direct)}")
    print(f"  direct protocol request callsites: {len(protocols)}")
    print(f"  unresolved entries: {len(unr)}")
    print(f"  presentation source-guard violations: {len(violations)}")
    print(f"  inventory:    {out/'inventory.tsv'}")
    print(f"  unresolved:   {out/'unresolved.tsv'}")
    print(f"  summary:      {out/'summary.md'}")
    print(f"  review pack:  {out/'review-pack.md'}")
    print(f"  semantic:     {out/'semantic-actions.tsv'}")
    print(f"  intents:      {out/'intent-candidates.tsv'}")
    if args.strict and (unr or violations):
        print("M1 presentation authority inventory v3 strict verification: INCOMPLETE",file=sys.stderr)
        return 1
    print("M1 presentation authority classification: " + ("COMPLETE" if not unr and not violations else "IN PROGRESS"))
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CaptureError as exc:
        print(f"M1 presentation authority inventory v2 capture: FAIL: {exc}",file=sys.stderr)
        raise SystemExit(2)

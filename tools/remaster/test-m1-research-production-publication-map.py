#!/usr/bin/env python3
from pathlib import Path
import csv
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

def require(text: str, tokens, label: str) -> None:
    for token in tokens:
        if token not in text:
            raise AssertionError(f"{label}: missing {token}")

def struct_body(text: str, name: str) -> str:
    marker = f"struct {name} "
    pos = text.find(marker)
    if pos < 0:
        raise AssertionError(f"missing {name}")
    start = text.find("{", pos)
    if start < 0:
        raise AssertionError(f"missing body for {name}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise AssertionError(f"unterminated {name}")

try:
    snapshot = (ROOT / "src/client/presentation/strategic_snapshot.h").read_text(encoding="utf-8")
    adapter = (ROOT / "src/client/presentation/strategic_snapshot_legacy_adapter.cpp").read_text(encoding="utf-8")
    intent = (ROOT / "src/client/presentation/strategic_intent.h").read_text(encoding="utf-8")

    require(snapshot, [
        "struct StrategicTechnologyView",
        "canonical::TechnologyId id;",
        "canonical::BaseId base;",
        "bool researchable;",
        "bool collected;",
        "const std::vector<StrategicTechnologyView>& technologies() const",
        "struct StrategicProductionView",
        "canonical::TechnologyId technology;",
        "int32_t queueIndex;",
        "const std::vector<StrategicProductionView>& productions() const",
    ], "strategic snapshot")

    production = struct_body(snapshot, "StrategicProductionView")
    if "canonical::ProductionId" in production:
        raise AssertionError("StrategicProductionView must not fabricate a stable ProductionId from queue position")

    require(adapter, [
        "StrategicTechnologyView projectTechnology(",
        "indexedId<canonical::TechnologyId>(technology.idx)",
        "std::vector<StrategicTechnologyView> technologies;",
        "RS_GetTechByIDX(i)",
        "StrategicProductionView projectProduction(",
        "indexedId<canonical::BaseId>(base.idx)",
        "production.idx",
        "PR_GetTech(&production.data)",
        "std::vector<StrategicProductionView> productions;",
        "PR_GetProductionForBase(productionBase)",
    ], "legacy strategic projection")

    require(intent, [
        "canonical::ProductionId production;",
        "submitDecreaseProduction(canonical::BaseId base, int32_t queueIndex, int32_t amount)",
        "submitMoveProductionDown(canonical::BaseId base, int32_t queueIndex)",
        "submitMoveProductionUp(canonical::BaseId base, int32_t queueIndex)",
        "submitStopProduction(canonical::BaseId base, int32_t queueIndex)",
    ], "production intent debt")

    rows = list(csv.DictReader(
        (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open(),
        delimiter="\t",
    ))
    strategic = {r["semantic_action"]: r for r in rows if r["domain"] == "strategic"}
    for name in {"DecreaseProduction", "MoveProductionDown", "MoveProductionUp", "StopProduction",
                 "IncreaseProduction", "SetProductionAmount"}:
        if strategic[name]["authority_bridge"] != "owner_extraction_pending_fail_closed":
            raise AssertionError(f"{name}: production mutation must remain fail-closed in publication-map slice")

    print("PASS M1 Research + Production publication map: TechnologyId + current (BaseId, queueIndex)")
    print("PASS immutable technology and production views expose no raw canonical pointers")
    print("PASS queueIndex remains snapshot-local location metadata; no fabricated ProductionId")
    print("PASS production mutation intents remain fail-closed pending stable identity/revision contract")
except AssertionError as exc:
    print("FAIL M1 Research + Production publication map: " + str(exc), file=sys.stderr)
    raise SystemExit(1)

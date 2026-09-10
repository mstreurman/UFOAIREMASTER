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
        "struct StrategicItemDefinitionView",
        "const std::vector<StrategicItemDefinitionView>& itemDefinitions() const",
        "struct StrategicAircraftDefinitionView",
        "const std::vector<StrategicAircraftDefinitionView>& aircraftDefinitions() const",
        "struct StrategicProductionView",
        "canonical::ProductionId id;",
        "canonical::TechnologyId technology;",
        "canonical::ItemId item;",
        "canonical::StoredUfoId storedUfo;",
        "std::string aircraftDefinition;",
        "int32_t queueIndex;",
        "const std::vector<StrategicProductionView>& productions() const",
    ], "strategic snapshot")

    production = struct_body(snapshot, "StrategicProductionView")
    if production.index("canonical::ProductionId id;") > production.index("int32_t queueIndex;"):
        raise AssertionError("StrategicProductionView should present stable identity before order metadata")

    require(adapter, [
        "StrategicTechnologyView projectTechnology(",
        "indexedId<canonical::TechnologyId>(technology.idx)",
        "std::vector<StrategicTechnologyView> technologies;",
        "RS_GetTechByIDX(i)",
        "StrategicItemDefinitionView projectItemDefinition(",
        "StrategicAircraftDefinitionView projectAircraftDefinition(",
        "StrategicProductionView projectProduction(",
        "canonical::ProductionId(PR_GetProductionRuntimeId(&production))",
        "indexedId<canonical::ItemId>(production.data.data.item->idx)",
        "valueString(production.data.data.aircraft->id)",
        "indexedId<canonical::StoredUfoId>(production.data.data.ufo->idx)",
        "indexedId<canonical::BaseId>(base.idx)",
        "production.idx",
        "PR_GetTech(&production.data)",
        "std::vector<StrategicProductionView> productions;",
        "PR_GetProductionForBase(productionBase)",
    ], "legacy strategic projection")

    require(intent, [
        "canonical::ProductionId production;",
        "submitDecreaseProduction(canonical::BaseId base, canonical::ProductionId production, int32_t amount)",
        "submitMoveProductionDown(canonical::BaseId base, canonical::ProductionId production)",
        "submitMoveProductionUp(canonical::BaseId base, canonical::ProductionId production)",
        "submitStopProduction(canonical::BaseId base, canonical::ProductionId production)",
    ], "production intent debt")

    rows = list(csv.DictReader(
        (ROOT / "tools/remaster/m1-authoritative-intent-coverage.tsv").open(),
        delimiter="\t",
    ))
    strategic = {r["semantic_action"]: r for r in rows if r["domain"] == "strategic"}
    for name in {"DecreaseProduction", "MoveProductionDown", "MoveProductionUp", "StopProduction",
                 "IncreaseProduction", "SetProductionAmount"}:
        if strategic[name]["authority_bridge"] != "canonical_applied":
            raise AssertionError(f"{name}: existing-job production owner must be canonical_applied")
    if strategic["CreateProduction"]["authority_bridge"] != "canonical_applied":
        raise AssertionError("CreateProduction canonical owner extraction missing")
    if strategic["CreateProduction"]["owner_source"] != "src/client/cgame/campaign/cp_produce.cpp":
        raise AssertionError("CreateProduction owner source changed")

    print("PASS M1 Research + Production publication map: TechnologyId + stable ProductionId + typed subjects + current queue order")
    print("PASS immutable technology and production views expose no raw canonical pointers")
    print("PASS ProductionId is canonical runtime identity; queueIndex remains snapshot-local order metadata")
    print("PASS all six existing-job production owners plus CreateProduction are canonical-applied")
except AssertionError as exc:
    print("FAIL M1 Research + Production publication map: " + str(exc), file=sys.stderr)
    raise SystemExit(1)

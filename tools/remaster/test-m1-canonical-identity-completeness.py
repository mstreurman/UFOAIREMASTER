#!/usr/bin/env python3
from __future__ import annotations
import csv, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_STRONG_IDS = [
    "EntityId","MissionId","AircraftId","BaseId","InstallationId","NationId",
    "EmployeeId","TechnologyId","ProductionId","FacilityId","TransferId",
    "DefenceSlotId","MessageId","ItemId","StoredUfoId","UfoRecoveryId","UfoSaleOfferId",
    "TransferManifestId",
]
REQUIRED_REGISTRY = {
    "EntityId": ("runtime_protocol", "direct_protocol"),
    "EmployeeId": ("runtime_direct", "direct_reconciled_persisted_qualified"),
    "TechnologyId": ("runtime_direct", "direct_published"),
    "ProductionId": ("runtime_direct", "runtime_mapping_implemented"),
    "FacilityId": ("runtime_direct", "runtime_mapping_implemented"),
    "TransferId": ("runtime_sidecar_required", "type_added_mapping_missing"),
    "DefenceSlotId": ("runtime_direct", "runtime_mapping_implemented"),
    "MessageId": ("runtime_sidecar_current", "pointer_sidecar_existing"),
    "ItemId": ("static_definition", "runtime_content_ordinal_qualified"),
    "StoredUfoId": ("runtime_direct", "direct_persisted_qualified"),
    "UfoRecoveryId": ("runtime_sidecar_current", "runtime_mapping_implemented"),
    "UfoSaleOfferId": ("runtime_sidecar_current", "runtime_mapping_implemented"),
    "TransferManifestId": ("submission_context", "bounded_submission_registry"),
    "AircraftEquipmentSlot": ("structural_reference", "structural_tuple"),
    "FacilityPlacementCell": ("structural_reference", "structural_tuple"),
    "ContainedAlienSpecies": ("aggregate_key", "technology_key"),
}
def require(cond, msg):
    if not cond:
        raise RuntimeError(msg)
def run(args):
    p = subprocess.run(args, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, check=False)
    if p.returncode != 0:
        raise RuntimeError(f"command failed ({p.returncode}): {' '.join(args)}\n{p.stdout}")
    return p.stdout
def main():
    header = (ROOT/"src/client/presentation/canonical_identity.h").read_text()
    for name in EXPECTED_STRONG_IDS:
        require(name in header, f"canonical_identity.h missing {name}")
    for name in ("FacilityId","TransferId","DefenceSlotId","UfoRecoveryId","UfoSaleOfferId"):
        require(f"UFOAI_CANONICAL_ID_CONTRACT({name})" in header,
                f"new ID domain missing compile-time contract: {name}")
    rows = list(csv.DictReader((ROOT/"tools/remaster/m1-canonical-identity-registry.tsv").open(),
                               delimiter="\t"))
    by_id = {r["identity"]: r for r in rows}
    require(len(by_id) == len(rows), "duplicate identity registry row")
    for ident, (classification, mapping) in REQUIRED_REGISTRY.items():
        require(ident in by_id, f"identity registry missing {ident}")
        require(by_id[ident]["classification"] == classification,
                f"{ident}: wrong classification")
        require(by_id[ident]["mapping_status"] == mapping,
                f"{ident}: wrong mapping status")
    for bogus in ("AircraftEquipmentSlotId","FacilityPlacementCellId","AircraftDefinitionId",
                  "FacilityDefinitionId","InstallationDefinitionId","UgvDefinitionId",
                  "UfoDefinitionId","SaveSlotId","AlienId"):
        require(bogus not in header, f"spurious runtime ID introduced: {bogus}")
    snapshot = (ROOT/"src/client/presentation/strategic_snapshot.h").read_text()
    start = snapshot.find("struct StrategicProductionView")
    require(start >= 0, "StrategicProductionView missing")
    end = snapshot.find("};", start)
    view = snapshot[start:end]
    require("canonical::ProductionId id;" in view,
            "stable ProductionId publication missing")
    require("canonical::ItemId item;" in view,
            "production ItemId subject publication missing")
    require("canonical::StoredUfoId storedUfo;" in view,
            "production StoredUfoId subject publication missing")
    require("std::string aircraftDefinition;" in view,
            "production aircraft definition subject publication missing")
    require("int32_t queueIndex;" in view,
            "production queue location/order metadata missing")
    require("struct StrategicItemDefinitionView" in snapshot,
            "ItemId definition catalog view missing")
    require("struct StrategicAircraftDefinitionView" in snapshot,
            "aircraft definition catalog view missing")
    stored_start = snapshot.find("struct StrategicStoredUfoView")
    require(stored_start >= 0, "StrategicStoredUfoView missing")
    stored_end = snapshot.find("};", stored_start)
    stored_view = snapshot[stored_start:stored_end]
    require("canonical::StoredUfoId id;" in stored_view,
            "StoredUfoId publication missing")
    require("canonical::InstallationId installation;" in stored_view,
            "StoredUfoId installation projection missing")
    cxx = shutil.which("g++")
    require(cxx is not None, "g++ not found")
    build = ROOT/".build/m1-canonical-identity-completeness"
    build.mkdir(parents=True, exist_ok=True)
    binary = build/"m1-canonical-identity-contract"
    run([cxx,"-std=c++11","-Wall","-Wextra","-Werror","-pedantic","-I",str(ROOT),
         str(ROOT/"tools/remaster/m1-canonical-identity-contract.cpp"),"-o",str(binary)])
    out = run([str(binary)])
    require("PASS (18 distinct 32-bit domains)" in out, "expanded identity contract failed")
    print("PASS M1 canonical identity completeness: 18 strong 32-bit domains")
    print("PASS FacilityId/DefenceSlotId mappings plus TransferManifestId submission mapping qualified; TransferId remains reserved debt")
    print("PASS identity taxonomy locked; UfoRecoveryId/UfoSaleOfferId runtime mappings published and qualified")
    print("PASS aggregate authority accounting is owned by test-m1-authoritative-intent-surface.py")
    return 0
if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print("FAIL M1 canonical identity completeness: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

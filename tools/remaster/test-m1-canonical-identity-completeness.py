#!/usr/bin/env python3
from __future__ import annotations
import csv, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_STRONG_IDS = [
    "EntityId","MissionId","AircraftId","BaseId","InstallationId","NationId",
    "EmployeeId","TechnologyId","ProductionId","FacilityId","TransferId",
    "DefenceSlotId","MessageId","ItemId","StoredUfoId","UfoSaleOfferId",
    "TransferManifestId",
]
REQUIRED_REGISTRY = {
    "EntityId": ("runtime_protocol", "direct_protocol"),
    "EmployeeId": ("runtime_direct", "natural_mapping_pending"),
    "TechnologyId": ("runtime_direct", "direct_published"),
    "ProductionId": ("runtime_direct", "runtime_mapping_implemented"),
    "FacilityId": ("runtime_sidecar_required", "type_added_mapping_missing"),
    "TransferId": ("runtime_sidecar_required", "type_added_mapping_missing"),
    "DefenceSlotId": ("runtime_sidecar_required", "type_added_mapping_missing"),
    "MessageId": ("runtime_sidecar_current", "pointer_sidecar_existing"),
    "ItemId": ("static_definition", "definition_mapping_pending"),
    "StoredUfoId": ("runtime_direct", "natural_mapping_pending"),
    "UfoSaleOfferId": ("runtime_sidecar_required", "stable_mapping_missing"),
    "TransferManifestId": ("submission_context", "typed_token_declared"),
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
    for name in ("FacilityId","TransferId","DefenceSlotId"):
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
    require("int32_t queueIndex;" in view,
            "production queue location/order metadata missing")
    ledger = list(csv.DictReader(
        (ROOT/"tools/remaster/m1-authoritative-intent-coverage.tsv").open(), delimiter="\t"))
    strategic = [r for r in ledger if r["domain"] == "strategic"]
    tactical = [r for r in ledger if r["domain"] == "tactical"]
    require(sum(r["authority_bridge"]=="canonical_applied" for r in strategic)==22,
            "strategic applied accounting changed")
    require(sum(r["authority_bridge"]=="owner_extraction_pending_fail_closed" for r in strategic)==35,
            "strategic fail-closed accounting changed")
    require(sum(r["authority_bridge"]=="server_request_forwarded" for r in tactical)==13,
            "tactical forwarded accounting changed")
    require(sum(r["authority_bridge"]=="client_request_helper_pending_fail_closed" for r in tactical)==2,
            "tactical fail-closed accounting changed")
    cxx = shutil.which("g++")
    require(cxx is not None, "g++ not found")
    build = ROOT/".build/m1-canonical-identity-completeness"
    build.mkdir(parents=True, exist_ok=True)
    binary = build/"m1-canonical-identity-contract"
    run([cxx,"-std=c++11","-Wall","-Wextra","-Werror","-pedantic","-I",str(ROOT),
         str(ROOT/"tools/remaster/m1-canonical-identity-contract.cpp"),"-o",str(binary)])
    out = run([str(binary)])
    require("PASS (17 distinct 32-bit domains)" in out, "expanded identity contract failed")
    print("PASS M1 canonical identity completeness: 17 strong 32-bit domains")
    print("PASS missing domains reserved: FacilityId, TransferId, DefenceSlotId")
    print("PASS identity taxonomy and remaining stale-index debt locked; ProductionId mapping published")
    print("PASS authority accounting current: strategic 22/35; tactical 13/2")
    return 0
if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print("FAIL M1 canonical identity completeness: " + str(exc), file=sys.stderr)
        raise SystemExit(1)

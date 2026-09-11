#!/usr/bin/env python3
from pathlib import Path
import csv, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "d10c58e4d6e826db89c4a4c7c7bfcbaf8c3dd903"

STRONG = [
    "EntityId","MissionId","AircraftId","BaseId","InstallationId","NationId",
    "EmployeeId","TechnologyId","ProductionId","FacilityId","TransferId",
    "DefenceSlotId","MessageId","ItemId","StoredUfoId","UfoSaleOfferId",
    "TransferManifestId",
]
ALIASED_STRONG = STRONG[1:]


def require(cond, msg):
    if not cond:
        raise RuntimeError(msg)


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def main():
    p = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"],
        cwd=ROOT
    )
    require(p.returncode == 0,
            "HEAD is not a descendant of the second-pass baseline")

    header = read("src/client/presentation/canonical_identity.h")

    require("struct EntityId {" in header,
            "canonical_identity.h missing hand-written EntityId")

    actual_aliases = []
    for ident in ALIASED_STRONG:
        token = f"using {ident} = detail::StableId<detail::{ident}Tag>;"
        if token in header:
            actual_aliases.append(ident)

    require(
        actual_aliases == ALIASED_STRONG,
        f"strong StableId alias catalog changed: expected {ALIASED_STRONG}, got {actual_aliases}"
    )

    alias_line_count = sum(
        1 for line in header.splitlines()
        if line.strip().startswith("using ")
        and " = detail::StableId<detail::" in line
        and line.strip().endswith(">;")
    )
    require(
        alias_line_count == len(ALIASED_STRONG),
        f"canonical_identity.h StableId alias count changed: "
        f"expected {len(ALIASED_STRONG)}, got {alias_line_count}"
    )

    with (ROOT / "tools/remaster/m1-canonical-identity-lifetime-registry.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    by = {r["identity"]: r for r in rows}
    require(len(by) == len(rows), "duplicate lifetime-registry identity")
    for ident in STRONG:
        require(
            ident in by and by[ident]["kind"] == "strong_id",
            f"missing strong lifetime row: {ident}"
        )

    # UCN evidence: generation, persistence, load reconciliation, duplicate rejection
    # and the inherited signed-16-bit wire domain are now qualified together.
    client_h = read("src/client/client.h")
    cl_team = read("src/client/cl_team.cpp")
    game_team = read("src/client/cgame/cl_game_team.cpp")
    employee = read("src/client/cgame/campaign/cp_employee.cpp")
    character = read("src/client/cgame/campaign/cp_character.cpp")
    events = read("src/game/g_events.cpp")

    require("nextUniqueCharacterNumber" in client_h,
            "client-static UCN allocator field missing")
    require("chr->ucn = cls.nextUniqueCharacterNumber++;" in cl_team,
            "UCN generator changed")
    require("CL_IsCharacterUCNWireRepresentable(cls.nextUniqueCharacterNumber)" in cl_team,
            "UCN signed-wire exhaustion guard missing")
    require("CL_ReconcileCharacterUCN(chr->ucn)" in game_team,
            "UCN allocator reconciliation missing from character load")
    require("Duplicate character UCN" in game_team,
            "standalone team duplicate UCN rejection missing")
    require("E_GetEmployeeFromChrUCN(e.chr.ucn)" in employee and "Duplicate employee UCN" in employee,
            "campaign employee duplicate UCN rejection missing")
    require("XML_AddInt(p, SAVE_CHARACTER_UCN, chr->ucn);" in game_team,
            "UCN save path changed")
    require("chr->ucn = XML_GetInt(p, SAVE_CHARACTER_UCN, 0);" in game_team,
            "UCN load path changed")
    require("E_GetEmployeeFromChrUCN" in employee,
            "employee UCN resolver missing")
    require("c.ucn = cgi->NET_ReadShort(msg);" in character,
            "campaign result UCN wire read changed")
    require("gi.WriteShort(check.chr.ucn);" in events,
            "tactical actor UCN wire write changed")

    tactical_adapter = read(
        "src/client/presentation/tactical_intent_legacy_adapter.cpp"
    )
    g_client = read("src/game/g_client.cpp")
    require("PA_REACT_SELECT" in tactical_adapter,
            "reaction-fire typed lowering changed")
    require("INVSH_GetItemByIDX(objIdx)" in g_client,
            "reaction-fire objDef ordinal resolution changed")
    scripts = read("src/common/scripts.cpp")
    produce = read("src/client/cgame/campaign/cp_produce.cpp")
    snapshot = read("src/client/presentation/strategic_snapshot.h")
    snapshot_adapter = read("src/client/presentation/strategic_snapshot_legacy_adapter.cpp")
    require("od->idx = csi.numODs - 1;" in scripts,
            "ItemId canonical content ordinal assignment changed")
    require("SAVE_PRODUCE_ITEMID, prod->data.data.item->id" in produce and "PR_SetData(&prod->data, PRODUCTION_TYPE_ITEM, INVSH_GetItemByID(s1));" in produce,
            "item production script-key save/load changed")
    require("struct StrategicItemDefinitionView" in snapshot and "canonical::ItemId item;" in snapshot,
            "ItemId/production subject publication missing")
    require("indexedId<canonical::ItemId>(item.idx)" in snapshot_adapter,
            "ItemId definition projection changed")

    base = read("src/client/cgame/campaign/cp_base.h")
    transfer = read("src/client/cgame/campaign/cp_transfer.h")
    require("baseWeapon_t batteries[MAX_BASE_SLOT];" in base,
            "defence topology changed")
    require("typedef struct transfer_s" in transfer,
            "transfer type changed")

    require(by["EmployeeId"]["second_pass_status"] == "qualified_persisted_wire_correlation",
            "EmployeeId qualified lifetime status changed")
    require(by["CharacterUcn"]["second_pass_status"] == "explicit_correlation_qualified",
            "CharacterUcn qualified correlation status changed")
    require(by["ItemId"]["second_pass_status"] == "qualified_runtime_content_ordinal",
            "ItemId qualified lifetime status changed")
    require(by["FacilityId"]["second_pass_status"] == "qualified_runtime_mapping",
            "FacilityId runtime mapping qualification regressed")
    require(by["TransferId"]["second_pass_status"] == "pending_mapping",
            "TransferId debt status changed")
    require(by["DefenceSlotId"]["second_pass_status"] == "pending_mapping",
            "DefenceSlotId debt status changed")

    print("PASS M1 second-pass identity lifetime audit")
    print("  strong canonical ID domains: 17/17")
    print("    EntityId: hand-written protocol value type")
    print("    StableId aliases: 16/16")
    print("  UCN generation/save/load/wire correlation: explicit")
    print("  UCN allocator restoration/non-reuse + signed-16-bit wire domain: qualified")
    print("  ItemId current-content ordinal + stable script key: qualified")
    print("  FacilityId runtime mapping: qualified; Transfer/Defence/Message debt remains pending")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print("FAIL M1 second-pass identity lifetime audit:", exc, file=sys.stderr)
        raise SystemExit(1)

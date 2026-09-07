#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

BASELINE = "8c8daf73150acff077b63fbf127a1cd1679f4b79"

class GateError(RuntimeError):
    pass


def run(args: list[str], root: Path) -> str:
    proc = subprocess.run(args, cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    if proc.returncode != 0:
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout}")
    return proc.stdout


def root_dir() -> Path:
    proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise GateError("not inside a Git work tree")
    return Path(proc.stdout.strip()).resolve()


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def require(cond: bool, message: str) -> None:
    if not cond:
        raise GateError(message)


def audit(root: Path) -> None:
    ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], cwd=root, check=False)
    require(ancestor.returncode == 0, f"HEAD is not descended from strategic-publication baseline {BASELINE}")

    snapshot = (root / "src/client/presentation/strategic_snapshot.h").read_text(encoding="utf-8")
    publication = (root / "src/client/presentation/strategic_publication.cpp").read_text(encoding="utf-8")
    adapter = (root / "src/client/presentation/strategic_snapshot_legacy_adapter.cpp").read_text(encoding="utf-8")
    campaign = (root / "src/client/cgame/campaign/cp_campaign.cpp").read_text(encoding="utf-8")
    callbacks = (root / "src/client/cgame/campaign/cp_cgame_callbacks.cpp").read_text(encoding="utf-8")
    client_cmake = (root / "src/client/CMakeLists.txt").read_text(encoding="utf-8")
    root_cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")

    public = strip_comments(snapshot + "\n" + (root / "src/client/presentation/strategic_publication.h").read_text(encoding="utf-8"))
    for token in (
        "ccs_t", "mission_t", "aircraft_t", "base_t", "installation_t", "nation_t",
        "uiMessageListNodeMessage_t", "linkedList_t", "uiNode_t", "DateTime", "cgi->",
        "Vk", "JPH::", "ALuint",
    ):
        require(token not in public, f"legacy/runtime type leaked into public strategic contract: {token}")

    for token in (
        "StrategicMissionView", "StrategicAircraftView", "StrategicBaseView",
        "StrategicInstallationView", "StrategicNationView", "StrategicMessageView",
        "StrategicSelectionView", "std::vector<StrategicMissionView>",
        "std::vector<StrategicMessageView>", "const std::vector<StrategicMissionView>& missions() const",
    ):
        require(token in snapshot, f"strategic snapshot contract missing: {token}")

    cl_shared_include = '#include "../cl_shared.h"'
    campaign_include = '#include "../cgame/campaign/cp_campaign.h"'
    require(cl_shared_include in adapter, "legacy strategic adapter missing cl_shared campaign prerequisite")
    require(campaign_include in adapter, "legacy strategic adapter missing cp_campaign include")
    require(adapter.index(cl_shared_include) < adapter.index(campaign_include),
            "legacy strategic adapter must establish cl_shared types before cp_campaign.h")

    for token in (
        "MIS_Foreach(mission)", "AIR_Foreach(craft)", "ccs.numUFOs", "ccs.numBases",
        "INS_Foreach(installation)", "NAT_Foreach(nation)", "cgi->UI_MessageGetStack()",
        "std::map<const uiMessageListNodeMessage_t*, canonical::MessageId> messageIds",
        "UFO_AIRCRAFT_ID_BIT", "messageIds.clear()", "nextMessageId = 0",
        "ccs.geoscape.selectedMission", "ccs.geoscape.selectedAircraft", "ccs.geoscape.selectedUFO",
        "B_GetCurrentSelectedBase()", "INS_GetCurrentSelectedInstallation()",
    ):
        require(token in adapter, f"legacy strategic projection missing required mapping: {token}")

    require("std::mutex publicationMutex;" in publication, "strategic publication must synchronize shared_ptr handoff")
    require("publicationSequence.fetch_add(1, std::memory_order_relaxed) + 1" in publication, "strategic publication serial must be monotonic")
    require("std::make_shared<const StrategicSnapshot>" in publication, "strategic publication must expose immutable shared ownership")

    frame_pattern = re.compile(
        r"CP_CampaignRun\(ccs\.curCampaign, secondsSinceLastFrame\);\s*"
        r"ufo::presentation::legacy::publishAfterCanonicalCampaignUpdate\(\);"
    )
    require(frame_pattern.search(callbacks) is not None, "strategic publication is not ordered after CP_CampaignRun")

    require(campaign.count("ufo::presentation::legacy::resetStrategicPublication();") == 2,
            "strategic publication/message identity state must reset at campaign init and shutdown")

    for token in (
        "presentation/strategic_snapshot_legacy_adapter.cpp",
        "presentation/strategic_publication.cpp",
    ):
        require(token in client_cmake, f"production client CMake missing strategic source: {token}")

    # cp_campaign.cpp and cp_cgame_callbacks.cpp are compiled into ufotestall by the sealed
    # canonical harness. Their strategic publication calls therefore require the same
    # implementation TUs to be attached at the root target-ownership seam, just as M1.2
    # already does for tactical publication.
    for token in (
        '${CMAKE_SOURCE_DIR}/src/client/presentation/strategic_snapshot_legacy_adapter.cpp',
        '${CMAKE_SOURCE_DIR}/src/client/presentation/strategic_publication.cpp',
    ):
        require(token in root_cmake, f"ufotestall root CMake ownership missing strategic source: {token}")


def compile_contract(root: Path) -> None:
    build = root / ".build/m1-strategic-publication-contract"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)
    binary = build / "m1-strategic-publication-contract"
    common = ["g++", "-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-I", str(root)]
    run(common + [str(root / "tools/remaster/m1-strategic-publication-contract.cpp"), "-o", str(binary)], root)
    output = run([str(binary)], root)
    require("M1 strategic snapshot contract: PASS" in output, "strategic snapshot contract executable did not pass")

    # Compile the publication handoff itself as a strict standalone translation unit.
    run(common + ["-c", str(root / "src/client/presentation/strategic_publication.cpp"), "-o", str(build / "strategic_publication.o")], root)


def main() -> int:
    root = root_dir()
    audit(root)
    compile_contract(root)
    print("M1 strategic publication focused lane: PASS")
    print("  public raw-pointer/type audit: PASS")
    print("  production publication ordering audit: PASS")
    print("  legacy projection coverage audit: PASS")
    print("  legacy adapter campaign prerequisite audit: PASS")
    print("  ufotestall source-ownership audit: PASS")
    print("  strict C++11 snapshot contract: PASS")
    print("  strict C++11 publication TU compile: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1 strategic publication focused lane: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

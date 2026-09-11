#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


class GateError(RuntimeError):
    pass


def run(args: list[str], root: Path, *, stream: bool = False) -> str:
    if stream:
        print("+ " + " ".join(args), flush=True)
        proc = subprocess.Popen(
            args, cwd=root, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
        )
        assert proc.stdout is not None
        chunks: list[str] = []
        for line in proc.stdout:
            chunks.append(line)
            print(line, end="", flush=True)
        rc = proc.wait()
        if rc != 0:
            raise GateError(f"command failed ({rc}): {' '.join(args)}")
        return "".join(chunks)

    proc = subprocess.run(
        args, cwd=root, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False,
    )
    if proc.returncode != 0:
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout}")
    return proc.stdout


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise GateError(msg)


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if proc.returncode != 0:
        raise GateError("not inside a Git work tree")
    return Path(proc.stdout.strip()).resolve()


def source_audit(root: Path) -> None:
    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    client_cmake = (root / "src/client/CMakeLists.txt").read_text(encoding="utf-8")
    cl_main = (root / "src/client/cl_main.cpp").read_text(encoding="utf-8")
    strategic_h = (root / "src/client/presentation/strategic_intent.h").read_text(encoding="utf-8")
    strategic_adapter = (root / "src/client/presentation/strategic_intent_legacy_adapter.cpp").read_text(encoding="utf-8")
    tactical_h = (root / "src/client/presentation/tactical_intent.h").read_text(encoding="utf-8")
    tactical_adapter = (root / "src/client/presentation/tactical_intent_legacy_adapter.cpp").read_text(encoding="utf-8")
    server = (root / "src/game/g_client.cpp").read_text(encoding="utf-8")

    for token in (
        "SetCampaignTimeLapse = 1",
        "SelectMission = 2",
        "SelectAircraft = 3",
        "SendAircraftToMission = 4",
        "ReturnAircraftToBase = 5",
        "submitSelectMission",
        "submitSelectAircraft",
        "submitSendAircraftToMission",
        "submitReturnAircraftToBase",
    ):
        require(token in strategic_h, f"strategic catalog token missing: {token}")

    for token in (
        "TacticalIntentKind",
        "SetReactionFire = 1",
        "SetReservedTimeUnits = 2",
        "ForwardedToServer = 1",
        "RejectedByClientBoundary = 2",
        "submitSetReactionFire",
        "submitSetReservedTimeUnits",
    ):
        require(token in tactical_h, f"tactical catalog token missing: {token}")

    # Audit owner semantics without depending on temporary local-variable names.
    for kind, owner_call in (
        ("SelectMission", "GEO_SelectMission("),
        ("SelectAircraft", "GEO_SelectAircraft("),
        ("SendAircraftToMission", "AIR_TrySendAircraftToMission("),
        ("ReturnAircraftToBase", "AIR_AircraftReturnToBase("),
    ):
        case_match = re.search(
            rf"case StrategicIntentKind::{kind}\s*:(?P<body>.*?)(?=\n\s*case StrategicIntentKind::)",
            strategic_adapter, flags=re.S,
        )
        require(case_match is not None, f"strategic compatibility case missing: {kind}")
        require(owner_call in case_match.group("body"),
                f"strategic canonical adapter mapping missing for {kind}: {owner_call}")
    require("RejectedByCanonical" in strategic_adapter,
            "strategic canonical rejection disposition missing")

    for token in (
        "MAX_TACTICAL_INTENTS_PER_FRAME = 64",
        "MSG_Write_PA(",
        "PA_STATE",
        "STATE_REACTION",
        "PA_RESERVE_STATE",
        "ForwardedToServer",
        "RejectedByClientBoundary",
    ):
        require(token in tactical_adapter, f"tactical client/server adapter mapping missing: {token}")

    # Tactical adapter drains after console/UI commands but before userinfo/network send.
    send_match = re.search(
        r"static void CL_SendCommand \(void\)\s*\{(?P<body>.*?)\n\}",
        cl_main, flags=re.S,
    )
    require(send_match is not None, "CL_SendCommand source body not found")
    body = send_match.group("body")
    cbuf = body.find("Cbuf_Execute();")
    tactical = body.find("applyPendingTacticalIntents();")
    userinfo = body.find("CL_SendChangedUserinfos();")
    require(0 <= cbuf < tactical < userinfo,
            "tactical typed intents must drain after UI/console input and before command send completion")

    clear_match = re.search(
        r"static void CL_ClearState \(void\)\s*\{(?P<body>.*?)\n\}",
        cl_main, flags=re.S,
    )
    require(clear_match is not None, "CL_ClearState source body not found")
    require("resetTacticalIntentAdapter();" in clear_match.group("body"),
            "tactical intent runtime must reset with tactical client state")

    for token in (
        "case PA_STATE:",
        "G_ClientStateChange(player, actor, i, true);",
        "case PA_RESERVE_STATE:",
        "G_ActorReserveTUs(ent, ent->chr.reservedTus.reaction, resShot, resCrouch);",
    ):
        require(token in server, f"server authority mapping missing: {token}")

    require("presentation/tactical_intent_legacy_adapter.cpp" in client_cmake,
            "production ufo target must own the tactical C++11 adapter")
    require("presentation/tactical_intent_dispatch.cpp" not in client_cmake,
            "C++26 tactical runtime must not compile directly inside legacy ufo target")

    for token in (
        'option(UFOAI_M1_INTENT_CATALOG_TESTS',
        '"${CMAKE_SOURCE_DIR}/src/client/presentation/tactical_intent_dispatch.cpp"',
        '"${CMAKE_SOURCE_DIR}/src/client/presentation/tactical_intent_legacy_adapter.cpp"',
        '"${CMAKE_SOURCE_DIR}/tools/remaster/m1-intent-catalog-integration.cpp"',
    ):
        require(token in cmake, f"root CMake intent-catalog ownership token missing: {token}")

    sealed = run(["git", "hash-object", "src/tests/CMakeLists.txt"], root).strip()
    require(sealed == "5110f532e62126a7b89fc07b1248717e5e71cbf0",
            f"sealed src/tests/CMakeLists.txt changed: {sealed}")


def direct_contracts(root: Path, build: Path) -> None:
    header = build / "m1-intent-catalog-header-contract"
    run([
        "g++", "-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", str(root),
        str(root / "tools/remaster/m1-intent-catalog-header-contract.cpp"),
        "-o", str(header),
    ], root)
    run([str(header)], root)

    runtime = build / "m1-intent-catalog-runtime-contract"
    run([
        "g++", "-std=c++26", "-Wall", "-Wextra", "-Werror", "-pedantic",
        "-I", str(root),
        str(root / "tools/remaster/m1-intent-catalog-contract.cpp"),
        str(root / "src/client/presentation/strategic_intent_dispatch.cpp"),
        str(root / "src/client/presentation/tactical_intent_dispatch.cpp"),
        "-pthread",
        "-o", str(runtime),
    ], root)
    output = run([str(runtime)], root)
    require("M1 expanded intent runtime contract: PASS" in output,
            "expanded intent runtime contract did not pass")


def integration_lane(root: Path, build: Path) -> None:
    configure = [
        "cmake", "-S", str(root), "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        "-DCMAKE_C_COMPILER=gcc",
        "-DCMAKE_CXX_COMPILER=g++",
        "-DUFOAI_REMASTER=OFF",
        "-DUFOAI_M1_INTENT_CATALOG_TESTS=ON",
        "-DDISABLE_UFO=ON",
        "-DDISABLE_UFODED=ON",
        "-DDISABLE_TESTS=OFF",
        "-DDISABLE_TOOLS=ON",
        "-DDISABLE_UFORADIANT=ON",
        "-DDISABLE_I18N=ON",
        "-DDISABLE_MANUAL=ON",
        "-DDISABLE_DOXYGEN_DOCS=ON",
        "-DDISABLE_BASE_PACKAGES=ON",
        "-DDISABLE_MAPS_COMPILE=ON",
    ]
    run(configure, root, stream=True)
    run(["cmake", "--build", str(build), "--parallel", "8", "--target", "ufotestall"],
        root, stream=True)
    output = run([
        str(build / "ufotestall"),
        "--gtest_filter=M1IntentCatalogTest.*",
        "--gtest_color=no",
        "--gtest_print_time=0",
    ], root, stream=True)
    require("[  PASSED  ] 3 tests." in output,
            "expanded intent catalog integration GoogleTests did not pass 3/3")


def main() -> int:
    root = repo_root()
    source_audit(root)

    build = root / ".build/m1-intent-catalog-expansion"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)

    direct_contracts(root, build)
    integration_lane(root, build)

    print("M1 intent catalog expansion lane: PASS")
    print("  seed strategic compatibility catalog: 5 intents (selection entries deprecated for new presentation)")
    print("  seed tactical compatibility catalog: 2 typed server-forwarded intents")
    print("  strict C++11 public contracts: PASS")
    print("  strict C++26 bounded runtimes: PASS")
    print("  FIFO/capacity/reset/sequence contracts: PASS")
    print("  strategic canonical-owner mappings: PASS")
    print("  tactical PA_STATE/PA_RESERVE_STATE server-authority mapping: PASS")
    print("  integration GoogleTests: 3/3")
    print("  sealed src/tests/CMakeLists.txt: unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1 intent catalog expansion lane: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

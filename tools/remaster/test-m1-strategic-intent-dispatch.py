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
            args,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
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
        args,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
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
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise GateError("not inside a Git work tree")
    return Path(proc.stdout.strip()).resolve()


def source_audit(root: Path) -> None:
    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    client_cmake = (root / "src/client/CMakeLists.txt").read_text(encoding="utf-8")
    callbacks = (root / "src/client/cgame/campaign/cp_cgame_callbacks.cpp").read_text(encoding="utf-8")
    campaign = (root / "src/client/cgame/campaign/cp_campaign.cpp").read_text(encoding="utf-8")
    time_cpp = (root / "src/client/cgame/campaign/cp_time.cpp").read_text(encoding="utf-8")
    adapter = (root / "src/client/presentation/strategic_intent_legacy_adapter.cpp").read_text(encoding="utf-8")
    runtime = (root / "src/client/presentation/strategic_intent_dispatch.cpp").read_text(encoding="utf-8")

    cl_shared_pos = adapter.find('#include "../cl_shared.h"')
    campaign_header_pos = adapter.find('#include "../cgame/campaign/cp_campaign.h"')
    require(0 <= cl_shared_pos < campaign_header_pos,
            "strategic intent legacy adapter must include cl_shared.h before cp_campaign.h")

    for token in (
        'option(UFOAI_M1_STRATEGIC_INTENT_TESTS',
        'add_library(ufoai_remaster_intent_runtime OBJECT',
        'src/client/presentation/strategic_intent_dispatch.cpp',
        'CXX_STANDARD 26',
        '$<TARGET_OBJECTS:ufoai_remaster_intent_runtime>',
        'src/client/presentation/strategic_intent_legacy_adapter.cpp',
    ):
        require(token in cmake, f"root CMake missing strategic intent ownership token: {token}")

    require("presentation/strategic_intent_legacy_adapter.cpp" in client_cmake,
            "production ufo target must compile the C++11 strategic intent adapter")
    require("presentation/strategic_intent_dispatch.cpp" not in client_cmake,
            "C++26 intent runtime must not compile directly inside legacy ufo target")

    frame_match = re.search(
        r"void GAME_CP_Frame \(float secondsSinceLastFrame\)\s*\{(?P<body>.*?)\n\}",
        callbacks,
        flags=re.S,
    )
    require(frame_match is not None, "GAME_CP_Frame source body not found")
    body = frame_match.group("body")
    apply_pos = body.find("applyPendingStrategicIntents();")
    campaign_pos = body.find("CP_CampaignRun(")
    publish_pos = body.find("publishAfterCanonicalCampaignUpdate();")
    require(0 <= apply_pos < campaign_pos < publish_pos,
            "strategic intent handling must occur before canonical campaign run and publication")

    require(campaign.count("resetStrategicIntentAdapter();") == 2,
            "campaign init/shutdown must reset strategic intent runtime exactly twice")

    setter_match = re.search(
        r"bool CP_TrySetGameTimeLapse \(int gameLapseValue\)\s*\{(?P<body>.*?)\n\}",
        time_cpp,
        flags=re.S,
    )
    require(setter_match is not None, "canonical presentation time-lapse setter missing")
    setter = setter_match.group("body")
    for token in (
        "CP_AllowTimeScale()",
        "gameLapseValue < 0",
        "gameLapseValue >= NUM_TIMELAPSE",
        "ccs.gameLapse = gameLapseValue;",
        "CP_UpdateTime();",
    ):
        require(token in setter, f"canonical time-lapse validation/mutation missing: {token}")

    for token in (
        "MAX_STRATEGIC_INTENTS_PER_FRAME = 64",
        "tryPopStrategicIntent",
        "CP_TrySetGameTimeLapse(intentValue.value)",
        "RejectedByCanonical",
        "result.canonicalValue = ccs.gameLapse",
        "publishStrategicIntentResult",
    ):
        require(token in adapter, f"legacy intent adapter contract missing: {token}")

    for token in (
        "STRATEGIC_INTENT_CAPACITY = 256",
        "STRATEGIC_INTENT_RESULT_CAPACITY = 256",
        "submitSetCampaignTimeLapse",
        "pollStrategicIntentResult",
        "pendingIntents.full()",
        "intentResults.full()",
        "resetStrategicIntentRuntime",
    ):
        require(token in runtime, f"C++26 strategic intent runtime contract missing: {token}")

    sealed = run(["git", "hash-object", "src/tests/CMakeLists.txt"], root).strip()
    require(sealed == "5110f532e62126a7b89fc07b1248717e5e71cbf0",
            f"sealed src/tests/CMakeLists.txt changed: {sealed}")


def direct_contracts(root: Path, build: Path) -> None:
    include = ["-I", str(root)]

    header_binary = build / "m1-strategic-intent-header-contract"
    run([
        "g++", "-std=c++11", "-Wall", "-Wextra", "-Werror", "-pedantic",
        *include,
        str(root / "tools/remaster/m1-strategic-intent-header-contract.cpp"),
        "-o", str(header_binary),
    ], root)
    run([str(header_binary)], root)

    runtime_binary = build / "m1-strategic-intent-runtime-contract"
    run([
        "g++", "-std=c++26", "-Wall", "-Wextra", "-Werror", "-pedantic",
        *include,
        str(root / "tools/remaster/m1-strategic-intent-contract.cpp"),
        str(root / "src/client/presentation/strategic_intent_dispatch.cpp"),
        "-pthread",
        "-o", str(runtime_binary),
    ], root)
    output = run([str(runtime_binary)], root)
    require("M1 strategic intent runtime contract: PASS" in output,
            "strategic intent runtime contract did not pass")


def integration_lane(root: Path, build: Path) -> None:
    configure = [
        "cmake", "-S", str(root), "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        "-DCMAKE_C_COMPILER=gcc",
        "-DCMAKE_CXX_COMPILER=g++",
        "-DUFOAI_REMASTER=OFF",
        "-DUFOAI_M1_STRATEGIC_INTENT_TESTS=ON",
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
    run(["cmake", "--build", str(build), "--parallel", "8", "--target", "ufotestall"], root, stream=True)
    output = run([
        str(build / "ufotestall"),
        "--gtest_filter=M1StrategicIntentTest.*",
        "--gtest_color=no",
        "--gtest_print_time=0",
    ], root, stream=True)
    require("[  PASSED  ] 3 tests." in output,
            "strategic intent integration GoogleTests did not pass 3/3")


def main() -> int:
    root = repo_root()
    source_audit(root)

    build = root / ".build/m1-strategic-intent-dispatch"
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)

    direct_contracts(root, build)
    integration_lane(root, build)

    print("M1 strategic typed intent dispatch lane: PASS")
    print("  C++11 public intent contract: PASS")
    print("  bounded C++26 intent/result runtime: PASS")
    print("  queue FIFO/capacity/reset/sequence contract: PASS")
    print("  Main-before-campaign-before-publication ordering audit: PASS")
    print("  canonical time-lapse validation/mutation audit: PASS")
    print("  strategic intent integration GoogleTests: 3/3")
    print("  sealed src/tests/CMakeLists.txt: unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1 strategic typed intent dispatch lane: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

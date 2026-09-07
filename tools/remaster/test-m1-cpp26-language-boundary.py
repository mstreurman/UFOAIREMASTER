#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASELINE = "5b45c193aff9a9ff170d1aaacabaa5a786702c3d"
BUILD_REL = Path(".build/m1-cpp26-language-boundary")


class GateError(RuntimeError):
    pass


def run(args: list[str], root: Path, *, capture: bool = True) -> str:
    proc = subprocess.run(
        args,
        cwd=root,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if proc.returncode != 0:
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout or ''}")
    return proc.stdout or ""


def run_streaming(args: list[str], root: Path) -> str:
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


def require(cond: bool, message: str) -> None:
    if not cond:
        raise GateError(message)


def require_baseline(root: Path) -> None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    require(proc.returncode == 0, f"HEAD is not descended from language-boundary baseline {BASELINE}")


def gcc_version(root: Path) -> str:
    version = run(["g++", "-dumpfullversion"], root).strip()
    if not version:
        version = run(["g++", "-dumpversion"], root).strip()
    require(re.match(r"^16\.2(?:\.|$)", version) is not None,
            f"reference lane requires GCC 16.2.x, found {version!r}")
    return version


def libstdcxx_abi(root: Path) -> str:
    macros = run(
        ["g++", "-std=c++11", "-dM", "-E", "-x", "c++", "-include", "string", "/dev/null"],
        root,
    )
    match = re.search(r"^#define _GLIBCXX_USE_CXX11_ABI (\d+)$", macros, flags=re.M)
    require(match is not None, "could not resolve _GLIBCXX_USE_CXX11_ABI")
    require(match.group(1) == "1", "reference lane requires _GLIBCXX_USE_CXX11_ABI=1")
    return match.group(1)


def audit_source_contract(root: Path) -> None:
    require_baseline(root)

    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    client_cmake = (root / "src/client/CMakeLists.txt").read_text(encoding="utf-8")
    tactical = (root / "src/client/presentation/tactical_publication.cpp").read_text(encoding="utf-8")
    tests_cmake = root / "src/tests/CMakeLists.txt"

    require("cmake_minimum_required(VERSION 3.25)" in cmake, "root CMake minimum must be 3.25")
    require("project(ufoai LANGUAGES CXX)" in cmake, "root project must enable CXX for root-owned language targets")
    require('set(CMAKE_CXX_STANDARD 11)' in cmake, "retained target default must be C++11")
    require('set(CMAKE_CXX_STANDARD_REQUIRED YES)' in cmake, "retained C++11 standard must be required")
    require('set(CMAKE_CXX_EXTENSIONS OFF)' in cmake, "retained Fedora baseline must use non-GNU C++ mode")
    require('add_library(ufoai_remaster_publication OBJECT' in cmake,
            "missing root-owned C++26 publication object target")
    for token in (
        'CXX_STANDARD 26',
        'CXX_STANDARD_REQUIRED YES',
        'CXX_EXTENSIONS NO',
        '$<TARGET_OBJECTS:ufoai_remaster_publication>',
        'src/client/presentation/tactical_publication.cpp',
        'src/client/presentation/strategic_publication.cpp',
    ):
        require(token in cmake, f"root language-boundary CMake contract missing: {token}")

    forbidden_global = (
        'CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=',
        "-std=c++0x",
        "-std=gnu++0x",
    )
    for token in forbidden_global:
        require(token not in cmake, f"inherited global language forcing remains: {token}")

    require("presentation/tactical_snapshot_legacy_adapter.cpp" in client_cmake,
            "tactical legacy adapter must remain client-owned C++11 source")
    require("presentation/strategic_snapshot_legacy_adapter.cpp" in client_cmake,
            "strategic legacy adapter must remain client-owned C++11 source")
    require("presentation/tactical_publication.cpp" not in client_cmake,
            "tactical publication must not be compiled directly by the legacy client target")
    require("presentation/strategic_publication.cpp" not in client_cmake,
            "strategic publication must not be compiled directly by the legacy client target")

    require("std::atomic<ufo::presentation::TacticalPublicationPtr> latestPublication;" in tactical,
            "tactical publication must use atomic<shared_ptr> specialization")
    require("latestPublication.load(std::memory_order_acquire)" in tactical,
            "tactical publication must acquire-load completed publication")
    require("latestPublication.store(publication, std::memory_order_release)" in tactical,
            "tactical publication must release-store completed publication")
    require("std::atomic_load_explicit(&latestPublication" not in tactical,
            "removed/deprecated shared_ptr atomic free-function load remains")
    require("std::atomic_store_explicit(&latestPublication" not in tactical,
            "removed/deprecated shared_ptr atomic free-function store remains")

    blob = run(["git", "hash-object", str(tests_cmake)], root).strip()
    require(blob == "5110f532e62126a7b89fc07b1248717e5e71cbf0",
            f"sealed src/tests/CMakeLists.txt changed: {blob}")


def write_compile_fixtures(root: Path, build: Path) -> tuple[Path, Path, Path]:
    fixture = build / "fixture"
    fixture.mkdir(parents=True, exist_ok=True)

    bridge_headers = fixture / "bridge_headers.cpp"
    bridge_headers.write_text(
        '#include "src/client/presentation/canonical_identity.h"\n'
        '#include "src/client/presentation/tactical_snapshot.h"\n'
        '#include "src/client/presentation/tactical_presentation_event.h"\n'
        '#include "src/client/presentation/tactical_publication.h"\n'
        '#include "src/client/presentation/strategic_snapshot.h"\n'
        '#include "src/client/presentation/strategic_publication.h"\n'
        'int main() { return 0; }\n',
        encoding="utf-8",
    )

    boundary_header = fixture / "mixed_boundary.h"
    boundary_header.write_text(
        '#pragma once\n'
        '#include "src/client/presentation/tactical_snapshot.h"\n'
        '#include "src/client/presentation/strategic_snapshot.h"\n'
        'ufo::presentation::TacticalSnapshot m1_make_tactical_snapshot();\n'
        'ufo::presentation::StrategicSnapshot m1_make_strategic_snapshot();\n',
        encoding="utf-8",
    )

    producer = fixture / "producer.cpp"
    producer.write_text(
        '#include "mixed_boundary.h"\n'
        '#include <utility>\n'
        '#include <vector>\n'
        'ufo::presentation::TacticalSnapshot m1_make_tactical_snapshot() {\n'
        '  ufo::presentation::TacticalActorView actor = {};\n'
        '  actor.entity = ufo::canonical::EntityId(7u);\n'
        '  actor.hitPoints = 42;\n'
        '  std::vector<ufo::presentation::TacticalActorView> actors;\n'
        '  actors.push_back(actor);\n'
        '  return ufo::presentation::TacticalSnapshot(11u, std::move(actors));\n'
        '}\n'
        'ufo::presentation::StrategicSnapshot m1_make_strategic_snapshot() {\n'
        '  using namespace ufo::presentation;\n'
        '  StrategicCampaignTime time = {3, 90};\n'
        '  StrategicSelectionView selection = {};\n'
        '  selection.mission = ufo::canonical::MissionId(9u);\n'
        '  std::vector<StrategicMissionView> missions;\n'
        '  std::vector<StrategicAircraftView> aircraft;\n'
        '  std::vector<StrategicBaseView> bases;\n'
        '  std::vector<StrategicInstallationView> installations;\n'
        '  std::vector<StrategicNationView> nations;\n'
        '  std::vector<StrategicMessageView> messages;\n'
        '  StrategicMessageView message = {};\n'
        '  message.id = ufo::canonical::MessageId(13u);\n'
        '  message.time = time;\n'
        '  message.type = 4;\n'
        '  message.title = "boundary";\n'
        '  message.text = "c++11-to-c++26";\n'
        '  message.iconName = "test";\n'
        '  messages.push_back(message);\n'
        '  return StrategicSnapshot(12u, time, 1234, 2, selection,\n'
        '    std::move(missions), std::move(aircraft), std::move(bases),\n'
        '    std::move(installations), std::move(nations), std::move(messages));\n'
        '}\n',
        encoding="utf-8",
    )

    consumer = fixture / "consumer.cpp"
    consumer.write_text(
        '#include "mixed_boundary.h"\n'
        '#include <iostream>\n'
        '#include <string_view>\n'
        'int main() {\n'
        '  const auto tactical = m1_make_tactical_snapshot();\n'
        '  if (tactical.publicationSerial() != 11u || tactical.actors().size() != 1u) return 10;\n'
        '  if (tactical.actors()[0].entity.value != 7u || tactical.actors()[0].hitPoints != 42) return 11;\n'
        '  const auto strategic = m1_make_strategic_snapshot();\n'
        '  if (strategic.publicationSerial() != 12u || strategic.credits() != 1234) return 20;\n'
        '  if (strategic.selection().mission.value != 9u || strategic.messages().size() != 1u) return 21;\n'
        '  if (std::string_view(strategic.messages()[0].title) != "boundary") return 22;\n'
        '  if (std::string_view(strategic.messages()[0].text) != "c++11-to-c++26") return 23;\n'
        '  std::cout << "M1 C++11/C++26 mixed ABI fixture: PASS\\n";\n'
        '  return 0;\n'
        '}\n',
        encoding="utf-8",
    )
    return bridge_headers, producer, consumer


def direct_language_checks(root: Path, build: Path) -> None:
    fixture = build / "fixture"
    bridge_headers, producer, consumer = write_compile_fixtures(root, build)

    common = ["-Wall", "-Wextra", "-Werror", "-pedantic", "-I", str(root), "-I", str(fixture)]
    run(["g++", "-std=c++11", *common, "-c", str(bridge_headers), "-o", str(fixture / "bridge-cxx11.o")], root)
    run(["g++", "-std=c++26", *common, "-c", str(bridge_headers), "-o", str(fixture / "bridge-cxx26.o")], root)

    modern_common = ["g++", "-std=c++26", "-Wall", "-Wextra", "-Werror", "-pedantic", "-I", str(root)]
    run(
        modern_common + [
            "-c", str(root / "src/client/presentation/tactical_publication.cpp"),
            "-o", str(fixture / "tactical_publication-cxx26.o"),
        ],
        root,
    )
    run(
        modern_common + [
            "-c", str(root / "src/client/presentation/strategic_publication.cpp"),
            "-o", str(fixture / "strategic_publication-cxx26.o"),
        ],
        root,
    )

    run(["g++", "-std=c++11", *common, "-c", str(producer), "-o", str(fixture / "producer.o")], root)
    run(["g++", "-std=c++26", *common, "-c", str(consumer), "-o", str(fixture / "consumer.o")], root)
    binary = fixture / "mixed-boundary"
    run(["g++", "-std=c++26", str(fixture / "producer.o"), str(fixture / "consumer.o"), "-o", str(binary)], root)
    output = run([str(binary)], root)
    require("M1 C++11/C++26 mixed ABI fixture: PASS" in output,
            "mixed C++11/C++26 ABI fixture did not pass")


def configure_and_audit_commands(root: Path, build: Path) -> None:
    configure = [
        "cmake", "-S", str(root), "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        "-DCMAKE_C_COMPILER=gcc",
        "-DCMAKE_CXX_COMPILER=g++",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        "-DUFOAI_REMASTER=OFF",
        "-DDISABLE_UFO=OFF",
        "-DDISABLE_UFODED=ON",
        "-DDISABLE_TESTS=ON",
        "-DDISABLE_TOOLS=ON",
        "-DDISABLE_UFORADIANT=ON",
        "-DDISABLE_I18N=ON",
        "-DDISABLE_MANUAL=ON",
        "-DDISABLE_DOXYGEN_DOCS=ON",
        "-DDISABLE_BASE_PACKAGES=ON",
        "-DDISABLE_MAPS_COMPILE=ON",
    ]
    run_streaming(configure, root)
    run_streaming(["cmake", "--build", str(build), "--target", "ufoai_remaster_publication", "--parallel", "4"], root)

    commands = json.loads((build / "compile_commands.json").read_text(encoding="utf-8"))

    def commands_for(suffix: str) -> list[str]:
        return [entry["command"] for entry in commands if entry["file"].replace("\\", "/").endswith(suffix)]

    for suffix in (
        "src/client/presentation/tactical_publication.cpp",
        "src/client/presentation/strategic_publication.cpp",
    ):
        hits = commands_for(suffix)
        require(len(hits) == 1, f"expected one CMake compile command for {suffix}, found {len(hits)}")
        require("-std=c++26" in hits[0], f"{suffix} is not compiled as C++26: {hits[0]}")
        require("-std=gnu++26" not in hits[0], f"{suffix} unexpectedly enables GNU C++26 extensions")

    for suffix in (
        "src/client/presentation/tactical_snapshot_legacy_adapter.cpp",
        "src/client/presentation/strategic_snapshot_legacy_adapter.cpp",
    ):
        hits = commands_for(suffix)
        require(len(hits) == 1, f"expected one CMake compile command for {suffix}, found {len(hits)}")
        require("-std=c++11" in hits[0], f"{suffix} is not compiled as C++11: {hits[0]}")
        require("-std=gnu++11" not in hits[0], f"{suffix} unexpectedly enables GNU C++11 extensions")


def main() -> int:
    root = repo_root()
    audit_source_contract(root)
    version = gcc_version(root)
    abi = libstdcxx_abi(root)

    build = root / BUILD_REL
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True)

    direct_language_checks(root, build)
    configure_and_audit_commands(root, build)

    print("M1 C++26 language boundary focused lane: PASS")
    print(f"  GCC reference compiler: {version}")
    print(f"  libstdc++ dual ABI setting: _GLIBCXX_USE_CXX11_ABI={abi}")
    print("  shared headers strict C++11: PASS")
    print("  shared headers strict C++26: PASS")
    print("  tactical publication strict C++26 -Werror: PASS")
    print("  strategic publication strict C++26 -Werror: PASS")
    print("  C++11 producer -> C++26 consumer ABI fixture: PASS")
    print("  CMake publication ownership: C++26")
    print("  production ufo legacy adapter ownership: C++11")
    print("  ufotestall language mode: dependency-driven; not used as boundary evidence")
    print("  sealed src/tests/CMakeLists.txt: unchanged")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1 C++26 language boundary focused lane: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

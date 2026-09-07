#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

BASELINE_REVISION = "ccdf66f0da7723f0689ab253ac1a127982669d52"
SEALED_TEST_CMAKE_BLOB = "5110f532e62126a7b89fc07b1248717e5e71cbf0"
BUILD_REL = Path(".build/m1-tactical-publication")
TEST_CMAKE_REL = Path("src/tests/CMakeLists.txt")
FIXTURE_REL = Path("tools/remaster/m1-tactical-publication-integration.cpp")


class GateError(RuntimeError):
    pass


def run(args: list[str], *, cwd: Path, capture: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        check=False,
    )
    if proc.returncode != 0:
        raise GateError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stdout or ''}")
    return proc


def run_streaming(args: list[str], *, cwd: Path) -> str:
    print("+ " + " ".join(args), flush=True)
    proc = subprocess.Popen(
        args,
        cwd=cwd,
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


def strip_cpp_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return text


def require_baseline(root: Path) -> None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_REVISION, "HEAD"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        head = run(["git", "rev-parse", "HEAD"], cwd=root).stdout.strip()
        raise GateError(f"HEAD {head} is not a descendant of M1.2 baseline {BASELINE_REVISION}")


def require_sealed_test_cmake(root: Path) -> None:
    blob = run(["git", "hash-object", str(root / TEST_CMAKE_REL)], cwd=root).stdout.strip()
    if blob != SEALED_TEST_CMAKE_BLOB:
        raise GateError(
            f"sealed {TEST_CMAKE_REL} changed: expected {SEALED_TEST_CMAKE_BLOB}, got {blob}"
        )


def audit_source_contract(root: Path) -> None:
    require_baseline(root)
    require_sealed_test_cmake(root)

    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    for token in (
        "option(UFOAI_M1_TACTICAL_PUBLICATION_TESTS",
        "tools/remaster/m1-tactical-publication-integration.cpp",
        "src/client/presentation/tactical_snapshot_legacy_adapter.cpp",
        "src/client/presentation/tactical_publication.cpp",
    ):
        if token not in cmake:
            raise GateError(f"missing tactical-publication CMake token: {token}")

    client_cmake = (root / "src/client/CMakeLists.txt").read_text(encoding="utf-8")
    for token in (
        "presentation/tactical_snapshot_legacy_adapter.cpp",
        "presentation/tactical_publication.cpp",
    ):
        if token not in client_cmake:
            raise GateError(f"production client does not compile tactical publication source: {token}")

    public_headers = [
        root / "src/client/presentation/canonical_identity.h",
        root / "src/client/presentation/tactical_snapshot.h",
        root / "src/client/presentation/tactical_presentation_event.h",
        root / "src/client/presentation/tactical_publication.h",
    ]
    forbidden_public_tokens = (
        "le_t", "le_s", "model_t", "uiNode_t", "JPH::", "VkDevice", "ALuint",
        "SDL_GLContext", "Inventory", "ptl_t", "entity_type_t",
    )
    for path in public_headers:
        text = strip_cpp_comments(path.read_text(encoding="utf-8"))
        for token in forbidden_public_tokens:
            if token in text:
                raise GateError(f"legacy/runtime type leaked into public presentation contract {path}: {token}")

    snapshot_header = (root / "src/client/presentation/tactical_snapshot.h").read_text(encoding="utf-8")
    if "uint16_t stateFlags;" not in snapshot_header:
        raise GateError("tactical state flags must preserve the canonical 16-bit protocol domain")

    adapter = (root / "src/client/presentation/tactical_snapshot_legacy_adapter.cpp").read_text(encoding="utf-8")
    if '#include "../client.h"' not in adapter:
        raise GateError("legacy adapter must enter the legacy client through client.h include context")
    for token in (
        "legacyActor.entnum < 0 || legacyActor.entnum >= MAX_EDICTS",
        "legacyActor.pos", "legacyActor.oldPos", "legacyActor.TU", "legacyActor.maxTU",
        "legacyActor.HP", "legacyActor.maxHP", "legacyActor.STUN",
        "legacyActor.morale", "legacyActor.maxMorale", "legacyActor.state",
        "legacyActor.team", "legacyActor.pnum", "legacyActor.ucn", "legacyActor.fieldSize",
    ):
        if token not in adapter:
            raise GateError(f"legacy actor projection is missing required mapping/guard: {token}")

    publication = (root / "src/client/presentation/tactical_publication.cpp").read_text(encoding="utf-8")
    if "std::atomic_load_explicit(&latestPublication, std::memory_order_acquire)" not in publication:
        raise GateError("latest tactical publication must use an acquire read-side handoff")
    for token in (
        "publicationSequence.fetch_add(1, std::memory_order_relaxed) + 1;",
        "TacticalSnapshot snapshot = buildCurrentClientSnapshot(sequence);",
        "event.sequence = sequence;",
        "event.scheduledPresentationTime = scheduledPresentationTime;",
        "event.kind = TacticalPresentationEventKind::CanonicalMirrorUpdated;",
        "event.canonicalType = CanonicalEventTypeId(canonicalEventType);",
        "std::make_shared<const TacticalPublication>",
        "std::atomic_store_explicit(&latestPublication, publication, std::memory_order_release);",
    ):
        if token not in publication:
            raise GateError(f"publication ordering contract missing token: {token}")

    event_parser = (root / "src/client/battlescape/events/e_parse.cpp").read_text(encoding="utf-8")
    call = "ufo::presentation::legacy::publishAfterCanonicalEvent"
    if event_parser.count(call) != 2:
        raise GateError("expected publication after both scheduled and instant legacy event callbacks")
    scheduled_pattern = re.compile(
        r"eventData->eventCallback\(eventData, event->msg\);\s*"
        r"ufo::presentation::legacy::publishAfterCanonicalEvent\("
    )
    instant_pattern = re.compile(
        r"eventData->eventCallback\(eventData, msg\);\s*"
        r"ufo::presentation::legacy::publishAfterCanonicalEvent\("
    )
    if not scheduled_pattern.search(event_parser):
        raise GateError("scheduled publication is not ordered after canonical mirror mutation")
    if not instant_pattern.search(event_parser):
        raise GateError("instant publication is not ordered after canonical mirror mutation")

    fixture = root / FIXTURE_REL
    if not fixture.is_file():
        raise GateError(f"missing tactical publication fixture: {FIXTURE_REL}")
    fixture_text = fixture.read_text(encoding="utf-8")
    for test_name in (
        "ProjectsOnlyCanonicalActorValues",
        "PublishesOrderedSnapshotAndEventAfterMirrorMutation",
        "PublicValueTypesStayPointerFreeAndCopyable",
    ):
        if f"TEST(M1TacticalPublicationTest, {test_name})" not in fixture_text:
            raise GateError(f"missing tactical publication integration test: {test_name}")


def ensure_link(path: Path, target: Path) -> None:
    if path.is_symlink():
        if path.resolve() == target.resolve():
            return
        path.unlink()
    elif path.exists():
        raise GateError(f"{path} exists and is not the expected source-tree symlink; remove {BUILD_REL} and retry")
    path.symlink_to(target, target_is_directory=True)


def configure_build_and_test(root: Path) -> None:
    build = root / BUILD_REL
    if build.exists():
        shutil.rmtree(build)
    build.mkdir(parents=True, exist_ok=True)
    ensure_link(build / "base", root / "base")
    ensure_link(build / "radiant", root / "radiant")

    configure = [
        "cmake", "-S", str(root), "-B", str(build), "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo",
        "-DCMAKE_C_COMPILER=gcc",
        "-DCMAKE_CXX_COMPILER=g++",
        "-DUFOAI_REMASTER=OFF",
        "-DUFOAI_M1_TACTICAL_PUBLICATION_TESTS=ON",
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
    run_streaming(configure, cwd=root)
    run_streaming(
        ["cmake", "--build", str(build), "--parallel", "8", "--target", "ufotestall"],
        cwd=root,
    )

    binary = build / "ufotestall"
    if not binary.is_file():
        raise GateError("dedicated M1.2 ufotestall artifact is missing")
    output = run_streaming(
        [
            str(binary),
            "--gtest_filter=M1TacticalPublicationTest.*",
            "--gtest_color=no",
            "--gtest_print_time=0",
        ],
        cwd=build,
    )
    if "[  PASSED  ] 3 tests." not in output:
        raise GateError("expected all three tactical publication integration tests to pass")


def main() -> int:
    root = repo_root()
    audit_source_contract(root)
    configure_build_and_test(root)
    print("M1.2 tactical publication lane: PASS")
    print("  source/ownership audit: PASS")
    print("  sealed src/tests/CMakeLists.txt: unchanged")
    print("  dedicated legacy configure: PASS")
    print("  tactical publication GoogleTests: 3/3")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1.2 tactical publication lane: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

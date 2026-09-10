#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

BASELINE_REVISION = "7bb19b74289b3ffec024835c335063fee7ba84d7"
SEALED_TEST_CMAKE_BLOB = "5110f532e62126a7b89fc07b1248717e5e71cbf0"
BUILD_REL = Path(".build/m1-employee-ucn")
FIXTURE_REL = Path("tools/remaster/m1-employee-ucn-integration.cpp")


class GateError(RuntimeError):
    pass


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise GateError(msg)


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


def body(text: str, signature: str) -> str:
    pos = text.find(signature)
    if pos < 0:
        raise GateError(f"missing function/body token: {signature}")
    start = text.find("{", pos)
    if start < 0:
        raise GateError(f"missing body opener: {signature}")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise GateError(f"unterminated body: {signature}")


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
        raise GateError(
            f"HEAD {head} is not a descendant of Employee/UCN baseline {BASELINE_REVISION}"
        )


def audit_source_contract(root: Path) -> None:
    require_baseline(root)

    test_cmake = root / "src/tests/CMakeLists.txt"
    blob = run(["git", "hash-object", str(test_cmake)], cwd=root).stdout.strip()
    require(
        blob == SEALED_TEST_CMAKE_BLOB,
        f"sealed src/tests/CMakeLists.txt changed: expected {SEALED_TEST_CMAKE_BLOB}, got {blob}",
    )

    cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
    for token in (
        "option(UFOAI_M1_EMPLOYEE_UCN_TESTS",
        "UFOAI_M1_EMPLOYEE_UCN_TESTS AND (DISABLE_TESTS OR DISABLE_GAME)",
        "tools/remaster/m1-employee-ucn-integration.cpp",
    ):
        require(token in cmake, f"missing Employee/UCN CMake ownership token: {token}")

    team_h = (root / "src/client/cl_team.h").read_text(encoding="utf-8")
    team_cpp = (root / "src/client/cl_team.cpp").read_text(encoding="utf-8")
    game_team = (root / "src/client/cgame/cl_game_team.cpp").read_text(encoding="utf-8")
    employee = (root / "src/client/cgame/campaign/cp_employee.cpp").read_text(encoding="utf-8")
    netpack = (root / "src/common/netpack.cpp").read_text(encoding="utf-8")
    byte_h = (root / "src/shared/byte.h").read_text(encoding="utf-8")
    common_h = (root / "src/common/common.h").read_text(encoding="utf-8")
    save_h = (root / "src/client/cgame/campaign/cp_save.h").read_text(encoding="utf-8")

    for token in (
        "bool CL_IsCharacterUCNWireRepresentable(int ucn);",
        "bool CL_ReconcileCharacterUCN(int ucn);",
    ):
        require(token in team_h, f"missing retained UCN helper declaration: {token}")

    representable = body(team_cpp, "bool CL_IsCharacterUCNWireRepresentable (")
    for token in ("ucn >= 0", "std::numeric_limits<std::int16_t>::max()"):
        require(token in representable, f"UCN wire-domain helper missing {token}")

    reconcile = body(team_cpp, "bool CL_ReconcileCharacterUCN (")
    for token in (
        "CL_IsCharacterUCNWireRepresentable(ucn)",
        "cls.nextUniqueCharacterNumber <= ucn",
        "cls.nextUniqueCharacterNumber = ucn + 1",
    ):
        require(token in reconcile, f"UCN reconciliation missing {token}")

    generate = body(team_cpp, "void CL_GenerateCharacter (")
    for token in (
        "CL_IsCharacterUCNWireRepresentable(cls.nextUniqueCharacterNumber)",
        "Com_Error(ERR_DROP",
        "chr->ucn = cls.nextUniqueCharacterNumber++;",
    ):
        require(token in generate, f"UCN generation guard missing {token}")
    require(
        generate.index("CL_IsCharacterUCNWireRepresentable(cls.nextUniqueCharacterNumber)")
        < generate.index("chr->ucn = cls.nextUniqueCharacterNumber++;"),
        "UCN exhaustion guard must precede allocation",
    )

    load_character = body(game_team, "bool GAME_LoadCharacter (")
    for token in (
        "chr->ucn = XML_GetInt(p, SAVE_CHARACTER_UCN, 0);",
        "CL_ReconcileCharacterUCN(chr->ucn)",
        "outside inherited signed-16-bit wire domain",
    ):
        require(token in load_character, f"character load UCN qualification missing {token}")
    require(
        load_character.rfind("CL_ReconcileCharacterUCN(chr->ucn)")
        > load_character.find("Com_GetCharacterModel(chr)"),
        "allocator reconciliation must happen only after the character otherwise validates",
    )

    team_load_info = body(game_team, "static bool GAME_LoadTeamInfo (")
    for token in (
        "if (!GAME_LoadCharacter(n, chr))",
        "LIST_Foreach(chrDisplayList, character_t, existing)",
        "existing->ucn == chr->ucn",
        "Duplicate character UCN",
        "return true;",
    ):
        require(token in team_load_info, f"team-file UCN uniqueness guard missing {token}")

    load_team = body(game_team, "static bool GAME_LoadTeam (")
    for token in (
        "if (!GAME_LoadTeamInfo(snode))",
        "GAME_ResetCharacters();",
        "return false;",
    ):
        require(token in load_team, f"failed team load cleanup missing {token}")

    employee_load = body(employee, "bool E_LoadXML (")
    for token in (
        "cgi->GAME_LoadCharacter(chrNode, &e.chr)",
        "E_GetEmployeeFromChrUCN(e.chr.ucn)",
        "Duplicate employee UCN",
    ):
        require(token in employee_load, f"campaign employee UCN uniqueness guard missing {token}")
    require(
        employee_load.index("E_GetEmployeeFromChrUCN(e.chr.ucn)")
        < employee_load.index("LIST_Add(&ccs.employees[emplType]"),
        "duplicate EmployeeId check must precede canonical list insertion",
    )

    require(
        "#define LittleShort(X) (short)SDL_SwapLE16(X)" in byte_h,
        "inherited short signedness anchor changed",
    )
    net_read = body(netpack, "int NET_ReadShort (")
    require(
        "unsigned short v;" in net_read and "return LittleShort(v);" in net_read,
        "inherited NET_ReadShort signed-short semantics changed",
    )
    net_write = body(netpack, "void NET_WriteShort (")
    require(
        "const unsigned short v = LittleShort(c);" in net_write,
        "inherited NET_WriteShort semantics changed",
    )

    protocol_match = re.search(
        r"^\s*#\s*define\s+PROTOCOL_VERSION\s+(\d+)\b",
        common_h,
        flags=re.MULTILINE,
    )
    require(
        protocol_match is not None and int(protocol_match.group(1)) == 18,
        "protocol version changed",
    )

    save_match = re.search(
        r"^\s*#\s*define\s+SAVE_FILE_VERSION\s+(\d+)\b",
        save_h,
        flags=re.MULTILINE,
    )
    require(
        save_match is not None and int(save_match.group(1)) == 4,
        "save version changed",
    )

    identity_rows = list(csv.DictReader(
        (root / "tools/remaster/m1-canonical-identity-registry.tsv").open(encoding="utf-8"),
        delimiter="\t",
    ))
    identity = {r["identity"]: r for r in identity_rows}
    require(
        identity["EmployeeId"]["mapping_status"] == "direct_reconciled_persisted_qualified",
        "EmployeeId canonical registry mapping is not qualified",
    )
    require(
        identity["EmployeeId"]["publication_status"] == "published",
        "EmployeeId must be published by the employee/team owner batch",
    )
    require(
        identity["EmployeeId"]["intent_status"] == "employee_team_owners_qualified",
        "employee/team mutation authority must be qualified",
    )

    lifetime_rows = list(csv.DictReader(
        (root / "tools/remaster/m1-canonical-identity-lifetime-registry.tsv").open(encoding="utf-8"),
        delimiter="\t",
    ))
    lifetime = {r["identity"]: r for r in lifetime_rows}
    require(
        lifetime["EmployeeId"]["second_pass_status"] == "qualified_persisted_wire_correlation",
        "EmployeeId lifetime registry is not qualified",
    )
    require(
        lifetime["CharacterUcn"]["second_pass_status"] == "explicit_correlation_qualified",
        "CharacterUcn correlation lifetime is not qualified",
    )

    fixture = root / FIXTURE_REL
    require(fixture.is_file(), f"missing Employee/UCN integration fixture: {FIXTURE_REL}")
    fixture_text = fixture.read_text(encoding="utf-8")
    for name in ("ReconcilesLoadedUcnMonotonically", "PreservesSigned16BitWireDomain"):
        require(
            f"TEST(M1EmployeeUcnTest, {name})" in fixture_text,
            f"missing Employee/UCN integration test: {name}",
        )


def ensure_link(path: Path, target: Path) -> None:
    if path.is_symlink():
        if path.resolve() == target.resolve():
            return
        path.unlink()
    elif path.exists():
        raise GateError(
            f"{path} exists and is not the expected source-tree symlink; remove {BUILD_REL} and retry"
        )
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
        "-DUFOAI_M1_EMPLOYEE_UCN_TESTS=ON",
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
    require(binary.is_file(), "dedicated Employee/UCN ufotestall artifact is missing")
    output = run_streaming(
        [
            str(binary),
            "--gtest_filter=M1EmployeeUcnTest.*",
            "--gtest_color=no",
            "--gtest_print_time=0",
        ],
        cwd=build,
    )
    require("[  PASSED  ] 2 tests." in output, "expected both Employee/UCN integration tests to pass")


def main() -> int:
    root = repo_root()
    audit_source_contract(root)
    configure_build_and_test(root)
    print("M1 EmployeeId / CharacterUcn qualification: PASS")
    print("  generation exhaustion guard: signed-16-bit compatible")
    print("  load allocator reconciliation: monotonic")
    print("  duplicate campaign/team UCN load rejection: locked")
    print("  inherited save version 4 / protocol version 18: unchanged")
    print("  EmployeeId direct UCN mapping: qualified; publication and employee/team owners qualified")
    print("  focused GoogleTests: 2/2")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"M1 EmployeeId / CharacterUcn qualification: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

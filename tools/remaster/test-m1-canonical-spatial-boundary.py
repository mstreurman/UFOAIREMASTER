#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


EXPECTED_BINDINGS = {
    "Trace": "SV_Trace",
    "LinkEdict": "SV_LinkEdict",
    "UnlinkEdict": "SV_UnlinkEdict",
    "TestLine": "SV_TestLine",
    "TestLineWithEnt": "SV_TestLineWithEnt",
    "GrenadeTarget": "Com_GrenadeTarget",
    "GridCalcPathing": "SV_GridCalcPathing",
    "GridFindPath": "SV_GridFindPath",
    "MoveStore": "Grid_MoveStore",
    "MoveLength": "Grid_MoveLength",
    "MoveNext": "Grid_MoveNext",
    "GetTUsForDirection": "Grid_GetTUsForDirection",
    "GridFall": "SV_GridFall",
    "GridPosToVec": "SV_GridPosToVec",
    "isOnMap": "SV_GridIsOnMap",
    "GridRecalcRouting": "SV_RecalcRouting",
    "CanActorStandHere": "SV_CanActorStandHere",
    "GridShouldUseAutostand": "Grid_ShouldUseAutostand",
    "GetVisibility": "SV_GetVisibility",
    "PointContents": "SV_PointContents",
    "SetInlineModelOrientation": "SV_SetInlineModelOrientation",
    "GetInlineModelAABB": "SV_GetInlineModelAABB",
    "LoadModelAABB": "SV_LoadModelAABB",
}

FORBIDDEN_PRESENTATION_TOKENS = (
    "OpenGL",
    "Vulkan",
    "Vk",
    "Jolt",
    "OpenAL",
    "renderer",
)


class BoundaryError(RuntimeError):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def function_body(text: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^)]*\)\s*\{{", text)
    if not match:
        raise BoundaryError(f"function not found: {name}")

    brace = text.find("{", match.start())
    depth = 0
    for index in range(brace, len(text)):
        ch = text[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:index]
    raise BoundaryError(f"unterminated function body: {name}")


def game_import_body(text: str) -> str:
    match = re.search(r"typedef\s+struct\s+game_import_s\s*\{", text)
    if not match:
        raise BoundaryError("game_import_t definition not found")
    end = text.find("} game_import_t;", match.end())
    if end < 0:
        raise BoundaryError("game_import_t definition is unterminated")
    return text[match.end():end]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BoundaryError(message)


def main() -> int:
    root = repo_root()
    game_h = (root / "src/game/game.h").read_text(encoding="utf-8")
    server_h = (root / "src/server/server.h").read_text(encoding="utf-8")
    sv_game = (root / "src/server/sv_game.cpp").read_text(encoding="utf-8")

    import_body = game_import_body(game_h)
    bind_body = function_body(sv_game, "SV_BindCanonicalSpatialServices")
    init_body = function_body(sv_game, "SV_InitGameProgs")

    declaration = re.search(
        r"\bvoid\s+SV_BindCanonicalSpatialServices\s*\(\s*game_import_t&\s+import\s*\)\s*;",
        server_h,
    )
    require(declaration is not None, "server.h does not declare the canonical spatial binder")

    for member, target in EXPECTED_BINDINGS.items():
        member_decl = re.search(rf"\bIMPORT\s*\*\s*{re.escape(member)}\s*\)", import_body)
        require(member_decl is not None, f"game_import_t no longer exposes expected spatial member {member}")

        binding = re.findall(
            rf"\bimport\.{re.escape(member)}\s*=\s*{re.escape(target)}\s*;",
            bind_body,
        )
        require(len(binding) == 1, f"expected exactly one binding: import.{member} = {target}")

        direct_init_binding = re.search(rf"\bimport\.{re.escape(member)}\s*=", init_body)
        require(direct_init_binding is None, f"SV_InitGameProgs bypasses canonical binder for {member}")

    all_bindings = re.findall(r"\bimport\.([A-Za-z_][A-Za-z0-9_]*)\s*=", bind_body)
    require(
        set(all_bindings) == set(EXPECTED_BINDINGS),
        "canonical spatial binder contains missing or unexpected import assignments: "
        f"expected={sorted(EXPECTED_BINDINGS)} actual={sorted(set(all_bindings))}",
    )
    require(
        len(all_bindings) == len(EXPECTED_BINDINGS),
        "canonical spatial binder contains duplicate import assignments",
    )

    binder_calls = re.findall(r"\bSV_BindCanonicalSpatialServices\s*\(\s*import\s*\)\s*;", init_body)
    require(len(binder_calls) == 1, "SV_InitGameProgs must invoke the canonical spatial binder exactly once")

    for token in FORBIDDEN_PRESENTATION_TOKENS:
        require(token not in bind_body, f"presentation token leaked into canonical spatial binder: {token}")

    print("M1 canonical spatial boundary: PASS")
    print(f"  services: {len(EXPECTED_BINDINGS)}")
    print("  game_import_t ABI: unchanged (struct declaration is only inspected, not modified by this slice)")
    print("  SV_InitGameProgs: routes all audited spatial bindings through one canonical seam")
    print("  presentation dependencies in binder: none")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BoundaryError as exc:
        print(f"M1 canonical spatial boundary: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)

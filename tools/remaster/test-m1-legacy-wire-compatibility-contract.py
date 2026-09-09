#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BASELINE_REVISION = "cefabf0ef5686b76921f10418dcb19a02152ade3"


class GateError(RuntimeError):
    pass


def repo_root() -> Path:
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
    )
    if proc.returncode != 0:
        raise GateError("not inside a Git work tree")
    return Path(proc.stdout.strip()).resolve()


def require_baseline(root: Path) -> None:
    proc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE_REVISION, "HEAD"],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
    )
    if proc.returncode != 0:
        raise GateError(f"HEAD is not a descendant of compatibility baseline {BASELINE_REVISION}")


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    return text


def enum_body(text: str, enum_name: str) -> str:
    clean = strip_comments(text)
    m = re.search(r"enum\s+" + re.escape(enum_name) + r"\s*\{(.*?)\}\s*;", clean, re.S)
    if not m:
        # event_t/player_action_t are anonymous typedef enums.
        if enum_name == "event_t":
            marker0, marker1 = "EV_NULL", "EV_NUM_EVENTS"
        elif enum_name == "player_action_t":
            marker0, marker1 = "PA_NULL", "PA_NUM_EVENTS"
        else:
            raise GateError(f"enum {enum_name} not found")
        for m2 in re.finditer(r"typedef\s+enum\s*\{(.*?)\}\s*(\w+)\s*;", clean, re.S):
            if m2.group(2) == enum_name and marker0 in m2.group(1) and marker1 in m2.group(1):
                return m2.group(1)
        raise GateError(f"typedef enum {enum_name} not found")
    return m.group(1)


def enum_entries(body: str) -> list[str]:
    entries = []
    for raw in body.split(","):
        item = re.sub(r"\s+", " ", raw).strip()
        if item:
            entries.append(item)
    return entries


def require_entries(actual: list[str], expected: list[str], label: str) -> None:
    if actual != expected:
        raise GateError(f"{label} changed\nexpected={expected}\nactual={actual}")


def main() -> int:
    root = repo_root()
    require_baseline(root)

    common = (root / "src/common/common.h").read_text(encoding="utf-8")
    q_shared_h = (root / "src/game/q_shared.h").read_text(encoding="utf-8")
    q_shared_cpp = (root / "src/game/q_shared.cpp").read_text(encoding="utf-8")
    adapter = (root / "src/client/presentation/tactical_intent_legacy_adapter.cpp").read_text(encoding="utf-8")

    if not re.search(r"#define\s+PROTOCOL_VERSION\s+18\b", common):
        raise GateError("PROTOCOL_VERSION is no longer 18")

    require_entries(
        enum_entries(enum_body(common, "svc_ops_e")),
        [
            "svc_bad", "svc_nop", "svc_ping", "svc_disconnect", "svc_reconnect",
            "svc_print", "svc_stufftext", "svc_serverdata", "svc_configstring",
            "svc_event", "svc_oob = 0xff"
        ],
        "svc_ops_e wire opcode order",
    )
    require_entries(
        enum_entries(enum_body(common, "clc_ops_e")),
        [
            "clc_bad", "clc_nop", "clc_ack", "clc_endround", "clc_teaminfo",
            "clc_initactorstates", "clc_action", "clc_userinfo", "clc_stringcmd",
            "clc_oob = svc_oob"
        ],
        "clc_ops_e wire opcode order",
    )

    expected_events = [
        "EV_NULL", "EV_RESET", "EV_START", "EV_ENDROUND", "EV_ENDROUNDANNOUNCE",
        "EV_RESULTS", "EV_CENTERVIEW", "EV_MOVECAMERA", "EV_ENT_APPEAR",
        "EV_ENT_PERISH", "EV_ENT_DESTROY", "EV_ADD_BRUSH_MODEL", "EV_ADD_EDICT",
        "EV_ACTOR_APPEAR", "EV_ACTOR_ADD", "EV_ACTOR_TURN", "EV_ACTOR_MOVE",
        "EV_ACTOR_REACTIONFIRECHANGE", "EV_ACTOR_REACTIONFIREADDTARGET",
        "EV_ACTOR_REACTIONFIREREMOVETARGET", "EV_ACTOR_REACTIONFIRETARGETUPDATE",
        "EV_ACTOR_REACTIONFIREABORTSHOT", "EV_ACTOR_START_SHOOT", "EV_ACTOR_SHOOT",
        "EV_ACTOR_SHOOT_HIDDEN", "EV_ACTOR_THROW", "EV_ACTOR_END_SHOOT",
        "EV_ACTOR_DIE", "EV_ACTOR_REVITALISED", "EV_ACTOR_STATS",
        "EV_ACTOR_STATECHANGE", "EV_ACTOR_RESERVATIONCHANGE", "EV_ACTOR_WOUND",
        "EV_INV_ADD", "EV_INV_DEL", "EV_INV_AMMO", "EV_INV_RELOAD",
        "EV_INV_TRANSFER", "EV_MODEL_EXPLODE", "EV_MODEL_EXPLODE_TRIGGERED",
        "EV_PARTICLE_APPEAR", "EV_PARTICLE_SPAWN", "EV_SOUND", "EV_DOOR_OPEN",
        "EV_DOOR_CLOSE", "EV_CLIENT_ACTION", "EV_RESET_CLIENT_ACTION",
        "EV_CAMERA_APPEAR", "EV_NUM_EVENTS"
    ]
    require_entries(enum_entries(enum_body(q_shared_h, "event_t")), expected_events, "event_t wire opcode order")

    expected_pa = [
        "PA_NULL", "PA_TURN", "PA_MOVE", "PA_STATE", "PA_SHOOT",
        "PA_USE", "PA_INVMOVE", "PA_REACT_SELECT", "PA_RESERVE_STATE",
        "PA_NUM_EVENTS"
    ]
    require_entries(enum_entries(enum_body(q_shared_h, "player_action_t")), expected_pa, "player_action_t wire opcode order")

    clean_cpp = strip_comments(q_shared_cpp)
    m = re.search(r"const\s+char\s*\*\s*pa_format\s*\[\s*\]\s*=\s*\{(.*?)\}\s*;", clean_cpp, re.S)
    if not m:
        raise GateError("pa_format[] not found")
    formats = re.findall(r'"([^"]*)"', m.group(1))
    expected_formats = ["", "s", "g", "s", "gbbl", "s", "bbbbbb", "sss", "ss"]
    if formats != expected_formats:
        raise GateError(f"pa_format wire layout changed: expected {expected_formats}, got {formats}")

    for shared in (common, q_shared_h, q_shared_cpp):
        for forbidden in ("UFOAI_REMASTER", "REMASTER_PROTOCOL", "svc_remaster", "clc_remaster", "PA_REMASTER"):
            if forbidden in shared:
                raise GateError(f"remaster-specific protocol fork detected in shared wire owner: {forbidden}")

    required_lowerings = (
        "MSG_Write_PA(PA_STATE",
        "MSG_Write_PA(PA_RESERVE_STATE",
        "MSG_Write_PA(PA_MOVE",
        "MSG_Write_PA(PA_TURN",
        "MSG_Write_PA(PA_SHOOT",
        "MSG_Write_PA(PA_USE",
        "MSG_Write_PA(PA_INVMOVE",
        "MSG_Write_PA(PA_REACT_SELECT",
        "NET_WriteByte(&msg,clc_endround)",
        "TacticalIntentKind::Reload",
        "TacticalIntentKind::AbortMission",
    )
    for token in required_lowerings:
        if token not in adapter:
            raise GateError(f"typed tactical intent no longer lowers through inherited wire path: missing {token}")

    for forbidden in (
        "clc_remaster", "svc_remaster", "PA_REMASTER", "PROTOCOL_REMASTER",
        "NET_WriteByte(&msg,clc_stringcmd)"
    ):
        if forbidden in adapter:
            raise GateError(f"remaster-only/command fallback wire path detected: {forbidden}")

    print("PASS legacy tactical wire compatibility contract")
    print("  PROTOCOL_VERSION: 18")
    print("  svc/clc opcode order: locked")
    print("  EV_* opcode order: locked")
    print("  PA_* + pa_format layout: locked")
    print("  remaster typed-intent lowering uses inherited protocol: PASS")
    print("  remaster-only gameplay protocol fork audit: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GateError as exc:
        print(f"FAIL legacy tactical wire compatibility contract: {exc}", file=sys.stderr)
        raise SystemExit(1)

"""Built-in Clutch tools (virtual MCP server, no subprocess)."""

from __future__ import annotations

from typing import Any

CLUTCH_TOOLS_SERVER_ID = "clutch-tools"


def resolve_clutch_tools_server() -> dict[str, Any] | None:
    from src.workspace import get_workspace

    if not get_workspace():
        return None
    return {
        "id": CLUTCH_TOOLS_SERVER_ID,
        "name": "Clutch Builtin Tools",
        "type": "builtin",
        "transport": "virtual",
        "enabled": True,
        "builtin": True,
        "virtual": True,
    }


def is_virtual_server(server: dict[str, Any]) -> bool:
    return bool(server.get("virtual")) or server.get("transport") == "virtual"


def list_builtin_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": "apply_patch",
            "description": (
                "Apply a Codex-style patch to the active workspace. "
                "Supports *** Add File, *** Delete File, *** Update File, and *** Move to. "
                "Patch must start with '*** Begin Patch' and end with '*** End Patch'. "
                "For deletion (including dotfiles like `.deleted_test.txt`), use "
                "`*** Delete File: .deleted_test.txt` — never use local-fs move_file."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "patch": {
                        "type": "string",
                        "description": "Full patch body including Begin/End markers.",
                    }
                },
                "required": ["patch"],
            },
        }
    ]


def execute_builtin_tool(tool_name: str, arguments: dict[str, Any]) -> str:
    if tool_name == "apply_patch":
        from src.apply_patch import ApplyPatchError, apply_patch_in_workspace, format_apply_patch_result

        patch = str(arguments.get("patch", "")).strip()
        if not patch:
            return "Error executing tool: apply_patch requires non-empty `patch`"
        try:
            return format_apply_patch_result(apply_patch_in_workspace(patch))
        except ApplyPatchError as exc:
            return f"Error executing tool: {exc}"
        except Exception as exc:
            return f"Error executing tool: {exc}"
    return f"Error executing tool: unknown builtin tool {tool_name}"

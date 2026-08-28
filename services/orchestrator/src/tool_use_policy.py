"""Harness policy: when the model must call tools (Grok Build–style loop discipline).

Clutch adapts Grok Build behavior in Python (D44):
1. Do not accept a prose refusal when advertised tools cover the turn.
2. Cap open-web thrash: typically 1× web_search + ≤2× web_fetch, then answer
   (mainstream agents do not burn a 24-step loop on Bing SERPs).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.deliverable_intent import (
    html_deliverable_wrapup_nudge,
    is_html_deliverable_path,
    wants_browser_preview as user_turn_requests_html_preview,
)

# Soft = inject "stop and answer"; hard = refuse further network tools this turn.
NETWORK_SOFT_BUDGET = 3
NETWORK_HARD_BUDGET = 5

# Same-tool thrash (Cursor/Claude-style): soft nudge then hard-block further calls
# to that tool name this turn. Tighter than network — retrying the identical failing
# tool is almost never useful (esp. generate_image / apply_patch).
SAME_TOOL_SOFT_BUDGET = 2
SAME_TOOL_HARD_BUDGET = 3

# --- Intent heuristics (user turn) ---

_NETWORK_RE = re.compile(
    r"("
    r"天气|氣溫|气温|预报|預報|weather|forecast|temperature|"
    r"今天|今日|实时|即時|最近|近期|最新|news|股价|股價|汇率|匯率|"
    r"活动|活動|events?|演出|门票|門票|"
    r"查一下|搜一下|搜索|搜尋|search\s+(for|the)|look\s+up|"
    r"https?://|www\."
    r")",
    re.IGNORECASE,
)

_WORKSPACE_READ_RE = re.compile(
    r"("
    r"读一下|读下|看看|打开|打开看|列出|列表|有哪些文件|项目结构|目录|"
    r"read\s+(the\s+)?file|open\s+|list\s+(the\s+)?(dir|directory|files)|"
    r"what('s|\s+is)\s+in|show\s+me\s+(the\s+)?(file|code|folder)|"
    r"grep|搜索代码|在代码里找|find\s+in\s+(the\s+)?(code|repo|project)|"
    r"\b(README|CLAUDE\.md|package\.json|pyproject\.toml)\b|"
    r"这个文件|那份文件|源码|代码里"
    r")",
    re.IGNORECASE,
)

_WORKSPACE_WRITE_RE = re.compile(
    r"("
    r"改一下|修改|编辑|重写|写到|写入|创建文件|新建文件|删掉|删除文件|优化|"
    r"fix|edit|change|update|refactor|implement|add\s+(a\s+)?|"
    r"create\s+(a\s+)?file|delete\s+(the\s+)?file|apply\s+patch|"
    r"search_replace|把.+改成|替换成"
    r")",
    re.IGNORECASE,
)

# User approved a plan / told the agent to execute — must todo_write then write.
_PLAN_APPROVAL_RE = re.compile(
    r"("
    r"^确认$|^批准$|^好$|^行$|^可以$|^开始$|"
    r"批准[，,\s]|确认[，,\s]|同意(计划|执行|优化)|"
    r"按(照)?你说的|按照(你的|该)?计划|按计划|"
    r"开始执行|执行吧|去做吧|帮我优化|你自己的计划|"
    r"\b(approved|lgtm|go\s+ahead|ship\s+it|do\s+it|sounds?\s+good)\b"
    r")",
    re.IGNORECASE,
)

_TODO_TOOLS = frozenset({"todo_write", "write_todos", "update_todos"})

_GIT_RE = re.compile(
    r"("
    r"\bgit\b|提交|commit|diff|status|暂存|stage|分支|branch|"
    r"看一下改动|有什么改动|未提交"
    r")",
    re.IGNORECASE,
)

_SHELL_RE = re.compile(
    r"("
    r"跑一下|执行命令|终端|shell|运行测试|跑测试|npm\s|pnpm\s|uv\s|pytest|"
    r"run\s+(the\s+)?(tests?|command|script)|execute\s+"
    r")",
    re.IGNORECASE,
)

# Prose that claims tools / workspace / network are unavailable.
_REFUSAL_RE = re.compile(
    r"("
    r"cannot\s+directly\s+obtain|can'?t\s+access\s+(the\s+)?(internet|web|real[- ]?time|files?|workspace|disk)|"
    r"don'?t\s+have\s+access\s+to\s+(your\s+)?(files?|workspace|code|internet|web)|"
    r"无法直接|不能直接|没法获取|沒有实时|没有实时|无法获取实时|"
    r"无法访问(你的)?(文件|工作区|代码|网络)|不能访问(你的)?(文件|工作区)|"
    r"i\s+don'?t\s+have\s+access\s+to\s+(the\s+)?(internet|web|live)|"
    r"check\s+(your\s+)?(phone|weather\s+app)|"
    r"as\s+an\s+ai\s+(language\s+)?model\s+i\s+can'?t\s+(read|access|modify)\s+files"
    r")",
    re.IGNORECASE,
)

_NETWORK_TOOLS = frozenset({"web_search", "web_fetch", "internet_search", "search_web"})
_READ_TOOLS = frozenset({"read_file", "list_dir", "grep"})
_FILE_EXT = (
    "md|txt|json|py|ts|tsx|js|jsx|mjs|cjs|rs|go|toml|yml|yaml|html|htm|css|"
    "sh|env|lock|c|h|java|kt|swift|rb|php"
)
_FILENAME_GREP_RE = re.compile(rf"^[\w.-]+\.(?:{_FILE_EXT})$", re.IGNORECASE)
_FILE_EXISTS_RE = re.compile(
    r"("
    r"不要读文件内容|"
    r"有没有叫.{0,80}的文件|"
    r"找出工作区里有没有|"
    r"find (if )?(there'?s |there is )?(a )?file named|"
    r"is there (a )?file named|"
    r"does (a )?file named"
    r")",
    re.IGNORECASE,
)
_FILE_SCOPE_RE = re.compile(rf"\.({_FILE_EXT})$", re.IGNORECASE)
_WRITE_TOOLS = frozenset({"search_replace", "apply_patch", "run_terminal_cmd"})
_GIT_TOOLS = frozenset({"git_status", "git_diff", "git_commit"})
_SHELL_TOOLS = frozenset({"run_terminal_cmd"})

_COMMIT_ASK_RE = re.compile(
    r"("
    r"\bgit\s+commit\b|"
    r"\b(please\s+)?commit\b|"
    r"提交(代码|改动|变更|一下|吧)?|"
    r"做成提交|帮我提交"
    r")",
    re.IGNORECASE,
)
_COMMIT_FORBID_RE = re.compile(
    r"(不要提交|别提交|don'?t\s+commit|do\s+not\s+commit)",
    re.IGNORECASE,
)

_SHELL_GIT_COMMIT_RE = re.compile(r"\bgit\s+commit\b", re.IGNORECASE)

GIT_COMMIT_NOT_REQUESTED = (
    "Commit skipped: the user did not ask to commit. "
    "Leave changes uncommitted; do not call git_commit or run `git commit` in the shell "
    "unless they explicitly request a commit / 提交."
)


def user_asked_to_commit(text: str) -> bool:
    raw = text or ""
    if _COMMIT_FORBID_RE.search(raw):
        return False
    return bool(_COMMIT_ASK_RE.search(raw))


def command_includes_git_commit(command: str) -> bool:
    return bool(_SHELL_GIT_COMMIT_RE.search(command or ""))


def git_commit_not_requested_result() -> str:
    return GIT_COMMIT_NOT_REQUESTED


def short_tool_name(name: str) -> str:
    return (name or "").split("__")[-1].lower().replace("-", "_").strip()


def is_network_tool(name: str) -> bool:
    return short_tool_name(name) in _NETWORK_TOOLS


def looks_like_filename_grep(pattern: str) -> bool:
    """True when grep is being used to find a file by name, not search contents."""
    raw = (pattern or "").strip()
    if not raw:
        return False
    core = raw[1:] if raw.startswith("^") else raw
    if core.endswith("$"):
        core = core[:-1]
    unescaped = core.replace(r"\.", ".")
    if re.search(r"[\\^$*+?()[\]{}|]", unescaped):
        return False
    name = unescaped.replace("\\", "/").rsplit("/", 1)[-1]
    return bool(_FILENAME_GREP_RE.match(name))


def _scope_looks_like_file(path: str) -> bool:
    raw = (path or "").strip().replace("\\", "/").rstrip("/")
    if not raw or raw in {".", ".."}:
        return False
    return bool(_FILE_SCOPE_RE.search(raw.rsplit("/", 1)[-1]))


def apply_filename_grep_rewrite(
    func_name: str, func_args: dict | None
) -> tuple[str, dict]:
    """Rewrite filename-shaped grep calls to list_dir so Chat shows List, not Search."""
    args = dict(func_args or {})
    if short_tool_name(func_name) != "grep":
        return func_name, args
    if not looks_like_filename_grep(str(args.get("pattern") or "")):
        return func_name, args
    if _scope_looks_like_file(str(args.get("path") or "")):
        return func_name, args
    list_path = str(args.get("path") or ".").strip() or "."
    if "__" in func_name:
        prefix = func_name.split("__", 1)[0]
        return f"{prefix}__list_dir", {"path": list_path}
    return "list_dir", {"path": list_path}


def same_tool_soft_budget() -> int:
    import os

    raw = (os.environ.get("CLUTCH_SAME_TOOL_SOFT_FAILURES") or "").strip()
    if not raw:
        return SAME_TOOL_SOFT_BUDGET
    try:
        return max(1, int(raw))
    except ValueError:
        return SAME_TOOL_SOFT_BUDGET


def same_tool_hard_budget() -> int:
    import os

    raw = (os.environ.get("CLUTCH_SAME_TOOL_HARD_FAILURES") or "").strip()
    if not raw:
        return SAME_TOOL_HARD_BUDGET
    try:
        return max(same_tool_soft_budget(), int(raw))
    except ValueError:
        return SAME_TOOL_HARD_BUDGET


def network_budget_stop_nudge(
    *,
    used: int,
    soft: int = NETWORK_SOFT_BUDGET,
) -> str:
    return (
        f"[System reminder — stop searching] You already used {used} network tool "
        f"calls (soft budget {soft}: typically 1× web_search + ≤2× web_fetch). "
        "Do not call web_search or web_fetch again unless one critical fact is still "
        "missing. If the user asked for a file/HTML/page/implementation, continue with "
        "write tools (search_replace / apply_patch / todo_write) and finish the "
        "deliverable — do not end the turn with prose alone."
    )


def network_budget_exhausted_result(
    *,
    used: int,
    hard: int = NETWORK_HARD_BUDGET,
) -> str:
    return (
        f"Error: network tool budget exhausted ({used}/{hard} web_search/web_fetch). "
        "Answer NOW from prior tool results. Do not retry network tools this turn."
    )


def same_tool_stop_nudge(tool: str, *, used: int, soft: int | None = None) -> str:
    soft = SAME_TOOL_SOFT_BUDGET if soft is None else soft
    name = short_tool_name(tool) or "tool"
    if name in {"generate_image", "generate_video"}:
        return (
            f"[System reminder — stop retrying {name}] Already failed {used} times "
            f"(soft budget {soft}). Do NOT call `{name}` again this turn. "
            "Continue remaining work (HTML / files / todos). Tell the user media "
            "generation failed and how to fix it (Settings → Models key / network). "
            "Do NOT write an HTML page as a fake image/video."
        )
    return (
        f"[System reminder — stop retrying {name}] Already failed {used} times "
        f"(soft budget {soft}). Do NOT call `{name}` again with the same approach. "
        "Change strategy or finish with other tools."
    )


def same_tool_exhausted_result(tool: str, *, used: int, hard: int | None = None) -> str:
    hard = SAME_TOOL_HARD_BUDGET if hard is None else hard
    name = short_tool_name(tool) or "tool"
    if name in {"generate_image", "generate_video"}:
        return (
            f"Error: tool failure budget exhausted for `{name}` ({used}/{hard}). "
            "Do not retry media generation this turn. Continue with other deliverables "
            "(e.g. HTML) and tell the user image/video generation failed."
        )
    return (
        f"Error: tool failure budget exhausted for `{name}` ({used}/{hard}). "
        "Do not call this tool again this turn; change strategy or finish without it."
    )


@dataclass(frozen=True)
class ToolExpect:
    kind: str
    nudge: str


def _nudge(kind: str, body: str) -> ToolExpect:
    return ToolExpect(
        kind=kind,
        nudge=(
            f"[System reminder — tool use required] You answered without calling any tool, "
            f"but this turn needs {kind} tools. {body} "
            "Do not claim you lack access while these tools are available. "
            "Call the appropriate tool NOW, then answer from the tool result."
        ),
    )


_NUDGES = {
    "network": _nudge(
        "network",
        "Call `web_search` (if listed) or `web_fetch` on a concrete public URL "
        "(e.g. https://wttr.in/Shanghai?format=3 for weather).",
    ),
    "file_exists": _nudge(
        "file_exists",
        "Call `list_dir` on the workspace (usually path `.`). "
        "Do NOT grep a filename and do NOT read_file — existence is a directory listing.",
    ),
    "workspace_read": _nudge(
        "workspace_read",
        "Call `list_dir`, `read_file`, and/or `grep` on the workspace — do not invent file contents.",
    ),
    "workspace_write": _nudge(
        "workspace_write",
        "Call `search_replace` or `apply_patch` (and `read_file` first if needed) — "
        "do not claim edits succeeded without a tool result.",
    ),
    "plan_execute": _nudge(
        "plan_execute",
        "The user approved. Call `todo_write` with ≥3 concrete steps (exactly one "
        "`in_progress`), then execute with `apply_patch`/`search_replace`. "
        "Do NOT ask for confirmation again. Do NOT only restate a plan. "
        "Do NOT claim work is done without tool results.",
    ),
    "git": _nudge(
        "git",
        "Call `git_status` / `git_diff` as appropriate — do not invent git output. "
        "Call `git_commit` only if the user explicitly asked to commit / 提交.",
    ),
    "shell": _nudge(
        "shell",
        "Call `run_terminal_cmd` for the requested command/tests — do not invent command output.",
    ),
    "generic": _nudge(
        "available",
        "Use the listed clutch-tools (read_file, list_dir, grep, web_fetch, etc.) instead of refusing.",
    ),
}


def looks_like_plan_approval(text: str) -> bool:
    return bool(_PLAN_APPROVAL_RE.search((text or "").strip()))


def last_user_text(messages: list[dict]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                return content.strip()
            return str(content or "").strip()
    return ""


def prose_looks_like_tool_refusal(text: str) -> bool:
    return bool(_REFUSAL_RE.search(text or ""))


def classify_tool_expectation(
    user_text: str,
    *,
    available_tools: set[str],
) -> ToolExpect | None:
    """Return which tool family this turn needs, if any of those tools are available."""
    text = (user_text or "").strip()
    if not text or not available_tools:
        return None

    short_tools = {short_tool_name(t) for t in available_tools}
    if looks_like_plan_approval(text) and (
        short_tools & _TODO_TOOLS or short_tools & _WRITE_TOOLS
    ):
        return _NUDGES["plan_execute"]
    if _NETWORK_RE.search(text) and available_tools & _NETWORK_TOOLS:
        return _NUDGES["network"]
    if _GIT_RE.search(text) and available_tools & _GIT_TOOLS:
        return _NUDGES["git"]
    if _SHELL_RE.search(text) and available_tools & _SHELL_TOOLS:
        return _NUDGES["shell"]
    if _WORKSPACE_WRITE_RE.search(text) and available_tools & _WRITE_TOOLS:
        return _NUDGES["workspace_write"]
    if _FILE_EXISTS_RE.search(text) and "list_dir" in short_tools:
        return _NUDGES["file_exists"]
    if _WORKSPACE_READ_RE.search(text) and available_tools & _READ_TOOLS:
        return _NUDGES["workspace_read"]
    return None


def should_nudge_for_skipped_tools(
    *,
    user_text: str,
    assistant_text: str,
    available_tools: set[str],
    already_nudged: bool,
) -> ToolExpect | None:
    """If the model skipped tools it should have used, return the nudge to inject."""
    if already_nudged or not available_tools:
        return None

    expect = classify_tool_expectation(user_text, available_tools=available_tools)
    if expect is not None:
        return expect

    # Refusal prose with any tools available → generic nudge once.
    if prose_looks_like_tool_refusal(assistant_text):
        return _NUDGES["generic"]
    return None


# Back-compat aliases used by earlier tests / imports.
TOOL_SKIP_NUDGE = _NUDGES["network"].nudge


def turn_expects_network_tools(
    user_text: str,
    *,
    has_web_search: bool,
    has_web_fetch: bool,
) -> bool:
    tools: set[str] = set()
    if has_web_search:
        tools.add("web_search")
    if has_web_fetch:
        tools.add("web_fetch")
    expect = classify_tool_expectation(user_text, available_tools=tools)
    return expect is not None and expect.kind == "network"

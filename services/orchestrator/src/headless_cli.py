"""D36 — `python -m src.headless_cli` entry."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Clutch Agent headlessly (D36)")
    parser.add_argument("-p", "--prompt", required=True, help="User prompt for one Agent turn")
    parser.add_argument("--workspace", default="", help="Workspace root path")
    parser.add_argument("--agent-id", default="", help="Agent id (default builtin)")
    parser.add_argument("--json", action="store_true", help="Emit JSON result on stdout")
    args = parser.parse_args(argv)

    from src.headless_agent import run_headless_agent_sync

    result = run_headless_agent_sync(
        prompt=args.prompt,
        workspace_path=args.workspace,
        agent_id=args.agent_id,
    )
    if args.json:
        print(
            json.dumps(
                {
                    "exit_code": result.exit_code,
                    "output": result.output,
                    "run_id": result.run_id,
                },
                ensure_ascii=False,
            )
        )
    else:
        if result.output:
            print(result.output)
    return int(result.exit_code)


if __name__ == "__main__":
    raise SystemExit(main())

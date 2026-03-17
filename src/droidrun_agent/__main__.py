"""Entry point for ``python -m droidrun_agent``."""

from __future__ import annotations

import sys


def main() -> None:
    """CLI entry point for droidrun-agent."""
    if "--mcp" in sys.argv:
        from .mcp_server import main as mcp_main

        mcp_main()
    else:
        print("Usage: droidrun-agent --mcp")
        print("  Start the MCP server over stdio for AI agent integration.")
        sys.exit(1)


if __name__ == "__main__":
    main()

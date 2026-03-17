"""Entry point for ``python -m droidrun_agent``."""

from __future__ import annotations

import sys


def main() -> None:
    """CLI entry point for droidrun-agent."""
    if "--mcp" in sys.argv:
        try:
            from .mcp_server import main as mcp_main
        except ImportError:
            print(
                "Error: the 'mcp' package is not installed.\n"
                "Install it with:  pip install droidrun-agent[mcp]\n"
                "Or run via uvx:   uvx --with mcp droidrun-agent --mcp",
                file=sys.stderr,
            )
            sys.exit(1)
        mcp_main()
    else:
        print("Usage: droidrun-agent --mcp")
        print("  Start the MCP server over stdio for AI agent integration.")
        sys.exit(1)


if __name__ == "__main__":
    main()

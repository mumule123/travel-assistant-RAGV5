"""
Modular RAG MCP Server - Main Entry Point

This is the entry point for the MCP Server. It initializes the configuration,
sets up logging, and starts the server.
"""

import sys
from pathlib import Path

from src.core.settings import SettingsError, load_settings
from src.observability.logger import get_logger


def main() -> int:
    """
    Main entry point for the MCP Server.
    
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    # 修复：在 stdio 模式下，普通的 print(stdout) 会破坏 MCP 协议的 JSON 格式
    # 改为输出到 stderr
    print("Modular RAG MCP Server - Starting...", file=sys.stderr)

    settings_path = Path("config/settings.yaml")
    try:
        settings = load_settings(settings_path)
    except SettingsError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    # 初始化配置后，需要启动真正的 MCP Server，而不是直接 return 0
    # 由于我们在之前看到了 src/mcp_server/server.py 里面有真实的入口
    try:
        from src.mcp_server.server import run_stdio_server
        return run_stdio_server()
    except ImportError as e:
        logger = get_logger(log_level=settings.observability.log_level)
        logger.error(f"Failed to import MCP server: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

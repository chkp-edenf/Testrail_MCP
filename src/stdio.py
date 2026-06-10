#!/usr/bin/env python3
"""TestRail MCP Server - Entry Point

Main entry point for the TestRail MCP server.

Architecture:
- Client Layer: src/client/api/ - HTTP client and resource-specific API clients
- Server Layer: src/server/api/ - MCP tool registration and handlers
- Shared Layer: src/shared/schemas/ - Pydantic models for validation
"""

import asyncio
import logging
import os
import sys
from contextlib import suppress

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

# Import MCP SDK components
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.shared.exceptions import McpError
from mcp.types import TextContent, Tool

# Import client and modular tool registration
from src.client.api import ClientConfig, TestRailClient
from src.server.api.access_control import configure_access, enforce_access
from src.server.api.cache_preload import configure_preload, preload_caches
from src.server.api.rate_limiter import rate_limiter


def validate_environment() -> None:
    """Validate required environment variables exist"""
    required_vars = ["TESTRAIL_URL", "TESTRAIL_USERNAME", "TESTRAIL_API_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please set TESTRAIL_URL, TESTRAIL_USERNAME, and TESTRAIL_API_KEY"
        )


def normalize_base_url(url: str) -> str:
    """Normalize TestRail base URL to standard format
    
    Ensures URL ends with /index.php for proper API v2 access.
    """
    url = url.rstrip("/")
    if url.endswith("/index.php"):
        return url
    return f"{url}/index.php"


async def main():
    """Main entry point for TestRail MCP Server"""
    client = None
    
    try:
        # Validate environment
        validate_environment()
        logger.info("Environment variables validated")

        # Resolve access-control flags (logs mode to stderr).
        configure_access()
        configure_preload()
        
        # Normalize and configure API client
        raw_url = os.getenv("TESTRAIL_URL", "")
        base_url = normalize_base_url(raw_url)
        
        config = ClientConfig(
            base_url=base_url,
            username=os.getenv("TESTRAIL_USERNAME", ""),
            api_key=os.getenv("TESTRAIL_API_KEY", ""),
            timeout=30
        )
        
        # Initialize client with persistent HTTP connection and rate limiter
        client = TestRailClient(config, rate_limiter=rate_limiter)
        logger.info(f"TestRail client initialized for {base_url} with rate limiting (180 req/min)")

        # Optional metadata-cache warm-up. No-op when TESTRAIL_PRELOAD_CACHE
        # is off. Failures here log a warning and let the server start —
        # caches will populate lazily on first tool use. Bounded by a
        # 60s wall-clock so the server still boots if every TestRail
        # endpoint hangs (httpx per-request timeout is 30s; 4 sequential
        # fetchers worst-case approach 2 minutes).
        with suppress(asyncio.TimeoutError):
            await asyncio.wait_for(preload_caches(client), timeout=60)
        
        # Create MCP server
        server = Server("testrail-mcp")
        logger.info("MCP server created")
        
        # Import tool definitions and handler registry
        from .server.api import get_tool_handlers
        from .server.api.tools import get_all_tools
        
        # Register tool schemas
        @server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available TestRail MCP tools"""
            return get_all_tools()
        
        # Get handler routing map (replaces long if/elif chain)
        tool_handlers = get_tool_handlers()
        
        # Register single tool call handler with routing dispatcher
        @server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Route tool calls to appropriate handlers"""
            logger.info(f"Tool called: {name}")

            # Access-control gate. Raises McpError before any handler work.
            # Kept outside the try/except below so McpError propagates as a
            # JSON-RPC error response rather than being wrapped as TextContent.
            enforce_access(name)

            try:
                handler = tool_handlers.get(name)
                if handler:
                    return await handler(arguments, client)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except McpError:
                raise
            except Exception as e:
                logger.error(f"Error calling tool {name}: {str(e)}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
        
        logger.info("Tool handler registered")
        
        # Connect transport and run server
        logger.info("Starting TestRail MCP Server...")
        try:
            async with stdio_server() as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        finally:
            # Ensure HTTP client is properly closed
            if client:
                await client.close()
                logger.info("HTTP client closed gracefully")
            
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        if client:
            await client.close()
        sys.exit(1)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        if client:
            await client.close()
        sys.exit(1)


def run():
    """Synchronous entry point for uvx/console_scripts."""
    asyncio.run(main())


if __name__ == "__main__":
    run()

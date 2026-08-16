#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Memory API - MCP Server
Exposes memory_store, memory_recall, memory_delete, memory_audit as MCP tools.

Transport: stdio (default for Claude Code / MCP clients)
Base URL: MEMORY_API_BASE_URL env var (default: https://agent-memory-api-bix5.onrender.com)
Payment:  MCP_PAYMENT_TOKEN env var → X-PAYMENT header (omit when TEST_MODE=true on server)
"""

import os
import json
import logging
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.getenv("MEMORY_API_BASE_URL", "https://agent-memory-api-bix5.onrender.com").rstrip("/")
PAYMENT_TOKEN = os.getenv("MCP_PAYMENT_TOKEN", "")

# Mounted at /mcp by the parent FastAPI app. Keep the internal path at /
# so the public endpoint is /mcp rather than /mcp/mcp.
mcp = FastMCP("Agent Memory API", streamable_http_path="/")
_mcp_session_context = None
_mcp_transport_installed = False


def install_http_transport(parent_app, mount_path: str = "/mcp") -> None:
    """Mount MCP and attach its session manager lifecycle to FastAPI once."""
    global _mcp_transport_installed
    if _mcp_transport_installed:
        return

    parent_app.mount(mount_path, mcp.streamable_http_app())

    async def _start_mcp_session_manager():
        global _mcp_session_context
        if _mcp_session_context is None:
            _mcp_session_context = mcp.session_manager.run()
            await _mcp_session_context.__aenter__()
            logging.getLogger(__name__).info("MCP session manager started")

    async def _stop_mcp_session_manager():
        global _mcp_session_context
        if _mcp_session_context is not None:
            await _mcp_session_context.__aexit__(None, None, None)
            _mcp_session_context = None
            logging.getLogger(__name__).info("MCP session manager stopped")

    parent_app.add_event_handler("startup", _start_mcp_session_manager)
    parent_app.add_event_handler("shutdown", _stop_mcp_session_manager)
    _mcp_transport_installed = True


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if PAYMENT_TOKEN:
        h["X-PAYMENT"] = PAYMENT_TOKEN
    return h


async def _post(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{BASE_URL}{path}", json=payload, headers=_headers())
        if resp.status_code == 402:
            return {"error": "Payment Required", "detail": resp.json()}
        resp.raise_for_status()
        return resp.json()


async def _get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{BASE_URL}{path}", params=params, headers=_headers())
        if resp.status_code == 402:
            return {"error": "Payment Required", "detail": resp.json()}
        resp.raise_for_status()
        return resp.json()


@mcp.tool()
async def memory_store(
    agent_id: str,
    session_id: str,
    context: str,
    tags: Optional[list[str]] = None,
    ttl: Optional[int] = 86400,
) -> str:
    """Store encrypted agent memory (0.05 USDC)."""
    result = await _post("/api/memory/store", {
        "agent_id": agent_id,
        "session_id": session_id,
        "context": context,
        "tags": tags or [],
        "ttl": ttl,
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def memory_recall(
    agent_id: str,
    query: str,
    tags: Optional[list[str]] = None,
    limit: Optional[int] = 10,
) -> str:
    """Recall encrypted agent memory by query (0.03 USDC)."""
    result = await _post("/api/memory/recall", {
        "agent_id": agent_id,
        "query": query,
        "tags": tags or [],
        "limit": limit,
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def memory_delete(memory_id: str, agent_id: str, reason: str) -> str:
    """Delete memory and return its deletion proof (0.03 USDC)."""
    result = await _post("/api/memory/delete", {
        "memory_id": memory_id,
        "agent_id": agent_id,
        "reason": reason,
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def memory_audit(
    agent_id: Optional[str] = None,
    limit: Optional[int] = 100,
) -> str:
    """Get memory operation audit logs (0.05 USDC)."""
    params: dict = {"limit": limit}
    if agent_id:
        params["agent_id"] = agent_id
    result = await _get("/api/memory/audit", params=params)
    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    mcp.run()

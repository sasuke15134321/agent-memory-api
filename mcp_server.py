#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Memory API - MCP Server
Exposes memory_store, memory_recall, memory_delete, memory_audit as MCP tools.

Transport: stdio (default for Claude Code / MCP clients)
Base URL: MEMORY_API_BASE_URL env var (default: https://agent-memory-api-bix5.onrender.com)
Payment:  MCP_PAYMENT_TOKEN env var -> X-PAYMENT header (omit when TEST_MODE=true on server)
"""

import os
import json
import asyncio
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

BASE_URL = os.getenv("MEMORY_API_BASE_URL", "https://agent-memory-api-bix5.onrender.com").rstrip("/")
PAYMENT_TOKEN = os.getenv("MCP_PAYMENT_TOKEN", "")

PUBLIC_HOST = "agent-memory-api-bix5.onrender.com"
TRANSPORT_SECURITY = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=[PUBLIC_HOST, f"{PUBLIC_HOST}:*"],
    allowed_origins=[f"https://{PUBLIC_HOST}", f"https://{PUBLIC_HOST}:*"],
)


class _MountedMCPApp:
    """ASGI wrapper that owns Streamable HTTP session-manager lifetime when mounted.

    Starlette does not run lifespan handlers for mounted sub-applications. FastMCP's
    Streamable HTTP handler therefore needs its session_manager.run() context to be
    owned by a task in the parent process. This wrapper starts that context lazily on
    the first HTTP request and keeps it alive for the lifetime of the process.
    """

    def __init__(self, app, session_manager):
        self.app = app
        self.session_manager = session_manager
        self._start_lock = asyncio.Lock()
        self._ready = asyncio.Event()
        self._stop = asyncio.Event()
        self._runner_task = None

    async def _runner(self):
        async with self.session_manager.run():
            self._ready.set()
            await self._stop.wait()

    async def _ensure_started(self):
        if self._ready.is_set():
            return
        async with self._start_lock:
            if self._runner_task is None:
                self._runner_task = asyncio.create_task(self._runner())
        while not self._ready.is_set():
            if self._runner_task.done():
                await self._runner_task
            await asyncio.sleep(0)

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            await self._ensure_started()
        await self.app(scope, receive, send)


class MountedFastMCP(FastMCP):
    """FastMCP variant safe for mounting inside an existing FastAPI app."""

    def streamable_http_app(self):
        app = super().streamable_http_app()
        return _MountedMCPApp(app, self.session_manager)


# Mounted at /mcp by the parent FastAPI app. Keep the internal path at /
# so the public endpoint is /mcp rather than /mcp/mcp. Keep DNS-rebinding
# protection enabled and explicitly allow only this service's Render hostname.
mcp = MountedFastMCP(
    "Agent Memory API",
    streamable_http_path="/",
    transport_security=TRANSPORT_SECURITY,
)
_mcp_transport_installed = False


def install_http_transport(parent_app, mount_path: str = "/mcp") -> None:
    """Mount MCP once. Session-manager lifetime is owned by _MountedMCPApp."""
    global _mcp_transport_installed
    if _mcp_transport_installed:
        return
    parent_app.mount(mount_path, mcp.streamable_http_app())
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

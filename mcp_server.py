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
import asyncio
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.getenv("MEMORY_API_BASE_URL", "https://agent-memory-api-bix5.onrender.com").rstrip("/")
PAYMENT_TOKEN = os.getenv("MCP_PAYMENT_TOKEN", "")

mcp = FastMCP("Agent Memory API")


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


# ── Tools ──────────────────────────────────────────────────────────────────────

@mcp.tool()
async def memory_store(
    agent_id: str,
    session_id: str,
    context: str,
    tags: Optional[list[str]] = None,
    ttl: Optional[int] = 86400,
) -> str:
    """
    AIエージェントの記憶を保存します (0.05 USDC)。

    Args:
        agent_id:   エージェントの識別子
        session_id: セッションの識別子
        context:    保存する記憶のテキスト
        tags:       検索用タグのリスト（省略可）
        ttl:        保存期間（秒、デフォルト86400=24時間）

    Returns:
        memory_id, stored_at, expires_at を含むJSON文字列
    """
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
    """
    保存された記憶をクエリで検索・想起します (0.03 USDC)。

    Args:
        agent_id: エージェントの識別子
        query:    検索クエリ
        tags:     絞り込みタグ（省略可）
        limit:    最大取得件数（デフォルト10）

    Returns:
        memories リストを含むJSON文字列
    """
    result = await _post("/api/memory/recall", {
        "agent_id": agent_id,
        "query": query,
        "tags": tags or [],
        "limit": limit,
    })
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
async def memory_delete(
    memory_id: str,
    agent_id: str,
    reason: str,
) -> str:
    """
    指定した記憶を完全削除し、SHA256削除証跡を返します (0.03 USDC)。

    Args:
        memory_id: 削除する記憶のID（memory_store で取得）
        agent_id:  エージェントの識別子
        reason:    削除理由（監査ログに記録）

    Returns:
        deleted, deletion_proof（SHA256ハッシュ）を含むJSON文字列
    """
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
    """
    保存・想起・削除の全操作監査ログを取得します (0.05 USDC)。

    Args:
        agent_id: エージェントIDでフィルタ（省略時は全エージェント）
        limit:    最大取得件数（デフォルト100）

    Returns:
        audit_logs リストとtotal_countを含むJSON文字列
    """
    params: dict = {"limit": limit}
    if agent_id:
        params["agent_id"] = agent_id
    result = await _get("/api/memory/audit", params=params)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()

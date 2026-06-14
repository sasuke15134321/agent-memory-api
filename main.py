#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Memory & Trust API
FastAPI server with x402 payment protocol for AI agent memory, trust, and context management
"""

import os
import uuid
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import base64
from datetime import datetime, timedelta
import asyncio
import traceback
from fastapi.openapi.utils import get_openapi
import hashlib

from payment_verifier import PaymentVerifier
from memory_engine import MemoryEngine
from trust_engine import TrustEngine
from context_engine import ContextEngine
from recall_engine import RecallEngine
from database import agent_db

# Environment variables
WALLET_ADDRESS = os.getenv("WALLET_ADDRESS", "0x")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

app = FastAPI(
    title="Agent Memory API",
    version="1.0.0",
    description=(
        "Pay-per-request encrypted memory APIs for autonomous AI agents using x402. "
        "Store, recall, and audit AI agent memory with AES-256 encryption. "
        "Built for USDC/Base payments and Japanese AI agent workflows."
    )
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["info"]["x-guidance"] = (
        "Agent Memory API provides x402-paid encrypted memory tools for autonomous AI agents. "
        "Use /api/memory/store to persist memory across sessions with AES-256 encryption. "
        "Use /api/memory/recall to retrieve stored memory. "
        "Use /api/trust/verify to detect hallucinations and verify content trustworthiness. "
        "Use /api/memory/audit for compliance audit logs. "
        "Useful for AI agent memory management, USDC/Base payments, and Japanese AI workflows."
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

def paid_operation(amount_usd: str) -> dict:
    return {
        "x-payment-info": {
            "price": {
                "mode": "fixed",
                "currency": "USD",
                "amount": amount_usd,
            },
            "protocols": [{"x402": {}}],
        }
    }

_PAID_ENDPOINTS = {
    ("POST", "/api/memory/store"):    "0.05",
    ("POST", "/api/memory/recall"):   "0.03",
    ("POST", "/api/trust/verify"):    "0.20",
    ("POST", "/api/context/package"): "0.10",
    ("POST", "/api/recall/compress"): "0.05",
    ("POST", "/api/recall/extract"):  "0.03",
    ("POST", "/api/memory/delete"):   "0.03",
    ("GET",  "/api/memory/audit"):    "0.05",
}

# CDP Bazaar indexing extension for /api/memory/store
_BAZAAR_EXTENSIONS = {
    "bazaar": {
        "info": {
            "input": {
                "type": "http",
                "method": "POST",
                "bodyType": "json",
                "body": {
                    "agent_id": "agent_001",
                    "memory_type": "session",
                    "content": "User approved budget check. Proceed with payment.",
                    "ttl_seconds": 86400
                }
            },
            "output": {
                "type": "json",
                "example": {
                    "stored": True,
                    "memory_id": "mem_abc123",
                    "audit_log_id": "audit_xyz456",
                    "next_recommended": "proceed_with_recall"
                }
            }
        },
        "schema": {
            "type": "object",
            "properties": {
                "stored": {"type": "boolean"},
                "memory_id": {"type": "string"},
                "audit_log_id": {"type": "string"},
                "next_recommended": {"type": "string"}
            }
        }
    }
}

@app.middleware("http")
async def x402_payment_middleware(request: Request, call_next):
    path = request.url.path
    price = _PAID_ENDPOINTS.get((request.method, path))
    if not TEST_MODE and price is not None:
        if not (request.headers.get("PAYMENT-SIGNATURE") or request.headers.get("X-PAYMENT")):
            max_amount = str(round(float(price) * 1_000_000))
            _pc = {
                "x402Version": 2,
                "error": "Payment required",
                "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": max_amount, "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": request.method, "mimeType": "application/json"}}],
            }
            if path == "/api/memory/store":
                _pc["resource"] = {
                    "url": "https://agent-memory-api-bix5.onrender.com/api/memory/store",
                    "method": "POST",
                    "description": "Store encrypted AI agent memory with audit-ready metadata",
                    "mimeType": "application/json"
                }
                _pc["extensions"] = _BAZAAR_EXTENSIONS
                _pc["stored"] = False
                _pc["memory_id"] = None
                _pc["audit_log_id"] = None
                _pc["next_recommended"] = "complete_x402_payment"
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})
    return await call_next(request)

# Initialize components
payment_verifier = PaymentVerifier()
memory_engine = MemoryEngine()
trust_engine = TrustEngine()
context_engine = ContextEngine()
recall_engine = RecallEngine()

# Startup event
@app.on_event("startup")
async def startup_event():
    try:
        await agent_db.initialize()
        print("[OK] Agent Memory & Trust API startup complete")
    except Exception as e:
        print(f"[WARN] Database initialization failed (continuing without DB): {e}")
        print("[OK] Agent Memory & Trust API started in DB-less mode")

# Search Result Trust Check models
class SearchResultSourceInput(BaseModel):
    name: Optional[str] = Field(default=None)
    source_type: Optional[str] = Field(default="unknown")
    origin: Optional[str] = Field(default="unknown")
    trust_level: Optional[str] = Field(default="unknown")

class SearchResultFreshnessInput(BaseModel):
    status: Optional[str] = Field(default="unknown")
    max_age_seconds: Optional[int] = Field(default=None)
    observed_at: Optional[str] = Field(default=None)

class SearchResultProvenanceInput(BaseModel):
    recorded_by: Optional[str] = Field(default=None)
    derived_from: Optional[List[str]] = Field(default=None)
    human_entered: Optional[bool] = Field(default=False)
    system_generated: Optional[bool] = Field(default=False)

class SearchResultContradictionInput(BaseModel):
    source: str
    source_type: str
    value: str
    timestamp: Optional[str] = Field(default=None)
    trust_level: Optional[str] = Field(default=None)

class SearchResultPolicyInput(BaseModel):
    deny_stale_results: Optional[bool] = Field(default=True)
    require_review_on_conflict: Optional[bool] = Field(default=True)
    allow_sensor_observations: Optional[bool] = Field(default=True)
    allow_human_entered_records: Optional[bool] = Field(default=True)
    require_provenance: Optional[bool] = Field(default=True)

class SearchResultTrustCheckRequest(BaseModel):
    agent_id: str
    user_id: Optional[str] = Field(default=None)
    session_id: Optional[str] = Field(default=None)
    result_id: Optional[str] = Field(default=None)
    result_type: Optional[str] = Field(default="unknown")
    source: Optional[SearchResultSourceInput] = Field(default=None)
    timestamp: Optional[str] = Field(default=None)
    modality: Optional[str] = Field(default=None)
    claimed_fact: Optional[str] = Field(default=None)
    intended_use: Optional[str] = Field(default="unknown")
    freshness: Optional[SearchResultFreshnessInput] = Field(default=None)
    provenance: Optional[SearchResultProvenanceInput] = Field(default=None)
    contradictions: Optional[List[SearchResultContradictionInput]] = Field(default=None)
    policy: Optional[SearchResultPolicyInput] = Field(default=None)

# Request models
class StoreMemoryRequest(BaseModel):
    agent_id: str
    session_id: str
    context: str
    tags: Optional[List[str]] = []
    ttl: Optional[int] = 86400  # Default 24 hours

class RecallMemoryRequest(BaseModel):
    agent_id: str
    query: str
    tags: Optional[List[str]] = []
    limit: Optional[int] = 10

class VerifyTrustRequest(BaseModel):
    content: str
    source_agent: str
    context: Optional[str] = ""

class PackageContextRequest(BaseModel):
    project_id: str
    include_memories: bool = True
    summary_level: str = "detailed"  # brief, detailed, comprehensive

class CompressContentRequest(BaseModel):
    content: str
    compression_level: str = "medium"  # high, medium, low
    focus: str = "all"  # decisions, constraints, summary, all
    next_agent_briefing: bool = False

class ExtractContentRequest(BaseModel):
    content: str
    extract_type: str = "all"  # decisions, facts, actions, all

class DeleteMemoryRequest(BaseModel):
    memory_id: str
    reason: str
    agent_id: str

# Response models
class NextRecommendation(BaseModel):
    api_name: str
    url: str
    reason: str
    expected_improvement: str
    price_usdc: float

class StoreMemoryResponse(BaseModel):
    memory_id: str
    stored_at: str
    expires_at: str
    next_recommended: NextRecommendation

class RecallMemoryResponse(BaseModel):
    memories: List[Dict[str, Any]]
    next_recommended: NextRecommendation

class VerifyTrustResponse(BaseModel):
    trust_score: int
    hallucination_risk: str
    verdict: str
    warnings: List[str]
    next_recommended: NextRecommendation

class PackageContextResponse(BaseModel):
    context_package: Dict[str, Any]
    next_recommended: NextRecommendation

class CompressContentResponse(BaseModel):
    compressed_summary: str
    key_decisions: List[str]
    constraints: List[str]
    unresolved_issues: List[str]
    next_agent_briefing: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    next_recommended: NextRecommendation

class ExtractContentResponse(BaseModel):
    extracted_items: List[str]
    confidence_scores: List[float]
    source_locations: List[str]
    next_recommended: NextRecommendation

# Memory Provenance Context Record Builder models
class MemoryRawSourceInput(BaseModel):
    source_id: Optional[str] = Field(default=None)
    source_type: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)

class MemoryFactInput(BaseModel):
    fact_id: Optional[str] = Field(default=None)
    statement: Optional[str] = Field(default=None)
    supported_by: Optional[List[str]] = Field(default=None)

class MemoryStateInput(BaseModel):
    status: Optional[str] = Field(default="unknown")
    use_rule: Optional[str] = Field(default="Do not use for payment or tool decisions until verified.")
    freshness_required: Optional[bool] = Field(default=True)
    last_checked: Optional[str] = Field(default=None)
    evidence: Optional[str] = Field(default="not_provided")

class MemoryRiskFlagsInput(BaseModel):
    stale_context_possible: Optional[bool] = Field(default=True)
    payment_decision_sensitive: Optional[bool] = Field(default=True)
    tool_permission_sensitive: Optional[bool] = Field(default=True)
    requires_source_of_truth: Optional[bool] = Field(default=True)

class MemoryContextUsageInput(BaseModel):
    used_for_payment_decision: Optional[bool] = Field(default=False)
    used_for_tool_permission: Optional[bool] = Field(default=False)
    used_for_spending_policy: Optional[bool] = Field(default=False)
    used_for_memory_scope_policy: Optional[bool] = Field(default=False)

class MemoryProvenanceRecordBuildRequest(BaseModel):
    agent_id: str
    context_id: Optional[str] = Field(default=None)
    context_type: Optional[str] = Field(default=None)
    memory_layer: Optional[str] = Field(default="unknown")
    summary: Optional[str] = Field(default=None)
    raw_sources: Optional[List[MemoryRawSourceInput]] = Field(default=None)
    facts: Optional[List[MemoryFactInput]] = Field(default=None)
    state: Optional[MemoryStateInput] = Field(default=None)
    risk_flags: Optional[MemoryRiskFlagsInput] = Field(default=None)
    context_usage: Optional[MemoryContextUsageInput] = Field(default=None)

# AI agent policy endpoint
@app.get("/.well-known/mcp/server-card.json", include_in_schema=False)
async def mcp_server_card():
    """Smithery MCP server card - allows Smithery to discover tools without MCP protocol scan"""
    return {
        "serverInfo": {
            "name": "agent-memory-api",
            "version": "1.0.0"
        },
        "tools": [
            {
                "name": "memory_store",
                "description": "Store memory with AES-256 encryption",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "agent_id": {"type": "string"},
                        "namespace": {"type": "string"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "memory_recall",
                "description": "Recall memories by semantic query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "agent_id": {"type": "string"},
                        "limit": {"type": "number"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "memory_delete",
                "description": "Delete memory with SHA256 audit proof",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "agent_id": {"type": "string"}
                    },
                    "required": ["memory_id"]
                }
            },
            {
                "name": "memory_audit",
                "description": "Get audit log of all memory operations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_id": {"type": "string"},
                        "limit": {"type": "number"}
                    },
                    "required": []
                }
            }
        ],
        "resources": [],
        "prompts": []
    }

@app.get("/.well-known/ai-agent-policy", include_in_schema=False)
async def ai_agent_policy():
    import json
    import os
    policy_path = "ai-agent-policy.json"
    if os.path.exists(policy_path):
        with open(policy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "Policy not found"}

@app.get("/ai-agent-policy.json", include_in_schema=False)
async def ai_agent_policy_json():
    from pathlib import Path
    import json
    policy_path = Path(__file__).parent / "ai-agent-policy.json"
    with open(policy_path) as f:
        return json.load(f)

# x402 payment protocol endpoint discovery
@app.get("/.well-known/x402.json", include_in_schema=False)
async def x402_discovery():
    """x402 protocol endpoint discovery for Agentic.Market"""
    return {
        "version": 1,
        "endpoints": [
            {
                "path": "/api/memory/store",
                "method": "POST",
                "price": "0.05",
                "currency": "USDC",
                "network": "base",
                "description": "AIエージェントの記憶を安全に保存・管理",
                "category": "infrastructure",
                "tags": ["ai", "memory", "agent", "storage"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "agent-memory-management"
                    }
                }
            },
            {
                "path": "/api/memory/recall",
                "method": "POST",
                "price": "0.03",
                "currency": "USDC",
                "network": "base",
                "description": "関連する記憶を関連度スコア付きで検索",
                "category": "infrastructure",
                "tags": ["ai", "memory", "recall", "search"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "memory-recall"
                    }
                }
            },
            {
                "path": "/api/trust/verify",
                "method": "POST",
                "price": "0.20",
                "currency": "USDC",
                "network": "base",
                "description": "AIエージェントのコンテンツ信頼性検証・幻覚検出",
                "category": "verification",
                "tags": ["ai", "trust", "verification", "hallucination"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "trust-verification"
                    }
                }
            },
            {
                "path": "/api/context/package",
                "method": "POST",
                "price": "0.10",
                "currency": "USDC",
                "network": "base",
                "description": "プロジェクト文脈の要約・引き継ぎパッケージ作成",
                "category": "infrastructure",
                "tags": ["ai", "context", "handover", "summary"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "context-packaging"
                    }
                }
            },
            {
                "path": "/api/recall/compress",
                "method": "POST",
                "price": "0.05",
                "currency": "USDC",
                "network": "base",
                "description": "会話ログ・作業履歴の圧縮・重要決定事項抽出",
                "category": "intelligence",
                "tags": ["ai", "compression", "recall", "memory", "handover"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "content-compression"
                    }
                }
            },
            {
                "path": "/api/recall/extract",
                "method": "POST",
                "price": "0.03",
                "currency": "USDC",
                "network": "base",
                "description": "テキストから重要情報・決定事項・事実の抽出",
                "category": "intelligence",
                "tags": ["ai", "extraction", "analysis", "information"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "information-extraction"
                    }
                }
            },
            {
                "path": "/api/memory/delete",
                "method": "POST",
                "price": "0.03",
                "currency": "USDC",
                "network": "base",
                "description": "記憶の完全削除と不変の削除証跡（SHA256）を生成",
                "category": "infrastructure",
                "tags": ["ai", "memory", "delete", "audit", "proof"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "memory-deletion-proof"
                    }
                }
            },
            {
                "path": "/api/memory/audit",
                "method": "GET",
                "price": "0.05",
                "currency": "USDC",
                "network": "base",
                "description": "全操作（保存・呼び出し・削除）の監査ログを返す",
                "category": "infrastructure",
                "tags": ["ai", "memory", "audit", "log", "compliance"],
                "extensions": {
                    "bazaar": {
                        "discoverable": True,
                        "language": ["ja", "en"],
                        "specialization": "memory-audit-log"
                    }
                }
            }
        ]
    }

@app.get("/.well-known/x402", include_in_schema=False)
async def x402_discovery_manifest():
    return {
        "version": 1,
        "name": "Agent Memory API",
        "title": "Agent Memory API",
        "description": (
            "Pay-per-request encrypted memory APIs for autonomous AI agents using x402. "
            "Store, recall, compress, and audit AI agent memory with AES-256 encryption."
        ),
        "tags": ["AI", "Memory", "Security"],
        "resources": [
            "https://agent-memory-api-bix5.onrender.com/api/memory/store",
            "https://agent-memory-api-bix5.onrender.com/api/memory/recall",
            "https://agent-memory-api-bix5.onrender.com/api/trust/verify",
            "https://agent-memory-api-bix5.onrender.com/api/context/package",
            "https://agent-memory-api-bix5.onrender.com/api/recall/compress",
            "https://agent-memory-api-bix5.onrender.com/api/recall/extract",
            "https://agent-memory-api-bix5.onrender.com/api/memory/delete",
            "https://agent-memory-api-bix5.onrender.com/api/memory/audit"
        ],
        "ownershipProofs": [
            "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"
        ],
        "instructions": (
            "Agent Memory API stores and recalls encrypted AI agent memory. "
            "Use /api/memory/store to persist memory, /api/memory/recall to retrieve it. "
            "Use /api/trust/verify to detect hallucinations."
        )
    }

@app.post(
    "/api/memory/store",
    response_model=StoreMemoryResponse,
    summary="Memory Store - Store AI agent memory with encryption",
    description="Stores AI agent memory with AES-256 encryption. Use to persist memory across sessions. Includes SHA256 deletion audit proof.",
    tags=["Memory"],
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.05"),
)
async def store_memory(request: StoreMemoryRequest, http_request: Request):
    """Store agent memory with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("PAYMENT-SIGNATURE") or http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "50000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "POST", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.05")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        result = await memory_engine.store_memory(
            agent_id=request.agent_id,
            session_id=request.session_id,
            context=request.context,
            tags=request.tags,
            ttl=request.ttl
        )

        # Add cross-sell recommendation
        result["next_recommended"] = {
            "api_name": "Agent Security API",
            "url": "https://agent-security-gateway.onrender.com",
            "reason": "保存された記憶データのセキュリティ強化と不正アクセス防止",
            "expected_improvement": "90%データ保護強化",
            "price_usdc": 0.05
        }

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory storage failed: {str(e)}")

@app.post(
    "/api/memory/recall",
    response_model=RecallMemoryResponse,
    summary="Memory Recall - Retrieve AI agent memory",
    description="Recalls stored AI agent memory by semantic query. Returns encrypted memory with audit trail.",
    tags=["Memory"],
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.03"),
)
async def recall_memory(request: RecallMemoryRequest, http_request: Request):
    """Recall related memories with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("PAYMENT-SIGNATURE") or http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "30000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "POST", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.03")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        memories = await memory_engine.recall_memories(
            agent_id=request.agent_id,
            query=request.query,
            tags=request.tags,
            limit=request.limit
        )

        return {
            "memories": memories,
            "next_recommended": {
                "api_name": "Agent Security API",
                "url": "https://agent-security-gateway.onrender.com",
                "reason": "想起された記憶の機密性検証とセキュリティリスク分析",
                "expected_improvement": "85%情報漏洩リスク削減",
                "price_usdc": 0.05
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory recall failed: {str(e)}")

@app.post(
    "/api/trust/verify",
    response_model=VerifyTrustResponse,
    summary="Trust Verify - Verify content trustworthiness",
    description="Verifies content trustworthiness and detects hallucinations. Returns trust score and verification metadata.",
    tags=["Security"],
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.20"),
)
async def verify_trust(request: VerifyTrustRequest, http_request: Request):
    """Verify content trust and detect hallucinations with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("PAYMENT-SIGNATURE") or http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "200000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "POST", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.20")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        result = await trust_engine.verify_trust(
            content=request.content,
            source_agent=request.source_agent,
            context=request.context
        )

        # Add cross-sell recommendation
        result["next_recommended"] = {
            "api_name": "Agent Security API",
            "url": "https://agent-security-gateway.onrender.com",
            "reason": "信頼性検証済みコンテンツの更なるセキュリティ脅威スキャン",
            "expected_improvement": "95%総合セキュリティ向上",
            "price_usdc": 0.05
        }

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trust verification failed: {str(e)}")

@app.post(
    "/api/context/package",
    response_model=PackageContextResponse,
    summary="Context Package - Package project context for handoff",
    description="Packages project context for AI agent handoff. Summarizes conversation history and key decisions.",
    tags=["Memory"],
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.10"),
)
async def package_context(request: PackageContextRequest, http_request: Request):
    """Create context handover package with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("PAYMENT-SIGNATURE") or http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "100000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "POST", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.10")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        context_package = await context_engine.create_package(
            project_id=request.project_id,
            include_memories=request.include_memories,
            summary_level=request.summary_level
        )

        return {
            "context_package": context_package,
            "next_recommended": {
                "api_name": "Agent Security API",
                "url": "https://agent-security-gateway.onrender.com",
                "reason": "文脈パッケージ内の機密情報スキャンとセキュリティ検証",
                "expected_improvement": "80%機密情報保護強化",
                "price_usdc": 0.05
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context packaging failed: {str(e)}")

@app.post(
    "/api/recall/compress",
    response_model=CompressContentResponse,
    summary="Memory Compress - Compress conversation logs",
    description="Compresses conversation logs and extracts key decisions. Reduces token usage while preserving important context.",
    tags=["Memory"],
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.05"),
)
async def compress_content(request: CompressContentRequest, http_request: Request):
    """Compress conversation logs and work history with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("PAYMENT-SIGNATURE") or http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "50000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "POST", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.05")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        result = await recall_engine.compress_content(
            content=request.content,
            compression_level=request.compression_level,
            focus=request.focus,
            next_agent_briefing=request.next_agent_briefing
        )

        # Add cross-sell recommendation
        result["next_recommended"] = {
            "api_name": "Agent Security API",
            "url": "https://agent-security-gateway.onrender.com",
            "reason": "圧縮されたコンテンツの機密情報残存チェックとセキュリティ検証",
            "expected_improvement": "75%データ漏洩リスク削減",
            "price_usdc": 0.05
        }

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Content compression failed: {str(e)}")

@app.post(
    "/api/recall/extract",
    response_model=ExtractContentResponse,
    summary="Memory Extract - Extract key information from text",
    description="Extracts key information and decisions from text. Returns structured summary for AI agent context management.",
    tags=["Memory"],
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.03"),
)
async def extract_content(request: ExtractContentRequest, http_request: Request):
    """Extract information from text with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("PAYMENT-SIGNATURE") or http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "30000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "POST", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.03")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        result = await recall_engine.extract_information(
            content=request.content,
            extract_type=request.extract_type
        )

        # Add cross-sell recommendation
        result["next_recommended"] = {
            "api_name": "Agent Security API",
            "url": "https://agent-security-gateway.onrender.com",
            "reason": "抽出情報のセンシティブデータ検出とセキュリティリスク分析",
            "expected_improvement": "85%機密情報保護向上",
            "price_usdc": 0.05
        }

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Information extraction failed: {str(e)}")

@app.post(
    "/api/memory/delete",
    summary="Memory Delete - Delete AI agent memory with audit proof",
    description="Deletes AI agent memory with SHA256 audit proof. Returns deletion certificate for compliance.",
    tags=["Memory"],
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.03"),
)
async def delete_memory(request: DeleteMemoryRequest, http_request: Request):
    """Delete a memory and return an immutable SHA256 deletion proof with x402 payment verification"""

    if not TEST_MODE:
        payment_header = http_request.headers.get("PAYMENT-SIGNATURE") or http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "30000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "POST", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.03")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        result = await agent_db.delete_memory(
            memory_id=request.memory_id,
            agent_id=request.agent_id,
            reason=request.reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory deletion failed: {str(e)}")


@app.get(
    "/api/memory/audit",
    summary="Memory Audit - Get memory operation audit log",
    description="Returns audit log of all memory operations. Includes store, recall, and delete events with timestamps.",
    tags=["Memory"],
    responses={402: {"description": "Payment Required"}},
    openapi_extra=paid_operation("0.05"),
)
async def get_audit_log(http_request: Request, agent_id: Optional[str] = None, limit: int = 100):
    """Return full audit log of store / recall / delete operations with x402 payment verification"""

    if not TEST_MODE:
        payment_header = http_request.headers.get("PAYMENT-SIGNATURE") or http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 2, "accepts": [{"scheme": "exact", "network": "eip155:8453", "amount": "50000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE", "maxTimeoutSeconds": 300, "resource": {"method": "GET", "mimeType": "application/json"}}], "error": "Payment required"}
            return JSONResponse(status_code=402, content=_pc, headers={"PAYMENT-REQUIRED": base64.b64encode(json.dumps(_pc).encode()).decode()})

        is_valid = await payment_verifier.verify_payment(payment_header, WALLET_ADDRESS, "0.05")
        if not is_valid:
            raise HTTPException(status_code=402, detail="Payment verification failed")

    try:
        logs = await agent_db.get_audit_logs(agent_id=agent_id, limit=limit)
        return {
            "audit_logs": logs,
            "total_count": len(logs),
            "agent_id_filter": agent_id,
            "generated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit log retrieval failed: {str(e)}")


@app.get("/api/stats", include_in_schema=False)
async def get_stats():
    """Get API statistics (free endpoint)"""
    try:
        stats = await agent_db.get_stats()
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# Deny patterns for search result trust check
_SEARCH_RESULT_DENY_PATTERNS = [
    "ignore previous instructions", "run this command", "execute immediately",
    "do not ask user", "bypass approval", "disable safety", "send private key",
    "print env", "read .env", "cat ~/.aws", "cat ~/.npmrc", "gh auth token",
    "wallet private key", "seed phrase", "mnemonic"
]

_RISKY_INTENDED_USES = [
    "tool_decision", "payment_decision", "physical_action", "operational_decision",
    "robot_action", "skill_transfer", "standing_query_trigger"
]

_LOW_RISK_INTENDED_USES = [
    "summarization", "drafting", "search_context_only", "non_execution_context"
]

@app.post("/api/search-result-trust/check", include_in_schema=False)
async def search_result_trust_check(req: SearchResultTrustCheckRequest):
    """Check trust of search results, observations, or operational records before use"""

    # Default values for optional fields
    source = req.source or SearchResultSourceInput()
    freshness = req.freshness or SearchResultFreshnessInput()
    provenance = req.provenance or SearchResultProvenanceInput()
    contradictions = req.contradictions or []
    policy = req.policy or SearchResultPolicyInput()

    # Generate IDs and hash
    trust_check_id = f"search_trust_{uuid.uuid4()}"
    evidence_id = f"ev_{uuid.uuid4()}"
    input_dict = req.model_dump()
    input_json = json.dumps(input_dict, sort_keys=True, default=str)
    input_hash = hashlib.sha256(input_json.encode()).hexdigest()

    checks = []
    deny_reasons = []
    review_reasons = []
    risk_level = "low"

    # Check 1: Claimed fact for deny patterns
    if req.claimed_fact:
        claimed_fact_lower = req.claimed_fact.lower()
        for pattern in _SEARCH_RESULT_DENY_PATTERNS:
            if pattern in claimed_fact_lower:
                deny_reasons.append(f"deny pattern in claimed_fact: {pattern}")
                checks.append({"name": "claimed_fact_check", "result": "deny", "reason": f"Dangerous pattern detected: '{pattern}'"})
                break

    if not deny_reasons:
        checks.append({"name": "claimed_fact_check", "result": "pass", "reason": "No dangerous patterns in claimed_fact"})

    # Check 2: Freshness
    freshness_status = freshness.status or "unknown"
    if freshness_status == "stale" and policy.deny_stale_results:
        deny_reasons.append("stale result with deny_stale_results=True")
        checks.append({"name": "freshness_check", "result": "deny", "reason": "Result is stale and policy denies stale results"})
    elif freshness_status in ["unknown", "undetermined"]:
        review_reasons.append("freshness status unknown")
        checks.append({"name": "freshness_check", "result": "review_required", "reason": "Freshness status is unknown"})
    else:
        checks.append({"name": "freshness_check", "result": "pass", "reason": f"Freshness status: {freshness_status}"})

    # Check 3: Provenance
    provenance_status = "missing"
    if provenance.recorded_by or provenance.derived_from:
        provenance_status = "complete"
    elif provenance.human_entered or provenance.system_generated:
        provenance_status = "partial"

    if provenance_status == "missing" and policy.require_provenance:
        deny_reasons.append("provenance missing with require_provenance=True")
        checks.append({"name": "provenance_check", "result": "deny", "reason": "Provenance is missing and required by policy"})
    elif provenance_status == "partial":
        review_reasons.append("provenance partially available")
        checks.append({"name": "provenance_check", "result": "review_required", "reason": "Provenance is partial"})
    else:
        checks.append({"name": "provenance_check", "result": "pass", "reason": f"Provenance status: {provenance_status}"})

    # Check 4: Source trust level
    source_trust_status = source.trust_level or "unknown"
    if source_trust_status in ["low", "untrusted"]:
        deny_reasons.append(f"source trust level: {source_trust_status}")
        checks.append({"name": "source_trust_check", "result": "deny", "reason": f"Source trust level is {source_trust_status}"})
    elif source_trust_status in ["medium", "unknown"]:
        review_reasons.append(f"source trust level: {source_trust_status}")
        checks.append({"name": "source_trust_check", "result": "review_required", "reason": f"Source trust level is {source_trust_status}"})
    else:
        checks.append({"name": "source_trust_check", "result": "pass", "reason": f"Source trust level: {source_trust_status}"})

    # Check 5: Result type
    result_type = req.result_type or "unknown"
    risky_types = ["untrusted_external_instruction", "robot_observation", "sensor_reading", "business_record", "sop", "operational_log", "unknown"]
    if result_type == "untrusted_external_instruction":
        deny_reasons.append(f"result_type: {result_type}")
        checks.append({"name": "result_type_check", "result": "deny", "reason": f"Result type is {result_type}"})
    elif result_type in risky_types:
        review_reasons.append(f"result_type: {result_type}")
        checks.append({"name": "result_type_check", "result": "review_required", "reason": f"Result type {result_type} requires review"})
    else:
        checks.append({"name": "result_type_check", "result": "pass", "reason": f"Result type: {result_type}"})

    # Check 6: Intended use
    intended_use_status = req.intended_use or "unknown"
    if intended_use_status in _RISKY_INTENDED_USES:
        review_reasons.append(f"intended_use: {intended_use_status}")
        checks.append({"name": "intended_use_check", "result": "review_required", "reason": f"Intended use '{intended_use_status}' requires review"})
    else:
        checks.append({"name": "intended_use_check", "result": "pass", "reason": f"Intended use: {intended_use_status}"})

    # Check 7: Contradictions
    contradiction_status = "none"
    if contradictions:
        contradiction_status = "found"
        if policy.require_review_on_conflict:
            review_reasons.append(f"contradictions found: {len(contradictions)} items")
            checks.append({"name": "contradiction_check", "result": "review_required", "reason": f"Found {len(contradictions)} contradictions and policy requires review"})
        else:
            checks.append({"name": "contradiction_check", "result": "pass", "reason": f"Found {len(contradictions)} contradictions but policy allows"})
    else:
        checks.append({"name": "contradiction_check", "result": "pass", "reason": "No contradictions found"})

    # Determine decision
    if deny_reasons:
        decision = "deny"
        risk_level = "high"
        recommended_action = "Block use of this result. Do not proceed."
    elif review_reasons:
        decision = "review_required"
        risk_level = "medium"
        recommended_action = "Route to human review or context verification before using for downstream decisions."
    else:
        decision = "allow"
        risk_level = "low"
        recommended_action = "Result can be used for intended purpose."

    reason = "; ".join(deny_reasons) if deny_reasons else ("; ".join(review_reasons) if review_reasons else "All checks passed")

    return {
        "trust_check_id": trust_check_id,
        "check_type": "search_result_trust_check",
        "status": "created",
        "experimental": True,
        "stateless": True,
        "free_mvp": True,
        "agent_id": req.agent_id,
        "result_id": req.result_id,
        "decision": decision,
        "risk_level": risk_level,
        "reason": reason,
        "recommended_action": recommended_action,
        "result_type": result_type,
        "freshness_status": freshness_status,
        "provenance_status": provenance_status,
        "contradiction_status": contradiction_status,
        "source_trust_status": source_trust_status,
        "intended_use_status": intended_use_status,
        "checks": checks,
        "evidence": {
            "evidence_id": evidence_id,
            "policy_version": "search-result-trust-v0.1",
            "input_hash": input_hash,
            "human_review_required": decision == "review_required",
            "checks_performed": [c["name"] for c in checks]
        },
        "agent_action_atom": {
            "atom_type": "search_result_trust_check_created",
            "action_type": "search_result_trust_check",
            "target": "retrieved_knowledge_or_observation",
            "audit_ready": True,
            "note": "Atom-compatible reference. This endpoint does not perform search or execute actions."
        },
        "can_feed_into": [
            "Memory Provenance Context Record",
            "Agent Tool Approval API",
            "Agent Payment Review API",
            "Payment Control Evidence Packet",
            "External Control Materials Map"
        ],
        "created_at": datetime.utcnow().isoformat() + "Z",
        "non_goals": [
            "does not perform search",
            "does not execute tools",
            "does not control robots",
            "does not execute physical actions",
            "does not update business systems",
            "does not replace safety systems",
            "not a robotics controller",
            "not a MES / WMS / CMMS",
            "not an official standard",
            "not legal or industrial safety certification"
        ]
    }

@app.post("/api/memory-provenance-record/build", include_in_schema=False)
async def build_memory_provenance_record(req: MemoryProvenanceRecordBuildRequest):
    state = req.state or MemoryStateInput()
    risk_flags = req.risk_flags or MemoryRiskFlagsInput()
    context_usage = req.context_usage or MemoryContextUsageInput()
    return {
        "memory_provenance_record_id": f"memory_provenance_record_{uuid.uuid4()}",
        "record_type": "memory_provenance_context_record",
        "status": "created",
        "experimental": True,
        "stateless": True,
        "free_builder": True,
        "agent_id": req.agent_id,
        "context_id": req.context_id,
        "context_type": req.context_type,
        "memory_layer": req.memory_layer,
        "provenance_graph": {
            "raw_sources": [s.model_dump() for s in req.raw_sources] if req.raw_sources else [],
            "facts": [f.model_dump() for f in req.facts] if req.facts else [],
            "profile_or_context_summary": req.summary
        },
        "state": state.model_dump(),
        "risk_flags": risk_flags.model_dump(),
        "context_usage": context_usage.model_dump(),
        "agent_action_atom": {
            "atom_type": "memory_provenance_record_created",
            "action_type": "context_state_record_build",
            "target": "agent_memory_or_context",
            "audit_ready": True,
            "includes": ["raw_sources", "facts", "profile_or_context_summary", "state", "risk_flags", "context_usage"],
            "note": "Atom-compatible reference. This builder does not call the external Action Atom Builder."
        },
        "can_feed_into": [
            "Tool Permission Policy",
            "Agent Spending Policy",
            "Budget Check",
            "Agent Action Atom",
            "Agent Payment Action Record",
            "Payment Control Evidence Packet",
            "Decision Cost Trace",
            "Memory Provenance Graph",
            "Token Placement Governance"
        ],
        "created_at": datetime.utcnow().isoformat() + "Z",
        "non_goals": [
            "not a memory store",
            "not a vector database",
            "not a model provider",
            "not a payment protocol",
            "not a wallet",
            "not a settlement layer",
            "not a legal compliance system",
            "not an official standard"
        ]
    }


@app.get("/.well-known/agent.json", include_in_schema=False)
async def agent_json():
    return [
        {
            "name": "Search Result Trust Check API",
            "endpoint": "POST /api/search-result-trust/check",
            "type": "search_result_trust_decision",
            "pricing": "free",
            "x402_required": False,
            "purpose": "Returns allow, deny, or review_required before an AI agent relies on a retrieved result, memory atom, observation, SOP, log, or operational record.",
            "use_when": [
                "an AI agent needs to decide whether retrieved knowledge can be used for a downstream decision",
                "a system needs to check freshness, provenance, source trust, and contradictions",
                "a developer needs an evidence_id for a search-result trust decision",
                "an agent is using search results before tool execution, payment review, operational decision, or physical action proposal"
            ],
            "returns": ["decision", "risk_level", "reason", "recommended_action", "freshness_status", "provenance_status", "contradiction_status", "source_trust_status", "intended_use_status", "evidence_id"],
            "can_feed_into": ["Memory Provenance Context Record", "Agent Tool Approval API", "Agent Payment Review API", "Payment Control Evidence Packet", "External Control Materials Map"],
            "non_goals": ["does not perform search", "does not execute tools", "does not control robots", "does not execute physical actions", "does not update business systems", "does not replace safety systems", "not a robotics controller", "not a MES / WMS / CMMS", "not an official standard", "not legal or industrial safety certification"]
        },
        {
            "name": "Memory Provenance Context Record Builder",
            "endpoint": "POST /api/memory-provenance-record/build",
            "type": "experimental_stateless_builder",
            "pricing": "free",
            "x402_required": False,
            "purpose": "Creates external control material for AI-agent memory and context usage, including raw sources, extracted facts, profile or context summary, state, use rule, evidence, last_checked, risk flags, and Atom-compatible reference.",
            "use_when": [
                "an AI agent needs to know whether a memory or context item can be used",
                "an AI agent needs source-of-truth context before payment or tool decisions",
                "a developer needs external provenance material for AI-agent memory usage",
                "a system needs a context state record that can feed into Tool Permission Policy, Spending Policy, Payment Action Record, and Evidence Packet workflows"
            ],
            "can_feed_into": [
                "Tool Permission Policy",
                "Agent Spending Policy",
                "Budget Check",
                "Agent Action Atom",
                "Agent Payment Action Record",
                "Payment Control Evidence Packet",
                "Decision Cost Trace",
                "Memory Provenance Graph",
                "Token Placement Governance"
            ],
            "non_goals": [
                "not a memory store",
                "not a vector database",
                "not a model provider",
                "not a payment protocol",
                "not a wallet",
                "not a settlement layer",
                "not a legal compliance system",
                "not an official standard"
            ]
        }
    ]


@app.get("/health", include_in_schema=False)
async def health_check():
    """Health check endpoint"""
    # Test database connectivity
    database_status = "operational"
    try:
        await agent_db.test_connection()
    except Exception:
        database_status = "error"

    return {
        "status": "healthy",
        "test_mode": TEST_MODE,
        "services": {
            "memory_engine": "operational",
            "trust_engine": "operational",
            "context_engine": "operational",
            "recall_engine": "operational",
            "database": database_status
        }
    }

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Agent Memory & Trust API",
        "description": "AI agent memory, trust verification, and context management infrastructure",
        "endpoints": {
            "search_result_trust_check": "/api/search-result-trust/check",
            "memory_store": "/api/memory/store",
            "memory_recall": "/api/memory/recall",
            "memory_delete": "/api/memory/delete",
            "memory_audit": "/api/memory/audit",
            "trust_verify": "/api/trust/verify",
            "context_package": "/api/context/package",
            "recall_compress": "/api/recall/compress",
            "recall_extract": "/api/recall/extract",
            "stats": "/api/stats",
            "health": "/health",
            "discovery": "/.well-known/x402.json"
        },
        "pricing": {
            "search_result_trust_check": "free",
            "memory_store": "0.05 USDC",
            "memory_recall": "0.03 USDC",
            "memory_delete": "0.03 USDC",
            "memory_audit": "0.05 USDC",
            "trust_verify": "0.20 USDC",
            "context_package": "0.10 USDC",
            "recall_compress": "0.05 USDC",
            "recall_extract": "0.03 USDC"
        },
        "network": "base",
        "currency": "USDC",
        "features": ["Agent Memory Management", "AES-256 Encryption", "Deletion Proof", "Audit Log", "Trust Verification", "Context Handover", "Content Compression", "Information Extraction", "Search Result Trust Check"]
    }

@app.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    content = open("llms.txt").read()
    return PlainTextResponse(content)

@app.get("/skill.md", include_in_schema=False)
async def skill_md():
    content = open("skill.md").read()
    return PlainTextResponse(content)

@app.get("/examples.md", include_in_schema=False)
async def examples_md():
    content = open("examples.md").read()
    return PlainTextResponse(content)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
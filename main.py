#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Memory & Trust API
FastAPI server with x402 payment protocol for AI agent memory, trust, and context management
"""

import os
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import base64
from datetime import datetime, timedelta
import asyncio
import traceback
from fastapi.openapi.utils import get_openapi

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
    title="Agent Memory & Trust API",
    description="AI agent memory, trust verification, and context management infrastructure",
    version="1.0.0"
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
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["info"]["x-guidance"] = "Store and recall encrypted AI agent memory across sessions. AES-256 encryption. Payment policy and audit memory."

    price_map = {
        "/api/memory/store": "0.05",
        "/api/memory/recall": "0.03",
        "/api/trust/verify": "0.20",
        "/api/context/package": "0.10",
        "/api/recall/compress": "0.05",
        "/api/recall/extract": "0.03",
        "/api/memory/delete": "0.03",
        "/api/memory/audit": "0.05"
    }

    for path, methods in openapi_schema.get("paths", {}).items():
        if path in price_map:
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    operation["x-payment-info"] = {
                        "protocols": ["x402"],
                        "authMode": "x402",
                        "price": {
                            "mode": "fixed",
                            "currency": "USDC",
                            "amount": price_map[path]
                        }
                    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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

@app.middleware("http")
async def x402_payment_middleware(request: Request, call_next):
    price = _PAID_ENDPOINTS.get((request.method, request.url.path))
    if not TEST_MODE and price is not None:
        if not request.headers.get("X-PAYMENT"):
            max_amount = str(round(float(price) * 1_000_000))
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": max_amount, "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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

# AI agent policy endpoint
@app.get("/.well-known/mcp/server-card.json")
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

@app.get("/.well-known/ai-agent-policy")
async def ai_agent_policy():
    import json
    import os
    policy_path = "ai-agent-policy.json"
    if os.path.exists(policy_path):
        with open(policy_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "Policy not found"}

# x402 payment protocol endpoint discovery
@app.get("/.well-known/x402.json")
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

@app.get("/.well-known/x402")
async def x402_discovery_manifest():
    return {
        "version": 1,
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
        "instructions": "Encrypted Japanese AI agent memory API with AES-256 encryption and audit trail."
    }

@app.post("/api/memory/store", response_model=StoreMemoryResponse)
async def store_memory(request: StoreMemoryRequest, http_request: Request):
    """Store agent memory with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "50000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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

@app.post("/api/memory/recall", response_model=RecallMemoryResponse)
async def recall_memory(request: RecallMemoryRequest, http_request: Request):
    """Recall related memories with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "30000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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

@app.post("/api/trust/verify", response_model=VerifyTrustResponse)
async def verify_trust(request: VerifyTrustRequest, http_request: Request):
    """Verify content trust and detect hallucinations with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "200000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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

@app.post("/api/context/package", response_model=PackageContextResponse)
async def package_context(request: PackageContextRequest, http_request: Request):
    """Create context handover package with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "100000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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

@app.post("/api/recall/compress", response_model=CompressContentResponse)
async def compress_content(request: CompressContentRequest, http_request: Request):
    """Compress conversation logs and work history with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "50000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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

@app.post("/api/recall/extract", response_model=ExtractContentResponse)
async def extract_content(request: ExtractContentRequest, http_request: Request):
    """Extract information from text with x402 payment verification"""

    # Skip payment verification in test mode
    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "30000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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

@app.post("/api/memory/delete")
async def delete_memory(request: DeleteMemoryRequest, http_request: Request):
    """Delete a memory and return an immutable SHA256 deletion proof with x402 payment verification"""

    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "30000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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


@app.get("/api/memory/audit")
async def get_audit_log(http_request: Request, agent_id: Optional[str] = None, limit: int = 100):
    """Return full audit log of store / recall / delete operations with x402 payment verification"""

    if not TEST_MODE:
        payment_header = http_request.headers.get("X-PAYMENT")
        if not payment_header:
            _pc = {"x402Version": 1, "accepts": [{"scheme": "exact", "network": "eip155:8453", "maxAmountRequired": "50000", "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "payTo": "0x60c402878EfcEcAe5733A88075328Aa2320C39BE"}], "error": "Payment required"}
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


@app.get("/api/stats")
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

@app.get("/health")
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

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Agent Memory & Trust API",
        "description": "AI agent memory, trust verification, and context management infrastructure",
        "endpoints": {
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
        "features": ["Agent Memory Management", "AES-256 Encryption", "Deletion Proof", "Audit Log", "Trust Verification", "Context Handover", "Content Compression", "Information Extraction"]
    }

@app.get("/llms.txt")
async def llms_txt():
    content = open("llms.txt").read()
    return PlainTextResponse(content)

@app.get("/skill.md")
async def skill_md():
    content = open("skill.md").read()
    return PlainTextResponse(content)

@app.get("/examples.md")
async def examples_md():
    content = open("examples.md").read()
    return PlainTextResponse(content)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
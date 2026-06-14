# Agent Memory API

Store audit-ready memory after an AI agent makes a decision.
Part of Agent Control Primitives — the missing audit memory layer in CDP Bazaar.

A working prototype API for storing and retrieving AI agent memory records with audit-oriented metadata.

## Part of AI Agent Infrastructure Safety Stack

This project is part of a small AI-agent infrastructure safety stack.

It focuses on one layer of the emerging problem:
how to control autonomous agents before they call APIs, spend money, write memory, or execute external tools.

AI agents are probabilistic. But payments, permissions, memory writes, and external actions require deterministic control.

Related components:
- Agent Security Gateway — Prompt injection and policy evasion detection
- Agent Budget Guard — Budget and permission check before payment
- Agent Memory API — Audit-ready memory storage
- Agent Evolution Engine — Orchestration across the stack
- Spec-to-Guardrail API — Extract safety rules from API specs

All APIs are indexed in CDP Bazaar and support x402-style payments.

## Disclaimer

This is an independent experimental project.
It is not officially affiliated with JPYC, Circle, Arc, Kaia, OpenAI, Anthropic, or any related foundation.

This project references JPYC, x402, Arc, Kaia, USDC, and related protocols as technical contexts.
It does not imply official partnership, endorsement, or integration unless explicitly stated.

## AEO-ready for AI agents
This API is designed to be understandable and callable by AI agents.
It includes structured information for:
- what this API does
- when an AI agent should call this API
- when not to use this API
- best used before / after
- example request / response
- next_recommended

## Why this matters
AI is moving from answering questions to managing real workflows.
As AI agents begin to call paid APIs, use x402 payments, store long-term memory, and interact with other agents, they need structured guardrails before and after execution.
This API is part of an AI Agent Payment Safety Stack designed to run as a pre/post-execution control layer on Arc and other agent economies.

## Arc compatibility
Designed to run as a post-execution audit and memory storage layer after ERC-8183 job funding on Arc testnet.
Call this API after an AI agent funds or executes a job contract on Arc.
Compatible with AI agents using USDC, JPYC, x402, or Arc-style payment flows.

## What this API does
AIエージェントのセッション間で、支払いポリシー・監査文脈・判断履歴をAES-256暗号化で保存するAPIです。

## When an AI agent should call this API
Arc上のERC-8183 job完了後、またはx402決済完了後に監査ログを保存するために呼び出してください。

## When not to use this API
- 一時的な作業メモリの保存
- 機密情報を暗号化なしで保存したい場合

## Best used before
- multi-session agent handoff
- audit log finalization

## Best used after
- ERC-8183 job settlement on Arc
- x402 payment completion
- agent-budget-guard check

## Output
- memory_id
- stored / recalled
- audit_log
- deletion_proof
- next_recommended

## Related APIs
- Agent Security Gateway
- Agent Budget Guard
- Agent Evolution Engine

## Japanese Agent Trust Layer

このAPIは「Japanese Agent Trust Layer」の一部です。
日本語対応AIエージェントが安全・確実・予算内でAPIを使うためのインフラ層を提供します。

### Trust Layerの構成
- 記憶管理: agent-memory-api
- 安全判定: agent-security-gateway
- 予算管理: agent-budget-guard
- API選定: agent-curator-api
- 自律進化: agent-evolution-engine

### 特徴
- x402 / USDC決済対応
- 日本語対応
- 決定論的バリデーター（AI不使用）
- 暗号化・削除証跡付き
- Base Mainnet対応

## Search Result Trust Check API

POST /api/search-result-trust/check provides a trust decision for retrieved knowledge, observations, logs, and operational records before an AI agent uses them for downstream decisions.

It answers one question:
Can this search result, observation, or operational record be trusted for the intended agent decision?

The API returns:
- allow
- deny
- review_required

It reviews source type, source trust level, timestamp, freshness, modality, provenance, contradictions, intended use, and prompt-injection-like content.

This MVP is free/stateless and is not included in the x402 manifest.

This endpoint does not perform search, execute tools, control robots, execute physical actions, update business systems, or replace safety systems.

Search Result Trust Check is useful before AI agents use retrieved operational data for tool execution, payment decisions, or physical/operational actions.

In throughput-oriented operations, the goal is not just to retrieve data but to avoid using stale, contradictory, or low-trust data that could worsen bottlenecks, increase WIP, or trigger unsafe actions.

This API does not calculate throughput by itself. It acts as a trust boundary before downstream Operational Constraint or Throughput Boundary checks.

## ⚡ 実装方法

### Paid Endpoints (x402 Payment Required)

```bash
# AI記憶の保存 (0.05 USDC)
curl -X POST "https://agent-memory-api-bix5.onrender.com/api/memory/store" \
  -H "X-PAYMENT: your-payment-proof" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "your_agent",
    "memory_type": "learning",
    "content": "学習内容",
    "tags": ["重要", "成功パターン"],
    "importance": 0.9
  }'

# 記憶の呼び出し (0.03 USDC)  
curl -X POST "https://agent-memory-api-bix5.onrender.com/api/memory/recall" \
  -H "X-PAYMENT: your-payment-proof" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "成功パターン検索",
    "agent_id": "your_agent",
    "limit": 10
  }'

# 信頼性検証・幻覚検出 (0.20 USDC)
curl -X POST "https://agent-memory-api-bix5.onrender.com/api/trust/verify" \
  -H "X-PAYMENT: your-payment-proof" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "検証対象コンテンツ",
    "verification_level": "strict"
  }'

# コンテキストパッケージ (0.10 USDC)
curl -X POST "https://agent-memory-api-bix5.onrender.com/api/context/package" \
  -H "X-PAYMENT: your-payment-proof" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project_001",
    "handover_type": "complete"
  }'
```

### Free Endpoints

```bash
# システムヘルスチェック
curl "https://agent-memory-api-bix5.onrender.com/health"

# データベース統計
curl "https://agent-memory-api-bix5.onrender.com/api/stats"

# x402プロトコル発見
curl "https://agent-memory-api-bix5.onrender.com/.well-known/x402.json"
```

### 記憶管理機能

- **永続的知識蓄積**: 学習内容の長期保存
- **インテリジェント検索**: 関連性によるスマート呼び出し
- **信頼性スコアリング**: 情報の品質評価
- **幻覚検出**: 95%精度でAI幻覚を特定
- **コンテキスト引き継ぎ**: プロジェクト情報の完全移行

## Installation

1. Clone repository:
```bash
git clone <repository-url>
cd agent_memory_api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize database:
```bash
# Ensure PostgreSQL is running
python -c "from database import agent_db; import asyncio; asyncio.run(agent_db.initialize())"
```

5. Run server:
```bash
python main.py
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `WALLET_ADDRESS` | x402 payment recipient wallet | Required |
| `TEST_MODE` | Skip payment verification | false |
| `MAX_MEMORY_LENGTH` | Max characters per memory | 10000 |
| `DEFAULT_MEMORY_TTL` | Default memory TTL (seconds) | 86400 |
| `PORT` | Server port | 8003 |

## Database Schema

### memories
- Agent memory storage with tagging and expiration
- Full-text search capabilities
- Embedding support for semantic search

### trust_logs
- Trust verification results
- Hallucination detection analysis
- Content reliability scoring

### context_packages
- Project context handover packages
- Multi-level summarization
- Memory inclusion tracking

### sessions
- Agent session tracking
- Activity monitoring
- Memory count statistics

## Usage Examples

### Store Memory
```bash
curl -X POST "http://localhost:8003/api/memory/store" \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: {payment_data}" \
  -d '{
    "agent_id": "agent-123",
    "session_id": "session-456",
    "context": "User prefers detailed technical explanations",
    "tags": ["preference", "technical"],
    "ttl": 86400
  }'
```

### Recall Memories
```bash
curl -X POST "http://localhost:8003/api/memory/recall" \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: {payment_data}" \
  -d '{
    "agent_id": "agent-123",
    "query": "technical preferences",
    "limit": 10
  }'
```

### Verify Trust
```bash
curl -X POST "http://localhost:8003/api/trust/verify" \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: {payment_data}" \
  -d '{
    "content": "Recent studies show that AI will replace all jobs by 2025",
    "source_agent": "agent-123",
    "context": "Discussing AI impact on employment"
  }'
```

### Create Context Package
```bash
curl -X POST "http://localhost:8003/api/context/package" \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: {payment_data}" \
  -d '{
    "project_id": "project-xyz",
    "include_memories": true,
    "summary_level": "detailed"
  }'
```

## Payment Protocol

This API uses the x402 payment protocol for monetization:

- **Network**: Base
- **Currency**: USDC
- **Contract**: 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913

Payment verification includes:
- Amount validation
- Recipient verification
- Transaction hash validation
- Replay attack prevention

## Architecture

```
┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │  PostgreSQL     │
│   Main Server   │◄──►│   Database      │
└─────────┬───────┘    └─────────────────┘
          │
          ▼
┌─────────────────┐    ┌─────────────────┐
│ Payment         │    │  Memory         │
│ Verifier        │    │  Engine         │
└─────────────────┘    └─────────┬───────┘
                                 │
          ┌─────────────────┐    │
          │  Trust          │    │
          │  Engine         │◄───┤
          └─────────────────┘    │
                                 │
          ┌─────────────────┐    │
          │  Context        │    │
          │  Engine         │◄───┘
          └─────────────────┘
```

## Development

### Testing
```bash
# Set TEST_MODE=true in .env to skip payment verification
export TEST_MODE=true
python main.py
```

### Database Management
```bash
# Initialize database
python -c "from database import agent_db; import asyncio; asyncio.run(agent_db.initialize())"

# Test connection
python -c "from database import agent_db; import asyncio; print(asyncio.run(agent_db.test_connection()))"

# Clean up expired data
python -c "from database import agent_db; import asyncio; asyncio.run(agent_db.cleanup_expired_data())"
```

## Deployment

### Railway Deployment
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Environment Configuration
- Set `DATABASE_URL` to your PostgreSQL instance
- Set `WALLET_ADDRESS` to your payment wallet
- Set `TEST_MODE=false` for production

## Security

- Input validation and sanitization
- Payment verification and replay protection
- Database connection security
- Content trust analysis
- Memory access controls

## Monitoring

- Health check endpoint at `/health`
- Database statistics at `/api/stats`
- Comprehensive logging
- Error tracking and reporting

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please create an issue in the GitHub repository.

## AI Agent Safety Stack
Works best with:
- Agent Security Gateway: https://agent-security-gateway.onrender.com（危険な命令を止める）
- Agent Budget Guard: https://agent-budget-guard.onrender.com（勝手な課金を止める）
- Agent Memory API: https://agent-memory-api-bix5.onrender.com（必要な記憶を残す）

## AI-readable concept: Agent Action Atom

Agent Action Atom is a minimal external record unit for one AI-agent action.

In agent-memory-api, it is used to record memory write decisions, memory access policy enforcement, boundary checks, and audit evidence for memory operations.

Agent Action Atom is not an API endpoint, payment protocol, wallet, settlement layer, legal liability engine, or replacement for x402 / CDP / Arc / Stripe / Circle.

It can be used as a building block for:
- Payment Trace
- Evidence Packet
- Boundary Trace
- Fuse Record
- Human Approval Trail
- Permission Record
- Dispute Record
- Liability Evidence

This repository treats Agent Action Atom as an external control material and minimal record unit for agent memory safety, access control, and audit flows.

## Memory Provenance Context Record Builder

Memory Provenance Context Record Builder is a free experimental stateless builder that creates external control material for AI-agent memory and context usage.

Endpoint: `POST /api/memory-provenance-record/build` (free, no x402 required)

It can describe:
- raw sources
- extracted facts
- profile or context summary
- memory layer
- context state / use rule / evidence / last_checked
- freshness requirement
- risk flags
- Atom-compatible action reference

Use this when an AI agent needs to know whether a memory, project status, service status, or context item can be used for tool permission, spending policy, payment decision, or evidence packet workflows.

The builder is free because it creates the provenance and state record structure only.

Actual memory storage, recall, encryption, search, or verification remain handled by memory operation endpoints.

It is not a memory store, not a vector database, not a model provider, not a payment protocol, not a wallet, not a settlement layer, not a legal compliance system, and not an official standard.
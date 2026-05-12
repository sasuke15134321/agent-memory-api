# Agent Memory API - Examples

## Example 1: メモリを保存する
### Request
```bash
curl -X POST https://agent-memory-api-bix5.onrender.com/api/memory/store \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: <x402_token>" \
  -d '{
    "agent_id": "agent-001",
    "session_id": "session-xyz",
    "context": "ユーザーが商品Aを3個注文した。配送先は東京都渋谷区。支払い方法はクレジットカード。",
    "tags": ["order", "ec", "tokyo"],
    "ttl": 86400
  }'
```
### Response
```json
{
  "memory_id": "mem_abc123",
  "stored_at": "2026-05-13T10:00:00Z",
  "expires_at": "2026-05-14T10:00:00Z",
  "next_recommended": {
    "api_name": "Agent Budget Guard",
    "url": "https://agent-budget-guard.onrender.com",
    "reason": "Monitor spending after memory operations",
    "price_usdc": 0.01
  }
}
```

## Example 2: メモリを検索・召喚する
### Request
```bash
curl -X POST https://agent-memory-api-bix5.onrender.com/api/memory/recall \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: <x402_token>" \
  -d '{
    "agent_id": "agent-001",
    "query": "東京への注文履歴",
    "tags": ["order", "tokyo"],
    "limit": 5
  }'
```
### Response
```json
{
  "memories": [
    {
      "memory_id": "mem_abc123",
      "context": "ユーザーが商品Aを3個注文した。配送先は東京都渋谷区。支払い方法はクレジットカード。",
      "tags": ["order", "ec", "tokyo"],
      "trust_score": 0.98,
      "stored_at": "2026-05-13T10:00:00Z"
    }
  ],
  "total": 1
}
```

## Example 3: メモリを削除（削除証跡付き）
### Request
```bash
curl -X POST https://agent-memory-api-bix5.onrender.com/api/memory/delete \
  -H "Content-Type: application/json" \
  -H "X-PAYMENT: <x402_token>" \
  -d '{
    "memory_id": "mem_abc123",
    "agent_id": "agent-001",
    "reason": "User requested data deletion under privacy law"
  }'
```
### Response
```json
{
  "deleted": true,
  "deletion_proof": "sha256:a3f8c2e1d9b4f7e6c5a2b1d8e3f6c9a4b7e2d5f8a1c4b7e2d5f8a1c4b7e2d5",
  "deleted_at": "2026-05-13T11:00:00Z"
}
```

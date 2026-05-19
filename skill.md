# Agent Memory API Skill

## Purpose
Use Agent Memory API after an AI agent completes a payment, API call, or decision that requires an audit record.

## When to use
- An AI agent completed an x402 payment and needs an audit record
- An AI agent needs to persist session context across multiple calls
- The system requires a tamper-evident record of agent decisions
- Storing approved budget policies for future reference

## When not to use
- Store large files or binary data
- Replace a database or file storage system
- Store personal data without TTL settings
- Replace a wallet or token custody system

## Main endpoint
POST /api/memory/store

## Example request
{
  "agent_id": "agent-001",
  "memory_type": "audit",
  "content": "Budget check approved: 0.05 USDC for api.example.com",
  "ttl_seconds": 86400
}

## Decision logic
- stored: true -> Audit record created, proceed
- stored: false -> Storage failed, retry or escalate
- audit_log_id -> Use for downstream invoice or compliance checks

## Recommended flow
AI Agent -> Security Gateway -> Budget Guard -> x402 Payment -> Paid API -> Memory API

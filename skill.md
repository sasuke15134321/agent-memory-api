# Agent Memory API Skill

## Search Result Trust Check (Free)

### Purpose
Check trust of search results, observations, or operational records before using them for downstream AI agent decisions.

### When to use
- An AI agent retrieved external data and needs to check freshness
- A system needs to verify source trust before tool execution
- Data contains contradictions that need review before payment decisions
- Observations or logs are used for physical/operational actions

### When not to use
- Replace actual security systems or policy enforcement
- Replace human judgment for critical decisions
- Guarantee completeness of trust assessment
- Control robots or physical systems directly

### Endpoint
POST /api/search-result-trust/check (FREE)

### Example
{
  "agent_id": "agent-001",
  "result_type": "operational_log",
  "source": {"trust_level": "medium", "source_type": "monitoring_system"},
  "freshness": {"status": "current", "max_age_seconds": 300},
  "intended_use": "tool_decision",
  "policy": {"deny_stale_results": true, "require_review_on_conflict": true}
}

## Paid Memory Operations

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
POST /api/memory/store (0.05 USDC)

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

## Skill: Agent Action Atom

### Use this when
- memory write decision recording
- memory access policy check
- boundary enforcement for memory operations
- audit evidence attachment for memory actions
- fuse allow / block / escalate for sensitive memory writes
- human approval for critical memory operations

### Do not use this as
- a payment protocol
- a wallet or settlement layer
- a legal liability engine
- a compliance guarantee
- an implemented API unless explicitly provided

### Minimal record fields
atom_id / actor / action / target / source / policy / meaning / state / proof / time / relation

### Purpose
Make one AI-agent memory operation externally explainable and auditable, especially for memory access control and audit flows.

---

## Skill: Memory Provenance Context Record Builder

Memory Provenance Context Record Builder is a free experimental stateless builder that creates external control material for AI-agent memory and context usage.

### Use this when
- an AI agent needs to know whether a memory or context item can be used
- an AI agent needs source-of-truth context before payment or tool decisions
- a developer needs external provenance material for AI-agent memory usage
- a system needs a context state record that can feed into Tool Permission Policy, Spending Policy, Payment Action Record, and Evidence Packet workflows

### It can describe
- raw sources
- extracted facts
- profile or context summary
- memory layer
- context state / use rule / evidence / last_checked
- freshness requirement
- risk flags
- Atom-compatible action reference

### Endpoint
POST /api/memory-provenance-record/build (free, no x402 required)

### Output
memory_provenance_record_id / provenance_graph / state / risk_flags / context_usage / agent_action_atom / can_feed_into / created_at / non_goals

### Can feed into
- Tool Permission Policy
- Agent Spending Policy
- Budget Check
- Agent Action Atom
- Agent Payment Action Record
- Payment Control Evidence Packet
- Decision Cost Trace
- Memory Provenance Graph
- Token Placement Governance

### Do not use this as
- a memory store
- a vector database
- a model provider
- a payment protocol
- a wallet
- a settlement layer
- a legal compliance system
- an official standard

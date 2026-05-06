# Agent Memory & Trust API

AI agent memory, trust verification, and context management infrastructure with x402 payment protocol integration.

## Features

- **Agent Memory Management**: Store and recall agent memories with intelligent tagging and search
- **Trust Verification**: Content trust scoring and hallucination detection
- **Context Packaging**: Project context handover and summarization
- **x402 Payment Protocol**: Cryptocurrency payment integration (USDC on Base network)
- **PostgreSQL Database**: Persistent storage for memories, trust logs, and context packages

## API Endpoints

### Paid Endpoints (x402 Payment Required)

- **POST /api/memory/store** (0.05 USDC) - Store agent memory
- **POST /api/memory/recall** (0.03 USDC) - Search and recall memories
- **POST /api/trust/verify** (0.20 USDC) - Verify content trust and detect hallucinations
- **POST /api/context/package** (0.10 USDC) - Create context handover package

### Free Endpoints

- **GET /health** - Health check
- **GET /api/stats** - Database statistics
- **GET /.well-known/x402.json** - x402 protocol discovery

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
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database operations for Agent Memory & Trust API
Handles PostgreSQL database for agent memories, trust logs, and context packages
"""

import os
import json
import asyncpg
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import hashlib


class AgentDatabase:
    def __init__(self):
        # Use DATABASE_URL environment variable for PostgreSQL connection
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            # Fallback to individual components if DATABASE_URL not set
            host = os.getenv("POSTGRES_HOST", "localhost")
            port = os.getenv("POSTGRES_PORT", "5432")
            database = os.getenv("POSTGRES_DB", "agent_memory")
            user = os.getenv("POSTGRES_USER", "postgres")
            password = os.getenv("POSTGRES_PASSWORD", "")

            if password:
                self.database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
            else:
                self.database_url = f"postgresql://{user}@{host}:{port}/{database}"

        print(f"[INFO] PostgreSQL database configured: {self.database_url.split('@')[1] if '@' in self.database_url else self.database_url}")

    async def get_connection(self):
        """Get database connection"""
        return await asyncpg.connect(self.database_url)

    async def initialize(self):
        """Initialize database and create tables if they don't exist"""
        conn = await self.get_connection()
        try:
            # Create memories table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id SERIAL PRIMARY KEY,
                    memory_id VARCHAR(255) UNIQUE NOT NULL,
                    agent_id VARCHAR(255) NOT NULL,
                    session_id VARCHAR(255) NOT NULL,
                    context TEXT NOT NULL,
                    tags JSONB DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP,
                    embedding VECTOR(1536),  -- OpenAI embedding dimension
                    metadata JSONB DEFAULT '{}'
                )
            """)

            # Create trust_logs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS trust_logs (
                    id SERIAL PRIMARY KEY,
                    content_hash VARCHAR(255) NOT NULL,
                    source_agent VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    context TEXT,
                    trust_score INTEGER NOT NULL,
                    hallucination_risk VARCHAR(50) NOT NULL,
                    verdict VARCHAR(50) NOT NULL,
                    warnings JSONB DEFAULT '[]',
                    analysis_metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)

            # Create context_packages table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS context_packages (
                    id SERIAL PRIMARY KEY,
                    package_id VARCHAR(255) UNIQUE NOT NULL,
                    project_id VARCHAR(255) NOT NULL,
                    summary_level VARCHAR(50) NOT NULL,
                    package_data JSONB NOT NULL,
                    memory_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP
                )
            """)

            # Create sessions table for tracking agent sessions
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    session_id VARCHAR(255) UNIQUE NOT NULL,
                    agent_id VARCHAR(255) NOT NULL,
                    project_id VARCHAR(255),
                    started_at TIMESTAMP DEFAULT NOW(),
                    last_activity TIMESTAMP DEFAULT NOW(),
                    memory_count INTEGER DEFAULT 0,
                    status VARCHAR(50) DEFAULT 'active'
                )
            """)

            # Create indexes for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_agent_id ON memories(agent_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_session_id ON memories(session_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON memories(expires_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_tags_gin ON memories USING GIN (tags)")

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_trust_logs_source_agent ON trust_logs(source_agent)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_trust_logs_content_hash ON trust_logs(content_hash)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_trust_logs_created_at ON trust_logs(created_at)")

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_context_packages_project_id ON context_packages(project_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_context_packages_created_at ON context_packages(created_at)")

            await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON sessions(agent_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id)")

            print("[OK] PostgreSQL database initialized with all tables and indexes")

        finally:
            await conn.close()

    async def store_memory(self, agent_id: str, session_id: str, context: str,
                          tags: List[str] = None, ttl: int = 86400) -> Dict[str, str]:
        """
        Store agent memory

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            context: Memory content
            tags: Optional tags
            ttl: Time to live in seconds

        Returns:
            Dictionary with memory_id, stored_at, expires_at
        """
        conn = await self.get_connection()
        try:
            # Generate unique memory ID
            memory_id = hashlib.sha256(f"{agent_id}:{session_id}:{context}:{datetime.now().isoformat()}".encode()).hexdigest()[:32]

            stored_at = datetime.now()
            expires_at = stored_at + timedelta(seconds=ttl)

            # Insert memory
            await conn.execute("""
                INSERT INTO memories (memory_id, agent_id, session_id, context, tags, created_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, memory_id, agent_id, session_id, context, json.dumps(tags or []), stored_at, expires_at)

            # Update session
            await self._update_session(conn, session_id, agent_id)

            return {
                "memory_id": memory_id,
                "stored_at": stored_at.isoformat(),
                "expires_at": expires_at.isoformat()
            }

        finally:
            await conn.close()

    async def recall_memories(self, agent_id: str, query: str, tags: List[str] = None,
                             limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recall memories for an agent

        Args:
            agent_id: Agent identifier
            query: Search query
            tags: Optional tag filters
            limit: Maximum number of memories to return

        Returns:
            List of memory dictionaries
        """
        conn = await self.get_connection()
        try:
            base_query = """
                SELECT memory_id, context, tags, created_at, expires_at, metadata
                FROM memories
                WHERE agent_id = $1 AND (expires_at IS NULL OR expires_at > NOW())
            """
            params = [agent_id]
            param_count = 1

            # Add tag filtering if specified
            if tags:
                param_count += 1
                base_query += f" AND tags @> ${param_count}"
                params.append(json.dumps(tags))

            # Add text search if query is provided
            if query.strip():
                param_count += 1
                base_query += f" AND context ILIKE ${param_count}"
                params.append(f"%{query}%")

            # Order by creation time and limit
            base_query += f" ORDER BY created_at DESC LIMIT ${param_count + 1}"
            params.append(limit)

            rows = await conn.fetch(base_query, *params)

            memories = []
            for row in rows:
                memories.append({
                    "memory_id": row["memory_id"],
                    "context": row["context"],
                    "tags": json.loads(row["tags"]) if row["tags"] else [],
                    "created_at": row["created_at"].isoformat(),
                    "expires_at": row["expires_at"].isoformat() if row["expires_at"] else None,
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
                })

            return memories

        finally:
            await conn.close()

    async def store_trust_verification(self, content: str, source_agent: str, context: str,
                                     trust_score: int, hallucination_risk: str, verdict: str,
                                     warnings: List[str], analysis_metadata: Dict[str, Any] = None) -> int:
        """
        Store trust verification result

        Args:
            content: Content that was verified
            source_agent: Source agent identifier
            context: Verification context
            trust_score: Trust score (0-100)
            hallucination_risk: Risk level
            verdict: Final verdict
            warnings: List of warnings
            analysis_metadata: Additional analysis data

        Returns:
            Log ID
        """
        conn = await self.get_connection()
        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            log_id = await conn.fetchval("""
                INSERT INTO trust_logs (content_hash, source_agent, content, context, trust_score,
                                      hallucination_risk, verdict, warnings, analysis_metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
            """, content_hash, source_agent, content, context, trust_score,
                hallucination_risk, verdict, json.dumps(warnings),
                json.dumps(analysis_metadata or {}))

            return log_id

        finally:
            await conn.close()

    async def store_context_package(self, project_id: str, summary_level: str,
                                   package_data: Dict[str, Any], memory_count: int = 0,
                                   ttl: int = 604800) -> str:  # Default 7 days
        """
        Store context package

        Args:
            project_id: Project identifier
            summary_level: Summary level
            package_data: Package content
            memory_count: Number of memories included
            ttl: Time to live in seconds

        Returns:
            Package ID
        """
        conn = await self.get_connection()
        try:
            package_id = hashlib.sha256(f"{project_id}:{summary_level}:{datetime.now().isoformat()}".encode()).hexdigest()[:32]

            created_at = datetime.now()
            expires_at = created_at + timedelta(seconds=ttl)

            await conn.execute("""
                INSERT INTO context_packages (package_id, project_id, summary_level, package_data,
                                            memory_count, created_at, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, package_id, project_id, summary_level, json.dumps(package_data),
                memory_count, created_at, expires_at)

            return package_id

        finally:
            await conn.close()

    async def _update_session(self, conn: asyncpg.Connection, session_id: str, agent_id: str, project_id: str = None):
        """Update session activity"""
        now = datetime.now()

        # Check if session exists
        existing = await conn.fetchrow("SELECT id FROM sessions WHERE session_id = $1", session_id)

        if existing:
            # Update existing session
            await conn.execute("""
                UPDATE sessions
                SET last_activity = $1, memory_count = memory_count + 1
                WHERE session_id = $2
            """, now, session_id)
        else:
            # Create new session
            await conn.execute("""
                INSERT INTO sessions (session_id, agent_id, project_id, started_at, last_activity, memory_count)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, session_id, agent_id, project_id, now, now, 1)

    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = await self.get_connection()
        try:
            stats = {}

            # Memory statistics
            total_memories = await conn.fetchval("SELECT COUNT(*) FROM memories")
            active_memories = await conn.fetchval("SELECT COUNT(*) FROM memories WHERE expires_at IS NULL OR expires_at > NOW()")
            stats['total_memories'] = total_memories
            stats['active_memories'] = active_memories

            # Agent statistics
            unique_agents = await conn.fetchval("SELECT COUNT(DISTINCT agent_id) FROM memories")
            stats['unique_agents'] = unique_agents

            # Session statistics
            active_sessions = await conn.fetchval("SELECT COUNT(*) FROM sessions WHERE status = 'active'")
            total_sessions = await conn.fetchval("SELECT COUNT(*) FROM sessions")
            stats['active_sessions'] = active_sessions
            stats['total_sessions'] = total_sessions

            # Trust verification statistics
            total_verifications = await conn.fetchval("SELECT COUNT(*) FROM trust_logs")
            high_trust_count = await conn.fetchval("SELECT COUNT(*) FROM trust_logs WHERE trust_score >= 80")
            stats['total_verifications'] = total_verifications
            stats['high_trust_verifications'] = high_trust_count

            # Context package statistics
            total_packages = await conn.fetchval("SELECT COUNT(*) FROM context_packages")
            active_packages = await conn.fetchval("SELECT COUNT(*) FROM context_packages WHERE expires_at IS NULL OR expires_at > NOW()")
            stats['total_packages'] = total_packages
            stats['active_packages'] = active_packages

            # Database size (PostgreSQL specific)
            db_size = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
            stats['database_size'] = db_size

            return stats

        finally:
            await conn.close()

    async def cleanup_expired_data(self):
        """Clean up expired memories and packages"""
        conn = await self.get_connection()
        try:
            now = datetime.now()

            # Clean up expired memories
            memories_deleted = await conn.fetchval("""
                WITH deleted_memories AS (
                    DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < $1
                    RETURNING id
                )
                SELECT COUNT(*) FROM deleted_memories
            """, now)

            # Clean up expired context packages
            packages_deleted = await conn.fetchval("""
                WITH deleted_packages AS (
                    DELETE FROM context_packages WHERE expires_at IS NOT NULL AND expires_at < $1
                    RETURNING id
                )
                SELECT COUNT(*) FROM deleted_packages
            """, now)

            if memories_deleted > 0 or packages_deleted > 0:
                print(f"[INFO] Cleaned up {memories_deleted} expired memories and {packages_deleted} expired packages")

        finally:
            await conn.close()

    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = await self.get_connection()
            await conn.fetchval("SELECT 1")
            await conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] Database connection test failed: {e}")
            return False


# Global database instance
agent_db = AgentDatabase()
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory Engine for AI Agent Memory Management
Handles memory storage, recall, and intelligent memory management
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import json
import hashlib
from datetime import datetime, timedelta
import re

from database import agent_db
from encryption_engine import encryption_engine


class MemoryEngine:
    def __init__(self):
        self.max_memory_length = int(os.getenv("MAX_MEMORY_LENGTH", "10000"))  # Max characters per memory
        self.default_ttl = int(os.getenv("DEFAULT_MEMORY_TTL", "86400"))  # 24 hours default

        # main.py creates MemoryEngine only after its FastAPI app exists.
        # Use that point to restore the MCP HTTP mount and lifecycle without
        # rewriting the large main.py module.
        try:
            import sys
            from mcp_server import install_http_transport
            parent_main = sys.modules.get("main")
            if parent_main is not None and hasattr(parent_main, "app"):
                install_http_transport(parent_main.app, "/mcp")
        except Exception as mcp_err:
            print(f"[WARN] MCP transport initialization failed: {mcp_err}")

    async def store_memory(self, agent_id: str, session_id: str, context: str,
                          tags: List[str] = None, ttl: int = None) -> Dict[str, str]:
        """
        Store agent memory with intelligent processing

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            context: Memory content
            tags: Optional tags for categorization
            ttl: Time to live in seconds

        Returns:
            Dictionary with storage result
        """
        try:
            if not agent_id or not session_id or not context:
                raise ValueError("agent_id, session_id, and context are required")

            if len(context) > self.max_memory_length:
                context = context[:self.max_memory_length] + "...[truncated]"

            context = self._clean_context(context)
            context = encryption_engine.encrypt(context)

            if tags is None:
                tags = []

            auto_tags = self._extract_tags_from_context(context)
            tags.extend(auto_tags)
            tags = list(set(tags))[:10]

            if ttl is None:
                ttl = self.default_ttl

            result = await agent_db.store_memory(
                agent_id=agent_id,
                session_id=session_id,
                context=context,
                tags=tags,
                ttl=ttl
            )

            print(f"[OK] Memory stored for agent {agent_id}: {result['memory_id']}")
            return result

        except Exception as e:
            print(f"[ERROR] Memory storage failed: {e}")
            raise

    async def recall_memories(self, agent_id: str, query: str, tags: List[str] = None,
                             limit: int = 10) -> List[Dict[str, Any]]:
        """Recall memories with intelligent search."""
        try:
            if not agent_id:
                raise ValueError("agent_id is required")

            query = self._clean_query(query)
            memories = await agent_db.recall_memories(
                agent_id=agent_id,
                query=query,
                tags=tags,
                limit=limit * 2
            )

            for m in memories:
                m["context"] = encryption_engine.decrypt(m["context"])

            scored_memories = self._score_relevance(memories, query)
            scored_memories.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            return scored_memories[:limit]

        except Exception as e:
            print(f"[ERROR] Memory recall failed: {e}")
            raise

    async def get_memory_summary(self, agent_id: str, session_id: str = None) -> Dict[str, Any]:
        """Get memory summary for an agent."""
        try:
            recent_memories = await agent_db.recall_memories(
                agent_id=agent_id,
                query="",
                limit=100
            )

            if session_id:
                recent_memories = [m for m in recent_memories if session_id in str(m)]

            total_memories = len(recent_memories)
            all_tags = []
            for memory in recent_memories:
                all_tags.extend(memory.get('tags', []))

            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            if recent_memories:
                earliest = min(datetime.fromisoformat(m['created_at'].replace('Z', '+00:00')) for m in recent_memories)
                latest = max(datetime.fromisoformat(m['created_at'].replace('Z', '+00:00')) for m in recent_memories)
                time_span_days = (latest - earliest).days
            else:
                time_span_days = 0

            return {
                'total_memories': total_memories,
                'time_span_days': time_span_days,
                'top_tags': [{'tag': tag, 'count': count} for tag, count in top_tags],
                'session_filter': session_id,
                'summary_generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[ERROR] Memory summary generation failed: {e}")
            raise

    def _clean_context(self, context: str) -> str:
        """Clean and normalize context text."""
        context = re.sub(r'\s+', ' ', context.strip())
        context = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', context)
        context = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', context)
        context = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', context)
        return context

    def _clean_query(self, query: str) -> str:
        """Clean and normalize search query."""
        if not query:
            return ""
        return re.sub(r'\s+', ' ', query.strip())

    def _extract_tags_from_context(self, context: str) -> List[str]:
        """Extract relevant tags from context content."""
        tags = []
        ai_keywords = [
            'ai', 'machine learning', 'deep learning', 'neural network',
            'llm', 'gpt', 'claude', 'chatbot', 'nlp', 'computer vision',
            'api', 'database', 'web', 'mobile', 'cloud', 'docker'
        ]

        context_lower = context.lower()
        for keyword in ai_keywords:
            if keyword in context_lower:
                tags.append(keyword.replace(' ', '_'))

        languages = [
            'python', 'javascript', 'java', 'go', 'rust', 'cpp',
            'typescript', 'swift', 'kotlin', 'php', 'ruby'
        ]

        for lang in languages:
            if lang in context_lower:
                tags.append(f'lang_{lang}')

        action_keywords = {
            'error': ['error', 'exception', 'fail', 'bug'],
            'debug': ['debug', 'trace', 'log'],
            'feature': ['feature', 'implement', 'add', 'create'],
            'fix': ['fix', 'resolve', 'solve', 'patch'],
            'optimization': ['optimize', 'performance', 'speed', 'improve']
        }

        for action, keywords in action_keywords.items():
            if any(keyword in context_lower for keyword in keywords):
                tags.append(action)

        return tags[:5]

    def _score_relevance(self, memories: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Score memories for relevance to query."""
        if not query:
            for memory in memories:
                memory['relevance_score'] = 50
            return memories

        query_terms = set(query.lower().split())

        for memory in memories:
            score = 0
            context = memory.get('context', '').lower()
            tags = [tag.lower() for tag in memory.get('tags', [])]

            for term in query_terms:
                if term in context:
                    score += context.count(term) * 10

                if term in tags:
                    score += 15

                for word in context.split():
                    if term in word and len(term) > 2:
                        score += 3

            try:
                created_at = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
                days_old = (datetime.now(created_at.tzinfo) - created_at).days
                if days_old < 7:
                    score += 5
            except Exception:
                pass

            memory['relevance_score'] = min(100, max(0, score))

        return memories

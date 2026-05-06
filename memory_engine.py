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


class MemoryEngine:
    def __init__(self):
        self.max_memory_length = int(os.getenv("MAX_MEMORY_LENGTH", "10000"))  # Max characters per memory
        self.default_ttl = int(os.getenv("DEFAULT_MEMORY_TTL", "86400"))  # 24 hours default

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
            # Validate inputs
            if not agent_id or not session_id or not context:
                raise ValueError("agent_id, session_id, and context are required")

            if len(context) > self.max_memory_length:
                # Truncate context if too long
                context = context[:self.max_memory_length] + "...[truncated]"

            # Clean and normalize context
            context = self._clean_context(context)

            # Extract additional tags from content if not provided
            if tags is None:
                tags = []

            # Auto-extract tags from content
            auto_tags = self._extract_tags_from_context(context)
            tags.extend(auto_tags)

            # Remove duplicates and limit tag count
            tags = list(set(tags))[:10]  # Max 10 tags

            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl

            # Store in database
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
        """
        Recall memories with intelligent search

        Args:
            agent_id: Agent identifier
            query: Search query
            tags: Optional tag filters
            limit: Maximum number of memories to return

        Returns:
            List of relevant memories with relevance scoring
        """
        try:
            # Validate inputs
            if not agent_id:
                raise ValueError("agent_id is required")

            # Clean query
            query = self._clean_query(query)

            # Get memories from database
            memories = await agent_db.recall_memories(
                agent_id=agent_id,
                query=query,
                tags=tags,
                limit=limit * 2  # Get more to allow for relevance filtering
            )

            # Apply relevance scoring and filtering
            scored_memories = self._score_relevance(memories, query)

            # Sort by relevance score and limit results
            scored_memories.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

            # Return top results with relevance scores
            return scored_memories[:limit]

        except Exception as e:
            print(f"[ERROR] Memory recall failed: {e}")
            raise

    async def get_memory_summary(self, agent_id: str, session_id: str = None) -> Dict[str, Any]:
        """
        Get memory summary for an agent

        Args:
            agent_id: Agent identifier
            session_id: Optional session filter

        Returns:
            Memory summary statistics
        """
        try:
            # Get recent memories
            recent_memories = await agent_db.recall_memories(
                agent_id=agent_id,
                query="",
                limit=100
            )

            # Filter by session if specified
            if session_id:
                recent_memories = [m for m in recent_memories if session_id in str(m)]

            # Analyze memories
            total_memories = len(recent_memories)

            # Extract tag statistics
            all_tags = []
            for memory in recent_memories:
                all_tags.extend(memory.get('tags', []))

            tag_counts = {}
            for tag in all_tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Get top tags
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            # Calculate time span
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
        """Clean and normalize context text"""
        # Remove excessive whitespace
        context = re.sub(r'\s+', ' ', context.strip())

        # Remove potentially sensitive data patterns
        context = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', context)
        context = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CARD]', context)
        context = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', context)

        return context

    def _clean_query(self, query: str) -> str:
        """Clean and normalize search query"""
        if not query:
            return ""

        # Remove excessive whitespace and normalize
        query = re.sub(r'\s+', ' ', query.strip())

        return query

    def _extract_tags_from_context(self, context: str) -> List[str]:
        """Extract relevant tags from context content"""
        tags = []

        # Common AI/tech keywords
        ai_keywords = [
            'ai', 'machine learning', 'deep learning', 'neural network',
            'llm', 'gpt', 'claude', 'chatbot', 'nlp', 'computer vision',
            'api', 'database', 'web', 'mobile', 'cloud', 'docker'
        ]

        context_lower = context.lower()
        for keyword in ai_keywords:
            if keyword in context_lower:
                tags.append(keyword.replace(' ', '_'))

        # Extract programming languages
        languages = [
            'python', 'javascript', 'java', 'go', 'rust', 'cpp',
            'typescript', 'swift', 'kotlin', 'php', 'ruby'
        ]

        for lang in languages:
            if lang in context_lower:
                tags.append(f'lang_{lang}')

        # Extract action types
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

        return tags[:5]  # Limit auto-extracted tags

    def _score_relevance(self, memories: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """Score memories for relevance to query"""
        if not query:
            # If no query, return all memories with neutral score
            for memory in memories:
                memory['relevance_score'] = 50
            return memories

        query_terms = set(query.lower().split())

        for memory in memories:
            score = 0
            context = memory.get('context', '').lower()
            tags = [tag.lower() for tag in memory.get('tags', [])]

            # Score based on exact term matches in content
            for term in query_terms:
                # Higher weight for exact matches
                if term in context:
                    score += context.count(term) * 10

                # Medium weight for tag matches
                if term in tags:
                    score += 15

                # Lower weight for partial matches
                for word in context.split():
                    if term in word and len(term) > 2:
                        score += 3

            # Boost recent memories slightly
            try:
                created_at = datetime.fromisoformat(memory['created_at'].replace('Z', '+00:00'))
                days_old = (datetime.now(created_at.tzinfo) - created_at).days
                if days_old < 7:
                    score += 5
            except:
                pass

            # Normalize score to 0-100 range
            memory['relevance_score'] = min(100, max(0, score))

        return memories
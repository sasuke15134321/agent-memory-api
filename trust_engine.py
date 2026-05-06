#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trust Engine for AI Content Verification
Handles trust scoring, hallucination detection, and content reliability analysis
"""

import os
import asyncio
import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

from database import agent_db


class TrustEngine:
    def __init__(self):
        self.min_content_length = int(os.getenv("MIN_TRUST_CONTENT_LENGTH", "10"))
        self.max_content_length = int(os.getenv("MAX_TRUST_CONTENT_LENGTH", "50000"))

        # Hallucination indicators
        self.hallucination_patterns = [
            r'I\s+(?:saw|heard|read|found)\s+(?:on|in)\s+(?:the\s+)?(?:news|internet|website)',
            r'(?:recent|latest)\s+(?:studies|research|reports)\s+(?:show|indicate|suggest)',
            r'according\s+to\s+(?:sources|experts|studies)',
            r'it\s+was\s+(?:reported|announced|confirmed)\s+(?:yesterday|today|recently)',
            r'breaking\s+news',
            r'I\s+remember\s+(?:reading|seeing|hearing)',
        ]

        # Uncertainty indicators
        self.uncertainty_patterns = [
            r'I\s+(?:think|believe|assume|guess|suppose)',
            r'(?:maybe|perhaps|possibly|probably|likely)',
            r'(?:might|could|may)\s+be',
            r'(?:seems|appears)\s+to\s+be',
            r'(?:not\s+sure|uncertain|unclear)',
        ]

        # Confidence indicators (positive)
        self.confidence_patterns = [
            r'(?:definitely|certainly|absolutely|clearly)',
            r'(?:proven|verified|confirmed|established)',
            r'(?:fact|factual|documented|recorded)',
            r'according\s+to\s+(?:documentation|official)',
        ]

        # Suspicious claim patterns
        self.suspicious_patterns = [
            r'(?:secret|hidden|classified)\s+(?:information|data|documents)',
            r'(?:insider|exclusive)\s+(?:information|knowledge|access)',
            r'(?:government|corporate)\s+(?:conspiracy|cover-up)',
            r'(?:leaked|hacked|stolen)\s+(?:data|information|documents)',
        ]

    async def verify_trust(self, content: str, source_agent: str, context: str = "") -> Dict[str, Any]:
        """
        Verify content trust and detect potential hallucinations

        Args:
            content: Content to verify
            source_agent: Source agent identifier
            context: Additional context for verification

        Returns:
            Dictionary with trust analysis results
        """
        try:
            # Validate inputs
            if not content or not source_agent:
                raise ValueError("content and source_agent are required")

            if len(content) < self.min_content_length:
                raise ValueError(f"Content too short (minimum {self.min_content_length} characters)")

            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "...[truncated]"

            # Perform trust analysis
            analysis_result = self._analyze_content_trust(content, context)

            # Store verification result in database
            log_id = await agent_db.store_trust_verification(
                content=content,
                source_agent=source_agent,
                context=context,
                trust_score=analysis_result['trust_score'],
                hallucination_risk=analysis_result['hallucination_risk'],
                verdict=analysis_result['verdict'],
                warnings=analysis_result['warnings'],
                analysis_metadata=analysis_result['metadata']
            )

            analysis_result['verification_id'] = log_id
            analysis_result['verified_at'] = datetime.now().isoformat()

            print(f"[OK] Trust verification completed for agent {source_agent}: score={analysis_result['trust_score']}, risk={analysis_result['hallucination_risk']}")

            return analysis_result

        except Exception as e:
            print(f"[ERROR] Trust verification failed: {e}")
            raise

    def _analyze_content_trust(self, content: str, context: str = "") -> Dict[str, Any]:
        """
        Analyze content for trustworthiness and hallucination indicators

        Args:
            content: Content to analyze
            context: Additional context

        Returns:
            Analysis result dictionary
        """
        warnings = []
        trust_score = 100  # Start with perfect trust
        metadata = {}

        # Normalize content for analysis
        content_lower = content.lower()
        combined_text = f"{content} {context}".lower()

        # Check for hallucination patterns
        hallucination_score = 0
        for pattern in self.hallucination_patterns:
            matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
            if matches > 0:
                hallucination_score += matches * 15
                warnings.append(f"Potential hallucination pattern detected: {pattern[:30]}...")

        # Check for uncertainty indicators
        uncertainty_score = 0
        for pattern in self.uncertainty_patterns:
            matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
            if matches > 0:
                uncertainty_score += matches * 5
                if matches > 2:
                    warnings.append("High uncertainty language detected")

        # Check for confidence indicators (positive)
        confidence_score = 0
        for pattern in self.confidence_patterns:
            matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
            confidence_score += matches * 5

        # Check for suspicious claims
        suspicious_score = 0
        for pattern in self.suspicious_patterns:
            matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
            if matches > 0:
                suspicious_score += matches * 25
                warnings.append(f"Suspicious claim pattern detected")

        # Check for factual inconsistencies
        inconsistency_score = self._check_factual_inconsistencies(content)
        if inconsistency_score > 0:
            warnings.append("Potential factual inconsistencies detected")

        # Check for temporal inconsistencies
        temporal_score = self._check_temporal_inconsistencies(content)
        if temporal_score > 0:
            warnings.append("Temporal inconsistencies detected")

        # Calculate final trust score
        trust_score = max(0, trust_score - hallucination_score - uncertainty_score - suspicious_score - inconsistency_score - temporal_score)
        trust_score = min(100, trust_score + confidence_score)

        # Determine hallucination risk level
        if hallucination_score > 30 or suspicious_score > 20:
            risk_level = "high"
        elif hallucination_score > 15 or uncertainty_score > 20:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Determine overall verdict
        if trust_score >= 80:
            verdict = "trusted"
        elif trust_score >= 60:
            verdict = "caution"
        else:
            verdict = "unreliable"

        # Additional analysis metadata
        metadata = {
            'content_length': len(content),
            'hallucination_score': hallucination_score,
            'uncertainty_score': uncertainty_score,
            'confidence_score': confidence_score,
            'suspicious_score': suspicious_score,
            'inconsistency_score': inconsistency_score,
            'temporal_score': temporal_score,
            'analysis_version': '1.0'
        }

        return {
            'trust_score': int(trust_score),
            'hallucination_risk': risk_level,
            'verdict': verdict,
            'warnings': warnings,
            'metadata': metadata
        }

    def _check_factual_inconsistencies(self, content: str) -> int:
        """
        Check for potential factual inconsistencies in content

        Args:
            content: Content to check

        Returns:
            Inconsistency score (higher = more inconsistent)
        """
        score = 0

        # Check for conflicting statements
        contradiction_patterns = [
            (r'(\w+)\s+is\s+(\w+)', r'(\w+)\s+is\s+not\s+(\w+)'),
            (r'(\w+)\s+can\s+(\w+)', r'(\w+)\s+cannot\s+(\w+)'),
            (r'(\w+)\s+will\s+(\w+)', r'(\w+)\s+will\s+not\s+(\w+)'),
        ]

        for pos_pattern, neg_pattern in contradiction_patterns:
            pos_matches = re.findall(pos_pattern, content, re.IGNORECASE)
            neg_matches = re.findall(neg_pattern, content, re.IGNORECASE)

            for pos_match in pos_matches:
                for neg_match in neg_matches:
                    if pos_match[0].lower() == neg_match[0].lower() and pos_match[1].lower() == neg_match[1].lower():
                        score += 20

        # Check for impossible dates or numbers
        impossible_patterns = [
            r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+(?:3[2-9]|[4-9]\d)',
            r'2[5-9]\d{2}|[3-9]\d{3}',  # Years far in the future
            r'(?:temperature|temp)\s+(?:of\s+)?[-+]?\d*\.?\d+\s*[°]?[fc]?\s+(?:degrees?)?\s*(?:below\s+)?(?:absolute\s+)?zero'
        ]

        for pattern in impossible_patterns:
            matches = len(re.findall(pattern, content, re.IGNORECASE))
            score += matches * 15

        return min(50, score)  # Cap at 50 points

    def _check_temporal_inconsistencies(self, content: str) -> int:
        """
        Check for temporal inconsistencies in content

        Args:
            content: Content to check

        Returns:
            Temporal inconsistency score
        """
        score = 0

        # Extract temporal references
        temporal_patterns = [
            r'(?:yesterday|today|tomorrow)',
            r'(?:last|next)\s+(?:week|month|year)',
            r'(?:in|on)\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)',
            r'(?:19|20)\d{2}',  # Years
        ]

        temporal_refs = []
        for pattern in temporal_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            temporal_refs.extend(matches)

        # Simple check for conflicting temporal references
        if len(temporal_refs) > 1:
            # Check for past and future references in the same content
            past_indicators = ['yesterday', 'last', 'was', 'were', 'had']
            future_indicators = ['tomorrow', 'next', 'will', 'shall', 'going to']

            has_past = any(indicator in content.lower() for indicator in past_indicators)
            has_future = any(indicator in content.lower() for indicator in future_indicators)

            if has_past and has_future:
                # This could be normal, but flag if there are conflicting dates
                score += 5

        return min(20, score)  # Cap at 20 points

    async def get_trust_history(self, source_agent: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get trust verification history for an agent

        Args:
            source_agent: Source agent identifier
            limit: Maximum number of records to return

        Returns:
            List of trust verification records
        """
        try:
            # This would require a new method in the database class
            # For now, return empty list
            return []

        except Exception as e:
            print(f"[ERROR] Failed to get trust history: {e}")
            return []

    async def get_trust_statistics(self) -> Dict[str, Any]:
        """
        Get overall trust statistics

        Returns:
            Trust statistics dictionary
        """
        try:
            # This would require database aggregation queries
            # For now, return basic stats
            return {
                'total_verifications': 0,
                'average_trust_score': 0,
                'high_risk_count': 0,
                'generated_at': datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[ERROR] Failed to get trust statistics: {e}")
            return {}
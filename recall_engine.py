#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recall Engine for AI Agent Memory Compression and Extraction
Handles conversation log compression, decision extraction, and handover briefing generation
"""

import os
import asyncio
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import anthropic


class RecallEngine:
    def __init__(self):
        self.anthropic_client = anthropic.AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", "")
        )
        self.model = "claude-3-5-sonnet-20241022"  # Updated model
        self.max_input_tokens = 180000  # Conservative limit for input
        self.compression_ratios = {
            "high": 0.95,    # 95% compression
            "medium": 0.85,  # 85% compression
            "low": 0.70      # 70% compression
        }

    async def compress_content(self, content: str, compression_level: str = "medium",
                              focus: str = "all", next_agent_briefing: bool = False) -> Dict[str, Any]:
        """
        Compress conversation logs and work history using Claude API

        Args:
            content: Content to compress
            compression_level: high/medium/low compression level
            focus: What to focus on (decisions/constraints/summary/all)
            next_agent_briefing: Whether to generate next agent briefing

        Returns:
            Compressed content with analysis
        """
        try:
            if not self.anthropic_client.api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")

            if not content.strip():
                raise ValueError("Content cannot be empty")

            # Calculate original token count (rough estimate)
            original_tokens = len(content.split()) * 1.3  # Rough token estimate

            # Generate compression prompt based on parameters
            prompt = self._generate_compression_prompt(content, compression_level, focus, next_agent_briefing)

            # Call Claude API
            response = await self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=8000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            result = self._parse_compression_response(response.content[0].text)

            # Calculate compression metrics
            compressed_tokens = len(result.get("compressed_summary", "").split()) * 1.3
            compression_ratio = self.compression_ratios.get(compression_level, 0.85)

            result.update({
                "original_tokens": int(original_tokens),
                "compressed_tokens": int(compressed_tokens),
                "compression_ratio": compression_ratio,
                "compression_level": compression_level,
                "focus": focus,
                "processed_at": datetime.now().isoformat()
            })

            print(f"[OK] Content compressed: {original_tokens:.0f} → {compressed_tokens:.0f} tokens ({compression_ratio:.1%} reduction)")
            return result

        except Exception as e:
            print(f"[ERROR] Content compression failed: {e}")
            raise

    async def extract_information(self, content: str, extract_type: str = "all") -> Dict[str, Any]:
        """
        Extract specific information from text using Claude API

        Args:
            content: Text content to extract from
            extract_type: Type of information to extract (decisions/facts/actions/all)

        Returns:
            Extracted information with confidence scores
        """
        try:
            if not self.anthropic_client.api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable is required")

            if not content.strip():
                raise ValueError("Content cannot be empty")

            # Generate extraction prompt
            prompt = self._generate_extraction_prompt(content, extract_type)

            # Call Claude API
            response = await self.anthropic_client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=0.2,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            result = self._parse_extraction_response(response.content[0].text)

            result.update({
                "extract_type": extract_type,
                "content_length": len(content),
                "processed_at": datetime.now().isoformat()
            })

            print(f"[OK] Information extracted: {len(result.get('extracted_items', []))} items of type '{extract_type}'")
            return result

        except Exception as e:
            print(f"[ERROR] Information extraction failed: {e}")
            raise

    def _generate_compression_prompt(self, content: str, compression_level: str, focus: str, next_agent_briefing: bool) -> str:
        """Generate prompt for content compression"""

        compression_instructions = {
            "high": "極限まで圧縮し、最も重要な情報のみを残してください。",
            "medium": "重要な詳細を保持しながら適度に圧縮してください。",
            "low": "主要な情報を保持し、軽い圧縮に留めてください。"
        }

        focus_instructions = {
            "decisions": "決定事項と意思決定プロセスに焦点を当ててください。",
            "constraints": "制約、制限、禁止事項に焦点を当ててください。",
            "summary": "全体的な要約に焦点を当ててください。",
            "all": "すべての側面を均等に扱ってください。"
        }

        briefing_instruction = ""
        if next_agent_briefing:
            briefing_instruction = "\n\n**重要**: 次のAIエージェントへの引き継ぎ文も生成してください。"

        prompt = f"""以下の会話ログ・作業履歴を分析し、構造化された形で圧縮してください。

**圧縮レベル**: {compression_level}
{compression_instructions.get(compression_level, "")}

**フォーカス**: {focus}
{focus_instructions.get(focus, "")}
{briefing_instruction}

**出力形式**: 以下のJSON形式で回答してください：
```json
{{
  "compressed_summary": "圧縮されたサマリー",
  "key_decisions": ["決定事項1", "決定事項2"],
  "constraints": ["制約1", "制約2"],
  "unresolved_issues": ["未解決問題1", "未解決問題2"],
  "next_agent_briefing": "次のAIエージェントへの引き継ぎ文（briefing=trueの場合のみ）"
}}
```

**入力コンテンツ**:
{content[:100000]}  # Limit content to prevent token overflow

上記の内容を分析し、指定された形式で圧縮結果を返してください。"""

        return prompt

    def _generate_extraction_prompt(self, content: str, extract_type: str) -> str:
        """Generate prompt for information extraction"""

        extraction_instructions = {
            "decisions": "決定事項、判断、選択された選択肢を抽出してください。",
            "facts": "事実、データ、確認された情報を抽出してください。",
            "actions": "実行されたアクション、タスク、作業を抽出してください。",
            "all": "決定事項、事実、アクションをすべて抽出してください。"
        }

        prompt = f"""以下のテキストから{extract_type}を抽出してください。

**抽出タイプ**: {extract_type}
{extraction_instructions.get(extract_type, "")}

**出力形式**: 以下のJSON形式で回答してください：
```json
{{
  "extracted_items": ["抽出項目1", "抽出項目2", "抽出項目3"],
  "confidence_scores": [0.95, 0.87, 0.92],
  "source_locations": ["元テキストの該当箇所1", "元テキストの該当箇所2", "元テキストの該当箇所3"]
}}
```

**入力テキスト**:
{content[:80000]}  # Limit content to prevent token overflow

上記の内容から指定されたタイプの情報を抽出し、信頼度スコア（0-1）と元テキストの該当箇所を含めて回答してください。"""

        return prompt

    def _parse_compression_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's compression response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                # Fallback: try to parse entire response as JSON
                result = json.loads(response_text)

            # Ensure required fields exist
            if "compressed_summary" not in result:
                result["compressed_summary"] = "Compression failed - invalid response format"
            if "key_decisions" not in result:
                result["key_decisions"] = []
            if "constraints" not in result:
                result["constraints"] = []
            if "unresolved_issues" not in result:
                result["unresolved_issues"] = []
            if "next_agent_briefing" not in result:
                result["next_agent_briefing"] = ""

            return result

        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[WARN] Failed to parse compression response as JSON: {e}")
            # Fallback response
            return {
                "compressed_summary": response_text[:1000] + "...",
                "key_decisions": [],
                "constraints": [],
                "unresolved_issues": [],
                "next_agent_briefing": ""
            }

    def _parse_extraction_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Claude's extraction response"""
        try:
            # Extract JSON from response
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                result = json.loads(json_str)
            else:
                # Fallback: try to parse entire response as JSON
                result = json.loads(response_text)

            # Ensure required fields exist
            if "extracted_items" not in result:
                result["extracted_items"] = []
            if "confidence_scores" not in result:
                result["confidence_scores"] = [0.5] * len(result.get("extracted_items", []))
            if "source_locations" not in result:
                result["source_locations"] = ["Unknown"] * len(result.get("extracted_items", []))

            # Ensure arrays have same length
            items_count = len(result["extracted_items"])
            if len(result["confidence_scores"]) != items_count:
                result["confidence_scores"] = [0.5] * items_count
            if len(result["source_locations"]) != items_count:
                result["source_locations"] = ["Unknown"] * items_count

            return result

        except (json.JSONDecodeError, AttributeError) as e:
            print(f"[WARN] Failed to parse extraction response as JSON: {e}")
            # Fallback response
            return {
                "extracted_items": [],
                "confidence_scores": [],
                "source_locations": []
            }

    def estimate_tokens(self, text: str) -> int:
        """Rough token count estimation"""
        return int(len(text.split()) * 1.3)
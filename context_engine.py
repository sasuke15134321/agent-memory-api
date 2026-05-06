#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Engine for AI Agent Context Management
Handles context packaging, handover, and project state summarization
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import json
import hashlib
from datetime import datetime, timedelta

from database import agent_db


class ContextEngine:
    def __init__(self):
        self.max_package_size = int(os.getenv("MAX_CONTEXT_PACKAGE_SIZE", "100000"))  # Max characters
        self.default_package_ttl = int(os.getenv("DEFAULT_PACKAGE_TTL", "604800"))  # 7 days

        # Context summary templates
        self.summary_templates = {
            "brief": {
                "max_items": 5,
                "max_description_length": 100,
                "include_technical_details": False
            },
            "detailed": {
                "max_items": 15,
                "max_description_length": 300,
                "include_technical_details": True
            },
            "comprehensive": {
                "max_items": 50,
                "max_description_length": 500,
                "include_technical_details": True
            }
        }

    async def create_package(self, project_id: str, include_memories: bool = True,
                           summary_level: str = "detailed") -> Dict[str, Any]:
        """
        Create a context handover package for a project

        Args:
            project_id: Project identifier
            include_memories: Whether to include agent memories
            summary_level: Level of detail (brief, detailed, comprehensive)

        Returns:
            Context package dictionary
        """
        try:
            # Validate inputs
            if not project_id:
                raise ValueError("project_id is required")

            if summary_level not in self.summary_templates:
                raise ValueError(f"Invalid summary_level: {summary_level}")

            # Get template configuration
            template = self.summary_templates[summary_level]

            # Initialize package structure
            package = {
                "project_id": project_id,
                "summary_level": summary_level,
                "created_at": datetime.now().isoformat(),
                "package_version": "1.0",
                "sections": {}
            }

            # Add project overview
            package["sections"]["project_overview"] = await self._generate_project_overview(
                project_id, template
            )

            # Add agent memories if requested
            memory_count = 0
            if include_memories:
                memories_section, memory_count = await self._generate_memories_section(
                    project_id, template
                )
                package["sections"]["memories"] = memories_section

            # Add technical context
            package["sections"]["technical_context"] = await self._generate_technical_context(
                project_id, template
            )

            # Add project timeline
            package["sections"]["timeline"] = await self._generate_timeline_section(
                project_id, template
            )

            # Add handover notes
            package["sections"]["handover_notes"] = await self._generate_handover_notes(
                project_id, template
            )

            # Add package metadata
            package["metadata"] = {
                "total_sections": len(package["sections"]),
                "memory_count": memory_count,
                "package_size_chars": len(json.dumps(package)),
                "generation_method": "automated",
                "includes_memories": include_memories
            }

            # Validate package size
            package_json = json.dumps(package)
            if len(package_json) > self.max_package_size:
                # Truncate package if too large
                package = await self._truncate_package(package, self.max_package_size)
                package["metadata"]["truncated"] = True

            # Store package in database
            package_id = await agent_db.store_context_package(
                project_id=project_id,
                summary_level=summary_level,
                package_data=package,
                memory_count=memory_count,
                ttl=self.default_package_ttl
            )

            package["package_id"] = package_id

            print(f"[OK] Context package created for project {project_id}: {package_id}")
            return package

        except Exception as e:
            print(f"[ERROR] Context package creation failed: {e}")
            raise

    async def _generate_project_overview(self, project_id: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """Generate project overview section"""
        return {
            "project_id": project_id,
            "description": f"Project {project_id} context overview generated automatically",
            "key_objectives": [
                "Maintain project continuity",
                "Preserve important context",
                "Enable smooth handover"
            ],
            "current_status": "active",
            "priority_level": "medium",
            "stakeholders": ["AI Agent System"],
            "last_updated": datetime.now().isoformat()
        }

    async def _generate_memories_section(self, project_id: str, template: Dict[str, Any]) -> tuple:
        """Generate memories section and return section data with count"""
        try:
            # Try to get memories related to this project
            # This is a simplified approach - in practice you'd search for project-related memories
            memories = await agent_db.recall_memories(
                agent_id=f"project_{project_id}",
                query="",
                limit=template["max_items"]
            )

            # Format memories for package
            formatted_memories = []
            for memory in memories[:template["max_items"]]:
                memory_item = {
                    "memory_id": memory.get("memory_id", ""),
                    "context": self._truncate_text(
                        memory.get("context", ""),
                        template["max_description_length"]
                    ),
                    "tags": memory.get("tags", []),
                    "created_at": memory.get("created_at", ""),
                    "relevance": "high"  # Simplified relevance assessment
                }
                formatted_memories.append(memory_item)

            memories_section = {
                "total_memories": len(formatted_memories),
                "included_memories": formatted_memories,
                "selection_criteria": f"Recent memories related to project {project_id}",
                "last_updated": datetime.now().isoformat()
            }

            return memories_section, len(formatted_memories)

        except Exception as e:
            print(f"[WARN] Could not retrieve memories for project {project_id}: {e}")
            return {
                "total_memories": 0,
                "included_memories": [],
                "selection_criteria": "No memories available",
                "error": str(e)
            }, 0

    async def _generate_technical_context(self, project_id: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """Generate technical context section"""
        context = {
            "architecture_notes": [],
            "dependencies": [],
            "configuration": {},
            "deployment_info": {},
        }

        if template["include_technical_details"]:
            context.update({
                "code_structure": {
                    "description": "Project follows standard architecture patterns",
                    "key_components": [
                        "API endpoints",
                        "Database layer",
                        "Business logic",
                        "Authentication"
                    ]
                },
                "environment_variables": {
                    "required": [
                        "DATABASE_URL",
                        "API_KEYS",
                        "WALLET_ADDRESS"
                    ],
                    "optional": [
                        "TEST_MODE",
                        "DEBUG_MODE"
                    ]
                },
                "external_services": [
                    "PostgreSQL Database",
                    "Claude API",
                    "x402 Payment Protocol"
                ]
            })

        return context

    async def _generate_timeline_section(self, project_id: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """Generate project timeline section"""
        return {
            "milestones": [
                {
                    "date": datetime.now().isoformat(),
                    "event": "Context package generation",
                    "type": "system",
                    "description": "Automated context package created for project handover"
                }
            ],
            "recent_activities": [],
            "upcoming_deadlines": [],
            "timeline_generated_at": datetime.now().isoformat()
        }

    async def _generate_handover_notes(self, project_id: str, template: Dict[str, Any]) -> Dict[str, Any]:
        """Generate handover notes section"""
        return {
            "critical_information": [
                "Review project overview and technical context",
                "Check environment configuration",
                "Verify database connections",
                "Test API endpoints"
            ],
            "known_issues": [],
            "recommendations": [
                "Monitor system health",
                "Regular database backups",
                "Keep dependencies updated",
                "Review security configurations"
            ],
            "contact_information": {},
            "handover_checklist": [
                {
                    "item": "Review context package",
                    "completed": False,
                    "priority": "high"
                },
                {
                    "item": "Verify system access",
                    "completed": False,
                    "priority": "high"
                },
                {
                    "item": "Test core functionality",
                    "completed": False,
                    "priority": "medium"
                }
            ]
        }

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length"""
        if len(text) <= max_length:
            return text
        return text[:max_length - 3] + "..."

    async def _truncate_package(self, package: Dict[str, Any], max_size: int) -> Dict[str, Any]:
        """Truncate package to fit within size limits"""
        # This is a simplified truncation - in practice you'd prioritize sections
        package_copy = package.copy()

        # Remove less critical sections if needed
        sections_to_trim = ["memories", "timeline", "handover_notes"]

        for section in sections_to_trim:
            if len(json.dumps(package_copy)) <= max_size:
                break

            if section in package_copy.get("sections", {}):
                # Reduce content in this section
                if section == "memories" and "included_memories" in package_copy["sections"][section]:
                    # Reduce number of memories
                    memories = package_copy["sections"][section]["included_memories"]
                    package_copy["sections"][section]["included_memories"] = memories[:max(1, len(memories) // 2)]

        return package_copy

    async def get_package_by_id(self, package_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a context package by ID

        Args:
            package_id: Package identifier

        Returns:
            Context package or None if not found
        """
        try:
            # This would require implementing a get_context_package method in the database
            # For now, return None
            return None

        except Exception as e:
            print(f"[ERROR] Failed to retrieve package {package_id}: {e}")
            return None

    async def list_packages_for_project(self, project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List context packages for a project

        Args:
            project_id: Project identifier
            limit: Maximum number of packages to return

        Returns:
            List of package metadata
        """
        try:
            # This would require implementing a list_context_packages method in the database
            # For now, return empty list
            return []

        except Exception as e:
            print(f"[ERROR] Failed to list packages for project {project_id}: {e}")
            return []
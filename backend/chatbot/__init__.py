"""
Core chatbot modules.

This package contains:
- conversation_manager: Conversation flow and context management
- knowledge_base: Knowledge retrieval from data sources
- agents: Conversational agent definitions
- prompt_builder: RAG prompt construction
"""

from .conversation_manager import process_conversation, detect_intent
from .knowledge_base import KnowledgeBase

__all__ = [
    "process_conversation",
    "detect_intent",
    "KnowledgeBase",
]

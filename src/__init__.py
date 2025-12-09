"""
Modules package for FAIX AI Chatbot.

Exports key functions/classes for easy imports.
"""
from .conversation_manager import process_conversation, detect_intent
from .knowledge_base import KnowledgeBase

__all__ = [
    "process_conversation",
    "detect_intent",
    "KnowledgeBase",
]

"""
Basic tests for agent registry and prompt building (no external LLM calls).
"""

import sys
from pathlib import Path
import types

import pytest

ROOT = Path(__file__).parent.parent
# Put the project root on sys.path (NOT src/)
sys.path.insert(0, str(ROOT))

# For these tests we don't need a real Django environment, but src.knowledge_base
# imports django at module import time. Install a lightweight stub so that import
# succeeds and KnowledgeBase falls back to non-Django mode.
sys.modules["django"] = types.ModuleType("django")

from backend.chatbot.agents import get_agent_registry, retrieve_for_agent  # noqa: E402
from backend.chatbot.prompt_builder import build_messages  # noqa: E402
from backend.chatbot.knowledge_base import KnowledgeBase  # noqa: E402


class DummyKnowledgeBase(KnowledgeBase):
    """Small in-memory KB stub for testing get_documents + retrieve_for_agent."""

    def __init__(self):
        # Bypass parent init to avoid Django/CSV setup
        self.use_database = False
        self.csv_path = None
        self.use_semantic_search = False
        self.semantic_search = None
        # Minimal attributes used by get_documents in CSV mode
        import pandas as pd

        self.df = pd.DataFrame(
            [
                {
                    "question": "When does the semester start?",
                    "answer": "The semester starts in September.",
                    "category": "academic_schedule",
                    "keywords": [],
                },
                {
                    "question": "How do I register for courses?",
                    "answer": "You can register via the student portal.",
                    "category": "registration",
                    "keywords": [],
                },
            ]
        )
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vectorizer = TfidfVectorizer()
        clean_questions = self.df["question"]
        self.question_vectors = self.vectorizer.fit_transform(clean_questions)


def test_agent_registry_has_default_agents():
    registry = get_agent_registry()
    agents = {a.id for a in registry.list_agents()}
    assert "faq" in agents
    assert "schedule" in agents
    assert "staff" in agents


def test_retrieve_for_faq_agent_uses_kb():
    kb = DummyKnowledgeBase()
    context = retrieve_for_agent(
        agent_id="faq",
        user_text="When is the semester starting?",
        knowledge_base=kb,
        intent="academic_schedule",
        top_k=2,
    )
    assert "faq" in context
    docs = context["faq"]
    assert len(docs) >= 1
    assert any("semester" in d["question"].lower() for d in docs)


def test_build_messages_includes_system_and_user_and_context():
    registry = get_agent_registry()
    agent = registry.get("faq")
    assert agent is not None

    faq_docs = [
        {
            "question": "What are the registration deadlines?",
            "answer": "Registration closes on August 31.",
            "category": "registration",
            "score": 0.9,
        }
    ]
    context = {"faq": faq_docs}
    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]

    messages = build_messages(
        agent=agent,
        user_message="When is the registration deadline?",
        history=history,
        context=context,
        intent="registration",
    )

    # Basic shape assertions
    assert messages[0]["role"] == "system"
    # There should be a synthetic assistant message with context
    assert any(
        m["role"] == "assistant" and "FAQ Context" in m["content"] for m in messages
    )
    # Last message should be the latest user input
    assert messages[-1]["role"] == "user"
    assert "registration deadline" in messages[-1]["content"].lower()



"""
Prompt building utilities for conversational agents.

Converts agent definitions, user input, conversation history and retrieved
documents into an OpenAI-style list of chat messages suitable for LLMClient.
"""

from typing import List, Dict, Any, Optional

from .agents import Agent


def _format_faq_context(faq_docs: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for i, doc in enumerate(faq_docs, start=1):
        q = doc.get("question", "")
        a = doc.get("answer", "")
        if not q and not a:
            continue
        lines.append(f"FAQ {i}:")
        if q:
            lines.append(f"Q: {q}")
        if a:
            lines.append(f"A: {a}")
        lines.append("")
    return "\n".join(lines).strip()


def _format_schedule_context(schedule_docs: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for item in schedule_docs:
        title = item.get("title") or item.get("name") or ""
        desc = item.get("description", "")
        time = item.get("time", "")
        parts = []
        if title:
            parts.append(title)
        if time:
            parts.append(f"Time: {time}")
        if desc:
            parts.append(desc)
        if parts:
            lines.append(" - " + " | ".join(parts))
    return "\n".join(lines).strip()


def _format_staff_context(staff_docs: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for person in staff_docs:
        name = person.get("name", "")
        role = person.get("role", "")
        email = person.get("email", "")
        phone = person.get("phone", "")
        office = person.get("office", "")
        department = person.get("department", "")
        specialization = person.get("specialization", "")
        
        parts = []
        if name:
            parts.append(name)
        if role:
            parts.append(f"Position: {role}")
        if department:
            parts.append(f"Department: {department}")
        if specialization:
            parts.append(f"Specialization: {specialization}")
        if email:
            parts.append(f"Email: {email}")
        if phone and phone != "-":
            parts.append(f"Phone: {phone}")
        if office and office != "-":
            parts.append(f"Office: {office}")
        
        if parts:
            lines.append(" - " + " | ".join(parts))
    return "\n".join(lines).strip()


def build_messages(
    agent: Agent,
    user_message: str,
    history: Optional[List[Dict[str, str]]],
    context: Dict[str, List[Dict]],
    intent: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Build messages for the LLM client.

    Args:
        agent: The conversational agent definition.
        user_message: The latest user message.
        history: Conversation history as a list of {role, content} dicts.
        context: Retrieved documents grouped by source key (faq/schedule/staff).
        intent: Optional detected intent string for additional guidance.
    """
    messages: List[Dict[str, str]] = []

    # System message with agent behaviour and RAG instructions
    system_parts: List[str] = [agent.system_prompt]
    if intent:
        system_parts.append(f"The detected intent for this query is: '{intent}'.")
    system_parts.append(
        "Use the provided context sections when answering. "
        "If the answer is not clearly supported by the context, say you are "
        "not sure and suggest contacting the FAIX office."
    )
    # Add reminder for staff queries to keep it short
    if agent.id == "staff":
        system_parts.append(
            "REMINDER: Show ONLY staff names first (bullet list, 3-5 max). "
            "Then ask if the user needs contact information. "
            "Only provide full details (email, phone, office) when specifically requested."
        )
    system_content = "\n\n".join(system_parts)
    messages.append({"role": "system", "content": system_content})

    # Inject a synthetic assistant message that contains context the model can cite
    context_lines: List[str] = []
    faq_docs = context.get("faq") or []
    if faq_docs:
        faq_text = _format_faq_context(faq_docs)
        if faq_text:
            context_lines.append("--- FAQ Context ---")
            context_lines.append(faq_text)

    schedule_docs = context.get("schedule") or []
    if schedule_docs:
        schedule_text = _format_schedule_context(schedule_docs)
        if schedule_text:
            context_lines.append("--- Schedule Context ---")
            context_lines.append(schedule_text)

    staff_docs = context.get("staff") or []
    if staff_docs:
        staff_text = _format_staff_context(staff_docs)
        if staff_text:
            context_lines.append("--- Staff Contacts Context ---")
            context_lines.append(staff_text)

    if context_lines:
        messages.append(
            {
                "role": "assistant",
                "content": "Here is reference context you can use:\n\n"
                + "\n".join(context_lines),
            }
        )

    # Conversation history (if any) to preserve dialog flow
    if history:
        for turn in history:
            role = turn.get("role")
            content = turn.get("content")
            if role in ("user", "assistant") and isinstance(content, str) and content:
                messages.append({"role": role, "content": content})

    # Latest user message
    messages.append({"role": "user", "content": user_message})

    return messages



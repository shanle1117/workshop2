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


def _format_faix_data_context(faix_data: Dict[str, Any]) -> str:
    """Format FAIX comprehensive data into readable context."""
    lines: List[str] = []
    
    # Faculty Information
    if "faculty_info" in faix_data:
        info = faix_data["faculty_info"]
        lines.append("=== FACULTY INFORMATION ===")
        if info.get("name"):
            lines.append(f"Name: {info['name']}")
        if info.get("university"):
            lines.append(f"University: {info['university']}")
        if info.get("dean"):
            lines.append(f"Dean: {info['dean']}")
        if info.get("established"):
            lines.append(f"Established: {info['established']}")
        if info.get("contact"):
            contact = info["contact"]
            if contact.get("email"):
                lines.append(f"Email: {contact['email']}")
            if contact.get("phone"):
                lines.append(f"Phone: {contact['phone']}")
            if contact.get("website"):
                lines.append(f"Website: {contact['website']}")
        lines.append("")
    
    # Vision & Mission
    if "vision_mission" in faix_data:
        vm = faix_data["vision_mission"]
        lines.append("=== VISION & MISSION ===")
        if vm.get("vision"):
            lines.append(f"Vision: {vm['vision']}")
        if vm.get("mission"):
            lines.append(f"Mission: {vm['mission']}")
        if vm.get("objectives") and isinstance(vm["objectives"], list):
            lines.append("Objectives:")
            for obj in vm["objectives"]:
                lines.append(f"  • {obj}")
        lines.append("")
    
    # Programmes
    if "programmes" in faix_data:
        programs = faix_data["programmes"]
        lines.append("=== PROGRAMMES ===")
        
        # Undergraduate
        if "undergraduate" in programs and isinstance(programs["undergraduate"], list):
            lines.append("Undergraduate Programs:")
            for prog in programs["undergraduate"]:
                if prog.get("name"):
                    lines.append(f"  • {prog['name']} ({prog.get('code', 'N/A')})")
                    if prog.get("duration"):
                        lines.append(f"    Duration: {prog['duration']}")
                    if prog.get("focus_areas") and isinstance(prog["focus_areas"], list):
                        lines.append(f"    Focus Areas: {', '.join(prog['focus_areas'][:5])}")
            lines.append("")
        
        # Postgraduate
        if "postgraduate" in programs and isinstance(programs["postgraduate"], list):
            lines.append("Postgraduate Programs:")
            for prog in programs["postgraduate"]:
                if prog.get("name"):
                    lines.append(f"  • {prog['name']} ({prog.get('code', 'N/A')})")
                    if prog.get("type"):
                        lines.append(f"    Type: {prog['type']}")
            lines.append("")
    
    # Admission
    if "admission" in faix_data:
        admission = faix_data["admission"]
        lines.append("=== ADMISSION INFORMATION ===")
        
        if "postgraduate" in admission and "entry_requirements" in admission["postgraduate"]:
            lines.append("Postgraduate Entry Requirements:")
            for req in admission["postgraduate"]["entry_requirements"]:
                if isinstance(req, dict):
                    lines.append(f"  • {req.get('category', '')}: {req.get('requirement', '')}")
            if "language_requirements" in admission["postgraduate"]:
                lang_req = admission["postgraduate"]["language_requirements"]
                lines.append(f"  • Language: MUET {lang_req.get('muet', 'N/A')} or CEFR {lang_req.get('cefr', 'N/A')}")
        lines.append("")
    
    # Departments
    if "departments" in faix_data and isinstance(faix_data["departments"], list):
        lines.append("=== DEPARTMENTS ===")
        for dept in faix_data["departments"]:
            if isinstance(dept, dict) and dept.get("name"):
                lines.append(f"  • {dept['name']}")
                if dept.get("focus"):
                    lines.append(f"    Focus: {dept['focus']}")
        lines.append("")
    
    # Facilities
    if "facilities" in faix_data:
        facilities = faix_data["facilities"]
        if "available" in facilities and isinstance(facilities["available"], list):
            lines.append("=== FACILITIES ===")
            for facility in facilities["available"]:
                lines.append(f"  • {facility}")
            if facilities.get("booking_system"):
                lines.append(f"Booking System: {facilities['booking_system']}")
            lines.append("")
    
    # Academic Resources
    if "academic_resources" in faix_data:
        resources = faix_data["academic_resources"]
        lines.append("=== ACADEMIC RESOURCES ===")
        if resources.get("ulearn_portal"):
            lines.append(f"uLearn Portal: {resources['ulearn_portal']}")
        if resources.get("resources") and isinstance(resources["resources"], list):
            lines.append("Available Resources:")
            for res in resources["resources"]:
                lines.append(f"  • {res}")
        lines.append("")
    
    # Key Highlights
    if "key_highlights" in faix_data and isinstance(faix_data["key_highlights"], list):
        lines.append("=== KEY HIGHLIGHTS ===")
        for highlight in faix_data["key_highlights"]:
            lines.append(f"  • {highlight}")
        lines.append("")
    
    # Research Focus
    if "research_focus" in faix_data and isinstance(faix_data["research_focus"], list):
        lines.append("=== RESEARCH FOCUS ===")
        for focus in faix_data["research_focus"]:
            lines.append(f"  • {focus}")
        lines.append("")
    
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
        "Use the provided context sections when answering. Format your response with proper "
        "line breaks (\\n) between paragraphs and sections. Summarize information clearly "
        "and use bullet points with line breaks for lists. Ensure your response is well-formatted "
        "and easy to read.\n\n"
        "IMPORTANT: Always preserve and include URLs/links from the context in your response, "
        "especially for fee schedules, official resources, or payment information. Links should "
        "be displayed as clickable URLs.\n\n"
        "If the answer is not clearly supported by the context, say you are "
        "not sure and suggest contacting the FAIX office."
    )
    # Add reminder for staff queries to keep it short
    if agent.id == "staff":
        system_parts.append(
            "REMINDER: Show ONLY staff names first (bullet list, 3-5 max), each on a new line. "
            "Then ask if the user needs contact information. "
            "Only provide full details (email, phone, office) when specifically requested, "
            "and format them with line breaks between each detail."
        )
    
    # Add reminder for fee queries - keep it simple, just provide the link
    if intent == 'fees' or any(kw in (user_message.lower() if isinstance(user_message, str) else '') for kw in ['fee', 'fees', 'tuition', 'yuran', 'diploma fee', 'degree fee']):
        system_parts.append(
            "IMPORTANT: This is a fee-related query. Provide ONLY the fee schedule link from the context. "
            "Do not add extra explanations. Just provide the URL: https://bendahari.utem.edu.my/ms/jadual-yuran-pelajar.html"
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

    # FAIX comprehensive data context (programs, admission, facilities, etc.)
    faix_data = context.get("faix_data")
    if faix_data:
        faix_text = _format_faix_data_context(faix_data)
        if faix_text:
            context_lines.append("--- FAIX Information Context ---")
            context_lines.append(faix_text)

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



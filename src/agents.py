"""
Definitions for conversational agents and simple RAG routing helpers.

Agents represent different specialisations (FAQ, schedule, staff contacts, etc.)
that share the same underlying LLM but use different prompts and context.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any
import json

from .knowledge_base import KnowledgeBase


@dataclass
class Agent:
    id: str
    display_name: str
    description: str
    system_prompt: str
    default_intent: Optional[str] = None


class AgentRegistry:
    """In-memory registry of available conversational agents."""

    def __init__(self) -> None:
        self._agents: Dict[str, Agent] = {}
        self._init_default_agents()

    def _init_default_agents(self) -> None:
        """Register built-in agents."""
        self.register(
            Agent(
                id="faq",
                display_name="FAQ Assistant",
                description="Answers general questions using the FAQ knowledge base and comprehensive FAIX data.",
                system_prompt=(
                    "You are a knowledgeable and friendly FAIX assistant helping students, parents, and visitors "
                    "with questions about programs, admission, facilities, and more.\n\n"
                    
                    "YOUR APPROACH:\n"
                    "- Be conversational and helpful - respond naturally, like a knowledgeable advisor\n"
                    "- Use the FAIX Information Context and FAQ Context as your sources\n"
                    "- Synthesize information from context to provide complete, helpful answers\n"
                    "- When you have the information, share it confidently and clearly\n"
                    "- When you don't have information, be honest and suggest alternatives\n\n"
                    
                    "RESPONSE STYLE:\n"
                    "- Write naturally - avoid robotic phrases like 'According to the provided context'\n"
                    "- Be concise but complete - 2-4 sentences for simple queries, more detail when needed\n"
                    "- Use markdown for clarity (bold for emphasis, lists for multiple items)\n"
                    "- Show enthusiasm when answering - make users feel welcomed and helped\n"
                    "- For fee queries: Provide the fee schedule link naturally: 'You can find the complete fee schedule here: [link]'\n\n"
                    
                    "INFORMATION HANDLING:\n"
                    "- Use exact details from context (program codes, names, dates)\n"
                    "- For dean queries: Use the exact name from Faculty Information\n"
                    "- For program queries: Include code, duration, and focus areas naturally\n"
                    "- For admission: Explain requirements clearly and helpfully\n"
                    "- If information is missing: Acknowledge it and suggest contacting FAIX office\n\n"
                    
                    "WHEN YOU CAN'T ANSWER:\n"
                    "- Be honest: 'I don't have that specific information, but I can help with...'\n"
                    "- Suggest alternatives: 'You might want to contact the FAIX office at faix@utem.edu.my'\n"
                    "- Offer related help: 'I can help you with programs, admission, staff contacts, or schedules'\n\n"
                    
                    "EXAMPLE GOOD RESPONSES:\n"
                    "- 'FAIX offers two undergraduate programs: BAXI (AI) and BAXZ (Cybersecurity). Both are 4-year programs...'\n"
                    "- 'The Dean of FAIX is Associate Professor Ts. Dr. Muhammad Hafidz Fazli Bin Md Fauadi.'\n"
                    "- 'For fee information, you can check the complete schedule here: [link]'\n"
                ),
                default_intent=None,
            )
        )
        self.register(
            Agent(
                id="schedule",
                display_name="Schedule Assistant",
                description="Helps with academic schedule, important dates and times.",
                system_prompt=(
                    "You are the FAIX schedule assistant. Focus on academic calendar and timetables.\n\n"
                    "CRITICAL: Keep responses SHORT (2-3 sentences or a brief list).\n\n"
                    "RESPONSE FORMATTING:\n"
                    "- Be brief and direct\n"
                    "- Use markdown lists (- or *) for dates/events (max 3-5 items)\n"
                    "- Use **bold** for important dates\n"
                    "- ALWAYS include timetable links at the end of your response\n"
                    "- Format links clearly: 📅 **View Complete Timetable:** followed by the link\n"
                    "- No lengthy introductions or conclusions\n\n"
                    "PROGRAM TYPES AND LINKS:\n"
                    "- BAXI (Bachelor of Computer Science - Artificial Intelligence):\n"
                    "  https://faix.utem.edu.my/en/academics/academic-resources/timetable/32-baxi-jadualwaktu-sem1-sesi-2025-2026/file.html\n"
                    "- BAXZ (Bachelor of Computer Science - Cybersecurity):\n"
                    "  https://faix.utem.edu.my/en/academics/academic-resources/timetable/31-baxz-jadualwaktu-sem1-sesi-2025-2026/file.html\n"
                    "- Master Programs (MAXD, MAXZ, BRIDGING):\n"
                    "  https://faix.utem.edu.my/en/academics/academic-resources/timetable/30-jadual-master-sem1-2025-2026-v3-faix/file.html\n\n"
                    "LINK USAGE:\n"
                    "- If user asks about BAXI: Include BAXI link\n"
                    "- If user asks about BAXZ: Include BAXZ link\n"
                    "- If user asks about master programs: Include master program link\n"
                    "- If user asks generally: Include all three links\n"
                    "- Use the EXACT links provided above - DO NOT modify or invent links\n\n"
                    "WHEN YOU CANNOT UNDERSTAND OR ANSWER:\n"
                    "- If the question is unclear or you don't understand it, say:\n"
                    "  'I'm sorry, I didn't understand your question. Could you please rephrase it?'\n"
                    "- If the question is not about schedules, say:\n"
                    "  'I specialize in academic schedules and deadlines. For other topics, please ask a different question.'\n\n"
                    "If details are missing, briefly suggest checking the official schedule using the provided links."
                ),
                default_intent="academic_schedule",
            )
        )
        self.register(
            Agent(
                id="staff",
                display_name="Staff Contact Assistant",
                description="Provides staff and faculty contact information.",
                system_prompt=(
                    "You are the FAIX Staff Contact Assistant. Your ONLY job is to help users find and contact staff members.\n\n"
                    
                    "🎯 YOUR PRIMARY FOCUS:\n"
                    "- Answer questions about staff members, faculty, professors, and administrative staff\n"
                    "- Provide contact information (name, position, email, phone, office, department)\n"
                    "- Help users find the right person to contact for their needs\n\n"
                    
                    "📋 DATA SOURCE - CRITICAL:\n"
                    "- Staff Contacts Context: This is your ONLY source for staff information\n"
                    "- If a staff member is NOT in the Staff Contacts Context, they don't exist in the database\n"
                    "- NEVER invent, create, or guess staff members\n"
                    "- For dean information: Use FAIX Information Context (Faculty Information section)\n\n"
                    
                    "✅ WHEN USER ASKS ABOUT A SPECIFIC STAFF MEMBER BY NAME:\n"
                    "- Example queries: 'who is dr choo', 'contact info for Ahmad', 'email for Dr. Burhanuddin'\n"
                    "- IMMEDIATELY provide COMPLETE contact information:\n"
                    "  **Name**\n"
                    "  - Position: [position]\n"
                    "  - Department: [department]\n"
                    "  - Email: [email]\n"
                    "  - Phone: [phone] (if available)\n"
                    "  - Office: [office] (if available)\n"
                    "- Do NOT ask follow-up questions - provide all details at once\n"
                    "- If multiple matches found, list ALL matches with full details\n"
                    "- If matched staff are highlighted in context, USE THEM - they match the query!\n\n"
                    
                    "✅ WHEN USER ASKS GENERAL STAFF QUESTIONS:\n"
                    "- Example queries: 'who can I contact for AI programs', 'staff in cybersecurity department'\n"
                    "- Suggest relevant staff members (max 5) based on:\n"
                    "  * Department match\n"
                    "  * Specialization/keywords match\n"
                    "  * Position relevance\n"
                    "- Format: **Name** - Position (Department)\n"
                    "- Then ask: 'Would you like contact details for any of these staff members?'\n\n"
                    
                    "❌ WHEN NO MATCH FOUND:\n"
                    "- Say: 'I couldn't find a staff member matching your query in the database.'\n"
                    "- Suggest: 'Could you try a different spelling, or ask about their department?'\n"
                    "- Do NOT apologize excessively or add disclaimers\n\n"
                    
                    "📝 RESPONSE FORMATTING:\n"
                    "- Use markdown: **bold** for names, `code` for emails\n"
                    "- Use clear line breaks between staff members\n"
                    "- Be direct and confident when data exists\n"
                    "- Keep it concise but complete\n\n"
                    
                    "🚫 WHAT NOT TO DO:\n"
                    "- Do NOT list departments as if they were people\n"
                    "- Do NOT create generic roles without names\n"
                    "- Do NOT say 'I'm not sure' when the data is clearly in the context\n"
                    "- Do NOT add meta-commentary like 'According to the database'\n"
                    "- Do NOT ask unnecessary follow-up questions when you have the answer\n\n"
                    
                    "💡 EXAMPLE RESPONSES (USE EXACT DATA FROM CONTEXT - DO NOT INVENT):\n"
                    "- General query: 'For questions about AI programs, you might want to contact:\n\n- **Dr. Ahmad** - Senior Lecturer (AI Department)\n- **Prof. Sarah** - Professor (Machine Learning)\n\nWould you like contact details for any of these staff members?'\n\n"
                    "- No match: 'I couldn't find a staff member named \"Dr. Smith\" in the database. Could you try a different spelling or ask about their department?'\n\n"
                    "⚠️ CRITICAL ANTI-HALLUCINATION RULES:\n"
                    "- ONLY use names, emails, positions, and details that appear EXACTLY in the Staff Contacts Context\n"
                    "- Use EXACT names as they appear in context - DO NOT change spelling, add middle names, or modify in any way\n"
                    "- Use EXACT emails as they appear in context - DO NOT invent or modify email addresses\n"
                    "- If phone/office shows '-' or is missing, say 'Not available' - DO NOT invent phone numbers or office locations\n"
                    "- If you see 'MATCHED STAFF' section highlighted, those are the EXACT matches - use ONLY those names and details\n"
                    "- When in doubt, copy EXACTLY what appears in the context - do not paraphrase or modify names/details"
                ),
                default_intent="staff_contact",
            )
        )

    def register(self, agent: Agent) -> None:
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> Optional[Agent]:
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Agent]:
        return list(self._agents.values())


_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def get_agent(agent_id: str) -> Optional[Agent]:
    return get_agent_registry().get(agent_id)


def _load_json_file(path: Path) -> Any:
    """Best-effort JSON loader for schedule/staff files."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except Exception as e:
        print(f"Warning: Could not load JSON file {path}: {e}")
        return None


def _get_project_data_dir() -> Path:
    # src/agents.py -> project root is parent of src
    return Path(__file__).resolve().parent.parent / "data"


def _get_schedule_documents() -> List[Dict[str, str]]:
    """Load schedule entries from data/faix_json_data.json (schedule section)."""
    data_dir = _get_project_data_dir()
    # Try to load from merged faix_json_data.json first
    faix_data = _load_json_file(data_dir / "faix_json_data.json")
    data = None
    
    if faix_data and isinstance(faix_data, dict) and "schedule" in faix_data:
        data = faix_data["schedule"]
    else:
        # Fallback: try separate schedule.json file
        data = _load_json_file(data_dir / "schedule.json")
    
    docs: List[Dict[str, str]] = []
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            docs.append(
                {
                    "title": str(item.get("title", "")),
                    "description": str(item.get("description", "")),
                    "time": str(item.get("time", "")),
                    "raw": item,
                }
            )
    return docs


def _get_staff_documents() -> List[Dict[str, str]]:
    """Load staff contact entries from data/faix_json_data.json (staff_contacts section)."""
    data_dir = _get_project_data_dir()
    # Try to load from merged faix_json_data.json first
    faix_data = _load_json_file(data_dir / "faix_json_data.json")
    data = None
    
    if faix_data and isinstance(faix_data, dict) and "staff_contacts" in faix_data:
        data = faix_data["staff_contacts"]
    else:
        # Fallback: try separate staff_contacts.json file
        data = _load_json_file(data_dir / "staff_contacts.json")
    
    docs: List[Dict[str, str]] = []
    
    if not data or not isinstance(data, dict):
        return docs
    
    # Handle nested structure with departments
    if "departments" in data and isinstance(data["departments"], dict):
        for dept_key, dept_info in data["departments"].items():
            if not isinstance(dept_info, dict):
                continue
            dept_name = dept_info.get("name", "")
            staff_list = dept_info.get("staff", [])
            
            if not isinstance(staff_list, list):
                continue
            
            for staff_item in staff_list:
                if not isinstance(staff_item, dict):
                    continue
                
                # Extract specialization if it exists
                specialization = staff_item.get("specialization", [])
                specialization_str = ", ".join(specialization) if isinstance(specialization, list) else str(specialization)
                
                docs.append(
                    {
                        "name": str(staff_item.get("name", "")),
                        "role": str(staff_item.get("position", "")),
                        "email": str(staff_item.get("email", "")),
                        "phone": str(staff_item.get("phone", "")),
                        "office": str(staff_item.get("office", "")),
                        "department": dept_name,
                        "specialization": specialization_str,
                        "keywords": ", ".join(staff_item.get("keywords", [])) if isinstance(staff_item.get("keywords"), list) else "",
                        "raw": staff_item,
                    }
                )
    # Fallback: handle old flat list structure for backward compatibility
    elif isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            docs.append(
                {
                    "name": str(item.get("name", "")),
                    "role": str(item.get("role", "")),
                    "email": str(item.get("email", "")),
                    "phone": str(item.get("phone", "")),
                    "office": str(item.get("office", "")),
                    "department": "",
                    "specialization": "",
                    "keywords": "",
                    "raw": item,
                }
            )
    
    return docs


def check_staff_data_available() -> bool:
    """Check if staff data is available in data/faix_json_data.json (staff_contacts section)"""
    docs = _get_staff_documents()
    return len(docs) > 0


def check_schedule_data_available() -> bool:
    """Check if schedule data is available in data/faix_json_data.json (schedule section)"""
    docs = _get_schedule_documents()
    return len(docs) > 0


def _get_faix_data_documents() -> Dict[str, Any]:
    """Load FAIX comprehensive data from data/faix_json_data.json (merged single source)."""
    data_dir = _get_project_data_dir()
    data = _load_json_file(data_dir / "faix_json_data.json")
    
    if not data or not isinstance(data, dict):
        return {}
    
    # Return structured data organized by sections
    # Note: staff_contacts and schedule are now in the same file
    structured_data = {}
    
    # Faculty information
    if "faculty_info" in data:
        structured_data["faculty_info"] = data["faculty_info"]
    
    # Vision & Mission
    if "vision_mission" in data:
        structured_data["vision_mission"] = data["vision_mission"]
    
    # Programmes
    if "programmes" in data:
        structured_data["programmes"] = data["programmes"]
    
    # Admission information
    if "admission" in data:
        structured_data["admission"] = data["admission"]
    
    # Departments
    if "departments" in data:
        structured_data["departments"] = data["departments"]
    
    # Facilities
    if "facilities" in data:
        structured_data["facilities"] = data["facilities"]
    
    # Academic resources
    if "academic_resources" in data:
        structured_data["academic_resources"] = data["academic_resources"]
    
    # Key highlights
    if "key_highlights" in data:
        structured_data["key_highlights"] = data["key_highlights"]
    
    # FAQs (already in knowledge base, but keep for reference)
    if "faqs" in data:
        structured_data["faqs"] = data["faqs"]
    
    # Research focus
    if "research_focus" in data:
        structured_data["research_focus"] = data["research_focus"]
    
    # Staff contacts (now merged)
    if "staff_contacts" in data:
        structured_data["staff_contacts"] = data["staff_contacts"]
    
    # Schedule (now merged)
    if "schedule" in data:
        structured_data["schedule"] = data["schedule"]
    
    # Course info (now merged)
    if "course_info" in data:
        structured_data["course_info"] = data["course_info"]
    
    return structured_data


def check_faix_data_available() -> bool:
    """Check if FAIX comprehensive data is available in data/faix_json_data.json"""
    data = _get_faix_data_documents()
    return len(data) > 0


def retrieve_for_agent(
    agent_id: str,
    user_text: str,
    knowledge_base: KnowledgeBase,
    intent: Optional[str] = None,
    top_k: int = 3,
) -> Dict[str, List[Dict]]:
    """
    Retrieve context documents for a given agent.

    Returns a dict with keys like 'faq', 'schedule', 'staff' so the caller can
    decide how to inject them into the prompt.
    """
    agent = get_agent(agent_id)
    if agent is None:
        return {}

    context: Dict[str, List[Dict]] = {}

    # FAQ-style documents from the main knowledge base
    # Use agent.default_intent if provided, otherwise fall back to detected intent.
    kb_intent = agent.default_intent or intent
    
    # For fee-related queries, ensure we explicitly search for fee entries
    user_text_lower = user_text.lower()
    fee_keywords = ['fee', 'fees', 'tuition', 'yuran', 'bayaran', 'cost', 'payment', 'diploma fee', 'degree fee']
    is_fee_query = any(keyword in user_text_lower for keyword in fee_keywords) or intent == 'fees'
    
    try:
        # First try with the detected intent
        faq_docs = knowledge_base.get_documents(kb_intent, user_text, top_k=top_k)
        
        # If it's a fee query and we didn't get good results, explicitly search for 'fees' category
        if is_fee_query and (not faq_docs or len(faq_docs) == 0):
            fee_docs = knowledge_base.get_documents('fees', user_text, top_k=top_k)
            if fee_docs:
                faq_docs = fee_docs
        
        # IMPROVEMENT: Filter out low-relevance documents
        # Only include docs with score > 0.1 to avoid irrelevant matches
        MIN_FAQ_SCORE = 0.1
        if faq_docs:
            faq_docs = [doc for doc in faq_docs if doc.get('score', 0) > MIN_FAQ_SCORE]
            
    except Exception as e:
        print(f"Warning: Knowledge base document retrieval failed: {e}")
        faq_docs = []

    if faq_docs:
        context["faq"] = faq_docs

    # Schedule-specific context
    if agent.id == "schedule":
        schedule_docs = _get_schedule_documents()
        if schedule_docs:
            context["schedule"] = schedule_docs

    # Staff-specific context
    if agent.id == "staff":
        staff_docs = _get_staff_documents()
        if staff_docs:
            context["staff"] = staff_docs

    # FAIX comprehensive data context (available for all agents, especially FAQ)
    # This provides rich context about programs, admission, facilities, etc.
    faix_data = _get_faix_data_documents()
    if faix_data:
        context["faix_data"] = faix_data

    return context



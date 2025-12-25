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
                    "You are the FAIX FAQ assistant. Answer student questions using "
                    "the provided FAQ context and comprehensive FAIX information (programs, admission, "
                    "facilities, departments, fees, etc.).\n\n"
                    "RESPONSE FORMATTING:\n"
                    "- Provide well-structured, summarized answers with proper paragraphs and line breaks\n"
                    "- Use bullet points (•) when listing multiple items\n"
                    "- Use line breaks (\\n) to separate paragraphs and sections\n"
                    "- Keep responses concise but informative (3-5 sentences for simple queries, "
                    "summarized paragraphs for complex topics)\n"
                    "- Format your response with clear sections using newlines\n"
                    "- IMPORTANT: Always preserve and display URLs/links exactly as provided in the context\n"
                    "- For fee-related queries: Provide ONLY the fee schedule link, no extra text. Just the URL.\n\n"
                    "The FAIX Information Context contains detailed information about programs, admission "
                    "requirements, facilities, departments, vision/mission, fees, and more. Summarize and present "
                    "this information in a clear, well-formatted manner. When answers include links (especially "
                    "for fees, payment, or official resources), always include them in your response. "
                    "For fee queries specifically, keep it minimal - just provide the link. "
                    "If the answer is not in the context, say you are not sure and suggest contacting the FAIX office."
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
                    "You are the FAIX schedule assistant. Focus on academic calendar, "
                    "class times, and important deadlines.\n\n"
                    "RESPONSE FORMATTING:\n"
                    "- Use bullet points (•) for dates/events\n"
                    "- Use line breaks (\\n) to separate different events or sections\n"
                    "- Provide a brief summary introduction, then list relevant schedule items\n"
                    "- Format dates clearly with line breaks between items\n\n"
                    "Use the schedule context if available. If details are missing, be honest and suggest "
                    "checking the official schedule or contacting the office."
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
                    "You are the FAIX staff contact assistant. Use the staff contact "
                    "context to provide accurate names, roles, and contact details.\n\n"
                    "RESPONSE FORMATTING:\n"
                    "- Use proper line breaks (\\n) between items\n"
                    "- Format each staff member on a new line with bullet points\n"
                    "- When showing contact details, use line breaks to separate name, email, phone, office\n\n"
                    "IMPORTANT: When listing staff members, show ONLY their NAMES first "
                    "in a simple bullet list (max 3-5 most relevant), each on a new line. "
                    "Then ask: 'Would you like contact information for any of these staff members?'\n"
                    "Example format:\n"
                    "• Name 1\n"
                    "• Name 2\n"
                    "• Name 3\n\n"
                    "Would you like contact information for any of these staff members?\n\n"
                    "Only provide full details (email, phone, office) when the user specifically asks for them, "
                    "and format them with clear line breaks. Never invent people or contact details; if you don't find the "
                    "information, say you are not sure and suggest contacting the FAIX office."
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
    """Load schedule entries from data/schedule.json if present."""
    data_dir = _get_project_data_dir()
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
    """Load staff contact entries from data/staff_contacts.json if present."""
    data_dir = _get_project_data_dir()
    data = _load_json_file(data_dir / "staff_contacts.json")
    docs: List[Dict[str, str]] = []
    
    if not data or not isinstance(data, dict):
        return docs
    
    # Handle new nested structure with departments
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
                        "role": str(staff_item.get("position", "")),  # Using "position" from new structure
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
    """Check if staff data is available in data/staff_contacts.json"""
    docs = _get_staff_documents()
    return len(docs) > 0


def check_schedule_data_available() -> bool:
    """Check if schedule data is available in data/schedule.json"""
    docs = _get_schedule_documents()
    return len(docs) > 0


def _get_faix_data_documents() -> Dict[str, Any]:
    """Load FAIX comprehensive data from data/faix_json_data.json if present."""
    data_dir = _get_project_data_dir()
    data = _load_json_file(data_dir / "faix_json_data.json")
    
    if not data or not isinstance(data, dict):
        return {}
    
    # Return structured data organized by sections
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
            print(f"DEBUG: Fee query detected, explicitly searching for fee entries")
            fee_docs = knowledge_base.get_documents('fees', user_text, top_k=top_k)
            if fee_docs:
                faq_docs = fee_docs
                print(f"DEBUG: Found {len(fee_docs)} fee-related documents")
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
            print(f"DEBUG: Loaded {len(staff_docs)} staff documents for staff agent")
        else:
            print("DEBUG: No staff documents found - check data/staff_contacts.json")

    # FAIX comprehensive data context (available for all agents, especially FAQ)
    # This provides rich context about programs, admission, facilities, etc.
    faix_data = _get_faix_data_documents()
    if faix_data:
        context["faix_data"] = faix_data

    return context



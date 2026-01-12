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
    """Format schedule documents for context, including timetable links."""
    lines: List[str] = []
    for item in schedule_docs:
        title = item.get("title") or item.get("name") or ""
        desc = item.get("description", "")
        time = item.get("time", "")
        schedule_text = item.get("schedule", "")
        parts = []
        if title:
            parts.append(title)
        if time:
            parts.append(f"Time: {time}")
        if desc:
            parts.append(desc)
        if schedule_text:
            parts.append(f"Schedule: {schedule_text[:200]}...")  # Truncate long schedules
        if parts:
            lines.append(" - " + " | ".join(parts))
    
    # Add timetable links information
    lines.append("")
    lines.append("=== OFFICIAL TIMETABLE LINKS ===")
    lines.append("BAXI (Bachelor of Computer Science - Artificial Intelligence):")
    lines.append("  https://faix.utem.edu.my/en/academics/academic-resources/timetable/32-baxi-jadualwaktu-sem1-sesi-2025-2026/file.html")
    lines.append("BAXZ (Bachelor of Computer Science - Cybersecurity):")
    lines.append("  https://faix.utem.edu.my/en/academics/academic-resources/timetable/31-baxz-jadualwaktu-sem1-sesi-2025-2026/file.html")
    lines.append("Master Programs (MAXD, MAXZ, BRIDGING):")
    lines.append("  https://faix.utem.edu.my/en/academics/academic-resources/timetable/30-jadual-master-sem1-2025-2026-v3-faix/file.html")
    lines.append("")
    lines.append("IMPORTANT: Always include the appropriate timetable link(s) at the end of your response.")
    
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
        if info.get("staff_count"):
            staff_count = info["staff_count"]
            if staff_count.get("academic"):
                lines.append(f"Academic Staff: {staff_count['academic']}")
            if staff_count.get("administrative"):
                lines.append(f"Administrative Staff: {staff_count['administrative']}")
        if info.get("address"):
            address = info["address"]
            addr_parts = []
            if address.get("street"):
                addr_parts.append(address["street"])
            if address.get("postcode"):
                addr_parts.append(address["postcode"])
            if address.get("city"):
                addr_parts.append(address["city"])
            if address.get("state"):
                addr_parts.append(address["state"])
            if addr_parts:
                lines.append(f"Address: {', '.join(addr_parts)}")
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
            mission = vm["mission"]
            # Handle both string and array formats
            if isinstance(mission, list):
                lines.append("Mission:")
                for item in mission:
                    lines.append(f"  - {item}")
            else:
                lines.append(f"Mission: {mission}")
        if vm.get("objectives") and isinstance(vm["objectives"], list):
            lines.append("Objectives:")
            for obj in vm["objectives"]:
                lines.append(f"  - {obj}")
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
                    lines.append(f"  - {prog['name']} ({prog.get('code', 'N/A')})")
                    if prog.get("duration"):
                        lines.append(f"    Duration: {prog['duration']}")
                    if prog.get("focus_areas") and isinstance(prog["focus_areas"], list):
                        lines.append(f"    Focus Areas: {', '.join(prog['focus_areas'][:6])}")
                    if prog.get("career_opportunities") and isinstance(prog["career_opportunities"], list):
                        careers = prog["career_opportunities"][:5]
                        lines.append(f"    Career Opportunities: {', '.join(careers)}")
                    if prog.get("learning_distribution"):
                        dist = prog["learning_distribution"]
                        lines.append(f"    Learning: {dist.get('coursework', 'N/A')} coursework, {dist.get('practical_projects', 'N/A')} practical")
            lines.append("")
        
        # Postgraduate
        if "postgraduate" in programs and isinstance(programs["postgraduate"], list):
            lines.append("Postgraduate Programs:")
            for prog in programs["postgraduate"]:
                if prog.get("name"):
                    lines.append(f"  - {prog['name']} ({prog.get('code', 'N/A')})")
                    if prog.get("type"):
                        lines.append(f"    Type: {prog['type']}")
                    if prog.get("focus"):
                        lines.append(f"    Focus: {prog['focus']}")
            lines.append("")
    
    # Admission
    if "admission" in faix_data:
        admission = faix_data["admission"]
        lines.append("=== ADMISSION INFORMATION ===")
        
        # Undergraduate - Local
        if "undergraduate_local" in admission:
            local = admission["undergraduate_local"]
            lines.append("Undergraduate (Local) Entry Requirements:")
            reqs = local.get("requirements", {})
            if reqs.get("spm_stpm"):
                lines.append(f"  - {reqs['spm_stpm']}")
            if reqs.get("minimum_requirements"):
                lines.append(f"  - {reqs['minimum_requirements']}")
            links = local.get("application_links", {})
            if links.get("entry_requirements"):
                lines.append(f"  - More info: {links['entry_requirements']}")
            if links.get("fees"):
                lines.append(f"  - Fee schedule: {links['fees']}")
            lines.append("")
        
        # Undergraduate - International
        if "undergraduate_international" in admission:
            intl = admission["undergraduate_international"]
            lines.append("Undergraduate (International) Entry Requirements:")
            reqs = intl.get("requirements", {})
            if reqs.get("description"):
                lines.append(f"  - {reqs['description']}")
            if reqs.get("academic"):
                lines.append(f"  - Academic: {reqs['academic']}")
            if intl.get("learning_approach"):
                lines.append(f"  - Learning approach: {intl['learning_approach']}")
            links = intl.get("application_links", {})
            if links.get("entry_requirements"):
                lines.append(f"  - More info: {links['entry_requirements']}")
            lines.append("")
        
        # Postgraduate
        if "postgraduate" in admission:
            pg = admission["postgraduate"]
            lines.append("Postgraduate Entry Requirements:")
            if "entry_requirements" in pg and isinstance(pg["entry_requirements"], list):
                for req in pg["entry_requirements"]:
                    if isinstance(req, dict):
                        lines.append(f"  - {req.get('category', '')}: {req.get('requirement', '')}")
            if "language_requirements" in pg:
                lang_req = pg["language_requirements"]
                lines.append(f"  - Language: MUET {lang_req.get('muet', 'N/A')} or CEFR {lang_req.get('cefr', 'N/A')}")
            if "contact" in pg:
                contact = pg["contact"]
                if contact.get("coordinator"):
                    lines.append(f"  - Coordinator: {contact['coordinator']}")
                if contact.get("email"):
                    lines.append(f"  - Contact: {contact['email']}")
            lines.append("")
    
    # Departments
    if "departments" in faix_data and isinstance(faix_data["departments"], list):
        lines.append("=== DEPARTMENTS ===")
        for dept in faix_data["departments"]:
            if isinstance(dept, dict) and dept.get("name"):
                lines.append(f"  - {dept['name']}")
                if dept.get("focus"):
                    lines.append(f"    Focus: {dept['focus']}")
        lines.append("")
    
    # Facilities
    if "facilities" in faix_data:
        facilities = faix_data["facilities"]
        lines.append("=== FACILITIES ===")
        if "available" in facilities and isinstance(facilities["available"], list):
            lines.append("Available Facilities:")
            for facility in facilities["available"]:
                lines.append(f"  - {facility}")
        if facilities.get("booking_system"):
            lines.append(f"Booking System: {facilities['booking_system']}")
        
        # Laboratories - CRITICAL: Include detailed lab information
        if "laboratories" in facilities:
            laboratories = facilities["laboratories"]
            lines.append("")
            lines.append("Laboratories:")
            
            # AI Labs
            if "ai_labs" in laboratories and isinstance(laboratories["ai_labs"], list):
                lines.append("  AI Labs:")
                for lab in laboratories["ai_labs"]:
                    name = lab.get("name", "")
                    block = lab.get("block", "")
                    level = lab.get("level", "")
                    if name:
                        lab_info = f"    - {name}"
                        if block:
                            lab_info += f" (Block: {block}"
                            if level:
                                lab_info += f", {level}"
                            lab_info += ")"
                        elif level:
                            lab_info += f" ({level})"
                        lines.append(lab_info)
            
            # Cybersecurity Labs
            if "cybersec_labs" in laboratories and isinstance(laboratories["cybersec_labs"], list):
                lines.append("  Cybersecurity Labs:")
                for lab in laboratories["cybersec_labs"]:
                    name = lab.get("name", "")
                    block = lab.get("block", "")
                    level = lab.get("level", "")
                    if name:
                        lab_info = f"    - {name}"
                        if block:
                            lab_info += f" (Block: {block}"
                            if level:
                                lab_info += f", {level}"
                            lab_info += ")"
                        elif level:
                            lab_info += f" ({level})"
                        lines.append(lab_info)
        
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
                lines.append(f"  - {res}")
        lines.append("")
    
    # Key Highlights
    if "key_highlights" in faix_data and isinstance(faix_data["key_highlights"], list):
        lines.append("=== KEY HIGHLIGHTS ===")
        for highlight in faix_data["key_highlights"]:
            lines.append(f"  - {highlight}")
        lines.append("")
    
    # Research Focus
    if "research_focus" in faix_data and isinstance(faix_data["research_focus"], list):
        lines.append("=== RESEARCH FOCUS ===")
        for focus in faix_data["research_focus"]:
            lines.append(f"  - {focus}")
        lines.append("")
    
    # Staff Contacts (now merged - provide summary)
    if "staff_contacts" in faix_data:
        staff_data = faix_data["staff_contacts"]
        if "departments" in staff_data and isinstance(staff_data["departments"], dict):
            lines.append("=== STAFF CONTACTS (Summary) ===")
            depts = staff_data["departments"]
            for dept_key, dept_info in depts.items():
                if isinstance(dept_info, dict):
                    dept_name = dept_info.get("name", dept_key)
                    staff_list = dept_info.get("staff", [])
                    if isinstance(staff_list, list):
                        lines.append(f"{dept_name}: {len(staff_list)} staff members")
            lines.append("Note: Full staff details available in Staff Contacts Context section.")
            lines.append("")
    
    # Schedule (now merged - if has data)
    if "schedule" in faix_data and isinstance(faix_data["schedule"], list) and len(faix_data["schedule"]) > 0:
        lines.append("=== ACADEMIC SCHEDULE ===")
        for item in faix_data["schedule"][:10]:  # Limit to first 10 items
            if isinstance(item, dict):
                parts = []
                if item.get("title"):
                    parts.append(item["title"])
                if item.get("time"):
                    parts.append(f"Time: {item['time']}")
                if item.get("description"):
                    parts.append(item["description"])
                if parts:
                    lines.append(f"  - {' | '.join(parts)}")
        lines.append("")
    
    # Course Info (now merged - if has data)
    if "course_info" in faix_data and isinstance(faix_data["course_info"], list) and len(faix_data["course_info"]) > 0:
        lines.append("=== COURSE INFORMATION ===")
        for item in faix_data["course_info"][:10]:  # Limit to first 10 items
            if isinstance(item, dict):
                parts = []
                for key, value in item.items():
                    if value:
                        parts.append(f"{key}: {value}")
                if parts:
                    lines.append(f"  - {' | '.join(parts)}")
        lines.append("")
    
    return "\n".join(lines).strip()


def build_messages(
    agent: Agent,
    user_message: str,
    history: Optional[List[Dict[str, str]]],
    context: Dict[str, List[Dict]],
    intent: Optional[str] = None,
    language_code: str = 'en',
) -> List[Dict[str, str]]:
    """
    Build messages for the LLM client.

    Args:
        agent: The conversational agent definition.
        user_message: The latest user message.
        history: Conversation history as a list of {role, content} dicts.
        context: Retrieved documents grouped by source key (faq/schedule/staff).
        intent: Optional detected intent string for additional guidance.
        language_code: Detected language code ('en', 'ms', 'zh', 'ar').
    """
    messages: List[Dict[str, str]] = []

    # Language names for reference
    language_names = {
        'en': 'English',
        'ms': 'Bahasa Malaysia (Malay)',
        'zh': 'Chinese (Simplified)',
        'ar': 'Arabic',
    }
    language_name = language_names.get(language_code, 'English')

    # Language-specific response instructions - STRENGTHENED for strict language matching
    language_instructions = {
        'en': (
            "You MUST respond entirely in English. "
            "Use clear, professional English throughout your response."
        ),
        'ms': (
            "ANDA WAJIB menjawab sepenuhnya dalam Bahasa Malaysia. "
            "Gunakan tatabahasa dan perbendaharaan kata Melayu yang betul dan profesional. "
            "JANGAN gunakan Bahasa Inggeris dalam jawapan anda. "
            "Contoh: 'program' bukan 'program', 'pendaftaran' bukan 'registration', "
            "'maklumat' bukan 'information', 'yuran' bukan 'fees'."
        ),
        'zh': (
            "您必须完全使用简体中文回复。"
            "使用正确的中文语法和词汇。"
            "不要在回复中使用英文。"
            "例如：使用'课程'而不是'course'，'注册'而不是'registration'，"
            "'信息'而不是'information'，'学费'而不是'fees'。"
        ),
        'ar': (
            "يجب أن ترد بالكامل باللغة العربية. "
            "استخدم القواعد النحوية والمفردات العربية الصحيحة. "
            "لا تستخدم اللغة الإنجليزية في ردك."
        ),
    }
    language_instruction = language_instructions.get(language_code, language_instructions['en'])

    # System message with agent behaviour and RAG instructions
    system_parts: List[str] = [agent.system_prompt]
    
    # Add CRITICAL language instruction at the beginning
    system_parts.append(
        f"CRITICAL LANGUAGE REQUIREMENT: The user is communicating in {language_name}. "
        f"You MUST match the user's language exactly. {language_instruction}"
    )
    if intent:
        system_parts.append(f"The detected intent for this query is: '{intent}'.")
    
    # Add follow-up question requirements based on intent
    follow_up_instruction = ""
    if intent in ['staff_contact']:
        follow_up_instruction = (
            "\nFOLLOW-UP QUESTIONS (REQUIRED for staff/faculty queries):\n"
            "- After providing the main answer, ALWAYS ask a specific follow-up question\n"
            "- For faculty queries, ask what specific information they need: research/courses/contact/office hours\n"
            "- Format: [Main Answer]\n\n[Follow-up Question]\n"
            "- Only skip follow-ups if user explicitly says 'No thanks', 'That's all', or similar\n"
        )
    elif intent in ['course_info']:
        follow_up_instruction = (
            "\nFOLLOW-UP QUESTIONS (REQUIRED for course queries):\n"
            "- Always ask for semester and level (undergraduate/graduate)\n"
            "- Format: [Main Answer]\n\n[Follow-up Question]\n"
        )
    elif intent in ['research']:
        follow_up_instruction = (
            "\nFOLLOW-UP QUESTIONS (REQUIRED for research queries):\n"
            "- Always ask for specific field (AI/systems/theory/cybersecurity)\n"
            "- Format: [Main Answer]\n\n[Follow-up Question]\n"
        )
    
    system_parts.append(
        "Use the provided context sections when answering. Format your response using markdown:\n"
        "- Use **bold** for emphasis\n"
        "- Use `code` for technical terms\n"
        "- Use - or * for bullet lists (NOT •)\n"
        "- Use proper line breaks between paragraphs\n"
        "Ensure your response is well-formatted and easy to read.\n\n"
        + follow_up_instruction +
        "IMPORTANT: Always preserve and include URLs/links from the context in your response, "
        "especially for fee schedules, official resources, or payment information. Links should "
        "be displayed as clickable URLs.\n\n"
        "LOCATION QUERIES: When users ask 'where is X' or 'location of X', look for Block and Level "
        "information in the Facilities section. For laboratories, provide the Block and Level details "
        "from the Laboratories section.\n\n"
        "CRITICAL: Do NOT add disclaimers like 'The final answer to your question is not explicitly stated' "
        "or 'According to the FAQ section:' or similar meta-commentary. Answer directly and naturally "
        "using the provided context. If the answer is not clearly supported by the context, simply say "
        "you are not sure and suggest contacting the FAIX office."
    )
    # Staff agent specific instructions
    if agent.id == "staff":
        system_parts.append(
            "STAFF QUERY HANDLING:\n"
            "- If user asks about a SPECIFIC staff member by name (e.g., 'who is dr choo', 'contact for Ahmad'):\n"
            "  → Provide COMPLETE contact information immediately (name, position, department, email, phone, office)\n"
            "  → Do NOT ask follow-up questions - give all details at once\n"
            "- If user asks GENERAL questions (e.g., 'who can I contact for X', 'staff in Y department'):\n"
            "  → Suggest relevant staff (max 5) with names and positions\n"
            "  → Then ask if they want contact details\n"
            "- If matched staff are highlighted in context, those are the EXACT matches - use them!\n"
            "- Format contact details clearly with line breaks between each field."
        )
    
    # Add reminder for fee queries - keep it simple, just provide the link
    if intent == 'fees' or any(kw in (user_message.lower() if isinstance(user_message, str) else '') for kw in ['fee', 'fees', 'tuition', 'yuran', 'diploma fee', 'degree fee']):
        system_parts.append(
            "IMPORTANT: This is a fee-related query. Provide ONLY the fee schedule link from the context. "
            "Do not add extra explanations. Just provide the URL: https://bendahari.utem.edu.my/ms/jadual-yuran-pelajar.html"
        )
    
    # Add reminder for schedule queries - always include correct timetable links
    if intent == 'academic_schedule' or agent.id == 'schedule' or any(kw in (user_message.lower() if isinstance(user_message, str) else '') for kw in ['timetable', 'schedule', 'jadual', 'class schedule']):
        system_parts.append(
            "IMPORTANT: This is a schedule/timetable query. ALWAYS include the correct timetable link(s) at the end:\n"
            "- For BAXI queries: https://faix.utem.edu.my/en/academics/academic-resources/timetable/32-baxi-jadualwaktu-sem1-sesi-2025-2026/file.html\n"
            "- For BAXZ queries: https://faix.utem.edu.my/en/academics/academic-resources/timetable/31-baxz-jadualwaktu-sem1-sesi-2025-2026/file.html\n"
            "- For Master program queries: https://faix.utem.edu.my/en/academics/academic-resources/timetable/30-jadual-master-sem1-2025-2026-v3-faix/file.html\n"
            "- For general queries: Include all three links\n"
            "Use the EXACT links above - DO NOT modify or invent links. Format as: 📅 **View Complete Timetable:** [link]"
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
    matched_staff = context.get("matched_staff", [])
    if staff_docs:
        staff_text = _format_staff_context(staff_docs)
        if staff_text:
            context_lines.append("--- Staff Contacts Context (ONLY SOURCE - USE THIS LIST ONLY) ---")
            context_lines.append(f"Total staff members available: {len(staff_docs)}")
            
            # Extract all valid staff names and add to context for explicit validation
            all_staff_names = []
            for staff in staff_docs:
                name = staff.get('name', '').strip()
                if name:
                    all_staff_names.append(name)
            
            if all_staff_names:
                context_lines.append("")
                context_lines.append("📋 COMPLETE LIST OF VALID STAFF NAMES (USE ONLY THESE):")
                context_lines.append("The following are ALL the staff members that exist in the database:")
                for i, name in enumerate(all_staff_names[:50], 1):  # Limit to 50 to avoid token bloat
                    context_lines.append(f"{i}. {name}")
                if len(all_staff_names) > 50:
                    context_lines.append(f"... and {len(all_staff_names) - 50} more (see full list below)")
                context_lines.append("")
                context_lines.append("🚫 CRITICAL: If a name is NOT in the above list, it DOES NOT EXIST.")
                context_lines.append("🚫 DO NOT invent, create, or mention ANY staff member not in this list.")
                context_lines.append("")
            
            # If we have matched staff, highlight them VERY prominently
            if matched_staff:
                matched_names = [s.get('name', '') for s in matched_staff if s.get('name')]
                context_lines.append("")
                context_lines.append("=" * 60)
                context_lines.append("🎯 MATCHED STAFF - USE THESE TO ANSWER THE QUERY!")
                context_lines.append("=" * 60)
                context_lines.append(f"The following {len(matched_staff)} staff member(s) MATCH the user's query:")
                for i, staff in enumerate(matched_staff[:5], 1):
                    name = staff.get('name', 'Unknown')
                    position = staff.get('role', '')
                    dept = staff.get('department', '')
                    email = staff.get('email', '')
                    phone = staff.get('phone', '-')
                    office = staff.get('office', '-')
                    context_lines.append(f"{i}. **{name}**")
                    context_lines.append(f"   - Position: {position}")
                    context_lines.append(f"   - Department: {dept}")
                    context_lines.append(f"   - Email: {email}")
                    if phone and phone != '-':
                        context_lines.append(f"   - Phone: {phone}")
                    if office and office != '-':
                        context_lines.append(f"   - Office: {office}")
                    context_lines.append("")
                context_lines.append("⚠️ CRITICAL ANTI-HALLUCINATION RULES:")
                context_lines.append("⚠️ Use ONLY the names, emails, positions shown above - DO NOT modify or invent")
                context_lines.append("⚠️ Use EXACT names as shown - DO NOT change spelling, add middle names, or modify in any way")
                context_lines.append("⚠️ Use EXACT emails as shown - DO NOT invent or modify email addresses")
                context_lines.append("⚠️ If phone/office shows '-', say 'Not available' - DO NOT invent phone numbers or offices")
                context_lines.append("⚠️ Copy EXACTLY what appears above - do not paraphrase names or details")
                context_lines.append("⚠️ FORBIDDEN FIELDS: DO NOT add 'Research Interests', 'Specialization', or any fields not shown above")
                context_lines.append("⚠️ Available fields ONLY: Name, Position, Department, Email, Phone, Office (if available)")
                context_lines.append("=" * 60)
                context_lines.append("")
            context_lines.append("You MUST ONLY use staff from this list. Do NOT invent or create any staff members.")
            context_lines.append("")
            context_lines.append("🚫 FORBIDDEN: DO NOT add fields that don't exist in the data such as:")
            context_lines.append("   - 'Research Interests' (this field does NOT exist in the database)")
            context_lines.append("   - 'Specialization' (unless shown in the staff data below)")
            context_lines.append("   - Any other fields not explicitly shown in the staff data")
            context_lines.append("")
            context_lines.append("✅ ALLOWED FIELDS ONLY:")
            context_lines.append("   - Name (exact as shown)")
            context_lines.append("   - Position (exact as shown)")
            context_lines.append("   - Department (if shown)")
            context_lines.append("   - Email (exact as shown)")
            context_lines.append("   - Phone (if available, otherwise say 'Not available')")
            context_lines.append("   - Office (if available, otherwise say 'Not available')")
            context_lines.append("")
            context_lines.append(staff_text)

    # FAIX comprehensive data context (programs, admission, facilities, etc.)
    # This is the PRIMARY source for all FAIX information (merged JSON)
    faix_data = context.get("faix_data")
    if faix_data:
        faix_text = _format_faix_data_context(faix_data)
        if faix_text:
            context_lines.append("--- FAIX Information Context (PRIMARY DATA SOURCE - Use This First) ---")
            context_lines.append("This section contains all merged FAIX data including:")
            context_lines.append("- Faculty Information (dean, contact, address, staff count)")
            context_lines.append("- Programmes (BCSAI, BCSCS, Masters - with codes, duration, focus areas, career opportunities)")
            context_lines.append("- Admission Requirements (undergraduate local/international, postgraduate)")
            context_lines.append("- Facilities, Academic Resources, Research Focus, Departments")
            context_lines.append("")
            context_lines.append("IMPORTANT: For dean queries, use the Dean name from Faculty Information section.")
            context_lines.append("For programme queries (BCSAI, BCSCS, etc.), use exact details from Programmes section.")
            context_lines.append("For staff member queries (not dean), use Staff Contacts Context above.")
            context_lines.append("")
            context_lines.append(faix_text)

    if context_lines:
        # For staff agent, add extra emphasis about using only the provided list
        content_prefix = "Here is reference context you can use:\n\n"
        if "staff" in context and context.get("staff"):
            staff_count = len(context.get("staff", []))
            content_prefix = (
                "Here is reference context you can use:\n\n"
                "CRITICAL: For staff-related queries, you MUST ONLY use staff members "
                "from the 'Staff Contacts Context' section below. "
                "Do NOT invent, create, or mention any staff members outside of this list.\n"
                f"You have access to {staff_count} staff members in the database. "
                "Each staff member has a NAME, POSITION, and EMAIL.\n"
                "IMPORTANT: ONLY list people whose names appear in the Staff Contacts Context. "
                "Do NOT list generic roles (like 'Office Manager', 'Human Resources Officer') without names. "
                "Do NOT list department names as if they were people. "
                "Do NOT create organizational charts or invent positions.\n"
                "When staff matching the query exist in this list, present them confidently with their actual names and positions. "
                "Do NOT say 'I am not sure' or add disclaimers when the data is available.\n\n"
            )
        messages.append(
            {
                "role": "assistant",
                "content": content_prefix + "\n".join(context_lines),
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



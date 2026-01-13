import os
import sys
import django
import json
from pathlib import Path
import re
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Optional, List, Dict, Any

# Shared logger for startup/status messages
logger = logging.getLogger("faix_chatbot")

# Import semantic search
try:
    from backend.nlp.nlp_semantic_search import get_semantic_search
    SEMANTIC_SEARCH_AVAILABLE = True
except ImportError:
    try:
        from backend.nlp import nlp_semantic_search
        get_semantic_search = nlp_semantic_search.get_semantic_search
        SEMANTIC_SEARCH_AVAILABLE = True
    except ImportError:
        SEMANTIC_SEARCH_AVAILABLE = False
        logger.warning("Semantic search not available. Using TF-IDF fallback.")

# Setup Django if not already configured
try:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(BASE_DIR))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
    django.setup()
    from django_app.models import FAQEntry
    DJANGO_AVAILABLE = True
except Exception as e:
    logger.warning("Django not available, falling back to CSV mode: %s", e)
    DJANGO_AVAILABLE = False
    import pandas as pd


class KnowledgeBase:
    """
    Knowledge Base module that retrieves answers from FAIX JSON data (primary) and CSV (fallback).
    Uses JSON files from data/separated/ directory as the primary data source.
    CSV is only used as fallback for non-FAIX-specific queries when database is unavailable.
    """
    
    def __init__(self, csv_path: Optional[str] = None, use_database: bool = False, use_semantic_search: bool = True):
        """
        Initialize KnowledgeBase.
        
        Args:
            csv_path: Path to CSV file (fallback for non-FAIX queries, optional)
            use_database: Whether to use database (default: False - JSON-only mode)
            use_semantic_search: Whether to use semantic search (default: True)
        """
        self.use_database = use_database and DJANGO_AVAILABLE
        self.csv_path = csv_path
        self.use_semantic_search = use_semantic_search and SEMANTIC_SEARCH_AVAILABLE
        self.semantic_search = None
        
        # PERFORMANCE OPTIMIZATION: Initialize cache for retrieval results
        self._retrieve_cache = {}
        
        # Load FAIX JSON data as primary data source
        self.faix_data = self._load_faix_json_data()
        
        # Load intent-to-data mapping from intent_config.json
        self.faix_data_mapping = self._load_intent_mapping()
        
        # Initialize semantic search if available (silent unless error)
        if self.use_semantic_search:
            try:
                self.semantic_search = get_semantic_search()
                if not self.semantic_search.is_available():
                    self.use_semantic_search = False
            except Exception as e:
                logger.debug("Semantic search unavailable: %s", e)
                self.use_semantic_search = False
        
        if self.use_database:
            self._init_database()
        else:
            if csv_path:
                self._init_csv(csv_path)
            else:
                # Try default path (go up from backend/chatbot/ to project root)
                default_path = Path(__file__).parent.parent.parent / 'data' / 'faix_data.csv'
                if default_path.exists():
                    self._init_csv(str(default_path))
                else:
                    # JSON-only mode - this is expected and normal
                    logger.debug("CSV not found, using JSON data only")
                    self.entries = []
                    self.vectorizer = TfidfVectorizer()
                    self.question_vectors = None
    
    def _load_faix_json_data(self) -> Dict[str, Any]:
        """Load FAIX comprehensive data from separated JSON files or merged file."""
        data = {}
        
        # First try: Load from separated files (preferred)
        try:
            from backend.chatbot.agents import _load_faix_json_data as load_separated_data
            separated_data = load_separated_data()
            if separated_data:
                logger.debug("FAIX data loaded from separated JSON files")
                return separated_data
        except Exception as e:
            logger.debug("Could not load from separated files: %s", e)
        
        # Fallback: Try merged file (go up from backend/chatbot/ to project root)
        try:
            json_path = Path(__file__).parent.parent.parent / 'data' / 'faix_json_data.json'
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.debug("FAIX data loaded from merged JSON file")
                return data
        except Exception as e:
            logger.warning("Could not load FAIX JSON data: %s", e)
        
        return {}
    
    def _load_intent_mapping(self) -> Dict[str, List[str]]:
        """Load intent-to-data mapping from intent_config.json"""
        try:
            # Go up from backend/chatbot/ to project root
            config_path = Path(__file__).parent.parent.parent / 'data' / 'intent_config.json'
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                mapping = config.get('faix_data_mapping', {})
                if mapping:
                    logger.debug("Loaded intent-to-data mapping from intent_config.json")
                return mapping
        except Exception as e:
            logger.warning("Could not load intent mapping from intent_config.json: %s", e)
        return {}
    
    def get_faix_answer(self, intent: str, user_text: str) -> Optional[str]:
        """
        Get answer directly from FAIX JSON data based on intent.
        This is the primary data source for structured information.
        Also checks user text directly for keywords if intent routing doesn't work.
        """
        if not self.faix_data:
            return None
        
        intent = intent.lower() if intent else ""
        user_lower = user_text.lower() if user_text else ""
        
        # Priority 1: Check for specific keywords in user text regardless of intent
        # This handles cases where intent detection is wrong
        
        # Top management queries - check FIRST before other queries
        # This handles "who is nc", "vice chancellor", "naib canselor", etc.
        top_management = self.faix_data.get('top_management', [])
        if top_management and isinstance(top_management, list):
            # Check for queries that might be about top management
            # Look for common abbreviations and position terms
            top_mgmt_keywords = ['nc', 'vc', 'dvc', 'avc', 'coo', 'cdo', 'chancellor', 'canselor', 
                                'vice chancellor', 'deputy vice chancellor', 'assistant vice chancellor',
                                'treasurer', 'bendahari', 'librarian', 'pustakawan', 'ketua pegawai',
                                'top management', 'pengurusan tertinggi']
            
            # Check if query contains top management keywords or "who is" + abbreviation
            is_top_mgmt_query = any(kw in user_lower for kw in top_mgmt_keywords)
            is_who_is_query = 'who is' in user_lower
            
            if is_top_mgmt_query or (is_who_is_query and len(user_lower.split()) <= 4):
                # Search for matching person in top management
                matched_person = None
                user_words = user_lower.split()
                for person in top_management:
                    keywords = person.get('keywords', [])
                    if keywords:
                        for keyword in keywords:
                            keyword_lower = keyword.lower().strip()
                            # Check if keyword matches in user text (substring match)
                            if keyword_lower in user_lower:
                                # For short keywords like "nc", "vc", also check word boundaries
                                if len(keyword_lower) <= 3:
                                    # Check if keyword appears as a whole word
                                    if keyword_lower in user_words:
                                        matched_person = person
                                        break
                                else:
                                    # For longer keywords, substring match is fine
                                    matched_person = person
                                    break
                        if matched_person:
                            break
                    
                    # Also check position
                    position = person.get('position', '').lower()
                    if position and position in user_lower:
                        matched_person = person
                        break
                
                if matched_person:
                    name = matched_person.get('name', '')
                    position = matched_person.get('position', '')
                    email = matched_person.get('email', '')
                    title = matched_person.get('title', '')
                    
                    answer = f"**{name}**\n\n"
                    answer += f"- **Position:** {position}\n"
                    if title:
                        answer += f"- **Title:** {title}\n"
                    if email:
                        answer += f"- **Email:** {email}\n"
                    return answer
        
        # Staff member queries - check for specific staff names/keywords
        # Look for queries that might be asking about a staff member by name
        staff_keywords = ['dr.', 'doctor', 'professor', 'associate professor', 'lecturer', 'senior lecturer', 'ts. dr.', 'ts dr']
        has_staff_keyword = any(kw in user_lower for kw in staff_keywords)
        
        # Check if query might contain a staff name (has words that could be names)
        # This catches queries like "Ts. Dr. Choo Yun Huoy" or "who is dr choo"
        words = [w.strip().strip('.,!?') for w in user_text.split() if len(w.strip()) > 2]
        # Look for capitalized words that might be names
        has_name_like_words = len([w for w in words if w[0].isupper() and w.lower() not in ['who', 'what', 'when', 'where', 'why', 'how', 'is', 'are', 'the', 'for', 'contact', 'info', 'information']]) >= 1
        
        if has_staff_keyword or has_name_like_words:
            # Try to find a specific staff member first (only if we might have a name)
            # Don't return general contact info, only return if we found a specific staff member
            staff_answer = self._get_staff_by_name(user_lower, user_text)
            if staff_answer:
                return staff_answer
        
        # Dean queries (can come from staff_contact or about_faix intent)
        if any(kw in user_lower for kw in ['who is dean', 'who is the dean', 'dean', 'head of faculty']) and 'chancellor' not in user_lower:
            faculty_info = self.faix_data.get('faculty_info', {})
            dean = faculty_info.get('dean', '')
            if dean:
                return f"The Dean of FAIX is **{dean}**."
        
        # BCSAI/BCSCS program code queries
        if any(kw in user_lower for kw in ['baxi', 'baxz', 'mcsss', 'mtdsa']):
            return self._get_program_answer(user_lower)
        
        # Map intents to FAIX JSON sections
        if intent == 'about_faix':
            return self._get_about_faix_answer(user_lower)
        elif intent == 'program_info':
            return self._get_program_answer(user_lower)
        elif intent == 'admission':
            return self._get_admission_answer(user_lower)
        elif intent == 'fees':
            return self._get_fees_answer(user_lower)
        elif intent == 'career':
            return self._get_career_answer(user_lower)
        elif intent == 'facility_info':
            return self._get_facility_answer(user_lower)
        elif intent == 'academic_resources':
            return self._get_academic_resources_answer(user_lower)
        elif intent == 'research':
            return self._get_research_answer(user_lower)
        elif intent == 'staff_contact':
            # Check for dean queries first (dean is in staff_contact context)
            if any(kw in user_lower for kw in ['dean', 'head', 'leader']):
                faculty_info = self.faix_data.get('faculty_info', {})
                dean = faculty_info.get('dean', '')
                if dean:
                    return f"The Dean of FAIX is **{dean}**."
            return self._get_contact_answer(user_lower)
        elif intent == 'academic_schedule':
            return self._get_schedule_answer(user_lower)
        
        # Check FAQs in FAIX data
        return self._search_faix_faqs(user_lower)
    
    def _get_about_faix_answer(self, user_text: str) -> Optional[str]:
        """Get answer about FAIX faculty info, vision, mission, etc."""
        faculty_info = self.faix_data.get('faculty_info', {})
        vision_mission = self.faix_data.get('vision_mission', {})
        departments = self.faix_data.get('departments', [])
        highlights = self.faix_data.get('key_highlights', [])
        user_text_lower = user_text.lower()
        
        # Normalize abbreviations: vc -> vice chancellor, nc -> naib canselor
        # This helps matching queries like "who is vc" or "who is nc"
        abbreviation_expansions = {
            'vc': 'vice chancellor',
            'nc': 'naib canselor'
        }
        normalized_text = user_text_lower
        for abbrev, expansion in abbreviation_expansions.items():
            # Replace standalone abbreviations (word boundaries)
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            normalized_text = re.sub(pattern, expansion, normalized_text, flags=re.IGNORECASE)
        
        # PRIORITY 1: Top management queries - check FIRST before other checks
        # This handles queries like "vice chancellor", "naib canselor", etc.
        top_management = self.faix_data.get('top_management', [])
        if top_management and isinstance(top_management, list):
            # Check for specific position/keyword queries first
            matched_person = None
            for person in top_management:
                # Check position field (exact or partial match)
                position = person.get('position', '').lower()
                if position:
                    # Check if position string is in user query
                    if position in user_text_lower:
                        matched_person = person
                        break
                    # Also check if any significant word from position matches
                    position_words = [w for w in position.split() if len(w) > 2]
                    if any(word in user_text_lower for word in position_words if word not in ['dan', 'the', 'of', 'and']):
                        # Additional check: make sure it's a relevant match
                        if any(word in user_text_lower for word in ['chancellor', 'canselor', 'timbalan', 'deputy', 'assistant', 'ketua', 'head', 'director', 'officer', 'treasurer', 'bendahari', 'librarian', 'pustakawan', 'legal', 'undang', 'digital', 'strategic']):
                            matched_person = person
                            break
                
                # Check keywords array - most reliable matching
                keywords = person.get('keywords', [])
                if keywords:
                    user_words = set(user_text_lower.split())
                    # Also check normalized text for expanded abbreviations
                    normalized_words = set(normalized_text.split())
                    combined_words = user_words | normalized_words
                    
                    for keyword in keywords:
                        keyword_lower = keyword.lower().strip()
                        # For short keywords (3 chars or less), check word boundaries
                        if len(keyword_lower) <= 3:
                            # Check if keyword appears as a whole word in original or normalized text
                            if keyword_lower in combined_words:
                                matched_person = person
                                break
                            # Also check if abbreviation was expanded and matches position
                            if keyword_lower == 'vc' and 'vice chancellor' in normalized_text:
                                matched_person = person
                                break
                            if keyword_lower == 'nc' and 'naib canselor' in normalized_text:
                                matched_person = person
                                break
                        else:
                            # For longer keywords, check both original and normalized text
                            if keyword_lower in user_text_lower or keyword_lower in normalized_text:
                                matched_person = person
                                break
                    if matched_person:
                        break
                
                # Check name (partial match for queries like "who is massila")
                name = person.get('name', '').lower()
                # Extract significant words from name (excluding titles)
                name_words = [w for w in name.split() if len(w) > 3 and w not in ['prof.', 'professor', 'dr.', 'doctor', 'associate', 'madya', 'datuk', 'ts.', 'encik', 'puan', 'mdm.']]
                if any(word in user_text_lower for word in name_words):
                    matched_person = person
                    break
            
            # If specific person matched, return their details
            if matched_person:
                name = matched_person.get('name', '')
                position = matched_person.get('position', '')
                email = matched_person.get('email', '')
                title = matched_person.get('title', '')
                
                answer = f"**{name}**\n\n"
                answer += f"- **Position:** {position}\n"
                if title:
                    answer += f"- **Title:** {title}\n"
                if email:
                    answer += f"- **Email:** {email}\n"
                return answer
            
            # General top management queries
            if any(kw in user_text_lower for kw in ['top management', 'management', 'leadership', 'leaders', 'who are the leaders', 'pengurusan tertinggi']):
                mgmt_list = []
                for person in top_management:
                    name = person.get('name', '')
                    position = person.get('position', '')
                    email = person.get('email', '')
                    if name and position:
                        mgmt_item = f"**{name}**\n- Position: {position}"
                        if email:
                            mgmt_item += f"\n- Email: {email}"
                        mgmt_list.append(mgmt_item)
                if mgmt_list:
                    return f"**UTeM Top Management (Pengurusan Tertinggi Universiti):**\n\n" + "\n\n".join(mgmt_list)
        
        # Check for specific questions (dean, vision, mission, etc.)
        if any(kw in user_text for kw in ['dean', 'head', 'leader']) and 'chancellor' not in user_text_lower:
            # Only match dean if it's not a chancellor query
            dean = faculty_info.get('dean', '')
            if dean:
                return f"The Dean of FAIX is **{dean}**."
        
        if any(kw in user_text for kw in ['when', 'establish', 'founded', 'created', 'start']):
            established = faculty_info.get('established', '')
            if established:
                return f"FAIX was established on **{established}**."
        
        if any(kw in user_text for kw in ['vision']):
            vision = vision_mission.get('vision', '')
            if vision:
                return f"**FAIX Vision:**\n\n{vision}"
        
        if any(kw in user_text for kw in ['mission']):
            mission = vision_mission.get('mission', '')
            if mission:
                # Handle both string and array formats
                if isinstance(mission, list):
                    mission_text = '\n'.join([f"- {item}" for item in mission])
                    return f"**FAIX Mission:**\n\n{mission_text}"
                else:
                    return f"**FAIX Mission:**\n\n{mission}"
        
        if any(kw in user_text for kw in ['objective', 'objectives']):
            objectives = vision_mission.get('objectives', [])
            if objectives:
                obj_list = '\n'.join([f"- {obj}" for obj in objectives])
                return f"**FAIX Objectives:**\n\n{obj_list}"
        
        if any(kw in user_text for kw in ['department']):
            if departments:
                dept_list = '\n'.join([f"- **{d.get('name', '')}**: {d.get('focus', '')}" for d in departments])
                return f"**FAIX Departments:**\n\n{dept_list}"
        
        if any(kw in user_text for kw in ['highlight', 'key', 'special', 'unique']):
            if highlights:
                hl_list = '\n'.join([f"- {h}" for h in highlights[:5]])
                return f"**Key Highlights of FAIX:**\n\n{hl_list}"
        
        # General about FAIX
        name = faculty_info.get('name', 'Faculty of Artificial Intelligence and Cyber Security (FAIX)')
        university = faculty_info.get('university', 'Universiti Teknikal Malaysia Melaka (UTeM)')
        established = faculty_info.get('established', '')
        dean = faculty_info.get('dean', '')
        
        answer = f"**{name}**\n\n"
        answer += f"- **University:** {university}\n"
        if established:
            answer += f"- **Established:** {established}\n"
        if dean:
            answer += f"- **Dean:** {dean}\n"
        
        if vision_mission.get('vision'):
            answer += f"\n**Vision:** {vision_mission['vision']}"
        
        return answer
    
    def _get_program_answer(self, user_text: str) -> Optional[str]:
        """Get answer about programmes offered"""
        programmes = self.faix_data.get('programmes', {})
        undergraduate = programmes.get('undergraduate', [])
        postgraduate = programmes.get('postgraduate', [])
        
        # Check for specific programme code questions first (most specific)
        if 'bcsai' in user_text.lower():
            for prog in undergraduate:
                if prog.get('code', '').upper() == 'BCSAI':
                    return self._format_program_details(prog)
        
        if 'bcscs' in user_text.lower():
            for prog in undergraduate:
                if prog.get('code', '').upper() == 'BCSCS':
                    return self._format_program_details(prog)
        
        if 'mcsss' in user_text.lower():
            for prog in postgraduate:
                if prog.get('code', '').upper() == 'MCSSS':
                    return self._format_program_details(prog)
        
        if 'mtdsa' in user_text.lower():
            for prog in postgraduate:
                if 'MTDSA' in prog.get('code', '').upper():
                    return self._format_program_details(prog)
        
        # Check for specific programme questions by name/keywords
        if any(kw in user_text for kw in ['artificial intelligence', 'ai programme', 'ai program', 'ai degree']):
            for prog in undergraduate:
                if 'artificial intelligence' in prog.get('name', '').lower():
                    return self._format_program_details(prog)
        
        if any(kw in user_text for kw in ['security', 'cyber', 'computer security']):
            for prog in undergraduate:
                if 'security' in prog.get('name', '').lower():
                    return self._format_program_details(prog)
        
        if any(kw in user_text for kw in ['master', 'postgraduate', 'graduate']):
            if postgraduate:
                prog_list = []
                for prog in postgraduate:
                    prog_list.append(f"- **{prog.get('name', '')}** ({prog.get('code', '')})\n  - Type: {prog.get('type', '')}\n  - Focus: {prog.get('focus', '')}")
                return f"**Postgraduate Programmes at FAIX:**\n\n" + '\n'.join(prog_list)
        
        if any(kw in user_text for kw in ['undergraduate', 'bachelor', 'degree']):
            if undergraduate:
                # Concise format for general queries - just name, code, and duration
                prog_list = []
                for prog in undergraduate:
                    name = prog.get('name', '')
                    code = prog.get('code', '')
                    duration = prog.get('duration', '')
                    # Extract main focus from name or use first focus area
                    if 'artificial intelligence' in name.lower():
                        focus_hint = "AI and Machine Learning"
                    elif 'security' in name.lower():
                        focus_hint = "Cybersecurity"
                    else:
                        focus_areas = prog.get('focus_areas', [])
                        focus_hint = focus_areas[0] if focus_areas else ""
                    
                    prog_list.append(f"- **{name}** ({code}) - {duration} - Focus: {focus_hint}")
                
                return f"**Undergraduate Programmes at FAIX:**\n\n" + '\n'.join(prog_list) + "\n\n💡 Ask about a specific program (e.g., 'Tell me about BAXI' or 'What is BAXZ?') for more details."
        
        # General programmes listing
        answer = "**Programmes Offered at FAIX:**\n\n"
        if undergraduate:
            answer += "**Undergraduate:**\n"
            for prog in undergraduate:
                answer += f"- {prog.get('name', '')} ({prog.get('code', '')})\n"
        if postgraduate:
            answer += "\n**Postgraduate:**\n"
            for prog in postgraduate:
                answer += f"- {prog.get('name', '')} ({prog.get('code', '')})\n"
        
        return answer
    
    def _format_program_details(self, prog: Dict) -> str:
        """Format detailed programme information"""
        answer = f"**{prog.get('name', '')}** ({prog.get('code', '')})\n\n"
        if prog.get('duration'):
            answer += f"- **Duration:** {prog['duration']}\n"
        if prog.get('focus_areas'):
            answer += f"- **Focus Areas:** {', '.join(prog['focus_areas'][:5])}\n"
        if prog.get('learning_distribution'):
            dist = prog['learning_distribution']
            answer += f"- **Learning:** {dist.get('coursework', '')} coursework, {dist.get('practical_projects', '')} practical\n"
        if prog.get('career_opportunities'):
            careers = prog['career_opportunities'][:5]
            answer += f"\n**Career Opportunities:** {', '.join(careers)}"
        return answer
    
    def _get_admission_answer(self, user_text: str) -> Optional[str]:
        """Get admission requirements information"""
        admission = self.faix_data.get('admission', {})
        
        if any(kw in user_text for kw in ['international', 'foreign', 'overseas']):
            intl = admission.get('undergraduate_international', {})
            if intl:
                answer = "**International Student Admission:**\n\n"
                reqs = intl.get('requirements', {})
                answer += f"- {reqs.get('description', '')}\n"
                links = intl.get('application_links', {})
                if links.get('entry_requirements'):
                    answer += f"\nMore info: {links['entry_requirements']}"
                return answer
        
        if any(kw in user_text for kw in ['postgraduate', 'master', 'graduate']):
            pg = admission.get('postgraduate', {})
            if pg:
                answer = "**Postgraduate Entry Requirements:**\n\n"
                for req in pg.get('entry_requirements', []):
                    answer += f"- **{req.get('category', '')}:** {req.get('requirement', '')}\n"
                lang = pg.get('language_requirements', {})
                if lang:
                    answer += f"\n**Language Requirements:**\n- MUET: Minimum Band {lang.get('muet', '4')}\n- CEFR: {lang.get('cefr', 'Low B2')}"
                return answer
        
        # Local undergraduate
        local = admission.get('undergraduate_local', {})
        if local:
            answer = "**Local Undergraduate Admission:**\n\n"
            reqs = local.get('requirements', {})
            answer += f"- {reqs.get('spm_stpm', '')}\n"
            answer += f"- {reqs.get('minimum_requirements', '')}\n"
            links = local.get('application_links', {})
            if links.get('entry_requirements'):
                answer += f"\nMore info: {links['entry_requirements']}"
            return answer
        
        return None
    
    def _get_fees_answer(self, user_text: str) -> Optional[str]:
        """Get fee information with direct link"""
        admission = self.faix_data.get('admission', {})
        local = admission.get('undergraduate_local', {})
        links = local.get('application_links', {})
        fee_url = links.get('fees', 'https://bendahari.utem.edu.my/ms/jadual-yuran-pelajar.html')
        
        # Return link directly for direct access
        return fee_url
    
    def _get_career_answer(self, user_text: str) -> Optional[str]:
        """Get career opportunities information"""
        programmes = self.faix_data.get('programmes', {})
        undergraduate = programmes.get('undergraduate', [])
        
        all_careers = []
        for prog in undergraduate:
            careers = prog.get('career_opportunities', [])
            prog_name = prog.get('name', '')
            for career in careers:
                all_careers.append((career, prog_name))
        
        if any(kw in user_text for kw in ['ai', 'artificial intelligence']):
            for prog in undergraduate:
                if 'artificial intelligence' in prog.get('name', '').lower():
                    careers = prog.get('career_opportunities', [])
                    if careers:
                        career_list = '\n'.join([f"- {c}" for c in careers])
                        return f"**Career Opportunities for AI Graduates:**\n\n{career_list}"
        
        if any(kw in user_text for kw in ['security', 'cyber']):
            for prog in undergraduate:
                if 'security' in prog.get('name', '').lower():
                    careers = prog.get('career_opportunities', [])
                    if careers:
                        career_list = '\n'.join([f"- {c}" for c in careers])
                        return f"**Career Opportunities for Cybersecurity Graduates:**\n\n{career_list}"
        
        # General career info
        if all_careers:
            unique_careers = list(set([c[0] for c in all_careers]))[:10]
            career_list = '\n'.join([f"- {c}" for c in unique_careers])
            return f"**Career Opportunities for FAIX Graduates:**\n\n{career_list}"
        
        return None
    
    def _get_facility_answer(self, user_text: str) -> Optional[str]:
        """Get facility information"""
        facilities = self.faix_data.get('facilities', {})
        available = facilities.get('available', [])
        booking = facilities.get('booking_system', '')
        laboratories = facilities.get('laboratories', {})
        
        user_lower = user_text.lower()
        
        # Check if user is asking specifically about labs
        lab_keywords = ['lab', 'laboratory', 'laboratories', 'makmal', 'ai lab', 'ai labs', 'cybersec', 'cybersecurity lab', 'where is', 'location']
        is_lab_query = any(kw in user_lower for kw in lab_keywords)
        
        # If booking system link exists, return it directly for booking queries
        booking_keywords = ['booking', 'book', 'reserve', 'tempahan']
        if booking and any(kw in user_lower for kw in booking_keywords):
            return booking
        
        answer = ""
        
        # If asking about labs specifically, show lab details
        if is_lab_query and laboratories:
            ai_labs = laboratories.get('ai_labs', [])
            cybersec_labs = laboratories.get('cybersec_labs', [])
            
            if ai_labs or cybersec_labs:
                answer = "**FAIX Laboratories:**\n\n"
                
                if ai_labs:
                    answer += "**AI Labs:**\n"
                    for lab in ai_labs:
                        answer += f"- {lab.get('name', '')}\n"
                        answer += f"  Block: {lab.get('block', '')}\n"
                        answer += f"  {lab.get('level', '')}\n\n"
                
                if cybersec_labs:
                    answer += "**CyberSec Labs:**\n"
                    for lab in cybersec_labs:
                        answer += f"- {lab.get('name', '')}\n"
                        answer += f"  Block: {lab.get('block', '')}\n"
                        answer += f"  {lab.get('level', '')}\n\n"
                
                if booking:
                    answer += f"**Room Booking System:** {booking}\n"
                
                return answer
        
        # General facilities answer
        if available:
            answer = "**FAIX Facilities:**\n\n"
            for f in available:
                answer += f"- {f}\n"
        
        if booking:
            answer += f"\n**Room Booking System:** {booking}"
        
        return answer if answer else None
    
    def _get_academic_resources_answer(self, user_text: str) -> Optional[str]:
        """Get academic resources information"""
        resources = self.faix_data.get('academic_resources', {})
        portal = resources.get('ulearn_portal', '')
        available = resources.get('resources', [])
        
        user_lower = user_text.lower()
        
        # If asking specifically about uLearn portal, return link directly
        portal_keywords = ['ulearn', 'portal', 'learning portal', 'online learning']
        if portal and any(kw in user_lower for kw in portal_keywords):
            return portal
        
        answer = "**Academic Resources:**\n\n"
        for r in available:
            answer += f"- {r}\n"
        if portal:
            answer += f"\n**uLearn Portal:** {portal}"
        
        return answer
    
    def _get_research_answer(self, user_text: str) -> Optional[str]:
        """Get research focus information"""
        research = self.faix_data.get('research_focus', [])
        
        if research:
            answer = "**FAIX Research Focus Areas:**\n\n"
            for r in research:
                answer += f"- {r}\n"
            return answer
        
        return None
    
    def _get_staff_by_name(self, user_text_lower: str, user_text_original: str) -> Optional[str]:
        """Search for a specific staff member by name/keywords. Returns None if no specific staff found."""
        staff_contacts = self.faix_data.get('staff_contacts', {})
        departments = staff_contacts.get('departments', {})
        
        if not departments:
            return None
        
        # Collect all staff members from all departments
        all_staff = []
        for dept_key, dept_info in departments.items():
            if isinstance(dept_info, dict):
                dept_name = dept_info.get('name', '')
                staff_list = dept_info.get('staff', [])
                if isinstance(staff_list, list):
                    for staff in staff_list:
                        if isinstance(staff, dict):
                            staff['department'] = dept_name
                            all_staff.append(staff)
        
        # Try to match staff by name or keywords
        matched_staff = []
        query_words = [w.strip() for w in user_text_lower.split() 
                      if len(w.strip()) > 2 and w.strip() not in ['who', 'is', 'the', 'contact', 'info', 'information', 'about', 'for']]
        
        if not query_words:
            return None
        
        for staff in all_staff:
            staff_name = staff.get('name', '').lower()
            staff_keywords = [kw.lower() for kw in staff.get('keywords', [])]
            
            # Check if any query word matches staff name or keywords
            match_score = 0
            for query_word in query_words:
                # Check name match
                if query_word in staff_name:
                    match_score += 2
                # Check keyword match
                if any(query_word in kw or kw in query_word for kw in staff_keywords):
                    match_score += 1
            
            if match_score > 0:
                matched_staff.append((staff, match_score))
        
        # Sort by match score and return best matches
        if not matched_staff:
            return None
        
        matched_staff.sort(key=lambda x: x[1], reverse=True)
        # Get top matches (same score)
        top_score = matched_staff[0][1]
        best_matches = [staff for staff, score in matched_staff if score == top_score]
        
        # Format staff details
        if len(best_matches) == 1:
            staff = best_matches[0]
            answer = f"**{staff.get('name', 'Unknown')}**\n\n"
            answer += f"- **Position:** {staff.get('position', 'N/A')}\n"
            if staff.get('department'):
                answer += f"- **Department:** {staff['department']}\n"
            answer += f"- **Email:** {staff.get('email', 'N/A')}\n"
            if staff.get('phone') and staff['phone'] != '-':
                answer += f"- **Phone:** {staff['phone']}\n"
            if staff.get('office') and staff['office'] != '-':
                answer += f"- **Office:** {staff['office']}\n"
            return answer
        else:
            # Multiple matches - list them all
            answer = f"Found {len(best_matches)} matching staff member(s):\n\n"
            for i, staff in enumerate(best_matches[:5], 1):
                answer += f"{i}. **{staff.get('name', 'Unknown')}**\n"
                answer += f"   - Position: {staff.get('position', 'N/A')}\n"
                if staff.get('department'):
                    answer += f"   - Department: {staff['department']}\n"
                answer += f"   - Email: {staff.get('email', 'N/A')}\n"
                answer += "\n"
            return answer
    
    def _get_contact_answer(self, user_text: str) -> Optional[str]:
        """Get contact information - searches for specific staff members first, then general contact"""
        user_lower = user_text.lower()
        
        # Check for general staff category queries (academic staff, administrative staff, etc.)
        staff_contacts = self.faix_data.get('staff_contacts', {})
        departments = staff_contacts.get('departments', {})
        
        # Check for general staff/faculty queries that should return ALL staff or let LLM handle
        general_staff_keywords = [
            'who are working', 'who works', 'who work', 'working in faix', 'working at faix',
            'staff in faix', 'staff at faix', 'faculty members', 'faculty in faix',
            'people working', 'people in faix', 'who all', 'list of staff', 'list staff',
            'all staff', 'all faculty', 'show me staff', 'show staff', 'staff members'
        ]
        
        # If it's a general query, return None to let LLM handle it with full context
        if any(kw in user_lower for kw in general_staff_keywords):
            # For general queries, let LLM generate response with full staff list from context
            return None
        
        # Handle "academic staff" queries
        if any(kw in user_lower for kw in ['academic staff', 'academic', 'lecturers', 'professors']):
            academic_dept = departments.get('academic', {})
            if academic_dept and isinstance(academic_dept, dict):
                academic_staff = academic_dept.get('staff', [])
                if academic_staff:
                    answer = f"**Academic Staff ({len(academic_staff)} members):**\n\n"
                    for i, staff in enumerate(academic_staff[:10], 1):  # Limit to first 10
                        name = staff.get('name', 'Unknown')
                        position = staff.get('position', '')
                        email = staff.get('email', '')
                        answer += f"{i}. **{name}**\n"
                        if position:
                            answer += f"   - Position: {position}\n"
                        if email:
                            answer += f"   - Email: {email}\n"
                        answer += "\n"
                    if len(academic_staff) > 10:
                        answer += f"... and {len(academic_staff) - 10} more academic staff members.\n"
                    return answer
        
        # Handle "administrative staff" queries
        if any(kw in user_lower for kw in ['administrative staff', 'admin staff', 'administration']):
            admin_dept = departments.get('administration', {})
            if admin_dept and isinstance(admin_dept, dict):
                admin_staff = admin_dept.get('staff', [])
                if admin_staff:
                    answer = f"**Administrative Staff ({len(admin_staff)} members):**\n\n"
                    for i, staff in enumerate(admin_staff, 1):
                        name = staff.get('name', 'Unknown')
                        position = staff.get('position', '')
                        email = staff.get('email', '')
                        answer += f"{i}. **{name}**\n"
                        if position:
                            answer += f"   - Position: {position}\n"
                        if email:
                            answer += f"   - Email: {email}\n"
                        answer += "\n"
                    return answer
        
        # First, try to find a specific staff member by name
        # But only if the query looks like it's asking for a specific person
        # Check if query contains name-like patterns or specific person indicators
        specific_person_indicators = [
            'who is', 'tell me about', 'contact for', 'email for', 'phone for',
            'info for', 'information about', 'details about', 'contact info for'
        ]
        
        # Only try name matching if query suggests looking for a specific person
        # OR if query words are very short/specific (likely a name)
        query_words = [w.strip() for w in user_lower.split() 
                      if len(w.strip()) > 2 and w.strip() not in ['who', 'are', 'is', 'the', 'contact', 'info', 'information', 'about', 'for', 'in', 'at', 'faix']]
        
        is_likely_specific_query = (
            any(indicator in user_lower for indicator in specific_person_indicators) or
            (len(query_words) == 1 and len(query_words[0]) > 3) or  # Single word that's not too short
            (len(query_words) == 2 and all(len(w) > 3 for w in query_words))  # Two words that look like names
        )
        
        if is_likely_specific_query:
            staff_answer = self._get_staff_by_name(user_lower, user_text)
            if staff_answer:
                return staff_answer
        else:
            # For general queries, return None to let LLM handle with full context
            return None
        
        # No specific staff member found - return general contact information
        faculty_info = self.faix_data.get('faculty_info', {})
        contact = faculty_info.get('contact', {})
        address = faculty_info.get('address', {})
        
        if contact:
            answer = "**FAIX Contact Information:**\n\n"
            if contact.get('email'):
                answer += f"- **Email:** {contact['email']}\n"
            if contact.get('phone'):
                answer += f"- **Phone:** {contact['phone']}\n"
            if contact.get('website'):
                answer += f"- **Website:** {contact['website']}\n"
            
            if address:
                addr_str = f"{address.get('street', '')}, {address.get('postcode', '')} {address.get('city', '')}, {address.get('state', '')}"
                answer += f"\n**Address:** {addr_str}"
            
            return answer
        
        return None
    
    def _get_schedule_answer(self, user_text: str) -> Optional[str]:
        """Get answer about academic schedule/timetable - provides explanation and links"""
        user_lower = user_text.lower()
        
        # Timetable links for different programs
        TIMETABLE_LINKS = {
            'baxi': 'https://faix.utem.edu.my/en/academics/academic-resources/timetable/32-baxi-jadualwaktu-sem1-sesi-2025-2026/file.html',
            'baxz': 'https://faix.utem.edu.my/en/academics/academic-resources/timetable/31-baxz-jadualwaktu-sem1-sesi-2025-2026/file.html',
            'master': 'https://faix.utem.edu.my/en/academics/academic-resources/timetable/30-jadual-master-sem1-2025-2026-v3-faix/file.html',
        }
        
        # Detect program type from user query
        detected_program = None
        if 'baxi' in user_lower and 'baxz' not in user_lower:
            detected_program = 'baxi'
        elif 'baxz' in user_lower:
            detected_program = 'baxz'
        elif any(kw in user_lower for kw in ['master', 'maxd', 'maxz', 'bridging', 'postgraduate', 'graduate']):
            detected_program = 'master'
        
        # Check if user is asking about timetable/schedule
        # More comprehensive detection including variations
        is_schedule_query = any(kw in user_lower for kw in [
            'timetable', 'schedule', 'jadual', 'class schedule', 'my schedule', 
            'when is', 'when are', 'time table', 'time-table', 'what is the schedule',
            'what is schedule', 'show schedule', 'show timetable', 'get schedule',
            'academic schedule', 'class timetable', 'course schedule'
        ])
        
        # Also check for "what is" + schedule-related words
        if not is_schedule_query:
            if 'what is' in user_lower or 'what are' in user_lower:
                if any(kw in user_lower for kw in ['schedule', 'timetable', 'jadual', 'time']):
                    is_schedule_query = True
        
        if not is_schedule_query:
            return None
        
        # Provide simple explanation and appropriate link(s)
        if detected_program == 'baxi':
            response = (
                "You can find the complete **BAXI (Bachelor of Computer Science - Artificial Intelligence)** "
                "timetable for Semester 1 Session 2025/2026 on the FAIX website.\n\n"
                "The timetable includes schedules for all BAXI groups (S1G1, S1G2, S2G1, S2G2, S3G1, S3G2, etc.) "
                "with detailed class times, rooms, and lecturers.\n\n"
                f"📅 **View Complete BAXI Timetable:**\n{TIMETABLE_LINKS['baxi']}"
            )
            return response
        
        elif detected_program == 'baxz':
            response = (
                "You can find the complete **BAXZ (Bachelor of Computer Science - Cybersecurity)** "
                "timetable for Semester 1 Session 2025/2026 on the FAIX website.\n\n"
                "The timetable includes schedules for all BAXZ groups (S1G1, S1G2, S2G1, S2G2, S3G1, etc.) "
                "with detailed class times, rooms, and lecturers.\n\n"
                f"📅 **View Complete BAXZ Timetable:**\n{TIMETABLE_LINKS['baxz']}"
            )
            return response
        
        elif detected_program == 'master':
            response = (
                "You can find the complete **Master Program** timetable for Semester 1 Session 2025/2026 on the FAIX website.\n\n"
                "The timetable includes schedules for:\n"
                "- MAXD (Master of Artificial Intelligence) - Full Time and Part Time\n"
                "- MAXZ (Master of Cybersecurity) - Full Time and Part Time\n"
                "- BRIDGING Program\n\n"
                f"📅 **View Complete Master Program Timetable:**\n{TIMETABLE_LINKS['master']}"
            )
            return response
        
        else:
            # General schedule query - provide all links
            response = (
                "You can find the complete academic timetables for Semester 1 Session 2025/2026 on the FAIX website.\n\n"
                "**Available Timetables:**\n\n"
                "📅 **BAXI (Bachelor of Computer Science - Artificial Intelligence)**\n"
                f"{TIMETABLE_LINKS['baxi']}\n\n"
                "📅 **BAXZ (Bachelor of Computer Science - Cybersecurity)**\n"
                f"{TIMETABLE_LINKS['baxz']}\n\n"
                "📅 **Master Programs (MAXD, MAXZ, BRIDGING)**\n"
                f"{TIMETABLE_LINKS['master']}\n\n"
                "Each timetable includes detailed schedules with class times, rooms, lecturers, and course information "
                "for all groups and programs."
            )
            return response
    
    def _search_faix_faqs(self, user_text: str) -> Optional[str]:
        """Search through FAQs in FAIX data"""
        faqs = self.faix_data.get('faqs', [])
        
        best_match = None
        best_score = 0
        
        for faq in faqs:
            question = faq.get('question', '').lower()
            # Simple keyword matching
            keywords = question.split()
            user_keywords = user_text.split()
            
            matches = sum(1 for kw in user_keywords if kw in question)
            if matches > best_score:
                best_score = matches
                best_match = faq
        
        if best_match and best_score >= 2:
            return best_match.get('answer', '')
        
        return None
    
    def _init_database(self):
        """Initialize database-backed knowledge base"""
        logger.info("Initializing FAQ knowledge base from database")
        
        try:
            # Load all FAQ entries from database
            entries = FAQEntry.objects.filter(is_active=True)
            
            if not entries.exists():
                logger.warning("No FAQ entries found in database. Consider running migration script.")
                self.entries = []
                self.vectorizer = TfidfVectorizer()
                self.question_vectors = None
                return
        except Exception as e:
            # Handle case where table doesn't exist yet (migrations not run)
            if 'no such table' in str(e).lower() or 'does not exist' in str(e).lower():
                logger.warning("Database table for FAQ entries not found yet. This is normal before running migrations. Error: %s", e)
                logger.info("Initializing knowledge base with empty entries. Run migrations to populate FAQs.")
            else:
                logger.warning("Database error during knowledge base initialization: %s", e)
            self.entries = []
            self.vectorizer = TfidfVectorizer()
            self.question_vectors = None
            return
        
        # Convert to list of dicts for processing
        self.entries = []
        questions = []
        
        for entry in entries:
            entry_dict = {
                'id': entry.id,
                'question': entry.question,
                'answer': entry.answer,
                'category': entry.category,
                'keywords': entry.get_keywords_list(),
            }
            self.entries.append(entry_dict)
            questions.append(entry.question)
        
        # Preprocess and vectorize questions
        clean_questions = [self.preprocess(q) for q in questions]
        self.vectorizer = TfidfVectorizer()
        self.question_vectors = self.vectorizer.fit_transform(clean_questions)
        
        logger.debug(f"Loaded {len(self.entries)} FAQ entries from database")
    
    def _init_csv(self, csv_path: str):
        """Initialize CSV-backed knowledge base (fallback mode)"""
        import pandas as pd
        self.df = pd.read_csv(csv_path).fillna("")
        
        self.df["keywords"] = self.df["keywords"].apply(
            lambda x: [kw.strip().lower() for kw in str(x).split(",") if kw.strip()]
        )
        
        # Preprocess all questions before vectorizing
        clean_questions = self.df["question"].apply(self.preprocess)
        self.vectorizer = TfidfVectorizer()
        self.question_vectors = self.vectorizer.fit_transform(clean_questions)
        
        logger.debug(f"Loaded {len(self.df)} entries from CSV fallback")
    
    def preprocess(self, text: str) -> str:
        """Clean and normalize text"""
        text = str(text).lower()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        return text.strip()
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        return text.split()
    
    def retrieve(self, intent: Optional[str], user_text: str) -> Optional[str]:
        """
        Retrieve answer based on intent and user text (cached for performance).
        
        Args:
            intent: Detected intent/category
            user_text: User's query text
            
        Returns:
            Answer string or None if not found
        """
        if not intent or not isinstance(intent, str):
            return None
        
        # PERFORMANCE OPTIMIZATION: Check cache first
        cache_key = hash((intent.lower(), user_text.strip()[:200]))
        if cache_key in self._retrieve_cache:
            return self._retrieve_cache[cache_key]
        
        intent = intent.lower()
        user_clean = self.preprocess(user_text)
        user_keywords = self.extract_keywords(user_clean)
        
        result = None
        try:
            if self.use_database:
                result = self._retrieve_from_database(intent, user_text, user_keywords, user_clean)
            else:
                result = self._retrieve_from_csv(intent, user_text, user_keywords, user_clean)
        except Exception as e:
            print(f"Warning: Error in knowledge base retrieval: {e}")
            import traceback
            traceback.print_exc()
            result = None
        
        # Cache the result (limit cache size to 2000 entries)
        if len(self._retrieve_cache) > 2000:
            # Clear half when cache gets too large (simple LRU)
            self._retrieve_cache = dict(list(self._retrieve_cache.items())[1000:])
        self._retrieve_cache[cache_key] = result
        
        return result
    
    def _retrieve_from_database(self, intent: str, user_text: str, 
                                user_keywords: List[str], user_clean: str) -> Optional[str]:
        """Retrieve answer from database"""
        # Filter entries by category/intent
        matching_entries = [
            entry for entry in self.entries
            if entry['category'].lower() == intent
        ]
        
        if not matching_entries:
            # Fallback: semantic search across all entries
            return self._semantic_search(user_text, user_clean)
        
        # Try semantic search first if available
        if self.use_semantic_search and self.semantic_search and self.semantic_search.is_available():
            try:
                # Use semantic search on matching entries
                results = self.semantic_search.find_similar_with_metadata(
                    user_text,
                    matching_entries,
                    text_field='question',
                    top_k=3,
                    threshold=0.3
                )
                
                if results:
                    best_entry, score = results[0]
                    # Update view count
                    try:
                        entry_obj = FAQEntry.objects.get(id=best_entry['id'])
                        entry_obj.view_count += 1
                        entry_obj.save(update_fields=['view_count'])
                    except FAQEntry.DoesNotExist:
                        pass
                    return best_entry['answer']
            except Exception as e:
                print(f"Warning: Semantic search failed, using keyword matching: {e}")
        
        # Fallback to keyword matching
        scores = []
        for entry in matching_entries:
            entry_keywords = entry['keywords']
            keyword_score = sum(1 for kw in user_keywords if kw in entry_keywords)
            scores.append((entry, keyword_score))
        
        if not scores:
            return self._semantic_search(user_text, user_clean)
        
        # Get best match
        best_entry, kw_score = max(scores, key=lambda x: x[1])
        
        # If no keyword match, use semantic search
        if kw_score == 0:
            return self._semantic_search(user_text, user_clean)
        
        # Update view count in database
        try:
            entry_obj = FAQEntry.objects.get(id=best_entry['id'])
            entry_obj.view_count += 1
            entry_obj.save(update_fields=['view_count'])
        except FAQEntry.DoesNotExist:
            pass
        
        return best_entry['answer']
    
    def _retrieve_from_csv(self, intent: str, user_text: str,
                           user_keywords: List[str], user_clean: str) -> Optional[str]:
        """Retrieve answer from CSV (fallback mode)"""
        # MINIMUM RELEVANCE THRESHOLD for TF-IDF matching
        MIN_TFIDF_THRESHOLD = 0.15
        
        # Filter with case insensitivity
        subset = self.df[self.df["category"].str.lower() == intent]
        
        if subset.empty:
            # Semantic fallback
            try:
                if self.question_vectors is None or not hasattr(self, 'vectorizer'):
                    return None
                query_vec = self.vectorizer.transform([user_clean])
                similarity = cosine_similarity(query_vec, self.question_vectors)[0]
                best_idx = similarity.argmax()
                best_score = similarity[best_idx]
                
                # Reject low-relevance matches
                if best_score < MIN_TFIDF_THRESHOLD:
                    print(f"CSV TF-IDF match rejected: score {best_score:.3f} below threshold")
                    return None
                    
                return self.df.iloc[best_idx]["answer"]
            except Exception as e:
                print(f"Warning: Semantic fallback failed in CSV mode: {e}")
                return None
        
        scores = []
        for idx, row in subset.iterrows():
            entry_keywords = row["keywords"]
            keyword_score = sum(1 for kw in user_keywords if kw in entry_keywords)
            scores.append((idx, keyword_score))
        
        if not scores:
            return None
        
        best_keyword_idx, kw_score = max(scores, key=lambda x: x[1])
        
        # Semantic fallback if no keyword match
        if kw_score == 0:
            try:
                if self.question_vectors is None or not hasattr(self, 'vectorizer'):
                    # No keyword match and no vectors - don't return random answer
                    return None
                query_vec = self.vectorizer.transform([user_clean])
                similarity = cosine_similarity(query_vec, self.question_vectors)[0]
                best_idx = similarity.argmax()
                best_score = similarity[best_idx]
                
                # Reject low-relevance matches
                if best_score < MIN_TFIDF_THRESHOLD:
                    print(f"CSV TF-IDF match rejected: score {best_score:.3f} below threshold")
                    return None
                    
                return self.df.iloc[best_idx]["answer"]
            except Exception as e:
                print(f"Warning: Semantic fallback failed in CSV mode: {e}")
                return None
        
        return self.df.iloc[best_keyword_idx]["answer"]
    
    def _semantic_search(self, user_text: str, user_clean: str) -> Optional[str]:
        """Perform semantic search across all entries"""
        # MINIMUM RELEVANCE THRESHOLD: Reject matches below this similarity score
        # This prevents gibberish queries from returning random answers
        MIN_TFIDF_THRESHOLD = 0.15
        
        # Try transformer-based semantic search first
        if self.use_semantic_search and self.semantic_search and self.semantic_search.is_available():
            try:
                if self.use_database:
                    results = self.semantic_search.find_similar_with_metadata(
                        user_text,
                        self.entries,
                        text_field='question',
                        top_k=1,
                        threshold=0.3
                    )
                    if results:
                        entry, score = results[0]
                        # Update view count
                        try:
                            entry_obj = FAQEntry.objects.get(id=entry['id'])
                            entry_obj.view_count += 1
                            entry_obj.save(update_fields=['view_count'])
                        except FAQEntry.DoesNotExist:
                            pass
                        return entry['answer']
                else:
                    # For CSV mode, convert to list of dicts
                    questions = self.df['question'].tolist()
                    results = self.semantic_search.find_similar(
                        user_text,
                        questions,
                        top_k=1,
                        threshold=0.3
                    )
                    if results:
                        question, score = results[0]
                        matching_row = self.df[self.df['question'] == question]
                        if not matching_row.empty:
                            return matching_row.iloc[0]['answer']
            except Exception as e:
                print(f"Warning: Semantic search failed, using TF-IDF: {e}")
        
        # Fallback to TF-IDF cosine similarity
        # Fix: Use shape[0] for sparse matrices instead of len() (sparse matrices don't support len())
        if self.question_vectors is None:
            return None
        
        # Check if sparse matrix is empty using shape[0] instead of len()
        # This prevents "sparse array length is ambiguous" error
        try:
            if hasattr(self.question_vectors, 'shape'):
                if self.question_vectors.shape[0] == 0:
                    return None
            else:
                return None
        except Exception as e:
            print(f"Warning: Error checking question_vectors: {e}")
            return None
        
        try:
            query_vec = self.vectorizer.transform([user_clean])
            similarity = cosine_similarity(query_vec, self.question_vectors)[0]
            best_idx = similarity.argmax()
            best_score = similarity[best_idx]
            
            # CRITICAL: Reject matches with very low similarity to prevent irrelevant responses
            # This prevents gibberish like "asdjiashjidfohqwf" from returning random FAQ answers
            if best_score < MIN_TFIDF_THRESHOLD:
                print(f"TF-IDF match rejected: score {best_score:.3f} below threshold {MIN_TFIDF_THRESHOLD}")
                return None
                
        except Exception as e:
            print(f"Warning: Error in TF-IDF similarity calculation: {e}")
            return None
        
        if self.use_database:
            if best_idx < len(self.entries):
                entry = self.entries[best_idx]
                # Update view count
                try:
                    entry_obj = FAQEntry.objects.get(id=entry['id'])
                    entry_obj.view_count += 1
                    entry_obj.save(update_fields=['view_count'])
                except FAQEntry.DoesNotExist:
                    pass
                return entry['answer']
        else:
            return self.df.iloc[best_idx]["answer"]
        
        return None
    
    def get_answer(self, intent: Optional[str], user_text: str) -> str:
        """
        Get answer for the query, with fallback message if not found.
        Prioritizes FAIX JSON data, then falls back to database/CSV only if needed.
        
        Args:
            intent: Detected intent/category
            user_text: User's query text
            
        Returns:
            Answer string
        """
        user_text_lower = user_text.lower() if user_text else ""
        
        # Try FAIX JSON data first (primary data source)
        faix_answer = self.get_faix_answer(intent, user_text)
        if faix_answer:
            # Don't automatically add handbook - let the chatbot ask the user first
            # This allows the user to decide if they need the handbook
            return faix_answer
        
        # For specific FAIX-related queries, don't fall back to database to avoid wrong answers
        # Only fall back for general queries
        faix_keywords = [
            'faix', 'program', 'programme', 'bcsai', 'bcscs', 'dean', 'vision', 'mission',
            'admission', 'fee', 'tuition', 'career', 'facility', 'research', 'department'
        ]
        
        # If query contains FAIX keywords but we didn't get an answer, provide helpful message
        if any(kw in user_text_lower for kw in faix_keywords):
            return (
                "I couldn't find specific information about that in the FAIX database. "
                "Please try rephrasing your question or contact the FAIX office directly at faix@utem.edu.my for assistance."
            )
        
        # Fall back to database/CSV retrieval only for non-FAIX-specific queries
        answer = self.retrieve(intent, user_text)
        if answer is None:
            return (
                "I couldn't find the exact information. "
                "Try asking about FAIX programmes, admission, fees, career opportunities, or contact information."
            )
        
        # Don't automatically add handbook - let the chatbot ask the user first
        # This allows the user to decide if they need the handbook
        
        return answer

    def get_documents(
        self,
        intent: Optional[str],
        user_text: str,
        top_k: int = 3,
    ) -> List[Dict]:
        """
        Retrieve FAQ-style documents for use as RAG context.

        Each document is a dict with at least:
            - question
            - answer
            - category
            - score (similarity score, best first)
        """
        intent_norm = intent.lower() if isinstance(intent, str) else None
        user_clean = self.preprocess(user_text)
        
        # For program_info queries, return programs from JSON data as documents
        if intent_norm == 'program_info':
            programmes = self.faix_data.get('programmes', {})
            undergraduate = programmes.get('undergraduate', [])
            postgraduate = programmes.get('postgraduate', [])
            user_text_lower = user_text.lower() if user_text else ""
            
            docs = []
            
            # Check if query is about undergraduate programs
            if any(kw in user_text_lower for kw in ['undergraduate', 'bachelor', 'degree']):
                # Check if asking about a specific program
                is_specific = any(code in user_text_lower for code in ['bcsai', 'bcscs', 'baxi', 'baxz', 'ai program', 'security program'])
                
                if is_specific:
                    # Return full details for specific program queries
                    for prog in undergraduate:
                        prog_code = prog.get('code', '').upper()
                        prog_name = prog.get('name', '').lower()
                        if (prog_code in user_text_lower.upper() or 
                            ('ai' in user_text_lower and 'artificial intelligence' in prog_name) or
                            ('security' in user_text_lower and 'security' in prog_name)):
                            docs.append({
                                "question": f"What is {prog.get('name', '')}?",
                                "answer": self._format_program_details(prog),
                                "category": "program_info",
                                "score": 0.9,
                            })
                else:
                    # Return concise format for general undergraduate queries
                    prog_list = []
                    for prog in undergraduate:
                        name = prog.get('name', '')
                        code = prog.get('code', '')
                        duration = prog.get('duration', '')
                        if 'artificial intelligence' in name.lower():
                            focus_hint = "AI and Machine Learning"
                        elif 'security' in name.lower():
                            focus_hint = "Cybersecurity"
                        else:
                            focus_areas = prog.get('focus_areas', [])
                            focus_hint = focus_areas[0] if focus_areas else ""
                        prog_list.append(f"- **{name}** ({code}) - {duration} - Focus: {focus_hint}")
                    
                    answer = f"**Undergraduate Programmes at FAIX:**\n\n" + '\n'.join(prog_list) + "\n\n💡 Ask about a specific program (e.g., 'Tell me about BAXI') for more details."
                    docs.append({
                        "question": "What undergraduate programmes does FAIX offer?",
                        "answer": answer,
                        "category": "program_info",
                        "score": 0.9,
                    })
                
                if docs:
                    return docs[:top_k]
            
            # Check if query is about postgraduate programs
            if any(kw in user_text_lower for kw in ['master', 'postgraduate', 'graduate']):
                for prog in postgraduate:
                    docs.append({
                        "question": f"What is {prog.get('name', '')}?",
                        "answer": f"**{prog.get('name', '')}** ({prog.get('code', '')})\n  - Type: {prog.get('type', '')}\n  - Focus: {prog.get('focus', '')}",
                        "category": "program_info",
                        "score": 0.9,
                    })
                if docs:
                    return docs[:top_k]
            
            # For general program queries, return all programs
            # Return undergraduate programs first (most common query)
            for prog in undergraduate:
                docs.append({
                    "question": f"What is {prog.get('name', '')}?",
                    "answer": self._format_program_details(prog),
                    "category": "program_info",
                    "score": 0.85,
                })
            
            # Add postgraduate programs
            for prog in postgraduate:
                docs.append({
                    "question": f"What is {prog.get('name', '')}?",
                    "answer": f"**{prog.get('name', '')}** ({prog.get('code', '')})\n  - Type: {prog.get('type', '')}\n  - Focus: {prog.get('focus', '')}",
                    "category": "program_info",
                    "score": 0.8,
                })
            
            if docs:
                return docs[:top_k]

        # Database-backed mode
        if self.use_database:
            if not getattr(self, "entries", None):
                return []

            # Optional filtering by category/intent
            if intent_norm:
                candidate_entries = [
                    e for e in self.entries
                    if isinstance(e.get("category"), str)
                    and e["category"].lower() == intent_norm
                ]
                if not candidate_entries:
                    candidate_entries = self.entries
            else:
                candidate_entries = self.entries

            # Semantic search if available
            if (
                self.use_semantic_search
                and self.semantic_search
                and self.semantic_search.is_available()
            ):
                try:
                    results = self.semantic_search.find_similar_with_metadata(
                        user_text,
                        candidate_entries,
                        text_field="question",
                        top_k=top_k,
                        threshold=0.2,
                    )
                    docs = []
                    for entry, score in results:
                        docs.append(
                            {
                                "question": entry.get("question", ""),
                                "answer": entry.get("answer", ""),
                                "category": entry.get("category", ""),
                                "score": float(score),
                            }
                        )
                    if docs:
                        return docs
                except Exception as e:
                    print(f"Warning: Semantic search for documents failed: {e}")

            # TF-IDF fallback across all entries
            # Fix: Check if question_vectors exists properly
            if not hasattr(self, "question_vectors") or self.question_vectors is None:
                return []
            # Check if sparse matrix is empty using shape[0] instead of len()
            try:
                if hasattr(self.question_vectors, 'shape') and self.question_vectors.shape[0] == 0:
                    return []
            except Exception:
                return []

            query_vec = self.vectorizer.transform([user_clean])
            similarity = cosine_similarity(query_vec, self.question_vectors)[0]

            # Get indices sorted by similarity (descending)
            ranked_indices = similarity.argsort()[::-1][:top_k]
            
            # IMPROVEMENT: Minimum relevance threshold to avoid irrelevant matches
            MIN_RELEVANCE_THRESHOLD = 0.15  # Reject matches below 15% similarity
            
            docs: List[Dict] = []
            for idx in ranked_indices:
                if 0 <= idx < len(self.entries):
                    score = float(similarity[idx])
                    # Skip low-relevance matches
                    if score < MIN_RELEVANCE_THRESHOLD:
                        continue
                    entry = self.entries[idx]
                    docs.append(
                        {
                            "question": entry.get("question", ""),
                            "answer": entry.get("answer", ""),
                            "category": entry.get("category", ""),
                            "score": score,
                        }
                    )
            return docs

        # CSV-backed mode
        if not hasattr(self, "df"):
            return []

        try:
            # Optional category filter
            if intent_norm:
                subset = self.df[
                    self.df["category"].str.lower() == intent_norm
                ]
            else:
                subset = self.df

            if subset.empty:
                subset = self.df

            query_vec = self.vectorizer.transform([user_clean])
            similarity = cosine_similarity(query_vec, self.question_vectors)[0]

            # Restrict to subset indices if filtering
            if subset is not self.df:
                subset_indices = subset.index.to_list()
                # Build (global_idx, score) pairs only for subset rows
                pairs = [(i, similarity[i]) for i in subset_indices]
            else:
                pairs = list(enumerate(similarity))

            # Sort by score, take top_k
            ranked = sorted(pairs, key=lambda x: x[1], reverse=True)[:top_k]

            docs: List[Dict] = []
            for idx, score in ranked:
                row = self.df.iloc[idx]
                docs.append(
                    {
                        "question": str(row.get("question", "")),
                        "answer": str(row.get("answer", "")),
                        "category": str(row.get("category", "")),
                        "score": float(score),
                    }
                )
            return docs
        except Exception as e:
            print(f"Warning: CSV document retrieval failed: {e}")
            return []
        
    def refresh(self):
        """Refresh knowledge base from database (useful after updates)"""
        if self.use_database:
            self._init_database()
        else:
            if self.csv_path:
                self._init_csv(self.csv_path)

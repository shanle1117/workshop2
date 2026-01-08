import os
import sys
import json
import uuid
import hashlib
import threading
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.core.cache import cache

# Setup structured logging (reduced verbosity for cleaner startup)
logger = logging.getLogger('faix_chatbot')
logger.setLevel(logging.WARNING)  # Only show warnings/errors during startup

# Create console handler if not exists
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.WARNING)  # Only warnings/errors by default
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Separate logger for chat operations (INFO level)
chat_logger = logging.getLogger('faix_chatbot.chat')
chat_logger.setLevel(logging.INFO)
if not chat_logger.handlers:
    chat_handler = logging.StreamHandler()
    chat_handler.setLevel(logging.INFO)
    chat_handler.setFormatter(formatter)
    chat_logger.addHandler(chat_handler)

# Setup paths for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from django_app.models import (
    UserSession, Conversation, Message, FAQEntry, ResponseFeedback
)
from src.query_preprocessing import QueryProcessor
from src.knowledge_base import KnowledgeBase
from src.conversation_manager import process_conversation
from src.llm_client import get_llm_client, LLMError
from src.agents import get_agent, retrieve_for_agent, check_staff_data_available, check_schedule_data_available, _get_staff_documents, _get_schedule_documents
from src.prompt_builder import build_messages

# Initialize global instances
query_processor = QueryProcessor()
# Use JSON-only mode (no database) - all data comes from data/separated/*.json files
knowledge_base = KnowledgeBase(use_database=False)

# Print clean startup summary (after all initialization)
import sys
def print_startup_summary():
    """Print a clean, simple startup summary"""
    print("\n" + "="*60)
    print("FAIX Chatbot - Ready")
    print("="*60)
    print("✓ Query Processor")
    print("✓ Knowledge Base (JSON)")
    if knowledge_base.faix_data:
        sections = len([k for k in knowledge_base.faix_data.keys() if knowledge_base.faix_data[k]])
        print(f"✓ {sections} data sections loaded")
    if knowledge_base.use_semantic_search and knowledge_base.semantic_search:
        print("✓ Semantic search")
    print("="*60 + "\n")

# Delay summary until after Django startup completes
import threading
def delayed_summary():
    import time
    time.sleep(0.5)  # Wait for Django to finish initializing
    print_startup_summary()

threading.Thread(target=delayed_summary, daemon=True).start()

# Cached tokens for fast staff-name detection in queries
STAFF_NAME_TOKENS: Set[str] = set()
STAFF_TOKENS_INITIALISED = False


def _init_staff_name_tokens() -> None:
    """
    Build a set of lowercase tokens derived from staff names and keywords.
    This lets us quickly detect when a query is actually about a known staff member,
    even if the query doesn't contain generic staff keywords.
    """
    global STAFF_NAME_TOKENS, STAFF_TOKENS_INITIALISED
    if STAFF_TOKENS_INITIALISED:
        return

    try:
        staff_docs = _get_staff_documents()
    except Exception:
        staff_docs = []

    tokens: Set[str] = set()
    for staff in staff_docs:
        # Name tokens - extract all meaningful name parts
        name = str(staff.get("name", "")).lower()
        # Remove titles and common words
        name = name.replace("professor", "").replace("associate", "").replace("ts.", "").replace("dr.", "").replace("gs.", "")
        for part in name.replace(".", " ").replace(",", " ").split():
            part = part.strip()
            # Include tokens of length 3 or more (changed from > 3 to >= 3)
            # This captures names like "choo", "yun", "ahmad", etc.
            if len(part) >= 3 and part not in ['bin', 'binti', 'the', 'a', 'an']:
                tokens.add(part)

        # Keyword tokens
        kw = str(staff.get("keywords", "")).lower()
        for part in kw.replace(",", " ").split():
            part = part.strip()
            if len(part) >= 3:  # Changed from > 3 to >= 3
                tokens.add(part)

    STAFF_NAME_TOKENS = tokens
    STAFF_TOKENS_INITIALISED = True


def match_staff_by_name(user_message: str, staff_docs: List[Dict]) -> List[Dict]:
    """
    Match staff members by name from user query.
    Returns list of matching staff members with full details.
    
    Handles:
    - Full names: "Burhanuddin", "Dr. Ahmad Zulkifli"
    - Partial names: "Ahmad", "Zulkifli"
    - Titles: "Dr.", "Prof.", "Professor"
    - Case-insensitive matching
    """
    if not staff_docs:
        return []
    
    user_message_lower = user_message.lower()
    
    # Remove common titles and words that aren't names
    title_words = ['dr.', 'doctor', 'prof.', 'professor', 'who is', 'who are', 'contact', 
                   'email', 'phone', 'for', 'the', 'a', 'an', 'info', 'information', 'about']
    
    # Extract potential name parts from query
    query_words = [w.strip() for w in user_message_lower.split() 
                   if w.strip() and w.strip() not in title_words and len(w.strip()) > 2]
    
    if not query_words:
        return []
    
    matched_staff = []
    
    for staff in staff_docs:
        staff_name = staff.get('name', '').lower()
        if not staff_name:
            continue
        
        # Check if any query word matches the staff name
        # Match if query word is in staff name or vice versa
        name_parts = staff_name.split()
        
        # Check for exact match or significant overlap
        match_score = 0
        for query_word in query_words:
            # Exact match in name parts
            if query_word in name_parts:
                match_score += 2
            # Partial match (query word contains name part or vice versa)
            elif any(query_word in part or part in query_word for part in name_parts if len(part) > 3):
                match_score += 1
            # Full name contains query word
            elif query_word in staff_name:
                match_score += 1
        
        # If we have a good match (at least one significant match)
        if match_score >= 1:
            matched_staff.append(staff)
    
    return matched_staff


def format_staff_details(staff: Dict) -> str:
    """Format staff member details in a readable markdown format."""
    name = staff.get('name', 'N/A')
    position = staff.get('role', staff.get('position', 'N/A'))
    department = staff.get('department', 'N/A')
    email = staff.get('email', 'N/A')
    phone = staff.get('phone', 'N/A')
    office = staff.get('office', 'N/A')
    
    details = [f"**{name}**"]
    
    if position and position != 'N/A':
        details.append(f"- **Position**: {position}")
    
    if department and department != 'N/A':
        details.append(f"- **Department**: {department}")
    
    if email and email != 'N/A' and email != '-':
        details.append(f"- **Email**: {email}")
    
    if phone and phone != 'N/A' and phone != '-':
        details.append(f"- **Phone**: {phone}")
    
    if office and office != 'N/A' and office != '-':
        details.append(f"- **Office**: {office}")
    
    return "\n".join(details)

# Multi-language response dictionaries
MULTILANG_GREETINGS = {
    'en': "Hello! I'm the FAIX AI Chatbot. How can I help you today?",
    'ms': "Hai! Saya FAIX AI Chatbot. Bagaimana saya boleh membantu anda hari ini?",
    'zh': "你好！我是FAIX AI聊天机器人。今天有什么可以帮助您的？",
    'ar': "مرحباً! أنا روبوت FAIX للدردشة. كيف يمكنني مساعدتك اليوم؟",
}

MULTILANG_FAREWELLS = {
    'en': "Thank you for using FAIX AI Chatbot! Have a great day!",
    'ms': "Terima kasih kerana menggunakan FAIX AI Chatbot! Semoga hari anda menyenangkan!",
    'zh': "感谢您使用FAIX AI聊天机器人！祝您有美好的一天！",
    'ar': "شكراً لاستخدام روبوت FAIX للدردشة! أتمنى لك يوماً سعيداً!",
}

MULTILANG_FALLBACK_HELP = {
    'en': (
        "I'm here to help! You can ask me about:\n"
        "- FAIX programs and courses\n"
        "- Registration procedures\n"
        "- Staff contacts\n"
        "- Academic schedules\n"
        "- Fees and tuition\n\n"
        "What would you like to know?"
    ),
    'ms': (
        "Saya di sini untuk membantu! Anda boleh bertanya tentang:\n"
        "- Program dan kursus FAIX\n"
        "- Prosedur pendaftaran\n"
        "- Hubungan kakitangan\n"
        "- Jadual akademik\n"
        "- Yuran dan bayaran\n\n"
        "Apa yang anda ingin tahu?"
    ),
    'zh': (
        "我在这里帮助您！您可以询问：\n"
        "- FAIX项目和课程\n"
        "- 注册程序\n"
        "- 教职员工联系方式\n"
        "- 学术日程\n"
        "- 学费和费用\n\n"
        "您想了解什么？"
    ),
    'ar': (
        "أنا هنا لمساعدتك! يمكنك السؤال عن:\n"
        "- برامج ودورات FAIX\n"
        "- إجراءات التسجيل\n"
        "- جهات اتصال الموظفين\n"
        "- الجداول الأكاديمية\n"
        "- الرسوم الدراسية\n\n"
        "ماذا تريد أن تعرف؟"
    ),
}

MULTILANG_NOT_FOUND = {
    'en': "I couldn't find the exact information for your query. Try asking about course info, registration, staff contacts, or program information.",
    'ms': "Saya tidak dapat mencari maklumat tepat untuk pertanyaan anda. Cuba tanya tentang maklumat kursus, pendaftaran, hubungan kakitangan, atau maklumat program.",
    'zh': "我找不到您查询的确切信息。请尝试询问课程信息、注册、教职员工联系方式或项目信息。",
    'ar': "لم أتمكن من العثور على المعلومات المحددة لاستفسارك. حاول السؤال عن معلومات الدورة أو التسجيل أو جهات اتصال الموظفين أو معلومات البرنامج.",
}

MULTILANG_REPHRASE = {
    'en': "I'm sorry, I couldn't process your query. Could you please rephrase your question?",
    'ms': "Maaf, saya tidak dapat memproses pertanyaan anda. Bolehkah anda menyatakan semula soalan anda?",
    'zh': "抱歉，我无法处理您的查询。您能否重新表述您的问题？",
    'ar': "عذراً، لم أتمكن من معالجة استفسارك. هل يمكنك إعادة صياغة سؤالك؟",
}

MULTILANG_GIBBERISH_RESPONSE = {
    'en': "I'm sorry, I didn't understand that. Could you please rephrase your question in a clearer way? You can ask me about FAIX programs, registration, staff contacts, schedules, or fees.",
    'ms': "Maaf, saya tidak faham. Bolehkah anda menyatakan semula soalan anda dengan lebih jelas? Anda boleh bertanya tentang program FAIX, pendaftaran, hubungan kakitangan, jadual, atau yuran.",
    'zh': "抱歉，我不明白。您能否用更清晰的方式重新表述您的问题？您可以询问关于FAIX项目、注册、教职员工联系方式、日程或费用的问题。",
    'ar': "عذراً، لم أفهم ذلك. هل يمكنك إعادة صياغة سؤالك بشكل أوضح؟ يمكنك السؤال عن برامج FAIX، التسجيل، جهات اتصال الموظفين، الجداول، أو الرسوم.",
}

MULTILANG_CANT_UNDERSTAND = {
    'en': "I'm sorry, I couldn't understand your question. Could you please rephrase it? I can help you with:\n- FAIX programs and courses\n- Registration and admission\n- Staff contacts\n- Academic schedules\n- Fees and tuition",
    'ms': "Maaf, saya tidak dapat memahami soalan anda. Bolehkah anda menyatakan semula? Saya boleh membantu dengan:\n- Program dan kursus FAIX\n- Pendaftaran dan kemasukan\n- Hubungan kakitangan\n- Jadual akademik\n- Yuran dan bayaran",
    'zh': "抱歉，我无法理解您的问题。您能重新表述一下吗？我可以帮助您：\n- FAIX项目和课程\n- 注册和入学\n- 教职员工联系方式\n- 学术日程\n- 学费和费用",
    'ar': "عذراً، لم أتمكن من فهم سؤالك. هل يمكنك إعادة صياغته؟ يمكنني مساعدتك في:\n- برامج ودورات FAIX\n- التسجيل والقبول\n- جهات اتصال الموظفين\n- الجداول الأكاديمية\n- الرسوم الدراسية",
}

MULTILANG_NO_INFO = {
    'en': "I don't have information about that topic. I can help you with FAIX programs, registration, staff contacts, schedules, and fees. Please contact the FAIX office at faix@utem.edu.my for other inquiries.",
    'ms': "Saya tidak mempunyai maklumat tentang topik itu. Saya boleh membantu dengan program FAIX, pendaftaran, hubungan kakitangan, jadual, dan yuran. Sila hubungi pejabat FAIX di faix@utem.edu.my untuk pertanyaan lain.",
    'zh': "我没有关于该主题的信息。我可以帮助您了解FAIX项目、注册、教职员工联系方式、日程和费用。其他咨询请联系FAIX办公室：faix@utem.edu.my",
    'ar': "ليس لدي معلومات حول هذا الموضوع. يمكنني مساعدتك في برامج FAIX والتسجيل وجهات اتصال الموظفين والجداول والرسوم. يرجى الاتصال بمكتب FAIX على faix@utem.edu.my للاستفسارات الأخرى.",
}


def is_off_topic_query(text: str) -> bool:
    """
    Detect if the user's query is clearly off-topic (not related to FAIX/education).
    Returns True if the query is about something unrelated to the chatbot's scope.
    """
    if not text or len(text.strip()) < 2:
        return False
    
    text_lower = text.lower().strip()

    # Ensure staff name tokens are initialised for staff-related detection
    _init_staff_name_tokens()
    
    # Keywords that indicate FAIX-related topics (keep these)
    faix_related_keywords = [
        # General education/university
        'faix', 'utem', 'university', 'fakulti', 'faculty', 'college',
        'student', 'pelajar', 'study', 'belajar', 'learn',
        # Programs/courses
        'program', 'programme', 'course', 'kursus', 'degree', 'ijazah',
        'diploma', 'master', 'phd', 'bachelor', 'sarjana',
        'bcsai', 'bcscs', 'mtdsa', 'mcsss', 'ai', 'artificial intelligence',
        'cybersecurity', 'cyber security', 'data science', 'computer',
        # Registration/admission
        'register', 'registration', 'pendaftaran', 'daftar', 'admission',
        'kemasukan', 'apply', 'application', 'enroll', 'enrollment',
        'cgpa', 'muet', 'spm', 'stpm', 'requirement', 'syarat',
        # Staff/contact
        'staff', 'lecturer', 'pensyarah', 'professor', 'dean', 'dekan',
        'contact', 'hubungi', 'email', 'phone', 'office', 'pejabat',
        # Schedule/academic
        'schedule', 'jadual', 'timetable', 'semester', 'academic',
        'calendar', 'deadline', 'date', 'tarikh', 'exam', 'peperiksaan',
        # Fees
        'fee', 'fees', 'yuran', 'tuition', 'payment', 'bayaran', 'cost',
        # Facilities
        'facility', 'facilities', 'kemudahan', 'lab', 'laboratory', 'library',
        # Career/research
        'career', 'kerjaya', 'job', 'research', 'penyelidikan',
        # General chatbot
        'help', 'tolong', 'can you', 'boleh', 'what can', 'apa boleh',
        'hello', 'hi', 'hai', 'hey', 'bye', 'thanks', 'thank', 'terima kasih',
    ]
    
    # Check if any FAIX-related keyword is present
    has_faix_keyword = any(kw in text_lower for kw in faix_related_keywords)

    # Additional FAIX-related detection:
    # If the query mentions any known staff name/keyword token, treat it as in-scope
    if STAFF_NAME_TOKENS:
        for token in STAFF_NAME_TOKENS:
            if token in text_lower:
                return False  # Definitely related to FAIX staff
    
    if has_faix_keyword:
        return False  # Not off-topic
    
    # Common off-topic patterns (things clearly unrelated to education)
    off_topic_patterns = [
        'what is ', 'what are ', 'who is ', 'where is ', 'when is ',
        'how to make', 'how to cook', 'recipe', 'resepi',
        'weather', 'cuaca', 'news', 'berita',
        'movie', 'filem', 'music', 'lagu', 'song', 'game', 'permainan',
        'food', 'makanan', 'pizza', 'burger', 'nasi', 'makan',
        'sport', 'sukan', 'football', 'bola', 'basketball',
        'travel', 'melancong', 'holiday', 'cuti',
        'animal', 'haiwan', 'cat', 'kucing', 'dog', 'anjing',
        'car', 'kereta', 'bike', 'basikal',
        'phone', 'telefon', 'iphone', 'samsung', 'laptop',
        'joke', 'jenaka', 'funny', 'kelakar',
        'love', 'cinta', 'relationship',
        'health', 'kesihatan', 'medicine', 'ubat', 'doctor', 'doktor',
        'money', 'wang', 'bitcoin', 'crypto',
        'country', 'negara', 'politics', 'politik',
        'religion', 'agama',
    ]
    
    # Check if text starts with off-topic patterns and doesn't have FAIX keywords
    for pattern in off_topic_patterns:
        if pattern in text_lower:
            return True
    
    # If the query is very short (1-3 words) and not a greeting or FAIX keyword
    words = text_lower.split()
    if len(words) <= 3 and not has_faix_keyword:
        # Check if it's asking "what is X" where X is not FAIX-related
        if text_lower.startswith(('what is', 'what are', 'apa itu', 'apakah')):
            return True
    
    return False


def is_gibberish(text: str) -> bool:
    """
    Detect if the input text is gibberish/nonsensical.
    Returns True if the text appears to be random characters without meaning.
    """
    import re
    
    if not text or len(text.strip()) < 2:
        return True
    
    text = text.strip().lower()
    
    # Check if text is only punctuation or special characters
    cleaned = re.sub(r'[^\w\s]', '', text)
    if not cleaned.strip():
        return True
    
    # Check for repeated characters (like "aaaaaaa" or "asdfasdf")
    if len(set(cleaned.replace(' ', ''))) <= 3 and len(cleaned) > 5:
        return True
    
    # Check for keyboard mashing patterns (consecutive consonants without vowels)
    # This detects things like "asdfjkl", "qwerty" nonsense, "asdfgh"
    vowels = set('aeiouàáâãäåèéêëìíîïòóôõöùúûü')
    words = cleaned.split()
    
    for word in words:
        if len(word) > 4:
            # Count consecutive consonants
            max_consonants = 0
            current_consonants = 0
            for char in word:
                if char.isalpha() and char not in vowels:
                    current_consonants += 1
                    max_consonants = max(max_consonants, current_consonants)
                else:
                    current_consonants = 0
            
            # More than 5 consecutive consonants is likely gibberish
            if max_consonants > 5:
                return True
    
    # Check for very long words with no apparent structure (likely random typing)
    for word in words:
        if len(word) > 15 and not any(kw in word for kw in ['university', 'registration', 'information', 'undergraduate', 'postgraduate']):
            # Check if it looks like a real word (has reasonable vowel distribution)
            vowel_count = sum(1 for c in word if c in vowels)
            vowel_ratio = vowel_count / len(word) if word else 0
            # Normal English words have ~30-40% vowels, gibberish often has < 20% or > 60%
            if vowel_ratio < 0.15 or vowel_ratio > 0.65:
                return True
    
    return False


def is_inadequate_response(response: str) -> bool:
    """
    Detect if the LLM response indicates it couldn't understand or answer properly.
    Returns True if the response seems inadequate or indicates confusion.
    """
    if not response or len(response.strip()) < 10:
        return True
    
    response_lower = response.lower().strip()
    
    # Indicators that the response is inadequate or the LLM couldn't understand
    inadequate_indicators = [
        # Empty or very short
        'i am not sure',
        'i\'m not sure',
        'i do not know',
        'i don\'t know',
        'i cannot answer',
        'i can\'t answer',
        'unable to answer',
        'cannot provide',
        'can\'t provide',
        'not able to',
        'i have no information',
        'no information available',
        'this information is not available',
        'i am unable to',
        'i\'m unable to',
        # Confusion indicators
        'i do not understand',
        'i don\'t understand',
        'unclear question',
        'not clear what',
        'could you clarify',
        'what do you mean',
        'please clarify',
        # Off-topic indicators
        'this is outside my scope',
        'outside my knowledge',
        'beyond my capabilities',
        'not within my scope',
        # Generic filler responses
        'as an ai',
        'as a language model',
        'i apologize, but',
    ]
    
    for indicator in inadequate_indicators:
        if indicator in response_lower:
            return True
    
    # Check if response is just repeating the question or very generic
    if len(response.strip()) < 30 and '?' in response:
        return True
    
    return False


MULTILANG_ERROR_FALLBACK = {
    'en': "I apologize, but I'm having trouble processing your request. Please try rephrasing your question or contact the FAIX office for assistance.",
    'ms': "Maaf, saya menghadapi masalah memproses permintaan anda. Sila cuba nyatakan semula soalan anda atau hubungi pejabat FAIX untuk bantuan.",
    'zh': "抱歉，我在处理您的请求时遇到问题。请尝试重新表述您的问题或联系FAIX办公室寻求帮助。",
    'ar': "أعتذر، ولكنني أواجه مشكلة في معالجة طلبك. يرجى محاولة إعادة صياغة سؤالك أو الاتصال بمكتب FAIX للحصول على المساعدة.",
}

MULTILANG_STAFF_FALLBACK = {
    'en': "I can help you find staff contact information. Please try asking about specific departments (AI, Cybersecurity, Data Science) or staff roles.",
    'ms': "Saya boleh membantu anda mencari maklumat hubungan kakitangan. Sila cuba tanya tentang jabatan tertentu (AI, Keselamatan Siber, Sains Data) atau peranan kakitangan.",
    'zh': "我可以帮您找到教职员工联系信息。请尝试询问特定部门（人工智能、网络安全、数据科学）或员工角色。",
    'ar': "يمكنني مساعدتك في العثور على معلومات الاتصال بالموظفين. حاول السؤال عن أقسام محددة (الذكاء الاصطناعي، الأمن السيبراني، علوم البيانات) أو أدوار الموظفين.",
}

MULTILANG_FAQ_FALLBACK = {
    'en': "I can help you with information about FAIX programs, courses, registration, and more. Could you rephrase your question or ask about specific topics?",
    'ms': "Saya boleh membantu anda dengan maklumat tentang program FAIX, kursus, pendaftaran, dan banyak lagi. Bolehkah anda menyatakan semula soalan anda atau bertanya tentang topik tertentu?",
    'zh': "我可以帮您了解FAIX项目、课程、注册等信息。您能重新表述您的问题或询问特定话题吗？",
    'ar': "يمكنني مساعدتك بمعلومات حول برامج FAIX والدورات والتسجيل والمزيد. هل يمكنك إعادة صياغة سؤالك أو السؤال عن مواضيع محددة؟",
}

# Multi-language greeting/farewell keywords
MULTILANG_GREETING_KEYWORDS = {
    'en': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
    'ms': ['hai', 'helo', 'selamat pagi', 'selamat petang', 'selamat malam', 'apa khabar'],
    'zh': ['你好', '您好', '早上好', '下午好', '晚上好', '嗨'],
    'ar': ['مرحبا', 'أهلا', 'صباح الخير', 'مساء الخير'],
}

MULTILANG_FAREWELL_KEYWORDS = {
    'en': ['bye', 'goodbye', 'see you', 'thanks', 'thank you', 'thank'],
    'ms': ['selamat tinggal', 'jumpa lagi', 'terima kasih', 'bye'],
    'zh': ['再见', '拜拜', '谢谢', '感谢'],
    'ar': ['مع السلامة', 'وداعا', 'شكرا', 'إلى اللقاء'],
}

# Multi-language "what can you do" / capabilities responses
MULTILANG_CAPABILITIES = {
    'en': (
        "I'm the FAIX AI Chatbot! Here's what I can help you with:\n\n"
        "- **Programs & Courses** - Information about FAIX degree programs, courses, and curriculum\n"
        "- **Registration** - How to register, add/drop subjects, enrollment procedures\n"
        "- **Staff Contacts** - Find professors, lecturers, and department contacts\n"
        "- **Academic Schedule** - Semester dates, deadlines, timetables\n"
        "- **Fees & Tuition** - Fee schedules and payment information\n"
        "- **Facilities** - Labs, libraries, and campus resources\n\n"
        "Just ask me anything about FAIX! 😊"
    ),
    'ms': (
        "Saya FAIX AI Chatbot! Ini yang boleh saya bantu:\n\n"
        "- **Program & Kursus** - Maklumat tentang program ijazah FAIX, kursus, dan kurikulum\n"
        "- **Pendaftaran** - Cara mendaftar, tambah/gugur subjek, prosedur pendaftaran\n"
        "- **Hubungan Kakitangan** - Cari profesor, pensyarah, dan hubungan jabatan\n"
        "- **Jadual Akademik** - Tarikh semester, tarikh akhir, jadual waktu\n"
        "- **Yuran & Bayaran** - Jadual yuran dan maklumat pembayaran\n"
        "- **Kemudahan** - Makmal, perpustakaan, dan sumber kampus\n\n"
        "Tanya saya apa sahaja tentang FAIX! 😊"
    ),
    'zh': (
        "我是FAIX AI聊天机器人！以下是我可以帮助您的：\n\n"
        "- **项目和课程** - FAIX学位项目、课程和课程安排信息\n"
        "- **注册** - 如何注册、选课/退课、入学程序\n"
        "- **教职员工联系** - 查找教授、讲师和部门联系方式\n"
        "- **学术日程** - 学期日期、截止日期、时间表\n"
        "- **学费和费用** - 费用表和付款信息\n"
        "- **设施** - 实验室、图书馆和校园资源\n\n"
        "有任何关于FAIX的问题都可以问我！😊"
    ),
    'ar': (
        "أنا روبوت FAIX للدردشة! إليك ما يمكنني مساعدتك به:\n\n"
        "- **البرامج والدورات** - معلومات حول برامج درجات FAIX والدورات والمناهج\n"
        "- **التسجيل** - كيفية التسجيل، إضافة/حذف المواد، إجراءات الالتحاق\n"
        "- **جهات اتصال الموظفين** - البحث عن الأساتذة والمحاضرين وجهات اتصال الأقسام\n"
        "- **الجدول الأكاديمي** - تواريخ الفصل الدراسي، المواعيد النهائية، الجداول\n"
        "- **الرسوم والتعليم** - جداول الرسوم ومعلومات الدفع\n"
        "- **المرافق** - المختبرات والمكتبات وموارد الحرم الجامعي\n\n"
        "اسألني أي شيء عن FAIX! 😊"
    ),
}

# Keywords that indicate user is asking about chatbot capabilities
MULTILANG_CAPABILITY_KEYWORDS = {
    'en': ['what can you do', 'what do you do', 'what u can do', 'what u do', 'how can you help', 
           'what are you', 'who are you', 'your capabilities', 'help me', 'what can u do',
           'tell me what you can', 'show me what you can', 'what are your functions'],
    'ms': ['apa boleh buat', 'apa yang boleh', 'apa kamu boleh', 'siapa kamu', 'siapa awak',
           'apa fungsi', 'boleh tolong apa', 'macam mana boleh tolong', 'apa yang awak boleh'],
    'zh': ['你能做什么', '你会什么', '你是谁', '你的功能', '能帮我什么', '可以做什么', '有什么功能'],
    'ar': ['ماذا يمكنك أن تفعل', 'من أنت', 'ما هي قدراتك', 'كيف يمكنك مساعدتي'],
}


def detect_language_quick(text: str) -> str:
    """Quick language detection for greeting/farewell handling."""
    text_lower = text.lower()
    
    # Check for Chinese characters first (most reliable)
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return 'zh'
    
    # Check for Arabic characters
    for char in text:
        if '\u0600' <= char <= '\u06FF':
            return 'ar'
    
    # Check Malay-specific keywords
    malay_indicators = ['apa', 'bagaimana', 'saya', 'anda', 'hai', 'selamat', 'terima kasih', 
                        'khabar', 'boleh', 'tolong', 'mahu', 'hendak', 'pagi', 'petang', 'malam']
    for indicator in malay_indicators:
        if indicator in text_lower:
            return 'ms'
    
    # Default to English
    return 'en'


def get_multilang_response(response_dict: dict, language_code: str) -> str:
    """Get response in the appropriate language, with English fallback."""
    return response_dict.get(language_code, response_dict.get('en', ''))


def check_rate_limit(session_id: str, limit: int = 30, window: int = 60) -> tuple:
    """
    Rate limiting: Allow 'limit' requests per 'window' seconds per session.
    Returns (allowed: bool, error_message: str or None)
    """
    cache_key = f"rate_limit:{session_id}"
    count = cache.get(cache_key, 0)
    
    if count >= limit:
        logger.warning(f"Rate limit exceeded for session {session_id[:8]}...")
        return False, "Too many requests. Please wait a moment before sending more messages."
    
    cache.set(cache_key, count + 1, timeout=window)
    return True, None


def get_language_with_persistence(context: dict, detected_lang: str, confidence: float) -> str:
    """
    Get language code with session persistence.
    - If confidence is high (>0.7), update the preferred language
    - If confidence is low (<0.5), use stored preference
    - Otherwise, use detected language
    """
    stored_lang = context.get('preferred_language')
    
    # High confidence detection - update preference
    if confidence > 0.7:
        if stored_lang != detected_lang:
            logger.info(f"Language preference updated: {stored_lang} -> {detected_lang}")
        context['preferred_language'] = detected_lang
        return detected_lang
    
    # Low confidence - use stored preference if available
    if confidence < 0.5 and stored_lang:
        logger.debug(f"Using stored language preference: {stored_lang}")
        return stored_lang
    
    # Medium confidence or no stored preference - use detected
    if not stored_lang:
        context['preferred_language'] = detected_lang
    return detected_lang


def update_conversation_memory(context: dict, entities: dict, intent: str) -> dict:
    """
    Update conversation memory with extracted entities for context continuity.
    Stores mentioned courses, staff, topics across the conversation.
    """
    # Initialize memory if not exists
    if 'memory' not in context:
        context['memory'] = {
            'mentioned_courses': [],
            'mentioned_staff': [],
            'discussed_topics': [],
            'last_intent': None,
        }
    
    memory = context['memory']
    
    # Store course codes
    if entities.get('course_codes'):
        for code in entities['course_codes']:
            if code not in memory['mentioned_courses']:
                memory['mentioned_courses'].append(code)
        # Keep only last 5
        memory['mentioned_courses'] = memory['mentioned_courses'][-5:]
    
    # Store discussed topics (intents) - skip greetings/farewells
    if intent and intent not in ['greeting', 'farewell']:
        if intent not in memory['discussed_topics']:
            memory['discussed_topics'].append(intent)
        memory['discussed_topics'] = memory['discussed_topics'][-5:]
    
    memory['last_intent'] = intent
    context['memory'] = memory
    
    return context


def get_query_cache_key(user_message: str, agent_id: str, intent: str) -> str:
    """Generate cache key for query"""
    query_hash = hashlib.md5(f"{user_message}_{agent_id}_{intent}".encode()).hexdigest()
    return f"chat_response:{query_hash}"


def detect_yes_no_response(user_message: str) -> Optional[bool]:
    """
    Detect if user message is a yes/no response.
    Returns True for yes, False for no, None if not clear.
    """
    message_lower = user_message.lower().strip()
    
    # Yes patterns
    yes_patterns = ['yes', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay', 'okey', 
                    'correct', 'right', 'that\'s right', 'please', 'yes please',
                    'i need', 'i want', 'i would like', 'give me', 'show me',
                    'send me', 'provide', 'yes i need', 'yes i want', 'ya', 'yea']
    
    # No patterns
    no_patterns = ['no', 'nope', 'nah', 'not', "don't", "dont", 'no thanks', 
                   'no thank you', 'skip', 'maybe later', 'later', 'not now',
                   'i don\'t need', "i don't need", 'i dont need', 'no i dont',
                   'no i don\'t', 'cancel', 'never mind', 'not needed']
    
    # Check for yes
    if any(pattern in message_lower for pattern in yes_patterns):
        # Make sure it's not a double negative
        if not any(no_pattern in message_lower for no_pattern in ['no', 'not', 'don\'t', 'dont']):
            return True
    
    # Check for no
    if any(pattern in message_lower for pattern in no_patterns):
        return False
    
    return None


def should_ask_for_handbook(intent: str, user_message: str, context: dict) -> bool:
    """
    Determine if we should ask the user if they need the academic handbook.
    Returns True if we should ask, False otherwise.
    """
    user_message_lower = user_message.lower()
    is_handbook_query = 'handbook' in user_message_lower or 'academic handbook' in user_message_lower
    
    # If user explicitly asked about handbook, don't ask again
    if is_handbook_query:
        return False
    
    # If we already asked about handbook in this context, don't ask again
    if context.get('handbook_asked', False):
        return False
    
    # Ask for program_info intent
    if intent == 'program_info':
        return True
    
    return False


def handle_handbook_request(user_message: str, context: dict, language_code: str = 'en') -> Tuple[Optional[str], Optional[str], dict]:
    """
    Handle academic handbook requests - ask user if they need it, or provide if confirmed.
    Returns: (answer, pdf_url, updated_context)
    """
    import os
    from django.conf import settings
    
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'Academic_Handbook.pdf')
    pdf_exists = os.path.exists(pdf_path)
    
    # Check if we previously asked about handbook
    if context.get('handbook_asked', False):
        # Check if user confirmed
        yes_no = detect_yes_no_response(user_message)
        
        if yes_no is True:
            # User confirmed, provide handbook
            context['handbook_asked'] = False  # Reset flag
            if pdf_exists:
                pdf_url = settings.MEDIA_URL + 'Academic_Handbook.pdf'
                answer = get_multilang_response({
                    'en': "📚 Here is the Academic Handbook PDF with detailed program information, courses, academic policies, and graduation requirements.",
                    'ms': "📚 Berikut adalah PDF Buku Panduan Akademik dengan maklumat program terperinci, kursus, dasar akademik, dan keperluan graduasi.",
                    'zh': "📚 以下是包含详细课程信息、课程、学术政策和毕业要求的学术手册PDF。"
                }, language_code)
                return answer, pdf_url, context
            else:
                answer = get_multilang_response({
                    'en': "📚 I'm sorry, but the Academic Handbook PDF is not available on this system. Please contact the FAIX office at faix@utem.edu.my for access to the handbook.",
                    'ms': "📚 Maaf, PDF Buku Panduan Akademik tidak tersedia dalam sistem ini. Sila hubungi pejabat FAIX di faix@utem.edu.my untuk mendapatkan akses kepada buku panduan.",
                    'zh': "📚 抱歉，本系统不提供学术手册PDF。请联系FAIX办公室 faix@utem.edu.my 获取手册访问权限。"
                }, language_code)
                context['handbook_asked'] = False  # Reset flag
                return answer, None, context
        elif yes_no is False:
            # User declined
            context['handbook_asked'] = False  # Reset flag
            answer = get_multilang_response({
                'en': "No problem! If you need the Academic Handbook later, just let me know.",
                'ms': "Tiada masalah! Jika anda memerlukan Buku Panduan Akademik kemudian, beritahu saya sahaja.",
                'zh': "没问题！如果您以后需要学术手册，告诉我即可。"
            }, language_code)
            return answer, None, context
        # If unclear, continue conversation normally
    
    # If not asked yet, ask user if they need handbook
    context['handbook_asked'] = True
    answer = get_multilang_response({
        'en': "Would you like me to provide the Academic Handbook PDF? It contains detailed information about programs, courses, academic policies, and graduation requirements.",
        'ms': "Adakah anda ingin saya menyediakan PDF Buku Panduan Akademik? Ia mengandungi maklumat terperinci mengenai program, kursus, dasar akademik, dan keperluan graduasi.",
        'zh': "您需要我提供学术手册PDF吗？它包含有关课程、学术政策和毕业要求的详细信息。"
    }, language_code)
    
    return answer, None, context


def save_messages_async(conversation, user_message, answer, intent, confidence, entities):
    """Save messages asynchronously to avoid blocking response"""
    def _save():
        try:
            with transaction.atomic():
                Message.objects.create(
                    conversation=conversation,
                    role='user',
                    content=user_message,
                    intent=intent,
                    confidence=confidence,
                    entities=entities,
                )
                Message.objects.create(
                    conversation=conversation,
                    role='bot',
                    content=answer,
                    intent=intent,
                    confidence=confidence,
                )
                conversation.updated_at = timezone.now()
                if not conversation.title or conversation.title == "New Conversation":
                    conversation.title = user_message[:50] + ("..." if len(user_message) > 50 else "")
                conversation.save()
        except Exception as e:
            logger.error(f"Error saving messages async: {e}")
    
    thread = threading.Thread(target=_save)
    thread.daemon = True
    thread.start()


def get_or_create_session(session_id=None, user_id=None):
    """Get or create a user session"""
    if session_id:
        try:
            session = UserSession.objects.get(session_id=session_id, is_active=True)
            return session
        except UserSession.DoesNotExist:
            pass
    
    # Create new session
    session = UserSession.objects.create(
        session_id=str(uuid.uuid4()),
        user_id=user_id or None,
    )
    return session


def get_or_create_conversation(session, user_id=None):
    """Get or create a conversation for the session"""
    # Get the most recent active conversation or create a new one
    conversation = Conversation.objects.filter(
        session=session,
        is_active=True
    ).order_by('-created_at').first()
    
    if not conversation:
        conversation = Conversation.objects.create(
            session=session,
            user_id=user_id or None,
            title="New Conversation",
        )
    
    return conversation


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    """
    Chat API endpoint that processes user messages and returns bot responses.
    
    Expected JSON payload:
    {
        "message": "user message text",
        "session_id": "optional session id",
        "user_id": "optional user id",
        "agent_id": "optional conversational agent id (e.g., 'faq', 'schedule', 'staff')",
        "history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    
    Returns:
    {
        "response": "bot response text",
        "session_id": "session id",
        "conversation_id": "conversation id",
        "intent": "detected intent",
         "confidence": 0.85,
        "timestamp": "2024-01-01T12:00:00Z"
    }
    """
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        agent_id = data.get('agent_id')
        history = data.get('history') or []
        
        if not user_message:
            return JsonResponse({
                'error': 'Message is required'
            }, status=400)
        
        # Get or create session
        session = get_or_create_session(session_id, user_id)
        
        # Rate limiting check
        allowed, rate_error = check_rate_limit(session.session_id)
        if not allowed:
            return JsonResponse({
                'error': rate_error,
                'rate_limited': True
            }, status=429)
        
        # Get or create conversation
        conversation = get_or_create_conversation(session, user_id)
        
        # Get context from session
        context = session.context if session.context else {}
        
        # Initialize variables
        answer = None
        pdf_url = None
        user_message_lower = user_message.lower()
        is_fee_query = False  # Initialize for cache timeout calculation
        is_handbook_query = (
            'handbook' in user_message_lower or
            'academic handbook' in user_message_lower
        )
        
        # PERFORMANCE OPTIMIZATION: Early exit for simple greeting/farewell queries
        # Detect language early for greeting/farewell handling
        early_lang_code = detect_language_quick(user_message)
        
        # Check for greetings in all supported languages
        is_greeting = False
        for lang, keywords in MULTILANG_GREETING_KEYWORDS.items():
            if any(kw in user_message_lower for kw in keywords):
                is_greeting = True
                # Use the language of the matched keyword
                if lang != 'en':
                    early_lang_code = lang
                break
        
        if is_greeting:
            # Get language-specific greeting with cache key per language
            cache_key_greeting = f'greeting_response_{early_lang_code}'
            cached_greeting = cache.get(cache_key_greeting)
            if cached_greeting:
                answer = cached_greeting
            else:
                answer = get_multilang_response(MULTILANG_GREETINGS, early_lang_code)
                cache.set(cache_key_greeting, answer, timeout=86400)  # Cache for 24 hours
            
            intent = 'greeting'
            confidence = 0.9
            entities = {}
            
            # Save asynchronously and return immediately
            save_messages_async(conversation, user_message, answer, intent, confidence, entities)
            session.context = context
            session.save(update_fields=['context', 'updated_at'])
            
            return JsonResponse({
                'response': answer,
                'session_id': session.session_id,
                'conversation_id': conversation.id,
                'intent': intent,
                'confidence': confidence,
                'entities': entities,
                'timestamp': timezone.now().isoformat(),
                'pdf_url': None,
            })
        
        # Check for farewells in all supported languages
        is_farewell = False
        for lang, keywords in MULTILANG_FAREWELL_KEYWORDS.items():
            if any(kw in user_message_lower for kw in keywords):
                is_farewell = True
                # Use the language of the matched keyword
                if lang != 'en':
                    early_lang_code = lang
                break
        
        if is_farewell:
            # Get language-specific farewell with cache key per language
            cache_key_farewell = f'farewell_response_{early_lang_code}'
            cached_farewell = cache.get(cache_key_farewell)
            if cached_farewell:
                answer = cached_farewell
            else:
                answer = get_multilang_response(MULTILANG_FAREWELLS, early_lang_code)
                cache.set(cache_key_farewell, answer, timeout=86400)
            
            intent = 'farewell'
            confidence = 0.9
            entities = {}
            
            save_messages_async(conversation, user_message, answer, intent, confidence, entities)
            session.context = context
            session.save(update_fields=['context', 'updated_at'])
            
            return JsonResponse({
                'response': answer,
                'session_id': session.session_id,
                'conversation_id': conversation.id,
                'intent': intent,
                'confidence': confidence,
                'entities': entities,
                'timestamp': timezone.now().isoformat(),
                'pdf_url': None,
            })
        
        # Check for "what can you do" / capabilities queries in all languages
        is_capability_query = False
        for lang, keywords in MULTILANG_CAPABILITY_KEYWORDS.items():
            if any(kw in user_message_lower for kw in keywords):
                is_capability_query = True
                # Use the language of the matched keyword
                if lang != 'en':
                    early_lang_code = lang
                break
        
        if is_capability_query:
            # Get language-specific capabilities response
            cache_key_caps = f'capabilities_response_{early_lang_code}'
            cached_caps = cache.get(cache_key_caps)
            if cached_caps:
                answer = cached_caps
            else:
                answer = get_multilang_response(MULTILANG_CAPABILITIES, early_lang_code)
                cache.set(cache_key_caps, answer, timeout=86400)
            
            intent = 'help'
            confidence = 0.95
            entities = {}
            
            save_messages_async(conversation, user_message, answer, intent, confidence, entities)
            session.context = context
            session.save(update_fields=['context', 'updated_at'])
            
            logger.info(f"Capabilities query detected, lang={early_lang_code}")
            
            return JsonResponse({
                'response': answer,
                'session_id': session.session_id,
                'conversation_id': conversation.id,
                'intent': intent,
                'confidence': confidence,
                'entities': entities,
                'timestamp': timezone.now().isoformat(),
                'pdf_url': None,
            })

        # EARLY GIBBERISH DETECTION: Catch nonsensical input before expensive processing
        # This prevents random typing like "asdjiashjidfohqwf" from returning irrelevant FAQ answers
        if is_gibberish(user_message):
            logger.info(f"Gibberish detected: '{user_message[:30]}...'")
            answer = get_multilang_response(MULTILANG_GIBBERISH_RESPONSE, early_lang_code)
            
            save_messages_async(conversation, user_message, answer, 'unknown', 0.0, {})
            session.context = context
            session.save(update_fields=['context', 'updated_at'])
            
            return JsonResponse({
                'response': answer,
                'session_id': session.session_id,
                'conversation_id': conversation.id,
                'intent': 'unknown',
                'confidence': 0.0,
                'entities': {},
                'timestamp': timezone.now().isoformat(),
                'pdf_url': None,
            })

        # OFF-TOPIC DETECTION: Catch questions clearly unrelated to FAIX/education
        # This prevents questions like "what is pizza" from returning irrelevant FAIX information
        if is_off_topic_query(user_message):
            logger.info(f"Off-topic query detected: '{user_message[:50]}...'")
            answer = get_multilang_response(MULTILANG_NO_INFO, early_lang_code)
            
            save_messages_async(conversation, user_message, answer, 'off_topic', 0.0, {})
            session.context = context
            session.save(update_fields=['context', 'updated_at'])
            
            return JsonResponse({
                'response': answer,
                'session_id': session.session_id,
                'conversation_id': conversation.id,
                'intent': 'off_topic',
                'confidence': 0.0,
                'entities': {},
                'timestamp': timezone.now().isoformat(),
                'pdf_url': None,
            })

        # STEP 1: Check data availability FIRST before NLP processing
        # This ensures we route to agents that have data available
        # NOTE: Frontend may send agent_id='faq' by default, but we override if query matches staff/schedule
        logger.debug(f"Initial agent_id: {agent_id}, message: '{user_message[:50]}...'")
        
        # PRIORITY 1: Check for staff name queries FIRST (before other routing)
        # This catches queries like "who is dr choo", "who is burhan", "burhan", etc.
        if check_staff_data_available():
            _init_staff_name_tokens()
            if STAFF_NAME_TOKENS:
                logger.debug(f"Staff name tokens initialized: {len(STAFF_NAME_TOKENS)} tokens")
                
                # Check if query contains any staff name tokens
                matched_tokens = [token for token in STAFF_NAME_TOKENS if token in user_message_lower]
                if matched_tokens:
                    # Found staff name token(s) - route to staff agent immediately
                    staff_docs = _get_staff_documents()
                    agent_id = 'staff'
                    logger.info(f"Staff agent routing: detected staff name token(s) '{matched_tokens[:3]}' in query")
                
                # Also check for "who is [name]" pattern (even if no token match yet)
                if not agent_id and user_message_lower.startswith('who is'):
                    # Extract potential name after "who is"
                    potential_name = user_message_lower.replace('who is', '').strip()
                    # Remove common words
                    for word in ['dr.', 'doctor', 'prof.', 'professor', 'the', 'a', 'an']:
                        potential_name = potential_name.replace(word, '').strip()
                    
                    # Check if any part matches staff tokens
                    if potential_name:
                        # Split potential name into words and check each
                        name_words = potential_name.split()
                        for word in name_words:
                            if len(word) > 2 and any(token in word or word in token for token in STAFF_NAME_TOKENS):
                                staff_docs = _get_staff_documents()
                                agent_id = 'staff'
                                logger.info(f"Staff agent routing: 'who is' pattern matched word '{word}'")
                                break
        
        # PRIORITY 2: Check for staff-related keywords (if not already routed by name)
        if not agent_id:
            # IMPORTANT: Exclude non-staff questions that might match staff keywords
            non_staff_keywords = [
                'established', 'founded', 'when was', 'history', 'facility', 'facilities',
                'lab', 'laboratory', 'laboratories', 'equipment', 'research', 'project',
                'program', 'programme', 'degree', 'course', 'schedule', 'calendar',
                'academic calendar', 'semester', 'registration', 'admission', 'fee', 'fees'
            ]
            is_non_staff_query = any(kw in user_message_lower for kw in non_staff_keywords)
            
            staff_keywords = [
                'contact', 'email', 'phone', 'professor', 'lecturer', 'staff', 'faculty member',
                'who can i contact', 'who can i', 'who should i email', 'who should i contact',
                'reach', 'get in touch', 'call', 'number', 'office', 'address',
                'administration', 'admin', 'registrar', 'secretary', 'academic staff',
                'who works', 'work in', 'works in', 'working in', 'coordinator'
            ]
            matched_keywords = [kw for kw in staff_keywords if kw in user_message_lower]
            
            # Only route to staff agent if:
            # 1. Staff keywords are present
            # 2. It's NOT a non-staff query (e.g., "when was FAIX established" shouldn't go to staff)
            # 3. It's specifically asking about contacting someone (not general info)
            if matched_keywords and not is_non_staff_query:
                # Additional check: ensure it's actually asking about contacts
                contact_intent_keywords = ['contact', 'email', 'phone', 'who can', 'who should', 'reach', 'get in touch']
                has_contact_intent = any(kw in user_message_lower for kw in contact_intent_keywords)
                
                if has_contact_intent:
                    # Check if staff data actually exists
                    staff_available = check_staff_data_available()
                    if staff_available:
                        staff_docs = _get_staff_documents()
                        agent_id = 'staff'
                        logger.info(f"Staff agent routing: {len(staff_docs)} staff, keywords={matched_keywords[:3]}")
        
        # Check for schedule-related keywords and verify schedule data exists
        if agent_id != 'staff':  # Don't override if we already set staff
            # More specific schedule keywords to avoid false positives
            schedule_keywords = [
                'schedule', 'timetable', 'jadual', 'academic calendar', 'semester', 'deadline',
                'when does the semester', 'when is the semester', 'when are classes',
                'important dates', 'academic year', 'class schedule', 'my schedule',
                'what is the schedule', 'what is schedule', 'show schedule', 'show timetable',
                'get schedule', 'course schedule', 'time table', 'time-table'
            ]
            # Also check for "what is" + schedule-related words
            if 'what is' in user_message_lower or 'what are' in user_message_lower:
                if any(kw in user_message_lower for kw in ['schedule', 'timetable', 'jadual', 'time']):
                    schedule_keywords.append('what is')  # This will match
            
            # Exclude non-schedule queries that might match "when"
            non_schedule_keywords = ['when was', 'when founded', 'when established', 'history']
            is_schedule_query = any(kw in user_message_lower for kw in schedule_keywords)
            is_non_schedule_query = any(kw in user_message_lower for kw in non_schedule_keywords)
            
            if is_schedule_query and not is_non_schedule_query:
                if check_schedule_data_available():
                    schedule_docs = _get_schedule_documents()
                    agent_id = 'schedule'
                    logger.info("Schedule agent routing activated")
        
        # STEP 2: Process query with NLP (as secondary check/confirmation)
        processed_query = query_processor.process_query(user_message)
        intent = processed_query.get('detected_intent', 'about_faix')
        confidence = processed_query.get('confidence_score', 0.0)
        entities = processed_query.get('extracted_entities', {})
        language_info = processed_query.get('language', {'code': 'en', 'name': 'English'})
        detected_lang = language_info.get('code', 'en')
        
        # CRITICAL: Override intent if we've already routed to staff agent
        # This prevents NLP from classifying staff queries as "contact" or "about_faix"
        if agent_id == 'staff':
            intent = 'staff_contact'
            confidence = max(confidence, 0.8)  # Boost confidence for staff queries
            logger.info(f"Intent overridden to 'staff_contact' for staff agent routing")
        
        # Apply language persistence - remember user's preferred language
        language_code = get_language_with_persistence(context, detected_lang, confidence)
        
        # Update conversation memory with entities for context continuity
        context = update_conversation_memory(context, entities, intent)
        
        logger.info(f"Query processed: intent={intent}, confidence={confidence:.2f}, lang={language_code}, agent={agent_id or 'none'}")
        
        # PERFORMANCE OPTIMIZATION: Check cache before expensive processing
        # Build cache key after we have intent (more accurate caching)
        cache_key = get_query_cache_key(user_message, agent_id or 'default', intent)
        cached_response = cache.get(cache_key)
        if cached_response:
            logger.debug("Cache hit - returning cached response")
            # Update session context asynchronously
            session.context = context
            session.save(update_fields=['context', 'updated_at'])
            # Save messages asynchronously
            save_messages_async(
                conversation, 
                user_message, 
                cached_response['response'], 
                cached_response['intent'], 
                cached_response.get('confidence', 0.0),
                cached_response.get('entities', {})
            )
            return JsonResponse(cached_response)
        
        # IMPROVEMENT: For about_faix with very low confidence, return helpful response
        # This prevents returning irrelevant FAQ answers for vague/unclear queries
        if intent == 'about_faix' and confidence < 0.25 and not agent_id:
            # Check if it's not a specific topic query
            specific_topic_keywords = [
                'program', 'course', 'fee', 'staff', 'contact', 'schedule', 'register',
                'admission', 'facility', 'department', 'yuran', 'kursus', 'pendaftaran'
            ]
            if not any(kw in user_message_lower for kw in specific_topic_keywords):
                logger.info("Low confidence about_faix - returning helpful response")
                answer = get_multilang_response(MULTILANG_FALLBACK_HELP, language_code)
                
                save_messages_async(conversation, user_message, answer, intent, confidence, entities)
                session.context = context
                session.save(update_fields=['context', 'updated_at'])
                
                return JsonResponse({
                    'response': answer,
                    'session_id': session.session_id,
                    'conversation_id': conversation.id,
                    'intent': intent,
                    'confidence': confidence,
                    'entities': entities,
                    'timestamp': timezone.now().isoformat(),
                    'pdf_url': None,
                })
        
        # Use NLP intent as confirmation - OVERRIDE agent_id if intent is staff_contact
        # This ensures staff queries are always routed correctly, even if name detection failed
        intent_to_agent = {
            'staff_contact': 'staff',
            'academic_schedule': 'schedule',
            'program_info': 'faq',       # Route program queries to FAQ (has FAIX data)
            'course_info': 'faq',        # Route course queries to FAQ (has FAIX data)
            'facility_info': 'faq',      # Route facility queries to FAQ (has FAIX data)
            'fees': 'faq',               # Route fee queries to FAQ (has fee information)
            'admission': 'faq',          # Route admission queries to FAQ (has FAIX data)
            'career': 'faq',             # Route career queries to FAQ (has FAIX data)
            'about_faix': 'faq',         # Route FAIX info queries to FAQ (has FAIX data)
            'research': 'faq',           # Route research queries to FAQ (has FAIX data)
            'academic_resources': 'faq', # Route academic resources to FAQ (has FAIX data)
            'registration': 'faq',       # Route registration queries to FAQ
        }
        
        # CRITICAL: If intent is staff_contact, ALWAYS route to staff agent (override any previous routing)
        if intent == 'staff_contact':
            previous_agent = agent_id
            agent_id = 'staff'
            logger.info(f"Intent-based routing: staff_contact -> staff agent (overriding previous agent={previous_agent})")
        elif not agent_id:
            # Only use intent mapping if agent_id not already set
            agent_id = intent_to_agent.get(intent)
            if agent_id:
                logger.info(f"Intent-based routing: {intent} -> {agent_id}")
            
            # Check for FAIX-related keywords and route to FAQ agent
            if not agent_id:
                faix_keywords = [
                    # Programs
                    'program', 'programme', 'degree', 'course', 'bcsai', 'bcscs', 'mtdsa', 'mcsss',
                    'undergraduate', 'postgraduate', 'master', 'bachelor', 'ai programme', 'cybersecurity',
                    # Admission
                    'admission', 'admit', 'apply', 'application', 'cgpa', 'muet', 'spm', 'stpm', 'eligibility',
                    'entry requirement', 'international student', 'local student',
                    # Fees
                    'fee', 'fees', 'tuition', 'yuran', 'bayaran', 'diploma fee', 'degree fee', 'payment', 'cost', 'scholarship',
                    # About FAIX
                    'about faix', 'faix', 'vision', 'mission', 'objective', 'objectives', 'dean', 'established',
                    'history', 'key highlight', 'department', 'departments', 'utem',
                    # Facilities & Resources
                    'facility', 'facilities', 'lab', 'laboratory', 'booking', 'ulearn', 'handbook', 'academic resource',
                    # Career & Research
                    'career', 'job', 'employment', 'opportunity', 'research', 'focus area', 'machine learning',
                    'data science', 'digital forensics', 'intelligent system'
                ]
                if any(kw in user_message_lower for kw in faix_keywords):
                    # Check if FAIX data is available
                    from src.agents import check_faix_data_available
                    if check_faix_data_available():
                        agent_id = 'faq'
                        logger.info("FAQ agent routing: FAIX keywords detected")
        
        # Final check: if still no agent_id and we have staff keywords, force staff agent
        # But only if it's actually a contact query (not a general info query)
        if not agent_id:
            contact_keywords = ['who can i contact', 'who should i contact', 'who should i email', 
                              'contact information', 'how do i contact', 'staff contact']
            if any(kw in user_message_lower for kw in contact_keywords) and not is_non_staff_query:
                if check_staff_data_available():
                    agent_id = 'staff'
        
        logger.info(f"Final routing: agent={agent_id or 'default'}, intent={intent}")

        # Normalise history into a compact, safe format
        history_messages = []
        if isinstance(history, list):
            for turn in history[-10:]:  # keep last 10 turns at most
                if not isinstance(turn, dict):
                    continue
                role = turn.get('role')
                content = turn.get('content')
                if role in ('user', 'assistant') and isinstance(content, str) and content.strip():
                    history_messages.append({'role': role, 'content': content.strip()})

        # Agent-based path: use LLM + RAG for all queries
        # Let LLM generate natural responses from context instead of hardcoded answers
        # This makes the chatbot feel more AI-driven and conversational
            
            agent = get_agent(agent_id)
            if not agent:
                return JsonResponse(
                    {'error': f"Unknown agent_id '{agent_id}'"},
                    status=400,
                )

            # Retrieve context for the agent (FAQ, schedule, staff, etc.)
            agent_context = retrieve_for_agent(
                agent_id=agent_id,
                user_text=user_message,
                knowledge_base=knowledge_base,
                intent=intent,
                top_k=3,
            )
            
            # Log staff context if available
            if agent_id == 'staff':
                staff_docs = agent_context.get('staff', [])
                logger.debug(f"Staff agent loaded {len(staff_docs)} members")
                
                # Log staff matches for context (but let LLM generate the response)
                matched_staff = match_staff_by_name(user_message, staff_docs)
                if matched_staff:
                    logger.info(f"Staff name match detected: {len(matched_staff)} matches - prioritizing matched staff in context")
                    # PRIORITY FIX: Put matched staff FIRST in the staff context so LLM sees them prominently
                    # This ensures the LLM finds the matched staff even if there are many staff members
                    matched_staff_list = matched_staff[:5]  # Limit to top 5
                    # Remove matched staff from full list to avoid duplicates
                    matched_names = {s.get('name', '').lower() for s in matched_staff_list}
                    remaining_staff = [s for s in staff_docs if s.get('name', '').lower() not in matched_names]
                    # Put matched staff first, then remaining staff
                    agent_context['staff'] = matched_staff_list + remaining_staff[:10]  # Limit total to 15 for context
                    # CRITICAL: Pass matched_staff separately so prompt builder can highlight them prominently
                    agent_context['matched_staff'] = matched_staff_list
                    logger.debug(f"Prioritized {len(matched_staff_list)} matched staff, added {len(remaining_staff[:10])} others")

            # PRIORITY CHECK: For FAQ agent queries about dean, vision, mission, faculty info, etc., check knowledge base first
            # This ensures we get direct answers for simple factual queries like "who is dean", "vision", "mission"
            if (agent_id == 'faq' or intent in ['about_faix', 'staff_contact']) and answer is None:
                # Check for factual queries (dean, vision, mission, established, etc.)
                user_message_lower_check = user_message.lower()
                factual_keywords = [
                    'who is dean', 'who is the dean', 'dean', 'head of faculty',
                    'vision', 'mission', 'what is the vision', 'what is the mission',
                    'faix vision', 'faix mission', 'when was faix', 'established',
                    'objective', 'objectives', 'what are the objectives', 'faix objectives',
                    'top management', 'management', 'leadership', 'who are the leaders'
                ]
                if any(kw in user_message_lower_check for kw in factual_keywords):
                    kb_factual_answer = knowledge_base.get_answer(intent, user_message)
                    if kb_factual_answer and 'couldn\'t find' not in kb_factual_answer.lower():
                        logger.info(f"Using knowledge base answer for factual query: {user_message[:50]}")
                        answer = kb_factual_answer
                        # Skip LLM call and use KB answer directly
            
            # PRIORITY CHECK: For schedule queries, check knowledge base first
            # This ensures we use the simple explanation + link approach instead of LLM-generated responses
            if (agent_id == 'schedule' or intent == 'academic_schedule') and answer is None:
                kb_schedule_answer = knowledge_base.get_answer(intent, user_message)
                if kb_schedule_answer and 'couldn\'t find' not in kb_schedule_answer.lower():
                    logger.info("Using knowledge base schedule answer (simple explanation + link)")
                    answer = kb_schedule_answer
                    # Skip LLM call and use KB answer directly
                    # Continue to response formatting below
                else:
                    # No KB answer, proceed with LLM
                    answer = None
            
            # PRIORITY CHECK: For staff queries, check knowledge base first for direct staff member matches
            # This ensures we retrieve staff data directly from JSON when a specific staff member is queried
            if (agent_id == 'staff' or intent == 'staff_contact') and answer is None:
                kb_staff_answer = knowledge_base.get_answer(intent, user_message)
                # Check if we got a specific staff member answer (not general contact info or "couldn't find")
                if kb_staff_answer and 'couldn\'t find' not in kb_staff_answer.lower() and 'FAIX Contact Information' not in kb_staff_answer:
                    logger.info("Using knowledge base staff answer (direct staff member match)")
                    answer = kb_staff_answer
                    # Skip LLM call and use KB answer directly
                # If it's general contact info or not found, let LLM handle it with context
            
            # Build LLM messages and call Llama via Ollama
            if answer is None:  # Only build messages if we don't have a KB answer
                messages = build_messages(
                    agent=agent,
                    user_message=user_message,
                    history=history_messages,
                    context=agent_context,
                    intent=intent,
                    language_code=language_code,
                )
            
            # Initialize answer and llm_client variables before try block
            llm_client = None
            if answer is None:
                answer = None

            try:
                if answer is not None:
                    # We already have a KB answer, skip LLM call
                    logger.info("Skipping LLM call - using KB answer")
                else:
                    # AI-DRIVEN APPROACH: Always use LLM to generate natural, conversational responses
                    # The LLM uses RAG context to provide accurate information while maintaining natural flow
                    llm_client = get_llm_client()
                    logger.info(f"LLM call: agent={agent_id}, lang={language_code}, intent={intent}")
                
                # Adjust max_tokens based on query complexity
                # Staff queries may need more detail, general queries can be concise
                if agent_id == 'staff':
                    max_tokens = 250  # Allow more detail for staff information
                elif intent in ['program_info', 'admission']:
                    max_tokens = 300  # Programs and admission need detailed explanations
                else:
                    max_tokens = 200  # Standard length for other queries
                
                # TIMEOUT HANDLING: Use shorter timeout for staff queries (they tend to be slower)
                import signal
                from contextlib import contextmanager
                
                @contextmanager
                def timeout_handler(timeout_seconds):
                    """Context manager for timeout handling"""
                    def timeout_signal(signum, frame):
                        raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
                    
                    # Set up signal handler (Unix only)
                    if hasattr(signal, 'SIGALRM'):
                        old_handler = signal.signal(signal.SIGALRM, timeout_signal)
                        signal.alarm(timeout_seconds)
                        try:
                            yield
                        finally:
                            signal.alarm(0)
                            signal.signal(signal.SIGALRM, old_handler)
                    else:
                        # Windows doesn't support SIGALRM, rely on LLM client timeout
                        yield
                
                # Set timeout based on agent type
                llm_timeout = 15 if agent_id == 'staff' else 20  # Reduced for shorter conversations
                
                try:
                    # AI-DRIVEN: Use moderate temperature for natural, conversational responses
                    # Temperature 0.5-0.7 balances accuracy with natural language flow
                    # Lower (0.2) was too robotic, higher (0.9) risks hallucinations
                    temperature = 0.6 if agent_id == 'staff' else 0.5  # Slightly higher for staff (more conversational)
                    llm_response = llm_client.chat(messages, max_tokens=max_tokens, temperature=temperature)
                    answer = llm_response.content
                    
                    # RESPONSE VALIDATION: Check if response matches intent
                    answer_lower = answer.lower()
                    invalid_responses = [
                        'no matching staff found',
                        'no matching',
                        'not found in database',
                        'could not find',
                        'unable to find'
                    ]
                    
                    # If response indicates "not found" but intent doesn't match, try knowledge base fallback
                    if any(invalid in answer_lower for invalid in invalid_responses):
                        # Check if this is actually a staff query
                        if intent != 'staff_contact' and agent_id == 'staff':
                            logger.warning(f"Staff agent returned 'not found' for non-staff intent: {intent}")
                            # Try knowledge base instead
                            kb_answer = knowledge_base.get_answer(intent, user_message)
                            if kb_answer and 'couldn\'t find' not in kb_answer.lower():
                                answer = kb_answer
                                logger.info("Using knowledge base fallback after invalid staff response")
                        
                        # For non-staff intents getting "not found", try knowledge base
                        elif intent not in ['staff_contact'] and any(invalid in answer_lower for invalid in invalid_responses):
                            logger.warning(f"Invalid response for intent {intent}: {answer[:100]}")
                            kb_answer = knowledge_base.get_answer(intent, user_message)
                            if kb_answer and 'couldn\'t find' not in kb_answer.lower():
                                answer = kb_answer
                                logger.info("Using knowledge base fallback after invalid response")
                    
                    # Validate response completeness
                    if len(answer.strip()) < 10:
                        logger.warning(f"Response too short: {answer}")
                        kb_answer = knowledge_base.get_answer(intent, user_message)
                        if kb_answer:
                            answer = kb_answer
                    
                    # CHECK FOR INADEQUATE RESPONSES: When agent can't understand or answer
                    if is_inadequate_response(answer):
                        logger.info(f"Inadequate response detected: {answer[:100]}...")
                        # Try knowledge base first
                        kb_answer = knowledge_base.get_answer(intent, user_message)
                        if kb_answer and not is_inadequate_response(kb_answer):
                            answer = kb_answer
                            logger.info("Using knowledge base fallback for inadequate response")
                        else:
                            # Use the "can't understand" fallback message
                            answer = get_multilang_response(MULTILANG_CANT_UNDERSTAND, language_code)
                            logger.info("Using 'can't understand' fallback response")
                
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"LLM call failed: {error_msg}")
                    
                    # TIMEOUT FALLBACK: If timeout or error, use knowledge base
                    if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                        logger.info("LLM timeout - falling back to knowledge base")
                        kb_answer = knowledge_base.get_answer(intent, user_message)
                        if kb_answer:
                            answer = kb_answer
                        else:
                            answer = get_multilang_response(MULTILANG_FALLBACK_HELP, language_code)
                    else:
                        # Other errors - try knowledge base first
                        kb_answer = knowledge_base.get_answer(intent, user_message)
                        if kb_answer:
                            answer = kb_answer
                        else:
                            answer = get_multilang_response(
                                MULTILANG_FALLBACK_ERROR if 'MULTILANG_FALLBACK_ERROR' in globals() else MULTILANG_FALLBACK_HELP,
                                language_code
                            )
                
                # Clean up unwanted disclaimers and meta-commentary from LLM responses
                if answer:
                    # Remove patterns like "The final answer to your question is not explicitly stated..."
                    import re
                    answer = re.sub(
                        r'^(The final answer to your question is not explicitly stated[^\n]*\.?\s*However,?\s*)?(According to|Based on|From) (the )?(FAQ section|provided context|the context)[^\n]*:?\s*',
                        '',
                        answer,
                        flags=re.IGNORECASE | re.MULTILINE
                    )
                    # Remove similar patterns with variations
                    answer = re.sub(
                        r'^(However,?\s*)?(According to|Based on|From) (the )?(FAQ section|provided context|the context)[^\n]*:?\s*',
                        '',
                        answer,
                        flags=re.IGNORECASE | re.MULTILINE
                    )
                    # Clean up any leading/trailing whitespace
                    answer = answer.strip()
                
                logger.debug(f"LLM response: {len(answer) if answer else 0} chars")
                
                # Fallback: If LLM returns empty or very short response for staff queries, use staff data directly
                if agent_id == 'staff' and (not answer or (answer and len(answer.strip()) < 20)):
                    staff_docs = agent_context.get('staff', [])
                    if staff_docs:
                        logger.debug("LLM response too short, using staff fallback")
                        # Filter staff by query keywords if possible
                        query_words = set(user_message_lower.split())
                        relevant_staff = []
                        for staff in staff_docs:
                            staff_text = ' '.join([
                                staff.get('name', '').lower(),
                                staff.get('department', '').lower(),
                                staff.get('specialization', '').lower(),
                                staff.get('keywords', '').lower()
                            ])
                            if any(word in staff_text for word in query_words if len(word) > 2):
                                relevant_staff.append(staff)
                        
                        if not relevant_staff:
                            relevant_staff = staff_docs[:3]  # Show first 3 if no match
                        
                        answer_parts = ["Here are some staff members you can contact:\n"]
                        for staff in relevant_staff[:5]:  # Limit to 5
                            if staff.get('name'):
                                answer_parts.append(f"- **{staff['name']}**")
                        
                        answer_parts.append("")
                        answer_parts.append("Would you like contact information (email, phone, office) for any of these staff members?")
                        answer = '\n'.join(answer_parts)
            except LLMError as e:
                # Log error with structured logging
                error_msg = str(e)
                if "Could not reach LLM provider" in error_msg or "connection" in error_msg.lower():
                    logger.warning("LLM unavailable - using fallback")
                else:
                    logger.error(f"LLM error: {e}")
                
                # Smart fallback based on agent type
                if agent_id == 'staff':
                    staff_docs = agent_context.get('staff', [])
                    if staff_docs:
                        logger.debug("Using staff data fallback")
                        answer = "Here are some staff members you can contact:\n\n"
                        for staff in staff_docs[:5]:
                            if staff.get('name'):
                                answer += f"- **{staff.get('name')}**"
                                if staff.get('department'):
                                    answer += f" ({staff.get('department')})"
                                answer += "\n"
                        answer += "\nWould you like contact information (email, phone, office) for any of these staff members?"
                    else:
                        # Fallback to knowledge base for staff queries
                        kb_answer = knowledge_base.get_answer(intent, user_message) if hasattr(knowledge_base, 'get_answer') else None
                        if kb_answer:
                            answer = kb_answer
                        else:
                            answer = get_multilang_response(MULTILANG_STAFF_FALLBACK, language_code)
                elif agent_id == 'faq':
                    # For FAQ queries, fallback to knowledge base
                    logger.debug("LLM failed, using knowledge base fallback")
                    kb_answer = knowledge_base.get_answer(intent, user_message) if hasattr(knowledge_base, 'get_answer') else None
                    if kb_answer:
                        answer = kb_answer
                    else:
                        answer = get_multilang_response(MULTILANG_FAQ_FALLBACK, language_code)
                else:
                    # Generic fallback
                    kb_answer = knowledge_base.get_answer(intent, user_message) if hasattr(knowledge_base, 'get_answer') else None
                    if kb_answer:
                        answer = kb_answer
                    else:
                        answer = get_multilang_response(MULTILANG_FALLBACK_HELP, language_code)
            except Exception as e:
                logger.exception(f"Unexpected error in LLM path: {e}")
                
                # Smart fallback based on agent type with multi-language support
                if agent_id == 'staff':
                    staff_docs = agent_context.get('staff', [])
                    if staff_docs:
                        logger.debug("Exception occurred, using staff fallback")
                        answer = "Here are some staff members you can contact:\n\n"
                        for staff in staff_docs[:5]:
                            if staff.get('name'):
                                answer += f"- **{staff.get('name')}**"
                                if staff.get('department'):
                                    answer += f" ({staff.get('department')})"
                                answer += "\n"
                        answer += "\nWould you like contact information (email, phone, office) for any of these staff members?"
                    else:
                        # Try knowledge base fallback
                        try:
                            kb_answer = knowledge_base.get_answer(intent, user_message)
                            answer = kb_answer if kb_answer else get_multilang_response(MULTILANG_STAFF_FALLBACK, language_code)
                        except Exception:
                            answer = get_multilang_response(MULTILANG_STAFF_FALLBACK, language_code)
                elif agent_id == 'faq':
                    # For FAQ queries, always try knowledge base
                    try:
                        kb_answer = knowledge_base.get_answer(intent, user_message)
                        answer = kb_answer if kb_answer else get_multilang_response(MULTILANG_FAQ_FALLBACK, language_code)
                    except Exception:
                        answer = get_multilang_response(MULTILANG_FAQ_FALLBACK, language_code)
                else:
                    # Try knowledge base first, then generic message
                    try:
                        kb_answer = knowledge_base.get_answer(intent, user_message)
                        answer = kb_answer if kb_answer else get_multilang_response(MULTILANG_REPHRASE, language_code)
                    except Exception:
                        answer = get_multilang_response(MULTILANG_FALLBACK_HELP, language_code)

            # Check if we should ask about handbook or if user confirmed
            if should_ask_for_handbook(intent, user_message, context) or context.get('handbook_asked', False):
                handbook_answer, handbook_pdf_url, context = handle_handbook_request(user_message, context, language_code)
                if handbook_answer:
                    # If user is confirming/declining handbook request, use handbook response
                    if context.get('handbook_asked') is False or detect_yes_no_response(user_message) is not None:
                        answer = handbook_answer
                        pdf_url = handbook_pdf_url if handbook_pdf_url else pdf_url
                    # If we're asking, append to existing answer or replace
                    elif should_ask_for_handbook(intent, user_message, context):
                        if answer:
                            answer = answer + "\n\n" + handbook_answer
                        else:
                            answer = handbook_answer
            elif is_handbook_query:
                # User explicitly asked for handbook - provide it directly
                import os
                from django.conf import settings
                pdf_path = os.path.join(settings.MEDIA_ROOT, 'Academic_Handbook.pdf')
                if os.path.exists(pdf_path):
                    pdf_url = settings.MEDIA_URL + 'Academic_Handbook.pdf'
                    if not answer:
                        answer = get_multilang_response({
                            'en': "📚 Here is the Academic Handbook PDF with detailed program information.",
                            'ms': "📚 Berikut adalah PDF Buku Panduan Akademik dengan maklumat program terperinci.",
                            'zh': "📚 以下是包含详细课程信息的学术手册PDF。"
                        }, language_code)
                else:
                    answer = get_multilang_response({
                        'en': "📚 I'm sorry, but the Academic Handbook PDF is not available on this system. Please contact the FAIX office at faix@utem.edu.my for access.",
                        'ms': "📚 Maaf, PDF Buku Panduan Akademik tidak tersedia dalam sistem ini. Sila hubungi pejabat FAIX di faix@utem.edu.my.",
                        'zh': "📚 抱歉，本系统不提供学术手册PDF。请联系FAIX办公室 faix@utem.edu.my。"
                    }, language_code)

        else:
            # Existing non-agent behaviour (no LLM)
            # Check if this is a fee query first - return link directly
            fee_keywords = ['fee', 'fees', 'tuition', 'yuran', 'bayaran', 'diploma fee', 'degree fee', 'cost', 'payment']
            is_fee_query = intent == 'fees' or any(kw in user_message_lower for kw in fee_keywords)
            
            if is_fee_query:
                logger.info("Fee query (non-agent) - returning direct link")
                answer = "https://bendahari.utem.edu.my/ms/jadual-yuran-pelajar.html"
            elif intent and intent not in ['greeting', 'farewell']:
                try:
                    answer = knowledge_base.get_answer(intent, user_message)
                except Exception as e:
                    logger.warning(f"Knowledge base retrieval error: {e}")
                    answer = None
                
                # Validate answer is not None, empty, or invalid type
                if not answer or not isinstance(answer, str) or not answer.strip():
                    answer = get_multilang_response(MULTILANG_CANT_UNDERSTAND, language_code)
                # Also check for inadequate responses from knowledge base
                elif is_inadequate_response(answer):
                    logger.info(f"Inadequate KB response: {answer[:50]}...")
                    answer = get_multilang_response(MULTILANG_NO_INFO, language_code)
                
                # Check if we should ask about handbook or if user confirmed
                if should_ask_for_handbook(intent, user_message, context) or context.get('handbook_asked', False):
                    handbook_answer, handbook_pdf_url, context = handle_handbook_request(user_message, context, language_code)
                    if handbook_answer:
                        # If user is confirming/declining handbook request, use handbook response
                        if context.get('handbook_asked') is False or detect_yes_no_response(user_message) is not None:
                            answer = handbook_answer
                            pdf_url = handbook_pdf_url if handbook_pdf_url else pdf_url
                        # If we're asking, append to existing answer
                        elif should_ask_for_handbook(intent, user_message, context):
                            if answer:
                                answer = answer + "\n\n" + handbook_answer
                            else:
                                answer = handbook_answer
                elif is_handbook_query:
                    # User explicitly asked for handbook - provide it directly
                    import os
                    from django.conf import settings
                    pdf_path = os.path.join(settings.MEDIA_ROOT, 'Academic_Handbook.pdf')
                    if os.path.exists(pdf_path):
                        pdf_url = settings.MEDIA_URL + 'Academic_Handbook.pdf'
                        if not answer:
                            answer = get_multilang_response({
                                'en': "📚 Here is the Academic Handbook PDF with detailed program information.",
                                'ms': "📚 Berikut adalah PDF Buku Panduan Akademik dengan maklumat program terperinci.",
                                'zh': "📚 以下是包含详细课程信息的学术手册PDF。"
                            }, language_code)
                    else:
                        answer = get_multilang_response({
                            'en': "📚 I'm sorry, but the Academic Handbook PDF is not available on this system. Please contact the FAIX office at faix@utem.edu.my for access.",
                            'ms': "📚 Maaf, PDF Buku Panduan Akademik tidak tersedia dalam sistem ini. Sila hubungi pejabat FAIX di faix@utem.edu.my.",
                            'zh': "📚 抱歉，本系统不提供学术手册PDF。请联系FAIX办公室 faix@utem.edu.my。"
                        }, language_code)
            else:
                # Use conversation manager for general queries
                # BUT check for handbook first
                if is_handbook_query:
                    # User explicitly asked for handbook - provide it directly
                    import os
                    from django.conf import settings
                    pdf_path = os.path.join(settings.MEDIA_ROOT, 'Academic_Handbook.pdf')
                    if os.path.exists(pdf_path):
                        pdf_url = settings.MEDIA_URL + 'Academic_Handbook.pdf'
                        answer = get_multilang_response({
                            'en': "📚 Here is the Academic Handbook PDF with comprehensive information about programs, courses, academic policies, and graduation requirements.",
                            'ms': "📚 Berikut adalah PDF Buku Panduan Akademik dengan maklumat menyeluruh mengenai program, kursus, dasar akademik, dan keperluan graduasi.",
                            'zh': "📚 以下是包含有关课程、学术政策和毕业要求的全面信息的学术手册PDF。"
                        }, language_code)
                    else:
                        answer = get_multilang_response({
                            'en': "📚 I'm sorry, but the Academic Handbook PDF is not available on this system. Please contact the FAIX office at faix@utem.edu.my for access.",
                            'ms': "📚 Maaf, PDF Buku Panduan Akademik tidak tersedia dalam sistem ini. Sila hubungi pejabat FAIX di faix@utem.edu.my.",
                            'zh': "📚 抱歉，本系统不提供学术手册PDF。请联系FAIX办公室 faix@utem.edu.my。"
                        }, language_code)
                elif should_ask_for_handbook(intent, user_message, context) or context.get('handbook_asked', False):
                    # Ask user if they need handbook
                    handbook_answer, handbook_pdf_url, context = handle_handbook_request(user_message, context, language_code)
                    if handbook_answer:
                        if context.get('handbook_asked') is False or detect_yes_no_response(user_message) is not None:
                            answer = handbook_answer
                            pdf_url = handbook_pdf_url if handbook_pdf_url else pdf_url
                        else:
                            # Get regular answer first, then append handbook question
                            answer, context = process_conversation(user_message, context)
                            if answer:
                                answer = answer + "\n\n" + handbook_answer
                            else:
                                answer = handbook_answer
                else:
                    answer, context = process_conversation(user_message, context)
                    # Validate answer from conversation manager
                    if not answer or not isinstance(answer, str) or not answer.strip():
                        answer = get_multilang_response(MULTILANG_CANT_UNDERSTAND, language_code)
                    # Also check for inadequate responses
                    elif is_inadequate_response(answer):
                        logger.info(f"Inadequate conversation manager response detected")
                        answer = get_multilang_response(MULTILANG_CANT_UNDERSTAND, language_code)
        
        # REINFORCEMENT LEARNING: Check for negative feedback patterns
        # If this response is similar to a previously negatively-rated response, try to avoid it
        # EXCEPTION: Don't block factual answers (like dean info) that are correct
        if answer and isinstance(answer, str) and answer.strip():
            # Skip negative feedback check for factual queries with specific keywords
            # These are correct answers that shouldn't be blocked
            factual_keywords = ['dean', 'associate professor', 'established', 'vision', 'mission']
            is_factual_answer = any(kw in answer.lower() for kw in factual_keywords)
            
            if not is_factual_answer:  # Only check negative feedback for non-factual answers
                negative_patterns = get_negative_feedback_patterns(intent, session.session_id)
                if negative_patterns and should_avoid_response(answer, negative_patterns):
                    logger.info(f"Response matches negative feedback pattern for intent '{intent}', trying alternative")
                    # Try knowledge base as alternative
                    kb_answer = knowledge_base.get_answer(intent, user_message)
                    if kb_answer and not is_inadequate_response(kb_answer):
                        # Check if KB answer is also similar to negative feedback
                        if not should_avoid_response(kb_answer, negative_patterns):
                            answer = kb_answer
                            logger.info("Using knowledge base alternative due to negative feedback")
                        else:
                            # Both match negative patterns, try conversation manager
                            conv_answer, _ = process_conversation(user_message, context)
                            if conv_answer and not should_avoid_response(conv_answer, negative_patterns):
                                answer = conv_answer
                                logger.info("Using conversation manager alternative due to negative feedback")
        
        # Final safety check: ensure answer is never None or empty before saving
        if not answer or not isinstance(answer, str) or not answer.strip():
            answer = get_multilang_response(MULTILANG_CANT_UNDERSTAND, language_code)
        # Final check for inadequate responses
        elif is_inadequate_response(answer):
            logger.info("Final check caught inadequate response")
            answer = get_multilang_response(MULTILANG_CANT_UNDERSTAND, language_code)
        
        # Update session context
        session.context = context
        session.save(update_fields=['context', 'updated_at'])
        
        # Save user message asynchronously, but save bot message synchronously to get ID for feedback
        def _save_user_message():
            try:
                with transaction.atomic():
                    Message.objects.create(
                        conversation=conversation,
                        role='user',
                        content=user_message,
                        intent=intent,
                        confidence=confidence,
                        entities=entities,
                    )
                    conversation.updated_at = timezone.now()
                    if not conversation.title or conversation.title == "New Conversation":
                        conversation.title = user_message[:50] + ("..." if len(user_message) > 50 else "")
                    conversation.save()
            except Exception as e:
                logger.error(f"Error saving user message async: {e}")
        
        thread = threading.Thread(target=_save_user_message)
        thread.daemon = True
        thread.start()
        
        # Save bot message synchronously to get ID for feedback
        bot_message = None
        try:
            with transaction.atomic():
                bot_message = Message.objects.create(
                    conversation=conversation,
                    role='bot',
                    content=answer,
                    intent=intent,
                    confidence=confidence,
                )
                conversation.updated_at = timezone.now()
                conversation.save()
        except Exception as e:
            logger.error(f"Error saving bot message: {e}")
        
        # Build response data
        response_data = {
            'response': answer,
            'session_id': session.session_id,
            'conversation_id': conversation.id,
            'message_id': bot_message.id if bot_message else None,  # Include message ID for feedback
            'intent': intent,
            'confidence': confidence,
            'entities': entities,
            'timestamp': timezone.now().isoformat(),
            'pdf_url': pdf_url,  # Add PDF URL to response
        }
        
        # PERFORMANCE OPTIMIZATION: Cache the response (TTL: 1 hour for general queries, 24 hours for static responses)
        # Check if it's a fee query directly (avoiding scope issues with is_fee_query variable)
        fee_keywords = ['fee', 'fees', 'tuition', 'yuran', 'bayaran', 'diploma fee', 'degree fee', 'cost', 'payment']
        is_fee_query_check = intent == 'fees' or any(kw in user_message_lower for kw in fee_keywords)
        cache_timeout = 86400 if (is_fee_query_check or intent in ['greeting', 'farewell', 'about_faix']) else 3600  # 24h for static, 1h for others
        cache.set(cache_key, response_data, timeout=cache_timeout)
        
        return JsonResponse(response_data)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        logger.exception(f"Unexpected error in chat_api: {e}")
        import traceback
        from django.conf import settings
        error_traceback = traceback.format_exc()
        logger.error(f"Full traceback:\n{error_traceback}")
        return JsonResponse({
            'error': str(e),
            'traceback': error_traceback if settings.DEBUG else None
        }, status=500)


@require_http_methods(["GET"])
def get_conversation_history(request):
    """
    Get conversation history for a session or conversation.
    
    Query parameters:
    - session_id: Get all conversations for a session
    - conversation_id: Get messages for a specific conversation
    - limit: Limit number of messages (default: 50)
    """
    session_id = request.GET.get('session_id')
    conversation_id = request.GET.get('conversation_id')
    limit = int(request.GET.get('limit', 50))
    
    if conversation_id:
        # Get messages for specific conversation
        try:
            conversation = Conversation.objects.get(id=conversation_id)
            messages = Message.objects.filter(conversation=conversation).order_by('timestamp')[:limit]
            
            messages_data = [{
                'id': msg.id,
                'role': msg.role,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat(),
                'intent': msg.intent,
                'confidence': msg.confidence,
            } for msg in messages]
            
            return JsonResponse({
                'conversation_id': conversation.id,
                'title': conversation.title,
                'messages': messages_data,
            })
        except Conversation.DoesNotExist:
            return JsonResponse({
                'error': 'Conversation not found'
            }, status=404)
    
    elif session_id:
        # Get all conversations for session
        try:
            session = UserSession.objects.get(session_id=session_id)
            conversations = Conversation.objects.filter(session=session).order_by('-created_at')
            
            conversations_data = [{
                'id': conv.id,
                'title': conv.title,
                'created_at': conv.created_at.isoformat(),
                'updated_at': conv.updated_at.isoformat(),
                'message_count': conv.messages.count(),
            } for conv in conversations]
            
            return JsonResponse({
                'session_id': session_id,
                'conversations': conversations_data,
            })
        except UserSession.DoesNotExist:
            return JsonResponse({
                'error': 'Session not found'
            }, status=404)
    
    else:
        return JsonResponse({
            'error': 'session_id or conversation_id is required'
        }, status=400)


@require_http_methods(["GET"])
def admin_dashboard_data(request):
    """
    Get analytics data for admin dashboard.
    
    Returns:
    {
        "total_conversations": 100,
        "total_messages": 500,
        "active_users": 25,
        "popular_queries": [...],
        "intent_distribution": {...}
    }
    """
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    
    # Get date range (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Total conversations
    total_conversations = Conversation.objects.count()
    
    # Total messages
    total_messages = Message.objects.count()
    
    # Active users (sessions with activity in last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    active_users = UserSession.objects.filter(
        updated_at__gte=seven_days_ago
    ).count()
    
    # Popular queries (most common intents)
    intent_distribution = Message.objects.filter(
        role='user',
        intent__isnull=False
    ).values('intent').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Popular queries (most frequent user messages)
    popular_queries = Message.objects.filter(
        role='user',
        timestamp__gte=thirty_days_ago
    ).values('content').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    return JsonResponse({
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'active_users': active_users,
        'popular_queries': [
            {'query': item['content'], 'count': item['count']}
            for item in popular_queries
        ],
        'intent_distribution': {
            item['intent']: item['count']
            for item in intent_distribution
        },
    })


@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def manage_knowledge_base(request):
    """
    CRUD operations for knowledge base entries.
    
    GET: List all FAQ entries (with optional filters)
    POST: Create new FAQ entry
    PUT: Update existing FAQ entry (requires id in body)
    DELETE: Delete FAQ entry (requires id in query params)
    """
    if request.method == 'GET':
        # List entries
        category = request.GET.get('category')
        search = request.GET.get('search')
        
        entries = FAQEntry.objects.filter(is_active=True)
        
        if category:
            entries = entries.filter(category=category)
        
        if search:
            entries = entries.filter(
                Q(question__icontains=search) |
                Q(answer__icontains=search) |
                Q(keywords__icontains=search)
            )
        
        entries_data = [{
            'id': entry.id,
            'question': entry.question,
            'answer': entry.answer,
            'category': entry.category,
            'keywords': entry.keywords,
            'view_count': entry.view_count,
            'helpful_count': entry.helpful_count,
        } for entry in entries[:100]]  # Limit to 100
        
        return JsonResponse({
            'entries': entries_data,
            'count': len(entries_data),
        })
    
    elif request.method == 'POST':
        # Create entry
        try:
            data = json.loads(request.body)
            entry = FAQEntry.objects.create(
                question=data.get('question'),
                answer=data.get('answer'),
                category=data.get('category', 'general'),
                keywords=data.get('keywords', ''),
            )
            
            # Refresh knowledge base
            knowledge_base.refresh()
            
            return JsonResponse({
                'id': entry.id,
                'message': 'FAQ entry created successfully',
            }, status=201)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=400)
    
    elif request.method == 'PUT':
        # Update entry
        try:
            data = json.loads(request.body)
            entry_id = data.get('id')
            
            if not entry_id:
                return JsonResponse({
                    'error': 'id is required'
                }, status=400)
            
            entry = FAQEntry.objects.get(id=entry_id)
            entry.question = data.get('question', entry.question)
            entry.answer = data.get('answer', entry.answer)
            entry.category = data.get('category', entry.category)
            entry.keywords = data.get('keywords', entry.keywords)
            entry.save()
            
            # Refresh knowledge base
            knowledge_base.refresh()
            
            return JsonResponse({
                'id': entry.id,
                'message': 'FAQ entry updated successfully',
            })
        except FAQEntry.DoesNotExist:
            return JsonResponse({
                'error': 'FAQ entry not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'error': str(e)
            }, status=400)
    
    elif request.method == 'DELETE':
        # Delete entry (soft delete)
        entry_id = request.GET.get('id')
        
        if not entry_id:
            return JsonResponse({
                'error': 'id is required'
            }, status=400)
        
        try:
            entry = FAQEntry.objects.get(id=entry_id)
            entry.is_active = False
            entry.save()
            
            # Refresh knowledge base
            knowledge_base.refresh()
            
            return JsonResponse({
                'message': 'FAQ entry deleted successfully',
            })
        except FAQEntry.DoesNotExist:
            return JsonResponse({
                'error': 'FAQ entry not found'
            }, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def submit_feedback(request):
    """
    Submit feedback on a bot response for reinforcement learning.
    
    Expected JSON payload:
    {
        "message_id": 123,
        "conversation_id": 456,
        "feedback_type": "good" or "bad",
        "user_message": "original user message",
        "bot_response": "bot response text",
        "intent": "detected intent",
        "user_comment": "optional comment",
        "session_id": "session id"
    }
    
    Returns:
    {
        "success": true,
        "message": "Feedback submitted successfully"
    }
    """
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        conversation_id = data.get('conversation_id')
        feedback_type = data.get('feedback_type')
        user_message = data.get('user_message', '')
        bot_response = data.get('bot_response', '')
        intent = data.get('intent')
        user_comment = data.get('user_comment', '')
        session_id = data.get('session_id')
        
        if not message_id or not conversation_id or not feedback_type:
            return JsonResponse({
                'error': 'message_id, conversation_id, and feedback_type are required'
            }, status=400)
        
        if feedback_type not in ['good', 'bad']:
            return JsonResponse({
                'error': 'feedback_type must be "good" or "bad"'
            }, status=400)
        
        try:
            message = Message.objects.get(id=message_id)
            conversation = Conversation.objects.get(id=conversation_id)
        except (Message.DoesNotExist, Conversation.DoesNotExist):
            return JsonResponse({
                'error': 'Message or conversation not found'
            }, status=404)
        
        # Create feedback record
        feedback = ResponseFeedback.objects.create(
            message=message,
            conversation=conversation,
            feedback_type=feedback_type,
            user_message=user_message,
            bot_response=bot_response,
            intent=intent,
            user_comment=user_comment,
            session_id=session_id
        )
        
        logger.info(f"Feedback submitted: {feedback_type} for message {message_id}, intent: {intent}")
        
        return JsonResponse({
            'success': True,
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON payload'
        }, status=400)
    except Exception as e:
        logger.exception(f"Error submitting feedback: {e}")
        return JsonResponse({
            'error': str(e)
        }, status=500)


def get_negative_feedback_patterns(intent: str, session_id: str = None) -> List[Dict]:
    """
    Retrieve patterns from negative feedback that should be avoided.
    Returns a list of dictionaries with user_message patterns and bot_responses to avoid.
    """
    try:
        # Get negative feedback for this intent (or general if no intent)
        query = ResponseFeedback.objects.filter(feedback_type='bad')
        
        if intent:
            query = query.filter(intent=intent)
        
        # Optionally filter by session to learn from current user's preferences
        if session_id:
            # Get feedback from same session or recent feedback
            from datetime import timedelta
            recent_threshold = timezone.now() - timedelta(days=30)
            query = query.filter(
                Q(session_id=session_id) | Q(created_at__gte=recent_threshold)
            )
        else:
            # Get recent feedback (last 30 days)
            from datetime import timedelta
            recent_threshold = timezone.now() - timedelta(days=30)
            query = query.filter(created_at__gte=recent_threshold)
        
        # Get the most recent negative feedback
        negative_feedback = query.order_by('-created_at')[:10]
        
        patterns = []
        for fb in negative_feedback:
            patterns.append({
                'user_message': fb.user_message.lower() if fb.user_message else '',
                'bot_response': fb.bot_response.lower() if fb.bot_response else '',
                'intent': fb.intent,
                'comment': fb.user_comment
            })
        
        return patterns
    except Exception as e:
        logger.warning(f"Error retrieving negative feedback patterns: {e}")
        return []


def should_avoid_response(response_text: str, negative_patterns: List[Dict]) -> bool:
    """
    Check if a response should be avoided based on negative feedback patterns.
    Returns True if the response is similar to a previously negatively-rated response.
    """
    if not negative_patterns or not response_text:
        return False
    
    response_lower = response_text.lower()
    
    # Check if response is too similar to a previously bad response
    for pattern in negative_patterns:
        bad_response = pattern.get('bot_response', '')
        if bad_response and len(bad_response) > 10:
            # Simple similarity check: if response contains significant portion of bad response
            # or vice versa, avoid it
            similarity_threshold = 0.7
            if bad_response in response_lower or response_lower in bad_response:
                # Check if it's substantial overlap (not just a small substring)
                min_length = min(len(bad_response), len(response_lower))
                if min_length > 20:  # Only check for substantial responses
                    overlap_ratio = len(bad_response) / len(response_lower) if response_lower else 0
                    if overlap_ratio > similarity_threshold or (bad_response in response_lower and len(bad_response) > len(response_lower) * 0.5):
                        logger.info(f"Avoiding response similar to negative feedback: {bad_response[:50]}...")
                        return True
    
    return False


def index(request):
    """Serve the main HTML page"""
    from django.shortcuts import render
    return render(request, 'index.html')


def admin_dashboard(request):
    """Serve the admin dashboard page"""
    from django.shortcuts import render
    return render(request, 'admin.html')


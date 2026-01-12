import os
import re
import json
import logging
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from collections import defaultdict
from functools import lru_cache

# Constants for cache sizes and scoring weights
LANGUAGE_CACHE_SIZE = 1000
INTENT_CACHE_SIZE = 2000
PREPROCESS_CACHE_SIZE = 5000

# Scoring weights for intent detection
KEYWORD_MATCH_WEIGHT = 2
EXACT_MATCH_BONUS = 1
STRONG_INDICATOR_WEIGHT = 3
ENGLISH_INDICATOR_WEIGHT = 2
SPECIFIC_INTENT_BOOST = 2

# Suppress warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['PYTHONWARNINGS'] = 'ignore'

# Import NLP modules
try:
    from .nlp_intent_classifier import get_intent_classifier
    NLP_AVAILABLE = True
except ImportError:
    try:
        from nlp_intent_classifier import get_intent_classifier
        NLP_AVAILABLE = True
    except ImportError:
        NLP_AVAILABLE = False
        print("Warning: NLP modules not available. Using keyword-based intent detection.")

class LanguageDetector:
    """Enhanced language detection for English, Malay, Chinese, Arabic"""
    
    def __init__(self):
        # Initialize cache
        self._detect_cache = {}
        # Language-specific keywords
        # Words that appear in both languages are weighted lower
        self.language_patterns = {
            'en': [
                r'\bthe\b', r'\band\b', r'\bfor\b', r'\bwith\b', r'\bthis\b',
                r'\bthat\b', r'\bwhat\b', r'\bhow\b', r'\bwhen\b', r'\bwhere\b',
                r'\bwho\b', r'\bwhy\b', r'\bare\b', r'\bis\b', r'\bwas\b',
                r'\bwere\b', r'\bhave\b', r'\bhas\b', r'\bhad\b', r'\bdo\b',
                r'\bdoes\b', r'\bdid\b', r'\bwill\b', r'\bwould\b', r'\bshould\b',
                r'\bcould\b', r'\bcan\b', r'\bmay\b', r'\bmight\b', r'\bmust\b',
                r'\bregister\b', r'\benroll\b', r'\bfaculty\b', r'\bstudent\b',
                r'\bprofessor\b', r'\bcontact\b', r'\binformation\b', r'\bavailable\b'
            ],
            'ms': [
                # Unique Malay words (high weight)
                r'\byang\b', r'\boleh\b', r'\bditawarkan\b',
                r'\bdengan\b', r'\buntuk\b', r'\bdari\b', r'\bdaripada\b',
                r'\bini\b', r'\bitu\b', r'\bsaya\b', r'\bawak\b', r'\banda\b',
                r'\bdia\b', r'\bkita\b', r'\bkami\b', r'\bmereka\b', r'\badalah\b',
                r'\bialah\b', r'\bakan\b', r'\btelah\b', r'\bsudah\b', r'\bbelum\b',
                r'\bjangan\b', r'\btidak\b', r'\bbukan\b', r'\bapakah\b', r'\bbagaimana\b',
                r'\bkenapa\b', r'\bsiapa\b', r'\bbila\b', r'\bdimana\b', r'\bmengapa\b',
                r'\bkursus\b', r'\bdaftar\b', r'\bmendaftar\b', r'\bfakulti\b',
                r'\bpelajar\b', r'\bprofesor\b', r'\bhubungi\b', r'\bmaklumat\b',
                r'\bhubungan\b', r'\bkemudahan\b', r'\byuran\b', r'\bbayaran\b',
                r'\bkemasukan\b', r'\bpendaftaran\b', r'\bpermohonan\b', r'\bmemohon\b'
            ],
            'zh': [
                r'[\u4e00-\u9fff]',  
            ],
            'ar': [
                r'[\u0600-\u06FF]',  # Arabic Unicode range
            ]
        }
        
        # Words that appear in multiple languages (lower weight)
        self.common_words = {
            'program', 'semester', 'course', 'programme'
        }
    
    def _detect_logic(self, text: str) -> str:
        """Internal language detection logic (extracted for caching)"""
        text = text.strip()
        
        # Check for Chinese characters first (most reliable)
        if self._has_chinese(text):
            return 'zh'
        
        # Check for Arabic characters (most reliable)
        if self._has_arabic(text):
            return 'ar'
        
        # Count pattern matches for each language with weighted scoring
        scores = {'en': 0, 'ms': 0, 'zh': 0, 'ar': 0}
        text_lower = text.lower()
        
        for lang, patterns in self.language_patterns.items():
            if lang in ['zh', 'ar']:
                continue  # Already handled
            
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                # Give higher weight to unique language indicators
                weight = KEYWORD_MATCH_WEIGHT if pattern not in [r'\bprogram\b', r'\bsemester\b'] else EXACT_MATCH_BONUS
                scores[lang] += len(matches) * weight
        
        # Check for Malay-specific indicators that are very reliable
        malay_strong_indicators = ['yang', 'oleh', 'ditawarkan', 'apakah', 'bagaimana', 
                                   'maklumat', 'hubungan', 'kakitangan', 'kemudahan']
        for indicator in malay_strong_indicators:
            if re.search(r'\b' + re.escape(indicator) + r'\b', text_lower):
                scores['ms'] += STRONG_INDICATOR_WEIGHT  # Strong boost for Malay
        
        # Check for English-specific indicators
        english_strong_indicators = ['the', 'what', 'how', 'when', 'where', 'who', 'why',
                                      'information', 'available', 'contact', 'register']
        for indicator in english_strong_indicators:
            if re.search(r'\b' + re.escape(indicator) + r'\b', text_lower):
                scores['en'] += ENGLISH_INDICATOR_WEIGHT  # Boost for English
        
        # If no pattern matches, use fallback
        if sum(scores.values()) == 0:
            return self._fallback_detection(text)
        
        # Return language with highest score
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def detect(self, text: str) -> str:
        """Detect language of input text with confidence (cached)"""
        # Use simple in-memory cache (faster than lru_cache for methods)
        text_key = text.strip()[:100]  # Limit key length
        text_hash = hash(text_key)
        
        if text_hash in self._detect_cache:
            return self._detect_cache[text_hash]
        
        result = self._detect_logic(text)
        # Cache last 1000 results (simple LRU by limiting cache size)
        if len(self._detect_cache) > LANGUAGE_CACHE_SIZE:
            # Clear oldest entries (simple approach: clear half)
            self._detect_cache = dict(list(self._detect_cache.items())[LANGUAGE_CACHE_SIZE // 2:])
        self._detect_cache[text_hash] = result
        return result
    
    def _has_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def _has_arabic(self, text: str) -> bool:
        """Check if text contains Arabic characters"""
        for char in text:
            if '\u0600' <= char <= '\u06FF':
                return True
        return False
    
    def _fallback_detection(self, text: str) -> str:
        """Fallback detection using common phrases"""
        text_lower = text.lower()
        
        malay_indicators = ['apa', 'bagaimana', 'kenapa', 'siapa', 'bila']
        chinese_indicators = ['吗', '呢', '什么', '怎么', '为什么']
        arabic_indicators = ['ما', 'كيف', 'متى', 'أين', 'لماذا', 'من', 'هل']
        
        for indicator in malay_indicators:
            if indicator in text_lower:
                return 'ms'
        
        for indicator in chinese_indicators:
            if indicator in text:
                return 'zh'
        
        for indicator in arabic_indicators:
            if indicator in text:
                return 'ar'
        
        # Default to English
        return 'en'

class ShortFormProcessor:
    """Process short-form/slang language commonly used by students"""
    
    # Pre-compiled regex patterns cache (class-level for reuse)
    _compiled_patterns = {}
    
    def __init__(self):
        # Comprehensive dictionary of short forms and their expansions
        self.short_forms = {
            'en': {
                # General abbreviations
                'u': 'you',
                'ur': 'your',
                'r': 'are',
                'pls': 'please',
                'plz': 'please',
                'thx': 'thanks',
                'ty': 'thank you',
                'np': 'no problem',
                'idk': "i don't know",
                'afaik': 'as far as i know',
                'tbh': 'to be honest',
                'brb': 'be right back',
                'btw': 'by the way',
                'fyi': 'for your information',
                'imo': 'in my opinion',
                'asap': 'as soon as possible',
                'atm': 'at the moment',
                'b4': 'before',
                'bc': 'because',
                'cuz': 'because',
                'coz': 'because',
                'w/': 'with',
                'w/o': 'without',
                'c': 'see',
                'n': 'and',
                '&': 'and',
                'k': 'ok',
                'ok': 'okay',
                
                # Academic-specific
                'prof': 'professor',
                'lect': 'lecturer',
                'admin': 'administration',
                'reg': 'registration',
                'enrl': 'enrollment',
                'enrol': 'enrollment',
                'sem': 'semester',
                'lab': 'laboratory',
                'tut': 'tutorial',
                'lec': 'lecture',
                'asgmt': 'assignment',
                'hw': 'homework',
                'cw': 'coursework',
                'exam': 'examination',
                'uni': 'university',
                
                # University leadership abbreviations
                'vc': 'vice chancellor',
                'nc': 'naib canselor',
                'dept': 'department',
                'fac': 'faculty',
                'cs': 'computer science',
                'ai': 'artificial intelligence',
                'ds': 'data science',
                'cyber': 'cybersecurity',
                'it': 'information technology',
                
                # Question short forms
                'wut': 'what',
                'wat': 'what',
                'wanna': 'want to',
                'gonna': 'going to',
                'gotta': 'got to',
                'hafta': 'have to',
                'needa': 'need to',
                'howz': 'how is',
                'whatz': 'what is',
                'wherez': 'where is',
                'whenz': 'when is',
                'whoz': 'who is',
                'whysz': 'why is',
                
                # Numbers as words
                '2': 'to',
                '4': 'for',
                '2day': 'today',
                '2moro': 'tomorrow',
                '2nite': 'tonight',
                '4ever': 'forever',
                'b4': 'before',
                'gr8': 'great',
                'l8r': 'later',
                'm8': 'mate',
                'h8': 'hate',
                'w8': 'wait',
            },
            'ms': {
                # General Malay abbreviations
                'n': 'dan',
                'sbb': 'sebab',
                'sbg': 'sebagai',
                'spt': 'seperti',
                'tp': 'tapi',
                'tgk': 'tengok',
                'nmpk': 'nampak',
                'skrg': 'sekarang',
                'skrng': 'sekarang',
                'esok': 'esok',
                'tdk': 'tidak',
                'tak': 'tidak',
                'x': 'tidak',
                'lg': 'lagi',
                'lgi': 'lagi',
                'dlm': 'dalam',
                'dgn': 'dengan',
                'stp': 'setiap',
                'otw': 'on the way',
                'ptg': 'petang',
                'pg': 'pagi',
                'mlm': 'malam',
                'tggl': 'tinggal',
                'kwn': 'kawan',
                'kk': 'kakak',
                'adk': 'adik',
                'bkn': 'bukan',
                'byk': 'banyak',
                'sdkt': 'sedikit',
                'yg': 'yang',
                'drpd': 'daripada',
                'utk': 'untuk',
                'pd': 'pada',
                'skit': 'sedikit',
                'g': 'sangat',
                'bg': 'bagi',
                'bgmn': 'bagaimana',
                'kpd': 'kepada',
                
                # Academic-specific Malay
                'univ': 'universiti',
                'uni': 'universiti',
                'krs': 'kursus',
                'prog': 'program',
                'fak': 'fakulti',
                'pns': 'pensyarah',
                'pro': 'profesor',
                'pela': 'pelajar',
                'daftar': 'pendaftaran',
                'sem': 'semester',
                'kul': 'kuliah',
                'tuto': 'tutorial',
                'tugas': 'tugasan',
                'pep': 'peperiksaan',
                'exam': 'peperiksaan',
                'lab': 'makmal',
                'admin': 'pentadbiran',
                'dekan': 'dekan',
                
                # University leadership abbreviations (Malay)
                'nc': 'naib canselor',
                'vc': 'naib canselor',  # Also recognize vc as naib canselor in Malay context
                
                # Question short forms
                'ape': 'apa',
                'mne': 'mana',
                'siape': 'siapa',
                'knpe': 'kenapa',
                'camne': 'bagaimana',
                'bile': 'bila',
                'dkat': 'di mana',
                'kate': 'kata',
                'bape': 'berapa',
                
                # Numbers as words
                '1': 'satu',
                '2': 'dua',
                '3': 'tiga',
                '4': 'empat',
                '5': 'lima',
                '10': 'sepuluh',
            },
            'zh': {
                # Common Chinese internet slang and abbreviations
                '课程': '课程',  # Keep original but handle variations
                '课': '课程',
                '程': '课程',
                '专业': '专业',
                '专': '专业',
                '老师': '老师',
                '师': '老师',
                '教授': '教授',
                '教': '教授',
                '学生': '学生',
                '学': '学生',
                '注册': '注册',
                '注': '注册',
                '报名': '报名',
                '报': '报名',
                '学期': '学期',
                '学费': '学费',
                '费': '费用',
                '多少钱': '多少钱',
                '多少': '多少钱',
                '钱': '钱',
                '什么时候': '什么时候',
                '何时': '什么时候',
                '几点': '什么时候',
                '时间': '时间',
                '地点': '地点',
                '哪里': '哪里',
                '怎么': '怎么',
                '如何': '如何',
                '为什么': '为什么',
                '为啥': '为什么',
                
                # Common internet abbreviations
                '啥': '什么',
                '咋': '怎么',
                '嘛': '吗',
                '呗': '吧',
                '滴': '的',
                '哒': '的',
                '辣': '了',
                '酱紫': '这样子',
                '肿么': '怎么',
                '为毛': '为什么',
                '神马': '什么',
                '木有': '没有',
                '有木有': '有没有',
                '灰常': '非常',
                '炒鸡': '超级',
                '造': '知道',
                '造吗': '知道吗',
                '不造': '不知道',
                '好哒': '好的',
                '好滴': '好的',
                '嗯呐': '嗯',
                '噢啦': '哦',
                '阔以': '可以',
                '行': '可以',
                'OK': '可以',
                'ok': '可以',
                
                # Academic-specific Chinese
                '大课': '主修课程',
                '必修': '必修课',
                '选修': '选修课',
                '学分': '学分',
                '绩点': 'GPA',
                'GPA': '绩点',
                '挂科': '不及格',
                '补考': '补考',
                '重修': '重修',
                '毕设': '毕业设计',
                '论文': '毕业论文',
                '导师': '指导老师',
                '导员': '辅导员',
                '班导': '班主任',
                '同学': '同学',
                '学长': '学长',
                '学姐': '学姐',
                '学弟': '学弟',
                '学妹': '学妹',
                '宿舍': '宿舍',
                '食堂': '食堂',
                '图书馆': '图书馆',
                '教室': '教室',
                '实验室': '实验室',
                '机房': '计算机房',
                'WiFi': '无线网络',
                '网': '网络',
                '电': '电力',
                '水': '自来水',
            }
        }
        
        # Patterns for detecting short forms (case-insensitive for English/Malay)
        self.patterns = {
            'en': [
                r'\b(u|ur|r|pls|plz|thx|ty|np|idk|afaik|tbh|brb|btw|fyi|imo|asap|atm|b4|bc|cuz|coz|w\/|w\/o|c|n|k|ok)\b',
                r'\b(prof|lect|admin|reg|enrl|enrol|sem|lab|tut|lec|asgmt|hw|cw|exam|uni|dept|fac|cs|ai|ds|cyber|it|vc|nc)\b',
                r'\b(wut|wat|wanna|gonna|gotta|hafta|needa|howz|whatz|wherez|whenz|whoz|whysz)\b',
                r'\b(2day|2moro|2nite|4ever|gr8|l8r|m8|h8|w8)\b',
            ],
            'ms': [
                r'\b(n|sbb|sbg|spt|tp|tgk|nmpk|skrg|skrng|esok|tdk|tak|x|lg|lgi|dlm|dgn|utk|stp|otw|ptg|pg|mlm|tggl|kwn|kk|adk|bkn|byk|sdkt|yg|drpd|pd|skit|g|bg|bgmn|kpd)\b',
                r'\b(univ|uni|krs|prog|fak|pns|pro|pela|daftar|sem|kul|tuto|tugas|pep|exam|lab|admin|dekan|vc|nc)\b',
                r'\b(ape|mne|siape|knpe|camne|bile|dkat|kate|bape)\b',
            ],
            'zh': [
                # Chinese short forms are handled differently
            ]
        }
    
    def is_short_form(self, text: str, language: str) -> bool:
        """Check if text contains short forms/slang"""
        if language not in ['en', 'ms']:
            # For Chinese, check if it contains common internet slang
            if language == 'zh':
                return any(slang in text for slang in self.short_forms['zh'].keys())
            return False
        
        text_lower = text.lower()
        for pattern in self.patterns[language]:
            if re.search(pattern, text_lower):
                return True
        return False
    
    def expand_short_forms(self, text: str, language: str) -> str:
        """
        Expand short forms and slang in the text
        Returns both original and expanded versions
        """
        if language not in self.short_forms:
            return text
        
        # For Chinese, handle differently due to character-based language
        if language == 'zh':
            expanded = text
            for short, long in self.short_forms['zh'].items():
                if short in expanded:
                    expanded = expanded.replace(short, long)
            return expanded
        
        # For English and Malay
        words = text.split()
        expanded_words = []
        
        for word in words:
            # Clean word for matching
            clean_word = re.sub(r'[^\w]', '', word.lower())
            
            if clean_word in self.short_forms[language]:
                # Exact match - replace the whole word
                expanded = self.short_forms[language][clean_word]
                expanded_words.append(expanded)
            else:
                # Check for number substitutions (like 2day, 4ever) or short forms at word boundaries
                expanded_word = word
                for short, long in self.short_forms[language].items():
                    if len(short) > 1:
                        # Use pre-compiled pattern for better performance
                        pattern_key = (short, language)
                        if pattern_key not in ShortFormProcessor._compiled_patterns:
                            ShortFormProcessor._compiled_patterns[pattern_key] = re.compile(
                                r'\b' + re.escape(short) + r'\b', re.IGNORECASE
                            )
                        compiled = ShortFormProcessor._compiled_patterns[pattern_key]
                        
                        if compiled.search(expanded_word):
                            expanded_word = compiled.sub(long, expanded_word)
                        # Also handle number substitutions (2day -> today, 4ever -> forever)
                        elif short.isdigit() or (len(short) == 1 and short.isdigit()):
                            if short in expanded_word.lower():
                                expanded_word = expanded_word.lower().replace(short, long)
                expanded_words.append(expanded_word)
        
        return ' '.join(expanded_words)
    
    def normalize_slang(self, text: str, language: str) -> Dict[str, Any]:
        """
        Normalize slang/short forms and return analysis
        """
        contains_slang = self.is_short_form(text, language)
        expanded_text = self.expand_short_forms(text, language)
        
        return {
            'original': text,
            'normalized': expanded_text,
            'contains_slang': contains_slang,
            'language': language
        }
    
    def process_query_with_slang(self, query: str, language: str) -> Dict[str, Any]:
        """
        Process query with slang detection and normalization
        """
        # Detect if contains slang
        slang_analysis = self.normalize_slang(query, language)
        
        # Also check for common student slang patterns
        student_slang_patterns = {
            'en': [
                (r'wanna\s+(\w+)', r'want to \1'),
                (r'gonna\s+(\w+)', r'going to \1'),
                (r'gotta\s+(\w+)', r'got to \1'),
                (r'lemme\s+(\w+)', r'let me \1'),
                (r'gimme\s+(\w+)', r'give me \1'),
                (r'whatcha\s+(\w+)', r'what are you \1'),
                (r'how\'?bout', r'how about'),
                (r'i\'?mma', r'i am going to'),
                (r'ya\'?ll', r'you all'),
                (r'dunno', r'don\'t know'),
                (r'kinda', r'kind of'),
                (r'sorta', r'sort of'),
                (r'coulda', r'could have'),
                (r'shoulda', r'should have'),
                (r'woulda', r'would have'),
                (r'musta', r'must have'),
            ],
            'ms': [
                (r'tak\s+(\w+)', r'tidak \1'),
                (r'x\s+(\w+)', r'tidak \1'),
                (r'tgk\s+(\w+)', r'tengok \1'),
                (r'nmpk\s+(\w+)', r'nampak \1'),
                (r'camne\s+(\w+)', r'bagaimana \1'),
                (r'skrz\s+(\w+)', r'sukar \1'),
                (r'senrz\s+(\w+)', r'senang \1'),
                (r'sgt\s+(\w+)', r'sangat \1'),
                (r'g\s+(\w+)', r'sangat \1'),
                (r'skit\s+(\w+)', r'sedikit \1'),
            ],
            'zh': [
                (r'啥(\w+)', r'什么\1'),
                (r'咋(\w+)', r'怎么\1'),
                (r'为毛', r'为什么'),
                (r'神马', r'什么'),
                (r'木有', r'没有'),
                (r'灰常', r'非常'),
                (r'炒鸡', r'超级'),
                (r'造吗', r'知道吗'),
                (r'不造', r'不知道'),
                (r'好哒', r'好的'),
                (r'阔以', r'可以'),
            ]
        }
        
        # Apply additional pattern replacements
        normalized_text = slang_analysis['normalized']
        if language in student_slang_patterns:
            for pattern, replacement in student_slang_patterns[language]:
                normalized_text = re.sub(pattern, replacement, normalized_text, flags=re.IGNORECASE)
        
        return {
            'original_query': query,
            'normalized_query': normalized_text,
            'had_slang': slang_analysis['contains_slang'],
            'language': language,
            'slang_detected': slang_analysis['contains_slang'] or (normalized_text != query)
        }

class QueryProcessor:
    def __init__(self, use_database: bool = True, data_path: str = "faix_data.csv", use_nlp: bool = True):
        # Basic flags and paths
        self.use_database = use_database
        self.use_nlp = use_nlp
        self.data_path = data_path
        
        # Initialize caches for performance optimization
        self._intent_cache = {}
        self._preprocess_cache = {}

        # Ensure logger exists early
        self.setup_logging()

        # Initialize NLP intent classifier if available and requested
        self.intent_classifier = None
        if self.use_nlp and NLP_AVAILABLE:
            try:
                self.intent_classifier = get_intent_classifier()
                self.logger.debug("NLP intent classifier ready")
            except Exception as e:
                self.logger.warning(f"Failed to initialize intent classifier: {e}")
                self.intent_classifier = None

        self.faq_model = None
        self.faix_data = None
        
        if self.use_database:
            try:
                import django
                os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')
                django.setup()
                from django_app.models import FAQEntry
                self.faq_model = FAQEntry
                entry_count = FAQEntry.objects.filter(is_active=True).count()
                self.logger.debug(f"Query Processor: {entry_count} FAQ entries from database")
                
            except Exception as e:
                self.logger.debug(f"Django unavailable, using CSV fallback: {e}")
                self.use_database = False
                self.faix_data = self.load_faix_data(self.data_path)
        else:
            self.faix_data = self.load_faix_data(self.data_path)

        # Language detector
        self.language_detector = LanguageDetector()
        
        # Add ShortFormProcessor
        self.slang_processor = ShortFormProcessor()

        # Stop words for different languages
        self.stop_words = {
            'en': set([
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 
                'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 
                'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                'will', 'would', 'should', 'could', 'can', 'may', 'might',
                'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
                'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their'
            ]),
            'ms': set([
                'yang', 'dan', 'atau', 'di', 'dalam', 'pada', 'ke', 'kepada',
                'untuk', 'dari', 'daripada', 'dengan', 'oleh', 'adalah', 'ialah',
                'akan', 'telah', 'sudah', 'belum', 'jangan', 'tidak', 'bukan',
                'saya', 'kamu', 'anda', 'dia', 'kami', 'kita', 'mereka'
            ]),
            'zh': set([
                '的', '了', '和', '在', '是', '我', '有', '就', '不', '人', '都',
                '一', '一个', '也', '很', '吗', '呢', '吧', '啊', '呀', '哦',
                '可以', '能', '会', '要', '想', '说', '看', '做', '去', '来'
            ]),
            'ar': set([
                'في', 'من', 'إلى', 'على', 'عن', 'مع', 'هذا', 'هذه', 'ذلك', 'تلك',
                'الذي', 'التي', 'الذين', 'اللاتي', 'كان', 'كانت', 'يكون', 'تكون',
                'أنا', 'أنت', 'هو', 'هي', 'نحن', 'أنتم', 'هم', 'هن',
                'و', 'أو', 'لكن', 'إذا', 'إن', 'أن', 'لا', 'لم', 'لن'
            ])
        }

        # Enhanced intent categories with multi-language translations
        self.intent_categories = {
            'course_info': {
                'en': 'Information about courses and subjects',
                'zh': '课程和科目信息',
                'ms': 'Maklumat tentang kursus dan subjek',
                'ar': 'معلومات عن الدورات والمواضيع'
            },
            'program_info': {
                'en': 'Information about programs and degrees',
                'zh': '项目和学位信息',
                'ms': 'Maklumat tentang program dan ijazah',
                'ar': 'معلومات عن البرامج والدرجات'
            },
            'registration': {
                'en': 'Registration and enrollment procedures',
                'zh': '注册和报名程序',
                'ms': 'Prosedur pendaftaran dan pendaftaran',
                'ar': 'إجراءات التسجيل والقبول'
            },
            'academic_schedule': {
                'en': 'Academic calendar and timelines',
                'zh': '学术日历和时间表',
                'ms': 'Kalendar akademik dan jadual waktu',
                'ar': 'التقويم الأكاديمي والجداول الزمنية'
            },
            'staff_contact': {
                'en': 'Faculty and staff contacts',
                'zh': '教职员工联系信息',
                'ms': 'Kontak fakulti dan kakitangan',
                'ar': 'جهات اتصال أعضاء هيئة التدريس والموظفين'
            },
            'facility_info': {
                'en': 'Campus facilities and resources',
                'zh': '校园设施和资源',
                'ms': 'Kemudahan dan sumber kampus',
                'ar': 'مرافق وموارد الحرم الجامعي'
            },
            'fees': {
                'en': 'Tuition and financial information',
                'zh': '学费和财务信息',
                'ms': 'Maklumat yuran dan kewangan',
                'ar': 'معلومات الرسوم الدراسية والمالية'
            },
            'academic_policy': {
                'en': 'Academic rules and requirements',
                'zh': '学术规则和要求',
                'ms': 'Peraturan dan keperluan akademik',
                'ar': 'القواعد والمتطلبات الأكاديمية'
            },
            'technical': {
                'en': 'IT and technical support',
                'zh': 'IT和技术支持',
                'ms': 'Sokongan IT dan teknikal',
                'ar': 'دعم تكنولوجيا المعلومات والتقنية'
            },
            'career': {
                'en': 'Career services and internships',
                'zh': '职业服务和实习',
                'ms': 'Perkhidmatan kerjaya dan latihan',
                'ar': 'خدمات التوظيف والتدريب'
            },
            'student_life': {
                'en': 'Clubs and student activities',
                'zh': '俱乐部和学生活动',
                'ms': 'Kelab dan aktiviti pelajar',
                'ar': 'الأندية والأنشطة الطلابية'
            },
            'housing': {
                'en': 'Accommodation and residence',
                'zh': '住宿和宿舍',
                'ms': 'Penginapan dan kediaman',
                'ar': 'الإقامة والسكن'
            },
            'international': {
                'en': 'International student matters',
                'zh': '国际学生事务',
                'ms': 'Hal ehwal pelajar antarabangsa',
                'ar': 'شؤون الطلاب الدوليين'
            },
            'research': {
                'en': 'Research opportunities',
                'zh': '研究机会',
                'ms': 'Peluang penyelidikan',
                'ar': 'فرص البحث'
            },
            'wellness': {
                'en': 'Health and counseling services',
                'zh': '健康和咨询服务',
                'ms': 'Perkhidmatan kesihatan dan kaunseling',
                'ar': 'خدمات الصحة والإرشاد'
            },
            'financial_aid': {'en': 'Scholarships and financial assistance', 'zh': '奖学金和经济援助'},
            'location': {'en': 'Campus location and directions', 'zh': '校园位置和方向'},
            'curriculum': {'en': 'Course content and programming languages', 'zh': '课程内容和编程语言'},
            'advising': {'en': 'Academic advising and counseling', 'zh': '学术咨询和辅导'},
            'documents': {'en': 'Transcripts and official documents', 'zh': '成绩单和官方文件'},
            'admin': {'en': 'Feedback and administrative matters', 'zh': '反馈和行政事务'},
            'about_faix': {'en': 'General information about FAIX', 'zh': '关于FAIX的一般信息'},
            'career': {'en': 'Career opportunities', 'zh': '职业机会'},
            'research': {'en': 'Research areas', 'zh': '研究领域'},
            'academic_resources': {'en': 'Academic handbook, uLearn, resources', 'zh': '学术手册, uLearn, 资源'},
            'greeting': {'en': 'Greeting', 'zh': '问候'},
            'farewell': {'en': 'Farewell', 'zh': '告别'}
        }

        # Language-specific patterns for intent detection
        self.patterns = self._initialize_patterns()

        # Startup complete - no verbose message needed
    
    def setup_logging(self):
        """Setup logging for debugging and monitoring"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger("FAIX_Query_Processor")
    
    def load_faix_data(self, csv_path: str) -> pd.DataFrame:
        """Load FAIX knowledge base from CSV"""
        try:
            if not os.path.exists(csv_path):
                if os.path.exists(f"data/{csv_path}"):
                    csv_path = f"data/{csv_path}"
                else:
                    self.logger.warning(f"File not found: {csv_path}. Using sample data.")
                    return self._create_sample_data()
            
            df = pd.read_csv(csv_path)
            
            # Validate required columns
            required_columns = ['id', 'question', 'answer', 'category', 'keywords']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns: {missing_columns}")
                raise ValueError(f"Missing columns: {missing_columns}")
            
            df['keywords'] = df['keywords'].fillna('').astype(str)
            
            self.logger.info(f"Successfully loaded {len(df)} entries from {csv_path}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading CSV: {str(e)}")
            return self._create_sample_data()
    
    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample FAIX data for testing"""
        sample_data = {
            'id': [1, 2, 3, 4, 5],
            'question': [
                'What programs does FAIX offer?',
                'How do I register for the semester?',
                'Who is the dean of FAIX?',
                'When does the fall semester start?',
                'What are the tuition fees?'
            ],
            'answer': [
                'FAIX offers Bachelor\'s degrees in Computer Science, Data Science, AI, and Cybersecurity.',
                'Register through the Student Portal at portal.faix.edu.',
                'The dean of FAIX is Dr. Sarah Mitchell.',
                'Fall 2025 semester starts on September 8, 2025.',
                'Annual tuition for Malaysian students is RM 18,000 per year.'
            ],
            'category': ['program_info', 'registration', 'staff_contact', 'academic_schedule', 'fees'],
            'keywords': [
                'program,course,degree,bachelor,major',
                'register,add subject,enroll,semester',
                'dean,staff,contact,administration',
                'semester,academic calendar,start date,fall',
                'tuition,fees,cost,payment'
            ]
        }
        return pd.DataFrame(sample_data)
    
    def _initialize_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize comprehensive language-specific patterns"""
        return {
            'en': {
                'course_info': ['course', 'courses', 'subject', 'subjects', 'module', 'modules', 'curriculum', 'class', 'classes', 'lecture', 'lectures', 'tutorial', 'tutorials'],
                'program_info': ['program', 'programs', 'programme', 'programmes', 'degree', 'degrees', 'bachelor', 'masters', 'master', 'phd', 'doctorate', 'major', 'majors', 'study', 'studies', 'offer', 'offers', 'offered', 'BCSAI', 'BCSCS', 'undergraduate', 'postgraduate'],
                'registration': ['register', 'registration', 'enroll', 'enrollment', 'enrolling', 'sign up', 'signup'],
                'admission': ['admission', 'admissions', 'apply', 'applying', 'application', 'applications', 'entry', 'requirements', 'criteria', 'international student', 'local student', 'CGPA', 'MUET', 'SPM', 'STPM'],
                'academic_schedule': ['schedule', 'schedules', 'timetable', 'timetables', 'calendar', 'when', 'time', 'times', 'date', 'dates', 'deadline', 'deadlines', 'semester', 'semesters', 'starting', 'starts', 'start'],
                'staff_contact': ['contact', 'contacts', 'email', 'emails', 'phone', 'telephone', 'number', 'numbers', 'professor', 'professors', 'lecturer', 'lecturers', 'staff', 'faculty', 'dean', 'who'],
                'facility_info': ['facility', 'facilities', 'lab', 'laboratory', 'laboratories', 'equipment', 'room', 'rooms', 'building', 'buildings', 'campus', 'library', 'libraries', 'available', 'booking'],
                'fees': ['tuition', 'fee', 'fees', 'cost', 'costs', 'payment', 'payments', 'price', 'prices', 'financial', 'money', 'scholarship', 'scholarships', 'how much'],
                'career': ['career', 'careers', 'job', 'jobs', 'employment', 'work', 'opportunity', 'opportunities', 'graduate', 'after graduation', 'profession', 'salary', 'industry'],
                'about_faix': ['about', 'FAIX', 'faculty', 'history', 'established', 'founded', 'vision', 'mission', 'objective', 'objectives', 'what is FAIX', 'tell me about', 'UTeM'],
                'research': ['research', 'project', 'projects', 'focus area', 'study', 'thesis', 'dissertation', 'publication', 'publications'],
                'academic_resources': ['handbook', 'academic handbook', 'student handbook', 'ulearn', 'portal', 'timetable', 'forms', 'certification', 'professional certification', 'education fund', 'resources'],
                'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening'],
                'farewell': ['bye', 'goodbye', 'thanks', 'thank you', 'thank', 'see you']
            },
            'ms': {
                'course_info': ['kursus', 'kursus-kursus', 'subjek', 'subjek-subjek', 'modul', 'modul-modul', 'kurikulum', 'kelas', 'kelas-kelas', 'kuliah', 'kuliah-kuliah', 'tutorial', 'tutorial-tutorial'],
                'program_info': ['program', 'program-program', 'programme', 'ijazah', 'ijazah-ijazah', 'sarjana', 'doktor', 'pengajian', 'bidang', 'tawarkan', 'ditawarkan', 'menawarkan', 'prasiswazah', 'pascasiswazah'],
                'registration': ['daftar', 'mendaftar', 'pendaftaran'],
                'admission': ['kemasukan', 'memohon', 'permohonan', 'mohon', 'syarat', 'kelayakan', 'pelajar antarabangsa', 'pelajar tempatan'],
                'academic_schedule': ['jadual', 'jadual-jadual', 'kalendar', 'bila', 'masa', 'tarikh', 'tarikh-tarikh', 'had masa', 'semester', 'semester-semester', 'bermula', 'mula'],
                'staff_contact': ['hubungi', 'menghubungi', 'emel', 'telefon', 'nombor', 'profesor', 'pensyarah', 'kakitangan', 'fakulti', 'dekan', 'siapa'],
                'facility_info': ['makmal', 'laboratori', 'kemudahan', 'kemudahan-kemudahan', 'peralatan', 'bilik', 'bilik-bilik', 'bangunan', 'bangunan-bangunan', 'kampus', 'perpustakaan', 'tersedia', 'tempahan'],
                'fees': ['yuran', 'yuran-yuran', 'kos', 'bayaran', 'bayaran-bayaran', 'harga', 'harga-harga', 'kewangan', 'wang', 'biasiswa', 'berapakah'],
                'career': ['kerjaya', 'pekerjaan', 'kerja', 'peluang', 'graduan', 'selepas tamat', 'profesion', 'gaji', 'industri'],
                'about_faix': ['tentang', 'FAIX', 'fakulti', 'sejarah', 'ditubuhkan', 'visi', 'misi', 'objektif', 'apa itu FAIX', 'beritahu saya tentang', 'UTeM'],
                'research': ['penyelidikan', 'projek', 'projek-projek', 'bidang fokus', 'kajian', 'tesis', 'disertasi', 'penerbitan'],
                'academic_resources': ['buku panduan', 'buku panduan akademik', 'buku panduan pelajar', 'ulearn', 'portal', 'jadual waktu', 'borang', 'sijil', 'sijil profesional', 'dana pendidikan', 'sumber'],
                'greeting': ['helo', 'hai', 'selamat pagi', 'selamat petang', 'selamat malam', 'apa khabar'],
                'farewell': ['selamat tinggal', 'jumpa lagi', 'terima kasih', 'bye']
            },
            'zh': {
                'course_info': ['课程', '科目', '模块', '课堂', '讲座', '辅导', '有哪些课程', '什么课程'],
                'program_info': ['专业', '项目', '学位', '学士', '硕士', '博士', '主修', '学习', '项目的信息', '关于项目', '项目信息', '提供', '提供什么', '提供哪些', '提供什么课程', '提供什么项目', '本科', '研究生'],
                'registration': ['注册', '报名', '登记', '注册表', '如何注册'],
                'admission': ['入学', '申请', '申请表', '要求', '标准', '国际学生', '本地学生'],
                'academic_schedule': ['时间表', '日历', '什么时候', '时间', '日期', '截止日期', '学期', '开始'],
                'staff_contact': ['联系', '电邮', '电话', '号码', '教授', '讲师', '员工', '学院', '院长'],
                'facility_info': ['实验室', '设备', '设施', '房间', '建筑', '校园', '图书馆', '有哪些设施', '预订'],
                'fees': ['学费', '费用', '成本', '付款', '价格', '财务', '钱', '奖学金', '是多少'],
                'career': ['职业', '工作', '就业', '机会', '毕业生', '毕业后', '专业', '薪水', '行业'],
                'about_faix': ['关于', 'FAIX', '学院', '历史', '成立', '愿景', '使命', '目标', '什么是FAIX', '告诉我关于'],
                'research': ['研究', '项目', '焦点领域', '论文', '出版物'],
                'academic_resources': ['手册', '学术手册', '学生手册', 'ulearn', '门户', '时间表', '表格', '证书', '专业认证', '教育基金', '资源'],
                'greeting': ['你好', '嗨', '早上好', '下午好', '晚上好'],
                'farewell': ['再见', '拜拜', '谢谢', '感谢']
            },
            'ar': {
                'course_info': ['دورة', 'دورات', 'الدورات', 'مادة', 'مواد', 'وحدة', 'وحدات', 'منهج', 'مناهج', 'فصل', 'فصول', 'محاضرة', 'محاضرات', 'دروس', 'ما هي الدورات', 'الدورات المتاحة'],
                'program_info': ['برنامج', 'برامج', 'البرامج', 'درجة', 'درجات', 'بكالوريوس', 'ماجستير', 'دكتوراه', 'تخصص', 'تخصصات', 'دراسة', 'دراسات', 'تقدم', 'تقدمها', 'عن البرامج', 'جامعية', 'دراسات عليا'],
                'registration': ['تسجيل', 'التسجيل', 'سجل', 'أسجل', 'كيف أسجل'],
                'admission': ['التحاق', 'قبول', 'تطبيق', 'طلب', 'استمارة', 'استمارات', 'متطلبات', 'معايير', 'طالب دولي', 'طالب محلي'],
                'academic_schedule': ['جدول', 'جداول', 'تقويم', 'تقاويم', 'متى', 'وقت', 'أوقات', 'تاريخ', 'تواريخ', 'موعد نهائي', 'فصل دراسي', 'فصول دراسية', 'يبدأ', 'تبدأ'],
                'staff_contact': ['اتصال', 'اتصالات', 'بريد إلكتروني', 'هاتف', 'هواتف', 'رقم', 'أرقام', 'أستاذ', 'أساتذة', 'محاضر', 'محاضرون', 'موظف', 'موظفون', 'كلية', 'عميد'],
                'facility_info': ['معدات', 'مرافق', 'المرافق', 'غرفة', 'غرف', 'مبنى', 'مبان', 'حرم', 'مكتبة', 'مكتبات', 'ما هي المرافق', 'المرافق المتاحة', 'حجز'],
                'fees': ['رسوم', 'الرسوم', 'تكلفة', 'تكاليف', 'دفع', 'مدفوعات', 'سعر', 'أسعار', 'مالي', 'مال', 'منحة', 'منح', 'كم'],
                'career': ['مهنة', 'وظيفة', 'عمل', 'فرصة', 'فرص', 'خريج', 'بعد التخرج', 'راتب', 'صناعة'],
                'about_faix': ['حول', 'عن', 'FAIX', 'كلية', 'تاريخ', 'تأسست', 'رؤية', 'رسالة', 'هدف', 'أهداف', 'ما هو FAIX', 'أخبرني عن'],
                'research': ['بحث', 'أبحاث', 'مشروع', 'مشاريع', 'مجال التركيز', 'أطروحة', 'منشورات'],
                'academic_resources': ['دليل', 'دليل أكاديمي', 'دليل الطالب', 'ulearn', 'بوابة', 'جدول زمني', 'نماذج', 'شهادة', 'شهادة مهنية', 'صندوق التعليم', 'موارد'],
                'greeting': ['مرحبا', 'أهلا', 'صباح الخير', 'مساء الخير'],
                'farewell': ['مع السلامة', 'وداعا', 'شكرا', 'إلى اللقاء']
            }
        }
    
    def _preprocess_logic(self, text: str, language: str) -> str:
        """Internal text preprocessing logic (extracted for caching)"""
        text = text.strip()
        
        # Keep original Chinese/Arabic characters, clean others
        if language not in ['zh', 'ar']:
            text = text.lower()
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Language-specific cleaning
        if language == 'zh':
            # For Chinese, keep Chinese characters, numbers, and basic punctuation
            text = re.sub(r'[^\u4e00-\u9fff0-9\s?.,!？，。！]', '', text)
            # Normalize multiple consecutive punctuation marks to single ones
            text = re.sub(r'([？，。！?!.,])+', r'\1', text)
        elif language == 'ar':
            # For Arabic, keep Arabic characters, numbers, and basic punctuation
            text = re.sub(r'[^\u0600-\u06FF0-9\s?.,!؟،؛]', '', text)
            # Normalize multiple consecutive punctuation marks to single ones
            text = re.sub(r'([؟،؛?!.,])+', r'\1', text)
        else:
            # For English/Malay, keep alphanumeric and basic punctuation
            text = re.sub(r'[^\w\s?.,!]', '', text)
            # Normalize multiple consecutive punctuation marks to single ones
            # But remove excessive question marks and exclamation marks
            text = re.sub(r'[?!]{2,}', '', text)  # Remove multiple ? or !
            text = re.sub(r'([.,])+', r'\1', text)  # Normalize multiple dots/commas to single
        
        # Final cleanup: remove trailing punctuation and extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        # Remove trailing punctuation for English/Malay (but keep single ? for questions)
        if language not in ['zh', 'ar']:
            text = re.sub(r'[.,!]+$', '', text).strip()
        
        return text
    
    def preprocess_text(self, text: str, language: str = 'en') -> str:
        """Clean and normalize the input text for specific language (cached)"""
        # Use simple in-memory cache
        text_key = text.strip()[:200]  # Limit key length
        cache_key = hash((text_key, language))
        
        if cache_key in self._preprocess_cache:
            return self._preprocess_cache[cache_key]
        
        result = self._preprocess_logic(text, language)
        # Cache results with size limit
        if len(self._preprocess_cache) > PREPROCESS_CACHE_SIZE:
            self._preprocess_cache = dict(list(self._preprocess_cache.items())[PREPROCESS_CACHE_SIZE // 2:])
        self._preprocess_cache[cache_key] = result
        return result
    
    def tokenize_text(self, text: str, language: str = 'en') -> List[str]:
        """Split text into tokens and remove stop words for specific language"""
        # Chinese tokenization is different (character/word based)
        if language == 'zh':
            # Simple Chinese tokenization - split by common delimiters
            tokens = []
            current_token = ""
            for char in text:
                if char in [' ', '，', '。', '？', '！', '、']:
                    if current_token:
                        tokens.append(current_token)
                        current_token = ""
                else:
                    current_token += char
            if current_token:
                tokens.append(current_token)
        elif language == 'ar':
            # Arabic tokenization - split by spaces and Arabic punctuation
            tokens = []
            current_token = ""
            for char in text:
                if char in [' ', '،', '؛', '؟', '!', '.', ',', ';', '?']:
                    if current_token:
                        tokens.append(current_token)
                        current_token = ""
                else:
                    current_token += char
            if current_token:
                tokens.append(current_token)
        else:
            # English/Malay tokenization
            tokens = text.split()
        
        # Remove stop words
        stop_words = self.stop_words.get(language, self.stop_words['en'])
        tokens = [token for token in tokens if token not in stop_words and len(token) > 1]
        
        return tokens
    
    def detect_language(self, query: str) -> Dict[str, Any]:
        """Detect language of the query with confidence"""
        lang_code = self.language_detector.detect(query)
        
        lang_names = {
            'en': {'code': 'en', 'name': 'English'},
            'ms': {'code': 'ms', 'name': 'Bahasa Malaysia'},
            'zh': {'code': 'zh', 'name': 'Chinese'},
            'ar': {'code': 'ar', 'name': 'Arabic'}
        }
        
        return lang_names.get(lang_code, lang_names['en'])
    
    def detect_intent_keyword(self, text: str, language: str) -> Tuple[str, float]:
        """Keyword-based intent detection for specific language (cached)"""
        # Cache intent detection results
        cache_key = hash((text.strip()[:200], language))
        if cache_key in self._intent_cache:
            return self._intent_cache[cache_key]
        
        if language not in self.patterns:
            language = 'en'  # Default to English
        
        language_patterns = self.patterns[language]
        text_lower = text.lower() if language not in ['zh', 'ar'] else text
        
        # Priority rules: certain patterns should override keyword matching
        # Check for high-priority patterns first
        priority_patterns = {
            'about_faix': [
                'when was faix', 'when was the faculty', 'when was faix established',
                'when was faix founded', 'when is faix', 'history of faix',
                'what is faix', 'what is the faculty', 'who is dean', 'who is the dean',
                'dean', 'head of faculty', 'who is the head', 'vision', 'mission',
                'what is the vision', 'what is the mission', 'faix vision', 'faix mission',
                'objective', 'objectives', 'what are the objectives', 'faix objectives',
                'top management', 'management', 'leadership', 'who are the leaders'
            ],
            'program_info': [
                'what programs', 'what programmes', 'what programs does',
                'what programmes does', 'what programs are', 'what programmes are',
                'what programs does faix', 'programs does faix', 'programs does faix offer',
                'what degrees', 'programs available', 'programmes available',
                'tell me about bcsai', 'tell me about bcscs', 'tell me about program'
            ],
            'staff_contact': [
                'who can i contact', 'who should i contact', 'who should i email',
                'who can i', 'how do i contact', 'contact information',
                'staff contact', 'email address', 'phone number',
                'contact staff', 'get in touch', 'staff email', 'staff phone',
                'faculty contact', 'who can i', 'contact information',
                'who can i contact?', 'contact staff', 'staff email', 'staff phone'
            ],
            'academic_schedule': [
                'academic calendar', 'when does the semester', 'when is the semester',
                'when is semester', 'when does semester', 'semester start',
                'semester dates', 'semester start date', 'when does semester start',
                'important dates', 'when are classes', 'when are class',
                'when is the', 'when are the'
            ],
            'admission': [
                'admission', 'admission requirements', 'what are admission', 'entry requirements',
                'admission criteria', 'what are the admission', 'admission requirement',
                'entry criteria', 'how to apply'
            ],
            'facility_info': [
                'what facilities', 'what labs', 'what laboratories', 'facilities available',
                'labs available', 'laboratories available'
            ],
            'research': [
                'what research', 'research areas', 'research areas are',
                'research focus', 'research focus areas', 'what research are',
                'research projects', 'faculty research', 'what research areas are',
                'research areas are the', 'what research areas'
            ]
        }
        
        # Check priority patterns first (exact phrase matching)
        # Order matters - check more specific patterns first
        for intent, patterns in priority_patterns.items():
            for pattern in patterns:
                # Use word boundary matching for single words to avoid false positives
                if ' ' in pattern:
                    # Multi-word pattern: check if pattern is in text
                    if pattern in text_lower:
                        result = (intent, 0.9)  # High confidence for exact pattern match
                        self._intent_cache[cache_key] = result
                        return result
                else:
                    # Single-word pattern: check with word boundaries for exact match
                    if pattern == text_lower.strip() or f" {pattern} " in f" {text_lower} " or text_lower.startswith(pattern + " ") or text_lower.endswith(" " + pattern):
                        result = (intent, 0.9)  # High confidence for exact pattern match
                        self._intent_cache[cache_key] = result
                        return result
        
        intent_scores = {}
        
        # Define specific high-weight keywords for better intent differentiation
        specific_keywords = {
            'program_info': ['bcsai', 'bcscs', 'mcsss', 'mtdsa', 'ai programme', 'cybersecurity programme', 
                           'computer science', 'artificial intelligence', 'cyber security', 'data science',
                           'what programs', 'what programmes', 'programs available', 'programs does faix'],
            'course_info': ['subject', 'subjects', 'module', 'modules', 'curriculum', 'coursework', 'practical',
                          'what courses', 'what subjects', 'what modules'],
            'admission': ['admission requirements', 'entry requirements', 'admission criteria', 'how to apply',
                         'application process', 'cgpa', 'muet', 'eligibility'],
            'staff_contact': ['who can i contact', 'staff email', 'staff phone', 'contact information',
                            'faculty contact', 'get in touch'],
            'academic_schedule': ['academic calendar', 'when is semester', 'when does semester', 'semester dates',
                                'when are classes', 'important dates'],
            'research': ['research areas', 'research focus', 'what research', 'faculty research'],
            'fees': ['tuition fees', 'tuition', 'how much', 'payment schedule']
        }
        
        # Define ambiguous keywords that should have lower weight
        ambiguous_keywords = ['program', 'programme', 'course', 'contact', 'about', 'information']
        
        for intent, keywords in language_patterns.items():
            score = 0
            keyword_match_count = 0
            has_multiword_match = False
            
            for keyword in keywords:
                keyword_lower = keyword.lower()
                keyword_weight = 2  # Default weight
                
                # Higher weight for specific keywords
                if intent in specific_keywords and keyword_lower in specific_keywords[intent]:
                    keyword_weight = 4
                # Lower weight for ambiguous keywords (unless in specific list)
                elif keyword_lower in ambiguous_keywords:
                    if intent not in specific_keywords or keyword_lower not in specific_keywords[intent]:
                        keyword_weight = 1
                
                # Check for multi-word keywords (boost if found)
                is_multiword = ' ' in keyword
                
                # For Chinese and Arabic, check if keyword is in text directly
                if language in ['zh', 'ar']:
                    if keyword in text:
                        score += keyword_weight
                        keyword_match_count += 1
                        if is_multiword:
                            has_multiword_match = True
                        # Bonus for exact word match
                        if f" {keyword} " in f" {text} " or text.startswith(keyword + " ") or text.endswith(" " + keyword):
                            score += 1
                else:
                    # For other languages, check in lowercase text
                    if keyword in text_lower:
                        score += keyword_weight
                        keyword_match_count += 1
                        if is_multiword:
                            has_multiword_match = True
                        # Bonus for exact word match
                        if f" {keyword} " in f" {text_lower} ":
                            score += 1
            
            # Boost for multi-word matches (indicates more specific intent)
            if has_multiword_match:
                score += 1
            
            # Special handling for program_info vs course_info distinction
            if intent == 'program_info':
                # Boost if we have specific program keywords
                program_specific = ['bcsai', 'bcscs', 'degree', 'bachelor', 'master', 'undergraduate', 'postgraduate']
                if any(kw in text_lower for kw in program_specific):
                    score += 2
            elif intent == 'course_info':
                # Only boost course_info if we have course-specific keywords (not just "program")
                course_specific = ['subject', 'module', 'curriculum', 'coursework', 'practical']
                if any(kw in text_lower for kw in course_specific):
                    score += 2
                # Penalize if "program" appears without course-specific context
                if 'program' in text_lower and not any(kw in text_lower for kw in course_specific):
                    # Don't boost course_info if "program" appears
                    pass
            
            # Prioritize specific intents over general_query
            # If a specific intent has any score, reduce general_query's influence
            if intent != 'general_query' and score > 0:
                # Boost specific intents
                score += SPECIFIC_INTENT_BOOST
            
            if score > 0:
                # Store score and keyword match count together
                intent_scores[intent] = (score, keyword_match_count)
        
        # Remove general_query from scores if we have any specific intents
        # Greetings and farewells are handled as specific intents now
        if 'general_query' in intent_scores:
            del intent_scores['general_query']
        
        if intent_scores:
            # Get best intent (compare by score, which is first element of tuple)
            best_intent = max(intent_scores.items(), key=lambda x: x[1][0] if isinstance(x[1], tuple) else x[1])
            intent_name = best_intent[0]
            # Extract score and keyword match count
            if isinstance(best_intent[1], tuple):
                raw_score, keyword_match_count = best_intent[1]
            else:
                raw_score = best_intent[1]
                keyword_match_count = 1  # Fallback if not tracked
            
            # Improved confidence calculation that doesn't penalize short queries
            # For short queries (1-2 words), use a simpler normalization
            query_word_count = len(text.strip().split())
            
            if query_word_count <= 2:
                # Short queries: normalize by typical score for 1-2 keyword matches
                # A single keyword match with exact bonus = 2 + 1 + boost = 5 (with new boost of 2)
                # Short queries with single keyword should get 0.6-0.8 confidence
                base_score = 5.0  # Typical score for 1 keyword match (updated for new boost)
                confidence = raw_score / base_score
                
                # For short queries, apply intelligent confidence scaling
                if raw_score >= 8:
                    confidence = 0.85  # Strong match (multiple keywords)
                elif raw_score >= 6:
                    confidence = 0.75  # Good match (multiple keywords)
                elif raw_score >= 5:
                    confidence = 0.70  # Good match (1 keyword with bonuses)
                elif raw_score >= 4:
                    confidence = 0.65  # Decent match
                elif raw_score >= 3:
                    confidence = 0.60  # Basic match
                else:
                    confidence = 0.50  # Weak match (raised from 0.40)
                
                # Cap at 0.9 for short queries (leave room for priority patterns)
                confidence = min(confidence, 0.9)
            else:
                # Longer queries: use improved normalization with query length consideration
                # Consider query word count in normalization to avoid penalizing longer queries
                max_possible_score = len(language_patterns.get(intent_name, [])) * 4  # Increased multiplier
                
                # Base normalization
                confidence = min(raw_score / max(max_possible_score, 1), 1.0)
                
                # Boost for longer queries with good keyword matches
                # Queries with 2+ keyword matches get additional boost
                if keyword_match_count >= 2:
                    confidence = min(confidence * 1.4, 0.95)
                elif raw_score >= 8:
                    confidence = min(confidence * 1.3, 0.95)
                elif raw_score >= 6:
                    confidence = min(confidence * 1.25, 0.90)
                elif raw_score >= 4:
                    confidence = min(confidence * 1.2, 0.85)
            
            # Improved minimum confidence thresholds
            if raw_score >= 6:
                confidence = max(confidence, 0.8)  # At least 80% confidence for strong matches
            elif raw_score >= 4:
                confidence = max(confidence, 0.7)  # At least 70% confidence for good matches
            elif raw_score >= 2:
                confidence = max(confidence, 0.6)  # At least 60% confidence if we matched something (raised from 0.5)
            elif raw_score >= 1:
                confidence = max(confidence, 0.5)  # At least 50% confidence for any match (raised from 0.3)
            
            # Minimum confidence boost for Chinese and Arabic
            if language in ['zh', 'ar'] and confidence < 0.3:
                confidence = 0.3
            
            result = (intent_name, confidence)
            # Cache the result
            if len(self._intent_cache) > INTENT_CACHE_SIZE:
                # Clear half when cache gets too large
                self._intent_cache = dict(list(self._intent_cache.items())[INTENT_CACHE_SIZE // 2:])
            self._intent_cache[cache_key] = result
            return result
        
        # Default to about_faix (general FAIX info) with low confidence when no match
        # Increased default confidence to better reflect uncertainty
        result = ('about_faix', 0.2 if language == 'zh' else 0.3)
        # Cache the result
        if len(self._intent_cache) > INTENT_CACHE_SIZE:
            self._intent_cache = dict(list(self._intent_cache.items())[INTENT_CACHE_SIZE // 2:])
        self._intent_cache[cache_key] = result
        return result
    
    def detect_intent(self, text: str, language: str) -> Tuple[str, float]:
        """
        Detect the main intent of the user query.
        Uses NLP model if available, otherwise falls back to keyword matching.
        """
        nlp_intent = None
        nlp_confidence = 0.0
        
        # Try NLP-based classification first (for English)
        if self.use_nlp and self.intent_classifier and language == 'en':
            try:
                intent, confidence, all_scores = self.intent_classifier.classify(text)
                
                # Map to our intent categories - improved mapping
                intent_mapping = {
                    'course_info': 'course_info',
                    'course_info_program': 'program_info',  # Maps program-related courses to program_info
                    'registration': 'registration',
                    'schedule': 'academic_schedule',
                    'staff': 'staff_contact',
                    'facilities': 'facility_info',
                    'fees': 'fees',
                    'admission': 'admission',
                    'career': 'career',
                    'about': 'about_faix',
                    'research': 'research',
                    'greeting': 'greeting',
                    'farewell': 'farewell',
                    'program_info': 'program_info',  # Direct mapping if NLP returns this
                    'academic_schedule': 'academic_schedule',  # Direct mapping
                    'staff_contact': 'staff_contact'  # Direct mapping
                }
                
                mapped_intent = intent_mapping.get(intent, None)
                
                # Store NLP results for comparison with keyword matching
                if mapped_intent:
                    nlp_intent = mapped_intent
                    nlp_confidence = confidence
                    
                    # Use NLP result only if confidence is reasonable (raised threshold to 0.4)
                    # BUT first check if keyword matching would give better results
                    keyword_intent, keyword_confidence = self.detect_intent_keyword(text, language)
                    
                    # If keyword matching found a significantly better match (priority patterns), use it
                    # Priority patterns return 0.9, so they should always win
                    if keyword_confidence >= 0.8 and keyword_confidence > nlp_confidence:
                        return keyword_intent, keyword_confidence
                    
                    # Use NLP result if confidence is reasonable
                    if confidence >= 0.4:
                        return mapped_intent, confidence
                
                # If NLP confidence is low or intent not mapped, fall through to keyword matching
                # This avoids defaulting to about_faix unnecessarily
            except Exception as e:
                self.logger.debug(f"NLP classification failed, using fallback: {e}")
        
        # Use keyword-based detection for all languages
        # This will find the best match and not default to about_faix unless truly no matches
        keyword_intent, keyword_confidence = self.detect_intent_keyword(text, language)
        
        # Compare NLP and keyword results if NLP was attempted and hasn't returned yet
        if nlp_intent and nlp_confidence >= 0.3:
            # If keyword matching found a significantly better match, use it
            # Priority patterns (0.9) should always win over NLP
            if keyword_confidence > nlp_confidence + 0.2:
                return keyword_intent, keyword_confidence
            # If NLP confidence is close or better, use NLP result
            elif nlp_confidence >= keyword_confidence - 0.1:
                return nlp_intent, nlp_confidence
        
        # Return keyword result (better than defaulting to about_faix)
        return keyword_intent, keyword_confidence
    
    def extract_entities(self, text: str, language: str) -> Dict[str, List[str]]:
        """Extract important entities from the text for specific language"""
        entities = {}
        
        # Course codes
        if codes := re.findall(r'\b(BAXI|BAXZ|BITZ|BAXS)\b', text, re.IGNORECASE):
            entities['course_codes'] = [code.upper() for code in codes]
        
        # Course codes with numbers
        if codes_with_nums := re.findall(r'\b(BAXI|BAXZ|BITZ|BAXS)\s?\d{3,4}\b', text, re.IGNORECASE):
            entities['course_codes'] = entities.get('course_codes', [])
            entities['course_codes'].extend([code.upper().replace(' ', '') for code in codes_with_nums])
        
        # Emails
        if emails := re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text):
            entities['emails'] = emails
        
        # Dates
        if dates := re.findall(r'\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}', text):
            entities['dates'] = dates
        
        # Phone numbers
        phones = []
        phones.extend(re.findall(r'\+60\s?\d{2}[-.\s]?\d{3}[-.\s]?\d{4}', text))
        phones.extend(re.findall(r'0\d{2}[-.\s]?\d{3}[-.\s]?\d{4}', text))
        if phones:
            entities['phones'] = phones
        
        # MYR amounts
        if amounts := re.findall(r'RM\s?\d+(?:,\d{3})*(?:\.\d{2})?', text, re.IGNORECASE):
            entities['amounts'] = amounts
        
        return entities
    
    def _identify_missing_info(self, intent: str, entities: Dict, language: str) -> List[str]:
        """Identify what information might be missing for better responses"""
        missing = []
        
        if intent == 'course_info' and 'course_codes' not in entities:
            if language == 'zh':
                missing.append('具体课程代码或名称')
            elif language == 'ms':
                missing.append('kod kursus atau nama khusus')
            elif language == 'ar':
                missing.append('رمز الدورة أو الاسم المحدد')
            else:
                missing.append('specific course code or name')
        
        elif intent == 'staff_contact' and 'staff_names' not in entities:
            if language == 'zh':
                missing.append('教职员工姓名')
            elif language == 'ms':
                missing.append('nama kakitangan')
            elif language == 'ar':
                missing.append('اسم الموظف')
            else:
                missing.append('staff member name')
        
        elif intent == 'registration' and 'dates' not in entities:
            if language == 'zh':
                missing.append('具体日期或学期')
            elif language == 'ms':
                missing.append('tarikh atau semester khusus')
            elif language == 'ar':
                missing.append('تاريخ محدد أو فصل دراسي')
            else:
                missing.append('specific date or semester')
        
        return missing
    
    def search_faix_knowledge(self, query: str, intent: str, keywords: List[str], language: str) -> List[Dict[str, Any]]:
        """Search FAIX knowledge base using appropriate data source"""
        # For program_info queries, check JSON data first (from separated files)
        if intent == 'program_info':
            json_matches = self._search_programs_json(query, language)
            if json_matches:
                return json_matches
        
        if self.use_database and self.faq_model:
            return self._search_database(query, intent, keywords, language)
        else:
            return self._search_csv(query, intent, keywords, language)
    
    def _search_programs_json(self, query: str, language: str) -> List[Dict[str, Any]]:
        """Search programs from JSON data files"""
        try:
            import json
            from pathlib import Path
            
            # Load programmes.json
            base_dir = Path(__file__).parent.parent
            programmes_path = base_dir / 'data' / 'separated' / 'programmes.json'
            
            if not programmes_path.exists():
                return []
            
            with open(programmes_path, 'r', encoding='utf-8') as f:
                programmes_data = json.load(f)
            
            programmes = programmes_data.get('programmes', {})
            undergraduate = programmes.get('undergraduate', [])
            postgraduate = programmes.get('postgraduate', [])
            
            query_lower = query.lower()
            matches = []
            
            # Check if query is about undergraduate programs
            if any(kw in query_lower for kw in ['undergraduate', 'bachelor', 'degree']):
                for prog in undergraduate:
                    matches.append({
                        'id': f"prog_{prog.get('code', '').lower()}",
                        'question': f"What is {prog.get('name', '')}?",
                        'answer': self._format_program_answer(prog),
                        'category': 'program_info',
                        'match_score': 10,
                        'keywords': [prog.get('code', '').lower()] + prog.get('focus_areas', [])[:3],
                        'language': language
                    })
                if matches:
                    return matches
            
            # Check if query is about postgraduate programs
            if any(kw in query_lower for kw in ['master', 'postgraduate', 'graduate']):
                for prog in postgraduate:
                    matches.append({
                        'id': f"prog_{prog.get('code', '').lower()}",
                        'question': f"What is {prog.get('name', '')}?",
                        'answer': f"**{prog.get('name', '')}** ({prog.get('code', '')})\n  - Type: {prog.get('type', '')}\n  - Focus: {prog.get('focus', '')}",
                        'category': 'program_info',
                        'match_score': 10,
                        'keywords': [prog.get('code', '').lower()],
                        'language': language
                    })
                if matches:
                    return matches
            
            # For general program queries, return all undergraduate programs (most common)
            for prog in undergraduate:
                matches.append({
                    'id': f"prog_{prog.get('code', '').lower()}",
                    'question': f"What is {prog.get('name', '')}?",
                    'answer': self._format_program_answer(prog),
                    'category': 'program_info',
                    'match_score': 8,
                    'keywords': [prog.get('code', '').lower()] + prog.get('focus_areas', [])[:3],
                    'language': language
                })
            
            return matches
            
        except Exception as e:
            self.logger.debug(f"Error searching programs JSON: {e}")
            return []
    
    def _format_program_answer(self, prog: Dict) -> str:
        """Format program information as answer"""
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
    
    def _search_database(self, query: str, intent: str, keywords: List[str], language: str) -> List[Dict[str, Any]]:
        """Search FAIX knowledge base in Django database"""
        try:
            from django.db.models import Q
            
            # PERFORMANCE OPTIMIZATION: Limit keywords to top 5 most important
            keywords = keywords[:5] if len(keywords) > 5 else keywords
            
            # Build search query
            search_query = Q(is_active=True)
            
            # Search in questions and keywords
            for keyword in keywords:
                if len(keyword) > 1:  # Chinese characters can be single
                    search_query &= (Q(question__icontains=keyword) | Q(keywords__icontains=keyword))
            
            # Filter by category if intent matches
            intent_category_map = {
                'course_info': 'course_info',
                'program_info': 'program_info',
                'registration': 'registration',
                'academic_schedule': 'academic_schedule',
                'staff_contact': 'staff_contact',
                'facility_info': 'facility_info',
                'fees': 'fees',
                'admission': 'admission',
                'career': 'career',
                'about_faix': 'about',
                'research': 'research'
            }
            
            category = intent_category_map.get(intent)
            if category:
                search_query &= Q(category=category)
            
            # PERFORMANCE OPTIMIZATION: Use .only() to fetch only needed fields and limit results
            results = self.faq_model.objects.filter(search_query)\
                .only('id', 'question', 'answer', 'category', 'keywords', 'view_count')\
                .order_by('-view_count')[:10]
            
            # Format results
            matches = []
            query_lower = query.lower() if language not in ['zh', 'ar'] else query
            
            for faq in results:
                score = 0
                
                # Category match
                if faq.category == intent:
                    score += 2
                
                # Keyword matches in question
                question_text = faq.question.lower() if language not in ['zh', 'ar'] else faq.question
                for keyword in keywords:
                    if keyword in question_text:
                        score += 1
                
                # Check keywords field
                faq_keywords = [k.strip() for k in faq.keywords.split(',')] if faq.keywords else []
                if any(keyword in query_lower for keyword in faq_keywords):
                    score += 3
                
                # Direct question match
                if query_lower in question_text:
                    score += 5
                
                if score > 0:
                    matches.append({
                        'id': faq.id,
                        'question': faq.question,
                        'answer': faq.answer,
                        'category': faq.category,
                        'match_score': score,
                        'keywords': faq_keywords,
                        'language': language
                    })
            
            matches.sort(key=lambda x: x['match_score'], reverse=True)
            return matches[:3]
            
        except Exception as e:
            self.logger.error(f"Database search error: {e}")
            return []
    
    def _search_csv(self, query: str, intent: str, keywords: List[str], language: str) -> List[Dict[str, Any]]:
        """Search FAIX knowledge base in CSV data"""
        knowledge_items = []
        for _, row in self.faix_data.iterrows():
            knowledge_items.append({
                'id': row.get('id', _),
                'question': row['question'],
                'answer': row['answer'],
                'category': row['category'],
                'keywords': str(row['keywords']).split(',') if pd.notna(row['keywords']) else []
            })
        
        matches = []
        query_lower = query.lower() if language != 'zh' else query
        
        for item in knowledge_items:
            score = 0
            
            # Check category match
            if item['category'] == intent:
                score += 2
            
            # Check question text match
            question_text = str(item['question']).lower() if language not in ['zh', 'ar'] else str(item['question'])
            for keyword in keywords:
                if keyword in question_text:
                    score += 1
            
            # Check direct substring match
            if query_lower in question_text:
                score += 3
            
            # Check keyword field match
            item_keywords = item['keywords']
            for keyword in keywords:
                if keyword in item_keywords:
                    score += 2
            
            if score > 0:
                matches.append({
                    'id': item['id'],
                    'question': item['question'],
                    'answer': item['answer'],
                    'category': item['category'],
                    'match_score': score,
                    'keywords': item_keywords,
                    'language': language
                })
        
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches[:3]
    
    def process_query(self, user_input: str) -> Dict[str, Any]:
        """
        Main method: Process user query through all steps
        """
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"Processing query: '{user_input}'")
        
        # Detect language first
        language_info = self.detect_language(user_input)
        language_code = language_info['code']
        
        # Check and normalize short forms/slang
        slang_analysis = self.slang_processor.process_query_with_slang(user_input, language_code)
        
        # Use normalized text for processing if slang was detected
        if slang_analysis['slang_detected']:
            processing_text = slang_analysis['normalized_query']
            self.logger.info(f"Detected slang/short forms. Normalized: '{user_input}' -> '{processing_text}'")
        else:
            processing_text = user_input
            self.logger.debug(f"No slang detected in: '{user_input}'")
        
        # Preprocess text with language-specific handling
        cleaned_text = self.preprocess_text(processing_text, language_code)
        
        # Tokenize with language-specific handling
        tokens = self.tokenize_text(cleaned_text, language_code)
        
        # Detect intent with language-specific handling
        intent, confidence = self.detect_intent(cleaned_text, language_code)
        
        # Extract entities with language-specific handling
        entities = self.extract_entities(processing_text, language_code)
        
        # Search FAIX knowledge base
        keywords = tokens  # Use all tokens as keywords for now
        faix_results = self.search_faix_knowledge(cleaned_text, intent, keywords, language_code)
        
        # Identify missing information
        missing_info = self._identify_missing_info(intent, entities, language_code)
        
        # Get intent description in correct language
        intent_description = self.intent_categories.get(intent, {}).get(language_code, 
                             self.intent_categories.get('about_faix', {}).get(language_code, 'General information about FAIX'))
        
        # Prepare comprehensive output
        processed_data = {
            'module': 'query_processor',
            'timestamp': datetime.now().isoformat(),
            
            # Original input
            'original_query': user_input,
            'normalized_query': processing_text if slang_analysis['slang_detected'] else user_input,
            'cleaned_query': cleaned_text,
            'tokens': tokens,
            
            # Language information
            'language': language_info,
            
            # Slang/short form information
            'slang_analysis': {
                'had_slang': slang_analysis['slang_detected'],
                'normalized': slang_analysis['normalized_query'] if slang_analysis['slang_detected'] else None,
            },
            
            # Intent information
            'detected_intent': intent,
            'intent_description': intent_description,
            'confidence_score': round(confidence, 2),
            'requires_clarification': confidence < 0.3,
            
            # Extracted information
            'extracted_entities': entities,
            
            # FAIX knowledge results
            'faix_matches': faix_results,
            
            # Missing information for clarification
            'missing_info': missing_info,
            
            # NLP capabilities used
            'nlp_capabilities': {
                'intent_classifier_used': self.use_nlp and confidence >= 0.3 and language_code == 'en',
                'advanced_nlp_available': NLP_AVAILABLE,
                'short_form_processed': slang_analysis['slang_detected']
            },
            
            # Data source info
            'data_source': 'database' if self.use_database else 'csv'
        }
        
        self.logger.info(f"Processing complete. Intent: {intent}, Language: {language_info['name']}")
        if slang_analysis['slang_detected']:
            self.logger.info(f"Short forms detected and normalized")
        self.logger.info(f"Confidence: {confidence:.0%}, Matches: {len(faix_results)}")
        self.logger.info(f"{'='*50}\n")
        
        return processed_data
    
    def quick_test(self, query: str):
        """Quick test for a single query"""
        print(f"\nQUICK TEST: '{query}'")
        print(f"{'─'*50}")
        
        result = self.process_query(query)
        
        print(f"Intent: {result['detected_intent']} ({result['intent_description']})")
        print(f"Confidence: {result['confidence_score']}")
        print(f"Language: {result['language']['name']}")
        if result['slang_analysis']['had_slang']:
            print(f"Short forms: YES → Normalized: {result['normalized_query']}")
        else:
            print(f"Short forms: No")
        print(f"Data Source: {result['data_source']}")
        print(f"Entities: {result['extracted_entities']}")
        print(f"Clarification Needed: {result['requires_clarification']}")
        print(f"FAIX Matches: {len(result['faix_matches'])}")
        
        if result['faix_matches']:
            print(f"Top match: {result['faix_matches'][0]['question']}")
    
    def run_demo(self):
        """Run demonstration"""
        print("\n" + "="*60)
        print("FAIX CHATBOT - QUERY PROCESSOR DEMONSTRATION")
        print("="*60)
        
        print(f"\nUsing {'Django Database' if self.use_database else 'CSV File'} as data source")
        print("Interactive Mode - Type queries to test")
        print("Commands: 'sample' for examples, 'slang' for short form examples, 'test' for full test, 'quit' to exit")
        print("-"*60)
        
        # Test with short forms immediately
        print("\nTesting short form query: 'wanna know bout FAIX prog'")
        self.quick_test("wanna know bout FAIX prog")
        print("-"*60)
        
        while True:
            try:
                query = input("\nEnter your query: ").strip()
                
                if query.lower() == 'quit':
                    break
                elif query.lower() == 'sample':
                    print("\nSample queries:")
                    print("  1. What programs does FAIX offer? (English)")
                    print("  2. Kursus apa yang ditawarkan FAIX? (Malay)")
                    print("  3. 课程 (Chinese)")
                    print("  4. How to register for BAXI? (English)")
                    print("  5. 学费多少？ (Chinese)")
                    continue
                elif query.lower() == 'slang':
                    print("\nShort form/slang examples:")
                    print("  English:")
                    print("    - wanna know bout cs prog")
                    print("    - how 2 register 4 sem")
                    print("    - pls tell me bout uni fees")
                    print("    - where's prof office?")
                    print("    - whenz exam timetable?")
                    print("  Malay:")
                    print("    - nak tau pasal kursus cs")
                    print("    - camne nk daftar utk sem")
                    print("    - kwn ckp fees byk sgt")
                    print("    - dekan kat mne?")
                    print("    - exam bile?")
                    print("  Chinese:")
                    print("    - 啥课程")
                    print("    - 咋报名")
                    print("    - 学费多少")
                    print("    - 老师在哪")
                    print("    - 考试啥时候")
                    continue
                
                if not query:
                    continue
                
                self.quick_test(query)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    def test_slang_processing(self):
        """Test the slang/short form processor"""
        test_cases = [
            ("wanna know bout FAIX prog", "en"),
            ("how 2 register 4 sem", "en"),
            ("wherez prof office?", "en"),
            ("nak tau pasal kursus cs", "ms"),
            ("camne nk daftar utk sem", "ms"),
            ("dekan kat mne?", "ms"),
            ("啥课程", "zh"),
            ("咋报名", "zh"),
            ("学费多少", "zh"),
            ("u r gonna need 2 register b4 sem starts", "en"),
            ("idk wat fees r 4 cs prog", "en"),
            ("tq 4 ur help", "en"),
        ]
        
        print("\n" + "="*60)
        print("SHORT FORM/SLANG PROCESSOR TEST")
        print("="*60)
        
        for query, expected_lang in test_cases:
            lang_info = self.detect_language(query)
            lang_code = lang_info['code']
            
            print(f"\nQuery: '{query}'")
            print(f"Detected language: {lang_info['name']} (expected: {expected_lang})")
            
            result = self.slang_processor.process_query_with_slang(query, lang_code)
            
            if result['slang_detected']:
                print(f"Contains slang: YES")
                print(f"Normalized: '{result['normalized_query']}'")
            else:
                print(f"Contains slang: NO")
        
        print("\n" + "="*60)

def create_query_processor(data_path: str = "faix_data.csv", use_nlp: bool = True, use_database: bool = True):
    """Factory function to create and return QueryProcessor instance"""
    return QueryProcessor(use_database=use_database, data_path=data_path, use_nlp=use_nlp)

if __name__ == "__main__":
    # Run the demo when this file is executed directly
    processor = create_query_processor()
    processor.run_demo()
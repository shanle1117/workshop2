import os

# Suppress warnings
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
# GPU enabled - models will use GPU if available (CUDA)
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['PYTHONWARNINGS'] = 'ignore'

import re
import json
import logging
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from collections import defaultdict

try:
    from nlp_intent_classifier import get_intent_classifier
    INTENT_CLASSIFIER_AVAILABLE = True
    print("Intent classifier module available")
except ImportError:
    INTENT_CLASSIFIER_AVAILABLE = False
    print("Note: nlp_intent_classifier.py not found. Install transformers for advanced intent detection.")

class LanguageDetector:
    """Language detection for English, Malay, Chinese"""
    
    LANGUAGE_KEYWORDS = {
        'en': [ 
            'course', 'program', 'register', 'enroll', 'semester', 'faculty',
            'student', 'professor', 'dean', 'contact', 'email', 'phone',
            'schedule', 'tuition', 'fee', 'library', 'lab', 'campus',
            'admission', 'academic', 'credit', 'gpa', 'degree', 'major'
        ],
        'ms': [ 
            'kursus', 'program', 'daftar', 'mendaftar', 'semester', 'fakulti',
            'pelajar', 'profesor', 'dekan', 'hubungi', 'emel', 'telefon',
            'jadual', 'yuran', 'bayaran', 'perpustakaan', 'makmal', 'kampus',
            'penerimaan', 'akademik', 'kredit', 'png', 'ijazah', 'pengajian'
        ],
        'zh': [ 
            '课程', '程序', '注册', '报名', '学期', '学院',
            '学生', '教授', '院长', '联系', '电邮', '电话',
            '时间表', '学费', '费用', '图书馆', '实验室', '校园',
            '入学', '学术', '学分', '平均分', '学位', '专业'
        ]
    }
    
    def detect(self, text: str) -> str:
        """
        Detect language of input text
        Returns: 'en', 'ms', or 'zh'
        """
        text_lower = text.lower()
        
        # Check for Chinese characters first
        if self._has_chinese(text):
            return 'zh'
        
        # Count keyword matches for each language
        scores = {'en': 0, 'ms': 0, 'zh': 0}
        
        for lang, keywords in self.LANGUAGE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[lang] += 1
        
        # If no keywords found, check for common phrases
        if sum(scores.values()) == 0:
            return self._fallback_detection(text_lower)
        
        # Return language with highest score
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _has_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters"""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False
    
    def _fallback_detection(self, text: str) -> str:
        """Fallback detection using common phrases"""
        malay_phrases = ['apa', 'bagaimana', 'untuk', 'dengan', 'adalah']
        chinese_phrases = ['什么', '如何', '吗', '呢', '的']
        
        for phrase in malay_phrases:
            if phrase in text:
                return 'ms'
        
        for phrase in chinese_phrases:
            if phrase in text:
                return 'zh'
        
        return 'en'

class QueryProcessor:
    """
    MODULE 1: Query Processing
    Processes user input to identify main intention and language
    """
    
    def __init__(self, data_path: str = "faix_data.csv"):
        """
        Initialize Query Processor with FAIX data
        """
        self.setup_logging()
        self.language_detector = LanguageDetector()
        self.faix_data = self.load_faix_data(data_path)
        
        # Define intent categories based on FAIX data
        self.intent_categories = {
            'programs': 'Information about courses and degrees',
            'registration': 'Registration and enrollment procedures',
            'staff': 'Faculty and staff contacts',
            'schedule': 'Academic calendar and timelines',
            'fees': 'Tuition and financial information',
            'facilities': 'Campus facilities and resources',
            'academic_policy': 'Academic rules and requirements',
            'technical': 'IT and technical support',
            'career': 'Career services and internships',
            'student_life': 'Clubs and student activities',
            'housing': 'Accommodation and residence',
            'international': 'International student matters',
            'research': 'Research opportunities',
            'wellness': 'Health and counseling services',
            'financial_aid': 'Scholarships and financial assistance',
            'location': 'Campus location and directions',
            'curriculum': 'Course content and programming languages',
            'advising': 'Academic advising and counseling',
            'documents': 'Transcripts and official documents',
            'admin': 'Feedback and administrative matters',
            'about_faix': 'General information about FAIX faculty',
            'career': 'Career opportunities and job prospects',
            'greeting': 'Greetings from user',
            'farewell': 'Farewell from user'
        }
        
        # Language-specific patterns for intent detection
        self.patterns = self._initialize_patterns()
        
        self.enhanced_pattern_weights = {
            'programs': {'program': 3, 'course': 3, 'degree': 2, 'major': 2, 'study': 1},
            'fees': {'tuition': 4, 'fee': 3, 'cost': 2, 'payment': 2},
            'staff': {'dean': 4, 'professor': 2, 'contact': 2},
            'registration': {'register': 3, 'enroll': 3, 'apply': 2},
            'facilities': {'library': 4, 'lab': 3, 'campus': 2}
        }

        # Initialize advanced NLP modules
        self.intent_classifier = None
        
        if INTENT_CLASSIFIER_AVAILABLE:
            try:
                # Use a simpler model to avoid loading issues
                self.intent_classifier = get_intent_classifier(
                    model_name='typeform/distilbert-base-uncased-mnli',  # Smaller model
                    use_zero_shot=True
                )
                if self.intent_classifier and hasattr(self.intent_classifier, 'is_available') and self.intent_classifier.is_available():
                    self.logger.info("Advanced intent classifier loaded")
                else:
                    self.logger.warning("Intent classifier loaded but not available")
            except Exception as e:
                self.logger.warning(f"Could not load intent classifier: {e}")
        
        self.logger.info(f"Query Processor initialized with {len(self.faix_data)} FAIX entries")
    
    def setup_logging(self):
        """Setup logging for debugging and monitoring"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger("FAIX_Query_Processor")
    
    def load_faix_data(self, csv_path: str) -> pd.DataFrame:
        """Load FAIX knowledge base from CSV with comprehensive error handling"""
        try:
            # Check if file exists
            if not os.path.exists(csv_path):
                # Try to find it in data directory
                if not os.path.exists(f"data/{csv_path}"):
                    self.logger.warning(f"File not found: {csv_path}. Checking in data/ directory...")
                    csv_path = f"data/{csv_path}"
                
                if not os.path.exists(csv_path):
                    self.logger.warning(f"File not found: {csv_path}. Using sample data.")
                    return self._create_sample_data()
            
            # Load CSV file
            df = pd.read_csv(csv_path)
            
            # Validate required columns
            required_columns = ['id', 'question', 'answer', 'category', 'keywords']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                self.logger.error(f"Missing required columns in CSV: {missing_columns}")
                raise ValueError(f"CSV file missing required columns: {missing_columns}")
            
            # Clean and validate data
            df['keywords'] = df['keywords'].fillna('').astype(str)
            
            self.logger.info(f"Successfully loaded {len(df)} entries from {csv_path}")
            self.logger.info(f"Categories found: {df['category'].unique().tolist()}")
            
            return df
            
        except FileNotFoundError:
            self.logger.warning(f"File not found: {csv_path}. Using sample data.")
            return self._create_sample_data()
        except pd.errors.EmptyDataError:
            self.logger.warning(f"CSV file is empty: {csv_path}. Using sample data.")
            return self._create_sample_data()
        except Exception as e:
            self.logger.error(f"Error loading CSV: {str(e)}")
            return self._create_sample_data()
    
    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample FAIX data for testing - using CSV content as template"""
        # Sample data that matches the CSV structure
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
                'FAIX offers Bachelor\'s degrees in Computer Science, Data Science, Artificial Intelligence, and Cybersecurity.',
                'You can register through the Student Portal at portal.faix.edu.',
                'The dean of FAIX is Dr. Sarah Mitchell.',
                'The Fall 2025 semester starts on September 8, 2025.',
                'Annual tuition for Malaysian students is RM 18,000 per year.'
            ],
            'category': ['programs', 'registration', 'staff', 'schedule', 'fees'],
            'keywords': [
                'program,course,degree,bachelor,master,major',
                'register,add subject,enroll,course registration,semester',
                'dean,staff,contact,administration,leadership',
                'semester,academic calendar,start date,fall,schedule',
                'tuition,fees,cost,payment,price,money'
            ]
        }
        df = pd.DataFrame(sample_data)
        self.logger.warning(f"Created sample data with {len(df)} entries")
        return df
    
    def _initialize_patterns(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize language-specific patterns for intent detection"""
        # Get all unique categories from the loaded data
        categories = self.faix_data['category'].unique().tolist()
        self.logger.info(f"Initializing patterns for categories: {categories}")
        
        # Base patterns that can be extended based on actual data
        base_patterns = {
            'en': {
                'programs': ['program', 'course', 'degree', 'major', 'study', 'bachelor', 'master'],
                'registration': ['register', 'enroll', 'admission', 'apply', 'add course', 'drop course'],
                'staff': ['dean', 'professor', 'lecturer', 'staff', 'contact', 'email', 'phone', 'office'],
                'schedule': ['semester', 'start date', 'calendar', 'timetable', 'when', 'deadline', 'exam'],
                'fees': ['tuition', 'fee', 'cost', 'payment', 'price', 'financial', 'scholarship'],
                'facilities': ['library', 'lab', 'campus', 'building', 'facility', 'room', 'wifi', 'computer'],
                'technical': ['technical', 'support', 'it', 'computer', 'software', 'hardware', 'internet'],
                'wellness': ['counseling', 'health', 'mental', 'wellness', 'support', 'psychologist'],
                'career': ['internship', 'job', 'career', 'employment', 'placement'],
                'academic_policy': ['gpa', 'grade', 'credit', 'attendance', 'policy', 'rule'],
                'financial_aid': ['scholarship', 'financial aid', 'funding', 'loan', 'bursary'],
                'location': ['location', 'address', 'campus', 'where', 'map', 'direction'],
                'curriculum': ['programming', 'language', 'code', 'CS', 'computer science', 'learning'],
                'advising': ['advisor', 'advising', 'academic help', 'counseling', 'guidance'],
                'documents': ['transcript', 'document', 'certificate', 'record', 'official'],
                'admin': ['feedback', 'complaint', 'suggestion', 'issue', 'problem', 'concern'],
                'housing': ['accommodation', 'dorm', 'housing', 'residence', 'hostel', 'room'],
                'student_life': ['club', 'society', 'organization', 'activities', 'extracurricular'],
                'international': ['exchange', 'study abroad', 'international', 'overseas', 'foreign'],
                'research': ['research', 'project', 'undergraduate', 'study', 'investigation']
            },
            'ms': {
                'programs': ['program', 'kursus', 'ijazah', 'pengajian', 'sarjana', 'dasar', 'subjek'],
                'registration': ['daftar', 'mendaftar', 'pendaftaran', 'memohon', 'tambah kursus', 'buang kursus'],
                'staff': ['dekan', 'profesor', 'pensyarah', 'kakitangan', 'hubungi', 'emel', 'telefon', 'pejabat'],
                'schedule': ['semester', 'tarikh mula', 'kalendar', 'jadual', 'bila', 'had masa', 'peperiksaan'],
                'fees': ['yuran', 'kos', 'bayaran', 'harga', 'kewangan', 'biasiswa'],
                'facilities': ['perpustakaan', 'makmal', 'kampus', 'bangunan', 'kemudahan', 'bilik', 'wifi', 'komputer'],
                'technical': ['teknikal', 'sokongan', 'it', 'komputer', 'perisian', 'perkakasan', 'internet'],
                'wellness': ['kaunseling', 'kesihatan', 'mental', 'kesejahteraan', 'sokongan', 'psikologi'],
                'career': ['internship', 'pekerjaan', 'kerjaya', 'tempatan', 'penempatan'],
                'academic_policy': ['gpa', 'gred', 'kredit', 'kehadiran', 'polisi', 'peraturan'],
                'financial_aid': ['biasiswa', 'bantuan kewangan', 'pembiayaan', 'pinjaman', 'dermasiswa'],
                'location': ['lokasi', 'alamat', 'kampus', 'di mana', 'peta', 'arah'],
                'curriculum': ['pengaturcaraan', 'bahasa', 'kod', 'CS', 'sains komputer', 'pembelajaran'],
                'advising': ['penasihat', 'nasihat', 'bantuan akademik', 'kaunseling', 'panduan'],
                'documents': ['transkrip', 'dokumen', 'sijil', 'rekod', 'rasmi'],
                'admin': ['maklum balas', 'aduan', 'cadangan', 'isu', 'masalah', 'kebimbangan'],
                'housing': ['penginapan', 'asrama', 'perumahan', 'tempat tinggal', 'hostel', 'bilik'],
                'student_life': ['kelab', 'persatuan', 'organisasi', 'aktiviti', 'kokurikulum'],
                'international': ['pertukaran', 'belajar di luar negara', 'antarabangsa', 'luar negara', 'asing'],
                'research': ['penyelidikan', 'projek', 'prasiswazah', 'kajian', 'penyiasatan']
            },
            'zh': {
                'programs': ['课程', '专业', '学位', '学习', '学士', '硕士', '科目'],
                'registration': ['注册', '报名', '登记', '申请', '加课', '退课'],
                'staff': ['院长', '教授', '讲师', '员工', '联系', '电邮', '电话', '办公室'],
                'schedule': ['学期', '开始日期', '日历', '时间表', '什么时候', '截止日期', '考试'],
                'fees': ['学费', '费用', '付款', '价格', '财务', '奖学金'],
                'facilities': ['图书馆', '实验室', '校园', '建筑', '设施', '房间', '无线网', '电脑'],
                'technical': ['技术', '支持', 'IT', '电脑', '软件', '硬件', '网络'],
                'wellness': ['咨询', '健康', '心理', '健康', '支持', '心理学家'],
                'career': ['实习', '工作', '职业', '就业', '安置'],
                'academic_policy': ['平均分', '成绩', '学分', '出勤', '政策', '规则'],
                'financial_aid': ['奖学金', '经济援助', '资金', '贷款', '助学金'],
                'location': ['位置', '地址', '校园', '哪里', '地图', '方向'],
                'curriculum': ['编程', '语言', '代码', '计算机科学', '学习'],
                'advising': ['顾问', '咨询', '学术帮助', '辅导', '指导'],
                'documents': ['成绩单', '文件', '证书', '记录', '官方'],
                'admin': ['反馈', '投诉', '建议', '问题', '关注'],
                'housing': ['住宿', '宿舍', '住房', '住所', '旅馆', '房间'],
                'student_life': ['俱乐部', '社团', '组织', '活动', '课外活动'],
                'international': ['交换', '留学', '国际', '海外', '外国'],
                'research': ['研究', '项目', '本科', '学习', '调查']
            }
        }
        
        return base_patterns
    
    def preprocess_query(self, query: str) -> str:
        """
        Clean and normalize the user query
        """
        query = query.lower().strip()
        query = re.sub(r'\s+', ' ', query)
        query = re.sub(r'[^\w\s?]', '', query)
        self.logger.debug(f"Preprocessed query: '{query}'")
        return query
    
    def detect_language(self, query: str) -> Dict[str, str]:
        """
        Detect language of the query
        """
        lang_code = self.language_detector.detect(query)
        
        lang_names = {
            'en': 'English',
            'ms': 'Bahasa Malaysia',
            'zh': 'Chinese'
        }
        
        result = {
            'code': lang_code,
            'name': lang_names.get(lang_code, 'English'),
            'confidence': 'high'
        }
        
        self.logger.info(f"Detected language: {result['name']}")
        return result
    
    def extract_keywords(self, query: str, language: str) -> List[str]:
        """
        Extract important keywords from query
        """
        words = query.split()
        
        # Remove common stop words
        stop_words = self._get_stop_words(language)
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Also check for multi-word patterns from our FAIX data
        for _, row in self.faix_data.iterrows():
            if pd.notna(row['keywords']):
                for keyword in str(row['keywords']).split(','):
                    keyword = keyword.strip()
                    if keyword and keyword in query.lower():
                        keywords.append(keyword)
        
        # Remove duplicates
        keywords = list(set(keywords))
        
        self.logger.debug(f"Extracted keywords: {keywords}")
        return keywords
    
    def _get_stop_words(self, language: str) -> List[str]:
        """Get stop words for each language"""
        stop_words = {
            'en': ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'do', 'does', 'can', 'could', 'would', 'should'],
            'ms': ['yang', 'dan', 'atau', 'di', 'dalam', 'pada', 'ke', 'untuk', 'dari', 'dengan', 'adalah', 'akan', 'telah', 'boleh', 'dapat', 'hendak', 'mahu'],
            'zh': ['的', '了', '和', '在', '是', '我', '有', '就', '不', '人', '都', '一', '一个', '也', '很', '吗', '呢', '可以', '能', '会', '要']
        }
        return stop_words.get(language, stop_words['en'])
    
    def _correct_intent_misclassification(self, intent: str, query_lower: str) -> str:
        """
        Correct common misclassifications from the transformer model
        """
        correction_rules = {
            'registration': [
                {
                    'keywords': ['program', 'course', 'degree', 'offer', 'available', 'provide'],
                    'correction': 'programs'
                },
                {
                    'keywords': ['tuition', 'fee', 'cost', 'payment', 'price', 'money', 'financial'],
                    'correction': 'fees'
                },
                {
                    'keywords': ['library', 'lab', 'facility', 'campus', 'building', 'room'],
                    'correction': 'facilities'
                },
                {
                    'keywords': ['when', 'schedule', 'semester', 'start', 'date', 'time'],
                    'correction': 'schedule'
                }
            ],
            'programs': [
                {
                    'keywords': ['register', 'enroll', 'admission', 'apply', 'sign up'],
                    'correction': 'registration'
                },
                {
                    'keywords': ['tuition', 'fee', 'cost', 'payment'],
                    'correction': 'fees'
                }
            ],
            'about_faix': [
                {
                    'keywords': ['program', 'course', 'degree', 'study'],
                    'correction': 'programs'
                },
                {
                    'keywords': ['register', 'enroll', 'apply'],
                    'correction': 'registration'
                },
                {
                    'keywords': ['dean', 'professor', 'staff', 'contact'],
                    'correction': 'staff'
                },
                {
                    'keywords': ['tuition', 'fee', 'cost'],
                    'correction': 'fees'
                },
                {
                    'keywords': ['library', 'lab', 'facility'],
                    'correction': 'facilities'
                },
                {
                    'keywords': ['career', 'job', 'work', 'employment'],
                    'correction': 'career'
                }
            ]
        }
        
        if intent in correction_rules:
            for rule in correction_rules[intent]:
                for keyword in rule['keywords']:
                    if keyword in query_lower:
                        return rule['correction']
        
        return intent

    def _boost_confidence(self, intent: str, query_lower: str, base_confidence: float) -> float:
        """Boost confidence for specific patterns"""
        # Rules to boost confidence for clear patterns
        boost_rules = {
            'programs': [('program', 0.3), ('course', 0.25), ('offer', 0.2), ('degree', 0.25), ('study', 0.15)],
            'fees': [('tuition', 0.4), ('fee', 0.35), ('cost', 0.3), ('payment', 0.25), ('price', 0.2)],
            'staff': [('dean', 0.5), ('professor', 0.3), ('contact', 0.25), ('email', 0.2), ('phone', 0.2)],
            'registration': [('register', 0.4), ('enroll', 0.35), ('apply', 0.3), ('admission', 0.25)],
            'facilities': [('library', 0.4), ('lab', 0.35), ('facility', 0.3), ('campus', 0.25), ('building', 0.2)],
            'schedule': [('when', 0.3), ('schedule', 0.35), ('semester', 0.3), ('date', 0.25), ('start', 0.2)],
            'financial_aid': [('scholarship', 0.4), ('financial aid', 0.35), ('funding', 0.3), ('bursary', 0.3)],
            'technical': [('password', 0.4), ('reset', 0.3), ('technical', 0.3), ('support', 0.25), ('it', 0.2)]
        }
        
        if intent in boost_rules:
            total_boost = 0
            for keyword, boost_value in boost_rules[intent]:
                if keyword in query_lower:
                    total_boost += boost_value
            
            # Cap the boost to avoid exceeding 1.0 too much
            boosted_confidence = min(base_confidence + total_boost, 1.0)
            return boosted_confidence
        
        return base_confidence

    def detect_intent(self, query: str, language: str) -> Dict[str, Any]:
        """
        Detect user intent from query with advanced NLP fallback and corrections
        """
        query_lower = query.lower()
        
        # Enhanced category mapping with more specific mappings
        enhanced_category_mapping = {
            'course_info': 'programs',
            'registration': 'registration',
            'academic_schedule': 'schedule',
            'staff_contact': 'staff',
            'facility_info': 'facilities',
            'program_info': 'programs',
            'admission': 'admission',
            'fees': 'fees',
            'financial': 'financial_aid',
            'technical': 'technical',
            'career': 'career',
            'housing': 'housing',
            'international': 'international',
            'research': 'research',
            'wellness': 'wellness',
            'location': 'location',
            'curriculum': 'curriculum',
            'advising': 'advising',
            'documents': 'documents',
            'admin': 'admin',
            'financial_aid': 'financial_aid',
            'student_life': 'student_life',
            'academic_policy': 'academic_policy',
            'about_faix': 'about_faix',
            'greeting': 'greeting',
            'farewell': 'farewell'
        }
        
        # Try advanced classifier first if available
        if self.intent_classifier and hasattr(self.intent_classifier, 'is_available') and self.intent_classifier.is_available():
            try:
                intent, confidence, details = self.intent_classifier.classify(query)
                
                # Map to our categories
                mapped_intent = enhanced_category_mapping.get(intent, 'about_faix')
                
                # Apply correction rules for common misclassifications
                corrected_intent = self._correct_intent_misclassification(mapped_intent, query_lower)
                
                # Boost confidence for clear patterns
                boosted_confidence = self._boost_confidence(corrected_intent, query_lower, confidence)
                
                # If confidence is reasonable after boosting, use transformer result
                if boosted_confidence > 0.3:
                    was_corrected = corrected_intent != mapped_intent
                    
                    result_dict = {
                        'category': corrected_intent,
                        'original_category': mapped_intent,
                        'original_intent': intent,
                        'description': self.intent_categories.get(corrected_intent, 'General inquiry'),
                        'confidence': round(boosted_confidence, 2),
                        'confidence_level': self._get_confidence_level(boosted_confidence),
                        'method': 'transformer',
                        'corrected': was_corrected,
                        'correction_note': f"Corrected from {mapped_intent}" if was_corrected else None
                    }
                    
                    correction_info = f" (corrected from {result_dict.get('original_category')})" if result_dict.get('corrected') else ""
                    self.logger.info(f"Detected intent: {result_dict['category']}{correction_info} ({result_dict['confidence']:.0%} confidence, method: {result_dict['method']})")
                    
                    return result_dict
                else:
                    self.logger.debug(f"Transformer confidence too low ({boosted_confidence:.2f}), falling back to keyword")
                    
            except Exception as e:
                self.logger.debug(f"Advanced classifier failed: {e}")
        
        # Enhanced keyword-based detection with weighted patterns
        language_patterns = self.patterns.get(language, self.patterns['en'])
        
        # Define pattern weights for better accuracy
        pattern_weights = {
            'programs': {'program': 3, 'course': 3, 'degree': 2, 'major': 2, 'study': 1, 'bachelor': 2, 'master': 2},
            'registration': {'register': 3, 'enroll': 3, 'admission': 2, 'apply': 2, 'add course': 3, 'drop course': 3},
            'staff': {'dean': 4, 'professor': 2, 'lecturer': 2, 'staff': 1, 'contact': 2, 'email': 1, 'phone': 1, 'office': 1},
            'fees': {'tuition': 4, 'fee': 3, 'cost': 2, 'payment': 2, 'price': 2, 'financial': 1, 'scholarship': 2},
            'facilities': {'library': 4, 'lab': 3, 'campus': 2, 'building': 2, 'facility': 1, 'room': 1, 'wifi': 2, 'computer': 1},
            'schedule': {'semester': 3, 'start date': 3, 'calendar': 2, 'timetable': 2, 'when': 1, 'deadline': 2, 'exam': 2},
            'technical': {'technical': 3, 'support': 2, 'it': 2, 'computer': 1, 'software': 1, 'hardware': 1, 'internet': 1},
            'wellness': {'counseling': 3, 'health': 2, 'mental': 2, 'wellness': 1, 'support': 1, 'psychologist': 2},
            'financial_aid': {'scholarship': 4, 'financial aid': 3, 'funding': 2, 'bursary': 2, 'loan': 2},
            'location': {'location': 3, 'address': 3, 'campus': 2, 'where': 2, 'map': 1, 'direction': 1}
        }
        
        # Calculate weighted scores
        scores = {}
        max_possible_score = {}
        
        for intent, patterns in language_patterns.items():
            score = 0
            max_score = 0
            
            for pattern in patterns:
                weight = pattern_weights.get(intent, {}).get(pattern, 1)
                max_score += weight
                
                if pattern in query_lower:
                    # Check for exact matches (better than substring)
                    words = query_lower.split()
                    if pattern in words or any(word.startswith(pattern) for word in words):
                        score += weight * 2  # Bonus for exact/close match
                    else:
                        score += weight
            
            # Normalize score
            if max_score > 0:
                scores[intent] = score / max_score
                max_possible_score[intent] = max_score
        
        # Find best matching intent
        if scores:
            best_intent = max(scores.items(), key=lambda x: x[1])
            intent_name = best_intent[0]
            confidence = best_intent[1]
            
            # Special handling for low confidence
            if confidence < 0.3:
                # Try to match against FAIX categories
                faix_intent, faix_confidence = self._match_faix_categories(query_lower)
                
                # Choose the better one
                if faix_confidence > confidence:
                    intent_name = faix_intent
                    confidence = faix_confidence
                    
                    # Apply confidence boost for FAIX matches
                    confidence = min(confidence * 1.5, 0.9)
            
            # Final confidence adjustment based on query length and specificity
            if len(query.split()) >= 4:  # Longer queries are usually more specific
                confidence = min(confidence * 1.2, 0.95)
        else:
            intent_name = 'about_faix'
            confidence = 0.15  # Slightly higher baseline for keyword method
        
        result = {
            'category': intent_name,
            'description': self.intent_categories.get(intent_name, 'General inquiry'),
            'confidence': round(confidence, 2),
            'confidence_level': self._get_confidence_level(confidence),
            'method': 'keyword',
            'details': {
                'scores': {k: round(v, 3) for k, v in scores.items() if v > 0.1} if scores else {},
                'query_length': len(query.split())
            }
        }
        
        self.logger.info(f"Detected intent: {result['category']} ({result['confidence']:.0%} confidence, method: {result['method']})")
        
        if result['confidence'] < 0.4:
            self.logger.debug(f"Low confidence intent detection. Query: '{query}', Scores: {result['details']['scores']}")
        
        return result
    
    def _match_faix_categories(self, query: str) -> Tuple[str, float]:
        """Match query against FAIX data categories"""
        best_match = 'about_faix'
        best_score = 0.0
        
        for _, row in self.faix_data.iterrows():
            category = row['category']
            keywords = str(row['keywords']).split(',') if pd.notna(row['keywords']) else []
            
            score = 0
            for keyword in keywords:
                if keyword.strip() and keyword.strip() in query:
                    score += 1
            
            normalized_score = score / len(keywords) if keywords else 0
            
            if normalized_score > best_score:
                best_score = normalized_score
                best_match = category
        
        return best_match, best_score
    
    def _get_confidence_level(self, score: float) -> str:
        """Convert numerical score to confidence level"""
        if score >= 0.8:
            return 'very_high'
        elif score >= 0.6:
            return 'high'
        elif score >= 0.4:
            return 'medium'
        elif score >= 0.2:
            return 'low'
        else:
            return 'very_low'
    
    def extract_entities(self, query: str) -> Dict[str, List[str]]:
        """
        Extract entities from query
        """
        entities = {
            'course_codes': re.findall(r'[A-Z]{2,4}\s?\d{4}', query, re.IGNORECASE),
            'emails': re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', query),
            'phones': re.findall(r'(\+?6?0?\d{1,2})?[-.\s]?\d{3,4}[-.\s]?\d{3,4}', query),
            'dates': re.findall(r'\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}', query),
            'amounts': re.findall(r'RM\s?\d+(?:,\d{3})*(?:\.\d{2})?|\$\s?\d+(?:,\d{3})*(?:\.\d{2})?', query)
        }
        
        # Filter out empty lists
        entities = {k: v for k, v in entities.items() if v}
        
        if entities:
            self.logger.debug(f"Extracted entities: {entities}")
        
        return entities
    
    def search_faix_knowledge(self, query: str, intent: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Search FAIX knowledge base using keyword matching
        """
        # Prepare knowledge items
        knowledge_items = []
        for _, row in self.faix_data.iterrows():
            knowledge_items.append({
                'id': row.get('id', _),
                'question': row['question'],
                'answer': row['answer'],
                'category': row['category'],
                'keywords': str(row['keywords']).split(',') if pd.notna(row['keywords']) else []
            })
        
        # Keyword-based search
        matches = []
        query_lower = query.lower()
        
        for item in knowledge_items:
            score = 0
            
            # Check category match
            if item['category'] == intent:
                score += 2
            
            # Check question text match
            question_lower = str(item['question']).lower()
            if any(keyword in question_lower for keyword in keywords):
                score += 1
            
            # Check direct substring match
            if query_lower in question_lower or any(keyword in query_lower for keyword in item['keywords']):
                score += 3
            
            # If we have a match, add to results
            if score > 0:
                matches.append({
                    'id': item['id'],
                    'question': item['question'],
                    'answer': item['answer'],
                    'category': item['category'],
                    'match_score': score,
                    'keywords': item['keywords'],
                    'method': 'keyword'
                })
        
        # Sort by match score (highest first)
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        
        # Return top 3 matches
        return matches[:3]
    
    def _get_related_intents(self, primary_intent: str) -> List[str]:
        """Get related intent categories for broader search"""
        related_map = {
            'programs': ['curriculum', 'academic_policy', 'career'],
            'registration': ['academic_policy', 'schedule', 'fees'],
            'staff': ['facilities', 'technical', 'student_life'],
            'schedule': ['registration', 'academic_policy', 'exam'],
            'fees': ['financial_aid', 'registration', 'academic_policy'],
            'facilities': ['student_life', 'technical', 'housing'],
            'financial_aid': ['fees', 'registration', 'academic_policy'],
            'technical': ['facilities', 'registration', 'schedule'],
            'career': ['programs', 'research', 'student_life'],
            'academic_policy': ['programs', 'registration', 'schedule']
        }
        return related_map.get(primary_intent, [])
    
    def process_query(self, user_input: str) -> Dict[str, Any]:
        """
        Main method: Process user query through all steps
        """
        self.logger.info(f"\n{'='*50}")
        self.logger.info(f"Processing query: '{user_input}'")
        
        # Preprocess
        processed_query = self.preprocess_query(user_input)
        
        # Detect language
        language_info = self.detect_language(processed_query)
        
        # Extract keywords
        keywords = self.extract_keywords(processed_query, language_info['code'])
        
        # Detect intent
        intent_info = self.detect_intent(processed_query, language_info['code'])
        
        # Extract entities
        entities = self.extract_entities(user_input)
        
        # Search FAIX knowledge base
        faix_results = self.search_faix_knowledge(
            processed_query, 
            intent_info['category'], 
            keywords
        )

        result = {
            'module': 'query_processor',
            'timestamp': datetime.now().isoformat(),
            
            # Original input
            'raw_input': user_input,
            'processed_input': processed_query,
            
            # Language information
            'language': language_info,
            
            # Intent information
            'intent': intent_info,
            
            # Extracted information
            'keywords': keywords,
            'entities': entities,
            
            # FAIX knowledge results
            'faix_matches': faix_results,
            
            # NLP capabilities used
            'nlp_capabilities': {
                'intent_classifier_used': intent_info.get('method') == 'transformer',
                'advanced_nlp_available': INTENT_CLASSIFIER_AVAILABLE
            },
            
            # Flags for Module 3
            'requires_clarification': intent_info['confidence'] < 0.3,
            'needs_human_assistance': len(faix_results) == 0 and intent_info['confidence'] < 0.2,
            
            # Search parameters for Module 2
            'search_parameters': {
                'primary_intent': intent_info['category'],
                'secondary_intents': self._get_related_intents(intent_info['category']),
                'search_terms': keywords + list(entities.keys()),
                'language_filter': language_info['code']
            }
        }
        
        self.logger.info(f"Processing complete. Intent: {intent_info['category']}, Language: {language_info['name']}")
        self.logger.info(f"NLP methods: Intent={intent_info.get('method')}")
        self.logger.info(f"{'='*50}\n")
        
        return result

def run_demo():
    """Run demonstration of the Query Processor using CSV data"""
    print("\n" + "="*60)
    print("FAIX CHATBOT - NLP MODULE DEMONSTRATION")
    print("Group 20: AI Chatbot Assistance for FAIX Students")
    print("="*60)
    
    # Initialize processor
    print("\nInitializing Query Processor...")
    processor = QueryProcessor("faix_data.csv")
    
    # Check NLP capabilities
    print(f"\nNLP Capabilities:")
    print(f"  Intent Classifier: {'Available' if processor.intent_classifier and hasattr(processor.intent_classifier, 'is_available') and processor.intent_classifier.is_available() else 'Not available'}")
    
    # Show data summary
    print(f"\nData Summary:")
    print(f"  Total entries loaded: {len(processor.faix_data)}")
    print(f"  Categories available: {processor.faix_data['category'].unique().tolist()}")
    
    # Interactive mode
    print(f"\nInteractive Mode - Enter queries based on CSV data")
    print("Type 'quit' to exit, 'sample' for example queries")
    print("-"*60)
    
    while True:
        try:
            query = input("\nEnter your query: ").strip()
            
            if query.lower() == 'quit':
                break
            elif query.lower() == 'sample':
                print("\nSample queries from CSV:")
                print("  1. What programs does FAIX offer?")
                print("  2. How do I register for the semester?")
                print("  3. Who is the dean of FAIX?")
                print("  4. When does the fall semester start?")
                print("  5. What are the tuition fees?")
                print("  6. How can I apply for financial aid?")
                print("  7. Where is the FAIX campus located?")
                continue
            
            if not query:
                continue
            
            # Process the query
            result = processor.process_query(query)
            
            # Display results
            print(f"\nResults:")
            print(f"  Language: {result['language']['name']}")
            print(f"  Intent: {result['intent']['category']} ({result['intent']['confidence']:.0%} confidence)")
            print(f"  Intent Method: {result['intent'].get('method', 'keyword')}")
            print(f"  Keywords: {', '.join(result['keywords'][:5])}")
            
            if result['faix_matches']:
                print(f"\nTop match from CSV:")
                print(f"  Q: {result['faix_matches'][0]['question']}")
                print(f"  A: {result['faix_matches'][0]['answer'][:150]}...")
                print(f"  Category: {result['faix_matches'][0]['category']}")
                print(f"  Match Score: {result['faix_matches'][0]['match_score']:.1f}")
            else:
                print(f"\nNo direct matches found in CSV data")
                print("Try rephrasing your question or using keywords from the CSV")
            
        except KeyboardInterrupt:
            print("\n\nInterrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nError processing query: {str(e)}")
    
    print("\n" + "="*60)
    print("NLP Module Demonstration Complete!")
    print("="*60)

def export_for_module2():
    """Export processed data for Module 2 integration"""
    processor = QueryProcessor("faix_data.csv")
    
    # Process sample queries from CSV
    sample_queries = [
        "What programs does FAIX offer?",
        "How do I register for courses?",
        "What are the tuition fees?"
    ]

    print(f"\nProcessing {len(sample_queries)} sample queries from CSV...")
    
    all_results = []
    for query in sample_queries:
        print(f"\nQuery: '{query}'")
        result = processor.process_query(query)
        all_results.append(result)
        
        print(f"  Language: {result['language']['name']}")
        print(f"  Intent: {result['intent']['category']}")
        print(f"  Matches: {len(result['faix_matches'])}")
    
    # Save to JSON for Module 2
    output_file = "module1_output.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\nModule 1 output saved to: {output_file}")
    print(f"Summary exported for Module 2: Knowledge Base & Response Generation")
    print(f"Contains {len(all_results)} processed queries with intent detection and CSV matching")

def validate_csv_data():
    """Validate and display information about the CSV data"""
    print("\n" + "="*60)
    print("VALIDATING CSV DATA")
    print("="*60)
    
    try:
        # Try to load CSV directly
        df = pd.read_csv("faix_data.csv")
        
        print(f"\nCSV File Information:")
        print(f"  File: faix_data.csv")
        print(f"  Total rows: {len(df)}")
        print(f"  Columns: {df.columns.tolist()}")
        
        print(f"\nCategory Distribution:")
        category_counts = df['category'].value_counts()
        for category, count in category_counts.items():
            print(f"  {category}: {count} questions")
        
        print(f"\nSample Questions:")
        for i, row in df.head(3).iterrows():
            print(f"  {i+1}. [{row['category']}] {row['question'][:50]}...")
        
        print(f"\nKeywords Summary:")
        all_keywords = []
        for keywords in df['keywords'].dropna():
            all_keywords.extend([k.strip() for k in str(keywords).split(',') if k.strip()])
        
        unique_keywords = set(all_keywords)
        print(f"  Total unique keywords: {len(unique_keywords)}")
        print(f"  Sample keywords: {', '.join(list(unique_keywords)[:10])}")
        
        return True
        
    except Exception as e:
        print(f"\nError loading CSV: {str(e)}")
        print("Make sure faix_data.csv is in the current directory or data/ directory")
        return False

if __name__ == "__main__":
    """
    Run this file directly to test the NLP Module with CSV data
    """
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            # First validate CSV data
            if validate_csv_data():
                run_demo()
        elif sys.argv[1] == "export":
            export_for_module2()
        elif sys.argv[1] == "validate":
            validate_csv_data()
        else:
            print("Usage:")
            print("  python query_preprocessing.py demo      # Run full demonstration")
            print("  python query_preprocessing.py export    # Export for Module 2")
            print("  python query_preprocessing.py validate  # Validate CSV data")
            print("  python query_preprocessing.py           # Run simple test")
    else:
        # Simple test by default
        print("\nRunning simple test with CSV data...")
        
        # Validate data first
        if validate_csv_data():
            print("\n" + "-"*40)
            processor = QueryProcessor("faix_data.csv")
            
            test_query = "What programs does FAIX offer?"
            print(f"\nQuery: '{test_query}'")
            
            result = processor.process_query(test_query)
            
            print("\n" + "-"*40)
            print("Results:")
            print(f"  Language: {result['language']['name']}")
            print(f"  Intent: {result['intent']['category']} ({result['intent']['confidence']:.0%} confidence)")
            print(f"  Intent Method: {result['intent'].get('method', 'keyword')}")
            print(f"  Keywords: {result['keywords']}")
            print(f"  CSV matches: {len(result['faix_matches'])}")
            
            if result['faix_matches']:
                print("\nTop match from CSV:")
                print(f"  Q: {result['faix_matches'][0]['question']}")
                print(f"  A: {result['faix_matches'][0]['answer'][:100]}...")
                print(f"  Category: {result['faix_matches'][0]['category']}")
                print(f"  Match Score: {result['faix_matches'][0]['match_score']:.1f}")
                print(f"  Method: {result['faix_matches'][0].get('method', 'keyword')}")
            print("-"*40)

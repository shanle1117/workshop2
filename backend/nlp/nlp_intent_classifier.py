"""
Intent classification module using transformer models (DistilBERT/RoBERTa).
Enhances intent detection with pre-trained transformer models.
Now supports dynamic configuration loading from JSON files.
"""
import os
import json
import logging
from typing import Dict, Tuple, List, Optional
import re
from pathlib import Path

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.getLogger("faix_chatbot").warning(
        "transformers not available. Install with: pip install transformers torch"
    )


class IntentClassifier:
    """
    Intent classification using transformer models.
    Uses zero-shot classification or fine-tuned models for intent detection.
    Now supports dynamic configuration loading.
    """
    
    def __init__(
        self, 
        model_name: str = None, 
        use_zero_shot: bool = None,
        config_path: str = None
    ):
        """
        Initialize intent classifier with dynamic configuration.
        
        Args:
            model_name: Name of the transformer model to use (overrides config)
            use_zero_shot: Whether to use zero-shot classification (overrides config)
            config_path: Path to JSON configuration file (default: data/intent_config.json)
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Set intent categories and descriptions from config
        self.intent_categories = self.config.get('intent_categories', [])
        self.intent_descriptions = self.config.get('intent_descriptions', {})
        self.keyword_patterns = self.config.get('keyword_patterns', {})
        
        # Model configuration
        model_config = self.config.get('model_config', {})
        self.model_name = model_name or model_config.get('default_model', 'facebook/bart-large-mnli')
        self.use_zero_shot = use_zero_shot if use_zero_shot is not None else model_config.get('use_zero_shot', True)
        self.confidence_threshold = model_config.get('confidence_threshold', 0.3)
        
        # Initialize model components
        self.model = None
        self.tokenizer = None
        self.classifier = None
        self.device = 'cuda' if TRANSFORMERS_AVAILABLE and torch.cuda.is_available() else 'cpu'
        self.logger = logging.getLogger("faix_chatbot")
        
        if TRANSFORMERS_AVAILABLE:
            try:
                if self.use_zero_shot:
                    # Silent loading - reduce startup noise
                    self.classifier = pipeline(
                        "zero-shot-classification",
                        model=self.model_name,
                        device=0 if self.device == 'cuda' else -1
                    )
                    self.logger.debug(f"Intent classifier ready on {self.device}")
                else:
                    # Silent loading - reduce startup noise
                    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                    self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
                    self.model.to(self.device)
                    self.model.eval()
                    self.logger.debug(f"Intent classifier ready on {self.device}")
            except Exception as e:
                self.logger.warning(f"Could not load transformer model: {e}")
                self.classifier = None
                self.model = None
        else:
            self.logger.warning("transformers not installed. Intent classification will use fallback method.")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """Load configuration from JSON file"""
        if config_path is None:
            # Default to data/intent_config.json relative to project root
            # Go up from backend/nlp/ to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / 'data' / 'intent_config.json'
        else:
            config_path = Path(config_path)
        
        # If config file doesn't exist, use defaults
        if not config_path.exists():
            logging.getLogger("faix_chatbot").warning(
                f"Intent config file not found at {config_path}. Using default configuration."
            )
            return self._get_default_config()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # Silent loading - reduce startup noise
            logging.getLogger("faix_chatbot").debug(
                f"Intent config loaded from {config_path.name}"
            )
            return config
        except Exception as e:
            logging.getLogger("faix_chatbot").warning(
                f"Could not load intent config file: {e}. Using default configuration."
            )
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Return default configuration if config file is not available"""
        return {
            'intent_categories': [
                'program_info',
                'admission',
                'fees',
                'career',
                'about_faix',
                'staff_contact',
                'facility_info',
                'academic_resources',
                'research',
                'course_info',
                'registration',
                'academic_schedule',
                'greeting',
                'farewell',
            ],
            'intent_descriptions': {
                'program_info': 'Questions about FAIX programmes - BCSAI, BCSCS, Master degrees, undergraduate and postgraduate programs',
                'admission': 'Questions about admission requirements, entry criteria, CGPA, MUET, international students',
                'fees': 'Questions about tuition fees, payment schedules, fee structure, scholarships',
                'career': 'Questions about career opportunities, job prospects, employment after graduation',
                'about_faix': 'Questions about FAIX faculty info, history, vision, mission, objectives, dean, departments',
                'staff_contact': 'Questions about contacting staff members, faculty, professors, email, phone',
                'facility_info': 'Questions about campus facilities, laboratories, room booking, buildings',
                'academic_resources': 'Questions about academic handbook, uLearn portal, timetable, forms, certifications',
                'research': 'Questions about research areas, AI, cybersecurity, data science, machine learning projects',
                'course_info': 'Questions about specific courses, subjects, modules, curriculum, class content',
                'registration': 'Questions about course registration, enrollment, add/drop subjects',
                'academic_schedule': 'Questions about academic calendar, semester dates, class schedules, timetable',
                'greeting': 'Greetings like hello, hi, hey, good morning',
                'farewell': 'Farewells like goodbye, bye, thanks, thank you',
            },
            'keyword_patterns': {
                'program_info': ['program', 'programme', 'degree', 'bachelor', 'master', 'BCSAI', 'BCSCS', 'MCSSS', 'MTDSA', 'undergraduate', 'postgraduate', 'offer', 'duration', 'computer science', 'artificial intelligence', 'cyber security', 'data science'],
                'admission': ['admission', 'apply', 'application', 'entry', 'requirements', 'criteria', 'CGPA', 'MUET', 'CEFR', 'SPM', 'STPM', 'eligibility', 'international student', 'prerequisite'],
                'fees': ['fee', 'fees', 'tuition', 'cost', 'payment', 'price', 'scholarship', 'financial', 'how much', 'yuran', 'bayaran'],
                'career': ['career', 'job', 'employment', 'work', 'opportunity', 'graduate', 'profession', 'salary', 'industry', 'knowledge engineer', 'developer', 'analyst'],
                'about_faix': ['about', 'FAIX', 'faculty', 'history', 'established', 'vision', 'mission', 'objective', 'UTeM', 'dean', 'department', '2024', 'highlight'],
                'staff_contact': ['contact', 'email', 'phone', 'number', 'professor', 'lecturer', 'staff', 'faculty', 'dean', 'coordinator'],
                'facility_info': ['lab', 'laboratory', 'facility', 'equipment', 'room', 'building', 'campus', 'booking', 'research center'],
                'academic_resources': ['handbook', 'academic handbook', 'ulearn', 'portal', 'timetable', 'forms', 'certification', 'education fund', 'resources'],
                'research': ['research', 'project', 'focus area', 'thesis', 'dissertation', 'publication', 'AI applications', 'machine learning', 'digital forensics'],
                'course_info': ['course', 'subject', 'module', 'curriculum', 'class', 'lecture', 'coursework', 'practical'],
                'registration': ['register', 'enroll', 'enrollment', 'sign up', 'deadline', 'add subject', 'drop subject'],
                'academic_schedule': ['schedule', 'timetable', 'calendar', 'when', 'time', 'date', 'semester', 'academic year'],
                'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'hai', 'helo'],
                'farewell': ['bye', 'goodbye', 'thanks', 'thank you', 'see you', 'terima kasih'],
            },
            'model_config': {
                'default_model': 'facebook/bart-large-mnli',
                'use_zero_shot': True,
                'confidence_threshold': 0.3
            }
        }
    
    def reload_config(self, config_path: str = None):
        """Reload configuration from file and update classifier"""
        print("Reloading configuration...")
        self.config = self._load_config(config_path)
        self.intent_categories = self.config.get('intent_categories', [])
        self.intent_descriptions = self.config.get('intent_descriptions', {})
        self.keyword_patterns = self.config.get('keyword_patterns', {})
        
        model_config = self.config.get('model_config', {})
        self.confidence_threshold = model_config.get('confidence_threshold', 0.3)
        print("✓ Configuration reloaded successfully")
    
    def update_intents(self, intents: Dict[str, str], descriptions: Dict[str, str] = None):
        """
        Dynamically update intent categories and descriptions at runtime.
        
        Args:
            intents: Dictionary mapping intent names to their descriptions
            descriptions: Optional separate descriptions dictionary
        """
        if descriptions:
            self.intent_descriptions.update(descriptions)
        else:
            # If intents dict contains descriptions, use them
            self.intent_descriptions.update(intents)
        
        # Update categories list
        new_categories = list(intents.keys()) if isinstance(intents, dict) else intents
        self.intent_categories = list(set(self.intent_categories + new_categories))
        print(f"✓ Updated intents: {new_categories}")
    
    def classify(self, text: str, top_k: int = 3) -> Tuple[str, float, Dict[str, float]]:
        """
        Classify intent from text.
        
        Args:
            text: Input text to classify
            top_k: Number of top intents to return
            
        Returns:
            Tuple of (best_intent, confidence, all_scores_dict)
        """
        if not text or not text.strip():
            return 'about_faix', 0.0, {'about_faix': 0.0}
        
        # Clean text
        text = self._preprocess(text)
        
        if self.use_zero_shot and self.classifier:
            return self._classify_zero_shot(text, top_k)
        elif self.model and self.tokenizer:
            return self._classify_fine_tuned(text, top_k)
        else:
            # Fallback to keyword-based classification
            return self._classify_keyword_based(text)
    
    def _classify_zero_shot(self, text: str, top_k: int) -> Tuple[str, float, Dict[str, float]]:
        """Classify using zero-shot classification"""
        candidate_labels = list(self.intent_descriptions.keys())
        candidate_labels_descriptions = [
            self.intent_descriptions[label] for label in candidate_labels
        ]
        
        try:
            result = self.classifier(text, candidate_labels_descriptions)
            
            # Map back to intent labels
            scores = {}
            for label, score in zip(result['labels'], result['scores']):
                # Find matching intent category
                for intent in candidate_labels:
                    if self.intent_descriptions[intent] == label:
                        scores[intent] = score
                        break
            
            # Get best intent
            best_intent = max(scores.items(), key=lambda x: x[1])
            
            return best_intent[0], float(best_intent[1]), scores
            
        except Exception as e:
            print(f"Error in zero-shot classification: {e}")
            return self._classify_keyword_based(text)
    
    def _classify_fine_tuned(self, text: str, top_k: int) -> Tuple[str, float, Dict[str, float]]:
        """Classify using fine-tuned model"""
        try:
            inputs = self.tokenizer(
                text,
                return_tensors='pt',
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)[0]
            
            # Map to intent categories (assuming model outputs match intent_categories order)
            scores = {}
            for i, intent in enumerate(self.intent_categories):
                if i < len(probabilities):
                    scores[intent] = float(probabilities[i])
            
            # Get best intent
            best_intent = max(scores.items(), key=lambda x: x[1])
            
            return best_intent[0], float(best_intent[1]), scores
            
        except Exception as e:
            print(f"Error in fine-tuned classification: {e}")
            return self._classify_keyword_based(text)
    
    def _classify_keyword_based(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """Fallback keyword-based classification using dynamic patterns"""
        text_lower = text.lower()
        
        scores = {}
        for intent, keywords in self.keyword_patterns.items():
            score = sum(2 if keyword in text_lower else 0 for keyword in keywords)
            scores[intent] = min(score / 10.0, 1.0)  # Normalize to 0-1
        
        # Add about_faix as fallback if no scores
        if not scores or all(s == 0 for s in scores.values()):
            scores['about_faix'] = 0.1
        
        # Get best intent
        best_intent = max(scores.items(), key=lambda x: x[1])
        
        # If confidence is too low, return about_faix
        if best_intent[1] < 0.2:
            return 'about_faix', 0.2, scores
        
        return best_intent[0], float(best_intent[1]), scores
    
    def _preprocess(self, text: str) -> str:
        """Preprocess text for classification"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def is_available(self) -> bool:
        """Check if intent classifier is available"""
        return (self.classifier is not None) or (self.model is not None)
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return {
            'intent_categories': self.intent_categories,
            'intent_descriptions': self.intent_descriptions,
            'keyword_patterns': self.keyword_patterns,
            'model_name': self.model_name,
            'use_zero_shot': self.use_zero_shot,
            'confidence_threshold': self.confidence_threshold
        }


# Global instance registry (supports multiple instances)
_intent_classifier_instances: Dict[str, IntentClassifier] = {}


def get_intent_classifier(
    instance_id: str = 'default',
    model_name: str = None,
    use_zero_shot: bool = None,
    config_path: str = None,
    force_reload: bool = False
) -> IntentClassifier:
    """
    Get or create intent classifier instance (supports multiple instances).
    
    Args:
        instance_id: Unique identifier for the classifier instance (default: 'default')
        model_name: Name of the transformer model to use (overrides config)
        use_zero_shot: Whether to use zero-shot classification (overrides config)
        config_path: Path to JSON configuration file
        force_reload: Force reload even if instance exists
        
    Returns:
        IntentClassifier instance
    """
    global _intent_classifier_instances
    
    if force_reload or instance_id not in _intent_classifier_instances:
        _intent_classifier_instances[instance_id] = IntentClassifier(
            model_name=model_name,
            use_zero_shot=use_zero_shot,
            config_path=config_path
        )
    
    return _intent_classifier_instances[instance_id]


def reload_classifier(instance_id: str = 'default', config_path: str = None):
    """Reload configuration for a specific classifier instance"""
    global _intent_classifier_instances
    if instance_id in _intent_classifier_instances:
        _intent_classifier_instances[instance_id].reload_config(config_path)
    else:
        print(f"Warning: Instance '{instance_id}' not found. Creating new instance.")
        get_intent_classifier(instance_id=instance_id, config_path=config_path)
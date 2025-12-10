"""
Intent classification module using transformer models (DistilBERT/RoBERTa).
Enhances intent detection with pre-trained transformer models.
"""
import os
from typing import Dict, Tuple, List, Optional
import re

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers not available. Install with: pip install transformers torch")


class IntentClassifier:
    """
    Intent classification using transformer models.
    Uses zero-shot classification or fine-tuned models for intent detection.
    """
    
    # Intent categories mapping
    INTENT_CATEGORIES = [
        'course_info',
        'registration',
        'academic_schedule',
        'staff_contact',
        'facility_info',
        'program_info',
        'general_query',
    ]
    
    # Intent descriptions for zero-shot classification
    INTENT_DESCRIPTIONS = {
        'course_info': 'Questions about specific courses, course content, course requirements, or course details',
        'registration': 'Questions about course registration, enrollment, application process, or registration deadlines',
        'academic_schedule': 'Questions about academic calendar, semester dates, class schedules, or timetable',
        'staff_contact': 'Questions about contacting staff members, faculty, professors, or getting contact information',
        'facility_info': 'Questions about campus facilities, laboratories, buildings, or equipment',
        'program_info': 'Questions about academic programs, degrees, requirements, or program details',
        'general_query': 'General questions, greetings, or unclear queries that don\'t fit other categories',
    }
    
    def __init__(self, model_name: str = 'distilbert-base-uncased', use_zero_shot: bool = True):
        """
        Initialize intent classifier.
        
        Args:
            model_name: Name of the transformer model to use
            use_zero_shot: Whether to use zero-shot classification (default: True)
                          If False, expects a fine-tuned model
        """
        self.model = None
        self.tokenizer = None
        self.classifier = None
        self.model_name = model_name
        self.use_zero_shot = use_zero_shot
        self.device = 'cuda' if torch.cuda.is_available() and TRANSFORMERS_AVAILABLE else 'cpu'
        
        if TRANSFORMERS_AVAILABLE:
            try:
                if use_zero_shot:
                    print(f"Loading zero-shot classifier (model: {model_name})...")
                    self.classifier = pipeline(
                        "zero-shot-classification",
                        model=model_name,
                        device=0 if self.device == 'cuda' else -1
                    )
                    print("✓ Zero-shot intent classifier loaded successfully")
                else:
                    print(f"Loading fine-tuned model: {model_name}...")
                    self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                    self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
                    self.model.to(self.device)
                    self.model.eval()
                    print("✓ Fine-tuned intent classifier loaded successfully")
            except Exception as e:
                print(f"Warning: Could not load transformer model: {e}")
                self.classifier = None
                self.model = None
        else:
            print("Warning: transformers not installed. Intent classification will use fallback method.")
    
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
            return 'general_query', 0.0, {'general_query': 0.0}
        
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
        candidate_labels = list(self.INTENT_DESCRIPTIONS.keys())
        candidate_labels_descriptions = [
            self.INTENT_DESCRIPTIONS[label] for label in candidate_labels
        ]
        
        try:
            result = self.classifier(text, candidate_labels_descriptions)
            
            # Map back to intent labels
            scores = {}
            for label, score in zip(result['labels'], result['scores']):
                # Find matching intent category
                for intent in candidate_labels:
                    if self.INTENT_DESCRIPTIONS[intent] == label:
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
            
            # Map to intent categories (assuming model outputs match INTENT_CATEGORIES order)
            scores = {}
            for i, intent in enumerate(self.INTENT_CATEGORIES):
                if i < len(probabilities):
                    scores[intent] = float(probabilities[i])
            
            # Get best intent
            best_intent = max(scores.items(), key=lambda x: x[1])
            
            return best_intent[0], float(best_intent[1]), scores
            
        except Exception as e:
            print(f"Error in fine-tuned classification: {e}")
            return self._classify_keyword_based(text)
    
    def _classify_keyword_based(self, text: str) -> Tuple[str, float, Dict[str, float]]:
        """Fallback keyword-based classification"""
        text_lower = text.lower()
        
        # Keyword patterns (from query_preprocessing.py)
        intent_patterns = {
            'course_info': ['course', 'subject', 'module', 'curriculum', 'class', 'lecture'],
            'registration': ['register', 'enroll', 'enrollment', 'admission', 'apply', 'sign up', 'deadline'],
            'academic_schedule': ['schedule', 'timetable', 'calendar', 'when', 'time', 'date', 'semester'],
            'staff_contact': ['contact', 'email', 'phone', 'number', 'professor', 'lecturer', 'staff', 'faculty'],
            'facility_info': ['lab', 'laboratory', 'facility', 'equipment', 'room', 'building', 'campus'],
            'program_info': ['program', 'degree', 'bachelor', 'master', 'requirement', 'eligibility', 'duration'],
        }
        
        scores = {}
        for intent, keywords in intent_patterns.items():
            score = sum(2 if keyword in text_lower else 0 for keyword in keywords)
            scores[intent] = min(score / 10.0, 1.0)  # Normalize to 0-1
        
        # Add general_query
        scores['general_query'] = 0.1
        
        # Get best intent
        best_intent = max(scores.items(), key=lambda x: x[1])
        
        # If confidence is too low, return general_query
        if best_intent[1] < 0.2:
            return 'general_query', 0.2, scores
        
        return best_intent[0], float(best_intent[1]), scores
    
    def _preprocess(self, text: str) -> str:
        """Preprocess text for classification"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        return text
    
    def is_available(self) -> bool:
        """Check if intent classifier is available"""
        return (self.classifier is not None) or (self.model is not None)


# Global instance
_intent_classifier_instance = None


def get_intent_classifier(
    model_name: str = 'distilbert-base-uncased',
    use_zero_shot: bool = True
) -> IntentClassifier:
    """Get or create global intent classifier instance"""
    global _intent_classifier_instance
    if _intent_classifier_instance is None:
        _intent_classifier_instance = IntentClassifier(model_name, use_zero_shot)
    return _intent_classifier_instance


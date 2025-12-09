import re
import json
from typing import Dict, List, Any

class QueryProcessor:
    """
    Module 1: Query Processing
    Processes user input to identify the main intention of the question
    """

    def __init__(self):
        print("Initializing Query Processor...")
        
        # NLP preprocessing
        self.stop_words = set([
            'a', 'an', 'the', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
            'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
            'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom',
            'where', 'when', 'why', 'how', 'please', 'thank', 'thanks', 'hello'
        ])
        
        # Intent patterns
        self.intent_patterns = {
            'course_info': ['course', 'subject', 'module', 'kokurikulum', 'curriculum', 'class', 'lecture'],
            'registration': ['register', 'enroll', 'enrollment', 'admission', 'apply', 'sign up', 'deadline'],
            'academic_schedule': ['schedule', 'timetable', 'calendar', 'when', 'time', 'date', 'semester'],
            'staff_contact': ['contact', 'email', 'phone', 'number', 'professor', 'lecturer', 'staff', 'faculty'],
            'facility_info': ['lab', 'laboratory', 'facility', 'equipment', 'room', 'building', 'campus'],
            'program_info': ['program', 'degree', 'bachelor', 'master', 'requirement', 'eligibility', 'duration']
        }
        
        print("Query Processor ready!")

    def preprocess_text(self, text: str) -> str:
        """Clean and normalize the input text"""
        
        # Convert to lowercase
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s?.,]', '', text)
        
        return text
    
    def tokenize_text(self, text: str) -> List[str]:
        """Split text into tokens and remove stop words"""
        
        # Simple tokenization
        tokens = text.split()
        
        # Remove stop words
        tokens = [token for token in tokens if token not in self.stop_words]
        
        return tokens
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract important entities from the text"""
        entities = {}
    
        # Course codes
        course_codes = re.findall(r'\b[B][A][XIZTS]{2,4}\b', text, re.IGNORECASE)
        if course_codes:
            entities['course_codes'] = [code.upper() for code in course_codes]
        
        # Catch course codes with numbers (like BAXI3923, BITZ2024)
        course_codes_with_numbers = re.findall(r'\b[B][A][XIZTS]{2,4}\s?\d{3,4}\b', text, re.IGNORECASE)
        if course_codes_with_numbers:
            if 'course_codes' not in entities:
                entities['course_codes'] = []
            entities['course_codes'].extend([code.upper() for code in course_codes_with_numbers])
        
        # Email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if emails:
            entities['emails'] = emails
        
        # Dates
        dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}', text)
        if dates:
            entities['dates'] = dates
        
        # Staff names (simple pattern)
        staff_names = re.findall(r'(professor|dr|mr|mrs|ms)\.?\s+[A-Z][a-z]+', text, re.IGNORECASE)
        if staff_names:
            entities['staff_names'] = staff_names
    
        # Important keywords (words longer than 3 characters)
        tokens = self.tokenize_text(text)
        important_words = [token for token in tokens if len(token) > 3]
        if important_words:
            entities['keywords'] = important_words
    
        return entities
    
    def detect_intent(self, text: str) -> tuple:
        """Detect the main intent of the user query"""
        
        tokens = self.tokenize_text(text)
        
        intent_scores = {}
        
        # Score each intent based on keyword matches
        for intent, keywords in self.intent_patterns.items():
            score = 0
            for keyword in keywords:
                if keyword in tokens:
                    score += 2  # Higher weight for exact matches
            intent_scores[intent] = score
        
        # Find intent with highest score
        if intent_scores:
            best_intent = max(intent_scores.items(), key=lambda x: x[1])
            confidence = min(best_intent[1] / 10, 1.0)  # Normalize to 0-1
            
            # If confidence is too low, return general query
            if confidence < 0.2:
                return "general_query", confidence
            else:
                return best_intent[0], confidence
        
        return "general_query", 0.0
    
    def process_query(self, user_input: str) -> Dict[str, Any]:
        """
        Main method: Process user query and return structured data
        This output will be passed to other modules
        """
        
        print(f"Processing query: '{user_input}'")
        
        # Preprocess text
        cleaned_text = self.preprocess_text(user_input)
        
        # Tokenize
        tokens = self.tokenize_text(cleaned_text)
        
        # Detect intent
        intent, confidence = self.detect_intent(cleaned_text)
        
        # Extract entities
        entities = self.extract_entities(user_input)
        
        # Prepare output for other modules
        processed_data = {
            'original_query': user_input,
            'cleaned_query': cleaned_text,
            'tokens': tokens,
            'detected_intent': intent,
            'confidence_score': round(confidence, 2),
            'extracted_entities': entities,
            'requires_clarification': confidence < 0.3,
            'module': 'query_processing'
        }
        
        print(f"Query processing complete!")
        return processed_data
    
    def format_for_knowledge_base(self, processed_data: Dict) -> Dict:
        """Format data specifically for Module 2 (Knowledge Base)"""
        
        return {
            'search_intent': processed_data['detected_intent'],
            'search_terms': processed_data['tokens'],
            'entities': processed_data['extracted_entities'],
            'confidence': processed_data['confidence_score'],
            'original_query': processed_data['original_query']
        }
    
    def format_for_conversation_manager(self, processed_data: Dict) -> Dict:
        """Format data specifically for Module 3 (Conversation Management)"""
        return {
            'user_query': processed_data['original_query'],
            'detected_intent': processed_data['detected_intent'],
            'confidence_level': processed_data['confidence_score'],
            'needs_clarification': processed_data['requires_clarification'],
            'missing_info': self._identify_missing_info(processed_data),
            'entities': processed_data['extracted_entities']
        }
    
    def _identify_missing_info(self, processed_data: Dict) -> List[str]:
        """Identify what information might be missing for better responses"""
        
        missing = []
        intent = processed_data['detected_intent']
        entities = processed_data['extracted_entities']
        
        if intent == 'course_info' and 'course_codes' not in entities:
            missing.append('specific course code or name')
        elif intent == 'staff_contact' and 'staff_names' not in entities:
            missing.append('staff member name')
        elif intent == 'registration' and 'dates' not in entities:
            missing.append('specific date or semester')
            
        return missing

    def display_test_queries(self):
        """Display comprehensive test queries for Module 1"""
        
        test_queries = [
            # Course Information Queries
            {
                "query": "What are the requirements for BAXI courses?",
                "description": "Course info with specific course code"
            },
            {
                "query": "Tell me about the BITZ program curriculum",
                "description": "Program curriculum inquiry"
            },
            {
                "query": "When does BAXZ 2024 registration start?",
                "description": "Registration with course code and year"
            },
            
            # Staff Contact Queries
            {
                "query": "What is Professor Rehan email address?",
                "description": "Staff email inquiry"
            },
            {
                "query": "How can I contact Dr. Elle from FAIX?",
                "description": "Staff contact request"
            },
            
            # Registration Queries
            {
                "query": "When is the deadline for course registration?",
                "description": "Registration deadline inquiry"
            },
            {
                "query": "How do I apply for the BAIS program?",
                "description": "Program application process"
            },
            
            # Schedule Queries
            {
                "query": "What is the academic calendar for next semester?",
                "description": "Academic schedule inquiry"
            },
            {
                "query": "When are the BACS classes scheduled?",
                "description": "Class schedule with course code"
            },
            
            # Facility Queries
            {
                "query": "What lab facilities are available in FAIX?",
                "description": "Facility information request"
            },
            {
                "query": "Where is the AI laboratory located?",
                "description": "Specific facility location"
            },
            
            # General Queries
            {
                "query": "Hello, can you help me with FAIX information?",
                "description": "General help request"
            },
            {
                "query": "What programs does the faculty offer?",
                "description": "General program inquiry"
            }
        ]
        
        print("\n" + "="*70)
        print("MODULE 1 - TEST QUERIES DEMONSTRATION")
        print("="*70)
        
        for i, test_case in enumerate(test_queries, 1):
            print(f"\n{'─'*70}")
            print(f"TEST {i:2d}: {test_case['query']}")
            print(f"Description: {test_case['description']}")
            print(f"{'─'*70}")
            
            # Process the query
            result = self.process_query(test_case['query'])
            
            # Display results
            print(f"\nCleaned Query: {result['cleaned_query']}")
            print(f"Detected Intent: {result['detected_intent']}")
            print(f"Confidence Score: {result['confidence_score']}")
            print(f"Requires Clarification: {result['requires_clarification']}")
            print(f"Extracted Entities: {json.dumps(result['extracted_entities'], indent=2)}")
            
            # Show formatted data for other modules
            kb_data = self.format_for_knowledge_base(result)
            conv_data = self.format_for_conversation_manager(result)
            
            print(f"For Knowledge Base: {len(kb_data['search_terms'])} search terms")
            print(f"For Conversation Manager: Needs clarification = {conv_data['needs_clarification']}")
        
        print(f"\n{'='*70}")
        print("MODULE 1 TESTING COMPLETE")
        print(f"{'='*70}")

    def quick_test(self, query: str):
        """Quick test for a single query"""
        print(f"\nQUICK TEST: '{query}'")
        print(f"{'─'*50}")
        
        result = self.process_query(query)
        
        print(f"Intent: {result['detected_intent']}")
        print(f"Confidence: {result['confidence_score']}")
        print(f"Entities: {result['extracted_entities']}")
        print(f"Clarification Needed: {result['requires_clarification']}")

# Integration function for other modules to use
def create_query_processor():
    """Factory function to create and return QueryProcessor instance"""
    return QueryProcessor()

# Demo function to show how to use the test functions
def demo_module1():
    """Demonstrate Module 1 functionality"""
    processor = QueryProcessor()
    
    print("\n MODULE 1 DEMONSTRATION")
    print("Choose an option:")
    print("1. Test main queries")
    print("2. Test custom query")
    print("3. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == '1':
            processor.display_test_queries()
        elif choice == '2':
            custom_query = input("Enter query: ").strip()
            if custom_query:
                processor.quick_test(custom_query)
            else:
                print("Please enter a valid query.")
        elif choice == '3':
            print("Exiting demo...")
            break
        else:
            print("Invalid choice. Please enter 1, 2, or 3.")

if __name__ == "__main__":
    
    # Run the demo when this file is executed directly
    demo_module1()

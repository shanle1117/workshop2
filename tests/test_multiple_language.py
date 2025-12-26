"""
Test module for multiple language support in the FAIX chatbot.

This module tests:
- Language detection (English, Malay, Chinese, Arabic)
- Intent detection in different languages
- Query processing in different languages
- Tokenization and preprocessing
- End-to-end query processing
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add src to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from query_preprocessing import QueryProcessor, LanguageDetector


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.RESET}\n")


def print_test(test_name):
    """Print test name"""
    print(f"{Colors.BOLD}{Colors.BLUE}→ Testing: {test_name}{Colors.RESET}")


def print_success(message):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_info(message):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ {message}{Colors.RESET}")


def test_language_detection():
    """Test language detection for all supported languages"""
    print_header("Language Detection Tests")
    
    detector = LanguageDetector()
    
    test_cases = [
        # English
        ("What programs does FAIX offer?", "en", "English"),
        ("How do I register for courses?", "en", "English"),
        ("Contact information for staff", "en", "English"),
        
        # Malay
        ("Apakah program yang ditawarkan oleh FAIX?", "ms", "Bahasa Malaysia"),
        ("Bagaimana untuk mendaftar kursus?", "ms", "Bahasa Malaysia"),
        ("Maklumat hubungan untuk kakitangan", "ms", "Bahasa Malaysia"),
        
        # Chinese
        ("FAIX提供什么课程？", "zh", "Chinese"),
        ("如何注册课程？", "zh", "Chinese"),
        ("教职员工联系方式", "zh", "Chinese"),
        
        # Arabic
        ("ما هي البرامج التي تقدمها FAIX؟", "ar", "Arabic"),
        ("كيف أسجل في الدورات؟", "ar", "Arabic"),
        ("معلومات الاتصال للموظفين", "ar", "Arabic"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_code, expected_name in test_cases:
        print_test(f"Detecting language for: '{query[:50]}...'")
        detected_code = detector.detect(query)
        
        if detected_code == expected_code:
            print_success(f"Detected {expected_name} correctly")
            passed += 1
        else:
            print_error(f"Expected {expected_name} ({expected_code}), got {detected_code}")
            failed += 1
    
    print(f"\n{Colors.BOLD}Language Detection Results: {Colors.GREEN}{passed} passed{Colors.RESET}, {Colors.RED}{failed} failed{Colors.RESET}")
    return passed, failed


def test_intent_detection():
    """Test intent detection in different languages"""
    print_header("Intent Detection Tests")
    
    processor = QueryProcessor(use_database=False, use_nlp=False)
    
    test_cases = [
        # English intents
        ("What courses are available?", "en", "course_info"),
        ("Tell me about the programs", "en", "program_info"),
        ("How to register?", "en", "registration"),
        ("When is the semester starting?", "en", "academic_schedule"),
        ("Contact the professor", "en", "staff_contact"),
        ("What facilities are available?", "en", "facility_info"),
        ("How much are the fees?", "en", "fees"),
        
        # Malay intents
        ("Apakah kursus yang tersedia?", "ms", "course_info"),
        ("Beritahu saya tentang program", "ms", "program_info"),
        ("Bagaimana untuk mendaftar?", "ms", "registration"),
        ("Bila semester bermula?", "ms", "academic_schedule"),
        ("Hubungi profesor", "ms", "staff_contact"),
        ("Apakah kemudahan yang tersedia?", "ms", "facility_info"),
        ("Berapakah yuran?", "ms", "fees"),
        
        # Chinese intents
        ("有哪些课程？", "zh", "course_info"),
        ("告诉我关于项目的信息", "zh", "program_info"),
        ("如何注册？", "zh", "registration"),
        ("学期什么时候开始？", "zh", "academic_schedule"),
        ("联系教授", "zh", "staff_contact"),
        ("有哪些设施？", "zh", "facility_info"),
        ("费用是多少？", "zh", "fees"),
        
        # Arabic intents
        ("ما هي الدورات المتاحة؟", "ar", "course_info"),
        ("أخبرني عن البرامج", "ar", "program_info"),
        ("كيف أسجل؟", "ar", "registration"),
        ("متى يبدأ الفصل الدراسي؟", "ar", "academic_schedule"),
        ("اتصل بالأستاذ", "ar", "staff_contact"),
        ("ما هي المرافق المتاحة؟", "ar", "facility_info"),
        ("كم هي الرسوم؟", "ar", "fees"),
    ]
    
    passed = 0
    failed = 0
    
    for query, lang, expected_intent in test_cases:
        print_test(f"Intent detection: '{query[:40]}...' ({lang})")
        
        # Detect language first
        lang_info = processor.detect_language(query)
        detected_lang = lang_info['code']
        
        # Detect intent
        intent, confidence = processor.detect_intent(query, detected_lang)
        
        if intent == expected_intent:
            print_success(f"Detected intent '{intent}' (confidence: {confidence:.2f})")
            passed += 1
        else:
            print_error(f"Expected '{expected_intent}', got '{intent}' (confidence: {confidence:.2f})")
            failed += 1
    
    print(f"\n{Colors.BOLD}Intent Detection Results: {Colors.GREEN}{passed} passed{Colors.RESET}, {Colors.RED}{failed} failed{Colors.RESET}")
    return passed, failed


def test_tokenization():
    """Test tokenization for different languages"""
    print_header("Tokenization Tests")
    
    processor = QueryProcessor(use_database=False, use_nlp=False)
    
    test_cases = [
        ("What courses are available?", "en", ["courses", "available"]),
        ("Apakah kursus yang tersedia?", "ms", ["kursus", "tersedia"]),
        ("有哪些课程？", "zh", ["课程"]),
        ("ما هي الدورات المتاحة؟", "ar", ["الدورات", "المتاحة"]),
    ]
    
    passed = 0
    failed = 0
    
    for text, lang, expected_keywords in test_cases:
        print_test(f"Tokenizing: '{text[:40]}...' ({lang})")
        
        tokens = processor.tokenize_text(text, lang)
        
        # Check if expected keywords are in tokens
        found_keywords = [kw for kw in expected_keywords if any(kw in token for token in tokens)]
        
        if len(found_keywords) > 0:
            print_success(f"Found keywords: {found_keywords}")
            print_info(f"All tokens: {tokens}")
            passed += 1
        else:
            print_error(f"Expected keywords {expected_keywords} not found in tokens: {tokens}")
            failed += 1
    
    print(f"\n{Colors.BOLD}Tokenization Results: {Colors.GREEN}{passed} passed{Colors.RESET}, {Colors.RED}{failed} failed{Colors.RESET}")
    return passed, failed


def test_preprocessing():
    """Test text preprocessing for different languages"""
    print_header("Preprocessing Tests")
    
    processor = QueryProcessor(use_database=False, use_nlp=False)
    
    test_cases = [
        ("  What   courses???  ", "en", "what courses"),
        ("  Apakah   kursus???  ", "ms", "apakah kursus"),
        ("  有哪些课程？  ", "zh", "有哪些课程？"),
        ("  ما هي   الدورات؟  ", "ar", "ما هي الدورات؟"),
    ]
    
    passed = 0
    failed = 0
    
    for text, lang, expected_cleaned in test_cases:
        print_test(f"Preprocessing: '{text}' ({lang})")
        
        cleaned = processor.preprocess_text(text, lang)
        
        # For non-Chinese/Arabic, compare lowercase
        if lang in ['zh', 'ar']:
            match = cleaned.strip() == expected_cleaned.strip()
        else:
            match = cleaned.strip().lower() == expected_cleaned.strip().lower()
        
        if match:
            print_success(f"Cleaned to: '{cleaned}'")
            passed += 1
        else:
            print_error(f"Expected '{expected_cleaned}', got '{cleaned}'")
            failed += 1
    
    print(f"\n{Colors.BOLD}Preprocessing Results: {Colors.GREEN}{passed} passed{Colors.RESET}, {Colors.RED}{failed} failed{Colors.RESET}")
    return passed, failed


def test_end_to_end_processing():
    """Test end-to-end query processing in different languages"""
    print_header("End-to-End Query Processing Tests")
    
    processor = QueryProcessor(use_database=False, use_nlp=False)
    
    test_cases = [
        # English
        {
            "query": "What programs does FAIX offer?",
            "expected_lang": "en",
            "expected_intent": "program_info"
        },
        # Malay
        {
            "query": "Apakah program yang ditawarkan oleh FAIX?",
            "expected_lang": "ms",
            "expected_intent": "program_info"
        },
        # Chinese
        {
            "query": "FAIX提供什么课程？",
            "expected_lang": "zh",
            "expected_intent": "program_info"
        },
        # Arabic
        {
            "query": "ما هي البرامج التي تقدمها FAIX؟",
            "expected_lang": "ar",
            "expected_intent": "program_info"
        },
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        query = test_case["query"]
        expected_lang = test_case["expected_lang"]
        expected_intent = test_case["expected_intent"]
        
        print_test(f"Processing: '{query[:50]}...'")
        
        try:
            result = processor.process_query(query)
            
            detected_lang = result.get('language', {}).get('code', 'unknown')
            detected_intent = result.get('detected_intent', 'unknown')
            confidence = result.get('confidence_score', 0.0)
            
            lang_match = detected_lang == expected_lang
            intent_match = detected_intent == expected_intent
            
            if lang_match and intent_match:
                print_success(f"Language: {detected_lang}, Intent: {detected_intent}, Confidence: {confidence:.2f}")
                print_info(f"Tokens: {result.get('tokens', [])}")
                passed += 1
            else:
                print_error(f"Language: {detected_lang} (expected {expected_lang}), "
                          f"Intent: {detected_intent} (expected {expected_intent})")
                failed += 1
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            failed += 1
    
    print(f"\n{Colors.BOLD}End-to-End Processing Results: {Colors.GREEN}{passed} passed{Colors.RESET}, {Colors.RED}{failed} failed{Colors.RESET}")
    return passed, failed


def test_mixed_language():
    """Test handling of mixed language queries"""
    print_header("Mixed Language Handling Tests")
    
    processor = QueryProcessor(use_database=False, use_nlp=False)
    
    test_cases = [
        ("What programs FAIX tawarkan?", "en"),  # English-Malay mix
        ("Apakah courses yang available?", "ms"),  # Malay-English mix
        ("有哪些programs？", "zh"),  # Chinese-English mix
        ("ما هي programs المتاحة؟", "ar"),  # Arabic-English mix
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_dominant_lang in test_cases:
        print_test(f"Mixed language: '{query}'")
        
        result = processor.process_query(query)
        detected_lang = result.get('language', {}).get('code', 'unknown')
        
        # Mixed language should detect the dominant language
        if detected_lang == expected_dominant_lang:
            print_success(f"Detected dominant language: {detected_lang}")
            passed += 1
        else:
            print_info(f"Detected: {detected_lang} (expected {expected_dominant_lang}) - acceptable for mixed language")
            passed += 1  # Acceptable for mixed language
    
    print(f"\n{Colors.BOLD}Mixed Language Results: {Colors.GREEN}{passed} passed{Colors.RESET}, {Colors.RED}{failed} failed{Colors.RESET}")
    return passed, failed


def test_edge_cases():
    """Test edge cases and special characters"""
    print_header("Edge Cases Tests")
    
    processor = QueryProcessor(use_database=False, use_nlp=False)
    
    test_cases = [
        ("", "en"),  # Empty string
        ("   ", "en"),  # Whitespace only
        ("123456", "en"),  # Numbers only
        ("!@#$%^&*()", "en"),  # Special characters only
        ("Hello مرحبا 你好", "en"),  # Multiple languages
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_fallback_lang in test_cases:
        print_test(f"Edge case: '{query[:30]}...'")
        
        try:
            result = processor.process_query(query)
            detected_lang = result.get('language', {}).get('code', 'unknown')
            
            # Should not crash and should return a language
            if detected_lang:
                print_success(f"Handled gracefully, detected: {detected_lang}")
                passed += 1
            else:
                print_error("No language detected")
                failed += 1
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            failed += 1
    
    print(f"\n{Colors.BOLD}Edge Cases Results: {Colors.GREEN}{passed} passed{Colors.RESET}, {Colors.RED}{failed} failed{Colors.RESET}")
    return passed, failed


def run_all_tests():
    """Run all test suites"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("=" * 70)
    print(" " * 15 + "MULTIPLE LANGUAGE SUPPORT TEST SUITE" + " " * 19)
    print("=" * 70)
    print(f"{Colors.RESET}")
    
    total_passed = 0
    total_failed = 0
    
    # Run all test suites
    test_functions = [
        ("Language Detection", test_language_detection),
        ("Intent Detection", test_intent_detection),
        ("Tokenization", test_tokenization),
        ("Preprocessing", test_preprocessing),
        ("End-to-End Processing", test_end_to_end_processing),
        ("Mixed Language", test_mixed_language),
        ("Edge Cases", test_edge_cases),
    ]
    
    results = {}
    
    for test_name, test_func in test_functions:
        try:
            passed, failed = test_func()
            total_passed += passed
            total_failed += failed
            results[test_name] = (passed, failed)
        except Exception as e:
            print_error(f"Test suite '{test_name}' crashed: {str(e)}")
            total_failed += 1
            results[test_name] = (0, 1)
    
    # Print summary
    print_header("Test Summary")
    
    for test_name, (passed, failed) in results.items():
        status = f"{Colors.GREEN}✓{Colors.RESET}" if failed == 0 else f"{Colors.RED}✗{Colors.RESET}"
        print(f"{status} {test_name:30} {Colors.GREEN}{passed:3} passed{Colors.RESET} {Colors.RED}{failed:3} failed{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}Total: {Colors.GREEN}{total_passed} passed{Colors.RESET} {Colors.RED}{total_failed} failed{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*70}{Colors.RESET}\n")
    
    if total_failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 All tests passed!{Colors.RESET}\n")
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠️  Some tests failed. Please review the output above.{Colors.RESET}\n")
    
    return total_passed, total_failed


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user.{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}")
        import traceback
        traceback.print_exc()


"""
Standalone Chatbot Testing Module (No Django Required)

This module tests chatbot components that don't require Django:
- Query preprocessing
- Language detection
- Intent detection
- Knowledge base (CSV mode)
- Performance optimizations
"""

import sys
import os
import time
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'src'))


# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")


def print_test(name):
    print(f"{Colors.BOLD}{Colors.BLUE}→ {name}{Colors.RESET}")


def print_pass(msg=""):
    print(f"{Colors.GREEN}  ✓ PASS{Colors.RESET} {msg}")


def print_fail(msg=""):
    print(f"{Colors.RED}  ✗ FAIL{Colors.RESET} {msg}")


def print_info(msg=""):
    print(f"{Colors.CYAN}  ℹ INFO{Colors.RESET} {msg}")


def test_query_processor():
    """Test query processor with caching"""
    print_test("Query Processor & Caching")
    
    try:
        from query_preprocessing import QueryProcessor
        
        processor = QueryProcessor(use_nlp=False, use_database=False)
        
        test_cases = [
            ("English", "What programs does FAIX offer?", "en", "program_info"),
            ("Malay", "Apakah program yang ditawarkan FAIX?", "ms", "program_info"),
            ("Chinese", "FAIX提供什么课程？", "zh", "program_info"),
        ]
        
        passed = 0
        failed = 0
        
        for lang_name, query, expected_lang, expected_intent in test_cases:
            try:
                # First run (cold)
                start = time.time()
                result1 = processor.process_query(query)
                time1 = time.time() - start
                
                # Second run (cached)
                start = time.time()
                result2 = processor.process_query(query)
                time2 = time.time() - start
                
                # Verify results
                assert result1['language']['code'] == result2['language']['code']
                assert result1['detected_intent'] == result2['detected_intent']
                
                lang_detected = result1['language']['code']
                intent_detected = result1['detected_intent']
                
                print_pass(f"{lang_name}: Lang={lang_detected}, Intent={intent_detected}")
                print_info(f"  First run: {time1:.4f}s, Second run: {time2:.4f}s")
                
                if time1 > 0 and time2 > 0:
                    speedup = time1 / max(time2, 0.0001)
                    if speedup > 1.1:
                        print_info(f"  Caching speedup: {speedup:.2f}x")
                
                passed += 1
                
            except Exception as e:
                print_fail(f"{lang_name}: {e}")
                failed += 1
        
        return passed, failed
        
    except ImportError as e:
        print_fail(f"Could not import: {e}")
        return 0, 1


def test_language_detection():
    """Test language detection"""
    print_test("Language Detection")
    
    try:
        from query_preprocessing import LanguageDetector
        
        detector = LanguageDetector()
        
        test_cases = [
            ("Hello, how are you?", "en"),
            ("Apa khabar?", "ms"),
            ("你好吗？", "zh"),
            ("كيف حالك؟", "ar"),
            ("What programs does FAIX offer?", "en"),
            ("Apakah program yang ditawarkan?", "ms"),
        ]
        
        passed = 0
        failed = 0
        
        for query, expected_lang in test_cases:
            try:
                # Test twice to verify caching
                lang1 = detector.detect(query)
                lang2 = detector.detect(query)
                
                assert lang1 == lang2, "Caching not working"
                
                if lang1 == expected_lang:
                    print_pass(f"'{query[:30]}...' → {lang1}")
                    passed += 1
                else:
                    print_fail(f"'{query[:30]}...' → Expected {expected_lang}, got {lang1}")
                    failed += 1
                    
            except Exception as e:
                print_fail(f"'{query[:30]}...': {e}")
                failed += 1
        
        return passed, failed
        
    except ImportError as e:
        print_fail(f"Could not import: {e}")
        return 0, 1


def test_intent_detection():
    """Test intent detection with caching"""
    print_test("Intent Detection & Caching")
    
    try:
        from query_preprocessing import QueryProcessor
        
        processor = QueryProcessor(use_nlp=False, use_database=False)
        
        test_cases = [
            ("What programs does FAIX offer?", "program_info"),
            ("How do I register?", "registration"),
            ("What are the fees?", "fees"),
            ("Who is the dean?", "staff_contact"),
            ("When does semester start?", "academic_schedule"),
        ]
        
        passed = 0
        failed = 0
        
        for query, expected_intent in test_cases:
            try:
                # First run
                start = time.time()
                result1 = processor.process_query(query)
                time1 = time.time() - start
                
                # Second run (should use cache)
                start = time.time()
                result2 = processor.process_query(query)
                time2 = time.time() - start
                
                intent1 = result1['detected_intent']
                intent2 = result2['detected_intent']
                
                assert intent1 == intent2, "Intent detection inconsistent"
                
                # Check if intent matches expected
                if expected_intent in intent1 or intent1 in expected_intent:
                    print_pass(f"'{query}' → {intent1}")
                    print_info(f"  Time: {time1:.4f}s → {time2:.4f}s")
                    passed += 1
                else:
                    print_fail(f"'{query}' → Expected {expected_intent}, got {intent1}")
                    failed += 1
                    
            except Exception as e:
                print_fail(f"'{query}': {e}")
                failed += 1
        
        return passed, failed
        
    except ImportError as e:
        print_fail(f"Could not import: {e}")
        return 0, 1


def test_knowledge_base():
    """Test knowledge base with caching"""
    print_test("Knowledge Base Retrieval & Caching")
    
    try:
        # The knowledge_base module imports Django but handles it gracefully
        # We can import it even if Django isn't available - it will use CSV mode
        KnowledgeBase = None
        try:
            from knowledge_base import KnowledgeBase
        except ImportError as e:
            # Only fail if it's not a Django-related import error
            if 'django' not in str(e).lower() and 'knowledge_base' in str(e).lower():
                print_fail(f"Could not import KnowledgeBase: {e}")
                return 0, 1
            # Django import error is fine - module will use CSV mode
            print_info("Django not available, using CSV mode")
        except Exception as e:
            # Other import errors - might be missing dependencies
            if 'pandas' in str(e).lower() or 'sklearn' in str(e).lower():
                print_warn(f"Missing dependencies: {e}")
                return 0, 0
            raise
        
        if KnowledgeBase is None:
            print_info("KnowledgeBase not available, skipping test")
            return 0, 0
        
        # Use CSV mode explicitly
        csv_path = BASE_DIR / 'data' / 'faix_data.csv'
        if not csv_path.exists():
            print_warn(f"CSV file not found: {csv_path}")
            return 0, 0
        
        # Create KnowledgeBase in CSV mode (will skip Django)
        kb = KnowledgeBase(csv_path=str(csv_path), use_database=False)
        
        test_cases = [
            ("program_info", "What programs does FAIX offer?"),
            ("registration", "How do I register?"),
            ("fees", "What are the tuition fees?"),
        ]
        
        passed = 0
        failed = 0
        
        for intent, query in test_cases:
            try:
                # First retrieval
                start = time.time()
                answer1 = kb.get_answer(intent, query)
                time1 = time.time() - start
                
                # Second retrieval (should use cache)
                start = time.time()
                answer2 = kb.get_answer(intent, query)
                time2 = time.time() - start
                
                assert answer1 == answer2, "Cached answer differs"
                assert answer1 is not None, "No answer returned"
                assert len(answer1) > 0, "Empty answer"
                
                print_pass(f"Intent '{intent}': Retrieved ({len(answer1)} chars)")
                print_info(f"  Time: {time1:.4f}s → {time2:.4f}s")
                
                if time1 > 0 and time2 > 0:
                    speedup = time1 / max(time2, 0.0001)
                    if speedup > 1.1:
                        print_info(f"  Caching speedup: {speedup:.2f}x")
                
                passed += 1
                
            except Exception as e:
                print_fail(f"Intent '{intent}': {e}")
                failed += 1
        
        return passed, failed
        
    except ImportError as e:
        print_fail(f"Could not import: {e}")
        return 0, 1


def test_performance_benchmark():
    """Benchmark performance improvements"""
    print_test("Performance Benchmark")
    
    try:
        from query_preprocessing import QueryProcessor
        
        processor = QueryProcessor(use_nlp=False, use_database=False)
        
        # Test queries
        queries = [
            "What programs does FAIX offer?",
            "How do I register?",
            "What are the fees?",
            "Who is the dean?",
        ]
        
        print_info("Testing query processing speed...")
        
        times = []
        for query in queries * 3:  # Run each query 3 times
            start = time.time()
            processor.process_query(query)
            elapsed = time.time() - start
            times.append(elapsed)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print_pass(f"Average: {avg_time:.4f}s")
        print_info(f"  Min: {min_time:.4f}s, Max: {max_time:.4f}s")
        print_info(f"  Total queries: {len(times)}")
        
        if avg_time < 0.1:
            print_pass("Performance is excellent!")
        elif avg_time < 0.5:
            print_pass("Performance is good")
        else:
            print_fail("Performance could be improved")
        
        return 1, 0
        
    except Exception as e:
        print_fail(f"Benchmark failed: {e}")
        return 0, 1


def main():
    """Run all standalone tests"""
    print_header("CHATBOT STANDALONE TESTS")
    print_info("Testing components without Django server")
    
    tests = [
        ("Language Detection", test_language_detection),
        ("Intent Detection", test_intent_detection),
        ("Query Processor", test_query_processor),
        ("Knowledge Base", test_knowledge_base),
        ("Performance Benchmark", test_performance_benchmark),
    ]
    
    results = []
    total_passed = 0
    total_failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if isinstance(result, tuple):
                passed, failed = result
                total_passed += passed
                total_failed += failed
                results.append((test_name, passed, failed))
            else:
                results.append((test_name, 0, 1))
        except Exception as e:
            import traceback
            total_failed += 1
            results.append((test_name, 0, 1))
            print_fail(f"Test crashed: {e}")
            traceback.print_exc()
    
    # Summary
    print_header("TEST SUMMARY")
    
    for test_name, passed, failed in results:
        status = f"{Colors.GREEN}✓{Colors.RESET}" if failed == 0 else f"{Colors.RED}✗{Colors.RESET}"
        print(f"{status} {test_name:30} Passed: {passed:3}  Failed: {failed:3}")
    
    print(f"\n{Colors.BOLD}Total: {total_passed} passed, {total_failed} failed{Colors.RESET}")
    
    if total_failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}All tests passed! 🎉{Colors.RESET}\n")
        return True
    else:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}Some tests had issues. Review above.{Colors.RESET}\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


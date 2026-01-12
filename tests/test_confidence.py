"""
Confidence Testing Module

This module tests confidence score calculation and usage throughout the chatbot system.
Tests include:
- Confidence calculation for different query types (short, long, edge cases)
- Confidence thresholds and their impact on routing decisions
- Confidence scores across different intents and languages
- Confidence level categorization (high, medium, low)
- Integration with intent classification and query preprocessing
- Confidence-based routing and fallback mechanisms

Usage:
    # Run all confidence tests
    python tests/test_confidence.py
    
    # Run specific test category
    python tests/test_confidence.py --category short_queries
    
    # Run with detailed output
    python tests/test_confidence.py --verbose
    
    # Save results to file
    python tests/test_confidence.py --output results.json
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'src'))

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


@dataclass
class ConfidenceTestResult:
    """Test result for a single confidence test case"""
    query: str
    language: str
    detected_intent: str
    confidence: float
    confidence_level: str
    expected_intent: Optional[str] = None
    expected_confidence_range: Optional[Tuple[float, float]] = None
    test_passed: bool = True
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ConfidenceTestSuite:
    """Collection of test cases organized by category"""
    category: str
    tests: List[ConfidenceTestResult]
    total: int = 0
    passed: int = 0
    failed: int = 0
    avg_confidence: float = 0.0
    min_confidence: float = 1.0
    max_confidence: float = 0.0


class ConfidenceTester:
    """Main class for testing confidence scores"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.processor = None
        self.intent_classifier = None
        self.test_suites: List[ConfidenceTestSuite] = []
        self._init_components()
    
    def _init_components(self):
        """Initialize query processor and intent classifier"""
        try:
            from backend.nlp.query_preprocessing import QueryProcessor
            self.processor = QueryProcessor(use_database=True, use_nlp=True)
            print(f"{Colors.GREEN}✓{Colors.RESET} QueryProcessor initialized")
        except Exception as e:
            print(f"{Colors.RED}✗{Colors.RESET} Failed to initialize QueryProcessor: {e}")
            sys.exit(1)
        
        try:
            if self.processor.intent_classifier:
                self.intent_classifier = self.processor.intent_classifier
                print(f"{Colors.GREEN}✓{Colors.RESET} IntentClassifier available")
            else:
                print(f"{Colors.YELLOW}⚠{Colors.RESET} IntentClassifier not available, using keyword fallback")
        except Exception as e:
            print(f"{Colors.YELLOW}⚠{Colors.RESET} IntentClassifier initialization warning: {e}")
    
    def get_confidence_level(self, score: float) -> str:
        """Convert numerical confidence score to level"""
        if score >= 0.8:
            return "high"
        elif score >= 0.5:
            return "medium"
        elif score >= 0.3:
            return "low"
        else:
            return "very_low"
    
    def test_short_queries(self) -> ConfidenceTestSuite:
        """Test confidence for short queries (1-2 words)"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}Testing Short Queries (1-2 words){Colors.RESET}")
        
        test_cases = [
            # Single word queries
            ("hello", "en", "greeting", (0.5, 1.0)),
            ("hi", "en", "greeting", (0.5, 1.0)),
            ("bye", "en", "farewell", (0.5, 1.0)),
            ("programs", "en", "program_info", (0.4, 1.0)),
            ("fees", "en", "fees", (0.4, 1.0)),
            ("admission", "en", "admission", (0.4, 1.0)),
            ("contact", "en", "staff_contact", (0.4, 1.0)),
            
            # Two word queries
            ("BCSAI program", "en", "program_info", (0.6, 1.0)),
            ("tuition fees", "en", "fees", (0.6, 1.0)),
            ("entry requirements", "en", "admission", (0.6, 1.0)),
            ("staff contact", "en", "staff_contact", (0.6, 1.0)),
            ("academic calendar", "en", "academic_schedule", (0.6, 1.0)),
            ("research areas", "en", "research", (0.6, 1.0)),
        ]
        
        results = []
        for query, language, expected_intent, expected_range in test_cases:
            result = self._run_confidence_test(
                query, language, expected_intent, expected_range
            )
            results.append(result)
            
            if self.verbose or not result.test_passed:
                self._print_result(result)
        
        return self._create_suite("short_queries", results)
    
    def test_long_queries(self) -> ConfidenceTestSuite:
        """Test confidence for longer queries (4+ words)"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}Testing Long Queries (4+ words){Colors.RESET}")
        
        test_cases = [
            ("What programs does FAIX offer for undergraduate students?", "en", "program_info", (0.7, 1.0)),
            ("How much are the tuition fees for the BCSAI program?", "en", "fees", (0.7, 1.0)),
            ("What are the admission requirements for international students?", "en", "admission", (0.7, 1.0)),
            ("Who can I contact if I have questions about course registration?", "en", "staff_contact", (0.8, 1.0)),
            ("When does the new academic semester start?", "en", "academic_schedule", (0.7, 1.0)),
            ("What research areas are the faculty members working on?", "en", "research", (0.7, 1.0)),
            ("Can you tell me about the facilities available in the faculty?", "en", "facility_info", (0.7, 1.0)),
            ("I need information about the academic handbook and forms", "en", "academic_resources", (0.7, 1.0)),
        ]
        
        results = []
        for query, language, expected_intent, expected_range in test_cases:
            result = self._run_confidence_test(
                query, language, expected_intent, expected_range
            )
            results.append(result)
            
            if self.verbose or not result.test_passed:
                self._print_result(result)
        
        return self._create_suite("long_queries", results)
    
    def test_priority_patterns(self) -> ConfidenceTestSuite:
        """Test confidence for priority patterns (should get high confidence)"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}Testing Priority Patterns (Expected: High Confidence){Colors.RESET}")
        
        test_cases = [
            ("when was faix established", "en", "about_faix", (0.8, 1.0)),
            ("when was faix founded", "en", "about_faix", (0.8, 1.0)),
            ("what programs does faix offer", "en", "program_info", (0.8, 1.0)),
            ("who can i contact", "en", "staff_contact", (0.8, 1.0)),
            ("what is the vision of faix", "en", "about_faix", (0.8, 1.0)),
            ("what is the mission", "en", "about_faix", (0.8, 1.0)),
            ("when is the semester", "en", "academic_schedule", (0.8, 1.0)),
        ]
        
        results = []
        for query, language, expected_intent, expected_range in test_cases:
            result = self._run_confidence_test(
                query, language, expected_intent, expected_range
            )
            results.append(result)
            
            if self.verbose or not result.test_passed:
                self._print_result(result)
        
        return self._create_suite("priority_patterns", results)
    
    def test_low_confidence_scenarios(self) -> ConfidenceTestSuite:
        """Test confidence for ambiguous or unclear queries"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}Testing Low Confidence Scenarios{Colors.RESET}")
        
        test_cases = [
            ("random text xyz", "en", None, (0.0, 0.3)),  # No expected intent, just low confidence
            ("asdfghjkl", "en", None, (0.0, 0.3)),
            ("123456", "en", None, (0.0, 0.3)),
            ("???", "en", None, (0.0, 0.3)),
            ("", "en", None, (0.0, 0.3)),
            ("maybe possibly perhaps", "en", None, (0.0, 0.4)),
        ]
        
        results = []
        for query, language, expected_intent, expected_range in test_cases:
            result = self._run_confidence_test(
                query, language, expected_intent, expected_range
            )
            results.append(result)
            
            if self.verbose or not result.test_passed:
                self._print_result(result)
        
        return self._create_suite("low_confidence", results)
    
    def test_multilingual_confidence(self) -> ConfidenceTestSuite:
        """Test confidence across different languages"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}Testing Multilingual Confidence{Colors.RESET}")
        
        test_cases = [
            # Malay
            ("program apa yang ditawarkan", "ms", "program_info", (0.5, 1.0)),
            ("yuran berapa", "ms", "fees", (0.5, 1.0)),
            ("siapa boleh saya hubungi", "ms", "staff_contact", (0.5, 1.0)),
            
            # Chinese (simplified examples - actual testing may vary)
            ("程序", "zh", None, (0.3, 1.0)),  # "program"
            ("费用", "zh", None, (0.3, 1.0)),  # "fees"
        ]
        
        results = []
        for query, language, expected_intent, expected_range in test_cases:
            result = self._run_confidence_test(
                query, language, expected_intent, expected_range
            )
            results.append(result)
            
            if self.verbose or not result.test_passed:
                self._print_result(result)
        
        return self._create_suite("multilingual", results)
    
    def test_confidence_thresholds(self) -> ConfidenceTestSuite:
        """Test that confidence thresholds work correctly"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}Testing Confidence Thresholds{Colors.RESET}")
        
        # Test queries that should trigger different threshold behaviors
        test_cases = [
            # High confidence (>= 0.8) - should route directly
            ("when was faix established", "en", None, (0.8, 1.0)),
            ("what programs does faix offer", "en", None, (0.8, 1.0)),
            
            # Medium confidence (0.5-0.8) - should route but may need clarification
            ("programs available", "en", None, (0.5, 0.8)),
            ("tell me about fees", "en", None, (0.5, 0.8)),
            
            # Low confidence (0.3-0.5) - may need fallback
            ("information", "en", None, (0.3, 0.5)),
            ("help", "en", None, (0.3, 0.5)),
            
            # Very low confidence (< 0.3) - should use fallback
            ("xyz abc", "en", None, (0.0, 0.3)),
            ("random text", "en", None, (0.0, 0.3)),
        ]
        
        results = []
        for query, language, expected_intent, expected_range in test_cases:
            result = self._run_confidence_test(
                query, language, expected_intent, expected_range
            )
            results.append(result)
            
            # Test threshold behavior
            threshold_high = result.confidence >= 0.8
            threshold_medium = 0.5 <= result.confidence < 0.8
            threshold_low = 0.3 <= result.confidence < 0.5
            threshold_very_low = result.confidence < 0.3
            
            result.metadata = result.metadata or {}
            result.metadata.update({
                'threshold_high': threshold_high,
                'threshold_medium': threshold_medium,
                'threshold_low': threshold_low,
                'threshold_very_low': threshold_very_low,
            })
            
            if self.verbose or not result.test_passed:
                self._print_result(result)
        
        return self._create_suite("confidence_thresholds", results)
    
    def test_intent_confidence_distribution(self) -> ConfidenceTestSuite:
        """Test confidence scores across different intents"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}Testing Intent Confidence Distribution{Colors.RESET}")
        
        intent_queries = {
            'program_info': [
                "What programs does FAIX offer?",
                "Tell me about BCSAI",
                "What degrees are available?",
            ],
            'admission': [
                "What are the admission requirements?",
                "How to apply?",
                "Entry criteria",
            ],
            'fees': [
                "How much are the fees?",
                "Tuition costs",
                "Payment schedule",
            ],
            'staff_contact': [
                "Who can I contact?",
                "Staff email",
                "Contact information",
            ],
            'about_faix': [
                "Tell me about FAIX",
                "What is FAIX?",
                "Faculty information",
            ],
            'academic_schedule': [
                "When is the semester?",
                "Academic calendar",
                "Important dates",
            ],
        }
        
        results = []
        for intent, queries in intent_queries.items():
            for query in queries:
                result = self._run_confidence_test(
                    query, "en", intent, (0.4, 1.0)
                )
                results.append(result)
                
                if self.verbose:
                    self._print_result(result)
        
        return self._create_suite("intent_distribution", results)
    
    def _run_confidence_test(
        self,
        query: str,
        language: str,
        expected_intent: Optional[str],
        expected_range: Optional[Tuple[float, float]]
    ) -> ConfidenceTestResult:
        """Run a single confidence test"""
        try:
            # Process the query
            processed = self.processor.process_query(query)
            
            detected_intent = processed.get('detected_intent', 'about_faix')
            confidence = processed.get('confidence_score', 0.0)
            confidence_level = self.get_confidence_level(confidence)
            
            # Check if test passed
            test_passed = True
            error = None
            
            # Check intent match (if expected)
            if expected_intent and detected_intent != expected_intent:
                test_passed = False
                error = f"Intent mismatch: expected '{expected_intent}', got '{detected_intent}'"
            
            # Check confidence range (if expected)
            if expected_range and not (expected_range[0] <= confidence <= expected_range[1]):
                test_passed = False
                if error:
                    error += f"; Confidence {confidence:.2f} not in range {expected_range}"
                else:
                    error = f"Confidence {confidence:.2f} not in range {expected_range}"
            
            metadata = {
                'query_length': len(query.split()),
                'processed_data': {
                    'intent': detected_intent,
                    'confidence': confidence,
                    'language': processed.get('language', {}).get('code', language),
                }
            }
            
            return ConfidenceTestResult(
                query=query,
                language=language,
                detected_intent=detected_intent,
                confidence=confidence,
                confidence_level=confidence_level,
                expected_intent=expected_intent,
                expected_confidence_range=expected_range,
                test_passed=test_passed,
                error=error,
                metadata=metadata
            )
            
        except Exception as e:
            return ConfidenceTestResult(
                query=query,
                language=language,
                detected_intent="error",
                confidence=0.0,
                confidence_level="very_low",
                expected_intent=expected_intent,
                expected_confidence_range=expected_range,
                test_passed=False,
                error=str(e)
            )
    
    def _print_result(self, result: ConfidenceTestResult):
        """Print a single test result"""
        status_color = Colors.GREEN if result.test_passed else Colors.RED
        status_symbol = "✓" if result.test_passed else "✗"
        
        print(f"  {status_color}{status_symbol}{Colors.RESET} {result.query[:50]}")
        print(f"    Intent: {result.detected_intent} | Confidence: {result.confidence:.2f} ({result.confidence_level})")
        
        if result.expected_intent:
            intent_match = "✓" if result.detected_intent == result.expected_intent else "✗"
            print(f"    Expected Intent: {result.expected_intent} {intent_match}")
        
        if result.expected_confidence_range:
            in_range = result.expected_confidence_range[0] <= result.confidence <= result.expected_confidence_range[1]
            range_match = "✓" if in_range else "✗"
            print(f"    Expected Range: {result.expected_confidence_range} {range_match}")
        
        if result.error:
            print(f"    {Colors.RED}Error: {result.error}{Colors.RESET}")
        
        if self.verbose and result.metadata:
            print(f"    {Colors.DIM}Metadata: {json.dumps(result.metadata, indent=4)}{Colors.RESET}")
    
    def _create_suite(self, category: str, results: List[ConfidenceTestResult]) -> ConfidenceTestSuite:
        """Create a test suite from results"""
        total = len(results)
        passed = sum(1 for r in results if r.test_passed)
        failed = total - passed
        
        if results:
            confidences = [r.confidence for r in results]
            avg_confidence = sum(confidences) / len(confidences)
            min_confidence = min(confidences)
            max_confidence = max(confidences)
        else:
            avg_confidence = 0.0
            min_confidence = 1.0
            max_confidence = 0.0
        
        suite = ConfidenceTestSuite(
            category=category,
            tests=results,
            total=total,
            passed=passed,
            failed=failed,
            avg_confidence=avg_confidence,
            min_confidence=min_confidence,
            max_confidence=max_confidence
        )
        
        self.test_suites.append(suite)
        return suite
    
    def print_suite_summary(self, suite: ConfidenceTestSuite):
        """Print summary for a test suite"""
        pass_rate = (suite.passed / suite.total * 100) if suite.total > 0 else 0
        
        print(f"\n{Colors.BOLD}{suite.category.replace('_', ' ').title()}{Colors.RESET}")
        print(f"  Total: {suite.total} | Passed: {Colors.GREEN}{suite.passed}{Colors.RESET} | Failed: {Colors.RED}{suite.failed}{Colors.RESET} ({pass_rate:.1f}%)")
        print(f"  Confidence: Avg={suite.avg_confidence:.2f} | Min={suite.min_confidence:.2f} | Max={suite.max_confidence:.2f}")
    
    def print_overall_summary(self):
        """Print overall test summary"""
        total_tests = sum(suite.total for suite in self.test_suites)
        total_passed = sum(suite.passed for suite in self.test_suites)
        total_failed = sum(suite.failed for suite in self.test_suites)
        
        all_confidences = []
        for suite in self.test_suites:
            all_confidences.extend([r.confidence for r in suite.tests])
        
        overall_avg = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}Overall Summary{Colors.RESET}")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {Colors.GREEN}{total_passed}{Colors.RESET} ({total_passed/total_tests*100:.1f}%)")
        print(f"Failed: {Colors.RED}{total_failed}{Colors.RESET} ({total_failed/total_tests*100:.1f}%)")
        print(f"Overall Average Confidence: {overall_avg:.2f}")
        
        # Confidence distribution
        high_conf = sum(1 for c in all_confidences if c >= 0.8)
        medium_conf = sum(1 for c in all_confidences if 0.5 <= c < 0.8)
        low_conf = sum(1 for c in all_confidences if 0.3 <= c < 0.5)
        very_low_conf = sum(1 for c in all_confidences if c < 0.3)
        
        print(f"\nConfidence Distribution:")
        print(f"  High (≥0.8): {high_conf} ({high_conf/len(all_confidences)*100:.1f}%)")
        print(f"  Medium (0.5-0.8): {medium_conf} ({medium_conf/len(all_confidences)*100:.1f}%)")
        print(f"  Low (0.3-0.5): {low_conf} ({low_conf/len(all_confidences)*100:.1f}%)")
        print(f"  Very Low (<0.3): {very_low_conf} ({very_low_conf/len(all_confidences)*100:.1f}%)")
        
        # Per-suite summary
        print(f"\nPer-Suite Results:")
        for suite in self.test_suites:
            self.print_suite_summary(suite)
    
    def export_results(self, output_path: str):
        """Export test results to JSON file"""
        results_data = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'suites': [asdict(suite) for suite in self.test_suites],
            'summary': {
                'total_tests': sum(suite.total for suite in self.test_suites),
                'total_passed': sum(suite.passed for suite in self.test_suites),
                'total_failed': sum(suite.failed for suite in self.test_suites),
                'overall_avg_confidence': sum(
                    r.confidence for suite in self.test_suites for r in suite.tests
                ) / sum(suite.total for suite in self.test_suites) if self.test_suites else 0.0,
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n{Colors.GREEN}✓{Colors.RESET} Results exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Test confidence scoring in the chatbot system')
    parser.add_argument('--category', type=str, help='Run specific test category')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--output', '-o', type=str, help='Export results to JSON file')
    
    args = parser.parse_args()
    
    tester = ConfidenceTester(verbose=args.verbose)
    
    # Define test categories
    test_categories = {
        'short_queries': tester.test_short_queries,
        'long_queries': tester.test_long_queries,
        'priority_patterns': tester.test_priority_patterns,
        'low_confidence': tester.test_low_confidence_scenarios,
        'multilingual': tester.test_multilingual_confidence,
        'thresholds': tester.test_confidence_thresholds,
        'intent_distribution': tester.test_intent_confidence_distribution,
        'all': None,  # Run all tests
    }
    
    if args.category:
        if args.category not in test_categories:
            print(f"{Colors.RED}Error: Unknown category '{args.category}'{Colors.RESET}")
            print(f"Available categories: {', '.join(test_categories.keys())}")
            sys.exit(1)
        
        if args.category == 'all':
            # Run all tests
            for name, test_func in test_categories.items():
                if test_func:
                    test_func()
        else:
            # Run specific category
            test_categories[args.category]()
    else:
        # Run all tests by default
        for name, test_func in test_categories.items():
            if test_func:
                test_func()
    
    # Print summary
    tester.print_overall_summary()
    
    # Export results if requested
    if args.output:
        tester.export_results(args.output)


if __name__ == '__main__':
    main()

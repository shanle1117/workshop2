"""
Chatbot Test Script with Questions

This script tests the FAIX chatbot using questions from test files.
Supports both API testing (Django server) and direct testing (standalone).

Usage:
    # Test via API (requires Django server running)
    python tests/test_chatbot_with_questions.py --mode api
    
    # Test standalone (no Django required)
    python tests/test_chatbot_with_questions.py --mode standalone
    
    # Test specific category
    python tests/test_chatbot_with_questions.py --category program_info
    
    # Quick test (fewer questions)
    python tests/test_chatbot_with_questions.py --quick
"""

import sys
import os
import json
import time
import argparse
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

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


@dataclass
class TestResult:
    """Test result for a single question"""
    question: str
    response: str
    success: bool
    time_taken: float
    error: Optional[str] = None
    intent: Optional[str] = None
    category: Optional[str] = None


class TestQuestionLoader:
    """Loads test questions from files"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.questions_file = base_dir / 'tests' / 'CHATBOT_TEST_QUESTIONS.md'
        self.quick_file = base_dir / 'tests' / 'QUICK_TEST_QUESTIONS.txt'
    
    def load_quick_questions(self) -> List[str]:
        """Load quick test questions"""
        questions = []
        try:
            with open(self.quick_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                skip_section = False
                for line in lines:
                    line = line.strip()
                    # Skip comments, headers, and empty lines
                    if not line or line.startswith('#') or line.startswith('##') or line == '---':
                        continue
                    # Skip the "Copy-paste ready format" section
                    if 'Copy-paste' in line.lower():
                        skip_section = True
                        continue
                    if skip_section and line:
                        questions.append(line)
                    # Regular questions (not starting with -)
                    elif line and not line.startswith('-'):
                        questions.append(line)
                    # Questions with markdown formatting
                    elif line.startswith('- '):
                        question = line[2:].strip()
                        # Remove language annotations
                        if ' (' in question:
                            question = question.split(' (')[0]
                        if question:
                            questions.append(question)
        except FileNotFoundError:
            print_warn(f"Quick questions file not found: {self.quick_file}")
        return questions
    
    def load_questions_by_category(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """Load questions organized by category from markdown file"""
        questions_by_category = {}
        current_category = None
        current_questions = []
        
        def is_valid_question(text: str) -> bool:
            """Check if text is a valid question (not markdown link, checklist, etc.)"""
            if not text or len(text) < 3:
                return False
            # Skip markdown links [text](#link)
            if text.startswith('[') and '](' in text:
                return False
            # Skip checklist items [ ] or [x]
            if text.startswith('[ ]') or text.startswith('[x]') or text.startswith('[X]'):
                return False
            # Skip bold text markers
            if text.startswith('**') and text.endswith('**'):
                return False
            # Skip table of contents entries
            if text.startswith('- [') or text.startswith('* ['):
                return False
            # Skip notes/instructions
            if 'should be replaced' in text.lower() or 'may require' in text.lower():
                return False
            # Skip very long lines (likely notes, not questions)
            if len(text) > 200:
                return False
            # Must contain at least one letter
            if not any(c.isalpha() for c in text):
                return False
            return True
        
        try:
            with open(self.questions_file, 'r', encoding='utf-8') as f:
                in_category = False
                skip_section = False
                
                for line in f:
                    line = line.strip()
                    
                    # Skip table of contents section
                    if 'Table of Contents' in line or 'table of contents' in line.lower():
                        skip_section = True
                        continue
                    if skip_section and line.startswith('---'):
                        skip_section = False
                        continue
                    if skip_section:
                        continue
                    
                    # Detect category headers (## Category Name)
                    if line.startswith('## ') and not line.startswith('###'):
                        # Save previous category
                        if current_category and current_questions:
                            questions_by_category[current_category] = current_questions
                        
                        # Start new category
                        current_category = line[3:].strip()
                        # Remove emoji if present
                        if ' ' in current_category:
                            parts = current_category.split(' ', 1)
                            if len(parts[0]) <= 2:  # Likely emoji
                                current_category = parts[1]
                        # Map to intent names
                        current_category = self._map_category_to_intent(current_category)
                        current_questions = []
                        in_category = True
                        skip_section = False
                    
                    # Skip certain sections
                    elif 'Testing Checklist' in line or 'Notes' in line or 'Usage Tips' in line:
                        skip_section = True
                        in_category = False
                    
                    # Collect questions (lines starting with -)
                    elif in_category and not skip_section and line.startswith('- '):
                        question = line[2:].strip()
                        # Remove language annotations
                        if ' (' in question:
                            question = question.split(' (')[0]
                        # Validate question
                        if is_valid_question(question):
                            current_questions.append(question)
                    
                    # Also collect questions without bullet points (in copy-paste sections)
                    elif in_category and not skip_section and line and not line.startswith('#') and not line.startswith('|'):
                        if is_valid_question(line):
                            # Only add if it looks like a question (ends with ? or is a short sentence)
                            if '?' in line or (len(line) < 100 and any(word in line.lower() for word in ['what', 'how', 'when', 'where', 'who', 'tell', 'can', 'is', 'are'])):
                                if line not in current_questions:  # Avoid duplicates
                                    current_questions.append(line)
            
            # Save last category
            if current_category and current_questions:
                questions_by_category[current_category] = current_questions
        
        except FileNotFoundError:
            print_warn(f"Questions file not found: {self.questions_file}")
        
        # Filter by category if specified
        if category:
            return {category: questions_by_category.get(category, [])}
        
        return questions_by_category
    
    def _map_category_to_intent(self, category: str) -> str:
        """Map category name to intent name"""
        mapping = {
            'Greetings': 'greeting',
            'Program Information': 'program_info',
            'Admission': 'admission',
            'Fees': 'fees',
            'Career Opportunities': 'career',
            'About FAIX': 'about_faix',
            'Staff Contacts': 'staff_contact',
            'Facility Information': 'facility_info',
            'Academic Resources': 'academic_resources',
            'Research': 'research',
            'Course Information': 'course_info',
            'Registration': 'registration',
            'Academic Schedule': 'academic_schedule',
            'Farewells': 'farewell',
        }
        return mapping.get(category, category.lower().replace(' ', '_'))


class ChatbotTester:
    """Tests chatbot with questions"""
    
    def __init__(self, mode: str = 'standalone', api_url: str = 'http://localhost:8000'):
        self.mode = mode
        self.api_url = api_url
        self.session_id = str(uuid.uuid4())
        self.history = []
        self.results: List[TestResult] = []
        
        # Initialize standalone components if needed
        if mode == 'standalone':
            try:
                from src.conversation_manager import process_conversation
                self.process_conversation = process_conversation
                self.standalone_available = True
            except ImportError as e:
                print_warn(f"Standalone mode not available: {e}")
                self.standalone_available = False
    
    def test_question(self, question: str, category: Optional[str] = None) -> TestResult:
        """Test a single question"""
        start_time = time.time()
        response = ""
        success = False
        error = None
        intent = None
        
        # Check if response is a fallback (not acceptable)
        fallback_phrases = [
            "i'm sorry, i didn't quite understand",
            "could you please clarify",
            "i couldn't find",
            "i don't understand",
            "please rephrase"
        ]
        
        try:
            if self.mode == 'api':
                response, intent = self._test_via_api(question)
                has_response = bool(response and len(response) > 0)
                is_fallback = any(phrase in response.lower() for phrase in fallback_phrases)
                # Success means we got a response AND it's not a fallback
                success = has_response and not is_fallback
            else:
                # Standalone mode
                if not self.standalone_available:
                    error = "Standalone mode not available"
                else:
                    context = {}
                    response, context = self.process_conversation(question, context)
                    has_response = bool(response and len(response) > 0)
                    is_fallback = any(phrase in response.lower() for phrase in fallback_phrases)
                    success = has_response and not is_fallback
                    intent = context.get('current_intent')
        
        except Exception as e:
            error = str(e)
            response = f"Error: {error}"
        
        time_taken = time.time() - start_time
        
        return TestResult(
            question=question,
            response=response,
            success=success,
            time_taken=time_taken,
            error=error,
            intent=intent,
            category=category
        )
    
    def _test_via_api(self, question: str) -> Tuple[str, Optional[str]]:
        """Test question via API"""
        try:
            import requests
            
            payload = {
                'message': question,
                'session_id': self.session_id,
                'agent_id': 'faq',
                'history': self.history[-10:]  # Last 10 turns
            }
            
            response = requests.post(
                f'{self.api_url}/api/chat/',
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get('response', '')
                intent = data.get('intent')
                
                # Update history
                self.history.append({'role': 'user', 'content': question})
                self.history.append({'role': 'assistant', 'content': bot_response})
                
                return bot_response, intent
            else:
                return f"API Error: {response.status_code}", None
        
        except ImportError:
            raise Exception("requests library not installed. Install with: pip install requests")
        except Exception as e:
            raise Exception(f"API request failed: {e}")
    
    def test_questions(self, questions: List[str], category: Optional[str] = None) -> List[TestResult]:
        """Test multiple questions"""
        results = []
        for i, question in enumerate(questions, 1):
            print(f"  [{i}/{len(questions)}] Testing: {question[:60]}...", end='', flush=True)
            result = self.test_question(question, category)
            results.append(result)
            
            if result.success:
                print(f" {Colors.GREEN}✓{Colors.RESET} ({result.time_taken:.2f}s)")
            else:
                print(f" {Colors.RED}✗{Colors.RESET} ({result.time_taken:.2f}s)")
                if result.error:
                    print(f"    Error: {result.error}")
        
        self.results.extend(results)
        return results
    
    def get_statistics(self) -> Dict:
        """Get test statistics"""
        if not self.results:
            return {}
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r.success)
        failed = total - successful
        avg_time = sum(r.time_taken for r in self.results) / total
        max_time = max(r.time_taken for r in self.results)
        min_time = min(r.time_taken for r in self.results)
        
        # Group by category
        by_category = {}
        for result in self.results:
            cat = result.category or 'unknown'
            if cat not in by_category:
                by_category[cat] = {'total': 0, 'success': 0}
            by_category[cat]['total'] += 1
            if result.success:
                by_category[cat]['success'] += 1
        
        return {
            'total': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'avg_time': avg_time,
            'max_time': max_time,
            'min_time': min_time,
            'by_category': by_category
        }


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")


def print_test(name: str):
    """Print test name"""
    print(f"{Colors.BOLD}{Colors.BLUE}→ Testing: {name}{Colors.RESET}")


def print_pass(message: str = ""):
    """Print pass message"""
    print(f"{Colors.GREEN}  ✓ PASS{Colors.RESET} {message}")


def print_fail(message: str = ""):
    """Print fail message"""
    print(f"{Colors.RED}  ✗ FAIL{Colors.RESET} {message}")


def print_warn(message: str = ""):
    """Print warning message"""
    print(f"{Colors.YELLOW}  ⚠ WARN{Colors.RESET} {message}")


def print_info(message: str = ""):
    """Print info message"""
    print(f"{Colors.CYAN}  ℹ INFO{Colors.RESET} {message}")


def print_statistics(stats: Dict):
    """Print test statistics"""
    print_header("Test Statistics")
    
    print(f"{Colors.BOLD}Overall Results:{Colors.RESET}")
    print(f"  Total Questions: {stats['total']}")
    print(f"  Successful: {Colors.GREEN}{stats['successful']}{Colors.RESET}")
    print(f"  Failed: {Colors.RED}{stats['failed']}{Colors.RESET}")
    print(f"  Success Rate: {Colors.BOLD}{stats['success_rate']:.1f}%{Colors.RESET}")
    
    print(f"\n{Colors.BOLD}Performance:{Colors.RESET}")
    print(f"  Average Time: {stats['avg_time']:.3f}s")
    print(f"  Min Time: {stats['min_time']:.3f}s")
    print(f"  Max Time: {stats['max_time']:.3f}s")
    
    if stats.get('by_category'):
        print(f"\n{Colors.BOLD}By Category:{Colors.RESET}")
        for category, cat_stats in stats['by_category'].items():
            success_rate = (cat_stats['success'] / cat_stats['total'] * 100) if cat_stats['total'] > 0 else 0
            status_color = Colors.GREEN if success_rate >= 80 else Colors.YELLOW if success_rate >= 50 else Colors.RED
            print(f"  {category:20s}: {cat_stats['success']}/{cat_stats['total']} ({status_color}{success_rate:.1f}%{Colors.RESET})")


def print_failed_tests(results: List[TestResult]):
    """Print failed test details"""
    failed = [r for r in results if not r.success]
    if not failed:
        return
    
    print_header("Failed Tests")
    for i, result in enumerate(failed, 1):
        print(f"\n{Colors.RED}{i}. {result.question}{Colors.RESET}")
        if result.error:
            print(f"   Error: {result.error}")
        if result.response:
            print(f"   Response: {result.response[:200]}...")


def main():
    """Main test function"""
    parser = argparse.ArgumentParser(description='Test FAIX Chatbot with questions')
    parser.add_argument('--mode', choices=['api', 'standalone'], default='api',
                       help='Test mode: api (requires Django server) or standalone')
    parser.add_argument('--api-url', default='http://localhost:8000',
                       help='API URL (default: http://localhost:8000)')
    parser.add_argument('--category', type=str, default=None,
                       help='Test specific category only')
    parser.add_argument('--quick', action='store_true',
                       help='Use quick test questions only')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of questions per category')
    parser.add_argument('--save-results', type=str, default=None,
                       help='Save results to JSON file')
    
    args = parser.parse_args()
    
    print_header("FAIX Chatbot Test Suite")
    print_info(f"Mode: {args.mode}")
    if args.mode == 'api':
        print_info(f"API URL: {args.api_url}")
    print_info(f"Quick mode: {args.quick}")
    if args.category:
        print_info(f"Category: {args.category}")
    
    # Load questions
    loader = TestQuestionLoader(BASE_DIR)
    
    if args.quick:
        questions = loader.load_quick_questions()
        if questions:
            print_test("Quick Test Questions")
            tester = ChatbotTester(mode=args.mode, api_url=args.api_url)
            tester.test_questions(questions)
        else:
            print_fail("No quick questions loaded")
            return
    else:
        questions_by_category = loader.load_questions_by_category(args.category)
        
        if not questions_by_category:
            print_fail("No questions loaded")
            return
        
        tester = ChatbotTester(mode=args.mode, api_url=args.api_url)
        
        # Test each category
        for category, questions in questions_by_category.items():
            if args.limit:
                questions = questions[:args.limit]
            
            if not questions:
                continue
            
            print_test(f"Category: {category} ({len(questions)} questions)")
            tester.test_questions(questions, category)
            print()  # Empty line between categories
    
    # Print statistics
    stats = tester.get_statistics()
    if stats:
        print_statistics(stats)
    
    # Print failed tests
    print_failed_tests(tester.results)
    
    # Save results if requested
    if args.save_results:
        results_data = {
            'statistics': stats,
            'results': [
                {
                    'question': r.question,
                    'response': r.response[:500],  # Truncate long responses
                    'success': r.success,
                    'time_taken': r.time_taken,
                    'error': r.error,
                    'intent': r.intent,
                    'category': r.category
                }
                for r in tester.results
            ]
        }
        with open(args.save_results, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        print_info(f"Results saved to: {args.save_results}")
    
    print_header("Test Complete")


if __name__ == '__main__':
    main()


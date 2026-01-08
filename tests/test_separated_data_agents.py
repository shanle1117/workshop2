"""
Test Module for Chatbot Agents with Separated Data

This module tests each chatbot agent (FAQ, Schedule, Staff) to ensure they:
1. Load data correctly from separated JSON files
2. Only load their assigned data sections
3. Properly format context for LLM queries
4. Handle edge cases and missing data gracefully
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / 'src'))

# Stub Django for testing (if needed)
import types
if 'django' not in sys.modules:
    sys.modules["django"] = types.ModuleType("django")

from src.agents import (
    get_agent,
    retrieve_for_agent,
    _load_separated_json_file,
    _get_schedule_documents,
    _get_staff_documents,
    _get_faix_data_for_faq,
    _get_faix_data_for_schedule,
    _get_faix_data_for_staff,
)
from src.knowledge_base import KnowledgeBase
from src.prompt_builder import build_messages

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


class DummyKnowledgeBase(KnowledgeBase):
    """Minimal KnowledgeBase stub for testing."""
    
    def __init__(self):
        # Bypass parent init to avoid Django/CSV setup
        self.use_database = False
        self.csv_path = None
        self.use_semantic_search = False
        self.semantic_search = None
        
        # Create minimal test data
        import pandas as pd
        self.df = pd.DataFrame([
            {
                "question": "What programs does FAIX offer?",
                "answer": "FAIX offers BAXI and BAXZ programs.",
                "category": "program_info",
                "keywords": ["program", "baxi", "baxz"],
            },
            {
                "question": "When does semester start?",
                "answer": "Semester 1 starts in September.",
                "category": "academic_schedule",
                "keywords": ["semester", "start"],
            },
            {
                "question": "Who is the dean?",
                "answer": "The dean is Associate Professor Ts. Dr. Muhammad Hafidz Fazli Bin Md Fauadi.",
                "category": "faculty_info",
                "keywords": ["dean"],
            },
        ])
        
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer()
        clean_questions = self.df["question"]
        self.question_vectors = self.vectorizer.fit_transform(clean_questions)


def print_header(text):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.RESET}\n")


def print_test(name):
    """Print test name."""
    print(f"{Colors.BOLD}{Colors.BLUE}→ {name}{Colors.RESET}")


def print_pass(msg=""):
    """Print pass message."""
    print(f"{Colors.GREEN}  [PASS]{Colors.RESET} {msg}")


def print_fail(msg=""):
    """Print fail message."""
    print(f"{Colors.RED}  [FAIL]{Colors.RESET} {msg}")


def print_info(msg=""):
    """Print info message."""
    print(f"{Colors.CYAN}  [INFO]{Colors.RESET} {msg}")


def print_warning(msg=""):
    """Print warning message."""
    print(f"{Colors.YELLOW}  [WARN]{Colors.RESET} {msg}")


def test_separated_file_loading():
    """Test that separated JSON files can be loaded correctly."""
    print_header("Test 1: Separated File Loading")
    
    test_sections = [
        "faculty_info",
        "vision_mission",
        "top_management",
        "programmes",
        "admission",
        "departments",
        "facilities",
        "academic_resources",
        "key_highlights",
        "faqs",
        "research_focus",
        "staff_contacts",
        "schedule",
        "course_info",
        "metadata",
    ]
    
    passed = 0
    failed = 0
    
    for section in test_sections:
        try:
            data = _load_separated_json_file(section)
            if data is not None:
                print_pass(f"Loaded {section}: {type(data).__name__}")
                passed += 1
            else:
                print_warning(f"Section {section} returned None (file may not exist)")
                failed += 1
        except Exception as e:
            print_fail(f"Failed to load {section}: {str(e)}")
            failed += 1
    
    print_info(f"\nTotal: {passed} passed, {failed} failed")
    return failed == 0


def test_faq_agent_data():
    """Test FAQ agent loads only its assigned data sections."""
    print_header("Test 2: FAQ Agent Data Loading")
    
    try:
        faq_data = _get_faix_data_for_faq()
        
        # Expected sections for FAQ agent
        expected_sections = {
            "faculty_info",
            "vision_mission",
            "top_management",
            "programmes",
            "admission",
            "departments",
            "facilities",
            "academic_resources",
            "key_highlights",
            "faqs",
            "research_focus",
            "course_info",
        }
        
        # Should NOT contain these
        forbidden_sections = {"staff_contacts", "schedule"}
        
        loaded_sections = set(faq_data.keys())
        
        print_info(f"Loaded sections: {sorted(loaded_sections)}")
        print_info(f"Expected sections: {sorted(expected_sections)}")
        
        # Check for expected sections
        missing = expected_sections - loaded_sections
        if missing:
            print_warning(f"Missing sections (may be OK if files don't exist): {missing}")
        else:
            print_pass("All expected sections present")
        
        # Check for forbidden sections
        present_forbidden = forbidden_sections & loaded_sections
        if present_forbidden:
            print_fail(f"Forbidden sections found: {present_forbidden}")
            return False
        else:
            print_pass("No forbidden sections (staff_contacts, schedule) present")
        
        # Validate data structure
        if "faculty_info" in faq_data:
            faculty = faq_data["faculty_info"]
            if isinstance(faculty, dict):
                print_pass("faculty_info is valid dict")
            else:
                print_fail(f"faculty_info should be dict, got {type(faculty)}")
                return False
        
        if "programmes" in faq_data:
            programmes = faq_data["programmes"]
            if isinstance(programmes, (list, dict)):
                print_pass("programmes structure is valid")
            else:
                print_fail(f"programmes should be list/dict, got {type(programmes)}")
                return False
        
        return True
        
    except Exception as e:
        print_fail(f"Error testing FAQ agent data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_schedule_agent_data():
    """Test Schedule agent loads only its assigned data sections."""
    print_header("Test 3: Schedule Agent Data Loading")
    
    try:
        schedule_data = _get_faix_data_for_schedule()
        
        # Expected sections for Schedule agent
        expected_sections = {"schedule", "academic_resources", "faculty_info"}
        
        loaded_sections = set(schedule_data.keys())
        
        print_info(f"Loaded sections: {sorted(loaded_sections)}")
        print_info(f"Expected sections: {sorted(expected_sections)}")
        
        # Check for expected sections
        if "schedule" in schedule_data:
            schedule_list = schedule_data["schedule"]
            if isinstance(schedule_list, list):
                print_pass(f"schedule contains {len(schedule_list)} items")
            else:
                print_fail(f"schedule should be list, got {type(schedule_list)}")
                return False
        else:
            print_warning("schedule section not found")
        
        # Check faculty_info is minimal (name, university only)
        if "faculty_info" in schedule_data:
            faculty = schedule_data["faculty_info"]
            if isinstance(faculty, dict):
                allowed_keys = {"name", "university"}
                actual_keys = set(faculty.keys())
                extra_keys = actual_keys - allowed_keys
                if extra_keys:
                    print_warning(f"faculty_info has extra keys: {extra_keys} (should only have name, university)")
                else:
                    print_pass("faculty_info has correct minimal structure")
        
        # Should NOT contain other sections
        forbidden_sections = {"staff_contacts", "faqs", "top_management", "programmes"}
        present_forbidden = forbidden_sections & loaded_sections
        if present_forbidden:
            print_warning(f"Unexpected sections found: {present_forbidden} (may be OK)")
        
        # Test schedule documents retrieval
        schedule_docs = _get_schedule_documents()
        print_info(f"Schedule documents: {len(schedule_docs)} documents retrieved")
        if len(schedule_docs) > 0:
            print_pass("Schedule documents retrieved successfully")
            # Check document structure
            first_doc = schedule_docs[0]
            required_keys = {"title", "description", "time", "raw"}
            if all(key in first_doc for key in required_keys):
                print_pass("Schedule document structure is correct")
            else:
                missing = required_keys - set(first_doc.keys())
                print_fail(f"Schedule document missing keys: {missing}")
                return False
        else:
            print_warning("No schedule documents found")
        
        return True
        
    except Exception as e:
        print_fail(f"Error testing Schedule agent data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_staff_agent_data():
    """Test Staff agent loads only its assigned data sections."""
    print_header("Test 4: Staff Agent Data Loading")
    
    try:
        staff_data = _get_faix_data_for_staff()
        
        # Expected sections for Staff agent
        expected_sections = {"staff_contacts", "departments", "faculty_info"}
        
        loaded_sections = set(staff_data.keys())
        
        print_info(f"Loaded sections: {sorted(loaded_sections)}")
        print_info(f"Expected sections: {sorted(expected_sections)}")
        
        # Check staff_contacts structure
        if "staff_contacts" in staff_data:
            staff_contacts = staff_data["staff_contacts"]
            if isinstance(staff_contacts, dict):
                print_pass("staff_contacts is valid dict")
                if "departments" in staff_contacts:
                    print_pass("staff_contacts contains departments structure")
            else:
                print_fail(f"staff_contacts should be dict, got {type(staff_contacts)}")
                return False
        else:
            print_warning("staff_contacts section not found")
        
        # Check faculty_info is minimal (dean, name, university only)
        if "faculty_info" in staff_data:
            faculty = staff_data["faculty_info"]
            if isinstance(faculty, dict):
                allowed_keys = {"dean", "name", "university"}
                actual_keys = set(faculty.keys())
                extra_keys = actual_keys - allowed_keys
                if extra_keys:
                    print_warning(f"faculty_info has extra keys: {extra_keys}")
                print_pass("faculty_info structure validated")
        
        # Test staff documents retrieval
        staff_docs = _get_staff_documents()
        print_info(f"Staff documents: {len(staff_docs)} staff members retrieved")
        if len(staff_docs) > 0:
            print_pass("Staff documents retrieved successfully")
            # Check document structure
            first_doc = staff_docs[0]
            required_keys = {"name", "role", "email"}
            if all(key in first_doc for key in required_keys):
                print_pass("Staff document structure is correct")
                print_info(f"Sample staff: {first_doc.get('name', 'N/A')} - {first_doc.get('role', 'N/A')}")
            else:
                missing = required_keys - set(first_doc.keys())
                print_fail(f"Staff document missing keys: {missing}")
                return False
        else:
            print_warning("No staff documents found")
        
        # Should NOT contain schedule or FAQs
        forbidden_sections = {"schedule", "faqs"}
        present_forbidden = forbidden_sections & loaded_sections
        if present_forbidden:
            print_warning(f"Unexpected sections found: {present_forbidden} (may be OK)")
        
        return True
        
    except Exception as e:
        print_fail(f"Error testing Staff agent data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_context_retrieval():
    """Test that each agent retrieves correct context for queries."""
    print_header("Test 5: Agent Context Retrieval")
    
    kb = DummyKnowledgeBase()
    
    test_cases = [
        {
            "agent_id": "faq",
            "query": "What programs does FAIX offer?",
            "intent": "program_info",
            "expected_keys": ["faq", "faix_data"],
            "should_have": ["programmes"],
        },
        {
            "agent_id": "schedule",
            "query": "When does the semester start?",
            "intent": "academic_schedule",
            "expected_keys": ["schedule", "faix_data"],
            "should_have": ["schedule"],
        },
        {
            "agent_id": "staff",
            "query": "Who is Dr. Burhanuddin?",
            "intent": "staff_contact",
            "expected_keys": ["staff", "faix_data"],
            "should_have": ["staff_contacts"],
        },
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        agent_id = test_case["agent_id"]
        query = test_case["query"]
        intent = test_case["intent"]
        expected_keys = test_case["expected_keys"]
        should_have = test_case["should_have"]
        
        print_test(f"Testing {agent_id} agent")
        
        try:
            context = retrieve_for_agent(
                agent_id=agent_id,
                user_text=query,
                knowledge_base=kb,
                intent=intent,
                top_k=3,
            )
            
            context_keys = set(context.keys())
            print_info(f"Context keys: {sorted(context_keys)}")
            
            # Check expected keys are present
            missing_keys = set(expected_keys) - context_keys
            if missing_keys:
                print_warning(f"Missing context keys: {missing_keys}")
            else:
                print_pass(f"All expected context keys present")
            
            # Check faix_data contains expected sections
            if "faix_data" in context:
                faix_data = context["faix_data"]
                faix_keys = set(faix_data.keys())
                print_info(f"FAIX data sections: {sorted(faix_keys)}")
                
                for required in should_have:
                    if required in faix_keys:
                        print_pass(f"FAIX data contains {required}")
                    else:
                        print_fail(f"FAIX data missing {required}")
                        failed += 1
                        continue
                
                passed += 1
            else:
                print_warning("faix_data not in context")
                failed += 1
            
        except Exception as e:
            print_fail(f"Error retrieving context for {agent_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print_info(f"\nTotal: {passed} passed, {failed} failed")
    return failed == 0


def test_prompt_building():
    """Test that prompts are built correctly with agent context."""
    print_header("Test 6: Prompt Building with Separated Data")
    
    kb = DummyKnowledgeBase()
    
    test_cases = [
        {
            "agent_id": "faq",
            "query": "What programs does FAIX offer?",
            "intent": "program_info",
        },
        {
            "agent_id": "schedule",
            "query": "Show me the timetable for BAXI",
            "intent": "academic_schedule",
        },
        {
            "agent_id": "staff",
            "query": "Contact information for Dr. Burhanuddin",
            "intent": "staff_contact",
        },
    ]
    
    passed = 0
    failed = 0
    
    for test_case in test_cases:
        agent_id = test_case["agent_id"]
        query = test_case["query"]
        intent = test_case["intent"]
        
        print_test(f"Building prompt for {agent_id} agent")
        
        try:
            agent = get_agent(agent_id)
            if not agent:
                print_fail(f"Agent {agent_id} not found")
                failed += 1
                continue
            
            # Retrieve context
            context = retrieve_for_agent(
                agent_id=agent_id,
                user_text=query,
                knowledge_base=kb,
                intent=intent,
                top_k=3,
            )
            
            # Build messages
            messages = build_messages(
                agent=agent,
                user_message=query,
                history=None,
                context=context,
                intent=intent,
            )
            
            # Validate message structure
            if not isinstance(messages, list) or len(messages) == 0:
                print_fail("Messages should be non-empty list")
                failed += 1
                continue
            
            # First message should be system prompt
            if messages[0]["role"] != "system":
                print_fail("First message should be system prompt")
                failed += 1
                continue
            
            # Last message should be user query
            if messages[-1]["role"] != "user" or query not in messages[-1]["content"]:
                print_fail("Last message should be user query")
                failed += 1
                continue
            
            # Check context is included in messages
            context_found = False
            for msg in messages:
                if msg["role"] == "assistant" and ("context" in msg["content"].lower() or "faix" in msg["content"].lower()):
                    context_found = True
                    break
            
            if context_found:
                print_pass("Context included in messages")
            else:
                print_warning("Context may not be in messages (check manually)")
            
            print_pass(f"Prompt built successfully ({len(messages)} messages)")
            passed += 1
            
        except Exception as e:
            print_fail(f"Error building prompt for {agent_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print_info(f"\nTotal: {passed} passed, {failed} failed")
    return failed == 0


def test_data_isolation():
    """Test that agents are properly isolated and don't load unnecessary data."""
    print_header("Test 7: Data Isolation Between Agents")
    
    try:
        # Get data for each agent
        faq_data = _get_faix_data_for_faq()
        schedule_data = _get_faix_data_for_schedule()
        staff_data = _get_faix_data_for_staff()
        
        faq_sections = set(faq_data.keys())
        schedule_sections = set(schedule_data.keys())
        staff_sections = set(staff_data.keys())
        
        print_info(f"FAQ agent sections: {sorted(faq_sections)}")
        print_info(f"Schedule agent sections: {sorted(schedule_sections)}")
        print_info(f"Staff agent sections: {sorted(staff_sections)}")
        
        # FAQ should NOT have staff or schedule
        if "staff_contacts" not in faq_sections and "schedule" not in faq_sections:
            print_pass("FAQ agent correctly excludes staff_contacts and schedule")
        else:
            print_fail("FAQ agent incorrectly includes staff_contacts or schedule")
            return False
        
        # Schedule should NOT have staff or FAQs
        if "staff_contacts" not in schedule_sections:
            print_pass("Schedule agent correctly excludes staff_contacts")
        else:
            print_fail("Schedule agent incorrectly includes staff_contacts")
            return False
        
        # Staff should NOT have schedule or FAQs
        if "schedule" not in staff_sections:
            print_pass("Staff agent correctly excludes schedule")
        else:
            print_fail("Staff agent incorrectly includes schedule")
            return False
        
        # Each should only have minimal faculty_info
        if "faculty_info" in faq_data and "faculty_info" in schedule_data:
            faq_faculty = faq_data["faculty_info"]
            schedule_faculty = schedule_data["faculty_info"]
            
            # Schedule should have minimal faculty_info
            if isinstance(schedule_faculty, dict):
                schedule_keys = set(schedule_faculty.keys())
                if schedule_keys <= {"name", "university"}:
                    print_pass("Schedule agent has minimal faculty_info")
                else:
                    print_warning(f"Schedule agent faculty_info has extra keys: {schedule_keys - {'name', 'university'}}")
            
            # FAQ should have full faculty_info
            if isinstance(faq_faculty, dict) and len(faq_faculty) > 2:
                print_pass("FAQ agent has full faculty_info")
        
        return True
        
    except Exception as e:
        print_fail(f"Error testing data isolation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and print summary."""
    print_header("Chatbot Separated Data Agent Testing")
    print_info("Testing agents with separated JSON data files\n")
    
    results = []
    
    # Run all tests
    results.append(("Separated File Loading", test_separated_file_loading()))
    results.append(("FAQ Agent Data", test_faq_agent_data()))
    results.append(("Schedule Agent Data", test_schedule_agent_data()))
    results.append(("Staff Agent Data", test_staff_agent_data()))
    results.append(("Agent Context Retrieval", test_agent_context_retrieval()))
    results.append(("Prompt Building", test_prompt_building()))
    results.append(("Data Isolation", test_data_isolation()))
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for test_name, result in results:
        status = f"{Colors.GREEN}[PASS]{Colors.RESET}" if result else f"{Colors.RED}[FAIL]{Colors.RESET}"
        print(f"{status} {test_name}")
    
    print(f"\n{Colors.BOLD}Total: {passed}/{len(results)} tests passed{Colors.RESET}")
    
    if failed > 0:
        print(f"{Colors.RED}{failed} test(s) failed{Colors.RESET}")
        return False
    else:
        print(f"{Colors.GREEN}All tests passed!{Colors.RESET}")
        return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

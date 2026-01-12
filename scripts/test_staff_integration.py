#!/usr/bin/env python3
"""
Test script to verify staff_contacts.json is properly loaded and accessible by the chatbot
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up Django environment if needed
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')

# Import after path setup
try:
    from backend.chatbot.agents import _get_staff_documents, retrieve_for_agent
    from backend.chatbot.knowledge_base import KnowledgeBase
except ImportError:
    print("[ERROR] Could not import backend modules. Please ensure the project structure is correct.")
    print(f"Project root: {project_root}")
    sys.exit(1)


def test_staff_loading():
    """Test if staff documents are loaded correctly."""
    print("=" * 70)
    print("TESTING STAFF CONTACTS INTEGRATION")
    print("=" * 70)
    print()
    
    # Test 1: Load staff documents directly
    print("Test 1: Loading staff documents from staff_contacts.json")
    print("-" * 70)
    staff_docs = _get_staff_documents()
    
    if not staff_docs:
        print("[FAIL] No staff documents loaded!")
        print("Check if data/separated/staff_contacts.json exists and has valid structure.")
        return False
    
    print(f"[SUCCESS] Loaded {len(staff_docs)} staff members")
    print()
    
    # Show sample staff members
    print("Sample staff members (first 5):")
    for i, staff in enumerate(staff_docs[:5], 1):
        print(f"  {i}. {staff.get('name', 'N/A')} - {staff.get('role', 'N/A')}")
        print(f"     Department: {staff.get('department', 'N/A')}")
        print(f"     Email: {staff.get('email', 'N/A')}")
        print()
    
    # Test 2: Test agent context retrieval
    print("Test 2: Testing agent context retrieval for 'staff' agent")
    print("-" * 70)
    
    try:
        kb = KnowledgeBase()
        context = retrieve_for_agent(
            agent_id="staff",
            user_text="Who are the professors?",
            knowledge_base=kb,
            top_k=5
        )
        
        staff_context = context.get("staff", [])
        if staff_context:
            print(f"[SUCCESS] Staff context retrieved: {len(staff_context)} staff members")
            print()
            
            # Check if semantic search is working
            print("Test 3: Testing semantic search for staff queries")
            print("-" * 70)
            
            test_queries = [
                "professor",
                "lecturer",
                "administrative",
                "deputy registrar"
            ]
            
            for query in test_queries:
                context = retrieve_for_agent(
                    agent_id="staff",
                    user_text=query,
                    knowledge_base=kb,
                    top_k=3
                )
                matched_staff = context.get("staff", [])
                print(f"  Query: '{query}' -> Found {len(matched_staff)} matches")
                if matched_staff:
                    print(f"    Examples: {', '.join([s.get('name', 'N/A')[:30] for s in matched_staff[:2]])}")
            
            print()
            print("[SUCCESS] All tests passed!")
            print()
            return True
        else:
            print("[FAIL] No staff context found in agent retrieval")
            return False
            
    except Exception as e:
        print(f"[FAIL] Error during agent context retrieval: {e}")
        import traceback
        traceback.print_exc()
        return False


def show_staff_statistics():
    """Show statistics about loaded staff."""
    staff_docs = _get_staff_documents()
    
    if not staff_docs:
        return
    
    print("=" * 70)
    print("STAFF STATISTICS")
    print("=" * 70)
    print()
    
    # Count by department
    departments = {}
    positions = {}
    
    for staff in staff_docs:
        dept = staff.get("department", "Unknown")
        position = staff.get("role", "Unknown")
        
        departments[dept] = departments.get(dept, 0) + 1
        positions[position] = positions.get(position, 0) + 1
    
    print("By Department:")
    for dept, count in sorted(departments.items()):
        print(f"  {dept}: {count} staff")
    
    print()
    print("By Position:")
    for pos, count in sorted(positions.items()):
        print(f"  {pos}: {count} staff")
    
    print()
    print(f"Total: {len(staff_docs)} staff members")
    print()


if __name__ == "__main__":
    success = test_staff_loading()
    print()
    show_staff_statistics()
    
    if success:
        print("=" * 70)
        print("CONCLUSION: Staff integration is working correctly!")
        print("The chatbot can now answer staff-related questions.")
        print("=" * 70)
    else:
        print("=" * 70)
        print("CONCLUSION: There are issues with staff integration.")
        print("Please check the error messages above.")
        print("=" * 70)
    
    sys.exit(0 if success else 1)


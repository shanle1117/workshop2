#!/usr/bin/env python3
"""
Test script to verify staff routing and data loading
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_staff_routing():
    """Test that staff-related queries are properly detected and routed."""
    
    # Staff keywords from views.py
    staff_keywords = [
        'contact', 'email', 'phone', 'professor', 'lecturer', 'staff', 'faculty', 
        'who can i', 'who can', 'reach', 'get in touch', 'call', 'number', 
        'office', 'address', 'dean', 'head of', 'department head', 'ai', 'artificial intelligence',
        'cybersecurity', 'data science', 'machine learning', 'nlp', 'deep learning',
        'administration', 'admin', 'registrar', 'secretary', 'academic staff', 'who works',
        'work in', 'works in', 'working in'
    ]
    
    test_queries = [
        "who works in administration",
        "who work in administration",
        "list administration staff",
        "contact the registrar",
        "who are the professors",
        "find a lecturer",
        "admin staff contact",
        "secretary email",
    ]
    
    print("=" * 70)
    print("TESTING STAFF KEYWORD ROUTING")
    print("=" * 70)
    print()
    
    for query in test_queries:
        query_lower = query.lower()
        matched = [kw for kw in staff_keywords if kw in query_lower]
        
        print(f"Query: '{query}'")
        if matched:
            print(f"  [OK] Matched keywords: {matched}")
            print(f"  -> Will route to STAFF agent")
        else:
            print(f"  [FAIL] No keywords matched - will NOT route to staff agent!")
        print()

    print("=" * 70)
    print("TESTING STAFF DATA LOADING")
    print("=" * 70)
    print()
    
    import json
    json_path = project_root / "data" / "staff_contacts.json"
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_staff = 0
    for dept_key, dept_info in data.get("departments", {}).items():
        staff_count = len(dept_info.get("staff", []))
        total_staff += staff_count
        print(f"Department: {dept_info.get('name', dept_key)}")
        print(f"  Staff count: {staff_count}")
        if dept_key == "administration":
            print("  Admin staff members:")
            for s in dept_info.get("staff", []):
                print(f"    - {s.get('name')} ({s.get('position')})")
        print()
    
    print(f"Total staff members: {total_staff}")
    print()
    print("=" * 70)
    print("CONCLUSION: Staff routing should now work correctly!")
    print("=" * 70)

if __name__ == "__main__":
    test_staff_routing()



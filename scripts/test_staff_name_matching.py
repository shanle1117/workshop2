#!/usr/bin/env python3
"""
Test script to verify staff name matching functionality
"""

import sys
from pathlib import Path
from typing import List, Dict

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up Django environment
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')

# Import Django setup
import django
django.setup()

from django_app.views import match_staff_by_name, format_staff_details
from src.agents import _get_staff_documents


def test_staff_name_matching():
    """Test staff name matching functionality."""
    print("=" * 70)
    print("TESTING STAFF NAME MATCHING")
    print("=" * 70)
    print()
    
    # Load staff documents
    staff_docs = _get_staff_documents()
    
    if not staff_docs:
        print("[ERROR] No staff documents loaded!")
        return False
    
    print(f"Loaded {len(staff_docs)} staff members")
    print()
    
    # Show sample staff names
    print("Sample staff names:")
    for i, staff in enumerate(staff_docs[:10], 1):
        print(f"  {i}. {staff.get('name', 'N/A')}")
    print()
    
    # Test queries
    test_queries = [
        # Full name queries
        ("Who is Burhanuddin?", "Should match if Burhanuddin exists"),
        ("Email for Dr. Ahmad Zulkifli", "Should match if Ahmad Zulkifli exists"),
        ("Contact information for Deputy Registrar", "Should match by position"),
        
        # Partial name queries
        ("Who is Ahmad?", "Should match any staff with 'Ahmad' in name"),
        ("Email for Zulkifli", "Should match any staff with 'Zulkifli' in name"),
        
        # General queries (should not match)
        ("Who works in administration?", "Should NOT match specific names"),
        ("List all professors", "Should NOT match specific names"),
    ]
    
    print("Testing name matching:")
    print("-" * 70)
    
    for query, expected in test_queries:
        print(f"\nQuery: '{query}'")
        print(f"Expected: {expected}")
        
        matched = match_staff_by_name(query, staff_docs)
        
        if matched:
            print(f"  [MATCH] Found {len(matched)} staff member(s):")
            for staff in matched[:3]:  # Show first 3
                print(f"    - {staff.get('name', 'N/A')} ({staff.get('role', 'N/A')})")
            
            # Test formatting
            if len(matched) == 1:
                formatted = format_staff_details(matched[0])
                print(f"\n  Formatted output:")
                print("  " + "\n  ".join(formatted.split("\n")))
        else:
            print(f"  [NO MATCH] No staff members matched")
    
    print()
    print("=" * 70)
    print("TESTING COMPLETE")
    print("=" * 70)
    
    return True


if __name__ == "__main__":
    success = test_staff_name_matching()
    sys.exit(0 if success else 1)

